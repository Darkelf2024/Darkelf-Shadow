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
    const domain = location.hostname;
    const seed = hashString(domain);
    const rand = mulberry32(seed);
    const amplitude = 1e-7;
    function perturb(data) {
        for (let i = 0; i < data.length; i++) {
            data[i] += (rand() - 0.5) * amplitude;
        }
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
