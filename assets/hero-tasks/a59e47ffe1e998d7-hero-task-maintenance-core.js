"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_ITEMS = 30;
  const MAX_INTERVAL = 3650;
  const MIN_YEAR = 1900;
  const MAX_YEAR = 2999;
  const DUE_SOON_DAYS = 7;
  const ADAPTER = "maintenance-next-due-v1";
  const UNITS = Object.freeze(["day", "week", "month"]);
  const DAY_MS = 86400000;

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  function daysInMonth(year, month) {
    return new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  }

  // Strict ISO calendar dates only: no time zones, no locale parsing.
  function calendarDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      throw new TypeError("Use a YYYY-MM-DD date.");
    }
    const year = Number(value.slice(0, 4));
    const month = Number(value.slice(5, 7));
    const day = Number(value.slice(8, 10));
    if (year < MIN_YEAR || year > MAX_YEAR || month < 1 || month > 12 ||
        day < 1 || day > daysInMonth(year, month - 1)) {
      throw new RangeError("Date is outside the supported calendar range.");
    }
    return {year, month: month - 1, day};
  }

  function iso(parts) {
    const pad = (value, width) => String(value).padStart(width, "0");
    return pad(parts.year, 4) + "-" + pad(parts.month + 1, 2) + "-" + pad(parts.day, 2);
  }

  function epochDays(parts) {
    return Date.UTC(parts.year, parts.month, parts.day) / DAY_MS;
  }

  function fromEpochDays(days) {
    const date = new Date(days * DAY_MS);
    return {year: date.getUTCFullYear(), month: date.getUTCMonth(), day: date.getUTCDate()};
  }

  // Month arithmetic keeps the day of month and clamps to the month's last day
  // (31 Jan + 1 month = 28/29 Feb), which is also how the App's contract behaves.
  function addInterval(parts, value, unit) {
    if (unit === "day") return fromEpochDays(epochDays(parts) + value);
    if (unit === "week") return fromEpochDays(epochDays(parts) + value * 7);
    const total = parts.year * 12 + parts.month + value;
    const year = Math.floor(total / 12);
    const month = total - year * 12;
    if (year > MAX_YEAR) throw new RangeError("Next due date is beyond the supported calendar range.");
    return {year, month, day: Math.min(parts.day, daysInMonth(year, month))};
  }

  function maintenanceNextDue(input) {
    objectWithKeys(input, ["today", "items"]);
    const today = calendarDate(input.today);
    const todayDays = epochDays(today);
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_ITEMS) {
      throw new RangeError("Provide between one and thirty tasks.");
    }
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "last_done", "interval_value", "interval_unit"]);
      if (typeof item.name !== "string" || !item.name.trim() || item.name.length > 120 ||
          /[\u0000-\u001f\u007f]/.test(item.name)) {
        throw new TypeError("Provide a short, single-line task name.");
      }
      if (!Number.isInteger(item.interval_value) || item.interval_value < 1 || item.interval_value > MAX_INTERVAL) {
        throw new RangeError("Interval must be a whole number from one to 3650.");
      }
      if (!UNITS.includes(item.interval_unit)) throw new RangeError("Unknown interval unit.");
      const lastDone = calendarDate(item.last_done);
      const nextDue = addInterval(lastDone, item.interval_value, item.interval_unit);
      const daysLeft = epochDays(nextDue) - todayDays;
      return {
        index,
        name: item.name.trim(),
        last_done: iso(lastDone),
        interval_value: item.interval_value,
        interval_unit: item.interval_unit,
        next_due: iso(nextDue),
        days_left: daysLeft,
        status: daysLeft < 0 ? "overdue" : daysLeft <= DUE_SOON_DAYS ? "due_soon" : "ok"
      };
    });
    const order = items.map((item) => item.index)
      .sort((a, b) => items[a].days_left - items[b].days_left || a - b);
    const counts = {overdue: 0, due_soon: 0, ok: 0};
    for (const item of items) counts[item.status] += 1;
    return {adapter: ADAPTER, formula_version: 1, today: iso(today), items, order, counts};
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return maintenanceNextDue(input);
  }

  function cell(value) {
    let text = String(value);
    // Quoting alone does not stop spreadsheet formula execution. A bare signed
    // integer (negative days left) is a number, not a formula, so it stays numeric.
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  // "day|days" style labels pick singular or plural; single-form labels are used as-is.
  function unitLabel(labels, unit, value) {
    const forms = String(labels["unit_" + unit]).split("|");
    return value === 1 ? forms[0] : forms[forms.length - 1];
  }

  function interval(labels, item) {
    return item.interval_value + " " + unitLabel(labels, item.interval_unit, item.interval_value);
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["item", "last_done", "interval", "next_due", "days_left", "status", "today",
      "unit_day", "unit_week", "unit_month", "status_ok", "status_due_soon", "status_overdue"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.item, labels.last_done, labels.interval, labels.next_due, labels.days_left, labels.status],
      ...result.order.map((index) => {
        const item = result.items[index];
        return [item.name, item.last_done, interval(labels, item), item.next_due, item.days_left,
          labels["status_" + item.status]];
      }),
      [labels.today, result.today, "", "", "", ""]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_ITEMS, MAX_INTERVAL, DUE_SOON_DAYS, UNITS, adapters: Object.freeze([ADAPTER]),
    run, csv, unitLabel, interval
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
