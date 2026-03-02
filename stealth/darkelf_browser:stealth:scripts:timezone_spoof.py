JS = """
(() => {
    Object.defineProperty(Date.prototype, "getTimezoneOffset", {
        value: function() { return 360; },
        configurable: true
    });
    const origDTF = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(locales, options) {
        options = options || {};
        options.timeZone = "UTC";
        return origDTF.call(this, locales, options);
    };
    Intl.DateTimeFormat.prototype = origDTF.prototype;
    if ('timezone' in navigator) {
        Object.defineProperty(navigator, "timezone", {
            get: () => "UTC",
            configurable: true
        });
    }
})();
"""
