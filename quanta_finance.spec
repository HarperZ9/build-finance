# Quanta Finance — PyInstaller Build Spec
import os
block_cipher = None

a = Analysis(
    ['quanta_finance/cli.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'quanta_finance', 'quanta_finance.data', 'quanta_finance.indicators',
        'quanta_finance.strategies', 'quanta_finance.risk', 'quanta_finance.sizing',
        'quanta_finance.orderbook', 'quanta_finance.backtest', 'quanta_finance.portfolio',
        'quanta_finance.market_data', 'quanta_finance.broker', 'quanta_finance.autotrader',
        'quanta_finance.gui', 'quanta_finance.gui.app',
        'quanta_finance.gui.pages.dashboard', 'quanta_finance.gui.pages.backtest_page',
        'quanta_finance.gui.pages.autotrader_page', 'quanta_finance.gui.pages.portfolio_page',
        'quanta_finance.gui.pages.market_data_page', 'quanta_finance.gui.pages.settings_page',
        'numpy', 'scipy', 'scipy.optimize',
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
    ],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='quanta-finance', console=True, icon=None)
coll = COLLECT(exe, a.binaries, a.datas, name='quanta-finance')
