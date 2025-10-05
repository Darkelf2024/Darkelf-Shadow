import sys, os, uuid
import math
import random
from PyQt5.QtCore import Qt, QUrl, QSize, QPointF, QRectF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QAction, QTabWidget, QMessageBox,
    QToolButton, QVBoxLayout, QHBoxLayout, QWidget
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineScript, QWebEngineSettings
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPalette, QPen, QBrush, QPolygonF, QPainterPath
import json

    # ---- Install ad/tracker interceptor ----
# --- Ad/Tracker request blocking -------------------------------------------
import re
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor

import shutil
import subprocess
import secrets
from urllib.parse import quote_plus

import stem.process
from stem.connection import authenticate_cookie
from stem.control import Controller
from stem import Signal as StemSignal
from stem import process as stem_process

devnull = open(os.devnull, 'w')
os.dup2(devnull.fileno(), sys.stderr.fileno())

DUCK_LITE_HTTPS = "https://duckduckgo.com/lite/?q="
DUCK_LITE_ONION = "https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/lite/?q="

MUTE_LOGS_AFTER_BOOT_MS = 0

# --- Tor defaults ---
DEFAULT_TOR = True
DEFAULT_TOR_SOCKS = "socks5://127.0.0.1:9052"   # matches start_tor() config

# --- CLI/env overrides still supported ---
_cli_tor   = any(a in sys.argv for a in ("--tor", "--use-tor", "-T"))
_cli_proxy = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--proxy=")), "")

_env_tor = (
    DEFAULT_TOR
    or _cli_tor
    or (os.environ.get("DARKELF_TOR", "").strip().lower() in ("1", "true", "yes", "on"))
)
_env_proxy = (
    _cli_proxy
    or os.environ.get("DARKELF_PROXY", "").strip()
    or (DEFAULT_TOR_SOCKS if _env_tor else "")
)

# --- Build Chromium flags (append more privacy flags here) ---
flags = []
if _env_proxy:
    flags.append(f'--proxy-server="{_env_proxy}"')

# Export flags so QtWebEngine picks them up before initialization
if flags:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)

# --- Homepage selection ---
USE_ONION_SEARCH = bool(_env_tor)

# --- URL interceptor class (top-level) ---
class DarkelfInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, patterns):
        super().__init__()
        self._patterns = patterns  # list of compiled regex or plain substrings

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        # YouTube/Googlevideo: only block true 3rd-party ad domains
        if "youtube.com" in url or "googlevideo.com" in url or "youtu.be" in url:
            if any(patt in url for patt in [
                "doubleclick.net", "googlesyndication.com", "googletagmanager.com"
            ]):
                info.block(True)
            # Don't block anything else
            return
        # Regular block for other sites
        for patt in self._patterns:
            if hasattr(patt, "search"):
                if patt.search(url):
                    info.block(True)
                    return
            else:
                if patt in url:
                    info.block(True)
                    return

# --- blocklist (module-level) ---
PATTERNS = [
    re.compile(r'(^|//)pagead2\.googlesyndication\.com', re.I),
    re.compile(r'(^|//)googlesyndication\.com', re.I),
    re.compile(r'(^|//)doubleclick\.net', re.I),
    re.compile(r'(^|//)google-analytics\.com', re.I),
    re.compile(r'(^|//)googletagmanager\.com', re.I),
    re.compile(r'(^|//)youtube\.com/api/stats/ads', re.I),
    re.compile(r'(^|//)youtube\.com/get_midroll_info', re.I),
    re.compile(r'(^|//)youtube\.com/pagead/', re.I),
    re.compile(r'(^|//)googlevideo\.com/.*[?&](adformat|oad|ctier)=', re.I),
    re.compile(r'(^|//)facebook\.net', re.I),
    re.compile(r'(^|//)facebook\.com/.*/tr\?', re.I),
    re.compile(r'(^|//)(adnxs|rubiconproject|criteo|pubmatic|openx|quantserve|scorecardresearch)\.(com|net)', re.I),
    re.compile(r'/pixel\.(gif|png|jpg)(\?|$)', re.I),
    re.compile(r'/track\.(gif|png|jpg)(\?|$)', re.I),
]

# Keep a global reference so GC won't collect it:
_DARKELF_INTERCEPTOR = None

def install_interceptor_once(profile=None):
    """
    Install the interceptor on the given QWebEngineProfile.
    If profile is None, installs on the defaultProfile().
    Call this after QApplication() is created and before creating pages.
    """
    global _DARKELF_INTERCEPTOR
    if _DARKELF_INTERCEPTOR is not None:
        return

    if profile is None:
        profile = QWebEngineProfile.defaultProfile()

    _DARKELF_INTERCEPTOR = DarkelfInterceptor(PATTERNS)

    # Defensive: different PyQt builds expose different setter names
    if hasattr(profile, "setUrlRequestInterceptor"):
        profile.setUrlRequestInterceptor(_DARKELF_INTERCEPTOR)
    elif hasattr(profile, "setRequestInterceptor"):
        profile.setRequestInterceptor(_DARKELF_INTERCEPTOR)
    else:
        print("[Darkelf] WARNING: profile has no interceptor setter on this PyQt build")

def get_canvas_js(seed_hex: str, rotate_minutes: int = 30, per_reload: bool = False):
    # Keep this as a *plain* raw triple-quoted string (no f-string!)
    js = r"""
(function(cfg){
  'use strict';
  const ROTATE_MS = Math.max(1,(cfg.rotateMinutes||30))*60*1000;
  const perReload = !!cfg.perReload;
  let seedBase = String(cfg.seed||'seed');
  const topHost = location.hostname.toLowerCase();
  const YT_RE = /(^|\.)youtube\.com$|(^|\.)youtu\.be$|(^|\.)googlevideo\.com$/i;

  // FNV-1a and sfc32 PRNG
  function xfnv1a(str){for(var i=0,h=2166136261>>>0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)}return function(n){for(var i=0,h2=h;i<str.length;i++){h2^=str.charCodeAt(i);h2=Math.imul(h2,16777619)}return (h^h2)>>>0}}
  function sfc32(a,b,c,d){return function(){a>>>0;b>>>0;c>>>0;d>>>0;var t=(a+b)|0;a=b^(b>>>9);b=(c+(c<<3))|0;c=(c<<21)|(c>>>11);d=(d+1)|0;t=(t+d)|0;c=(c+t)|0;return (t>>>0)/4294967296}}
  function bucket(t){return Math.floor(t/ROTATE_MS)}
  function navSalt(){try{return String(Math.floor(performance.timeOrigin||Date.now()))}catch(_ ){return String(Date.now())}}

  function makePRNG(){
    const salt = perReload ? navSalt() : bucket(Date.now());
    const h = xfnv1a(seedBase + '|' + topHost + '|' + salt);
    return sfc32(h('a'), h('b'), h('c'), h('d'));
  }
  let rand = makePRNG();
  function reseed(){ rand = makePRNG(); }

  // control hooks
  window.__darkelf_canvas_set_seed = (s)=>{ try{ seedBase=String(s||'seed'); reseed(); }catch(_ ){} };
  window.__darkelf_canvas_force_rotate = ()=>{ reseed(); };

  function cloneImageData(ctx, src){ const copy=ctx.createImageData(src.width, src.height); copy.data.set(src.data); return copy; }
  function noiseImageData(imgData){
    const data=imgData.data, stride=4;
    const rate = (/youtube|googlevideo|youtu\.be/i.test(topHost)) ? 0.04 : 0.12; // softer on YT
    for(let i=0;i<data.length;i+=stride) if (rand() < rate) data[i] ^= 1; // flip LSB in R channel
  }

  // Patch getImageData
  const _gid = CanvasRenderingContext2D.prototype.getImageData;
  CanvasRenderingContext2D.prototype.getImageData = function(x,y,w,h){
    const real=_gid.call(this,x,y,w,h);
    try{ const copy=cloneImageData(this, real); noiseImageData(copy); return copy; }catch(_ ){ return real; }
  };

  // Patch toDataURL via offscreen copy
  const _td = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(){
    try{ const off=document.createElement('canvas'); off.width=this.width; off.height=this.height;
      const oc=off.getContext('2d'); oc.drawImage(this,0,0);
      const img=oc.getImageData(0,0,off.width,off.height); noiseImageData(img); oc.putImageData(img,0,0);
      return _td.apply(off, arguments);
    }catch(_ ){ return _td.apply(this, arguments); }
  };

  // Patch toBlob similarly
  const _tb = HTMLCanvasElement.prototype.toBlob;
  if (_tb) HTMLCanvasElement.prototype.toBlob = function(cb,type,qual){
    try{ const off=document.createElement('canvas'); off.width=this.width; off.height=this.height;
      const oc=off.getContext('2d'); oc.drawImage(this,0,0);
      const img=oc.getImageData(0,0,off.width,off.height); noiseImageData(img); oc.putImageData(img,0,0);
      return _tb.call(off, cb, type, qual);
    }catch(_ ){ return _tb.call(this, cb, type, qual); }
  };

  // Time-based rotation only when perReload=false
  if (!perReload) setInterval(reseed, ROTATE_MS);

})(JSON.parse('__CFG__'));
"""
    cfg = json.dumps({
        "seed": seed_hex,
        "rotateMinutes": int(rotate_minutes),
        "perReload": bool(per_reload),
    })
    return js.replace("__CFG__", cfg)

def get_or_create_fp_seed():
    # compatibility alias
    return get_or_create_canvas_seed()
    
# --- Canvas Protection: safe, domain-aware ---
from PyQt5.QtWebEngineWidgets import QWebEngineScript

