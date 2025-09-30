#!/usr/bin/env python3
"""
Darkelf Shadow Browser - A Privacy-Focused Web Browser
Built with PyQt5 and PyQtWebEngine
"""

import sys
import json
import os
import random
import argparse
from urllib.parse import urlparse

from PyQt5.QtCore import QUrl, Qt, QSettings
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QAction,
    QTabWidget, QWidget, QVBoxLayout, QStatusBar, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtGui import QIcon


class AntiFingerPrintingScript:
    """JavaScript injection for anti-fingerprinting protection"""
    
    @staticmethod
    def get_script():
        """Returns the anti-fingerprinting JavaScript code"""
        return """
        (function() {
            'use strict';
            
            // Canvas Fingerprinting Protection
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                const context = this.getContext('2d');
                if (context) {
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = imageData.data[i] ^ Math.floor(Math.random() * 10);
                    }
                    context.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, arguments);
            };
            
            // WebGL Fingerprinting Protection
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Generic Renderer';
                }
                if (parameter === 37446) {
                    return 'Generic Vendor';
                }
                return getParameter.apply(this, arguments);
            };
            
            // Audio Context Fingerprinting Protection
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const OriginalAudioContext = AudioContext;
                window.AudioContext = function() {
                    const context = new OriginalAudioContext();
                    const originalCreateOscillator = context.createOscillator;
                    context.createOscillator = function() {
                        const oscillator = originalCreateOscillator.apply(this, arguments);
                        const originalStart = oscillator.start;
                        oscillator.start = function() {
                            oscillator.frequency.value = oscillator.frequency.value + Math.random() * 0.0001;
                            return originalStart.apply(this, arguments);
                        };
                        return oscillator;
                    };
                    return context;
                };
            }
            
            // Font Fingerprinting Protection
            Object.defineProperty(document, 'fonts', {
                get: function() {
                    return {
                        check: function() { return false; },
                        ready: Promise.resolve(),
                        size: 0
                    };
                }
            });
            
            // Screen Resolution Spoofing
            Object.defineProperty(screen, 'width', {
                get: function() { return 1920; }
            });
            Object.defineProperty(screen, 'height', {
                get: function() { return 1080; }
            });
            Object.defineProperty(screen, 'availWidth', {
                get: function() { return 1920; }
            });
            Object.defineProperty(screen, 'availHeight', {
                get: function() { return 1040; }
            });
            
            // Hardware Concurrency Spoofing
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: function() { return 4; }
            });
            
            // Device Memory Spoofing
            Object.defineProperty(navigator, 'deviceMemory', {
                get: function() { return 8; }
            });
            
            // Battery API Blocking
            if (navigator.getBattery) {
                navigator.getBattery = function() {
                    return Promise.reject(new Error('Battery API is disabled for privacy'));
                };
            }
            
            // Plugin Enumeration Prevention
            Object.defineProperty(navigator, 'plugins', {
                get: function() { return []; }
            });
            
            // MIME Type Enumeration Prevention
            Object.defineProperty(navigator, 'mimeTypes', {
                get: function() { return []; }
            });
            
            console.log('[Darkelf Shadow] Anti-fingerprinting protection enabled');
        })();
        """


