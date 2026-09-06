"use strict";

(function () {
  const config = JSON.parse(document.getElementById("hero-config").textContent);
  const core = globalThis.HeroTaskCore;
  const form = document.getElementById("hero-form");
  const rows = document.getElementById("point-rows");
  const status = document.getElementById("hero-status");
  const download = document.getElementById("download-csv");
  const add = document.getElementById("add-point");
  const headlineInput = document.getElementById("headline");
  const actionInput = document.getElementById("next-action");
  const metricInput = document.getElementById("metric");
  const counter = new Intl.NumberFormat(config.locale, {maximumFractionDigits: 0});
  let sequence = rows.children.length;

  function read() {
    return {
      headline: headlineInput.value,
      points: Array.from(rows.children, (row) => row.querySelector("[data-field=point]").value),
      action: actionInput.value,
      metric: metricInput.value
    };
  }

  function preview(result) {
    document.getElementById("preview-headline").textContent = result.headline;
    const list = document.getElementById("preview-points");
    list.replaceChildren(...result.points.map((point) => {
      const item = document.createElement("li");
      item.textContent = point.text;
      return item;
    }));
    document.getElementById("preview-action").textContent = result.action;
    const metric = document.getElementById("preview-metric");
    metric.textContent = result.metric || "";
    metric.hidden = !result.metric;
    document.getElementById("point-count").textContent = counter.format(result.point_count);
  }

  function update() {
    try {
      const result = core.run(config.adapter, read());
      Array.from(rows.children).forEach((row, index) => {
        row.querySelector("[data-remove]").setAttribute("aria-label",
          config.copy.remove + " · " + counter.format(index + 1));
      });
      preview(result);
      status.textContent = "";
      download.disabled = false;
      return true;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      status.textContent = config.copy.error;
      download.disabled = true;
      document.getElementById("point-count").textContent = "—";
      return false;
    } finally {
      add.disabled = rows.children.length >= core.MAX_POINTS;
      for (const button of rows.querySelectorAll("[data-remove]")) button.disabled = rows.children.length <= core.MIN_POINTS;
    }
  }

  function restore() {
    rows.replaceChildren();
    sequence = 0;
    for (const point of config.example.points) append(point);
    headlineInput.value = config.example.headline;
    actionInput.value = config.example.action;
    metricInput.value = config.example.metric;
    update();
  }

  function append(text) {
    sequence += 1;
    const row = document.getElementById("point-template").content.firstElementChild.cloneNode(true);
    const input = row.querySelector("[data-field=point]");
    input.value = text;
    input.id = "row-" + sequence + "-point";
    row.querySelector("[data-label=point]").htmlFor = input.id;
    row.querySelector("[data-label=point]").textContent = config.copy.point + " " + counter.format(sequence);
    rows.appendChild(row);
  }

  add.addEventListener("click", () => {
    if (rows.children.length >= core.MAX_POINTS) return;
    append("");
    update();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button || rows.children.length <= core.MIN_POINTS) return;
    const row = button.closest(".point-row");
    if (!window.confirm(config.copy.remove + ": " + row.querySelector("[data-field=point]").value)) return;
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
    const scope = config.copy.reset + "\n" + config.copy.point + ": " + counter.format(rows.children.length);
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
