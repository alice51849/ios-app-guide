"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_FIXED_ROWS = 15;
  const MAX_AMOUNT_MINOR = 100000000 * 100;
  const MAX_DAYS = 120;
  const MAX_TRAVELERS = 20;
  const ADAPTER = "trip-budget-v1";
  const CATEGORIES = Object.freeze(["food", "transport", "tickets", "shopping"]);
  const CONTROL = /[\u0000-\u001f\u007f]/;

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Amounts are decimal strings with at most two fractional digits and become
  // integer minor units, so sums never accumulate floating-point error.
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

  function wholeNumber(value, minimum, maximum, message) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,2})$/.test(value)) throw new TypeError(message);
    const number = Number(value);
    if (number < minimum || number > maximum) throw new RangeError(message);
    return number;
  }

  function shortText(value, message) {
    if (typeof value !== "string" || !value.trim() || value.length > 120 || CONTROL.test(value)) {
      throw new TypeError(message);
    }
    return value.trim();
  }

  function tripBudget(input) {
    objectWithKeys(input, ["budget_total", "days", "travelers", "shares", "items"]);
    const budgetMinor = minorUnits(input.budget_total);
    if (budgetMinor <= 0) throw new RangeError("The total budget must be greater than zero.");
    const days = wholeNumber(input.days, 1, MAX_DAYS, "Days must be a whole number from 1 to 120.");
    const travelers = wholeNumber(input.travelers, 1, MAX_TRAVELERS, "Travelers must be a whole number from 1 to 20.");
    objectWithKeys(input.shares, CATEGORIES);
    const shares = {};
    let shareTotal = 0;
    for (const category of CATEGORIES) {
      shares[category] = wholeNumber(input.shares[category], 0, 100, "Each share is a whole percentage from 0 to 100.");
      shareTotal += shares[category];
    }
    if (shareTotal !== 100) throw new RangeError("The four shares must add up to exactly 100.");
    if (!Array.isArray(input.items) || input.items.length > MAX_FIXED_ROWS) {
      throw new RangeError("Provide at most fifteen fixed costs.");
    }
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "amount"]);
      return {
        index,
        name: shortText(item.name, "Provide a short, single-line cost name."),
        amount_minor: minorUnits(item.amount)
      };
    });
    const fixedMinor = items.reduce((sum, item) => sum + item.amount_minor, 0);
    const variableMinor = budgetMinor - fixedMinor;
    if (variableMinor < 0) throw new RangeError("Fixed costs already exceed the total budget.");
    // Daily figures are exact rationals of whole cents; they are only rounded
    // when printed, so category rows and the day total reconcile in the sheet.
    const perDayMinor = variableMinor / days;
    const perPersonDayMinor = perDayMinor / travelers;
    const categories = CATEGORIES.map((category) => ({
      category, share_pct: shares[category],
      per_day_minor: perDayMinor * shares[category] / 100,
      per_person_day_minor: perPersonDayMinor * shares[category] / 100
    }));
    return {
      adapter: ADAPTER, formula_version: 1,
      budget_minor: budgetMinor, days, travelers, items,
      fixed_total_minor: fixedMinor, variable_minor: variableMinor,
      per_day_minor: perDayMinor, per_person_day_minor: perPersonDayMinor,
      categories
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return tripBudget(input);
  }

  function money(minor) {
    const negative = minor < 0;
    const absolute = Math.abs(Math.round(minor));
    const text = String(Math.floor(absolute / 100)) + "." + String(absolute % 100).padStart(2, "0");
    return negative ? "-" + text : text;
  }

  function cell(value) {
    let text = String(value);
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["item", "amount", "share", "per_day", "per_person_day", "budget", "days", "travelers",
      "fixed", "variable", ...CATEGORIES];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.item, labels.amount, labels.share, labels.per_day, labels.per_person_day],
      [labels.budget, money(result.budget_minor), "", "", ""],
      [labels.days, String(result.days), "", "", ""],
      [labels.travelers, String(result.travelers), "", "", ""],
      ...result.items.map((item) => [item.name, money(item.amount_minor), "", "", ""]),
      [labels.fixed, money(result.fixed_total_minor), "", "", ""],
      [labels.variable, money(result.variable_minor), "100%", money(result.per_day_minor), money(result.per_person_day_minor)],
      ...result.categories.map((row) => [labels[row.category], "", row.share_pct + "%", money(row.per_day_minor), money(row.per_person_day_minor)])
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_FIXED_ROWS, MAX_DAYS, MAX_TRAVELERS, CATEGORIES, adapters: Object.freeze([ADAPTER]), run, csv, money
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
