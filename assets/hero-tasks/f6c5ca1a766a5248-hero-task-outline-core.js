"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MIN_POINTS = 3;
  const MAX_POINTS = 12;
  const MAX_HEADLINE = 80;
  const MAX_POINT = 160;
  const MAX_ACTION = 160;
  const MAX_METRIC = 60;
  const ADAPTER = "one-page-outline-v1";
  const CONTROL = /[\u0000-\u001f\u007f]/;
  const SECTIONS = Object.freeze(["headline", "point", "action", "metric"]);

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Text is trimmed and length-checked only. Nothing is summarised, reworded
  // or generated: the sheet structures what the user typed, exactly as typed.
  function line(value, maximum, message, optional) {
    if (typeof value !== "string" || CONTROL.test(value)) throw new TypeError(message);
    const text = value.trim();
    if (!text) {
      if (optional) return "";
      throw new TypeError(message);
    }
    if (text.length > maximum) throw new RangeError(message);
    return text;
  }

  function onePageOutline(input) {
    objectWithKeys(input, ["headline", "points", "action", "metric"]);
    const headline = line(input.headline, MAX_HEADLINE, "Provide a single-line headline of at most 80 characters.");
    if (!Array.isArray(input.points) || input.points.length < MIN_POINTS || input.points.length > MAX_POINTS) {
      throw new RangeError("Provide between three and twelve points.");
    }
    const points = input.points.map((point, index) => ({
      order: index + 1,
      text: line(point, MAX_POINT, "Each point is a single line of at most 160 characters.")
    }));
    const action = line(input.action, MAX_ACTION, "Provide a single-line next action of at most 160 characters.");
    const metric = line(input.metric, MAX_METRIC, "The number is a single line of at most 60 characters.", true);
    const sections = [
      {section: "headline", order: 1, text: headline},
      ...points.map((point) => ({section: "point", order: point.order, text: point.text})),
      {section: "action", order: 1, text: action}
    ];
    // The metric is whatever the user typed, kept as text: an ordinal or a
    // label is never turned into a value that could be charted.
    if (metric) sections.push({section: "metric", order: 1, text: metric});
    return {
      adapter: ADAPTER, formula_version: 1, headline, points, action, metric: metric || null,
      point_count: points.length, sections
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return onePageOutline(input);
  }

  function cell(value) {
    let text = String(value);
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["section", "order", "text", ...SECTIONS];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.section, labels.order, labels.text],
      ...result.sections.map((row) => [labels[row.section], String(row.order), row.text])
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MIN_POINTS, MAX_POINTS, MAX_HEADLINE, MAX_POINT, MAX_ACTION, MAX_METRIC, SECTIONS,
    adapters: Object.freeze([ADAPTER]), run, csv
  });
});

if (typeof module === "object" && module.exports && require.main === module) {
  try {
    const requests = JSON.parse(require("node:fs").readFileSync(0, "utf8"));
    if (!Array.isArray(requests) || requests.length > 500) throw new RangeError("Invalid build batch.");
    const output = requests.map(({adapter, input, labels}) => ({
      result: module.exports.run(adapter, input),
      csv: module.exports.csv(adapter, input, labels)
    }));
    process.stdout.write(JSON.stringify(output));
  } catch (error) {
    process.stderr.write(error.name + ": " + error.message + "\n");
    process.exitCode = 1;
  }
}
