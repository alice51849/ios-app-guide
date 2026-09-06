"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_ITEMS = 10;
  const MIN_CAPACITY = 60;
  const MAX_CAPACITY = 100;
  const MAX_CYCLES = 3000;
  const MAX_AGE_MONTHS = 240;
  const MIN_YEAR = 2007;
  const MAX_YEAR = 2099;
  const BAND = 0.25;              // honest ±25 % band around the observed average
  const TARGET_CAPACITY = 80;     // Apple's service threshold for "significantly degraded"
  const ADAPTER = "battery-wear-range-v1";
  const CONTROL = /[\u0000-\u001f\u007f]/;

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Strict YYYY-MM only: the sheet never guesses a day or a time zone.
  function calendarMonth(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}$/.test(value)) {
      throw new TypeError("Use a YYYY-MM month.");
    }
    const year = Number(value.slice(0, 4));
    const month = Number(value.slice(5, 7));
    if (year < MIN_YEAR || year > MAX_YEAR || month < 1 || month > 12) {
      throw new RangeError("Month is outside the supported range.");
    }
    return year * 12 + (month - 1);
  }

  function wholeNumber(value, minimum, maximum, message) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,3})$/.test(value)) throw new TypeError(message);
    const number = Number(value);
    if (number < minimum || number > maximum) throw new RangeError(message);
    return number;
  }

  function twoDecimals(value) {
    return Math.round(value * 100) / 100;
  }

  function batteryWear(input) {
    objectWithKeys(input, ["today", "items"]);
    const today = calendarMonth(input.today);
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_ITEMS) {
      throw new RangeError("Provide between one and ten devices.");
    }
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "purchase_month", "max_capacity_pct", "cycle_count"]);
      if (typeof item.name !== "string" || !item.name.trim() || item.name.length > 120 || CONTROL.test(item.name)) {
        throw new TypeError("Provide a short, single-line device name.");
      }
      const purchased = calendarMonth(item.purchase_month);
      const ageMonths = today - purchased;
      if (ageMonths < 1 || ageMonths > MAX_AGE_MONTHS) {
        throw new RangeError("The device must be between one month and twenty years old.");
      }
      const capacity = wholeNumber(item.max_capacity_pct, MIN_CAPACITY, MAX_CAPACITY,
        "Maximum capacity is a whole percentage from 60 to 100.");
      let cycles = null;
      if (typeof item.cycle_count !== "string") throw new TypeError("Cycle count must be text.");
      if (item.cycle_count.trim() !== "") {
        cycles = wholeNumber(item.cycle_count, 0, MAX_CYCLES, "Cycle count is a whole number from 0 to 3000.");
      }
      const lost = MAX_CAPACITY - capacity;
      const remaining = capacity - TARGET_CAPACITY;
      // Everything below is an estimate from two numbers the person typed in.
      // A single observed average cannot justify one exact figure, so the sheet
      // only reports a band and never a score.
      const average = lost / ageMonths;
      const wearLow = twoDecimals(average * (1 - BAND));
      const wearHigh = twoDecimals(average * (1 + BAND));
      let status = "estimated";
      let monthsLow = null;
      let monthsHigh = null;
      if (lost === 0) {
        status = "no_wear_yet";
      } else if (remaining <= 0) {
        status = "at_or_below_80";
        monthsLow = 0;
        monthsHigh = 0;
      } else {
        monthsLow = Math.floor(remaining / (average * (1 + BAND)));
        monthsHigh = Math.ceil(remaining / (average * (1 - BAND)));
      }
      return {
        index,
        name: item.name.trim(),
        purchase_month: item.purchase_month,
        max_capacity_pct: capacity,
        cycle_count: cycles,
        age_months: ageMonths,
        wear_low: wearLow,
        wear_high: wearHigh,
        months_to_80_low: monthsLow,
        months_to_80_high: monthsHigh,
        cycles_per_month: cycles === null ? null : Math.round(cycles / ageMonths * 10) / 10,
        status
      };
    });
    // The summary repeats the same labelled values: a device count, the lowest
    // capacity the person typed in, and the soonest 80% band. A device already at
    // or below 80% makes "soonest" a fact, not an estimate; no wear yet stays open.
    const estimated = items.filter((item) => item.status === "estimated");
    const soonest = estimated.length === 0 ? null : estimated.reduce((best, item) =>
      item.months_to_80_low < best.months_to_80_low ||
      (item.months_to_80_low === best.months_to_80_low && item.months_to_80_high < best.months_to_80_high) ? item : best);
    const summary = {
      devices: items.length,
      min_capacity_pct: Math.min(...items.map((item) => item.max_capacity_pct)),
      soonest_status: items.some((item) => item.status === "at_or_below_80") ? "at_or_below_80"
        : soonest ? "estimated" : "no_wear_yet",
      soonest_low: soonest ? soonest.months_to_80_low : null,
      soonest_high: soonest ? soonest.months_to_80_high : null
    };
    return {adapter: ADAPTER, formula_version: 1, today: input.today, band: BAND, target_capacity: TARGET_CAPACITY, items, summary};
  }

  function soonestText(labels, summary) {
    if (summary.soonest_status === "at_or_below_80") return labels.at_or_below_80;
    if (summary.soonest_status === "no_wear_yet") return labels.no_wear_yet;
    return null;
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return batteryWear(input);
  }

  function fixed(value) {
    return value.toFixed(2);
  }

  function cell(value) {
    let text = String(value);
    // Quoting alone does not stop spreadsheet formula execution; plain numbers stay numeric.
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function monthsText(labels, item) {
    if (item.status === "no_wear_yet") return labels.no_wear_yet;
    if (item.status === "at_or_below_80") return labels.at_or_below_80;
    return null;
  }

  function marker(labels, item) {
    const provided = [labels.purchase_month, labels.capacity];
    if (item.cycle_count !== null) provided.push(labels.cycles);
    const estimated = [labels.age, labels.wear_rate, labels.months_to_80];
    return labels.marker_provided + ": " + provided.join(", ") + "; " +
      labels.marker_estimated + ": " + estimated.join(", ");
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["item", "purchase_month", "capacity", "cycles", "age", "wear_rate", "months_to_80", "low", "high",
      "source_marker", "marker_provided", "marker_estimated", "no_wear_yet", "at_or_below_80", "today"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const header = [labels.item, labels.purchase_month, labels.capacity, labels.cycles, labels.age,
      labels.wear_rate + " (" + labels.low + ")", labels.wear_rate + " (" + labels.high + ")",
      labels.months_to_80 + " (" + labels.low + ")", labels.months_to_80 + " (" + labels.high + ")", labels.source_marker];
    const rows = [
      header,
      ...result.items.map((item) => {
        const text = monthsText(labels, item);
        return [item.name, item.purchase_month, item.max_capacity_pct,
          item.cycle_count === null ? "" : item.cycle_count, item.age_months,
          fixed(item.wear_low), fixed(item.wear_high),
          text === null ? item.months_to_80_low : text, text === null ? item.months_to_80_high : text,
          marker(labels, item)];
      }),
      [labels.today, result.today, "", "", "", "", "", "", "", ""]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_ITEMS, MIN_CAPACITY, MAX_CAPACITY, MAX_CYCLES, MAX_AGE_MONTHS, BAND, TARGET_CAPACITY,
    adapters: Object.freeze([ADAPTER]), run, csv, marker, monthsText, soonestText
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
