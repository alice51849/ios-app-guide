(() => {
  'use strict';
  const locales = new Set(['ar-SA','bn-BD','ca','zh-Hans','zh-Hant','hr','cs','da','nl-NL','en-AU','en-CA','en-GB','en-US','fi','fr-CA','fr-FR','de-DE','el','gu-IN','he','hi','hu','id','it','ja','kn-IN','ko','ms','ml-IN','mr-IN','no','or-IN','pl','pt-BR','pt-PT','pa-IN','ro','ru','sk','sl-SI','es-MX','es-ES','sv','ta-IN','te-IN','th','tr','uk','ur-PK','vi']);
  const fields = ['home','support','privacy','title','hero','formatsTitle','formatsText','verifyTitle','verifyText','batchTitle','batchText','supportTitle','supportIntro','step1','step2','step3','faqTitle','faqText','contactTitle','contactText','privacyTitle','privacyIntro','deviceTitle','deviceText','faceTitle','faceText','storeTitle','storeText','retentionTitle','retentionText'];
  const app = document.getElementById('app');
  const requested = new URLSearchParams(location.search).get('lang') || 'en-US';
  const rtl = new Set(['ar-SA','he','ur-PK']);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function failure(code) {
    document.documentElement.lang = locales.has(requested) ? requested : 'en-US';
    document.documentElement.dir = rtl.has(requested) ? 'rtl' : 'ltr';
    app.innerHTML = `<div class="mark">M</div><p class="lead">Mask My File · ${escape(requested)} · ${code}</p>`;
  }
  function nav(d) {
    return `<nav><a href="index.html?lang=${encodeURIComponent(requested)}">${escape(d.home)}</a><a href="support.html?lang=${encodeURIComponent(requested)}">${escape(d.support)}</a><a href="privacy.html?lang=${encodeURIComponent(requested)}">${escape(d.privacy)}</a></nav>`;
  }
  function card(title, text) { return `<article class="card"><b>${escape(title)}</b><p>${escape(text)}</p></article>`; }
  function render(d) {
    if (!fields.every(key => typeof d[key] === 'string' && d[key].trim())) return failure('0xMMF-DATA');
    document.documentElement.lang = requested;
    document.documentElement.dir = rtl.has(requested) ? 'rtl' : 'ltr';
    document.title = d.title;
    const page = app.dataset.page;
    if (page === 'index') app.innerHTML = `<div class="mark">M</div><h1>${escape(d.title)}</h1><p class="lead">${escape(d.hero)}</p><a class="store" href="https://apps.apple.com/app/id6792850916">Mask My File · App Store</a><section class="grid">${card(d.formatsTitle,d.formatsText)}${card(d.verifyTitle,d.verifyText)}${card(d.batchTitle,d.batchText)}</section>${nav(d)}`;
    else if (page === 'support') app.innerHTML = `<div class="mark">M</div><h1>${escape(d.supportTitle)}</h1><p class="lead">${escape(d.supportIntro)}</p><section class="grid">${card('1',d.step1)}${card('2',d.step2)}${card('3',d.step3)}</section><details open><summary>${escape(d.faqTitle)}</summary><p>${escape(d.faqText)}</p></details><details><summary>${escape(d.contactTitle)}</summary><p>${escape(d.contactText)}</p></details>${nav(d)}`;
    else if (page === 'privacy') app.innerHTML = `<div class="mark">M</div><h1>${escape(d.privacyTitle)}</h1><p class="lead">${escape(d.privacyIntro)}</p><section class="grid">${card(d.deviceTitle,d.deviceText)}${card(d.faceTitle,d.faceText)}${card(d.storeTitle,d.storeText)}</section><details open><summary>${escape(d.retentionTitle)}</summary><p>${escape(d.retentionText)}</p></details>${nav(d)}`;
    else failure('0xMMF-PAGE');
  }
  if (!locales.has(requested)) return failure('0xMMF-LOCALE');
  fetch(`locales/${encodeURIComponent(requested)}.json`, {credentials:'same-origin'})
    .then(response => response.ok ? response.json() : Promise.reject(response.status))
    .then(render)
    .catch(() => failure('0xMMF-LOAD'));
})();
