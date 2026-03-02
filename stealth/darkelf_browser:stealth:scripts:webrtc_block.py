JS = """
(() => {
    const block = (target, key) => {
        try {
            Object.defineProperty(target, key, {
                get: () => undefined,
                set: () => {},
                configurable: false
            });
            delete target[key];
        } catch (e) {
            // Silently ignore expected errors (e.g. non-configurable)
        }
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
    console.log('[DarkelfAI] WebRTC APIs neutralized.');
})();
"""
