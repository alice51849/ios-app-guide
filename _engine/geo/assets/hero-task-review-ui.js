"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("note-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-note");
  const todayInput = document.getElementById("today-date");
  const counter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  const digits = Array.from({length: 10}, (_, index) =>
    new Intl.NumberFormat(config.locale, {useGrouping: false}).format(index));
  let sequence = rows.children.length;

  function numeric(value) {
    let text = value.trim();
    digits.forEach((digit, index) => { text = text.split(digit).join(String(index)); });
    return text;
  }

  function read() {
    return {
      today: numeric(todayInput.value),
      items: Array.from(rows.children, (row) => ({
        name: row.querySelector("[data-field=name]").value,
        studied_on: numeric(row.querySelector("[data-field=studied_on]").value)
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
        row.querySelector("[data-output=next]").textContent = item.next_review || "—";
        const badge = row.querySelector("[data-output=status]");
        const next = item.reviews.find((review) => review.days_left >= 0) || null;
        badge.textContent = next ? config.copy["status_" + next.status] : config.copy.status_passed;
        badge.dataset.status = next ? next.status : "passed";
      });
      show("note-count", counter.format(result.note_count));
      show("review-count", counter.format(result.review_count));
      show("next-review", result.next_review || "—");
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      for (const output of document.querySelectorAll(".total-value, [data-output]")) output.textContent = "—";
      for (const badge of rows.querySelectorAll("[data-output=status]")) delete badge.dataset.status;
      return false;
    } finally {
      add.disabled = rows.children.length >= core.MAX_NOTES;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length === 1;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const item of config.example.items) append(item);
    todayInput.value = config.example.today;
    update();
  }

  function append(item) {
    sequence += 1;
    const row = document.getElementById("note-template").content.firstElementChild.cloneNode(true);
    for (const field of ["name", "studied_on"]) {
      const input = row.querySelector("[data-field=" + field + "]");
      input.value = item[field];
      input.id = "row-" + sequence + "-" + field;
      row.querySelector("[data-label=" + field + "]").htmlFor = input.id;
    }
    row.querySelector("[data-remove]").setAttribute("aria-label", config.copy.remove + " · " + item.name);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_NOTES) return;
    append({
      name: config.copy.note + " " + counter.format(rows.children.length + 1),
      studied_on: numeric(todayInput.value)
    });
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length === 1) return;
    const row = button.closest(".note-row");
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
    const scope = config.copy.reset + "\n" + config.copy.note + ": " + counter.format(rows.children.length);
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
