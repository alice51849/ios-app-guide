(() => {
  "use strict";

  const script = document.querySelector("script[data-app-store-share]");
  const appId = script && script.dataset.appStoreShare;
  const rawUrl = script && script.dataset.appStoreUrl;
  if (!appId || !/^\d+$/.test(appId) || !rawUrl) return;
  if (typeof navigator.share !== "function") return;

  let store;
  try {
    store = new URL(rawUrl);
    const path = store.pathname.match(
      /^\/(?:[a-z]{2}\/)?app\/id([0-9]{9,12})$/i
    );
    const parameters = [...store.searchParams.entries()];
    const campaign = Object.fromEntries(parameters);
    if (
      store.protocol !== "https:" ||
      store.hostname !== "apps.apple.com" ||
      store.username ||
      store.password ||
      store.port ||
      !path ||
      path[1] !== appId ||
      store.hash ||
      parameters.some(
        ([key], index) =>
          parameters.findIndex(([candidate]) => candidate === key) !== index
      ) ||
      (parameters.length !== 0 &&
        (parameters.length !== 3 ||
          parameters.map(([key]) => key).join(",") !== "pt,ct,mt" ||
          !/^[0-9]{1,20}$/.test(campaign.pt || "") ||
          !/^[A-Za-z0-9_]{1,30}$/.test(campaign.ct || "") ||
          campaign.mt !== "8"))
    ) throw new TypeError("Invalid direct App Store share URL.");
  } catch (error) {
    console.error("App Store share URL is invalid.", error);
    return;
  }
  const url = store.href;
  const payload = { url };
  if (
    typeof navigator.canShare === "function" &&
    !navigator.canShare(payload)
  ) return;

  const shareLabels = Object.freeze({"ar-sa":"مشاركة","bn-bd":"শেয়ার করুন","ca":"Comparteix","cs":"Sdílet","da":"Del","de-de":"Teilen","el":"Κοινοποίηση","en":"Share","es-es":"Compartir","es-mx":"Compartir","fi":"Jaa","fr-ca":"Partager","fr-fr":"Partager","gu-in":"શેર કરો","he":"שיתוף","hi":"साझा करें","hr":"Podijeli","hu":"Megosztás","id":"Bagikan","it":"Condividi","ja":"共有","kn-in":"ಹಂಚಿಕೊಳ್ಳಿ","ko":"공유","ml-in":"പങ്കിടുക","mr-in":"शेअर करा","ms":"Kongsi","nl-nl":"Delen","no":"Del","or-in":"ସେୟାର କରନ୍ତୁ","pa-in":"ਸਾਂਝਾ ਕਰੋ","pl":"Udostępnij","pt-br":"Compartilhar","pt-pt":"Partilhar","ro":"Distribuie","ru":"Поделиться","sk":"Zdieľať","sl-si":"Deli","sv":"Dela","ta-in":"பகிர்","te-in":"షేర్ చేయండి","th":"แชร์","tr":"Paylaş","uk":"Поділитися","ur-pk":"شیئر کریں","vi":"Chia sẻ","zh-hans":"分享","zh-hant":"分享"});
  const language = (document.documentElement.lang || "en").toLowerCase();
  const label = shareLabels[language] || shareLabels.en;

  if (!document.getElementById("app-store-share-style")) {
    const style = document.createElement("style");
    style.id = "app-store-share-style";
    style.textContent = `
.app-store-share-button{appearance:none;-webkit-appearance:none;display:inline-grid;place-items:center;flex:0 0 48px;inline-size:48px;block-size:48px;min-inline-size:48px;margin:0;padding:0;border:1px solid rgba(79,85,232,.2);border-radius:14px;color:#4f55e8;background:rgba(79,85,232,.08);font:inherit;line-height:1;white-space:nowrap;cursor:pointer;touch-action:manipulation;-webkit-tap-highlight-color:transparent;transition:background-color .18s ease,transform .18s ease}
.app-store-share-button svg{inline-size:23px;block-size:23px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round;pointer-events:none}
.app-store-share-button:focus-visible{outline:3px solid #4f55e8;outline-offset:3px}
.mobile-store-cta .mobile-store-cta__link{flex:1 1 auto;width:auto;min-width:0}
.mobile-store-cta>.app-store-share-button{margin-inline-start:6px;color:#fff;background:linear-gradient(135deg,#7378ee,#946ee1);border-color:rgba(255,255,255,.55);box-shadow:0 7px 18px rgba(79,85,232,.2)}
.app-store-qr-card>.app-store-share-button{align-self:center;margin-inline-start:.75rem}
@media(hover:hover){.app-store-share-button:hover{background:rgba(79,85,232,.15);transform:translateY(-1px)}.mobile-store-cta>.app-store-share-button:hover{background:linear-gradient(135deg,#686ee9,#895fdc)}}
@media print{.app-store-share-button{display:none!important}}
@media(prefers-reduced-motion:reduce){.app-store-share-button{transition:none}}
`;
    document.head.appendChild(style);
  }

  const icon = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
  <path d="M12 15V3m0 0L7.5 7.5M12 3l4.5 4.5"></path>
  <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"></path>
</svg>`;

  const addButton = (container, modifier) => {
    if (!container || container.querySelector(".app-store-share-button")) {
      return null;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = `app-store-share-button ${modifier}`;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.dataset.appStoreUrl = url;
    button.innerHTML = icon;
    button.addEventListener("click", async () => {
      try {
        await navigator.share(payload);
      } catch (error) {
        if (!error || error.name !== "AbortError") {
          console.error("App Store share failed", error);
        }
      }
    });
    container.appendChild(button);
    return button;
  };

  const mobileBar = document.querySelector("[data-mobile-store-cta]");
  const mobileButton = addButton(mobileBar, "app-store-share-button--mobile");
  if (mobileButton) {
    const syncTabOrder = () => {
      mobileButton.tabIndex = mobileBar.classList.contains("is-visible") ? 0 : -1;
    };
    new MutationObserver(syncTabOrder).observe(mobileBar, {
      attributes: true,
      attributeFilter: ["class"],
    });
    syncTabOrder();
  }

  addButton(
    document.querySelector(".app-store-qr-card"),
    "app-store-share-button--desktop"
  );
})();
