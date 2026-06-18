# backend/hardening.py
#
# All fingerprint-defense JavaScript, installed ONCE at the profile level via
# profile.scripts(). Every page that uses the hardened profile -- including a
# QML WebEngineView -- inherits these injections automatically at
# DocumentCreation, in the main world, on all sub-frames.
#
# This is the modern replacement for the old per-page HardenedWebPage subclass:
# the frontend can use any view type and still get the full hardening surface.

import json
import secrets

from PySide6.QtWebEngineCore import QWebEngineScript

from .constants import CHROME_UA_STR, PLATFORM_PART


def detect_nav_platform_value() -> str:
    if "Windows" in PLATFORM_PART:
        return "Win32"
    if "Mac" in PLATFORM_PART:
        return "MacIntel"
    if "Linux" in PLATFORM_PART:
        return "Linux x86_64"
    return "Win32"


# ----------------------------------------------------------------------------
# Script bodies
# ----------------------------------------------------------------------------

_LETTERBOXING = r"""
(() => {
    const detectPlatform = () => {
        try {
            const p = navigator.platform.toLowerCase();
            if (p.includes('mac')) return 'mac';
            if (p.includes('win')) return 'windows';
            if (p.includes('linux')) return 'linux';
            return 'windows';
        } catch (e) { return 'windows'; }
    };
    const personas = [[1920,1080],[1536,864],[1440,900],[1366,768],[1280,720]];
    const pickPersona = () => {
        try {
            const p = personas[Math.floor(Math.random() * personas.length)];
            return { width: p[0], height: p[1] };
        } catch(e) { return { width: 1920, height: 1080 }; }
    };
    const frameSizes = { windows: 140, mac: 80, linux: 120 };
    const persona = pickPersona();
    const applyPatch = (win) => {
        try {
            const platform = detectPlatform();
            const frame = frameSizes[platform] || 140;
            const width = persona.width;
            const height = persona.height;
            const safeDefine = (obj, key, getter) => {
                try { Object.defineProperty(obj, key, { get: getter, configurable: false }); } catch(e) {}
            };
            safeDefine(win.screen, "width", () => width);
            safeDefine(win.screen, "height", () => height);
            safeDefine(win.screen, "availWidth", () => width);
            safeDefine(win.screen, "availHeight", () => height);
            safeDefine(win, "innerWidth", () => width);
            safeDefine(win, "innerHeight", () => height);
            safeDefine(win, "outerWidth", () => width);
            safeDefine(win, "outerHeight", () => height + frame);
        } catch (e) {}
    };
    applyPatch(window);
    new MutationObserver((muts) => {
        for (const m of muts) {
            m.addedNodes.forEach((node) => {
                if (node.tagName === 'IFRAME') {
                    try { applyPatch(node.contentWindow); } catch (e) {}
                }
            });
        }
    }).observe(document, { childList: true, subtree: true });
})();
"""

_WEBRTC_BLOCK = r"""
(() => {
    const block = (target, key) => {
        try {
            Object.defineProperty(target, key, {
                get: () => undefined, set: () => {}, configurable: false
            });
            delete target[key];
        } catch (e) {}
    };
    const targets = [
        [window, 'RTCPeerConnection'],
        [window, 'webkitRTCPeerConnection'],
        [window, 'mozRTCPeerConnection'],
        [window, 'RTCDataChannel'],
        [navigator, 'mozRTCPeerConnection'],
        [navigator, 'mediaDevices']
    ];
    targets.forEach(([obj, key]) => block(obj, key));
    new MutationObserver((muts) => {
        for (const m of muts) {
            m.addedNodes.forEach((node) => {
                if (node.tagName === 'IFRAME') {
                    try {
                        const w = node.contentWindow;
                        targets.forEach(([obj, key]) => block(w, key));
                        targets.forEach(([obj, key]) => block(w.navigator, key));
                    } catch (e) {}
                }
            });
        }
    }).observe(document, { childList: true, subtree: true });
})();
"""

_GEOLOCATION = r"""
(function() {
    Object.defineProperty(navigator, "geolocation", {
        get: function () { return undefined; },
        configurable: true
    });
    if (navigator.permissions && navigator.permissions.query) {
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {
            if (parameters.name === "geolocation") {
                return Promise.resolve({ state: "denied" });
            }
            return originalQuery(parameters);
        };
    }
})();
"""

