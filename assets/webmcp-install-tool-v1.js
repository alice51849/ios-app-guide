(() => {
  "use strict";
  const script = document.currentScript;
  const dataId = script?.dataset.webmcpInstall;
  const node = dataId ? document.getElementById(dataId) : null;
  if (!node || !document.modelContext?.registerTool) return;
  let data;
  try {
    data = JSON.parse(node.textContent);
    const store = new URL(data.app_store_url);
    const facts = data.storefront_facts;
    if (
      store.protocol !== "https:" ||
      store.hostname !== "apps.apple.com" ||
      !/^\/(?:[a-z]{2}\/)?app\/id[0-9]{9,12}$/i.test(store.pathname) ||
      store.search ||
      store.hash ||
      !/^[0-9]{9,12}$/.test(data.app_store_id)
    ) throw new TypeError("Invalid verified App Store payload.");
    if (
      facts !== undefined &&
      (
        facts === null ||
        typeof facts !== "object" ||
        Array.isArray(facts) ||
        typeof facts.price !== "string" ||
        !/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(facts.price) ||
        typeof facts.currency !== "string" ||
        !/^[A-Z]{3}$/.test(facts.currency) ||
        typeof facts.formatted_price !== "string" ||
        !facts.formatted_price ||
        (
          (facts.rating_value === undefined) !==
          (facts.rating_count === undefined)
        ) ||
        (
          facts.rating_value !== undefined &&
          (
            typeof facts.rating_value !== "number" ||
            facts.rating_value < 0 ||
            facts.rating_value > 5 ||
            !Number.isInteger(facts.rating_count) ||
            facts.rating_count <= 0
          )
        )
      )
    ) throw new TypeError("Invalid verified App Store facts.");
  } catch (error) {
    console.error("WebMCP install data is invalid.", error);
    return;
  }
  const emptyInput = {
    type: "object",
    additionalProperties: false,
    properties: {}
  };
  function validateInput(input) {
    if (
      input === null ||
      typeof input !== "object" ||
      Array.isArray(input) ||
      Object.keys(input).length
    ) throw new TypeError("This tool does not accept input fields.");
  }
  const result = {
    result_type: "verified_ios_app_install_link",
    app_store_id: data.app_store_id,
    app_name: data.app_name,
    page_language: data.page_language,
    page_url: data.page_url,
    app_store_url: data.app_store_url,
    availability_source: "Apple public storefront lookup snapshot"
  };
  if (data.storefront_facts) {
    result.storefront_facts = data.storefront_facts;
  }
  async function register() {
    await document.modelContext.registerTool({
      name: "get_verified_ios_app_install_link",
      description:
        `Return the verified direct App Store link for ${data.app_name}. ` +
        data.localized_description,
      inputSchema: emptyInput,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input = {}) => {
        validateInput(input);
        return {
          content: [{type: "text", text: JSON.stringify(result)}]
        };
      }
    });
    await document.modelContext.registerTool({
      name: "open_verified_ios_app_store_listing",
      description:
        `Open the verified App Store listing for ${data.app_name}. ` +
        data.localized_description,
      inputSchema: emptyInput,
      annotations: {readOnlyHint: false, untrustedContentHint: false},
      execute: async (input = {}) => {
        validateInput(input);
        window.location.assign(data.app_store_url);
        return null;
      }
    });
  }
  register().catch(error =>
    console.error("WebMCP install tool registration failed.", error)
  );
})();
