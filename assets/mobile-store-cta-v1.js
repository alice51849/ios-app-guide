(() => {
  "use strict";

  const bar = document.querySelector("[data-mobile-store-cta]");
  if (!bar || !("IntersectionObserver" in window)) return;
  const link = bar.querySelector("a");
  const source =
    document.querySelector(
      '.hero a[href^="https://apps.apple.com/"][href*="/app/id"]'
    ) ||
    document.querySelector(
      'main a[href^="https://apps.apple.com/"][href*="/app/id"]'
    );
  if (!link || !source) return;

  if (!document.getElementById("mobile-store-cta-style")) {
    const style = document.createElement("style");
    style.id = "mobile-store-cta-style";
    style.textContent = `
.mobile-store-cta{position:fixed;z-index:2147483000;left:12px;left:max(12px,env(safe-area-inset-left));right:12px;right:max(12px,env(safe-area-inset-right));bottom:10px;bottom:max(10px,env(safe-area-inset-bottom));display:flex;box-sizing:border-box;padding:6px;border:1px solid rgba(255,255,255,.72);border-radius:20px;background:rgba(255,255,255,.9);box-shadow:0 14px 44px rgba(20,22,45,.2);-webkit-backdrop-filter:blur(18px) saturate(1.35);backdrop-filter:blur(18px) saturate(1.35);opacity:0;transform:translateY(calc(100% + 28px));pointer-events:none;transition:opacity .22s ease,transform .28s cubic-bezier(.22,1,.36,1)}
.mobile-store-cta.is-visible{opacity:1;transform:translateY(0);pointer-events:auto}
.mobile-store-cta__link{display:flex;align-items:center;justify-content:center;width:100%;min-height:48px;padding:0 18px;border-radius:14px;background:linear-gradient(135deg,#4f55e8,#8057d9);box-shadow:0 7px 18px rgba(79,85,232,.28);color:#fff!important;text-decoration:none;font-size:clamp(.82rem,3.5vw,1rem);font-weight:850;letter-spacing:-.01em;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;-webkit-tap-highlight-color:transparent}
.mobile-store-cta__link:focus-visible{outline:3px solid #fff;outline-offset:-5px}
@media(min-width:760px),print{.mobile-store-cta{display:none!important}}
@media(max-width:759px){body.mobile-store-cta-active{padding-bottom:calc(82px + env(safe-area-inset-bottom))}}
@media(prefers-reduced-motion:reduce){.mobile-store-cta{transition:none}}
`;
    document.head.appendChild(style);
  }

  let sourceVisible = true;
  let ticking = false;
  const update = () => {
    ticking = false;
    const threshold = Math.min(320, window.innerHeight * 0.4);
    const visible = window.scrollY >= threshold && !sourceVisible;
    bar.classList.toggle("is-visible", visible);
    bar.setAttribute("aria-hidden", String(!visible));
    link.tabIndex = visible ? 0 : -1;
    document.body.classList.toggle("mobile-store-cta-active", visible);
  };
  const requestUpdate = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  };

  bar.hidden = false;
  new IntersectionObserver(
    (entries) => {
      sourceVisible = entries[0].isIntersecting;
      requestUpdate();
    },
    { threshold: 0.01 }
  ).observe(source);
  window.addEventListener("scroll", requestUpdate, { passive: true });
  window.addEventListener("resize", requestUpdate, { passive: true });
  update();
})();
