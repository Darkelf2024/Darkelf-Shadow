import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings

from browser.browser_window import DarkelfBrowser

def create_profile(app):

    profile = QWebEngineProfile("", app)

    profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
    profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)

    profile.setHttpAcceptLanguage("en-US,en;q=0.9")

    profile.setHttpUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    )

    settings = profile.settings()

    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

    return profile


def configure_palette(app):

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


def main():

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    configure_palette(app)

    profile = create_profile(app)

    window = DarkelfBrowser(profile)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
