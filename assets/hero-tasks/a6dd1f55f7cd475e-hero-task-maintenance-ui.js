"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("maintenance-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-task");
  const todayInput = document.getElementById("today-date");
  const formatter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  const dateFormatter = new Intl.DateTimeFormat(config.locale, {dateStyle: "medium", timeZone: "UTC"});
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    return text;
  }

  function localDate() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
  }

  function displayDate(value) {
    return dateFormatter.format(new Date(value + "T00:00:00Z"));
  }

  function read() {
    return {
      today: todayInput.value.trim(),
      items: Array.from(rows.children, (row) => {
        const interval = numeric(row.querySelector("[data-field=interval_value]").value);
        return {
          name: row.querySelector("[data-field=name]").value,
          last_done: row.querySelector("[data-field=last_done]").value.trim(),
          interval_value: /^\d{1,4}$/.test(interval) ? Number(interval) : NaN,
          interval_unit: row.querySelector("[data-field=interval_unit]").value
        };
      })
    };
  }

  function update() {
    try {
      const result = core.run(config.adapter, read());
      Array.from(rows.children).forEach((row, index) => {
        const item = result.items[index];
        row.querySelector("[data-output=next_due]").textContent = displayDate(item.next_due);
        row.querySelector("[data-output=days_left]").textContent = formatter.format(item.days_left);
        const badge = row.querySelector("[data-output=status]");
        badge.textContent = config.copy["status_" + item.status];
        badge.dataset.status = item.status;
        row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
      });
      for (const key of ["overdue", "due_soon", "ok"]) {
        document.getElementById("count-" + key).textContent = formatter.format(result.counts[key]);
      }
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

  function restore(today) {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    todayInput.value = today || config.example.today;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("maintenance-template").content.firstElementChild.cloneNode(true);
    for (const field of ["name", "last_done", "interval_value", "interval_unit"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "task-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_ITEMS) return;
    append({name: config.copy.item + " " + formatter.format(sequence + 1),
      last_done: todayInput.value.trim() || config.example.today, interval_value: 1, interval_unit: "month"});
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".maintenance-row");
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
    const scope = config.copy.reset + "\n" + config.copy.item + ": " +
      formatter.format(rows.children.length) + "\n" + config.copy.today;
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
  // The static example is dated; the live sheet starts from the visitor's own calendar day.
  restore(localDate());
  document.getElementById("hero-fields").disabled = false;
  form.dataset.ready = "true";
})();