def build_canvas_protection_script(global_seed: str) -> str:
    # This JS disables spoofing on YouTube, Netflix, Gamespot, and gaming/video domains
    return r"""
(function(GLOBAL_SEED){
  try{
    var host = (location && location.hostname) ? location.hostname : "";
    var skipDomains = [
      "youtube.com", "youtu.be", "netflix.com", "gamespot.com", "twitch.tv", "vimeo.com"
    ];
    if (skipDomains.some(function(d){ return host.endsWith(d) || host === d; })) {
      console.log("[Darkelf] Skipping canvas protection on", host);
      return;
    }

    // ---------- utils ----------
    function xfnv1a(str){var h=2166136261>>>0;for(var i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
    function mulberry32(a){a=a>>>0;return function(){a=(a+0x6D2B79F5)>>>0;var t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return ((t^(t>>>14))>>>0)/4294967296;};}
    function hash32(s){return xfnv1a(String(s));}

    var origin=(location&&location.origin)?location.origin:(location.hostname||"");
    var siteKey=(hash32(GLOBAL_SEED+"|"+origin))>>>0;

    // ---------- Canvas 2D ----------
    var _origGetImageData=CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData=function(x,y,w,h){
      var img=_origGetImageData.apply(this,arguments);
      try{
        var area=(w|0)*(h|0);
        // Only spoof on small canvases (<350x350 or area < 122500)
        if(area>122500) return img;
        var stride=67;
        var salt=(siteKey^((w&0xFFFF)<<16)^(h&0xFFFF))>>>0;
        var rnd=mulberry32(salt);
        var d=img.data;
        for(var i=0;i<d.length;i+=4*stride){
          var ch=(i+salt)&2;
          var ii=i+ch;
          d[ii]=(d[ii]+(rnd()<0.5?-1:1))&0xFF;
        }
      }catch(e){}
      return img;
    };

    function tweakImageDataCopy(ctx,w,h,salt2){
      var img=ctx.getImageData(0,0,w,h);
      var d=img.data;
      var rnd=mulberry32((salt2>>>0)^0xA11CE);
      var stride=61;
      for(var i=0;i<d.length;i+=4*stride){
        var ch=(i+w+h)&2;
        var ii=i+ch;
        d[ii]=(d[ii]+(rnd()<0.5?1:-1))&0xFF;
      }
      return img;
    }
    function safeToDataURL(orig,canvas,type){
      try{
        var w=canvas.width|0,h=canvas.height|0,area=w*h;
        if(area<=122500){
          var ctx=canvas.getContext('2d');
          var img=tweakImageDataCopy(ctx,w,h,(siteKey^(w<<16)^h^0x5EED));
          var off=document.createElement('canvas');off.width=w;off.height=h;
          off.getContext('2d').putImageData(img,0,0);
          return off.toDataURL(type||'image/png');
        }
      }catch(e){}
      return orig.apply(canvas,arguments);
    }
    function safeToBlob(orig,canvas,cb,type,q){
      try{
        var w=canvas.width|0,h=canvas.height|0,area=w*h;
        if(area<=122500){
          var ctx=canvas.getContext('2d');
          var img=tweakImageDataCopy(ctx,w,h,(siteKey^(w<<16)^h^0xBADC0DE));
          var off=document.createElement('canvas');off.width=w;off.height=h;
          off.getContext('2d').putImageData(img,0,0);
          return off.toBlob(cb,type||'image/png',q);
        }
      }catch(e){}
      return orig.apply(canvas,arguments);
    }
    (function wrapCanvas(){
      var _origToDataURL=HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL=function(type){return safeToDataURL(_origToDataURL,this,type);};
      var _origToBlob=HTMLCanvasElement.prototype.toBlob;
      HTMLCanvasElement.prototype.toBlob=function(cb,type,q){return safeToBlob(_origToBlob,this,cb,type,q);};
    })();

    // ---------- WebGL (safe spoof only) ----------
    function spoofGLParam(proto){
      if(!proto||!proto.getParameter) return;
      var orig=proto.getParameter;
      proto.getParameter=function(param){
        if(param===37445) return "Intel Inc.";
        if(param===37446) return "Intel Iris OpenGL Engine";
        return orig.apply(this,arguments);
      };
    }
    if(window.WebGLRenderingContext) spoofGLParam(WebGLRenderingContext.prototype);
    if(window.WebGL2RenderingContext) spoofGLParam(WebGL2RenderingContext.prototype);

    try{console.log("[Darkelf] canvas protection: enabled on", origin);}catch(_){}
  }catch(_e){}
})(%s);
""" % json.dumps(global_seed)

def install_canvas_protection_on(page):
    # No need to check URL here: the JS skips itself if on a video domain.
    seed = get_or_create_canvas_seed()
    js = build_canvas_protection_script(seed)
    scripts = page.profile().scripts()
    try:
        existing = list(scripts.toList())
    except Exception:
        existing = []
    for s in existing:
        try:
            if s.name() == "darkelf_canvas_protection":
                scripts.remove(s)
        except Exception:
            pass
    sc = QWebEngineScript()
    sc.setName("darkelf_canvas_protection")
    sc.setInjectionPoint(QWebEngineScript.DocumentCreation)
    try:
        sc.setWorldId(QWebEngineScript.MainWorld)
    except Exception:
        pass
    sc.setRunsOnSubFrames(True)
    sc.setSourceCode(js)
    scripts.insert(sc)

# (optional) install once at app startup so ALL pages inherit it:
def install_canvas_protection_on_profile(profile: QWebEngineProfile):
    tmp = QWebEnginePage(profile)
    install_canvas_protection_on(tmp)
    tmp.deleteLater()

# --- Strict WebRTC lockdown (Cocoa-style) ---
STRICT_WEBRTC_JS = """
(function(){
  // ===== Flags you can toggle =====
  var STRIP_HOST = true;          // Drop "typ host" (LAN)
  var STRIP_SRFLX = true;         // Drop "typ srflx" (public via STUN)
  var REDACT_IPS = true;          // Scrub private IPs in SDP lines
  var BLOCK_GUM  = true;          // Reject mic/cam, keep mediaDevices present
  var FORCE_TURN_ONLY = false;    // Keep only TURN servers from config
  var FORCE_RELAY = true;         // <— Set true to use relay-only policy (best for “no public IP”)
  var NUKE_STUN   = true;         // <— Strip all STUN servers in constructor and setConfiguration
  var DEBUG_LOG   = false;

  // ===== Helpers =====
  var PRIVATE_V4 = /\\b(?:10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|172\\.(?:1[6-9]|2\\d|3[0-1])\\.\\d{1,3}\\.\\d{1,3}|192\\.168\\.\\d{1,3}\\.\\d{1,3}|169\\.254\\.\\d{1,3}\\.\\d{1,3})\\b/g;
  var PRIVATE_V6 = /\\b(?:fc00:[0-9a-f:]+|fd00:[0-9a-f:]+)\\b/ig;
  function log(){ if(DEBUG_LOG && console && console.debug) try{ console.debug.apply(console, arguments);}catch(_){ } }

  function sanitizeCandidateLine(line){
    if(STRIP_HOST  && / typ host /i.test(line)) { log('[webrtc] drop host');  return null; }
    if(STRIP_SRFLX && / typ srflx /i.test(line)){ log('[webrtc] drop srflx'); return null; }
    if(REDACT_IPS) line = line.replace(PRIVATE_V4,'0.0.0.0').replace(PRIVATE_V6,'fd00::');
    return line;
  }

  function sanitizeSDP(sdp){
    if(!sdp) return sdp;
    var out=[], lines=sdp.split(/\\r\\n/);
    for(var i=0;i<lines.length;i++){
      var l=lines[i];
      if(/^a=candidate:/i.test(l)){ l = sanitizeCandidateLine(l); if(l) out.push(l); continue; }
      if(REDACT_IPS && /^c=/.test(l)){ l = l.replace(PRIVATE_V4,'0.0.0.0').replace(PRIVATE_V6,'fd00::'); }
      out.push(l);
    }
    return out.join('\\r\\n');
  }

  function onlyTurn(iceServers){
    if(!iceServers) return iceServers;
    try{
      var out=[];
      for(var i=0;i<iceServers.length;i++){
        var s = iceServers[i]; if(!s) continue;
        var urls = Array.isArray(s.urls)? s.urls : (s.urls? [s.urls] : []);
        if(urls.some(function(u){ return typeof u==='string' && /^turns?:/i.test(u); })) out.push(s);
      }
      return out.length ? out : [];
    }catch(_){ return iceServers; }
  }

  function sanitizeConfig(cfg){
    if(!cfg) cfg = {};
    if(NUKE_STUN || FORCE_TURN_ONLY || FORCE_RELAY){
      cfg = Object.assign({}, cfg);
      if(cfg.iceServers) cfg.iceServers = onlyTurn(cfg.iceServers);
      if(FORCE_RELAY) cfg.iceTransportPolicy = 'relay';
    }
    return cfg;
  }

  // ===== Patch RTCPeerConnection =====
  var PC = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
  if(PC && PC.prototype){
    var Native = PC;

    // Wrap constructor to enforce config policies early
    function WrappedPC(cfg,constraints){
      return new Native(sanitizeConfig(cfg), constraints);
    }
    WrappedPC.prototype = Native.prototype;

    // Patch setConfiguration so pages can’t re-add STUN or disable relay
    var _setConfiguration = Native.prototype.setConfiguration;
    if(_setConfiguration){
      Native.prototype.setConfiguration = function(cfg){
        cfg = sanitizeConfig(cfg);
        return _setConfiguration.call(this, cfg);
      };
    }

    // Patch SDP creators & setters (strip host/srflx + redact)
    var _createOffer = Native.prototype.createOffer;
    Native.prototype.createOffer = function(o){
      return _createOffer.call(this, o).then(function(d){ d.sdp = sanitizeSDP(d.sdp); return d; });
    };
    var _createAnswer = Native.prototype.createAnswer;
    Native.prototype.createAnswer = function(o){
      return _createAnswer.call(this, o).then(function(d){ d.sdp = sanitizeSDP(d.sdp); return d; });
    };
    var _setLocalDescription = Native.prototype.setLocalDescription;
    Native.prototype.setLocalDescription = function(d){
      try{ if(d && d.sdp) d = {type:d.type, sdp:sanitizeSDP(d.sdp)}; }catch(_){}
      return _setLocalDescription.call(this, d);
    };

    // Block adding remote host/srflx candidates
    var _addIceCandidate = Native.prototype.addIceCandidate;
    Native.prototype.addIceCandidate = function(c){
      try{
        var s = (typeof c==='string') ? c : c && c.candidate;
        if(s && ((STRIP_HOST && / typ host /i.test(s)) || (STRIP_SRFLX && / typ srflx /i.test(s)))) {
          log('[webrtc] ignore remote candidate');
          return Promise.resolve();
        }
      }catch(_){}
      return _addIceCandidate.call(this, c);
    };

    // Filter local icecandidate events w/o redispatch gymnastics
    var _addEventListener = Native.prototype.addEventListener;
    Native.prototype.addEventListener = function(type, listener, opts){
      if(type !== 'icecandidate') return _addEventListener.call(this, type, listener, opts);
      var wrapped = function(ev){
        try{
          var cand = ev && ev.candidate && ev.candidate.candidate;
          if(cand && ((STRIP_HOST && / typ host /i.test(cand)) || (STRIP_SRFLX && / typ srflx /i.test(cand)))){
            log('[webrtc] swallowed local candidate');
            return;
          }
        }catch(_){}
        if(typeof listener==='function') return listener.call(this, ev);
      };
      return _addEventListener.call(this, type, wrapped, opts);
    };

    // Expose wrapper so feature detection passes
    try{ Object.defineProperty(window,'RTCPeerConnection',{value:WrappedPC, configurable:false}); }catch(_){}
    try{ if('webkitRTCPeerConnection' in window) Object.defineProperty(window,'webkitRTCPeerConnection',{value:WrappedPC, configurable:false}); }catch(_){}
    try{ if('mozRTCPeerConnection' in window) Object.defineProperty(window,'mozRTCPeerConnection',{value:WrappedPC, configurable:false}); }catch(_){}
  }

  // ===== mediaDevices shim (don’t break YouTube) =====
  try{
    if(!navigator.mediaDevices) Object.defineProperty(navigator,'mediaDevices',{value:{}, configurable:false});
    var md = navigator.mediaDevices;
    if(BLOCK_GUM){
      md.getUserMedia = function(){ return Promise.reject(new DOMException('getUserMedia blocked by policy','NotAllowedError')); };
    }else if(!md.getUserMedia){
      md.getUserMedia = function(){ return Promise.reject(new DOMException('NotSupportedError','NotSupportedError')); };
    }
    md.enumerateDevices = function(){ return Promise.resolve([]); };
    try{ Object.defineProperty(navigator,'getUserMedia',{value:undefined}); }catch(_){}
  }catch(_){}
})();
"""

