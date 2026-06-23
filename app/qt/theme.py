"""VS Code–inspired dark theme."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.qt.fonts import EDITOR_FONT_SIZE_PT, editor_font_family_css

# VS Code dark+ palette
COLOR_BG = "#1e1e1e"
COLOR_EDITOR = "#1e1e1e"
COLOR_WORKSPACE = "#1e1e1e"
COLOR_SIDEBAR = "#252526"
COLOR_ACTIVITY = "#2a2d2e"
COLOR_TOOLBAR = "#2d2d2d"
COLOR_PANEL = "#181818"
COLOR_INPUT = "#3c3c3c"
COLOR_BORDER = "#454545"
COLOR_DIVIDER = "#3c3c3c"
COLOR_ZONE_LINE = "#4a4a4a"
COLOR_TEXT = "#cccccc"
COLOR_MUTED = "#858585"
COLOR_PRIMARY = "#007acc"
COLOR_PRIMARY_HOVER = "#1f8ad2"
COLOR_SUCCESS = "#89d185"
COLOR_WARNING = "#cca700"
COLOR_ERROR = "#f48771"
COLOR_RECORDING = "#f14c4c"
COLOR_DIR_SELECTED = "#094771"
COLOR_TAB_INACTIVE = "#2d2d2d"

COLOR_BRAND_ACCENT = "#5ec8f2"
COLOR_BRAND_ACCENT_DEEP = COLOR_DIR_SELECTED
COLOR_BRAND_GHERKIN = "#9cdc8a"
COLOR_BRAND_RECORD = "#ff6b6b"


def apply_dark_theme(app: QApplication) -> None:
    code_font = editor_font_family_css()
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLOR_BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLOR_TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLOR_EDITOR))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLOR_SIDEBAR))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLOR_SIDEBAR))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COLOR_TEXT))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLOR_TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLOR_INPUT))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLOR_TEXT))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLOR_DIR_SELECTED))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLOR_MUTED))
    app.setPalette(palette)

    app.setStyleSheet(
        f"""
        QWidget {{
            color: {COLOR_TEXT};
            font-family: "Segoe UI";
            font-size: 9pt;
        }}
        QMainWindow {{
            background: {COLOR_BG};
        }}
        QMenuBar {{
            background: {COLOR_TOOLBAR};
            border-bottom: 1px solid {COLOR_DIVIDER};
            padding: 0;
            spacing: 0;
        }}
        QMenuBar::item {{
            padding: 2px 6px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: {COLOR_INPUT};
        }}
        QMenu {{
            background: {COLOR_SIDEBAR};
            border: 1px solid {COLOR_BORDER};
            padding: 4px 0;
        }}
        QMenu::item {{
            padding: 3px 20px 3px 10px;
        }}
        QMenu::item:selected {{
            background: {COLOR_DIR_SELECTED};
        }}
        QLineEdit {{
            background: {COLOR_INPUT};
            border: 1px solid transparent;
            border-radius: 2px;
            padding: 1px 4px;
            min-height: 18px;
            selection-background-color: {COLOR_DIR_SELECTED};
        }}
        QLineEdit:focus {{
            border-color: {COLOR_PRIMARY};
        }}
        QPlainTextEdit, QTextEdit {{
            background: {COLOR_EDITOR};
            border: none;
            padding: 4px 6px;
            selection-background-color: {COLOR_DIR_SELECTED};
        }}
        QPlainTextEdit[role="code-editor"] {{
            font-family: {code_font};
            font-size: {EDITOR_FONT_SIZE_PT}pt;
            padding: 8px 12px;
        }}
        QPlainTextEdit[role="mono-panel"] {{
            font-family: {code_font};
            font-size: {EDITOR_FONT_SIZE_PT}pt;
        }}
        QPushButton {{
            background: transparent;
            border: none;
            border-radius: 2px;
            padding: 2px 6px;
            min-height: 16px;
        }}
        QPushButton:hover {{
            background: {COLOR_INPUT};
        }}
        QPushButton[primary="true"] {{
            background: {COLOR_PRIMARY};
        }}
        QPushButton[primary="true"]:hover {{
            background: {COLOR_PRIMARY_HOVER};
        }}
        QPushButton[activity="true"] {{
            border-radius: 0;
            padding: 6px 0;
            min-width: 40px;
            max-width: 40px;
        }}
        QPushButton[activity="true"]:checked {{
            border-left: 2px solid {COLOR_PRIMARY};
            background: {COLOR_SIDEBAR};
        }}
        QToolButton[activity="true"] {{
            border-radius: 0;
            min-width: 40px;
            max-width: 40px;
            min-height: 36px;
            max-height: 36px;
            padding: 0;
        }}
        QToolButton[activity="true"]:checked {{
            border-left: 2px solid {COLOR_PRIMARY};
            background: {COLOR_SIDEBAR};
        }}
        QToolButton[toolbar="true"] {{
            border: none;
            border-radius: 3px;
            padding: 2px 8px;
            min-height: 24px;
        }}
        QWidget[role="quick-toolbar"] QToolButton[toolbar-icon="true"] {{
            border: none;
            border-radius: 3px;
            padding: 0;
            margin: 0;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QWidget[role="quick-toolbar"] QToolButton[toolbar-icon="true"]:hover {{
            background: {COLOR_INPUT};
        }}
        QWidget[role="quick-toolbar"] QToolButton[toolbar-icon="true"]:disabled {{
            opacity: 0.55;
        }}
        QToolButton[compact-icon="true"] {{
            border: none;
            border-radius: 3px;
            padding: 0;
            margin: 0;
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
        }}
        QToolButton[compact-icon="true"]:hover {{
            background: {COLOR_INPUT};
        }}
        QToolButton[tab-close="true"] {{
            border: none;
            border-radius: 3px;
            padding: 0;
            margin: 0;
            min-width: 16px;
            max-width: 16px;
            min-height: 16px;
            max-height: 16px;
        }}
        QToolButton[tab-close="true"]:hover {{
            background: {COLOR_INPUT};
        }}
        QToolTip {{
            background: {COLOR_SIDEBAR};
            color: {COLOR_TEXT};
            border: 1px solid {COLOR_BORDER};
            padding: 3px 6px;
        }}
        QToolButton[toolbar="true"]:hover {{
            background: {COLOR_INPUT};
        }}
        QToolButton[toolbar="true"]:disabled {{
            opacity: 0.55;
        }}
        QWidget[role="quick-toolbar"] {{
            background: {COLOR_TOOLBAR};
            border-bottom: 1px solid {COLOR_DIVIDER};
        }}
        QWidget[role="gherkin-hints"] {{
            background: {COLOR_SIDEBAR};
            border-bottom: 1px solid {COLOR_BORDER};
        }}
        QTreeView {{
            background: {COLOR_SIDEBAR};
            border: none;
            outline: none;
        }}
        QTreeView::item {{
            height: 20px;
            padding: 0 2px;
        }}
        QTreeView::item:hover {{
            background: {COLOR_INPUT};
        }}
        QTreeView::item:selected {{
            background: {COLOR_DIR_SELECTED};
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLOR_INPUT};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QStatusBar {{
            background: {COLOR_PANEL};
            color: {COLOR_TEXT};
            border-top: 1px solid {COLOR_BORDER};
            min-height: 22px;
            font-size: 8pt;
        }}
        QStatusBar::item {{
            border: none;
        }}
        QWidget[role="ide-status-bar"] {{
            background: {COLOR_PANEL};
            border-top: 1px solid {COLOR_DIVIDER};
        }}
        QFrame[status="separator"] {{
            background: {COLOR_BORDER};
            max-width: 1px;
        }}
        QToolButton[status-segment="true"]:disabled {{
            color: {COLOR_TEXT};
        }}
        QWidget[status-segment="true"] {{
            min-height: 24px;
            border-left: 1px solid {COLOR_BORDER};
            background: transparent;
        }}
        QWidget[status-segment="true"][clickable="true"] {{
            border: none;
            border-left: 1px solid {COLOR_BORDER};
        }}
        QWidget[status-segment="true"][clickable="true"]:hover {{
            background: #2a2d2e;
        }}
        QWidget[status-segment="true"][accent="recording"] {{
            background: {COLOR_RECORDING};
            border-left: 1px solid {COLOR_BORDER};
        }}
        QWidget[status-segment="true"][accent="playing"] {{
            background: {COLOR_PRIMARY};
            border-left: 1px solid {COLOR_BORDER};
        }}
        QLabel[muted="true"] {{
            color: {COLOR_MUTED};
        }}
        QTabBar[role="editor-tabs"] {{
            background: {COLOR_TOOLBAR};
            border-bottom: 1px solid {COLOR_ZONE_LINE};
        }}
        QTabBar[role="editor-tabs"]::tab {{
            background: {COLOR_TAB_INACTIVE};
            color: {COLOR_MUTED};
            padding: 2px 20px 2px 8px;
            margin-right: 0;
            border-right: 1px solid {COLOR_DIVIDER};
            min-width: 56px;
            max-height: 22px;
            font-size: 8pt;
        }}
        QTabBar[role="editor-tabs"]::tab:selected {{
            background: {COLOR_EDITOR};
            color: {COLOR_TEXT};
            border-top: 1px solid {COLOR_PRIMARY};
            border-bottom: 1px solid {COLOR_EDITOR};
        }}
        QTabBar[role="editor-tabs"]::close-button {{
            subcontrol-position: right;
            subcontrol-origin: padding;
            width: 14px;
            height: 14px;
            margin: 2px 4px 2px 0;
            border-radius: 3px;
        }}
        QTabBar[role="editor-tabs"]::close-button:hover {{
            background: {COLOR_INPUT};
        }}
        QTabBar[role="editor-tabs"]::close-button:selected {{
            background: {COLOR_INPUT};
        }}
        QTabWidget[role="bottom-panel-tabs"]::pane {{
            border: none;
            background: {COLOR_PANEL};
            top: 0;
        }}
        QTabBar[role="panel-tabs"] {{
            background: {COLOR_PANEL};
            border: none;
        }}
        QTabBar[role="panel-tabs"]::tab {{
            background: transparent;
            color: {COLOR_MUTED};
            border: none;
            border-top: 2px solid transparent;
            border-right: none;
            padding: 3px 12px;
            min-width: 40px;
            max-height: 24px;
            font-size: 8pt;
        }}
        QTabBar[role="panel-tabs"]::tab:selected {{
            color: {COLOR_TEXT};
            background: transparent;
            border-top: 2px solid {COLOR_PRIMARY};
        }}
        QTabBar[role="panel-tabs"]::tab:hover {{
            color: {COLOR_TEXT};
        }}
        QTabWidget::pane {{
            border: none;
            background: {COLOR_EDITOR};
        }}
        QSplitter::handle {{
            background: transparent;
            border: none;
            margin: 0;
            padding: 0;
        }}
        QSplitter::handle:horizontal {{
            width: 9px;
        }}
        QSplitter::handle:vertical {{
            height: 9px;
        }}
        QWidget[role="activity"] {{
            background: {COLOR_ACTIVITY};
        }}
        QFrame[role="zone-divider"] {{
            background: {COLOR_ZONE_LINE};
            border: none;
            margin: 0;
            padding: 0;
        }}
        QWidget[role="sidebar"] {{
            background: {COLOR_SIDEBAR};
        }}
        QWidget[role="catalog-panel"] {{
            background: {COLOR_SIDEBAR};
        }}
        QWidget[role="sidebar-header"] {{
            background: #2a2a2b;
            border-bottom: 1px solid {COLOR_DIVIDER};
        }}
        QLabel[role="zone-title"] {{
            color: {COLOR_MUTED};
            font-size: 6.5pt;
            font-weight: 500;
            letter-spacing: 0.3px;
            padding: 1px 2px 0 2px;
        }}
        QWidget[role="catalog-empty-card"] {{
            background: #2a2a2b;
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
        }}
        QLabel[role="catalog-empty-icon"] {{
            background: {COLOR_INPUT};
            border: 1px solid {COLOR_BORDER};
            border-radius: 26px;
        }}
        QLabel[role="catalog-empty-title"] {{
            color: {COLOR_TEXT};
            font-weight: 600;
            font-size: 9pt;
        }}
        QLabel[role="catalog-empty-hint"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
            line-height: 130%;
        }}
        QWidget[role="workspace"] {{
            background: {COLOR_WORKSPACE};
        }}
        QWidget[role="welcome"] {{
            background: {COLOR_WORKSPACE};
        }}
        QScrollArea[role="welcome-scroll"] {{
            background: {COLOR_WORKSPACE};
            border: none;
        }}
        QWidget[role="welcome-scroll-body"] {{
            background: {COLOR_WORKSPACE};
        }}
        QWidget[role="welcome-card"] {{
            background: #252526;
            border: 1px solid {COLOR_DIVIDER};
            border-radius: 8px;
            max-width: 520px;
        }}
        QWidget[role="empty-editor"] {{
            background: {COLOR_WORKSPACE};
        }}
        QWidget[role="empty-editor-card"] {{
            background: #252526;
            border: 1px solid {COLOR_DIVIDER};
            border-radius: 8px;
            max-width: 420px;
            min-width: 320px;
        }}
        QLabel[role="empty-editor-tips"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
            padding-top: 8px;
            line-height: 140%;
        }}
        QWidget[role="panel"] {{
            background: {COLOR_PANEL};
        }}
        QWidget[role="run-history-dialog"] {{
            background: {COLOR_PANEL};
        }}
        QLabel[role="run-history-title"] {{
            font-size: 11pt;
            font-weight: 600;
            padding-bottom: 2px;
        }}
        QLabel[role="run-history-empty"] {{
            color: {COLOR_MUTED};
            padding: 24px 16px;
            border: 1px dashed {COLOR_BORDER};
            border-radius: 4px;
            background: {COLOR_SIDEBAR};
        }}
        QLabel[role="run-history-detail"] {{
            color: {COLOR_TEXT};
            background: #2a1f1f;
            border: 1px solid {COLOR_ERROR};
            border-radius: 4px;
            padding: 8px 10px;
        }}
        QLabel[role="results-summary"] {{
            font-weight: 500;
        }}
        QLabel[role="results-summary"][success="true"] {{
            color: {COLOR_SUCCESS};
        }}
        QLabel[role="results-summary"][success="false"] {{
            color: {COLOR_ERROR};
        }}
        QTableWidget[role="run-results-table"] {{
            background: {COLOR_PANEL};
            alternate-background-color: {COLOR_SIDEBAR};
            border: 1px solid {COLOR_DIVIDER};
            gridline-color: {COLOR_DIVIDER};
        }}
        QTableWidget[role="run-results-table"]::item {{
            padding: 4px 6px;
        }}
        QTableWidget[role="run-results-table"]::item:selected {{
            background: {COLOR_DIR_SELECTED};
        }}
        QWidget[role="results-panel"] {{
            background: {COLOR_PANEL};
        }}
        QFrame[role="v-divider"] {{
            background: {COLOR_ZONE_LINE};
            max-width: 1px;
            min-width: 1px;
            border: none;
        }}
        QWidget[role="editor-action-bar"] QFrame[role="v-divider"] {{
            min-height: 32px;
            max-height: 32px;
        }}
        QWidget[role="editor-action-bar"] {{
            background: {COLOR_TOOLBAR};
            border-bottom: 1px solid {COLOR_ZONE_LINE};
        }}
        QWidget[role="editor-action-bar"] QWidget[role="scenario-chip"] {{
            background: #2a2d2e;
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            min-height: 24px;
            max-height: 24px;
            margin: 0 10px;
        }}
        QToolButton[role="scenario-chip-icon"] {{
            border: none;
            background: transparent;
            padding: 0;
            margin: 0;
        }}
        QStackedWidget[role="editor-stack"] {{
            background: {COLOR_WORKSPACE};
        }}
        QWidget[role="editor-action-bar"] QWidget[role="quick-toolbar"] {{
            background: transparent;
            border: none;
        }}
        QWidget[role="dirty-banner"] {{
            background: #3a2f00;
            border-bottom: 1px solid {COLOR_WARNING};
        }}
        QWidget[role="post-record-banner"] {{
            background: #1a2a1a;
            border-bottom: 1px solid {COLOR_SUCCESS};
        }}
        QWidget[role="recording-modes"] {{
            background: {COLOR_TOOLBAR};
            border-bottom: 1px solid {COLOR_DIVIDER};
        }}
        QWidget[role="steps-strip"] {{
            background: {COLOR_SIDEBAR};
            border-top: 1px solid {COLOR_ZONE_LINE};
        }}
        QWidget[role="steps-collapsed-bar"] {{
            background: {COLOR_SIDEBAR};
            border-top: 1px solid {COLOR_ZONE_LINE};
        }}
        QTableView {{
            background: {COLOR_SIDEBAR};
            border: none;
            gridline-color: {COLOR_BORDER};
            font-size: 8pt;
        }}
        QHeaderView::section {{
            background: {COLOR_SIDEBAR};
            border: none;
            border-bottom: 1px solid {COLOR_BORDER};
            padding: 2px 4px;
            font-size: 8pt;
        }}
        QDialog[role="settings-dialog"] {{
            background: {COLOR_BG};
        }}
        QWidget[role="settings-search-header"] {{
            background: {COLOR_SIDEBAR};
            border-bottom: 1px solid {COLOR_DIVIDER};
        }}
        QWidget[role="settings-search-header"] QLineEdit {{
            background: {COLOR_INPUT};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 9pt;
        }}
        QLabel[role="settings-empty-search"] {{
            color: {COLOR_MUTED};
            font-size: 10pt;
            padding: 32px;
        }}
        QListWidget[role="settings-nav"] {{
            background: {COLOR_SIDEBAR};
            border: none;
            outline: none;
            padding: 8px 6px;
            font-size: 9pt;
        }}
        QListWidget[role="settings-nav"]::item {{
            color: {COLOR_MUTED};
            padding: 8px 10px;
            border-radius: 4px;
            margin: 1px 0;
        }}
        QListWidget[role="settings-nav"]::item:selected {{
            background: {COLOR_DIR_SELECTED};
            color: {COLOR_TEXT};
        }}
        QListWidget[role="settings-nav"]::item:hover {{
            background: {COLOR_INPUT};
            color: {COLOR_TEXT};
        }}
        QFrame[role="settings-nav-divider"] {{
            background: {COLOR_DIVIDER};
            max-width: 1px;
            min-width: 1px;
            border: none;
        }}
        QFrame[role="settings-footer-line"] {{
            background: {COLOR_DIVIDER};
            max-height: 1px;
            min-height: 1px;
            border: none;
        }}
        QWidget[role="settings-footer"] {{
            background: {COLOR_SIDEBAR};
        }}
        QStackedWidget[role="settings-content"] {{
            background: {COLOR_EDITOR};
        }}
        QScrollArea[role="settings-scroll"] {{
            background: transparent;
            border: none;
        }}
        QLabel[role="settings-section-title"] {{
            color: {COLOR_TEXT};
            font-size: 11pt;
            font-weight: 600;
            padding-bottom: 2px;
        }}
        QLabel[role="settings-section-hint"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
            line-height: 130%;
            padding-bottom: 4px;
        }}
        QWidget[role="settings-option"] {{
            background: #2a2d2e;
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
        }}
        QLabel[role="settings-option-title"] {{
            color: {COLOR_TEXT};
            font-size: 9pt;
            font-weight: 500;
        }}
        QLabel[role="settings-option-hint"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
            line-height: 130%;
        }}
        QWidget[role="settings-plugin-card"] {{
            background: #2a2d2e;
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
        }}
        QDialog[role="settings-dialog"] QDialogButtonBox QPushButton {{
            background: {COLOR_INPUT};
            border: 1px solid {COLOR_BORDER};
            border-radius: 3px;
            padding: 2px 10px;
            min-height: 20px;
            max-height: 24px;
        }}
        QDialog[role="settings-dialog"] QDialogButtonBox QPushButton:hover {{
            background: #4a4a4a;
        }}
        QListWidget[role="settings-list"] {{
            background: {COLOR_INPUT};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 4px;
        }}
        QListWidget[role="settings-list"]::item {{
            padding: 4px 6px;
            border-radius: 2px;
        }}
        QListWidget[role="settings-list"]::item:selected {{
            background: {COLOR_DIR_SELECTED};
        }}
        QListWidget[role="settings-list"]::item:hover {{
            background: #4a4a4a;
        }}
        QDialog[role="app-dialog"] {{
            background: {COLOR_BG};
        }}
        QLabel[role="dialog-hint"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
            line-height: 130%;
        }}
        QLabel[role="dialog-title"] {{
            font-size: 11pt;
            font-weight: 600;
        }}
        QLabel[role="muted"] {{
            color: {COLOR_MUTED};
        }}
        QLabel[role="ui-caption"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
        }}
        QLabel[role="ui-caption"][padding="top"] {{
            padding-top: 4px;
        }}
        QLabel[role="ui-body"] {{
            color: {COLOR_TEXT};
            font-size: 9pt;
        }}
        QLabel[role="ui-body-secondary"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
        }}
        QLabel[role="ui-section"] {{
            font-weight: 600;
            margin-top: 8px;
        }}
        QLabel[role="ui-section-sm"] {{
            font-size: 8pt;
            font-weight: 600;
        }}
        QLabel[role="ui-strip-title"] {{
            font-size: 8pt;
            font-weight: 600;
        }}
        QLabel[role="ui-error"] {{
            color: {COLOR_ERROR};
            font-size: 9pt;
        }}
        QLabel[tone="muted"] {{
            color: {COLOR_MUTED};
            font-size: 8pt;
        }}
        QLabel[tone="success"] {{
            color: {COLOR_SUCCESS};
            font-size: 8pt;
        }}
        QLabel[tone="warning"] {{
            color: {COLOR_WARNING};
            font-size: 8pt;
        }}
        QLabel[tone="error"] {{
            color: {COLOR_ERROR};
            font-size: 8pt;
        }}
        QLabel[tone="recording"] {{
            color: {COLOR_RECORDING};
            font-size: 8pt;
            font-weight: 600;
        }}
        QLabel[tone="active"] {{
            color: {COLOR_TEXT};
            font-size: 8pt;
            font-weight: 600;
        }}
        QLabel[tone="inverse"] {{
            color: #ffffff;
            font-size: 8pt;
            font-weight: 600;
        }}
        QLabel[role="code-preview"] {{
            color: {COLOR_TEXT};
            background: #2d2d2d;
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 8px;
            font-family: {code_font};
        }}
        QLabel[role="link-label"] {{
            color: {COLOR_PRIMARY};
        }}
        QLabel[role="welcome-title"] {{
            font-size: 18pt;
            font-weight: 300;
        }}
        QLabel[role="welcome-section"] {{
            font-weight: 600;
            margin-top: 8px;
        }}
        QLabel[role="welcome-muted-heading"] {{
            color: {COLOR_MUTED};
            font-weight: 600;
            margin-top: 12px;
        }}
        QLabel[role="welcome-subtitle"] {{
            color: {COLOR_MUTED};
            margin-bottom: 8px;
        }}
        QLabel[role="banner-warning-icon"] {{
            color: {COLOR_WARNING};
        }}
        QLabel[role="error-title"] {{
            color: {COLOR_ERROR};
            font-weight: 600;
        }}
        QWidget[role="gherkin-error-bar"] {{
            background: #2a1f1f;
            border-bottom: 1px solid {COLOR_ERROR};
        }}
        QWidget[role="url-bar"] {{
            background: {COLOR_TOOLBAR};
            border-bottom: 1px solid {COLOR_DIVIDER};
        }}
        QTextBrowser[role="help-detail"] {{
            background: {COLOR_SIDEBAR};
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
            padding: 12px 14px;
        }}
        QPushButton[banner-dismiss="true"] {{
            color: {COLOR_MUTED};
        }}
        QLabel[role="status-led"][tone="on"] {{
            background: {COLOR_SUCCESS};
            border-radius: 3px;
            min-width: 6px;
            max-width: 6px;
            min-height: 6px;
            max-height: 6px;
        }}
        QLabel[role="status-led"][tone="off"] {{
            background: {COLOR_MUTED};
            border-radius: 3px;
            min-width: 6px;
            max-width: 6px;
            min-height: 6px;
            max-height: 6px;
        }}
        QWidget[status-segment="true"] QLabel {{
            font-size: 8pt;
        }}
        QWidget[status-segment="true"][clickable="false"] QLabel {{
            color: {COLOR_MUTED};
        }}
        QWidget[status-segment="true"][clickable="true"] QLabel {{
            color: {COLOR_TEXT};
        }}
        QWidget[status-segment="true"][accent="recording"] QLabel,
        QWidget[status-segment="true"][accent="playing"] QLabel {{
            color: #ffffff;
            font-weight: 600;
        }}
        QLabel[status="message"] {{
            padding: 0 12px;
            font-size: 8pt;
        }}
        QLabel[status="message"][tone="normal"] {{
            color: {COLOR_TEXT};
        }}
        QLabel[status="message"][tone="error"] {{
            color: {COLOR_ERROR};
        }}
        QLabel[status="message"][tone="success"] {{
            color: {COLOR_SUCCESS};
        }}
        QLabel[status="message"][tone="warning"] {{
            color: {COLOR_WARNING};
        }}
        QLabel[status="message"][tone="busy"],
        QLabel[status="message"][tone="muted"],
        QLabel[status="message"][tone="info"] {{
            color: {COLOR_MUTED};
        }}
        QWidget#browserOverlay {{
            background: {COLOR_TOOLBAR};
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
        }}
        QWidget#browserOverlay QPushButton {{
            min-height: 24px;
            max-height: 28px;
            padding: 2px 8px;
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
        }}
        QWidget#browserOverlay QPushButton:hover:enabled {{
            border-color: #5a5a5a;
        }}
        QWidget#browserOverlay QPushButton:disabled {{
            color: {COLOR_MUTED};
        }}
        QFrame[role="dialog-footer-line"] {{
            background: {COLOR_DIVIDER};
            max-height: 1px;
            min-height: 1px;
            border: none;
        }}
        QDialog[role="app-dialog"] QPushButton[dialog-action="true"],
        QDialog[role="app-dialog"] QDialogButtonBox QPushButton {{
            background: {COLOR_INPUT};
            border: 1px solid {COLOR_BORDER};
            border-radius: 3px;
            padding: 2px 10px;
            min-height: 20px;
            max-height: 24px;
        }}
        QDialog[role="app-dialog"] QPushButton[dialog-action="true"]:hover,
        QDialog[role="app-dialog"] QDialogButtonBox QPushButton:hover {{
            background: #4a4a4a;
        }}
        QDialog[role="app-dialog"] QPushButton[dialog-action="true"]:pressed,
        QDialog[role="app-dialog"] QDialogButtonBox QPushButton:pressed {{
            background: #383838;
        }}
        QDialog[role="app-dialog"] QPushButton[dialog-action="true"][primary="true"],
        QDialog[role="app-dialog"] QDialogButtonBox QPushButton:default {{
            background: {COLOR_PRIMARY};
            border-color: {COLOR_PRIMARY};
        }}
        QDialog[role="app-dialog"] QPushButton[dialog-action="true"][primary="true"]:hover,
        QDialog[role="app-dialog"] QDialogButtonBox QPushButton:default:hover {{
            background: {COLOR_PRIMARY_HOVER};
            border-color: {COLOR_PRIMARY_HOVER};
        }}
        QLabel[role="dialog-phase"] {{
            font-size: 11pt;
            font-weight: 600;
        }}
        """
    )
