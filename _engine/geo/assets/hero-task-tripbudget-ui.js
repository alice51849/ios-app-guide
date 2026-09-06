"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("fixed-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-fixed");
  const budgetInput = document.getElementById("budget-total");
  const daysInput = document.getElementById("trip-days");
  const travelersInput = document.getElementById("travelers");
  const money = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const counter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  const decimal = money.formatToParts(1.1).find((part) => part.type === "decimal").value;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    if (decimal !== ".") text = text.split(decimal).join(".");
    return text.replace(",", ".");
  }

  function read() {
    const shares = {};
    for (const category of core.CATEGORIES) {
      shares[category] = numeric(document.getElementById("share-" + category).value);
    }
    return {
      budget_total: numeric(budgetInput.value),
      days: numeric(daysInput.value),
      travelers: numeric(travelersInput.value),
      shares,
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
      Array.from(rows.children).forEach((row) => {
        row.querySelector("[data-remove]").setAttribute("aria-label",
          config.copy.remove + " · " + row.querySelector("[data-field=name]").value);
      });
      show("fixed-total", money.format(result.fixed_total_minor / 100));
      show("variable-total", money.format(result.variable_minor / 100));
      show("per-day", money.format(result.per_day_minor / 100));
      show("per-person-day", money.format(result.per_person_day_minor / 100));
      for (const row of result.categories) {
        show("day-" + row.category, money.format(row.per_day_minor / 100));
        show("person-" + row.category, money.format(row.per_person_day_minor / 100));
      }
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
      add.disabled = rows.children.length >= core.MAX_FIXED_ROWS;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    budgetInput.value = config.example.budget_total;
    daysInput.value = config.example.days;
    travelersInput.value = config.example.travelers;
    for (const category of core.CATEGORIES) {
      document.getElementById("share-" + category).value = config.example.shares[category];
    }
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("fixed-template").content.firstElementChild.cloneNode(true);
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
    if (rows.children.length >= core.MAX_FIXED_ROWS) return;
    append({name: config.copy.item + " " + counter.format(rows.children.length + 1), amount: "0"});
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button) return;
    const row = button.closest(".fixed-row");
    if (!window.confirm(config.copy.remove + ": " + row.querySelector("[data-field=name]").value)) return;
    const next = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    update();
    (next ? next.querySelector("input") : budgetInput).focus();
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