TOOLBAR_PADDING_FIX_JS = r"""
(function () {
  const PAD = "56px";
  let scheduled = false;

  function applyPadding() {
    scheduled = false;
    const body = document.body;
    if (!body) return;
    if (body.style.paddingTop !== PAD) body.style.paddingTop = PAD;
    const main = document.querySelector("main,#container,#content,[role=main],[id*=main],[class*=main]");
    if (main && main.offsetHeight > 100 && main.style.marginTop !== PAD) {
      main.style.marginTop = PAD;
    }
  }

  function scheduleApply() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(applyPadding);
    }
  }

  function setupObservers() {
    if (document.body) {
      const ro = new ResizeObserver(scheduleApply);
      ro.observe(document.body);

      new MutationObserver(scheduleApply)
        .observe(document.documentElement, { childList: true, subtree: true });
    }
    scheduleApply();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupObservers);
  } else {
    setupObservers();
  }
})();
"""

# --- YouTube in-page hardening (remove ad placements & auto-skip) ---
YOUTUBE_AD_NUKE_JS = r"""
(function(){ try{
  // Strip ad fields early
  Object.defineProperty(window, 'ytInitialPlayerResponse', {
    configurable: true,
    get: function(){ return this.__yipr; },
    set: function(v){
      try{
        if (v) {
          if (v.playerAds) v.playerAds = [];
          if (v.adPlacements) delete v.adPlacements;
          if (v.adSlots) delete v.adSlots;
        }
      }catch(_){}
      this.__yipr = v;
    }
  });

  // Patch JSON.parse so late payloads also get scrubbed
  const _parse = JSON.parse;
  JSON.parse = function(s, reviver){
    const o = _parse(s, reviver);
    try{
      if (o) {
        if (o.playerAds) o.playerAds = [];
        if (o.adPlacements) delete o.adPlacements;
        if (o.adSlots) delete o.adSlots;
      }
    }catch(_){}
    return o;
  };

  // Click "Skip" & remove overlay ads when they appear
  function zap(){
    const click = sel => { const el = document.querySelector(sel); if (el) el.click(); };
    click('.ytp-ad-skip-button');
    click('.ytp-ad-skip-button-modern');
    click('.ytp-ad-overlay-close-button');

    ['.ytp-ad-player-overlay',
     '.ytp-ad-text-overlay',
     '.ytp-ad-image-overlay',
     '.video-ads',
     '.ytp-ad-module'
    ].forEach(sel => {
      document.querySelectorAll(sel).forEach(n => n.remove());
    });
  }

  new MutationObserver(zap).observe(document.documentElement, { childList: true, subtree: true });
  setInterval(zap, 800);
}catch(e){} })();
"""

WEBGL_DEFENSE_JS = r'''
(function() {var getParameter = WebGLRenderingContext.prototype.getParameter;WebGLRenderingContext.prototype.getParameter = function(parameter) {if (parameter === 37445) return "Intel Inc.";if (parameter === 37446) return "Intel(R) Iris(TM) Graphics 6100";return getParameter.apply(this, arguments);};})();
'''
AUDIO_DEFENSE_JS = r'''
(function() {if (window.OfflineAudioContext) {var orig = window.OfflineAudioContext.prototype.getChannelData;window.OfflineAudioContext.prototype.getChannelData = function() {var data = orig.apply(this, arguments);for (var i = 0; i < data.length; i++) data[i] = 0;return data;};}})();
'''
# ---- NEW: Battery spoof ----
BATTERY_DEFENSE_JS = r'''
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
'''

UA_SPOOF_JS = """
Object.defineProperty(navigator,'userAgent',{
    get:function(){
        return "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0";
    },
    configurable:true
});
Object.defineProperty(navigator,'platform',{
    get:()=> "Win32",
    configurable:true
});
Object.defineProperty(navigator,'hardwareConcurrency',{
    get:()=> 2,
    configurable:true
});
Object.defineProperty(navigator,'deviceMemory',{
    get:()=> 2,
    configurable:true
});
Object.defineProperty(navigator,'userAgentData',{
    get:()=> ({
        brands: [
            {brand:"Not-A.Brand",version:"99"},
            {brand:"Chromium",version:"115"},
            {brand:"Google Chrome",version:"115"}
        ],
        mobile: false,
        getHighEntropyValues: (h)=>Promise.resolve({
            architecture:"x86",
            model:"",
            platform:"Windows",
            platformVersion:"10.0.0",
            uaFullVersion:"115.0.0.0",
            fullVersionList: [{brand:"Chromium",version:"115.0.0.0"}]
        })
    }),
    configurable:true
});
Object.defineProperty(navigator,'vendor',{
    get:function(){ return ""; }, // Firefox default: empty string
    configurable:true
});
"""

# --- Minimal font, locale, media, webgl, audio spoofs ---
FONTS_JS = "if(navigator.fonts){navigator.fonts.query=function(){return Promise.resolve([]);};}var s=document.createElement('style');s.textContent='*{font-family:Arial,sans-serif!important}';document.head.appendChild(s);"
LOCALE_JS = "Object.defineProperty(Intl.DateTimeFormat.prototype,'resolvedOptions',{value:function(){return {timeZone:'UTC',locale:'en-US'};},configurable:true});"
MEDIA_JS = "if(navigator.mediaDevices&&navigator.mediaDevices.enumerateDevices){navigator.mediaDevices.enumerateDevices=function(){return Promise.resolve([]);};}"

WEBGL_VENDOR_SPOOF_JS = r"""
(function() {
    // Patch WebGL getParameter
    const spoofed_vendor = "";
    const spoofed_renderer = "ANGLE (Intel, Intel(R) HD Graphics 5500 Direct3D11 vs_5_0 ps_5_0, D3D11)";
    const spoofed_gl_version = "WebGL 2.0 (OpenGL ES 3.0 Mesa 23.1.2)";
    const spoofed_glsl = "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.00)";
    const spoofed_unmasked_vendor = "Intel Open Source Technology Center";
    const spoofed_unmasked_renderer = "Mesa DRI Intel(R) HD Graphics 5500 (Broadwell GT2)";

    function patchGL(ctxProto) {
        if (!ctxProto) return;
        const origGetParameter = ctxProto.getParameter;
        ctxProto.getParameter = function(param) {
            // WebGL constants
            if (param === 0x1F00) return spoofed_vendor; // VENDOR
            if (param === 0x1F01) return spoofed_renderer; // RENDERER
            if (param === 0x1F02) return spoofed_gl_version; // VERSION
            if (param === 0x8B8C) return spoofed_glsl; // SHADING_LANGUAGE_VERSION
            return origGetParameter.apply(this, arguments);
        };
        // Patch getExtension for debug info
        const origGetExtension = ctxProto.getExtension;
        ctxProto.getExtension = function(name) {
            const ext = origGetExtension.apply(this, arguments);
            if (name === "WEBGL_debug_renderer_info" && ext) {
                Object.defineProperty(ext, "UNMASKED_VENDOR_WEBGL", { value: 0x9245 });
                Object.defineProperty(ext, "UNMASKED_RENDERER_WEBGL", { value: 0x9246 });
                const origGetParameter = this.getParameter;
                this.getParameter = function(param) {
                    if (param === 0x9245) return spoofed_unmasked_vendor;
                    if (param === 0x9246) return spoofed_unmasked_renderer;
                    return origGetParameter.apply(this, arguments);
                };
            }
            return ext;
        };
    }
    patchGL(window.WebGLRenderingContext && window.WebGLRenderingContext.prototype);
    patchGL(window.WebGL2RenderingContext && window.WebGL2RenderingContext.prototype);
})();
"""

VENDOR_BLANK_JS = """
try {
    Object.defineProperty(navigator, 'vendor', {
        get: function() { return ""; },
        configurable: true
    });
} catch (e) {}
"""

VENDOR_SMART_SPOOF_JS = """
(function() {
    var host = window.location.hostname || "";
    var youtubeDomains = [
        "youtube.com", "youtu.be", "googlevideo.com"
    ];
    function isYoutubeDomain(h) {
        if (!h) return false;
        h = h.toLowerCase();
        return (
            h === "youtube.com" || h.endsWith(".youtube.com") ||
            h === "googlevideo.com" || h.endsWith(".googlevideo.com") ||
            h === "youtu.be" || h.endsWith(".youtu.be")
        );
    }
    // ---- VENDOR PATCH ----
    try {
        Object.defineProperty(navigator, 'vendor', {
            get: function() {
                if (isYoutubeDomain(host)) return "Google Inc.";
                return "";
            },
            configurable: true
        });
    } catch (e) {}
    // ---- window.chrome PATCH ----
    try {
        if (isYoutubeDomain(host)) {
            if (!('chrome' in window)) {
                // Provide a minimal window.chrome object as required by YouTube
                Object.defineProperty(window, 'chrome', {
                    value: {},
                    configurable: true
                });
            }
        } else {
            if ('chrome' in window) {
                try { delete window.chrome; } catch (e) {}
            }
        }
    } catch (e) {}
})();
"""

