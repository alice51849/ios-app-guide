"use strict";

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.HeroTaskCore = factory();
})(typeof globalThis === "object" ? globalThis : this, function () {
  const MAX_ROWS = 20;
  const MAX_DEVICES = 50;
  const MIN_PLAN_TENTHS = 5;        // 0.5 Mbps
  const MAX_PLAN_TENTHS = 100000;   // 10000 Mbps
  const TIGHT_RATIO = 0.2;          // less than 20 % headroom is "tight"
  const ADAPTER = "bandwidth-need-v1";
  // Approximate per-device planning figures in tenths of a megabit per second,
  // taken from the providers' own published guidance (Netflix, Zoom, console
  // makers, FCC broadband speed guide). Planning figures, never measurements.
  const ACTIVITIES = Object.freeze({
    sd_stream: Object.freeze({down: 30, up: 5}),
    hd_stream: Object.freeze({down: 50, up: 5}),
    uhd_stream: Object.freeze({down: 150, up: 5}),
    video_call: Object.freeze({down: 30, up: 30}),
    gaming: Object.freeze({down: 30, up: 10}),
    cloud_backup: Object.freeze({down: 10, up: 50}),
    browsing: Object.freeze({down: 10, up: 5}),
    smart_home: Object.freeze({down: 5, up: 5})
  });
  const ACTIVITY_KEYS = Object.freeze(Object.keys(ACTIVITIES));
  const CONTROL = /[\u0000-\u001f\u007f]/;

  function objectWithKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length ||
        keys.some((key) => !Object.prototype.hasOwnProperty.call(value, key))) {
      throw new TypeError("Unexpected input shape.");
    }
  }

  // Plan speeds are decimal strings with at most one fractional digit and become
  // integer tenths of a Mbps, so sums never accumulate floating-point error.
  function tenths(value) {
    if (typeof value !== "string" || !/^(0|[1-9]\d{0,4})(\.\d)?$/.test(value)) {
      throw new TypeError("Use a speed in Mbps with at most one decimal.");
    }
    const parts = value.split(".");
    const result = Number(parts[0]) * 10 + Number(parts[1] || "0");
    if (result < MIN_PLAN_TENTHS || result > MAX_PLAN_TENTHS) {
      throw new RangeError("Plan speed must be between 0.5 and 10000 Mbps.");
    }
    return result;
  }

  function devices(value) {
    if (typeof value !== "string" || !/^[1-9]\d?$/.test(value)) throw new TypeError("Use a whole number of devices.");
    const number = Number(value);
    if (number < 1 || number > MAX_DEVICES) throw new RangeError("Devices must be between 1 and 50.");
    return number;
  }

  function shortText(value, message) {
    if (typeof value !== "string" || !value.trim() || value.length > 120 || CONTROL.test(value)) {
      throw new TypeError(message);
    }
    return value.trim();
  }

  function status(headroom, plan) {
    if (headroom < 0) return "short";
    if (headroom < plan * TIGHT_RATIO) return "tight";
    return "ok";
  }

  function bandwidthNeed(input) {
    objectWithKeys(input, ["plan_down_mbps", "plan_up_mbps", "items"]);
    const planDown = tenths(input.plan_down_mbps);
    const planUp = tenths(input.plan_up_mbps);
    if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > MAX_ROWS) {
      throw new RangeError("Provide between one and twenty rows.");
    }
    const items = input.items.map((item, index) => {
      objectWithKeys(item, ["name", "activity", "devices"]);
      if (!ACTIVITY_KEYS.includes(item.activity)) throw new RangeError("Choose a listed activity.");
      const count = devices(item.devices);
      const per = ACTIVITIES[item.activity];
      return {
        index, name: shortText(item.name, "Provide a short, single-line row name."),
        activity: item.activity, devices: count,
        per_device_down_tenths: per.down, per_device_up_tenths: per.up,
        total_down_tenths: per.down * count, total_up_tenths: per.up * count
      };
    });
    const needDown = items.reduce((sum, item) => sum + item.total_down_tenths, 0);
    const needUp = items.reduce((sum, item) => sum + item.total_up_tenths, 0);
    const headroomDown = planDown - needDown;
    const headroomUp = planUp - needUp;
    const down = status(headroomDown, planDown);
    const up = status(headroomUp, planUp);
    const order = {short: 0, tight: 1, ok: 2};
    return {
      adapter: ADAPTER, formula_version: 1,
      plan_down_tenths: planDown, plan_up_tenths: planUp, items,
      need_down_tenths: needDown, need_up_tenths: needUp,
      headroom_down_tenths: headroomDown, headroom_up_tenths: headroomUp,
      status_down: down, status_up: up,
      status: order[down] <= order[up] ? down : up
    };
  }

  function run(adapter, input) {
    if (adapter !== ADAPTER) throw new RangeError("No reviewed adapter for this task.");
    return bandwidthNeed(input);
  }

  function mbps(tenthsValue) {
    const negative = tenthsValue < 0;
    const absolute = Math.abs(tenthsValue);
    const text = String(Math.floor(absolute / 10)) + "." + String(absolute % 10);
    return negative ? "-" + text : text;
  }

  function cell(value) {
    let text = String(value);
    // Quoting alone does not stop spreadsheet formula execution; a plain signed
    // decimal is a number, not a formula, so negative headroom stays numeric.
    if (/^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]*[=+\-@]/.test(text) && !/^-?\d+(\.\d+)?%?$/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csv(adapter, input, labels) {
    const result = run(adapter, input);
    const keys = ["item", "activity", "devices", "per_device_down", "per_device_up", "total_down", "total_up",
      "plan_down", "plan_up", "need_down", "need_up", "headroom", "status", "status_ok", "status_tight", "status_short",
      ...ACTIVITY_KEYS.map((key) => "activity_" + key)];
    for (const key of keys) {
      if (!labels || typeof labels[key] !== "string" || !labels[key].trim()) {
        throw new TypeError("Missing localized CSV header.");
      }
    }
    const rows = [
      [labels.item, labels.activity, labels.devices, labels.per_device_down, labels.per_device_up, labels.total_down, labels.total_up],
      ...result.items.map((item) => [item.name, labels["activity_" + item.activity], String(item.devices),
        mbps(item.per_device_down_tenths), mbps(item.per_device_up_tenths), mbps(item.total_down_tenths), mbps(item.total_up_tenths)]),
      [labels.need_down, "", "", "", "", mbps(result.need_down_tenths), ""],
      [labels.need_up, "", "", "", "", "", mbps(result.need_up_tenths)],
      [labels.plan_down, "", "", "", "", mbps(result.plan_down_tenths), ""],
      [labels.plan_up, "", "", "", "", "", mbps(result.plan_up_tenths)],
      [labels.headroom, "", "", "", "", mbps(result.headroom_down_tenths), mbps(result.headroom_up_tenths)],
      [labels.status, "", "", "", "", labels["status_" + result.status_down], labels["status_" + result.status_up]]
    ];
    return "\ufeff" + rows.map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  return Object.freeze({
    MAX_ROWS, MAX_DEVICES, ACTIVITIES, ACTIVITY_KEYS, adapters: Object.freeze([ADAPTER]), run, csv, mbps
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