_CANVAS = r"""
(() => {
    const tabSeed = __TAB_SEED__;
    function hashString(str) {
        let h = 2166136261;
        for (let i = 0; i < str.length; i++) {
            h ^= str.charCodeAt(i);
            h = Math.imul(h, 16777619);
        }
        return h >>> 0;
    }
    const domainHash = hashString(location.hostname);
    const seed = tabSeed ^ domainHash;
    function pixelNoise(seed, index) {
        let x = seed ^ index;
        x = Math.imul(x ^ (x >>> 15), 0x85ebca6b);
        x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
        x = x ^ (x >>> 16);
        return (x & 0xff);
    }
    function applyNoise(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i++) {
            const n = (pixelNoise(seed, i) % 12) - 4;
            data[i] = Math.min(255, Math.max(0, data[i] + n));
        }
    }
    function cloneImageData(ctx, src) {
        const copy = ctx.createImageData(src.width, src.height);
        copy.data.set(src.data);
        return copy;
    }
    function safePatch(proto, method, wrapper) {
        const original = proto[method];
        Object.defineProperty(proto, method, {
            value: wrapper(original), configurable: false, writable: false
        });
    }
    safePatch(HTMLCanvasElement.prototype, 'toDataURL', function(original) {
        return function() {
            try {
                const ctx = this.getContext('2d');
                if (!ctx) return original.apply(this, arguments);
                const w = this.width, h = this.height;
                if (!w || !h) return original.apply(this, arguments);
                const originalData = ctx.getImageData(0, 0, w, h);
                const modifiedData = cloneImageData(ctx, originalData);
                applyNoise(modifiedData);
                ctx.putImageData(modifiedData, 0, 0);
                const result = original.apply(this, arguments);
                ctx.putImageData(originalData, 0, 0);
                return result;
            } catch (e) { return original.apply(this, arguments); }
        };
    });
    safePatch(HTMLCanvasElement.prototype, 'toBlob', function(original) {
        return function(callback, type, quality) {
            try {
                const ctx = this.getContext('2d');
                if (!ctx) return original.apply(this, arguments);
                const w = this.width, h = this.height;
                if (!w || !h) return original.apply(this, arguments);
                const originalData = ctx.getImageData(0, 0, w, h);
                const modifiedData = cloneImageData(ctx, originalData);
                applyNoise(modifiedData);
                ctx.putImageData(modifiedData, 0, 0);
                original.call(this, function(blob) {
                    ctx.putImageData(originalData, 0, 0);
                    callback(blob);
                }, type, quality);
            } catch (e) { return original.apply(this, arguments); }
        };
    });
    safePatch(CanvasRenderingContext2D.prototype, 'getImageData', function(original) {
        return function(x, y, w, h) {
            const imageData = original.call(this, x, y, w, h);
            applyNoise(imageData);
            return imageData;
        };
    });
})();
"""

_HW_FINGERPRINT = r"""
(() => {
  try {
    Object.defineProperty(navigator, "deviceMemory", { get: () => undefined, configurable: true });
  } catch(e){}
  try {
    const cpuRand = Math.floor(Math.random() * 11) + 2;
    Object.defineProperty(navigator, "hardwareConcurrency", { get: () => cpuRand, configurable: true });
  } catch(e){}
})();
"""

_WEBGL = r"""
(() => {
    function stringHash(s) {
        let h = 2166136261;
        for (let i = 0; i < s.length; i++) {
            h ^= s.charCodeAt(i);
            h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
        }
        return h >>> 0;
    }
    const SEED = stringHash(location.hostname);
    const PLATFORM = navigator.platform.toLowerCase();
    const PROFILES = {
        mac: [
            { vendor: "Google Inc. (Apple)", renderer: "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)" },
            { vendor: "Google Inc. (Apple)", renderer: "ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)" }
        ],
        win: [
            { vendor: "Google Inc. (Intel)", renderer: "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)" },
            { vendor: "Google Inc. (NVIDIA)", renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)" }
        ],
        linux: [
            { vendor: "Google Inc. (X.Org)", renderer: "ANGLE (AMD, AMD Radeon RX 580 (POLARIS10), OpenGL 4.6)" },
            { vendor: "Google Inc. (Mesa)", renderer: "ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (KBL GT2), OpenGL 4.6)" }
        ]
    };
    function pickProfile() {
        let list;
        if (PLATFORM.includes("mac")) list = PROFILES.mac;
        else if (PLATFORM.includes("win")) list = PROFILES.win;
        else list = PROFILES.linux;
        return list[SEED % list.length];
    }
    const PROFILE = pickProfile();
    function patchWebGL(ctxName) {
        let proto = window[ctxName] && window[ctxName].prototype;
        if (!proto) return;
        let _getParameter = proto.getParameter;
        proto.getParameter = function(param) {
            switch (param) {
                case 37445: return PROFILE.vendor;
                case 37446: return PROFILE.renderer;
                case 7936:  return PROFILE.vendor;
                case 7937:  return PROFILE.renderer;
                case 35724: return "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)";
                case 7938:  return "WebGL 2.0 (OpenGL ES 3.0 Chromium)";
            }
            return _getParameter.apply(this, arguments);
        };
    }
    patchWebGL('WebGLRenderingContext');
    patchWebGL('WebGL2RenderingContext');
})();
"""

