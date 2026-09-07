"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("split-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-person");
  const taxInput = document.getElementById("tax-pct");
  const tipInput = document.getElementById("tip-pct");
  const money = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const counter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  const decimal = money.formatToParts(1.1).find((part) => part.type === "decimal").value;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    // Accept the locale's own decimal separator (comma, Arabic momayyez, ...) as
    // well as a plain comma; the core only understands the dot.
    if (decimal !== ".") text = text.split(decimal).join(".");
    return text.replace(",", ".");
  }

  function read() {
    return {
      tax_pct: numeric(taxInput.value),
      tip_pct: numeric(tipInput.value),
      items: Array.from(rows.children, (row) => ({
        name: row.querySelector("[data-field=name]").value,
        amount: numeric(row.querySelector("[data-field=amount]").value)
      }))
    };
  }

  function show(id, value) {
    document.getElementById(id).textContent = value;
  }

  function update() {
    try {
      const result = core.run(config.adapter, read());
      Array.from(rows.children).forEach((row, index) => {
        const item = result.items[index];
        row.querySelector("[data-remove]").setAttribute("aria-label",
          config.copy.remove + " · " + row.querySelector("[data-field=name]").value);
        row.querySelector("[data-output=tax]").textContent = money.format(item.tax_minor / 100);
        row.querySelector("[data-output=tip]").textContent = money.format(item.tip_minor / 100);
        row.querySelector("[data-output=due]").textContent = money.format(item.total_minor / 100);
      });
      show("subtotal-value", money.format(result.subtotal_minor / 100));
      show("tax-value", money.format(result.tax_minor / 100));
      show("tip-value", money.format(result.tip_minor / 100));
      show("grand-total-value", money.format(result.grand_total_minor / 100));
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      for (const output of document.querySelectorAll(".total-value, [data-output]")) output.textContent = "—";
      return false;
    } finally {
      add.disabled = rows.children.length >= core.MAX_PEOPLE;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length === 1;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    taxInput.value = config.example.tax_pct;
    tipInput.value = config.example.tip_pct;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("split-template").content.firstElementChild.cloneNode(true);
    for (const field of ["name", "amount"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "row-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_PEOPLE) return;
    append({name: config.copy.person + " " + counter.format(rows.children.length + 1), amount: "0"});
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".split-row");
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
    const scope = config.copy.reset + "\n" + config.copy.person + ": " + counter.format(rows.children.length);
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
