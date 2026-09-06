"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("bandwidth-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-row");
  const planDown = document.getElementById("plan-down");
  const planUp = document.getElementById("plan-up");
  const speed = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 1, maximumFractionDigits: 1});
  const counter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  const decimal = speed.formatToParts(1.1).find((part) => part.type === "decimal").value;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    // Accept the locale's own decimal separator as well as a plain comma; the
    // core only understands the dot.
    if (decimal !== ".") text = text.split(decimal).join(".");
    return text.replace(",", ".");
  }

  function read() {
    return {
      plan_down_mbps: numeric(planDown.value),
      plan_up_mbps: numeric(planUp.value),
      items: Array.from(rows.children, (row) => ({
        name: row.querySelector("[data-field=name]").value,
        activity: row.querySelector("[data-field=activity]").value,
        devices: numeric(row.querySelector("[data-field=devices]").value)
      }))
    };
  }

  function show(id, value) {
    document.getElementById(id).textContent = value;
  }

  function mbps(tenths) {
    return speed.format(tenths / 10);
  }

  function update() {
    try {
      const result = core.run(config.adapter, read());
      Array.from(rows.children).forEach((row, index) => {
        const item = result.items[index];
        row.querySelector("[data-remove]").setAttribute("aria-label",
          config.copy.remove + " · " + row.querySelector("[data-field=name]").value);
        row.querySelector("[data-output=total_down]").textContent = mbps(item.total_down_tenths);
        row.querySelector("[data-output=total_up]").textContent = mbps(item.total_up_tenths);
      });
      show("need-down", mbps(result.need_down_tenths));
      show("need-up", mbps(result.need_up_tenths));
      show("headroom-down", mbps(result.headroom_down_tenths));
      show("headroom-up", mbps(result.headroom_up_tenths));
      const badge = document.getElementById("status-total");
      badge.textContent = config.copy["status_" + result.status];
      badge.dataset.status = result.status;
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      for (const output of document.querySelectorAll(".total-value, [data-output]")) output.textContent = "—";
      delete document.getElementById("status-total").dataset.status;
      return false;
    } finally {
      add.disabled = rows.children.length >= core.MAX_ROWS;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length === 1;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    planDown.value = config.example.plan_down_mbps;
    planUp.value = config.example.plan_up_mbps;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("bandwidth-template").content.firstElementChild.cloneNode(true);
    for (const field of ["name", "activity", "devices"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "row-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_ROWS) return;
    append({name: config.copy.item + " " + counter.format(rows.children.length + 1), activity: "browsing", devices: "1"});
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".bandwidth-row");
    if (!window.confirm(config.copy.remove + ": " + row.querySelector("[data-field=name]").value)) return;
    const next = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    update();
    next.querySelector("input").focus();
  });
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    update();
  });
  document.getElementById("reset-example").addEventListener("click", () => {
    const scope = config.copy.reset + "\n" + config.copy.item + ": " + counter.format(rows.children.length);
    if (window.confirm(scope)) restore();
  });
  download.addEventListener("click", () => {
    if (!update()) return;
    const blob = new Blob([core.csv(config.adapter, read(), config.copy)], {type: "text/csv;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = config.slug + ".csv";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  // Never retain edits, including when a browser restores a back/forward snapshot.
  window.addEventListener("pagehide", restore);
  window.addEventListener("pageshow", (event) => { if (event.persisted) restore(); });
  restore();
  document.getElementById("hero-fields").disabled = false;
  form.dataset.ready = "true";
})();