IFRAME_VENDOR_SMART_SPOOF_JS = """
(function() {
    var youtubeDomains = [
        "youtube.com", "youtu.be", "googlevideo.com"
    ];
    function isYoutubeDomain(h) {
        if (!h) return false;
        h = h.toLowerCase();
        return (
            h === "youtube.com" || h.endsWith(".youtube.com") ||
            h === "googlevideo.com" || h.endsWith(".googlevideo.com") ||
            h === "youtu.be" || h.endsWith(".youtu.be")
        );
    }
    function patchIframeVendor(win) {
        try {
            var host = "";
            try { host = win.location.hostname; } catch(e) {}
            Object.defineProperty(win.navigator, "vendor", {
                get: function() {
                    if (isYoutubeDomain(host)) return "Google Inc.";
                    return "";
                },
                configurable: true
            });
            // window.chrome object if needed
            if (isYoutubeDomain(host)) {
                if (!('chrome' in win)) {
                    Object.defineProperty(win, 'chrome', { value: {}, configurable: true });
                }
            } else {
                if ('chrome' in win) {
                    try { delete win.chrome; } catch (e) {}
                }
            }
        } catch(e){}
    }
    // Patch main window
    patchIframeVendor(window);
    // Patch all same-origin iframes
    Array.from(document.getElementsByTagName("iframe")).forEach(function(frame) {
        try {
            if (frame.contentWindow) patchIframeVendor(frame.contentWindow);
        } catch(e){}
    });
    // Patch future iframes
    new MutationObserver(function(mutations) {
        for (var i=0; i<mutations.length; ++i) {
            var nodes = mutations[i].addedNodes || [];
            for (var j=0; j<nodes.length; ++j) {
                var node = nodes[j];
                if (node.tagName === "IFRAME") {
                    try {
                        node.addEventListener("load", function() {
                            try {
                                if (this.contentWindow) patchIframeVendor(this.contentWindow);
                            } catch(e){}
                        });
                        if (node.contentWindow) patchIframeVendor(node.contentWindow);
                    } catch(e){}
                }
            }
        }
    }).observe(document.documentElement || document, {childList:true, subtree:true});
})();
"""

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36"
)
FIREFOX_TOR_UA = (
    "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0"
)

SMART_UA_SPOOF_JS = f"""
(function() {{
    var host = window.location.hostname || "";
    function isYoutubeDomain(h) {{
        if (!h) return false;
        h = h.toLowerCase();
        return (
            h === "youtube.com" || h.endsWith(".youtube.com") ||
            h === "googlevideo.com" || h.endsWith(".googlevideo.com") ||
            h === "youtu.be" || h.endsWith(".youtu.be")
        );
    }}
    try {{
        Object.defineProperty(navigator, 'userAgent', {{
            get: function() {{
                if (isYoutubeDomain(host)) return "{CHROME_UA}";
                return "{FIREFOX_TOR_UA}";
            }},
            configurable: true
        }});
    }} catch (e) {{}}
}})();
"""

def get_or_create_canvas_seed():
    path = os.path.expanduser("~/.darkelf_pyqt5_canvas_seed.txt")
    if os.path.exists(path):
        with open(path,"r") as f: return f.read().strip()
    s = "darkelf-"+uuid.uuid4().hex
    with open(path,"w") as f: f.write(s)
    try: os.chmod(path,0o600)
    except Exception: pass
    return s

# --- Custom Icon helpers (ported from fixed2) ---
def make_icon(color="#34C759", size=24):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, size-8, size-8)
    p.end()
    return QIcon(pix)

