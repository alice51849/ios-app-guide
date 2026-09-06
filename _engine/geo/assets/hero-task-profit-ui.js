"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("profit-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const addIncome = document.getElementById("add-income");
  const addExpense = document.getElementById("add-expense");
  const projectInput = document.getElementById("project-name");
  const hoursInput = document.getElementById("hours-spent");
  const money = new Intl.NumberFormat(config.locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const percent = new Intl.NumberFormat(config.locale, {style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1});
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
      project_name: projectInput.value,
      hours_spent: numeric(hoursInput.value),
      items: Array.from(rows.children, (row) => ({
        name: row.querySelector("[data-field=name]").value,
        kind: row.dataset.kind,
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
      show("income-total", money.format(result.income_total_minor / 100));
      show("expense-total", money.format(result.expense_total_minor / 100));
      show("profit-total", money.format(result.profit_minor / 100));
      show("margin-total", result.margin === null ? "—" : percent.format(result.margin));
      show("hourly-net", result.hourly_net_minor === null ? "—" : money.format(result.hourly_net_minor / 100));
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      for (const output of document.querySelectorAll(".total-value")) output.textContent = "—";
      return false;
    } finally {
      const counts = {income: 0, expense: 0};
      for (const row of rows.children) counts[row.dataset.kind] += 1;
      addIncome.disabled = counts.income >= core.MAX_ROWS_PER_KIND;
      addExpense.disabled = counts.expense >= core.MAX_ROWS_PER_KIND;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length === 1;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    projectInput.value = config.example.project_name;
    hoursInput.value = config.example.hours_spent;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("profit-template").content.firstElementChild.cloneNode(true);
    row.dataset.kind = item.kind;
    row.querySelector("[data-output=kind]").textContent = config.copy[item.kind];
    for (const field of ["name", "amount"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "row-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  function addRow(kind) {
    const count = Array.from(rows.children).filter((row) => row.dataset.kind === kind).length;
    if (count >= core.MAX_ROWS_PER_KIND) return;
    append({name: config.copy[kind] + " " + counter.format(count + 1), kind, amount: "0"});
    update();
    rows.lastElementChild.querySelector("input").focus();
  }

  addIncome.addEventListener("click", () => addRow("income"));
  addExpense.addEventListener("click", () => addRow("expense"));
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".profit-row");
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
