"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_PEOPLE = 20;
  const MAX_AMOUNT_MINOR = 100000000 * 100;
  const MAX_RATE = 10000; // hundredths of a percent, i.e. 100.00%
  const ADAPTER = "bill-split-v1";
  const CONTROL = /[\u0000-\u001f\u007f]/;

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Amounts are decimal strings with at most two fractional digits and become
  // integer minor units, so the split always reconciles to the exact bill.
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

  // Percentages keep two decimals as hundredths of a percent; 8.25% is 825.
  function rate(value, message) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,2})(\.\d{1,2})?$/.test(value)) throw new TypeError(message);
    const parts = value.split(".");
    const result = Number(parts[0]) * 100 + Number((parts[1] || "").padEnd(2, "0"));
    if (result > MAX_RATE) throw new RangeError(message);
    return result;
  }

  function shortText(value, message) {
    if (typeof value !== "string" || !value.trim() || value.length > 120 || CONTROL.test(value)) {
      throw new TypeError(message);
    }
    return value.trim();
  }

  // Half-up on a non-negative integer quotient; never banker's rounding, so the
  // page, the CSV and the Python renderer print the same cents.
  function scaled(amountMinor, hundredthsOfPercent) {
    return Math.floor((amountMinor * hundredthsOfPercent) / 10000 + 0.5);
  }

  // Largest-remainder allocation: every cent of tax and tip is handed to exactly
  // one person, in proportion to what that person ordered. The parts always add
  // back up to the charge, which plain per-person rounding cannot guarantee.
  function allocate(totalMinor, weights, weightSum) {
    const exact = weights.map((weight) => (totalMinor * weight) / weightSum);
    const shares = exact.map((value) => Math.floor(value));
    let remainder = totalMinor - shares.reduce((sum, value) => sum + value, 0);
    const order = exact
      .map((value, index) => ({index, fraction: value - Math.floor(value)}))
      .sort((left, right) => right.fraction - left.fraction || left.index - right.index);
    for (let position = 0; remainder > 0; position += 1, remainder -= 1) {
      shares[order[position % order.length].index] += 1;
    }
    return shares;
  }

  function billSplit(input) {
    objectWithKeys(input, ["tax_pct", "tip_pct", "items"]);
    const taxRate = rate(input.tax_pct, "Tax is a percentage from 0 to 100 with at most two decimals.");
    const tipRate = rate(input.tip_pct, "Tip is a percentage from 0 to 100 with at most two decimals.");
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_PEOPLE) {
      throw new RangeError("Provide between one and twenty people.");
    }
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "amount"]);
      return {
        index, order: index + 1,
        name: shortText(item.name, "Provide a short, single-line name."),
        amount_minor: minorUnits(item.amount)
      };
    });
    const subtotalMinor = items.reduce((sum, item) => sum + item.amount_minor, 0);
    if (subtotalMinor <= 0) throw new RangeError("The shared bill must be greater than zero.");
    const taxMinor = scaled(subtotalMinor, taxRate);
    const tipMinor = scaled(subtotalMinor, tipRate);
    const weights = items.map((item) => item.amount_minor);
    const taxShares = allocate(taxMinor, weights, subtotalMinor);
    const tipShares = allocate(tipMinor, weights, subtotalMinor);
    const rows = items.map((item, index) => ({
      index: item.index, order: item.order, name: item.name, amount_minor: item.amount_minor,
      tax_minor: taxShares[index],
      tip_minor: tipShares[index],
      total_minor: item.amount_minor + taxShares[index] + tipShares[index]
    }));
    return {
      adapter: ADAPTER, formula_version: 1,
      tax_rate: taxRate, tip_rate: tipRate, items: rows,
      subtotal_minor: subtotalMinor, tax_minor: taxMinor, tip_minor: tipMinor,
      grand_total_minor: subtotalMinor + taxMinor + tipMinor,
      people: rows.length
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return billSplit(input);
  }

  function money(minor) {
    return Math.floor(minor / 100) + "." + String(minor % 100).padStart(2, "0");
  }

  function percentText(hundredthsOfPercent) {
    return money(hundredthsOfPercent) + "%";
  }

  function cell(value) {
    let text = String(value);
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["person", "amount", "tax_share", "tip_share", "total_due", "subtotal", "tax", "tip", "grand_total"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.person, labels.amount, labels.tax_share, labels.tip_share, labels.total_due],
      ...result.items.map((item) => [item.name, money(item.amount_minor), money(item.tax_minor),
        money(item.tip_minor), money(item.total_minor)]),
      [labels.subtotal, money(result.subtotal_minor), "", "", ""],
      [labels.tax, percentText(result.tax_rate), money(result.tax_minor), "", ""],
      [labels.tip, percentText(result.tip_rate), money(result.tip_minor), "", ""],
      [labels.grand_total, "", "", "", money(result.grand_total_minor)]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_PEOPLE, MAX_AMOUNT_MINOR, MAX_RATE, adapters: Object.freeze([ADAPTER]), run, csv, money, percentText
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