_AUDIO = r"""
(function() {
    function hashString(str) {
        let h = 2166136261 >>> 0;
        for (let i = 0; i < str.length; i++) {
            h ^= str.charCodeAt(i);
            h = Math.imul(h, 16777619);
        }
        return h >>> 0;
    }
    function mulberry32(a) {
        return function() {
            var t = a += 0x6D2B79F5;
            t = Math.imul(t ^ t >>> 15, t | 1);
            t ^= t + Math.imul(t ^ t >>> 7, t | 61);
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        }
    }
    const seed = hashString(location.hostname);
    const rand = mulberry32(seed);
    const amplitude = 1e-7;
    function perturb(data) {
        for (let i = 0; i < data.length; i++) { data[i] += (rand() - 0.5) * amplitude; }
        return data;
    }
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function() {
        const data = origGetChannelData.apply(this, arguments);
        return perturb(data);
    };
    if (AudioBuffer.prototype.copyFromChannel) {
        const origCopy = AudioBuffer.prototype.copyFromChannel;
        AudioBuffer.prototype.copyFromChannel = function(dest, channel, start) {
            origCopy.apply(this, arguments);
            perturb(dest);
        };
    }
})();
"""

_BATTERY = r"""
if ("getBattery" in navigator) {
  navigator.getBattery = function() {
    return Promise.resolve({
      charging: true, chargingTime: 0, dischargingTime: Infinity, level: 1,
      addEventListener: function(){}, removeEventListener: function(){},
      onchargingchange: null, onlevelchange: null
    });
  };
}
"""

_FONT = r"""
(function() {
    function hashString(str) {
        let h = 2166136261 >>> 0;
        for (let i = 0; i < str.length; i++) {
            h ^= str.charCodeAt(i);
            h = Math.imul(h, 16777619);
        }
        return h >>> 0;
    }
    function mulberry32(a) {
        return function() {
            var t = a += 0x6D2B79F5;
            t = Math.imul(t ^ t >>> 15, t | 1);
            t ^= t + Math.imul(t ^ t >>> 7, t | 61);
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        }
    }
    const seed = hashString(window.__darkelfSeed || location.hostname);
    const rand = mulberry32(seed);
    const commonFonts = ["Arial","Verdana","Tahoma","Times New Roman","Courier New","Georgia","Trebuchet MS","Comic Sans MS","Impact","Calibri"];
    const fakeInstalled = new Set();
    commonFonts.forEach(font => { if (rand() > 0.4) { fakeInstalled.add(font.toLowerCase()); } });
    if (document.fonts && document.fonts.check) {
        const origCheck = document.fonts.check;
        document.fonts.check = function(str) {
            const match = str.match(/^\d+px\s+["']?([^"']+)["']?/);
            if (match) { return fakeInstalled.has(match[1].toLowerCase()); }
            return origCheck.apply(this, arguments);
        };
    }
    const amplitude = 0.01;
    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {
        const metrics = origMeasureText.apply(this, arguments);
        const noise = (rand() - 0.5) * amplitude;
        return new Proxy(metrics, {
            get(target, prop) {
                if (prop === "width") { return target.width + noise; }
                return target[prop];
            }
        });
    };
})();
"""

_RESIZE_OBSERVER = r"""
try { new ResizeObserver(() => {}).observe(document.body); } catch (e) {}
window.addEventListener("error", function(e) {
  if (e && e.message && e.message.indexOf('ResizeObserver loop limit exceeded') > -1)
    e.preventDefault();
}, true);
"""

