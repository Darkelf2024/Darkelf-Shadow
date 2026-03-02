def get_js(seed):
    return f"""
(() => {{
    const tabSeed = {seed};
    function hashString(str) {{
        let h = 2166136261;
        for (let i = 0; i < str.length; i++) {{
            h ^= str.charCodeAt(i);
            h = Math.imul(h, 16777619);
        }}
        return h >>> 0;
    }}
    const domainHash = hashString(location.hostname);
    const seed = tabSeed ^ domainHash;
    function pixelNoise(seed, index) {{
        let x = seed ^ index;
        x = Math.imul(x ^ (x >>> 15), 0x85ebca6b);
        x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
        x = x ^ (x >>> 16);
        return (x & 0xff);
    }}
    function applyNoise(imageData) {{
        const data = imageData.data;
        for (let i = 0; i < data.length; i++) {{
            const n = (pixelNoise(seed, i) % 12) - 4;
            data[i] = Math.min(255, Math.max(0, data[i] + n));
        }}
    }}
    function cloneImageData(ctx, src) {{
        const copy = ctx.createImageData(src.width, src.height);
        copy.data.set(src.data);
        return copy;
    }}
    function safePatch(proto, method, wrapper) {{
        const original = proto[method];
        Object.defineProperty(proto, method, {{
            value: wrapper(original),
            configurable: false,
            writable: false
        }});
    }}
    safePatch(HTMLCanvasElement.prototype, 'toDataURL', function(original) {{
        return function() {{
            try {{
                const ctx = this.getContext('2d');
                if (!ctx) return original.apply(this, arguments);
                const w = this.width;
                const h = this.height;
                if (!w || !h) return original.apply(this, arguments);
                const originalData = ctx.getImageData(0, 0, w, h);
                const modifiedData = cloneImageData(ctx, originalData);
                applyNoise(modifiedData);
                ctx.putImageData(modifiedData, 0, 0);
                const result = original.apply(this, arguments);
                ctx.putImageData(originalData, 0, 0);
                return result;
            }} catch (e) {{
                return original.apply(this, arguments);
            }}
        }};
    }});
    safePatch(HTMLCanvasElement.prototype, 'toBlob', function(original) {{
        return function(callback, type, quality) {{
            try {{
                const ctx = this.getContext('2d');
                if (!ctx) return original.apply(this, arguments);
                const w = this.width;
                const h = this.height;
                if (!w || !h) return original.apply(this, arguments);
                const originalData = ctx.getImageData(0, 0, w, h);
                const modifiedData = cloneImageData(ctx, originalData);
                applyNoise(modifiedData);
                ctx.putImageData(modifiedData, 0, 0);
                original.call(this, function(blob) {{
                    ctx.putImageData(originalData, 0, 0);
                    callback(blob);
                }}, type, quality);
            }} catch (e) {{
                return original.apply(this, arguments);
            }}
        }};
    }});
    safePatch(CanvasRenderingContext2D.prototype, 'getImageData', function(original) {{
        return function(x, y, w, h) {{
            const imageData = original.call(this, x, y, w, h);
            applyNoise(imageData);
            return imageData;
        }};
    }});
}})();
"""
