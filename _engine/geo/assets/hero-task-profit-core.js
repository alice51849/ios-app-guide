"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_ROWS_PER_KIND = 20;
  const MAX_AMOUNT_MINOR = 100000000 * 100;
  const MIN_HOURS_QUARTERS = 1;      // 0.25 h
  const MAX_HOURS_QUARTERS = 8000;   // 2000 h
  const ADAPTER = "project-profit-v1";
  const KINDS = Object.freeze(["income", "expense"]);

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Amounts are decimal strings with at most two fractional digits and become
  // integer minor units, so totals never accumulate floating-point error.
  function minorUnits(value) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,8})(\.\d{1,2})?$/.test(value)) {
      throw new TypeError("Use a non-negative amount with at most two fractional digits.");
    }
    const parts = value.split(".");
    const result = Number(parts[0]) * 100 + Number((parts[1] || "").padEnd(2, "0"));
    if (!Number.isSafeInteger(result) || result > MAX_AMOUNT_MINOR) {
      throw new RangeError("Amount is outside the supported range.");
    }
    return result;
  }

  // Hours are optional; when present they are a positive decimal in quarter-hour
  // steps (0.25 to 2000) so the hourly figure has a stable, honest denominator.
  function hoursQuarters(value) {
    if (typeof value !== "string") throw new TypeError("Hours must be text.");
    if (value.trim() === "") return null;
    if (!/^(0|[1-9]\d{0,3})(\.(25|5|50|75|0|00))?$/.test(value)) {
      throw new TypeError("Use hours in quarter-hour steps, for example 12.5 or 0.75.");
    }
    const parts = value.split(".");
    const fraction = {"": 0, "0": 0, "00": 0, "25": 1, "5": 2, "50": 2, "75": 3}[parts[1] || ""];
    const quarters = Number(parts[0]) * 4 + fraction;
    if (quarters < MIN_HOURS_QUARTERS || quarters > MAX_HOURS_QUARTERS) {
      throw new RangeError("Hours must be between 0.25 and 2000.");
    }
    return quarters;
  }

  function shortText(value, message) {
    if (typeof value !== "string" || !value.trim() || value.length > 120 || /[\u0000-\u001f\u007f]/.test(value)) {
      throw new TypeError(message);
    }
    return value.trim();
  }

  function projectProfit(input) {
    objectWithKeys(input, ["project_name", "hours_spent", "items"]);
    const project = shortText(input.project_name, "Provide a short, single-line project name.");
    const quarters = hoursQuarters(input.hours_spent);
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_ROWS_PER_KIND * 2) {
      throw new RangeError("Provide between one and forty rows.");
    }
    const counts = {income: 0, expense: 0};
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "kind", "amount"]);
      if (!KINDS.includes(item.kind)) throw new RangeError("Each row is either income or expense.");
      counts[item.kind] += 1;
      return {
        index,
        name: shortText(item.name, "Provide a short, single-line row name."),
        kind: item.kind,
        amount_minor: minorUnits(item.amount)
      };
    });
    if (counts.income < 1 && counts.expense < 1) throw new RangeError("Provide at least one row.");
    for (const kind of KINDS) {
      if (counts[kind] > MAX_ROWS_PER_KIND) throw new RangeError("At most twenty rows per kind.");
    }
    const incomeMinor = items.filter((item) => item.kind === "income").reduce((sum, item) => sum + item.amount_minor, 0);
    const expenseMinor = items.filter((item) => item.kind === "expense").reduce((sum, item) => sum + item.amount_minor, 0);
    const profitMinor = incomeMinor - expenseMinor;
    // Margin is undefined without income; hourly net is undefined without hours.
    // Both stay null instead of pretending to be zero.
    const margin = incomeMinor > 0 ? profitMinor / incomeMinor : null;
    const hourlyNetMinor = quarters === null ? null : profitMinor * 4 / quarters;
    return {
      adapter: ADAPTER, formula_version: 1, project_name: project,
      hours_spent: quarters === null ? null : quarters / 4,
      items, counts,
      income_total_minor: incomeMinor, expense_total_minor: expenseMinor, profit_minor: profitMinor,
      margin, hourly_net_minor: hourlyNetMinor
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return projectProfit(input);
  }

  function money(minor) {
    const negative = minor < 0;
    const absolute = Math.abs(Math.round(minor));
    const text = String(Math.floor(absolute / 100)) + "." + String(absolute % 100).padStart(2, "0");
    return negative ? "-" + text : text;
  }

  function percent(ratio) {
    return ratio === null ? "" : (ratio * 100).toFixed(1) + "%";
  }

  function cell(value) {
    let text = String(value);
    // Quoting alone does not stop spreadsheet formula execution. A plain signed
    // decimal is a number, not a formula, so negative profit stays numeric.
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["kind", "item", "amount", "income", "expense", "income_total", "expense_total",
      "profit", "margin", "hourly_net", "project", "hours"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.kind, labels.item, labels.amount],
      ...result.items.map((item) => [labels[item.kind], item.name, money(item.amount_minor)]),
      [labels.project, result.project_name, ""],
      [labels.hours, "", result.hours_spent === null ? "" : String(result.hours_spent)],
      [labels.income_total, "", money(result.income_total_minor)],
      [labels.expense_total, "", money(result.expense_total_minor)],
      [labels.profit, "", money(result.profit_minor)],
      [labels.margin, "", percent(result.margin)],
      [labels.hourly_net, "", result.hourly_net_minor === null ? "" : money(result.hourly_net_minor)]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_ROWS_PER_KIND, KINDS, adapters: Object.freeze([ADAPTER]), run, csv, money, percent
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
