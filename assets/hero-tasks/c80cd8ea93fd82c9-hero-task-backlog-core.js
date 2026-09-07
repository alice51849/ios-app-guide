"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_ITEMS = 30;
  const MIN_MINUTES = 1;
  const MAX_MINUTES = 600;
  const MIN_DAILY = 5;
  const MAX_DAILY = 600;
  const MIN_YEAR = 2000;
  const MAX_YEAR = 2099;
  const DAY_MS = 86400000;
  const ADAPTER = "reading-backlog-v1";
  const CONTROL = /[\u0000-\u001f\u007f]/;

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
    return Date.UTC(year, month - 1, day) / DAY_MS;
  }

  function iso(epochDays) {
    const date = new Date(epochDays * DAY_MS);
    const pad = (value, width) => String(value).padStart(width, "0");
    return pad(date.getUTCFullYear(), 4) + "-" + pad(date.getUTCMonth() + 1, 2) + "-" + pad(date.getUTCDate(), 2);
  }

  function wholeNumber(value, minimum, maximum, message) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,3})$/.test(value)) throw new TypeError(message);
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

  // One reading session per day of exactly the daily budget. An item is finished
  // on the day its running total is reached, so a long item simply spans days;
  // nothing is reordered and nothing is dropped.
  function readingBacklog(input) {
    objectWithKeys(input, ["daily_minutes", "start_date", "items"]);
    const daily = wholeNumber(input.daily_minutes, MIN_DAILY, MAX_DAILY,
      "Daily reading time must be a whole number of minutes from 5 to 600.");
    const start = calendarDate(input.start_date);
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_ITEMS) {
      throw new RangeError("Provide between one and thirty saved items.");
    }
    let running = 0;
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "minutes"]);
      const name = shortText(item.name, "Provide a short, single-line item name.");
      const minutes = wholeNumber(item.minutes, MIN_MINUTES, MAX_MINUTES,
        "Reading time must be a whole number of minutes from 1 to 600.");
      running += minutes;
      const day = Math.ceil(running / daily);
      const finish = start + day - 1;
      if (finish > calendarDate(MAX_YEAR + "-12-31")) {
        throw new RangeError("The plan runs past the supported calendar range.");
      }
      return {
        index, order: index + 1, name, minutes,
        cumulative_min: running, day, finish_date: iso(finish)
      };
    });
    const totalMinutes = running;
    const totalDays = items[items.length - 1].day;
    return {
      adapter: ADAPTER, formula_version: 1,
      daily_minutes: daily, start_date: iso(start), items,
      total_minutes: totalMinutes, total_days: totalDays,
      // Whatever is still free in the reading budget on the last day.
      leftover_minutes: totalDays * daily - totalMinutes,
      finish_date: items[items.length - 1].finish_date
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return readingBacklog(input);
  }

  function cell(value) {
    let text = String(value);
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["day", "item", "minutes", "cumulative", "finish_date", "total_minutes", "total_days", "leftover"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.item, labels.minutes, labels.cumulative, labels.day, labels.finish_date],
      ...result.items.map((item) => [item.name, String(item.minutes), String(item.cumulative_min),
        String(item.day), item.finish_date]),
      [labels.total_minutes, String(result.total_minutes), "", "", ""],
      [labels.total_days, String(result.total_days), "", "", result.finish_date],
      [labels.leftover, String(result.leftover_minutes), "", "", ""]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_ITEMS, MIN_MINUTES, MAX_MINUTES, MIN_DAILY, MAX_DAILY,
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
