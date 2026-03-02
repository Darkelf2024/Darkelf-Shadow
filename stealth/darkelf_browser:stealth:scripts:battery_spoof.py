JS = r"""
if ("getBattery" in navigator) {
    navigator.getBattery = function() {
        return Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1,
            addEventListener: function(){},
            removeEventListener: function(){},
            onchargingchange: null,
            onlevelchange: null
        });
    };
}
"""
