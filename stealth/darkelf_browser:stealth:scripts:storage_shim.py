JS = r"""
(() => {
  if (window.__darkelf_storage_shim) return;
  window.__darkelf_storage_shim = true;
  function makeMemoryStorage() {
    const store = new Map();
    const api = {
      get length() { return store.size; },
      key: (i) => Array.from(store.keys())[i] ?? null,
      getItem: (k) => {
        k = String(k);
        return store.has(k) ? store.get(k) : null;
      },
      setItem: (k, v) => {
        k = String(k);
        v = String(v);
        store.set(k, v);
      },
      removeItem: (k) => { store.delete(String(k)); },
      clear: () => { store.clear(); }
    };
    return api;
  }
  const memLocal = makeMemoryStorage();
  const memSession = makeMemoryStorage();
  function def(obj, prop, value) {
    try {
      Object.defineProperty(obj, prop, {
        get: () => value,
        configurable: true
      });
    } catch(e) {}
  }
  try { def(window, "localStorage", memLocal); } catch(e) {}
  try { def(window, "sessionStorage", memSession); } catch(e) {}
  try { Object.defineProperty(window, "indexedDB", { get: () => undefined, configurable: true }); } catch(e) {}
  try { Object.defineProperty(window, "openDatabase", { get: () => undefined, configurable: true }); } catch(e) {}
  try {
    window.addEventListener("storage", () => {}, true);
  } catch(e) {}
  const applyTo = (w) => {
    try {
      if (!w || w.__darkelf_storage_shim) return;
      w.__darkelf_storage_shim = true;
      try { def(w, "localStorage", makeMemoryStorage()); } catch(e) {}
      try { def(w, "sessionStorage", makeMemoryStorage()); } catch(e) {}
      try { Object.defineProperty(w, "indexedDB", { get: () => undefined, configurable: true }); } catch(e) {}
      try { Object.defineProperty(w, "openDatabase", { get: () => undefined, configurable: true }); } catch(e) {}
    } catch(e) {}
  };
  new MutationObserver((muts) => {
    for (const m of muts) {
      for (const node of m.addedNodes) {
        if (node && node.tagName === "IFRAME") {
          try { applyTo(node.contentWindow); } catch(e) {}
          try { node.addEventListener("load", () => applyTo(node.contentWindow), { once: true }); } catch(e) {}
        }
      }
    }
  }).observe(document.documentElement || document, { childList: true, subtree: true });
})();
"""
