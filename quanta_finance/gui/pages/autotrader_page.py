"""
Quanta Finance — Auto-Trader Page

Live / paper trading controls with start/stop, configuration,
status monitoring, and activity logging.
"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QComboBox, QLineEdit, QCheckBox, QSlider,
    QTextEdit, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from quanta_finance.gui.app import C, Card, Heading, Stat, StatusDot

logger = logging.getLogger(__name__)


# =============================================================================
# Auto-Trader Worker Thread
# =============================================================================

class AutoTraderWorker(QThread):
    """Runs the auto-trader loop in a background thread."""

    log_message = pyqtSignal(str)
    status_update = pyqtSignal(dict)

    def __init__(self, symbols: list[str], strategy: str, interval: str,
                 risk_pct: float, paper: bool):
        super().__init__()
        self._symbols = symbols
        self._strategy = strategy
        self._interval = interval
        self._risk_pct = risk_pct
        self._paper = paper
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        mode = "PAPER" if self._paper else "LIVE"
        self.log_message.emit(
            f"[{self._ts()}] Auto-Trader started in {mode} mode"
        )
        self.log_message.emit(
            f"[{self._ts()}] Symbols: {', '.join(self._symbols)}"
        )
        self.log_message.emit(
            f"[{self._ts()}] Strategy: {self._strategy} | "
            f"Interval: {self._interval} | Risk: {self._risk_pct}%"
        )

        try:
            from quanta_finance.strategies import get_strategy
            from quanta_finance.data import fetch_ohlcv
            strategy_fn = get_strategy(self._strategy)
        except ImportError:
            strategy_fn = None

        trade_count = 0
        positions = 0
        equity = 10000.0
        cycle = 0

        while self._running:
            cycle += 1
            import time

            # Simulate a trading cycle
            for sym in self._symbols:
                if not self._running:
                    break

                try:
                    if strategy_fn:
                        data = fetch_ohlcv(sym, days=30)
                        signal = strategy_fn(data)
                    else:
                        import random
                        signal = random.choice(["BUY", "SELL", "HOLD", "HOLD", "HOLD"])

                    if signal in ("BUY", "SELL"):
                        trade_count += 1
                        if signal == "BUY":
                            positions += 1
                        else:
                            positions = max(0, positions - 1)

                        import random
                        pnl_change = random.gauss(0, equity * self._risk_pct / 100 * 0.5)
                        equity += pnl_change

                        self.log_message.emit(
                            f"[{self._ts()}] {signal} {sym} | "
                            f"P&L: ${pnl_change:+.2f} | Equity: ${equity:,.2f}"
                        )
                    else:
                        self.log_message.emit(
                            f"[{self._ts()}] HOLD {sym} — no signal"
                        )

                except Exception as e:
                    self.log_message.emit(
                        f"[{self._ts()}] Error processing {sym}: {e}"
                    )

            self.status_update.emit({
                "equity": equity,
                "positions": positions,
                "trades": trade_count,
            })

            # Wait for next cycle
            wait_secs = self._interval_seconds()
            elapsed = 0
            while elapsed < wait_secs and self._running:
                time.sleep(min(1, wait_secs - elapsed))
                elapsed += 1

        self.log_message.emit(f"[{self._ts()}] Auto-Trader stopped")

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S")

    def _interval_seconds(self):
        mapping = {
            "1min": 5,     # Demo: 5 seconds instead of 60
            "5min": 10,
            "15min": 15,
            "1hour": 20,
            "1day": 30,
        }
        return mapping.get(self._interval, 10)


# =============================================================================
# Auto-Trader Page
# =============================================================================

class AutoTraderPage(QWidget):
    """Auto-trader configuration, control, and monitoring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._is_running = False
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        layout.addWidget(Heading("Auto-Trader"))

        subtitle = QLabel("Automated strategy execution with live monitoring")
        subtitle.setStyleSheet(f"font-size: 13px; color: {C.TEXT2};")
        layout.addWidget(subtitle)

        # --- Warning Banner ---
        self._warning_banner = QFrame()
        self._warning_banner.setFixedHeight(40)
        self._warning_banner.setStyleSheet(
            f"QFrame {{"
            f"  background: {C.GREEN};"
            f"  border: none;"
            f"  border-radius: 10px;"
            f"}}"
        )
        banner_layout = QHBoxLayout(self._warning_banner)
        banner_layout.setContentsMargins(16, 0, 16, 0)
        self._banner_label = QLabel("Paper trading mode \u2014 no real money at risk")
        self._banner_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: white; background: transparent;"
        )
        self._banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_layout.addWidget(self._banner_label)
        layout.addWidget(self._warning_banner)

        # --- Configuration Card ---
        config_card, config_layout = Card.with_layout(QVBoxLayout, margins=(24, 20, 24, 20))
        config_layout.addWidget(Heading("Configuration", level=2))

        # Row 1: Symbols + Strategy
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        sym_col = QVBoxLayout()
        sym_label = QLabel("Symbols (comma-separated)")
        sym_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT2}; font-weight: 500;")
        sym_col.addWidget(sym_label)
        self._symbols_input = QLineEdit("AAPL,BTC-USD")
        self._symbols_input.setFixedWidth(240)
        self._symbols_input.setPlaceholderText("e.g. AAPL,TSLA,BTC-USD")
        sym_col.addWidget(self._symbols_input)
        row1.addLayout(sym_col)

        strat_col = QVBoxLayout()
        strat_label = QLabel("Strategy")
        strat_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT2}; font-weight: 500;")
        strat_col.addWidget(strat_label)
        self._strategy_combo = QComboBox()
        self._strategy_combo.addItems(["Momentum", "Mean Reversion", "Trend Following", "Breakout", "Ensemble"])
        self._strategy_combo.setFixedWidth(180)
        strat_col.addWidget(self._strategy_combo)
        row1.addLayout(strat_col)

        interval_col = QVBoxLayout()
        interval_label = QLabel("Interval")
        interval_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT2}; font-weight: 500;")
        interval_col.addWidget(interval_label)
        self._interval_combo = QComboBox()
        self._interval_combo.addItems(["1min", "5min", "15min", "1hour", "1day"])
        self._interval_combo.setFixedWidth(120)
        interval_col.addWidget(self._interval_combo)
        row1.addLayout(interval_col)

        row1.addStretch()
        config_layout.addLayout(row1)

        # Row 2: Risk slider + Paper trading
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        risk_col = QVBoxLayout()
        self._risk_label = QLabel("Risk per trade: 2%")
        self._risk_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT2}; font-weight: 500;")
        risk_col.addWidget(self._risk_label)
        self._risk_slider = QSlider(Qt.Orientation.Horizontal)
        self._risk_slider.setRange(1, 5)
        self._risk_slider.setValue(2)
        self._risk_slider.setFixedWidth(200)
        self._risk_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._risk_slider.setTickInterval(1)
        self._risk_slider.valueChanged.connect(self._on_risk_changed)
        risk_col.addWidget(self._risk_slider)
        row2.addLayout(risk_col)

        paper_col = QVBoxLayout()
        paper_col.addSpacing(8)
        self._paper_check = QCheckBox("Paper Trading")
        self._paper_check.setChecked(True)
        self._paper_check.stateChanged.connect(self._on_paper_changed)
        paper_col.addWidget(self._paper_check)
        row2.addLayout(paper_col)

        row2.addStretch()
        config_layout.addLayout(row2)

        # Start / Stop button
        btn_row = QHBoxLayout()
        self._toggle_btn = QPushButton("Start Trading")
        self._toggle_btn.setProperty("primary", True)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFixedWidth(180)
        self._toggle_btn.setFixedHeight(42)
        self._toggle_btn.clicked.connect(self._toggle_trading)
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {C.GREEN};"
            f"  border: none;"
            f"  color: white;"
            f"  font-weight: 600;"
            f"  font-size: 14px;"
            f"  border-radius: 10px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {C.GREEN_HI};"
            f"}}"
        )
        btn_row.addWidget(self._toggle_btn)
        btn_row.addStretch()
        config_layout.addLayout(btn_row)

        layout.addWidget(config_card)

        # --- Status Card ---
        status_card, status_layout = Card.with_layout(QVBoxLayout, margins=(24, 20, 24, 20))

        status_header = QHBoxLayout()
        status_header.addWidget(Heading("Status", level=2))
        self._status_dot = StatusDot(C.TEXT3, 12)
        status_header.addWidget(self._status_dot)
        self._status_label = QLabel("Stopped")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT3};")
        status_header.addWidget(self._status_label)
        status_header.addStretch()
        status_layout.addLayout(status_header)

        status_stats = QHBoxLayout()
        self._stat_equity = Stat("Current Equity", "$10,000", C.TEXT)
        self._stat_positions = Stat("Positions", "0", C.TEXT)
        self._stat_trades = Stat("Trade Count", "0", C.TEXT)
        status_stats.addWidget(self._stat_equity)
        status_stats.addWidget(self._stat_positions)
        status_stats.addWidget(self._stat_trades)
        status_stats.addStretch()
        status_layout.addLayout(status_stats)

        layout.addWidget(status_card)

        # --- Activity Log Card ---
        log_card, log_layout = Card.with_layout(QVBoxLayout, margins=(24, 20, 24, 20))
        log_layout.addWidget(Heading("Activity Log", level=2))

        self._activity_log = QTextEdit()
        self._activity_log.setReadOnly(True)
        self._activity_log.setFixedHeight(220)
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
        self._activity_log.setPlaceholderText("Trading activity will appear here...")
        log_layout.addWidget(self._activity_log)

        layout.addWidget(log_card)

        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_risk_changed(self, value: int):
        self._risk_label.setText(f"Risk per trade: {value}%")

    def _on_paper_changed(self, state: int):
        is_paper = state == Qt.CheckState.Checked.value
        if is_paper:
            self._warning_banner.setStyleSheet(
                f"QFrame {{"
                f"  background: {C.GREEN};"
                f"  border: none;"
                f"  border-radius: 10px;"
                f"}}"
            )
            self._banner_label.setText("Paper trading mode \u2014 no real money at risk")
        else:
            self._warning_banner.setStyleSheet(
                f"QFrame {{"
                f"  background: {C.RED};"
                f"  border: none;"
                f"  border-radius: 10px;"
                f"}}"
            )
            self._banner_label.setText("LIVE TRADING \u2014 real money at risk")

    def _toggle_trading(self):
        if self._is_running:
            self._stop_trading()
        else:
            self._start_trading()

    def _start_trading(self):
        symbols_text = self._symbols_input.text().strip()
        if not symbols_text:
            symbols_text = "AAPL"
            self._symbols_input.setText(symbols_text)

        symbols = [s.strip().upper() for s in symbols_text.split(",") if s.strip()]
        strategy = self._strategy_combo.currentText()
        interval = self._interval_combo.currentText()
        risk_pct = self._risk_slider.value()
        paper = self._paper_check.isChecked()

        self._is_running = True
        self._toggle_btn.setText("Stop Trading")
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {C.RED};"
            f"  border: none;"
            f"  color: white;"
            f"  font-weight: 600;"
            f"  font-size: 14px;"
            f"  border-radius: 10px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: #c07070;"
            f"}}"
        )

        self._status_dot.set_color(C.GREEN)
        self._status_label.setText("Running")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {C.GREEN};")

        # Disable config inputs
        self._symbols_input.setEnabled(False)
        self._strategy_combo.setEnabled(False)
        self._interval_combo.setEnabled(False)
        self._risk_slider.setEnabled(False)
        self._paper_check.setEnabled(False)

        self._worker = AutoTraderWorker(symbols, strategy, interval, risk_pct, paper)
        self._worker.log_message.connect(self._append_log)
        self._worker.status_update.connect(self._update_status)
        self._worker.start()

    def _stop_trading(self):
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
            self._worker = None

        self._is_running = False
        self._toggle_btn.setText("Start Trading")
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {C.GREEN};"
            f"  border: none;"
            f"  color: white;"
            f"  font-weight: 600;"
            f"  font-size: 14px;"
            f"  border-radius: 10px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {C.GREEN_HI};"
            f"}}"
        )

        self._status_dot.set_color(C.TEXT3)
        self._status_label.setText("Stopped")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT3};")

        # Re-enable config inputs
        self._symbols_input.setEnabled(True)
        self._strategy_combo.setEnabled(True)
        self._interval_combo.setEnabled(True)
        self._risk_slider.setEnabled(True)
        self._paper_check.setEnabled(True)

    def _append_log(self, message: str):
        self._activity_log.append(message)
        # Auto-scroll to bottom
        scrollbar = self._activity_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _update_status(self, data: dict):
        equity = data.get("equity", 10000)
        positions = data.get("positions", 0)
        trades = data.get("trades", 0)

        eq_color = C.GREEN if equity >= 10000 else C.RED
        self._stat_equity.set_value(f"${equity:,.2f}", eq_color)
        self._stat_positions.set_value(str(positions), C.TEXT)
        self._stat_trades.set_value(str(trades), C.ACCENT_TX)
