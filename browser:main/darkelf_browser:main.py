import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from .webengine.profile_factory import create_hardened_profile
from .browser_window import DarkelfBrowser

def main():
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
    app.setStyleSheet(app.styleSheet() + """
    QMenu { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #171b20, stop:1 #15191c);
    border: 1px solid #1a1f23; border-radius: 6px; padding: 6px;}
    QMenu::separator{ height:1px; background:#23292e; margin:6px 8px; }
    QMenu::item{ color: #e5e7eb; padding:6px 16px; border-radius:8px; background:transparent;}
    QMenu::item:selected, QMenu::item:hover{background:#34C759;color:#181a1b;font-weight:bold;}
    QMenu::item:disabled {color:#7f8c8d;background:transparent;}
    QMenu::icon{margin-right:8px;} QMenu::item{cursor:pointer;}
    QToolTip{background:#161a1e;color:#e5e7eb;border:1px solid #22292f; border-radius:0px; padding:6px 8px;}
    """)
    profile = create_hardened_profile()
    w = DarkelfBrowser(profile)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
