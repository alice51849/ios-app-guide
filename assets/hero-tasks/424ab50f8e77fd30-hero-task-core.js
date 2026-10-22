"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_ITEMS = 30;
  const ADAPTER = "purchase-worktime-v1";

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  function hundredths(value, maximum, allowZero) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,8})(\.\d{1,2})?$/.test(value)) {
      throw new TypeError("Use a non-negative decimal with at most two fractional digits.");
    }
    const parts = value.split(".");
    const result = Number(parts[0]) * 100 + Number((parts[1] || "").padEnd(2, "0"));
    if (!Number.isSafeInteger(result) || result > maximum || (!allowZero && result === 0)) {
      throw new RangeError("Amount is outside the supported range.");
    }
    return result;
  }

  function purchaseWorktime(input) {
    objectWithKeys(input, ["hourly_income", "workday_hours", "items"]);
    const income = hundredths(input.hourly_income, 10000000000, false);
    const day = hundredths(input.workday_hours, 2400, false);
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_ITEMS) {
      throw new RangeError("Provide between one and thirty purchases.");
    }
    const items = input.items.map((item) => {
      objectWithKeys(item, ["name", "quantity", "price"]);
      if (typeof item.name !== "string" || !item.name.trim() || item.name.length > 120 ||
          /[\u0000-\u001f\u007f]/.test(item.name)) {
        throw new TypeError("Provide a short, single-line purchase name.");
      }
      if (!Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 999) {
        throw new RangeError("Quantity must be an integer from one to 999.");
      }
      const price = hundredths(item.price, 10000000000, true);
      const amount = price * item.quantity;
      return {
        name: item.name.trim(),
        quantity: item.quantity,
        price_minor: price,
        total_minor: amount,
        work_hours: amount / income,
        workdays: amount * 100 / (income * day)
      };
    });
    const total = items.reduce((sum, item) => sum + item.total_minor, 0);
    return {
      adapter: ADAPTER,
      formula_version: 1,
      hourly_income_minor: income,
      workday_hundredths: day,
      items,
      total_minor: total,
      work_hours: total / income,
      workdays: total * 100 / (income * day)
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return purchaseWorktime(input);
  }

  function cell(value) {
    let text = String(value);
    // Quoting alone does not stop spreadsheet formula execution.
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["item", "quantity", "price", "total", "income", "day", "hours", "days"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const money = (value) => (value / 100).toFixed(2);
    const values = (item) => [
      item.name, item.quantity, money(item.price_minor), money(item.total_minor),
      money(result.hourly_income_minor), money(result.workday_hundredths),
      item.work_hours.toFixed(2), item.workdays.toFixed(2)
    ];
    const rows = [
      keys.map((key) => labels[key]),
      ...result.items.map(values),
      [labels.total, "", "", money(result.total_minor),
        money(result.hourly_income_minor), money(result.workday_hundredths),
        result.work_hours.toFixed(2), result.workdays.toFixed(2)]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({MAX_ITEMS, adapters: Object.freeze([ADAPTER]), run, csv});
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
