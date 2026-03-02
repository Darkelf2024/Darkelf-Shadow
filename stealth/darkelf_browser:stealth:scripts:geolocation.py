JS = """
(function() {
    Object.defineProperty(navigator, "geolocation", {
        get: function () {
            return undefined;
        },
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
