from PySide6.QtWebEngineCore import QWebEngineScript

JS_YOUTUBE_AD_NEUTRALIZER = r"""
(function() {

const host = location.hostname;

if (!(host === "www.youtube.com" ||
      host === "youtube.com" ||
      host.endsWith(".youtube.com") ||
      host === "youtu.be")) {
    return;
}

function clean(obj) {

    if (!obj || typeof obj !== "object")
        return obj;

    try {

        if (obj.playerAds)
            delete obj.playerAds;

        if (obj.adPlacements)
            obj.adPlacements = [];

        if (obj.adSlots)
            obj.adSlots = [];

        if (obj.adBreakHeartbeatParams)
            delete obj.adBreakHeartbeatParams;

    } catch(e) {}

    return obj;
}

try {

    let valueStore;

    Object.defineProperty(window, "ytInitialPlayerResponse", {

        configurable: true,

        get() {
            return valueStore;
        },

        set(v) {
            valueStore = clean(v);
        }

    });

} catch(e) {}

try {

    let dataStore;

    Object.defineProperty(window, "ytInitialData", {

        configurable: true,

        get() {
            return dataStore;
        },

        set(v) {
            dataStore = clean(v);
        }

    });

} catch(e) {}

})();
"""


def install_darkelf_youtube_adblock(profile):

    script = QWebEngineScript()

    script.setName("darkelf_youtube_ad_neutralizer")

    script.setInjectionPoint(QWebEngineScript.DocumentCreation)

    script.setWorldId(QWebEngineScript.MainWorld)

    script.setRunsOnSubFrames(False)

    script.setSourceCode(JS_YOUTUBE_AD_NEUTRALIZER)

    profile.scripts().insert(script)