_HW_CONCURRENCY = r"""
(() => {
    const values = [2,4,6,8];
    const hashHost = (host) => {
        let h = 0;
        for (let i = 0; i < host.length; i++) { h = ((h << 5) - h) + host.charCodeAt(i); h |= 0; }
        return Math.abs(h);
    };
    const getValue = () => {
        try {
            const host = location.hostname || "default";
            return values[hashHost(host) % values.length];
        } catch(e) { return values[Math.floor(Math.random()*values.length)]; }
    };
    const patch = (nav) => {
        try {
            Object.defineProperty(nav, "hardwareConcurrency", { get() { return getValue(); }, configurable: false, enumerable: true });
            Object.defineProperty(Navigator.prototype, "hardwareConcurrency", { get() { return getValue(); }, configurable: false, enumerable: true });
        } catch(e) {}
    };
    const apply = (win) => {
        try {
            if (!win || win.__darkelf_hw_patch) return;
            win.__darkelf_hw_patch = true;
            patch(win.navigator);
        } catch(e) {}
    };
    apply(window);
    new MutationObserver((muts) => {
        for (const m of muts) {
            m.addedNodes.forEach((node) => {
                if (!node.tagName) return;
                if (node.tagName.toLowerCase() === "iframe") {
                    try { apply(node.contentWindow); } catch(e) {}
                }
            });
        }
    }).observe(document,{childList:true,subtree:true});
})();
"""

_IFRAME_HARMONIZER = r"""
(() => {
  if (window.__darkelf_iframe_harmonizer) return;
  window.__darkelf_iframe_harmonizer = true;
  const SPOOF = __SPOOF_JSON__;
  try { SPOOF.userAgent = navigator.userAgent; } catch(e) {}
  function def(obj, prop, getter) {
    try { Object.defineProperty(obj, prop, { get: getter, configurable: true }); } catch(e) {}
  }
  function applyToWindow(w) {
    if (!w || w.__darkelf_spoofed) return;
    try { w.__darkelf_spoofed = true; } catch(e) {}
    try {
      const nav = w.navigator;
      if (!nav) return;
      const proto = Object.getPrototypeOf(nav);
      def(proto,"platform",() => SPOOF.platform);
      def(proto,"vendor",() => SPOOF.vendor);
      def(proto,"userAgent",() => SPOOF.userAgent);
      def(proto,"deviceMemory",() => SPOOF.deviceMemory);
      def(proto,"languages",() => SPOOF.languages.slice());
      def(proto,"language",() => SPOOF.language);
      def(proto,"maxTouchPoints",() => SPOOF.maxTouchPoints);
    } catch(e) {}
  }
  applyToWindow(window);
})();
"""

_STEALTH_CHROME_ENV = r"""
(() => {
    const hashString = (str) => {
        let h = 0;
        for (let i = 0; i < str.length; i++) { h = (h << 5) - h + str.charCodeAt(i); h |= 0; }
        return Math.abs(h);
    };
    const seededShuffle = (array, seed) => {
        let arr = array.slice();
        for (let i = arr.length - 1; i > 0; i--) {
            seed = (seed * 9301 + 49297) % 233280;
            const j = Math.floor((seed / 233280) * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
    };
    const patchPlugins = (nav, win) => {
        try {
            if (!nav) return;
            const host = (win.location && win.location.hostname) || "default";
            const seed = hashString(host);
            const basePlugins = [
                { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" },
                { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" },
                { name: "Native Client", filename: "internal-nacl-plugin" }
            ];
            let plugins;
            if (seed % 3 === 0) { plugins = []; }
            else {
                plugins = seededShuffle(basePlugins, seed);
                const cut = 2 + (seed % 2);
                plugins = plugins.slice(0, cut);
            }
            plugins.length = plugins.length;
            plugins.item = (i) => plugins[i];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            Object.defineProperty(nav, 'plugins', { get: () => plugins, configurable: true });
            Object.defineProperty(nav, 'mimeTypes', { get: () => [], configurable: true });
        } catch (e) {}
    };
    const patchChromeRuntime = (win) => {
        try {
            if (!win.chrome) win.chrome = {};
            if (!win.chrome.runtime) {
                Object.defineProperty(win.chrome, 'runtime', { get: () => ({}), configurable: true });
            }
        } catch (e) {}
    };
    const patchPermissions = (nav) => {
        try {
            if (nav.permissions && nav.permissions.query) {
                const originalQuery = nav.permissions.query.bind(nav.permissions);
                nav.permissions.query = function(parameters) {
                    if (parameters && parameters.name === 'notifications') {
                        return Promise.resolve({ state: Notification.permission });
                    }
                    return originalQuery(parameters);
                };
            }
        } catch (e) {}
    };
    const apply = (win) => {
        try {
            if (!win || win.__darkelf_chrome_env) return;
            win.__darkelf_chrome_env = true;
            patchPlugins(win.navigator, win);
            patchChromeRuntime(win);
            patchPermissions(win.navigator);
        } catch (e) {}
    };
    apply(window);
    new MutationObserver((muts) => {
        for (const m of muts) {
            m.addedNodes.forEach((node) => {
                if (!node.tagName) return;
                if (node.tagName.toLowerCase() === "iframe") {
                    try { apply(node.contentWindow); } catch (e) {}
                }
            });
        }
    }).observe(document, { childList: true, subtree: true });
})();
"""

