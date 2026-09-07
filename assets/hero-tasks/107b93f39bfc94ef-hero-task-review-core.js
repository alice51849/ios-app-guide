"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_NOTES = 20;
  const MIN_YEAR = 2000;
  const MAX_YEAR = 2099;
  const DAY_MS = 86400000;
  const ADAPTER = "review-schedule-v1";
  // A fixed expanding interval ladder in days. It is a plain schedule, not a
  // memory model: nothing here predicts or scores what anyone will remember.
  const INTERVALS = Object.freeze([1, 3, 7, 16, 35]);
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

  function shortText(value, message) {
    if (typeof value !== "string" || !value.trim() || value.length > 120 || CONTROL.test(value)) {
      throw new TypeError(message);
    }
    return value.trim();
  }

  function reviewSchedule(input) {
    objectWithKeys(input, ["today", "items"]);
    const today = calendarDate(input.today);
    const limit = calendarDate(MAX_YEAR + "-12-31");
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_NOTES) {
      throw new RangeError("Provide between one and twenty notes.");
    }
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "studied_on"]);
      const name = shortText(item.name, "Provide a short, single-line note name.");
      const studied = calendarDate(item.studied_on);
      const reviews = INTERVALS.map((interval, position) => {
        const when = studied + interval;
        if (when > limit) throw new RangeError("A review date falls outside the supported calendar range.");
        const daysLeft = when - today;
        return {
          step: position + 1, interval, date: iso(when), days_left: daysLeft,
          status: daysLeft > 0 ? "upcoming" : daysLeft === 0 ? "today" : "passed"
        };
      });
      const next = reviews.find((review) => review.days_left >= 0) || null;
      return {
        index, order: index + 1, name, studied_on: iso(studied), reviews,
        next_review: next ? next.date : null,
        next_days_left: next ? next.days_left : null,
        passed: reviews.filter((review) => review.status === "passed").length
      };
    });
    const upcoming = items
      .filter((item) => item.next_review)
      .map((item) => item.next_review)
      .sort();
    return {
      adapter: ADAPTER, formula_version: 1,
      today: iso(today), intervals: INTERVALS.slice(), items,
      note_count: items.length, review_count: items.length * INTERVALS.length,
      next_review: upcoming.length ? upcoming[0] : null,
      passed_count: items.reduce((sum, item) => sum + item.passed, 0)
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return reviewSchedule(input);
  }

  function cell(value) {
    let text = String(value);
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["note", "studied_on", "step", "review_date", "days_left", "status",
      "status_passed", "status_today", "status_upcoming", "note_count", "review_count", "next_review"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.note, labels.studied_on, labels.step, labels.review_date, labels.days_left, labels.status]
    ];
    for (const item of result.items) {
      for (const review of item.reviews) {
        rows.push([item.name, item.studied_on, String(review.step), review.date,
          String(review.days_left), labels["status_" + review.status]]);
      }
    }
    rows.push([labels.note_count, String(result.note_count), "", "", "", ""]);
    rows.push([labels.review_count, String(result.review_count), "", "", "", ""]);
    rows.push([labels.next_review, result.next_review || "", "", "", "", ""]);
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_NOTES, INTERVALS, adapters: Object.freeze([ADAPTER]), run, csv
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
