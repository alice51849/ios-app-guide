// Executed inside Chromium by the regression runner. No external state.
export function measureOutreachPage(options = {}) {
  const epsilon = 1;
  const rounded = value => Math.round(value * 1000) / 1000;
  const box = rect => ({
    left: rounded(rect.left), top: rounded(rect.top),
    right: rounded(rect.right), bottom: rounded(rect.bottom),
    width: rounded(rect.width), height: rounded(rect.height),
  });
  const styles = new Map();
  const boxes = new Map();
  const style = element => {
    if (!styles.has(element)) styles.set(element, getComputedStyle(element));
    return styles.get(element);
  };
  const rect = element => {
    if (!boxes.has(element)) boxes.set(element, element.getBoundingClientRect());
    return boxes.get(element);
  };
  const visible = element => {
    if (element.closest("[hidden],script,style,pre,code,textarea,svg")) return false;
    const bounds = rect(element);
    if (bounds.width <= 0 || bounds.height <= 0) return false;
    for (let parent = element; parent; parent = parent.parentElement) {
      const css = style(parent);
      if (css.display === "none" || css.visibility === "hidden" || Number(css.opacity) === 0) return false;
    }
    return true;
  };
  const name = element => element.id ? `#${element.id}` :
    element.tagName.toLowerCase() + (typeof element.className === "string" && element.className ? "." + element.className.trim().split(/\s+/).join(".") : "");
  const paddingBox = element => {
    const bounds = rect(element), css = style(element);
    const sx = element.offsetWidth ? bounds.width / element.offsetWidth : 1;
    const sy = element.offsetHeight ? bounds.height / element.offsetHeight : 1;
    const left = bounds.left + (parseFloat(css.borderLeftWidth) || 0) * sx;
    const right = bounds.right - (parseFloat(css.borderRightWidth) || 0) * sx;
    const top = bounds.top + (parseFloat(css.borderTopWidth) || 0) * sy;
    const bottom = bounds.bottom - (parseFloat(css.borderBottomWidth) || 0) * sy;
    return { left, right, top, bottom };
  };
  const outside = (text, clip, axis) => axis === "x" ?
    text.left < clip.left - epsilon || text.right > clip.right + epsilon :
    text.top < clip.top - epsilon || text.bottom > clip.bottom + epsilon;
  const clippingAncestors = element => {
    const result = [];
    for (let parent = element; parent; parent = parent.parentElement) {
      const css = style(parent);
      const clip = paddingBox(parent);
      const documentRoot = parent === document.documentElement || parent === document.body;
      const x = /^(hidden|clip|auto|scroll)$/.test(css.overflowX);
      const y = /^(hidden|clip)$/.test(css.overflowY) ||
        (!documentRoot && /^(auto|scroll)$/.test(css.overflowY));
      const paint = /\b(paint|strict|content)\b/.test(css.contain);
      const clippedPath = css.clipPath !== "none";
      const legacyClip = css.clip !== "auto";
      let unsupported = false;
      if (clippedPath) {
        const inset = css.clipPath.match(/^inset\(([\d.\s%px-]+)(?: round .*)?\)$/);
        if (!inset) unsupported = true;
        else {
          const values = inset[1].trim().split(/\s+/);
          const four = values.length === 1 ? [values[0], values[0], values[0], values[0]] :
            values.length === 2 ? [values[0], values[1], values[0], values[1]] :
            values.length === 3 ? [values[0], values[1], values[2], values[1]] : values;
          const pixels = (value, length) => parseFloat(value) * (value.endsWith("%") ? length / 100 : 1);
          const bounds = rect(parent);
          clip.top += pixels(four[0], bounds.height);
          clip.right -= pixels(four[1], bounds.width);
          clip.bottom -= pixels(four[2], bounds.height);
          clip.left += pixels(four[3], bounds.width);
        }
      }
      if (legacyClip) {
        const match = css.clip.match(/^rect\(([^)]+)\)$/);
        if (!match) unsupported = true;
        else {
          const values = match[1].split(/,\s*|\s+/);
          const bounds = rect(parent);
          if (values[0] !== "auto") clip.top = bounds.top + parseFloat(values[0]);
          if (values[1] !== "auto") clip.right = bounds.left + parseFloat(values[1]);
          if (values[2] !== "auto") clip.bottom = bounds.top + parseFloat(values[2]);
          if (values[3] !== "auto") clip.left = bounds.left + parseFloat(values[3]);
        }
      }
      if (x || y || paint || clippedPath || legacyClip) {
        result.push({
          node: parent, selector: name(parent), clip,
          x: x || paint || clippedPath || legacyClip,
          y: y || paint || clippedPath || legacyClip,
          overflowX: css.overflowX, overflowY: css.overflowY,
          contain: css.contain, clipPath: css.clipPath, unsupported,
        });
      }
    }
    return result;
  };
  const scope = "h1,h2,h3,p,a,button,label,figcaption,summary,.eyebrow,.fact,.pill,.iag-decision-card__title,.iag-decision-card__fact,.iag-decision-card__storefront";
  const actionSelector = 'a[href*="apps.apple.com"],a.button,a.cta,.nav a,.ll a,button,[role="button"],summary,input[type="submit"],input[type="button"]';
  const groups = new Map();
  const canvas = document.createElement("canvas").getContext("2d");
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    const element = parent?.closest(scope);
    if (!element || !visible(parent) || !node.nodeValue.trim()) continue;
    const start = node.nodeValue.search(/\S/);
    const end = node.nodeValue.replace(/\s+$/u, "").length;
    if (end <= start) continue;
    const range = document.createRange();
    range.setStart(node, start);
    range.setEnd(node, end);
    const union = range.getBoundingClientRect();
    const fragments = [...range.getClientRects()].filter(part => part.width > 0.1 && part.height > 0.1);
    if (!fragments.length) continue;
    if (!groups.has(element)) groups.set(element, { fragments: [], ink: [], ranges: [], clips: [], opticalEnds: [] });
    const group = groups.get(element);
    group.fragments.push(...fragments);
    group.ranges.push(box(union));
    const fontStyle = style(parent);
    canvas.font = `${fontStyle.fontStyle} ${fontStyle.fontWeight} ${fontStyle.fontSize} ${fontStyle.fontFamily}`;
    canvas.letterSpacing = fontStyle.letterSpacing;
    const metrics = canvas.measureText(node.nodeValue.slice(start, end));
    if (![metrics.fontBoundingBoxAscent, metrics.actualBoundingBoxAscent, metrics.actualBoundingBoxDescent].every(Number.isFinite)) {
      throw new Error("Actual font ink metrics are unavailable");
    }
    // Range rectangles include unused font ascender/descender space. Use actual
    // ink metrics for overlap; keep unmodified Range rectangles for clipping.
    group.ink.push(...fragments.map(part => ({
      left: part.left, right: part.right, width: part.width,
      top: part.top + metrics.fontBoundingBoxAscent - metrics.actualBoundingBoxAscent,
      bottom: part.top + metrics.fontBoundingBoxAscent + metrics.actualBoundingBoxDescent,
      height: metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent,
    })));
    const finalCharacter = node.nodeValue.slice(end - 1, end);
    if (/^(zh|ja)(-|$)/.test(document.documentElement.lang) &&
        /[，。、；：！？）】」』〕〉》]/u.test(finalCharacter) &&
        fontStyle.direction === "ltr") {
      const ending = document.createRange();
      ending.setStart(node, end - 1);
      ending.setEnd(node, end);
      const glyph = canvas.measureText(finalCharacter);
      for (const bounds of ending.getClientRects()) {
        group.opticalEnds.push({
          left: bounds.left, right: bounds.right, top: bounds.top, bottom: bounds.bottom,
          inkRight: bounds.left + glyph.actualBoundingBoxRight,
        });
      }
    }
    for (const ancestor of clippingAncestors(parent)) {
      if (ancestor.unsupported || fragments.some(part =>
        (ancestor.x && outside(part, ancestor.clip, "x")) ||
        (ancestor.y && outside(part, ancestor.clip, "y")))) {
        group.clips.push({
          ancestor: ancestor.selector, box: ancestor.clip,
          overflowX: ancestor.overflowX, overflowY: ancestor.overflowY,
          contain: ancestor.contain, clipPath: ancestor.clipPath,
          unsupported: ancestor.unsupported,
          text: node.nodeValue.trim().slice(0, 160),
        });
      }
    }
  }
  const failures = [];
  const controls = [];
  const cjkTokenOverflows = [];
  let opticalPunctuationEnds = 0;
  let legacyAppleClips = 0;
  const requestedWidth = options.width ?? innerWidth;
  for (const [element, group] of groups) {
    const bounds = rect(element), css = style(element);
    const apple = element.matches('a[href*="apps.apple.com"]');
    const own = paddingBox(element);
    const ownX = group.fragments.some(part => {
      if (!outside(part, own, "x")) return false;
      // CJK closing punctuation can hang its unused advance beyond a line.
      // Exempt only a measured final glyph whose ink remains inside; actual
      // clipping ancestors and viewport bounds are still checked separately.
      const optical = part.left >= own.left - epsilon && group.opticalEnds.some(end =>
        Math.abs(end.right - part.right) < 0.5 && Math.abs(end.top - part.top) < 0.5 &&
        end.left <= own.right && end.inkRight <= own.right + epsilon);
      if (optical) opticalPunctuationEnds++;
      return !optical;
    });
    const viewportX = group.fragments.some(part => part.left < -epsilon || part.right > requestedWidth + epsilon);
    let lineOverlap = false;
    for (let i = 0; i < group.ink.length && !lineOverlap; i++) {
      for (let j = i + 1; j < group.ink.length; j++) {
        const a = group.ink[i], b = group.ink[j];
        const separateLines = Math.abs(group.fragments[i].top - group.fragments[j].top) > 0.5;
        if (separateLines && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > epsilon &&
            Math.min(a.right, b.right) - Math.max(a.left, b.left) > epsilon) lineOverlap = true;
      }
    }
    if (apple && (group.clips.length || bounds.left < -2 || bounds.right > innerWidth + 2)) legacyAppleClips++;
    if (element.matches(".iag-decision-card__promise,.iag-decision-card__terms,.iag-decision-card__cta") &&
        element.scrollWidth > element.clientWidth + 2) cjkTokenOverflows.push(name(element));
    if (group.clips.length || ownX || viewportX || lineOverlap) {
      failures.push({
        selector: name(element), apple, text: element.textContent.trim().slice(0, 180),
        element: box(bounds), ranges: group.ranges, fragments: group.fragments.map(box), ink: group.ink.map(box),
        clips: group.clips, ownX, viewportX, lineOverlap,
        whiteSpace: css.whiteSpace, overflowX: css.overflowX, overflowY: css.overflowY,
        fontSize: css.fontSize, lineHeight: css.lineHeight, letterSpacing: css.letterSpacing,
      });
    }
  }
  for (const element of document.querySelectorAll(actionSelector)) {
    if (!visible(element)) continue;
    const bounds = rect(element);
    const small = bounds.width < 43.99 || bounds.height < 43.99;
    const css = style(element);
    const fragments = groups.get(element)?.fragments ?? [];
    const lineTops = [...new Set(fragments.map(fragment => Math.round(fragment.top * 2) / 2))];
    const record = { selector: name(element), href: element.getAttribute("href"), bounds: box(bounds), small,
      whiteSpace: css.whiteSpace, lineHeight: css.lineHeight, lines: lineTops.length,
      text: (element.textContent.trim() || element.getAttribute("aria-label") || "").slice(0, 100) };
    controls.push(record);
    if (small) failures.push({ selector: name(element), text: record.text, hitTarget: box(bounds), small: true });
  }
  const actionOverlaps = [];
  for (const element of document.querySelectorAll(".app-store-qr-card__url")) {
    if (!visible(element)) continue;
    if (element.scrollWidth > element.clientWidth + epsilon) {
      failures.push({ selector: name(element), pseudoContentOverflow: true,
        content: getComputedStyle(element, "::before").content,
        bounds: box(rect(element)), clientWidth: element.clientWidth, scrollWidth: element.scrollWidth });
    }
  }
  for (let i = 0; i < controls.length; i++) {
    for (let j = i + 1; j < controls.length; j++) {
      const a = controls[i], b = controls[j];
      if (Math.min(a.bounds.right, b.bounds.right) - Math.max(a.bounds.left, b.bounds.left) > epsilon &&
          Math.min(a.bounds.bottom, b.bounds.bottom) - Math.max(a.bounds.top, b.bounds.top) > epsilon) {
        actionOverlaps.push([a.selector, b.selector]);
      }
    }
  }
  const anchors = [...document.querySelectorAll("h1,.iag-decision-card,.iag-decision-card__icon,.iag-decision-card__cta,main")].
    filter(visible).map(element => ({ selector: name(element), bounds: box(rect(element)) }));
  return {
    width: innerWidth, requestedWidth, height: innerHeight, scrollX, scrollY,
    documentWidth: document.documentElement.scrollWidth,
    documentHeight: document.documentElement.scrollHeight,
    horizontalOverflow: document.documentElement.scrollWidth > requestedWidth + epsilon || innerWidth > requestedWidth + epsilon,
    fontStatus: document.fonts.status,
    fonts: [...document.fonts].map(face => ({ family: face.family, status: face.status })),
    lang: document.documentElement.lang, direction: style(document.body).direction,
    reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
    mobileScriptActive: Boolean(document.getElementById("mobile-store-cta-style")),
    mobileBarPresent: Boolean(document.querySelector("[data-mobile-store-cta]")),
    isolates: document.querySelectorAll('bdi[dir="ltr"]').length,
    legacyAppleClips,
    legacyCjkOverflow: document.documentElement.scrollWidth > innerWidth + 2 || cjkTokenOverflows.length > 0,
    cjkTokenOverflows,
    opticalPunctuationEnds,
    failures, controls, actionOverlaps, anchors,
  };
}
