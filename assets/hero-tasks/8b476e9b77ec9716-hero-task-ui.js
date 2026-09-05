"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("purchase-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-purchase");
  const formatter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 2});
  const decimal = formatter.formatToParts(1.1).find((part) => part.type === "decimal").value;
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    return decimal === "." ? text : text.split(decimal).join(".");
  }

  function read() {
    return {
      hourly_income: numeric(document.getElementById("hourly-income").value),
      workday_hours: numeric(document.getElementById("workday-hours").value),
      items: Array.from(rows.children, (row) => {
        const quantity = numeric(row.querySelector("[data-field=quantity]").value);
        return {
          name: row.querySelector("[data-field=name]").value,
          quantity: /^\d{1,3}$/.test(quantity) ? Number(quantity) : NaN,
          price: numeric(row.querySelector("[data-field=price]").value)
        };
      })
    };
  }

  function update() {
    try {
      const result = core.run(config.adapter, read());
      Array.from(rows.children).forEach((row, index) => {
        const item = result.items[index];
        row.querySelector("[data-output=amount]").textContent = formatter.format(item.total_minor / 100);
        row.querySelector("[data-output=hours]").textContent = formatter.format(item.work_hours);
        row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
      });
      document.getElementById("total-amount").textContent = formatter.format(result.total_minor / 100);
      document.getElementById("total-hours").textContent = formatter.format(result.work_hours);
      document.getElementById("total-days").textContent = formatter.format(result.workdays);
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      for (const output of document.querySelectorAll("[data-output], .total-value")) output.textContent = "—";
      return false;
    } finally {
      add.disabled = rows.children.length >= core.MAX_ITEMS;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length === 1;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    document.getElementById("hourly-income").value = config.example.hourly_income;
    document.getElementById("workday-hours").value = config.example.workday_hours;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("purchase-template").content.firstElementChild.cloneNode(true);
    for (const field of ["name", "quantity", "price"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "purchase-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_ITEMS) return;
    append({name: config.copy.item + " " + formatter.format(sequence + 1), quantity: 1, price: "0"});
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".purchase-row");
    if (!window.confirm(config.copy.remove + ": " + row.querySelector("[data-field=name]").value)) return;
    const next = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    update();
    next.querySelector("input").focus();
  });
  form.addEventListener("input", update);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    update();
  });
  document.getElementById("reset-example").addEventListener("click", () => {
    const scope = config.copy.reset + "\n" + config.copy.item + ": " +
      formatter.format(rows.children.length) + "\n" + config.copy.income + "\n" + config.copy.day;
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
  update();
  document.getElementById("hero-fields").disabled = false;
  form.dataset.ready = "true";
})();
