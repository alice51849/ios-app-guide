const supported = [
  "ar-SA", "bn-BD", "ca", "zh-Hans", "zh-Hant", "hr", "cs", "da", "nl-NL",
  "en-AU", "en-CA", "en-GB", "en-US", "fi", "fr-CA", "fr-FR", "de-DE", "el",
  "gu-IN", "he", "hi", "hu", "id", "it", "ja", "kn-IN", "ko", "ms", "ml-IN",
  "mr-IN", "no", "or-IN", "pl", "pt-BR", "pt-PT", "pa-IN", "ro", "ru", "sk",
  "sl-SI", "es-MX", "es-ES", "sv", "ta-IN", "te-IN", "th", "tr", "uk",
  "ur-PK", "vi"
];

function resolvedLocale(requested) {
  if (supported.includes(requested)) return requested;
  const base = requested?.split("-")[0];
  return supported.find((locale) => locale.split("-")[0] === base) || "en-US";
}

function localizedURL(path, locale) {
  return `${path}?lang=${encodeURIComponent(locale)}`;
}

async function render() {
  const queryLocale = new URLSearchParams(location.search).get("lang");
  const locale = resolvedLocale(queryLocale || navigator.language);
  const copy = await fetch("copy.json", { cache: "no-cache" }).then((response) => {
    if (!response.ok) throw new Error(`copy.json returned ${response.status}`);
    return response.json();
  });
  const content = copy[locale] || copy["en-US"];
  const page = document.body.dataset.page;
  const pageContent = content[page];

  document.documentElement.lang = locale;
  document.documentElement.dir = ["ar-SA", "he", "ur-PK"].includes(locale) ? "rtl" : "ltr";
  document.getElementById("page-title").textContent =
    page === "marketing" ? "AI BriefPack" : pageContent.title;
  document.getElementById("page-lead").textContent = pageContent.lead;

  const grid = document.getElementById("feature-grid");
  grid.replaceChildren(
    ...pageContent.cards.map(({ title, body }) => {
      const card = document.createElement("article");
      card.className = "card";
      const heading = document.createElement("h2");
      heading.textContent = title;
      const paragraph = document.createElement("p");
      paragraph.textContent = body;
      card.append(heading, paragraph);
      return card;
    })
  );

  const picker = document.getElementById("language-picker");
  const displayNames = new Intl.DisplayNames([locale], { type: "language" });
  for (const code of supported) {
    const option = document.createElement("option");
    option.value = code;
    option.textContent = displayNames.of(code) || code;
    option.selected = code === locale;
    picker.append(option);
  }
  picker.addEventListener("change", () => {
    location.href = localizedURL(location.pathname.split("/").pop() || "index.html", picker.value);
  });

  document.getElementById("home-link").href = localizedURL("index.html", locale);
  document.getElementById("support-link").href = localizedURL("support.html", locale);
  document.getElementById("support-link").textContent = content.supportLabel;
  document.getElementById("privacy-link").href = localizedURL("privacy.html", locale);
  document.getElementById("privacy-link").textContent = content.privacyLabel;
}

render().catch((error) => console.error("AI BriefPack localization failed", error));
