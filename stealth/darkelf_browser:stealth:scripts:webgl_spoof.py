JS = """
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
    function seededRand(seed) {
        let a = seed + 0x6D2B79F5;
        a = Math.imul(a ^ a >>> 15, a | 1);
        a ^= a + Math.imul(a ^ a >>> 7, a | 61);
        return ((a ^ a >>> 14) >>> 0) / 4294967296;
    }
    function tweak(val, rn) {
        if (typeof val === 'number')
            return (val + Math.round(rn * 8 - 4));
        if (typeof val === 'string')
            return val.replace(/[A-Za-z0-9]/g, function(c) {
                return String.fromCharCode(c.charCodeAt(0) ^ (rn * 21 | 0));
            });
        return val;
    }
    function patchWebGL(ctxName) {
        let proto = window[ctxName] && window[ctxName].prototype;
        if (!proto) return;
        let _getParameter = proto.getParameter;
        proto.getParameter = function(param) {
            const SENSITIVE = [
                37445, 37446, 7936, 7937, 35724, 7938
            ];
            if (SENSITIVE.includes(param)) {
                let orig = _getParameter.apply(this, arguments);
                let r = seededRand(SEED + param);
                return tweak(orig, r);
            }
            if (typeof param === "string" && param.match(/_webgl|_renderer|_vendor|_version/i)) {
                let orig = _getParameter.apply(this, arguments);
                let r = seededRand(SEED + (param.length || 0));
                return tweak(orig, r);
            }
            return _getParameter.apply(this, arguments);
        };
    }
    patchWebGL('WebGLRenderingContext');
    patchWebGL('WebGL2RenderingContext');
})();
"""
