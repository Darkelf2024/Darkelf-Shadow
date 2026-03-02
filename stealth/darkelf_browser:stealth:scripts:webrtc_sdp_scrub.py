JS = """
(function() {
    if (!window.RTCPeerConnection) return;
    const OriginalRTCPeerConnection = window.RTCPeerConnection;
    window.RTCPeerConnection = function(...args) {
        const pc = new OriginalRTCPeerConnection(...args);
        const wrap = (method) => {
            if (pc[method]) {
                const original = pc[method].bind(pc);
                pc[method] = async function(...mArgs) {
                    const result = await original(...mArgs);
                    if (result && result.sdp) {
                        result.sdp = result.sdp.replace(/(\\d{1,3}\\.){3}\\d{1,3}/g, "0.0.0.0");
                        result.sdp = result.sdp.replace(/ice-ufrag:.+\\r\\n/g, '');
                        result.sdp = result.sdp.replace(/ice-pwd:.+\\r\\n/g, '');
                    }
                    return result;
                };
            }
        };
        wrap("createOffer");
        wrap("createAnswer");
        return pc;
    };
})();
"""
