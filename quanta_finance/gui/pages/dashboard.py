"""
Quanta Finance — Dashboard Page

Overview page showing strategy counts, account summary,
quick actions, and recent activity.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer

from quanta_finance.gui.app import C, Card, Heading, Stat, StatusDot


class DashboardPage(QWidget):
    """Main dashboard with stats, account overview, quick actions, and activity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # Scrollable content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Page heading
        layout.addWidget(Heading("Dashboard"))

        subtitle = QLabel("Algorithmic trading workbench overview")
        subtitle.setStyleSheet(f"font-size: 13px; color: {C.TEXT2};")
        layout.addWidget(subtitle)

        # --- Stats Row ---
        stats_card, stats_layout = Card.with_layout(QHBoxLayout, margins=(24, 20, 24, 20))

        self._stat_strategies = Stat("Strategies", "5", C.ACCENT_TX)
        self._stat_indicators = Stat("Indicators", "10", C.GREEN)
        self._stat_risk = Stat("Risk Metrics", "14", C.CYAN)

        stats_layout.addWidget(self._stat_strategies)
        stats_layout.addWidget(self._stat_indicators)
        stats_layout.addWidget(self._stat_risk)
        stats_layout.addStretch()

        layout.addWidget(stats_card)

        # --- Account Overview Card ---
        acct_card, acct_layout = Card.with_layout(QVBoxLayout, margins=(24, 20, 24, 20))

        acct_header = QHBoxLayout()
        acct_header.addWidget(Heading("Account Overview", level=2))

        self._acct_dot = StatusDot(C.TEXT3, 12)
        acct_header.addWidget(self._acct_dot)

        self._acct_status_label = QLabel("No broker connected")
        self._acct_status_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT3};")
        acct_header.addWidget(self._acct_status_label)
        acct_header.addStretch()

        acct_layout.addLayout(acct_header)

        # Account stats row
        acct_stats = QHBoxLayout()

        self._stat_equity = Stat("Equity", "\u2014", C.TEXT)
        self._stat_cash = Stat("Cash", "\u2014", C.TEXT)
        self._stat_pnl = Stat("P&L Today", "\u2014", C.TEXT)
        self._stat_positions = Stat("Positions", "\u2014", C.TEXT)

        acct_stats.addWidget(self._stat_equity)
        acct_stats.addWidget(self._stat_cash)
        acct_stats.addWidget(self._stat_pnl)
        acct_stats.addWidget(self._stat_positions)
        acct_stats.addStretch()

        acct_layout.addLayout(acct_stats)

        layout.addWidget(acct_card)

        # --- Quick Actions Card ---
        actions_card, actions_layout = Card.with_layout(QVBoxLayout, margins=(24, 20, 24, 20))
        actions_layout.addWidget(Heading("Quick Actions", level=2))

        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        btn_backtest = QPushButton("Run Backtest")
        btn_backtest.setProperty("primary", True)
        btn_backtest.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backtest.setToolTip("Navigate to the Backtest page (Ctrl+2)")
        btn_backtest.clicked.connect(self._go_backtest)
        actions_row.addWidget(btn_backtest)

        btn_autotrader = QPushButton("Start Auto-Trader")
        btn_autotrader.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_autotrader.setToolTip("Navigate to the Auto-Trader page (Ctrl+3)")
        btn_autotrader.clicked.connect(self._go_autotrader)
        actions_row.addWidget(btn_autotrader)

        btn_fetch = QPushButton("Fetch Data")
        btn_fetch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fetch.setToolTip("Navigate to Market Data page (Ctrl+5)")
        btn_fetch.clicked.connect(self._go_market_data)
        actions_row.addWidget(btn_fetch)

        btn_portfolio = QPushButton("Optimize Portfolio")
        btn_portfolio.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_portfolio.setToolTip("Navigate to Portfolio page (Ctrl+4)")
        btn_portfolio.clicked.connect(self._go_portfolio)
        actions_row.addWidget(btn_portfolio)

        actions_row.addStretch()
        actions_layout.addLayout(actions_row)

        layout.addWidget(actions_card)

        # --- Recent Activity Card ---
        activity_card, activity_layout = Card.with_layout(QVBoxLayout, margins=(24, 20, 24, 20))
        activity_layout.addWidget(Heading("Recent Activity", level=2))

        self._activity_log = QTextEdit()
        self._activity_log.setReadOnly(True)
        self._activity_log.setFixedHeight(180)
        self._activity_log.setStyleSheet(
            f"QTextEdit {{"
            f"  background: {C.SURFACE2};"
            f"  border: 1px solid {C.BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 10px;"
            f"  font-family: 'Cascadia Code', 'Consolas', monospace;"
            f"  font-size: 11px;"
            f"  color: {C.TEXT};"
            f"}}"
        )
        self._activity_log.setPlaceholderText("No recent trades. Run a backtest or start the auto-trader to see activity here.")
        activity_layout.addWidget(self._activity_log)

        layout.addWidget(activity_card)

        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Try to load account data
        self._try_load_account()

    def _try_load_account(self):
        """Attempt to load broker account data for display."""
        try:
            from quanta_finance.data import get_account_info
            info = get_account_info()
            if info:
                self._acct_dot.set_color(C.GREEN)
                self._acct_status_label.setText("Connected")
                self._acct_status_label.setStyleSheet(f"font-size: 11px; color: {C.GREEN};")
                self._stat_equity.set_value(f"${info.get('equity', 0):,.2f}", C.TEXT)
                self._stat_cash.set_value(f"${info.get('cash', 0):,.2f}", C.TEXT)
                pnl = info.get('pnl', 0)
                pnl_color = C.GREEN if pnl >= 0 else C.RED
                self._stat_pnl.set_value(f"${pnl:+,.2f}", pnl_color)
                self._stat_positions.set_value(str(info.get('positions', 0)), C.TEXT)
        except Exception:
            pass

    def add_activity(self, message: str):
        """Append a timestamped message to the activity log."""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._activity_log.append(f"[{ts}] {message}")

    def _find_main_window(self):
        """Walk up the widget tree to find the main window."""
        widget = self.parent()
        while widget:
            if hasattr(widget, 'sidebar'):
                return widget
            widget = widget.parent() if hasattr(widget, 'parent') else None
        return None

    def _navigate_to(self, index: int):
        """Navigate to a page by index through the main window."""
        main = self._find_main_window()
        if main:
            main._switch_page(index)
            main.sidebar._on_click(index)

    def _go_backtest(self):
        self._navigate_to(1)

    def _go_autotrader(self):
        self._navigate_to(2)

    def _go_portfolio(self):
        self._navigate_to(3)

    def _go_market_data(self):
        self._navigate_to(4)

    def refresh(self):
        """Refresh dashboard data."""
        self._try_load_account()
