JS = r"""
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
    const commonFonts = [
        "Arial","Verdana","Tahoma","Times New Roman",
        "Courier New","Georgia","Trebuchet MS",
        "Comic Sans MS","Impact","Calibri"
    ];
    const fakeInstalled = new Set();
    commonFonts.forEach(font => {
        if (rand() > 0.4) {
            fakeInstalled.add(font.toLowerCase());
        }
    });
    if (document.fonts && document.fonts.check) {
        const origCheck = document.fonts.check;
        document.fonts.check = function(str) {
            const match = str.match(/^\d+px\s+["']?([^"']+)["']?/);
            if (match) {
                const font = match[1].toLowerCase();
                return fakeInstalled.has(font);
            }
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
                if (prop === "width") {
                    return target.width + noise;
                }
                return target[prop];
            }
        });
    };
})();
"""
