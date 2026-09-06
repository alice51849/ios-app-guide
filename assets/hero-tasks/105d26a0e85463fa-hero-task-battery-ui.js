"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("battery-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-device");
  const todayInput = document.getElementById("today-month");
  const decimals = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const oneDecimal = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 1, maximumFractionDigits: 1});
  const counter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    return text;
  }

  function localMonth() {
    const now = new Date();
    return now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0");
  }

  function read() {
    return {
      today: numeric(todayInput.value),
      items: Array.from(rows.children, (row) => ({
        name: row.querySelector("[data-field=name]").value,
        purchase_month: numeric(row.querySelector("[data-field=purchase_month]").value),
        max_capacity_pct: numeric(row.querySelector("[data-field=max_capacity_pct]").value),
        cycle_count: numeric(row.querySelector("[data-field=cycle_count]").value)
      }))
    };
  }

  function range(low, high, formatter) {
    return formatter.format(low) + "–" + formatter.format(high);
  }

  function update() {
    try {
      const result = core.run(config.adapter, read());
      Array.from(rows.children).forEach((row, index) => {
        const item = result.items[index];
        row.querySelector("[data-output=age]").textContent = counter.format(item.age_months);
        row.querySelector("[data-output=wear]").textContent = range(item.wear_low, item.wear_high, decimals);
        const months = core.monthsText(config.copy, item);
        row.querySelector("[data-output=months]").textContent =
          months === null ? range(item.months_to_80_low, item.months_to_80_high, counter) : months;
        row.querySelector("[data-output=cycles]").textContent =
          item.cycles_per_month === null ? "—" : oneDecimal.format(item.cycles_per_month);
        row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
      });
      const summary = result.summary;
      document.getElementById("device-count").textContent = counter.format(summary.devices);
      document.getElementById("lowest-capacity").textContent = counter.format(summary.min_capacity_pct);
      const soonest = core.soonestText(config.copy, summary);
      document.getElementById("soonest-80").textContent =
        soonest === null ? range(summary.soonest_low, summary.soonest_high, counter) : soonest;
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      for (const output of document.querySelectorAll("[data-output],.total-value")) output.textContent = "—";
      return false;
    } finally {
      add.disabled = rows.children.length >= core.MAX_ITEMS;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length === 1;
    }
  }

  function restore(today) {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    todayInput.value = today || config.example.today;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("battery-template").content.firstElementChild.cloneNode(true);
    for (const field of ["name", "purchase_month", "max_capacity_pct", "cycle_count"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "device-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_ITEMS) return;
    append({name: config.copy.item + " " + counter.format(sequence + 1),
      purchase_month: config.example.items[0].purchase_month, max_capacity_pct: "100", cycle_count: ""});
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".battery-row");
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
  // The static example is dated; the live sheet starts from the visitor's own month.
  restore(localMonth());
  document.getElementById("hero-fields").disabled = false;
  form.dataset.ready = "true";
})();
