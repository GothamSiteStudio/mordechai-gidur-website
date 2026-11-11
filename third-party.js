/* GTM, Matomo and the site chat. Queues are created immediately so hits are
   not lost; the network requests wait for the first interaction or a short
   idle delay so they do not compete with the first paint. */
(function () {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ "gtm.start": new Date().getTime(), event: "gtm.js" });

    var _paq = (window._paq = window._paq || []);
    _paq.push(["setDocumentTitle", document.domain + "/" + document.title]);
    _paq.push(["setCookieDomain", "*.mordechaigidur.co.il"]);
    _paq.push(["setDomains", ["*.mordechaigidur.co.il"]]);
    _paq.push(["trackPageView"]);
    _paq.push(["enableLinkTracking"]);
    _paq.push(["setTrackerUrl", "https://matomo.gothamsitestudio.com/matomo/matomo.php"]);
    _paq.push(["setSiteId", "19"]);

    var started = false;
    function load(src) {
        var s = document.createElement("script");
        s.async = true;
        s.src = src;
        document.head.appendChild(s);
    }
    function start() {
        if (started) return;
        started = true;
        load("https://www.googletagmanager.com/gtm.js?id=GTM-PQFNX7KN");
        load("https://matomo.gothamsitestudio.com/matomo/matomo.js");
        load("https://bhwebchat.gothamsitestudio.com/w/bwc_b862d740498e76143b67f9839fa5b2d2.js");
    }

    ["pointerdown", "keydown", "touchstart"].forEach(function (ev) {
        window.addEventListener(ev, start, { once: true, passive: true });
    });
    var later = function () { setTimeout(start, 4000); };
    if ("requestIdleCallback" in window) requestIdleCallback(later, { timeout: 5000 });
    else window.addEventListener("load", later);

    document.querySelectorAll(".footer-year").forEach(function (el) {
        el.textContent = String(new Date().getFullYear());
    });
})();
