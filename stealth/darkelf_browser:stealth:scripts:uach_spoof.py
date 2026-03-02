import json
from ..ua_spoof import SPOOF_UA

def get_js():
    UA = SPOOF_UA
    UAData = {
        "brands": [
            {"brand": "Chromium", "version": "122"},
            {"brand": "Not(A:Brand", "version": "24"},
            {"brand": "Google Chrome", "version": "122"}
        ],
        "mobile": False,
        "platform": "macOS",
        "getHighEntropyValues": "dummy"
    }
    return f"""
(() => {{
  const UA = {json.dumps(UA)};
  const UAData = {{
    brands: [
      {{ brand: "Chromium", version: "122" }},
      {{ brand: "Not(A:Brand", version: "24" }},
      {{ brand: "Google Chrome", version: "122" }}
    ],
    mobile: false,
    platform: "macOS",
    getHighEntropyValues: async (hints) => {{
      const out = {{}};
      (hints || []).forEach((k) => {{
        if (k === "architecture") out.architecture = "x86";
        else if (k === "bitness") out.bitness = "64";
        else if (k === "model") out.model = "";
        else if (k === "platform") out.platform = "macOS";
        else if (k === "platformVersion") out.platformVersion = "10.15.7";
        else if (k === "uaFullVersion") out.uaFullVersion = "122.0.0.0";
        else if (k === "fullVersionList") out.fullVersionList = [
          {{ brand: "Chromium", version: "122.0.0.0" }},
          {{ brand: "Not(A:Brand", version: "24.0.0.0" }},
          {{ brand: "Google Chrome", version: "122.0.0.0" }}
        ];
      }});
      return out;
    }}
  }};
  function def(obj, prop, value) {{
    try {{
      Object.defineProperty(obj, prop, {{ get: () => value, configurable: true }});
    }} catch(e) {{}}
  }}
  try {{
    def(navigator, "userAgent", UA);
    def(navigator, "vendor", "Google Inc.");
    if (navigator.userAgentData) {{
      def(navigator, "userAgentData", UAData);
    }}
  }} catch(e) {{}}
}})();
"""