_YOUTUBE_SPOOF = r"""
(() => {
    try {
        const host = location.hostname || "";
        const isYouTube = host.includes("youtube.com") || host.includes("youtu.be") ||
                          host.includes("ytimg.com") || host.includes("googlevideo.com");
        if (!isYouTube) return;
        const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)";
        Object.defineProperty(navigator, "userAgent", { get: () => UA, configurable: true });
        Object.defineProperty(navigator, "appVersion", { get: () => UA, configurable: true });
        Object.defineProperty(navigator, "platform", { get: () => "MacIntel", configurable: true });
        Object.defineProperty(navigator, "vendor", { get: () => "Apple Computer, Inc.", configurable: true });
    } catch(e) {}
})();
"""

_GLOBAL_CHROME_SPOOF = r"""
(() => {
    try {
        const UA = "__UA__";
        Object.defineProperty(navigator, "userAgent", { get: () => UA, configurable: true });
        Object.defineProperty(navigator, "appVersion", { get: () => UA, configurable: true });
        Object.defineProperty(navigator, "vendor", { get: () => "Google Inc.", configurable: true });
        Object.defineProperty(navigator, "platform", { get: () => "__PLATFORM__", configurable: true });
    } catch(e) {}
})();
"""


def _build_script(name: str, source: str) -> QWebEngineScript:
    s = QWebEngineScript()
    s.setName(name)
    s.setSourceCode(source)
    s.setInjectionPoint(QWebEngineScript.DocumentCreation)
    s.setRunsOnSubFrames(True)
    s.setWorldId(QWebEngineScript.MainWorld)
    return s


def install_hardening(profile, canvas_seed: int | None = None) -> None:
    """
    Install every fingerprint-defense script onto the profile and pin the
    profile-level User-Agent. Call once, right after creating the profile.
    """
    if canvas_seed is None:
        canvas_seed = secrets.randbits(32) & 0xFFFFFFFF

    # Pin the network-level UA to match the JS-level spoof.
    profile.setHttpUserAgent(CHROME_UA_STR)

    spoof = {
        "platform": detect_nav_platform_value(),
        "vendor": "Google Inc.",
        "userAgent": None,
        "deviceMemory": None,
        "languages": ["en-US", "en"],
        "language": "en-US",
        "maxTouchPoints": 0,
    }

    canvas_src = _CANVAS.replace("__TAB_SEED__", str(int(canvas_seed)))
    iframe_src = _IFRAME_HARMONIZER.replace("__SPOOF_JSON__", json.dumps(spoof))
    global_src = (
        _GLOBAL_CHROME_SPOOF
        .replace("__UA__", CHROME_UA_STR)
        .replace("__PLATFORM__", PLATFORM_PART)
    )

    scripts = [
        ("darkelf_letterboxing", _LETTERBOXING),
        ("darkelf_webrtc_block", _WEBRTC_BLOCK),
        ("darkelf_geolocation", _GEOLOCATION),
        ("darkelf_canvas", canvas_src),
        ("darkelf_hw_fingerprint", _HW_FINGERPRINT),
        ("darkelf_webgl", _WEBGL),
        ("darkelf_audio", _AUDIO),
        ("darkelf_battery", _BATTERY),
        ("darkelf_font", _FONT),
        ("darkelf_resize_observer", _RESIZE_OBSERVER),
        ("darkelf_hw_concurrency", _HW_CONCURRENCY),
        ("darkelf_iframe_harmonizer", iframe_src),
        ("darkelf_stealth_chrome_env", _STEALTH_CHROME_ENV),
        ("darkelf_youtube_spoof", _YOUTUBE_SPOOF),
        ("darkelf_global_chrome_spoof", global_src),
    ]

    collection = profile.scripts()
    for name, source in scripts:
        collection.insert(_build_script(name, source))