def make_nav_arrow_icon(direction: str, color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    center = size / 2
    length = size * 0.19
    if direction == "left":
        points = [
            (center + length, center - length),
            (center - length, center),
            (center + length, center + length)
        ]
    elif direction == "right":
        points = [
            (center - length, center - length),
            (center + length, center),
            (center - length, center + length)
        ]
    else:
        points = []
    if points:
        # Convert list of tuples to list of QPointF, then to QPolygonF
        polygon = [QPointF(x, y) for x, y in points]
        p.drawPolygon(*polygon)
    p.end()
    return QIcon(pix)
    
def make_reload_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen_width = max(2, size // 16)
    margin = pen_width // 2 + 6
    radius = (size - 2 * margin) / 2
    center = size / 2
    start_angle_deg = 135
    span_angle_deg = 320
    rect = QRectF(center - radius, center - radius, 2 * radius, 2 * radius)
    pen = QPen(QColor(color), pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))
    p.end()
    return QIcon(pix)

def make_house_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    c = QColor(color)
    linew = max(2, int(size * 0.11))
    cx, cy = size / 2, size / 2
    scale = size / 42.0
    roof_w, roof_h = 20 * scale, 10 * scale
    wall_h, wall_w = 13 * scale, 16 * scale
    roof_peak = QPointF(cx, cy - roof_h)
    roof_left = QPointF(cx - roof_w / 2, cy)
    roof_right = QPointF(cx + roof_w / 2, cy)
    wall_top_left = QPointF(cx - wall_w / 2, cy)
    wall_top_right = QPointF(cx + wall_w / 2, cy)
    wall_bot_left = QPointF(cx - wall_w / 2, cy + wall_h)
    wall_bot_right = QPointF(cx + wall_w / 2, cy + wall_h)
    path = QPainterPath()
    path.moveTo(roof_left)
    path.lineTo(roof_peak)
    path.lineTo(roof_right)
    path.lineTo(wall_top_right)
    path.lineTo(wall_bot_right)
    path.lineTo(wall_bot_left)
    path.lineTo(wall_top_left)
    path.lineTo(roof_left)
    p.setPen(QPen(c, linew, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.end()
    return QIcon(pix)

def make_zoom_icon(sign: str, color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen_width = max(2, size // 10)
    pen = QPen(QColor(color), pen_width, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    center = size / 2
    length = size * 0.15
    # Use QPointF for all coordinates!
    if sign == "+":
        p.drawLine(QPointF(center - length, center), QPointF(center + length, center))
        p.drawLine(QPointF(center, center - length), QPointF(center, center + length))
    else:
        p.drawLine(QPointF(center - length, center), QPointF(center + length, center))
    p.end()
    return QIcon(pix)

def make_fullscreen_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color), max(2, size//10), Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    gap = size * 0.22
    span = size * 0.13
    # Use QPointF for all coordinates!
    p.drawLine(QPointF(gap, gap+span),      QPointF(gap, gap))
    p.drawLine(QPointF(gap, gap),           QPointF(gap+span, gap))
    p.drawLine(QPointF(size-gap, gap+span), QPointF(size-gap, gap))
    p.drawLine(QPointF(size-gap, gap),      QPointF(size-gap-span, gap))
    p.drawLine(QPointF(gap, size-gap-span), QPointF(gap, size-gap))
    p.drawLine(QPointF(gap, size-gap),      QPointF(gap+span, size-gap))
    p.drawLine(QPointF(size-gap, size-gap-span), QPointF(size-gap, size-gap))
    p.drawLine(QPointF(size-gap, size-gap),      QPointF(size-gap-span, size-gap))
    p.end()
    return QIcon(pix)
    
def make_java_icon(color: str, size: int = 48) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    accent = QColor(color)
    pen = QPen(accent, int(size * 0.08), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    # Draw steam
    for i, offset in enumerate([-0.15, 0, 0.15]):
        path = QPainterPath()
        cx = size * 0.5 + offset * size
        top = size * 0.16 + i * size * 0.05
        path.moveTo(cx, top)
        path.cubicTo(cx + size*0.08, top + size*0.04, cx - size*0.08, top + size*0.10, cx, top + size*0.18)
        p.drawPath(path)

    # Draw cup
    cup_rect = QRectF(size*0.20, size*0.53, size*0.60, size*0.23)
    body_rect = QRectF(size*0.28, size*0.63, size*0.44, size*0.18)
    saucer_rect = QRectF(size*0.17, size*0.78, size*0.66, size*0.14)
    handle_rect = QRectF(size*0.68, size*0.62, size*0.18, size*0.22)
    # All angles for drawArc must be int
    p.drawArc(QRectF(int(cup_rect.x()), int(cup_rect.y()), int(cup_rect.width()), int(cup_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(body_rect.x()), int(body_rect.y()), int(body_rect.width()), int(body_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(saucer_rect.x()), int(saucer_rect.y()), int(saucer_rect.width()), int(saucer_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(handle_rect.x()), int(handle_rect.y()), int(handle_rect.width()), int(handle_rect.height())), int(16*40), int(16*175))

    p.end()
    return QIcon(pm)

def make_nuke_icon(hex_color: str, size: int) -> QIcon:
    """
    Returns a QIcon of the classic nuclear/radiation symbol,
    using the given accent color (hex, e.g. "#34C759") and black for the blades.
    All coordinates are cast to int to avoid PyQt5 TypeError.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    accent = QColor(hex_color)
    black = QColor("#111412")
    cx, cy = size / 2, size / 2
    radius = size * 0.48

    # Outer circle (accent with black border)
    border_width = int(size * 0.06)
    p.setPen(QPen(black, border_width))
    p.setBrush(QBrush(accent))
    p.drawEllipse(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius))

    # Inner hub (black)
    hub_r = size * 0.14
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(black))
    p.drawEllipse(int(cx - hub_r), int(cy - hub_r), int(2 * hub_r), int(2 * hub_r))

    # Blades (black)
    p.setBrush(QBrush(black))
    for i in range(3):
        p.save()
        p.translate(cx, cy)
        p.rotate(i * 120)
        path = [
            QPointF(0, -hub_r * 1.35),
            QPointF(size * 0.18, -size * 0.35),
            QPointF(0, -radius),
            QPointF(-size * 0.18, -size * 0.35)
        ]
        p.drawPolygon(*path)
        p.restore()

    p.end()
    return QIcon(pm)
    
# Pick engine based on your Tor/onion mode
SEARCH_ACTION = (
    DUCK_LITE_ONION if USE_ONION_SEARCH else DUCK_LITE_HTTPS
)

# --- Homepage (green, minimal, ported from fixed2) ---
HOMEPAGE = f"""<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Darkelf Browser — Shadow, Private, Hardened</title>
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline' 'unsafe-eval';
                 img-src 'self' data:; connect-src 'none'; font-src 'none';
                 form-action https://duckduckgo.com/lite/ https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/lite/;
                 base-uri 'none'">
  <style>
    :root{{--bg:#0a0b10;--accent:#34C759;--border:rgba(255,255,255,.10);--input-bg:#12141b;--input-text:#e5e7eb;}}
    *{{box-sizing:border-box}} html,body{{height:100%}}
    body{{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
      background:radial-gradient(1200px 600px at 20% -10%,rgba(4,168,200,.25),transparent 60%),
                 radial-gradient(1000px 600px at 120% 10%,rgba(52,199,89,.18),transparent 60%),var(--bg);
      color:#eef2f6;display:flex;flex-direction:column;justify-content:center;align-items:center;}}
    .brand{{display:flex;gap:10px;align-items:center;justify-content:center;font-weight:700;font-size:2rem;}}
    .brand i{{color:var(--accent);}}
    .tagline{{font-size:.95rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#cfd8e3;margin:6px 0 20px;}}
    .search-wrap{{display:flex;align-items:stretch;gap:10px;justify-content:center;}}
    .search-wrap input{{height:48px;padding:0 16px;width:min(720px,92vw);border-radius:12px;border:1px solid var(--border);background:var(--input-bg);color:var(--input-text);font-size:16px;outline:none;}}
    .search-wrap input::placeholder{{color:#9aa3ad;}}
    .search-wrap input:focus{{box-shadow:0 0 0 3px rgba(52,199,89,.30);border-color:transparent;}}
    .search-wrap button{{width:48px;height:48px;border-radius:12px;border:none;cursor:pointer;font-size:20px;display:inline-flex;align-items:center;justify-content:center;color:#fff;background:var(--accent);}}
    .search-wrap button:focus {{outline: 2px solid #34C759;}}
  </style>
</head>
<body>
  <div class="brand">
    <svg width="32" height="32" style="vertical-align:middle;"><ellipse cx="16" cy="16" rx="13" ry="14" fill="#111b13" stroke="#34C759" stroke-width="2"/></svg>
    <span style="color:#34C759">Darkelf Browser</span>
  </div>
  <div class="tagline">SHADOW • PRIVATE • HARDENED</div>
  <form class="search-wrap"
        action="{SEARCH_ACTION}"
        method="get" role="search" aria-label="Search DuckDuckGo">
    <input type="text" name="q" placeholder="Search DuckDuckGo" aria-label="Search query" />
    <button type="submit" aria-label="Search">
      <svg viewBox="0 0 24 24" aria-hidden="true" width="22" height="22"><path d="M10 3a7 7 0 1 1 0 14 7 7 0 0 1 0-14zm0 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm9.707 12.293l-3.387-3.387a1 1 0 0 0-1.414 1.414l3.387 3.387a1 1 0 0 0 1.414-1.414z"/></svg>
    </button>
  </form>
</body></html>
"""

# --- Paste your full ADBLOCK_JS from your Shell Copy 2 here ---
ADBLOCK_JS = """
(function(){
  if(window.__darkelf_adblock_injected) return;
  window.__darkelf_adblock_injected = true;
  let trackersBlocked = 0;
  // Extended YouTube-specific ad/tracker patterns
  const trackerPatterns = [
    /doubleclick\.net/i, /adservice\.google\.com/i, /googlesyndication\.com/i,
    /google-analytics\.com/i, /googletagmanager\.com/i,
    /facebook\.net/i, /facebook\.com.*\/tr\?/i,
    /pixel.*\.io/i, /adsafeprotected\.com/i,
    /hotjar\.com/i, /mixpanel\.com/i, /segment\.com/i,
    /taboola\.com/i, /outbrain\.com/i, /ads-twitter\.com/i, /scorecardresearch\.com/i,
    /1x1(\.png|\.gif|\.jpg)/i,
    /\/pixel(\.gif|\.png|\.jpg)/i,
    /\/track(\.gif|\.png|\.jpg)/i,
    /adroll\.com/i, /adnxs\.com/i, /ads\.yahoo\.com/i, /criteo\.com/i, /pubmatic\.com/i, /rubiconproject\.com/i,
    /openx\.net/i, /yieldmo\.com/i, /mathtag\.com/i, /quantserve\.com/i, /scorecardresearch\.com/i,
    // Extra for YouTube:
    /youtube\.com\/(pagead|ptracking|api\/stats\/ads|get_midroll_info)/i,
    /googlevideo\.com.*[?&](oad|ctier|adformat|ad_status|ad_break|yt_ad|nva_ad|nva_adid|nva_adtype|nva_adformat)=/i
  ];

  function updateBadge() {
    try {
      let e = document.getElementById('trackers-badge');
      if (e) {
        e.textContent = trackersBlocked;
        e.style.display = trackersBlocked > 0 ? 'inline-block' : 'none';
      }
    } catch(_) {}
  }

  // Block all suspicious <img>, <iframe>, <script> at creation time
  const origCreateElement = document.createElement;
  document.createElement = function(tag) {
    let el = origCreateElement.call(this, tag);
    if(['img','iframe','script','video','audio','source'].includes(tag.toLowerCase())) {
      let origSetAttribute = el.setAttribute;
      el.setAttribute = function(name, value) {
        if((name === 'src' || name==='data-src') && value) {
          for(let patt of trackerPatterns) {
            if(patt.test(value)) {
              trackersBlocked++; updateBadge(); return;
            }
          }
        }
        return origSetAttribute.apply(this, arguments);
      };
    }
    if(tag.toLowerCase() === 'iframe' || tag.toLowerCase() === 'img') {
      setTimeout(function(){
        if((el.width<=1&&el.height<=1) || (el.style && (parseInt(el.style.width)<=1&&parseInt(el.style.height)<=1))) {
          el.remove(); trackersBlocked++; updateBadge();
        }
      },100);
    }
    return el;
  };

  // Block fetch/XHR to tracker/ad domains
  let origFetch = window.fetch;
  window.fetch = function() {
    let url = arguments[0];
    if(typeof url==='string' && trackerPatterns.some(patt=>patt.test(url))) {
      trackersBlocked++; updateBadge(); return new Promise(()=>{});
    }
    return origFetch.apply(this, arguments);
  };
  let origXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method,url){
    if(typeof url==='string' && trackerPatterns.some(patt=>patt.test(url))) {
      trackersBlocked++; updateBadge(); return;
    }
    return origXHROpen.apply(this,arguments);
  };

  // Block <img> srcs via constructor/assignment
  const origImg = window.Image;
  window.Image = function(...args){
    const img = new origImg(...args);
    const origSetAttribute = img.setAttribute;
    img.setAttribute = function(name,value){
      if((name==='src' || name==='data-src') && value){
        for(let patt of trackerPatterns){
          if(patt.test(value)){ trackersBlocked++; updateBadge(); return; }
        }
      }
      return origSetAttribute.apply(this,arguments);
    };
    return img;
  };

  // Remove existing invisible trackers on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function(){
    let imgs = Array.from(document.images);
    for(let img of imgs){
      if((img.width<=1&&img.height<=1) || trackerPatterns.some(patt=>patt.test(img.src))){
        img.remove(); trackersBlocked++;
      }
    }
    updateBadge();
  });

  // --- YouTube-specific ad removal (UI AND network) ---
  const isYouTube = location.hostname.includes('youtube.com') || location.hostname.includes('youtu.be');
  if(isYouTube){
    setInterval(()=>{
      // Hide ad containers and overlays, increment counter if hidden
      document.querySelectorAll('.ad-showing,ytd-ad-slot-renderer,.ytp-ad-module,.ytp-ad-player-overlay,.ytp-ad-overlay-close-button,.ytp-ad-image-overlay,.ytp-ad-text-overlay,.video-ads').forEach(e=>{
        if(e && e.style.display !== "none") {
          e.style.display = "none";
          trackersBlocked++; updateBadge();
        }
      });
      let skip=document.querySelector('.ytp-ad-skip-button,.ytp-ad-skip-button-modern');
      if(skip) { skip.click(); trackersBlocked++; updateBadge(); }
      // Remove <div> overlays/ads
      document.querySelectorAll('div[id^="ad-"],div[class*="ad-"],div[class*="ytp-ad"]').forEach(e=>{
        if(e && e.style.display !== "none") {
          e.style.display = "none";
          trackersBlocked++; updateBadge();
        }
      });
      // --- NEW: Force skip video ads (fixes white screen with ad audio) ---
      var video = document.querySelector('video');
      var adOverlay = document.querySelector('.ad-showing');
      // Only try to skip if ad overlay is present and video is ad (whiteout fix)
      if (video && adOverlay) {
        if (typeof video.duration === "number" && !isNaN(video.duration)) {
          if (!video.ended && (video.currentTime < video.duration - 0.1)) {
            video.currentTime = video.duration;
            // Also try to trigger the end of ad event
            video.dispatchEvent(new Event('ended'));
            trackersBlocked++; updateBadge();
          }
        }
      }
    }, 800);
  }

  // Patch ytInitialPlayerResponse and JSON.parse to strip playerAds/adPlacements/adSlots
  if(isYouTube){
    try{
      Object.defineProperty(window, 'ytInitialPlayerResponse', {
        configurable: true,
        get: function(){ return this.__yipr; },
        set: function(v){
          try{
            if (v) {
              if (v.playerAds) v.playerAds = [];
              if (v.adPlacements) delete v.adPlacements;
              if (v.adSlots) delete v.adSlots;
            }
          }catch(_){}
          this.__yipr = v;
        }
      });
      const _parse = JSON.parse;
      JSON.parse = function(s, reviver){
        const o = _parse(s, reviver);
        try{
          if (o) {
            if (o.playerAds) o.playerAds = [];
            if (o.adPlacements) delete o.adPlacements;
            if (o.adSlots) delete o.adSlots;
          }
        }catch(_){}
        return o;
      };
    }catch(e){}
  }

})();
"""

FONT_FP_PROTECTION_JS = """
(function() {
    // --- Only spoof on non-YouTube domains! ---
    var host = window.location.hostname || "";
    if (
        host.endsWith(".youtube.com") ||
        host === "youtube.com" ||
        host.endsWith(".ytimg.com")
    ) {
        console.warn("[Darkelf] Skipping font fingerprint spoofing on YouTube.");
        return;
    }

    // Add slight random noise to canvas font metrics (width, height)
    const randomize = (val, factor = 0.07) => val + (Math.random() * val * factor - val * factor / 2);

    // Patch measureText for all canvases
    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {
        const metrics = origMeasureText.call(this, text);
        if (metrics && typeof metrics.width === "number") {
            metrics.width = randomize(metrics.width, 0.12);
        }
        for (let k in metrics) {
            if (typeof metrics[k] === "number") {
                metrics[k] = randomize(metrics[k], 0.11);
            }
        }
        return metrics;
    };

    // Patch getComputedStyle to always return the same font-family
    const origGetComputedStyle = window.getComputedStyle;
    window.getComputedStyle = function(...args) {
        const style = origGetComputedStyle.apply(this, args);
        return new Proxy(style, {
            get(target, prop) {
                if (typeof prop === 'string' && prop.toLowerCase().includes('font')) {
                    return '16px "Arial"';
                }
                return target[prop];
            }
        });
    };

    // Patch offsetWidth/offsetHeight for fingerprinting
    const offsetNoise = () => Math.floor(3500 + Math.random() * 800);
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
        get: function () { return offsetNoise(); },
        configurable: true
    });
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
        get: function () { return offsetNoise(); },
        configurable: true
    });

    if (document.fonts) {
        document.fonts.query = function() { return Promise.resolve([]); };
    }
})();
"""

def install_font_fp_protection(page):
    script = QWebEngineScript()
    script.setSourceCode(FONT_FP_PROTECTION_JS)
    script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    script.setRunsOnSubFrames(True)
    script.setWorldId(QWebEngineScript.MainWorld)
    page.profile().scripts().insert(script)
    
def inject_adblock_badge_always(page):
    badge_js = """
    (function(){
      var badge = document.getElementById('trackers-badge');
      if (!badge) {
        badge = document.createElement('div');
        badge.id = 'trackers-badge';
        badge.textContent = '0';
        badge.style = "position:fixed;top:9px;right:19px;z-index:2147483647;background:#121722cc;color:#ffd700;font-size:15px;font-family:sans-serif;padding:3px 13px;border-radius:999px;border:1.7px solid #f39c12;box-shadow:0 2px 6px #0004";
        document.body.appendChild(badge);
      }
      window.__darkelf_adblock_injected = true;
    })();
    """
    script = QWebEngineScript()
    script.setSourceCode(badge_js)
    script.setInjectionPoint(QWebEngineScript.DocumentReady)
    script.setRunsOnSubFrames(False)
    script.setWorldId(QWebEngineScript.MainWorld)
    page.profile().scripts().insert(script)
    
class _DarkelfLetterboxMixin:
    def inject_darkelf_letterboxing(self, skip_youtube=True):
        # Letterboxing JS as you wrote it
        script = r"""
        (() => {
          const W = 1000, H = 1000, OUT_W = W + 16, OUT_H = H + 88;
          const ro = (o, k, v) => { try { Object.defineProperty(o, k, { get: () => v, configurable: true }); } catch(_){} };

          ro(window, "innerWidth",  W);
          ro(window, "innerHeight", H);
          ro(window, "outerWidth",  OUT_W);
          ro(window, "outerHeight", OUT_H);
          ro(window, "devicePixelRatio", 1);

          ro(screen, "width", W); ro(screen, "height", H);
          ro(screen, "availWidth", W); ro(screen, "availHeight", H - 20);
          ro(screen, "availTop", 0); ro(screen, "availLeft", 0);
          ro(screen, "colorDepth", 24);
          ro(window, "screenX", 0); ro(window, "screenY", 0);

          if (window.visualViewport) {
            try {
              ro(window.visualViewport, "width",  W);
              ro(window.visualViewport, "height", H);
              ro(window.visualViewport, "scale",  1);
              ro(window.visualViewport, "offsetTop", 0);
              ro(window.visualViewport, "offsetLeft", 0);
            } catch(_){}
          }

          const origMM = window.matchMedia;
          window.matchMedia = function(q) {
            try {
              const m = String(q).toLowerCase();
              const yes = (
                /\(min\-width:\s*(\d+)px\)/.test(m) ? W >= +RegExp.$1 :
                /\(max\-width:\s*(\d+)px\)/.test(m) ? W <= +RegExp.$1 :
                /\(min\-height:\s*(\d+)px\)/.test(m) ? H >= +RegExp.$1 :
                /\(max\-height:\s*(\d+)px\)/.test(m) ? H <= +RegExp.$1 :
                false
              );
              return { matches: yes, media: q, onchange: null,
                       addListener: ()=>{}, removeListener: ()=>{},
                       addEventListener: ()=>{}, removeEventListener: ()=>{},
                       dispatchEvent: ()=>false };
            } catch(_) { return origMM.apply(this, arguments); }
          };

          window.addEventListener("resize", ev => {
            try { ev.stopImmediatePropagation?.(); ev.preventDefault?.(); } catch(_){}
          }, true);
        })();
        """
        # Wrap in a check to skip YouTube
        if skip_youtube:
            script = f"""
            (function(){{
                var host = window.location.hostname || "";
                if (
                    host.endsWith(".youtube.com") ||
                    host === "youtube.com" ||
                    host.endsWith(".googlevideo.com") ||
                    host === "googlevideo.com" ||
                    host.endsWith(".youtu.be") ||
                    host === "youtu.be"
                ) {{
                    return;
                }}
                {script}
            }})();
            """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36"
)
FIREFOX_TOR_UA = (
    "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0"
)

FIREFOX_UA_JS = f"""
(function() {{
    var host = window.location.hostname || "";
    if (
        host.endsWith(".youtube.com") ||
        host === "youtube.com" ||
        host.endsWith(".googlevideo.com") ||
        host === "googlevideo.com" ||
        host.endsWith(".youtu.be") ||
        host === "youtu.be"
    ) {{
        return;
    }}
    Object.defineProperty(navigator, 'userAgent', {{
        get: function() {{ return "{FIREFOX_TOR_UA}"; }},
        configurable: true
    }});
    Object.defineProperty(navigator, 'platform', {{
        get: function() {{ return "Win32"; }},
        configurable: true
    }});
    Object.defineProperty(navigator, 'appVersion', {{
        get: function() {{ return "{FIREFOX_TOR_UA}"; }},
        configurable: true
    }});
    Object.defineProperty(navigator, "vendor", {{
        get: function() {{ return ""; }}, // Firefox default: empty string
        configurable: true
    }});
    // Optional: spoof more fingerprinting APIs here!
}})();
"""

class HardenedWebPage(QWebEnginePage, _DarkelfLetterboxMixin):
    def __init__(self, parent=None, profile=None):
        view = parent  # just to be explicit

        # Prefer a real profile if available; fall back to default where possible
        if profile is None:
            try:
                profile = QWebEngineProfile.defaultProfile()
            except AttributeError:
                profile = None

        # Construct the base page in a version-tolerant way
        if profile is not None:
            try:
                # Newer Qt: QWebEnginePage(profile, parent)
                super().__init__(profile, view)
            except TypeError:
                # Older Qt: only (parent)
                super().__init__(view)
        else:
            super().__init__(view)

        self._parent_view = view

        # Attach one interceptor per profile (guard if profile unavailable)
        try:
            prof = self.profile()
        except AttributeError:
            prof = None

        if prof is not None:
            if not hasattr(prof, "_darkelf_interceptor"):
                interceptor = DarkelfInterceptor(PATTERNS)
                prof.setUrlRequestInterceptor(interceptor)
                prof._darkelf_interceptor = interceptor
            else:
                interceptor = prof._darkelf_interceptor
            self.interceptor = interceptor
        else:
            self.interceptor = None  # or raise/log if you require it

        self._canvas_seed = get_or_create_canvas_seed()
        self._inject_all_spoofs()

    def userAgentForUrl(self, url):
        host = url.host().lower()
        if (
            "youtube.com" in host or
            "youtu.be" in host or
            "googlevideo.com" in host
        ):
            return CHROMIUM_UA
        return FIREFOX_TOR_UA
        
    def _inject_all_spoofs(self):
        self.profile().scripts().clear()
        self.inject_script(SMART_UA_SPOOF_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(VENDOR_SMART_SPOOF_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(IFRAME_VENDOR_SMART_SPOOF_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(YOUTUBE_AD_NUKE_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(ADBLOCK_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(WEBGL_VENDOR_SPOOF_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(FONT_FP_PROTECTION_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_script(TOOLBAR_PADDING_FIX_JS, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.inject_darkelf_letterboxing(skip_youtube=True)
        self.inject_script(get_canvas_js(self._canvas_seed, rotate_minutes=30), injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        self.block_webrtc_sdp_logging()
        self.block_font_fingerprinting()
        self.spoof_webgl_tor_style()
        inject_adblock_badge_always(self)

    def inject_script(self, script_source, injection_point=None, subframes=True):
        script_obj = QWebEngineScript()
        script_obj.setSourceCode(script_source)
        if injection_point is None:
            injection_point = QWebEngineScript.DocumentCreation
        script_obj.setInjectionPoint(injection_point)
        script_obj.setRunsOnSubFrames(subframes)
        script_obj.setWorldId(QWebEngineScript.MainWorld)
        self.profile().scripts().insert(script_obj)

    def block_webrtc_sdp_logging(self):
        script = """
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
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

    def block_font_fingerprinting(self):
        script = """
        (function() {
            const isOnion = window.location.hostname.endsWith(".onion");
            if (isOnion) {
                console.warn("[DarkelfAI] .onion site detected — skipping font spoofing.");
                return;
            }
            const randomize = (val, factor = 0.03) => val + (Math.random() * val * factor);
            const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
            CanvasRenderingContext2D.prototype.measureText = function(text) {
                const metrics = originalMeasureText.call(this, text);
                metrics.width = randomize(metrics.width);
                return metrics;
            };
            const originalGetComputedStyle = window.getComputedStyle;
            window.getComputedStyle = function(...args) {
                const style = originalGetComputedStyle.apply(this, args);
                return new Proxy(style, {
                    get(target, prop) {
                        if (typeof prop === 'string' && prop.toLowerCase().includes('font')) {
                            return '16px "Noto Sans"';
                        }
                        return target[prop];
                    }
                });
            };
            const offsetNoise = () => Math.floor(90 + Math.random() * 10);
            Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
                get: function () { return offsetNoise(); },
                configurable: true
            });
            Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
                get: function () { return offsetNoise(); },
                configurable: true
            });
            console.log('[DarkelfAI] Soft font fingerprinting vectors spoofed.');
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

    def spoof_webgl_tor_style(self):
        script = """
        class WebGLAlignmentDummyClass {};
        (function(){
          var spoofed_vendor = "Intel Inc.";
          var spoofed_renderer = "Intel Iris OpenGL Engine";
          var getParameter = WebGLRenderingContext.prototype.getParameter;
          WebGLRenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return spoofed_vendor;
            if (param === 37446) return spoofed_renderer;
            return getParameter.apply(this, arguments);
          };
          if (window.WebGL2RenderingContext) {
            var getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {
              if (param === 37445) return spoofed_vendor;
              if (param === 37446) return spoofed_renderer;
              return getParameter2.apply(this, arguments);
            };
          }
          function patchBufferMethod(proto, name) {
            var orig = proto[name];
            proto[name] = function() {
              var res = orig.apply(this, arguments);
              if (res && res.length) {
                for (var i=0; i<res.length; i+=31) res[i] = res[i] ^ 31;
              }
              return res;
            };
          }
          patchBufferMethod(WebGLRenderingContext.prototype, 'readPixels');
          if (window.WebGL2RenderingContext)
            patchBufferMethod(WebGL2RenderingContext.prototype, 'readPixels');
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    # IMPORTANT: reuse the same profile so the profile-level script applies
    def createWindow(self, _type):
        # Try to locate a tabbed main window from the current view, if any
        parent_view = getattr(self, "_parent_view", None)
        main_window = parent_view.window() if parent_view else None
        has_tabs = bool(main_window and hasattr(main_window, "_add_tab") and hasattr(main_window, "tabs"))

        # Create a new view; parent it so it stays alive
        view_parent = main_window if has_tabs else parent_view
        view = QWebEngineView(view_parent)

        # Create the page, reusing the profile if our constructor supports it
        try:
            page = HardenedWebPage(view, self.profile())  # preferred path
        except TypeError:
            page = HardenedWebPage(view)

        # Wire things up
        view.setPage(page)
        page._parent_view = view  # ensure downstream calls can find their view/window

        # If we have a tabbed host, add as a new tab; otherwise just show the window
        if has_tabs:
            idx = main_window.tabs.addTab(view, "New Tab")
            main_window.tabs.setCurrentIndex(idx)
        else:
            view.show()

        # Keep a reference so the view/page aren't GC'd
        if not hasattr(self, "_spawned_views"):
            self._spawned_views = []
        self._spawned_views.append(view)

        return page

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        if url.scheme() == "file":
            QMessageBox.warning(None, "Navigation blocked", "File URLs are blocked for privacy.")
            return False
        return super().acceptNavigationRequest(url, navtype, isMainFrame)

class DarkelfBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self._set_tab_style()
        self._configure_tabbar_small()            # << compact tabs + ellipsis
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(lambda idx: self._hook_tab_switch())

        self.toolbar = self._make_toolbar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self._add_tab(home=True)

        self.tor_network_enabled = True
        self.init_tor()

    def _make_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(22, 22))  # Slightly smaller for compact fit

        # Navigation
        self.back_action = QAction(make_nav_arrow_icon("left", "#34C759", 22), "Back", self)
        self.fwd_action = QAction(make_nav_arrow_icon("right", "#34C759", 22), "Forward", self)
        self.reload_action = QAction(make_reload_icon("#34C759", 22), "Reload", self)
        self.home_action = QAction(make_house_icon("#34C759", 22), "Home", self)
        self.zoom_in_action = QAction(make_zoom_icon("+", "#34C759", 20), "Zoom In", self)
        self.zoom_out_action = QAction(make_zoom_icon("-", "#34C759", 20), "Zoom Out", self)
        self.full_action = QAction(make_fullscreen_icon("#34C759", 20), "Full Screen", self)
        self.nuke_action = QAction(make_nuke_icon("#ff2a2a", 18), "Nuke", self)
        self.nuke_action.triggered.connect(self.nuke_all_data)
        self.java_action = QAction(make_java_icon("#f89820", 18), "JavaScript", self)
        self.addtab_action = QAction(make_icon("#34C759", 20), "New Tab", self)

        # Connect navigation actions
        self.back_action.triggered.connect(self.go_back)
        self.fwd_action.triggered.connect(self.go_fwd)
        self.reload_action.triggered.connect(self.reload)
        self.home_action.triggered.connect(self.go_home)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.full_action.triggered.connect(self.toggle_fullscreen)
        self.addtab_action.triggered.connect(lambda: self._add_tab(home=True))

        tb.addAction(self.back_action)
        tb.addAction(self.fwd_action)
        tb.addAction(self.reload_action)
        tb.addAction(self.home_action)
        tb.addSeparator()

        self.addr = QLineEdit()
        self.addr.setPlaceholderText("Search or enter URL")
        self.addr.returnPressed.connect(self.on_url_entered)
        tb.addWidget(self.addr)
        tb.addSeparator()

        tb.addAction(self.zoom_out_action)
        tb.addAction(self.zoom_in_action)
        tb.addAction(self.full_action)
        tb.addAction(self.addtab_action)

        tb.addSeparator()
        tb.addAction(self.nuke_action)  # Nuke button: wipes all browser data

        # JavaScript toggle button as a checkable action
        self.java_action.setCheckable(True)
        self.java_action.setChecked(True)
        self.java_action.setToolTip("Enable/Disable JavaScript globally")
        tb.addAction(self.java_action)

        def update_js_icon():
            enabled = self.java_action.isChecked()
            color = "#f89820" if enabled else "#bbbbbb"
            self.java_action.setIcon(make_java_icon(color, 18))
            self.java_action.setText("JavaScript" if enabled else "JS Off")
            self.toggle_javascript()
        self.java_action.triggered.connect(update_js_icon)

        tb.addSeparator()
        return tb

    # --- compact tab bar + ellipsis -----------------------------------------
    def _configure_tabbar_small(self):
        bar = self.tabs.tabBar()
        bar.setExpanding(False)               # don't stretch tabs across bar
        bar.setMovable(True)
        bar.setElideMode(Qt.ElideRight)       # long text -> …
        bar.setIconSize(QSize(16, 16))        # small favicon
        bar.setUsesScrollButtons(True)
        # keep tabs short and capped in width so many fit
        bar.setStyleSheet("""
            QTabBar::tab { height: 22px; padding: 2px 8px; max-width: 140px; }
        """)

    def _set_tab_style(self):
        self.tabs.setStyleSheet("""
        QTabWidget::pane { border: 0; }
        QTabBar { qproperty-drawBase: 0; }
        QTabBar::tab {
            background: #222;
            color: #e5e7eb;
            padding: 2px 8px;
            margin: 2px 3px;
            height: 22px;                /* compact height */
            border-radius: 8px;
        }
        QTabBar::tab:selected { background: #34C759; color: #0a0b10; }
        QTabBar::tab:hover    { background: #2a2e34; }
        """)

    # --- short labels like "YouTube", "BBC" ---------------------------------
    @staticmethod
    def _short_label_from_qurl(qurl):
        try:
            host = qurl.host().lower() if hasattr(qurl, "host") else ""
        except Exception:
            host = ""
        if not host:
            return "Home"

        aliases = {
            "youtube.com": "YouTube", "www.youtube.com": "YouTube", "youtu.be": "YouTube",
            "bbc.com": "BBC", "www.bbc.com": "BBC", "bbc.co.uk": "BBC", "www.bbc.co.uk": "BBC",
            "github.com": "GitHub",
            "twitter.com": "Twitter", "x.com": "Twitter",
            "reddit.com": "Reddit", "www.reddit.com": "Reddit",
            "duckduckgo.com": "DuckDuckGo",
        }
        if host in aliases:
            return aliases[host]
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        base = parts[-2] if len(parts) >= 2 else host
        return base.capitalize()

    def _should_use_chrome_ua(self, url):
        if not url:
            return False
        host = QUrl(url).host().lower() if isinstance(url, str) else url.host().lower()
        return any(x in host for x in ["youtube.com", "googlevideo.com", "youtu.be"])

    def _update_global_ua_for_tab(self, url):
        profile = QWebEngineProfile.defaultProfile()
        if self._should_use_chrome_ua(url):
            profile.setHttpUserAgent(CHROME_UA)
        else:
            profile.setHttpUserAgent(FIREFOX_TOR_UA)

    def _hook_tab_url_change(self, view):
        def sync_ua(url):
            self._update_global_ua_for_tab(url.toString())
        view.urlChanged.connect(sync_ua)
        if view.url().isValid():
            self._update_global_ua_for_tab(view.url().toString())

    def _hook_tab_switch(self):
        idx = self.tabs.currentIndex()
        view = self.tabs.widget(idx)
        if isinstance(view, QWebEngineView):
            url = view.url().toString()
            self._update_global_ua_for_tab(url)

    def _add_tab(self, url="", home=False):
        view = QWebEngineView()
        page = HardenedWebPage(view)
        view.setPage(page)
        install_canvas_protection_on(page)

        # initial short label
        initial_label = "Home" if home else (self._short_label_from_qurl(QUrl(url)) if url else "New")
        idx = self.tabs.addTab(view, initial_label)
        self.tabs.setCurrentIndex(idx)

        # keep UA synced
        self._hook_tab_url_change(view)

        # relabel tab from URL (short label), and set favicon
        def relabel_from_url(qurl, view=view):
            i = self.tabs.indexOf(view)
            if i != -1:
                self.tabs.setTabText(i, self._short_label_from_qurl(qurl))
        view.urlChanged.connect(relabel_from_url)

        def set_icon(icon, view=view):
            i = self.tabs.indexOf(view)
            if i != -1:
                self.tabs.setTabIcon(i, icon)
        view.iconChanged.connect(set_icon)

        # REMOVE full-title labeling so long headlines don't appear on tabs
        # def update_tab_title(new_title):
        #     pass
        # page.titleChanged.connect(update_tab_title)

        # URL bar sync
        view.urlChanged.connect(self._sync_urlbar)
        view.loadFinished.connect(lambda ok: self._sync_urlbar(view.url()))

        if home:
            view.setHtml(HOMEPAGE)
        else:
            view.load(QUrl(url or "https://duckduckgo.com/lite/"))
            
    # ---- Canvas seed rotation (call when you want a new fingerprint) ----
    def rotate_canvas_seed_all_tabs(self):
        new_seed = secrets.token_hex(16)
        js = (
            "try{"
            "window.__darkelf_canvas_set_seed('%s');"
            "window.__darkelf_canvas_force_rotate();"
            "}catch(e){}"
        ) % new_seed

        for i in range(self.tabs.count()):
            v = self.tabs.widget(i)
            # If you have PySide6/PyQt5 imports, QWebEngineView is already in scope
            if isinstance(v, QWebEngineView):
                v.page().runJavaScript(js)

     # replace your close_tab with this
    def close_tab(self, idx):
        # get the widget for this tab
        w = self.tabs.widget(idx)

        if isinstance(w, QWebEngineView):
            try:
                # try to pause/stop via JS (polite stop)
                w.page().runJavaScript(
                    "document.querySelectorAll('video,audio').forEach(m=>{try{m.pause(); m.src='';}catch(e){}})"
                )
            except Exception:
                pass

            # hard stop: unload the page so Chromium media process dies
            w.page().setAudioMuted(True)
            w.page().setUrl(QUrl("about:blank"))
            w.page().deleteLater()
            w.deleteLater()

        # remove the tab UI
        self.tabs.removeTab(idx)

        # ensure you always have at least one tab open (optional, matches your style)
        if self.tabs.count() == 0:
            self._add_tab(home=True)

    def _close_tab_current(self):
        self.close_tab(self.tabs.currentIndex())

    def current_view(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def go_back(self):
        v = self.current_view()
        if v: v.back()
    def go_fwd(self):
        v = self.current_view()
        if v: v.forward()
    def reload(self):
        v = self.current_view()
        if v: v.reload()
    def go_home(self):
        v = self.current_view()
        if v: v.setHtml(HOMEPAGE)
    def zoom_in(self):
        v = self.current_view()
        if v: v.setZoomFactor(v.zoomFactor() + 0.1)
    def zoom_out(self):
        v = self.current_view()
        if v: v.setZoomFactor(v.zoomFactor() - 0.1)
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def on_url_entered(self):

        text = self.addr.text().strip()
        if not text:
            self._add_tab(home=True)
            return

        # Detect explicit scheme (http://, https://, ftp://, etc.)
        has_scheme = re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', text) is not None

        # Heuristics for domain/IP/localhost without scheme
        looks_like_domain = re.match(r'^[\w.-]+\.[A-Za-z]{2,}(/|$)', text) is not None
        looks_like_ip_or_local = re.match(r'^(localhost|(?:\d{1,3}\.){3}\d{1,3})(:\d+)?(/|$)?$', text) is not None

        if has_scheme:
            url = text
        elif looks_like_domain or looks_like_ip_or_local:
            url = "https://" + text
        else:
            # Treat as a search
            base = DUCK_LITE_ONION if USE_ONION_SEARCH else DUCK_LITE_HTTPS
            url = base + quote_plus(text)

        # Always open in a new tab
        self._add_tab(url=url)

    def _sync_urlbar(self, url=None):
        v = self.current_view()
        if not v: return
        u = v.url().toString() if url is None else url.toString()
        if u.startswith("data:text/html"):
            self.addr.setText("")
        else:
            self.addr.setText(u)
            
    def toggle_javascript(self):
        enabled = self.java_action.isChecked()
        settings = QWebEngineProfile.defaultProfile().settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, enabled)
        # Optionally reload all tabs
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            if isinstance(view, QWebEngineView):
                view.reload()
                
    def nuke_all_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Nuke",
            "This will erase ALL cookies, cache, and browsing history. Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            profile = QWebEngineProfile.defaultProfile()
            profile.clearHttpCache()
            profile.clearAllVisitedLinks()
            profile.cookieStore().deleteAllCookies()
            self.tabs.clear()
            self._add_tab(home=True)
            QMessageBox.information(self, "Nuke Complete", "All browser data has been wiped!")
            
    def init_tor(self):
        # start Tor if enabled, then try to route via QNetworkProxy + DNS env
        try:
            if getattr(self, "tor_network_enabled", False):
                self.start_tor()
                if self.is_tor_running():
                    self.configure_tor_proxy()
                    self.configure_tor_dns()
        except Exception as e:
            print("[Tor] init error:", e)

    def start_tor(self):
        try:
            if getattr(self, "tor_process", None):
                print("Tor is already running.")
                return

            tor_path = shutil.which("tor")
            if not tor_path or not os.path.exists(tor_path):
                QMessageBox.critical(self, "Tor Error", "Tor executable not found! Install it (e.g., 'brew install tor').")
                return

            # Prefer stem if available
            try:
                import stem.process
                from stem.control import Controller
            except Exception as e:
                print("[Tor] python-stem not available:", e)
                # Fallback: try to launch tor detached (no controller auth)
                self.tor_process = subprocess.Popen(
                    [tor_path, "SocksPort", "9052", "ControlPort", "9053", "DNSPort", "9054",
                     "AutomapHostsOnResolve", "1", "VirtualAddrNetworkIPv4", "10.192.0.0/10",
                     "CircuitBuildTimeout", "10", "MaxCircuitDirtiness", "180", "NewCircuitPeriod", "120",
                     "NumEntryGuards", "2", "AvoidDiskWrites", "1", "CookieAuthentication", "1",
                     "DataDirectory", "/tmp/darkelf-tor-data", "Log", "notice stdout"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print("[Darkelf] Tor started (no stem controller).")
                return

            tor_config = {
                'SocksPort': '9052',
                'ControlPort': '9053',
                'DNSPort': '9054',
                'AutomapHostsOnResolve': '1',
                'VirtualAddrNetworkIPv4': '10.192.0.0/10',
                'CircuitBuildTimeout': '10',
                'MaxCircuitDirtiness': '180',
                'NewCircuitPeriod': '120',
                'NumEntryGuards': '2',
                'AvoidDiskWrites': '1',
                'CookieAuthentication': '1',
                'DataDirectory': '/tmp/darkelf-tor-data',
                'Log': 'notice stdout'
            }

            import stem.process
            from stem.control import Controller
            self.tor_process = stem.process.launch_tor_with_config(
                tor_cmd=tor_path, config=tor_config,
                init_msg_handler=lambda line: print("[tor]", line)
            )

            # Authenticate controller via cookie
            self.controller = Controller.from_port(port=9053)
            cookie_path = os.path.join('/tmp/darkelf-tor-data', 'control_auth_cookie')
            self.authenticate_cookie(self.controller, cookie_path=cookie_path)
            print("[Darkelf] Tor authenticated via cookie.")
            print("Tor started successfully.")

            try:
                self._stream_to_circ = {}  # stream_id -> circ_id
                self._circ_paths = {}      # circ_id -> [fp1, fp2, fp3...]
                self.controller.add_event_listener(self._on_circ_event, stem.control.EventType.CIRC)
                self.controller.add_event_listener(self._on_stream_event, stem.control.EventType.STREAM)
                print("[Darkelf] Tor event listeners registered.")
            except OSError as e:
                QMessageBox.critical(None, "Tor Error", f"Failed to start Tor: {e}")

        except Exception as e:
            print(f"[Darkelf] start_tor error: {e}")

    def authenticate_cookie(self, controller, cookie_path):
        try:
            with open(cookie_path, 'rb') as f:
                cookie = f.read()
            controller.authenticate(cookie)
        except Exception as e:
            print(f"[Darkelf] Tor cookie authentication failed: {e}")

    def is_tor_running(self):
        try:
            from stem.control import Controller
            with Controller.from_port(port=9053) as controller:
                controller.authenticate()
                print("Tor is running.")
                return True
        except Exception as e:
            print(f"Tor is not running: {e}")
            return False

    def configure_tor_proxy(self):
        # NOTE: QtWebEngine/Chromium primarily honors --proxy-server; this is a fallback.
        try:
            from PySide6.QtNetwork import QNetworkProxy
            proxy = QNetworkProxy(QNetworkProxy.Socks5Proxy, '127.0.0.1', 9052)
            QNetworkProxy.setApplicationProxy(proxy)
            print("Configured QNetworkProxy (SOCKS 127.0.0.1:9052).")
        except Exception as e:
            print("QNetworkProxy not available:", e)

    def configure_tor_dns(self):
        os.environ['DNSPORT'] = '127.0.0.1:9054'
        print("Configured Tor DNS env (DNSPORT=127.0.0.1:9054).")

    def stop_tor(self):
        try:
            if getattr(self, "tor_process", None):
                self.tor_process.terminate()
                self.tor_process = None
                print("Tor stopped.")
        except Exception:
            pass
            
    def _on_circ_event(self, event):
        print("[Tor] CIRC event:", event)

    def _on_stream_event(self, event):
        print("[Tor] STREAM event:", event)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0a0b10"))
    palette.setColor(QPalette.WindowText, QColor("#eafaf0"))
    palette.setColor(QPalette.Base, QColor("#12141b"))
    palette.setColor(QPalette.AlternateBase, QColor("#0f1114"))
    palette.setColor(QPalette.ToolTipBase, QColor("#eafaf0"))
    palette.setColor(QPalette.ToolTipText, QColor("#0a0b10"))
    palette.setColor(QPalette.Text, QColor("#eafaf0"))
    palette.setColor(QPalette.Button, QColor("#0f1114"))
    palette.setColor(QPalette.ButtonText, QColor("#eafaf0"))
    palette.setColor(QPalette.Highlight, QColor("#34C759"))
    palette.setColor(QPalette.HighlightedText, QColor("#0a0b10"))
    app.setPalette(palette)

    # ---- CONTEXT MENU STYLE ----
    app.setStyleSheet(app.styleSheet() + """
    QMenu {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #171b20, stop:1 #15191c);
        border: 1px solid #1a1f23;
        border-radius: 6px;
        padding: 6px;
    }
    QMenu::separator {
        height: 1px;
        background: #23292e;
        margin: 6px 8px;
    }
    QMenu::item {
        color: #e5e7eb;
        padding: 6px 16px;
        border-radius: 8px;
        background: transparent;
    }
    QMenu::item:selected, QMenu::item:hover {
        background: #34C759;
        color: #181a1b;
        font-weight: bold;
    }
    QMenu::item:disabled {
        color: #7f8c8d;
        background: transparent;
    }
    QMenu::icon { margin-right: 8px; }
    QMenu::item { cursor: pointer; }
    QToolTip {
        background: #161a1e;
        color: #e5e7eb;
        border: 1px solid #22292f;
        border-radius: 0px;
        padding: 6px 8px;
    }
    """)
    
    profile = QWebEngineProfile.defaultProfile()

    # Strict WebRTC lockdown
    webrtc_script = QWebEngineScript()
    webrtc_script.setName("webrtc_lockdown")
    webrtc_script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    webrtc_script.setRunsOnSubFrames(True)
    webrtc_script.setWorldId(QWebEngineScript.MainWorld)
    webrtc_script.setSourceCode(STRICT_WEBRTC_JS)
    profile.scripts().insert(webrtc_script)

    # YouTube ad nuker
    yt_script = QWebEngineScript()
    yt_script.setName("youtube_ad_nuke")
    yt_script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    yt_script.setRunsOnSubFrames(True)
    yt_script.setWorldId(QWebEngineScript.MainWorld)
    yt_script.setSourceCode(YOUTUBE_AD_NUKE_JS)
    profile.scripts().insert(yt_script)

    # ---- Toolbar padding fix ----
    toolbar_fix_script = QWebEngineScript()
    toolbar_fix_script.setName("toolbar_fix")
    toolbar_fix_script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    toolbar_fix_script.setRunsOnSubFrames(True)
    toolbar_fix_script.setWorldId(QWebEngineScript.MainWorld)
    toolbar_fix_script.setSourceCode(TOOLBAR_PADDING_FIX_JS)
    profile.scripts().insert(toolbar_fix_script)

    interceptor = DarkelfInterceptor(PATTERNS)
    profile.setUrlRequestInterceptor(interceptor)

    # Install network interceptor
    install_interceptor_once(profile)
    
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpUserAgent(FIREFOX_TOR_UA)
    
    w = DarkelfBrowser()
    w.show()
    sys.exit(app.exec_())

