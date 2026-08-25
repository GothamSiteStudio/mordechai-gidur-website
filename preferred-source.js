/*
 * Google preferred sources - the custom-button ("advanced JavaScript") integration.
 * https://developers.google.com/search/docs/appearance/preferred-sources
 *
 * The footer offers all three integrations Google documents:
 *   1. the button Google renders itself into [google-add-preferred-source-btn]
 *   2. the custom button below, wired to the JS API by this file
 *   3. a plain deeplink to the Google Search source settings
 *
 * If Google library cannot load, the custom button falls back to the deeplink.
 */
(function () {
  var buttons = document.querySelectorAll(".js-preferred-source");
  if (!buttons.length) return;

  var lang = document.documentElement.getAttribute("lang") || "en";

  function fallback() {
    Array.prototype.forEach.call(buttons, function (button) {
      button.addEventListener("click", function () {
        var url = button.getAttribute("data-preferred-source-url");
        if (url) window.open(url, "_blank", "noopener");
      });
    });
  }

  try {
    import("https://news.google.com/swg/js/v1/publisher.mjs")
      .then(function (module) {
        var preferredSource = module.preferredSource;
        preferredSource.init({ theme: "dark", lang: lang });
        Array.prototype.forEach.call(buttons, function (button) {
          button.addEventListener("click", function () {
            preferredSource.addPreferredSource();
          });
        });
      })
      .catch(fallback);
  } catch (e) {
    fallback();
  }
})();