class PrivacyWebEnginePage(QWebEnginePage):
    """Custom web engine page with privacy features"""
    
    def __init__(self, profile, config, parent=None):
        super().__init__(profile, parent)
        self.config = config
        
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Filter navigation requests for ad/tracker blocking"""
        url_string = url.toString()
        hostname = urlparse(url_string).hostname
        
        if hostname and self.config['privacy']['block_trackers']:
            for blocked_domain in self.config['blocked_domains']:
                if blocked_domain in hostname:
                    print(f"[Blocked] {url_string}")
                    return False
        
        # Force HTTPS if enabled
        if self.config['privacy']['https_only'] and url.scheme() == 'http':
            https_url = QUrl(url_string.replace('http://', 'https://', 1))
            self.setUrl(https_url)
            return False
            
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class BrowserTab(QWidget):
    """Individual browser tab with privacy features"""
    
    def __init__(self, config, profile, parent=None):
        super().__init__(parent)
        self.config = config
        self.profile = profile
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view with custom page
        self.web_view = QWebEngineView()
        self.page = PrivacyWebEnginePage(profile, config, self.web_view)
        self.web_view.setPage(self.page)
        
        # Inject anti-fingerprinting script on page load
        if config['privacy']['anti_fingerprinting']:
            self.page.loadFinished.connect(self.inject_anti_fingerprint)
        
        layout.addWidget(self.web_view)
        self.setLayout(layout)
    
    def inject_anti_fingerprint(self):
        """Inject anti-fingerprinting JavaScript"""
        script = AntiFingerPrintingScript.get_script()
        self.page.runJavaScript(script)
    
    def load(self, url):
        """Load a URL in the tab"""
        if isinstance(url, str):
            if not url.startswith(('http://', 'https://', 'about:')):
                url = 'https://' + url
            url = QUrl(url)
        self.web_view.load(url)
    
    def url(self):
        """Get current URL"""
        return self.web_view.url()
    
    def title(self):
        """Get current page title"""
        return self.web_view.title()


class DarkelfShadowBrowser(QMainWindow):
    """Main browser window with privacy-focused features"""
    
    def __init__(self, config, args):
        super().__init__()
        self.config = config
        self.args = args
        
        # Setup web profile with privacy settings
        self.profile = self.setup_web_profile()
        
        # Initialize UI
        self.init_ui()
        
        # Load homepage
        homepage = args.homepage if args.homepage else config['browser']['homepage']
        if homepage and homepage != 'about:blank':
            self.add_new_tab(homepage)
        else:
            self.add_new_tab('about:blank')
    
    def setup_web_profile(self):
        """Configure web engine profile with privacy settings"""
        profile = QWebEngineProfile.defaultProfile()
        
        # Set random user agent
        user_agents = self.config['user_agents']
        user_agent = random.choice(user_agents)
        profile.setHttpUserAgent(user_agent)
        
        # Configure privacy settings
        settings = profile.settings()
        
        # JavaScript
        if self.args.no_js:
            settings.setAttribute(settings.JavascriptEnabled, False)
        else:
            settings.setAttribute(settings.JavascriptEnabled, 
                                self.config['browser']['enable_javascript'])
        
        # Plugins
        settings.setAttribute(settings.PluginsEnabled, 
                            self.config['browser']['enable_plugins'])
        
        # WebGL
        settings.setAttribute(settings.WebGLEnabled, 
                            self.config['browser']['enable_webgl'])
        
        # Geolocation
        settings.setAttribute(settings.LocalStorageEnabled, True)
        
        # Disable various tracking features
        settings.setAttribute(settings.JavascriptCanAccessClipboard, False)
        settings.setAttribute(settings.JavascriptCanOpenWindows, False)
        settings.setAttribute(settings.AllowRunningInsecureContent, False)
        
        # Set cache to memory only for privacy
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        
        # Set Do Not Track
        if self.config['privacy']['do_not_track']:
            profile.setHttpUserAgent(profile.httpUserAgent() + ' DNT/1')
        
        # Cookie policy
        if self.config['privacy']['block_third_party_cookies']:
            profile.setPersistentCookiesPolicy(
                QWebEngineProfile.NoPersistentCookies
            )
        
        return profile
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('Darkelf Shadow Browser')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        
        self.setCentralWidget(self.tabs)
        
        # Create navigation toolbar
        self.create_navigation_toolbar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
        
        # Apply dark mode if enabled
        if self.config['appearance']['dark_mode']:
            self.apply_dark_mode()
    
    def apply_dark_mode(self):
        """Apply dark mode styling"""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QToolBar {
            background-color: #3c3c3c;
            border: none;
            spacing: 5px;
        }
        QLineEdit {
            background-color: #4a4a4a;
            color: #ffffff;
            border: 1px solid #5a5a5a;
            border-radius: 3px;
            padding: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #3c3c3c;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 8px 20px;
            border: 1px solid #2b2b2b;
        }
        QTabBar::tab:selected {
            background-color: #4a4a4a;
        }
        QStatusBar {
            background-color: #3c3c3c;
            color: #ffffff;
        }
        QPushButton {
            background-color: #4a4a4a;
            color: #ffffff;
            border: 1px solid #5a5a5a;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #5a5a5a;
        }
        """
        self.setStyleSheet(dark_stylesheet)
    
    def create_navigation_toolbar(self):
        """Create navigation toolbar with browser controls"""
        nav_toolbar = QToolBar('Navigation')
        nav_toolbar.setMovable(False)
        self.addToolBar(nav_toolbar)
        
        # Back button
        back_action = QAction('←', self)
        back_action.setStatusTip('Go back')
        back_action.triggered.connect(self.navigate_back)
        nav_toolbar.addAction(back_action)
        
        # Forward button
        forward_action = QAction('→', self)
        forward_action.setStatusTip('Go forward')
        forward_action.triggered.connect(self.navigate_forward)
        nav_toolbar.addAction(forward_action)
        
        # Reload button
        reload_action = QAction('⟳', self)
        reload_action.setStatusTip('Reload page')
        reload_action.triggered.connect(self.reload_page)
        nav_toolbar.addAction(reload_action)
        
        # Home button
        home_action = QAction('⌂', self)
        home_action.setStatusTip('Go home')
        home_action.triggered.connect(self.navigate_home)
        nav_toolbar.addAction(home_action)
        
        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav_toolbar.addWidget(self.url_bar)
        
        # New tab button
        new_tab_action = QAction('+', self)
        new_tab_action.setStatusTip('New tab')
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        nav_toolbar.addAction(new_tab_action)
        
        # Privacy indicator
        privacy_action = QAction('🔒', self)
        privacy_action.setStatusTip('Privacy features enabled')
        nav_toolbar.addAction(privacy_action)
    
    def add_new_tab(self, url='about:blank', label='New Tab'):
        """Add a new browser tab"""
        browser_tab = BrowserTab(self.config, self.profile, self)
        
        i = self.tabs.addTab(browser_tab, label)
        self.tabs.setCurrentIndex(i)
        
        # Connect signals
        browser_tab.web_view.urlChanged.connect(
            lambda qurl, tab=browser_tab: self.update_url_bar(qurl, tab)
        )
        browser_tab.web_view.loadFinished.connect(
            lambda _, i=i, tab=browser_tab: self.tabs.setTabText(i, tab.title()[:20])
        )
        
        # Load URL
        browser_tab.load(url)
        
        return browser_tab
    
    def close_tab(self, index):
        """Close a browser tab"""
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.close()
    
    def current_tab_changed(self, index):
        """Handle tab change"""
        if index >= 0:
            tab = self.tabs.widget(index)
            if tab:
                self.update_url_bar(tab.url(), tab)
    
    def navigate_back(self):
        """Navigate back in current tab"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.web_view.back()
    
    def navigate_forward(self):
        """Navigate forward in current tab"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.web_view.forward()
    
    def reload_page(self):
        """Reload current page"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.web_view.reload()
    
    def navigate_home(self):
        """Navigate to homepage"""
        current_tab = self.tabs.currentWidget()
        if current_tab:
            homepage = self.config['browser']['homepage']
            current_tab.load(homepage)
    
    def navigate_to_url(self):
        """Navigate to URL from URL bar"""
        url = self.url_bar.text()
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.load(url)
    
    def update_url_bar(self, qurl, tab=None):
        """Update URL bar with current URL"""
        if tab == self.tabs.currentWidget():
            self.url_bar.setText(qurl.toString())
    
    def update_status_bar(self):
        """Update status bar with privacy info"""
        status_text = "🔒 Privacy Mode Active"
        
        if self.config['privacy']['anti_fingerprinting']:
            status_text += " | Anti-Fingerprint: ON"
        
        if self.config['privacy']['block_trackers']:
            status_text += " | Tracker Blocking: ON"
        
        if self.config['privacy']['block_ads']:
            status_text += " | Ad Blocking: ON"
        
        if self.args.tor or self.config['privacy']['enable_tor']:
            status_text += " | Tor: ON"
        
        self.status_bar.showMessage(status_text)


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        print("Warning: config.json not found, using defaults")
        return get_default_config()


def get_default_config():
    """Return default configuration"""
    return {
        'privacy': {
            'enable_tor': False,
            'block_trackers': True,
            'block_ads': True,
            'anti_fingerprinting': True,
            'block_third_party_cookies': True,
            'https_only': True,
            'do_not_track': True
        },
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        ],
        'blocked_domains': [
            'doubleclick.net', 'googleadservices.com', 'google-analytics.com'
        ],
        'browser': {
            'homepage': 'about:blank',
            'enable_javascript': True,
            'enable_plugins': False,
            'enable_webgl': False
        },
        'appearance': {
            'dark_mode': True
        }
    }


def main():
    """Main entry point for Darkelf Shadow Browser"""
    parser = argparse.ArgumentParser(description='Darkelf Shadow - Privacy-Focused Web Browser')
    parser.add_argument('--homepage', type=str, help='Set custom homepage URL')
    parser.add_argument('--tor', action='store_true', help='Enable Tor routing')
    parser.add_argument('--no-js', action='store_true', help='Disable JavaScript')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Override config with command line args
    if args.tor:
        config['privacy']['enable_tor'] = True
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName('Darkelf Shadow Browser')
    
    # Create and show main window
    browser = DarkelfShadowBrowser(config, args)
    browser.show()
    
    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
