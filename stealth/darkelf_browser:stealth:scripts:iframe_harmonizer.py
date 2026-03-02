JS = r"""
(() => {
  if (window.__darkelf_iframe_harmonizer) return;
  window.__darkelf_iframe_harmonizer = true;
  const SPOOF = {
    platform: "Win32",
    vendor: "Google Inc.",
    userAgent: navigator.userAgent,
    deviceMemory: undefined,
    hardwareConcurrency: (Math.floor(Math.random() * 11) + 2),
    languages: ["en-US", "en"],
    language: "en-US",
    maxTouchPoints: 0,
  };
  function def(obj, prop, getter) {
    try {
      Object.defineProperty(obj, prop, { get: getter, configurable: true });
    } catch (e) {}
  }
  function applyToWindow(w) {
    if (!w || w.__darkelf_spoofed) return;
    try { w.__darkelf_spoofed = true; } catch(e) {}
    try {
      const n = w.navigator;
      if (n) {
        def(n, "platform", () => SPOOF.platform);
        def(n, "vendor", () => SPOOF.vendor);
        def(n, "userAgent", () => SPOOF.userAgent);
        def(n, "deviceMemory", () => SPOOF.deviceMemory);
        def(n, "hardwareConcurrency", () => SPOOF.hardwareConcurrency);
        def(n, "languages", () => SPOOF.languages.slice());
        def(n, "language", () => SPOOF.language);
        def(n, "maxTouchPoints", () => SPOOF.maxTouchPoints);
      }
    } catch(e) {}
  }
  function patchAllIframes() {
    document.querySelectorAll("iframe").forEach((f) => {
      try { applyToWindow(f.contentWindow); } catch(e) {}
    });
  }
  applyToWindow(window);
  patchAllIframes();
  const mo = new MutationObserver((muts) => {
    for (const m of muts) {
      for (const node of m.addedNodes) {
        if (!node || !node.tagName) continue;
        if (node.tagName === "IFRAME") {
          try { applyToWindow(node.contentWindow); } catch(e) {}
          try {
            node.addEventListener("load", () => {
              try { applyToWindow(node.contentWindow); } catch(e) {}
            }, { once: true });
          } catch(e) {}
          continue;
        }
        if (node.querySelectorAll) {
          node.querySelectorAll("iframe").forEach((f) => {
            try { applyToWindow(f.contentWindow); } catch(e) {}
          });
        }
      }
    }
  });
  try {
    mo.observe(document.documentElement || document, { childList: true, subtree: true });
  } catch(e) {}
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", patchAllIframes, { once: true });
  }
})();
"""
