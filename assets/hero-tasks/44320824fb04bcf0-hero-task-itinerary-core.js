"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_STOPS = 25;
  const MIN_STAY = 5;
  const MAX_STAY = 720;
  const MAX_TRAVEL = 600;
  const DAY = 24 * 60;
  const ADAPTER = "day-itinerary-v1";
  const CONTROL = /[\u0000-\u001f\u007f]/;

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Clock times are plain HH:MM strings; there is no time zone and no date.
  function clockMinutes(value) {
    if (typeof value !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(value)) {
      throw new TypeError("Use a 24-hour HH:MM time.");
    }
    return Number(value.slice(0, 2)) * 60 + Number(value.slice(3, 5));
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

  function dayItinerary(input) {
    objectWithKeys(input, ["start_time", "end_time", "items"]);
    const start = clockMinutes(input.start_time);
    const end = clockMinutes(input.end_time);
    // An end time at or before the start means the window crosses midnight;
    // identical times would be a zero window, which is refused.
    if (start === end) throw new RangeError("The day window must be longer than zero minutes.");
    const available = end > start ? end - start : end + DAY - start;
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_STOPS) {
      throw new RangeError("Provide between one and twenty-five stops.");
    }
    let clock = start;
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "stay_min", "travel_min"]);
      const name = shortText(item.name, "Provide a short, single-line place name.");
      const stay = wholeNumber(item.stay_min, MIN_STAY, MAX_STAY, "Stay must be a whole number of minutes from 5 to 720.");
      const travel = wholeNumber(item.travel_min, 0, MAX_TRAVEL, "Travel must be a whole number of minutes from 0 to 600.");
      const arrive = clock;
      const leave = arrive + stay;
      clock = leave + travel;
      return {index, order: index + 1, name, stay_min: stay, travel_min: travel, arrive_min: arrive, leave_min: leave};
    });
    const total = clock - start;
    const overrun = total - available;
    return {
      adapter: ADAPTER, formula_version: 1,
      start_min: start, end_min: end, available_min: available, items,
      total_min: total, overrun_min: overrun, status: overrun > 0 ? "overrun" : "fits"
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return dayItinerary(input);
  }

  // Minutes from the start of the day; anything past midnight is shown with a
  // "+1" day marker instead of silently wrapping.
  function clockText(minutes) {
    const days = Math.floor(minutes / DAY);
    const rest = minutes - days * DAY;
    const text = String(Math.floor(rest / 60)).padStart(2, "0") + ":" + String(rest % 60).padStart(2, "0");
    return days > 0 ? text + " +" + days : text;
  }

  function cell(value) {
    let text = String(value);
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["order", "place", "arrive", "leave", "stay", "travel", "total", "available", "overrun",
      "status", "status_fits", "status_overrun"];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.order, labels.place, labels.arrive, labels.leave, labels.stay, labels.travel],
      ...result.items.map((item) => [String(item.order), item.name, clockText(item.arrive_min), clockText(item.leave_min),
        String(item.stay_min), String(item.travel_min)]),
      [labels.total, "", "", "", String(result.total_min), ""],
      [labels.available, "", clockText(result.start_min), clockText(result.start_min + result.available_min), String(result.available_min), ""],
      [labels.overrun, "", "", "", String(result.overrun_min), ""],
      [labels.status, labels["status_" + result.status], "", "", "", ""]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_STOPS, MIN_STAY, MAX_STAY, MAX_TRAVEL, adapters: Object.freeze([ADAPTER]), run, csv, clockText
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
