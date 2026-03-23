# Quanta Finance — Optimized PyInstaller Build Spec
# Targets <200 MB by excluding unused packages from the shared Python environment.
# The app only needs: numpy, scipy (optimize, cluster, spatial), PyQt6.
import os

block_cipher = None

EXCLUDES = [
    # ── PyTorch / ML stack (biggest offenders: ~2 GB) ────────────────
    'torch', 'torchvision', 'torchaudio',
    'transformers', 'diffusers', 'accelerate', 'safetensors',
    'sentencepiece', 'tokenizers', 'huggingface_hub', 'hf_xet',
    'protobuf',

    # ── Other heavy libs not used by quanta-finance ──────────────────
    'matplotlib', 'matplotlib.tests',
    'pandas', 'pandas.tests',
    'PIL', 'pillow', 'Pillow',
    'tkinter', '_tkinter',
    'IPython', 'jupyter', 'jupyter_core', 'notebook',
    'sphinx', 'docutils',
    'pytest', '_pytest', 'pluggy', 'iniconfig',
    'lxml',

    # ── Unused networking / API libs ─────────────────────────────────
    'openai', 'httpx', 'httpcore', 'anyio', 'h11', 'sniffio',
    'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
    'pydantic', 'pydantic_core',

    # ── Other installed packages not needed ───────────────────────────
    'colour_science', 'colour',
    'python_docx', 'docx',
    'rich', 'pygments', 'markdown_it_py', 'mdurl',
    'typer', 'click', 'shellingham',
    'psutil', 'pystray',
    'jinja2', 'markupsafe',
    'sympy', 'mpmath', 'networkx',
    'yaml', 'pyyaml',
    'capstone',
    'hidapi',
    'tqdm', 'filelock', 'fsspec',
    'regex',

    # ── Sibling quanta-* projects ────────────────────────────────────
    'quanta_color', 'quanta_engine', 'quanta_oracle',
    'calibrate_pro',

    # ── Test suites inside kept packages ─────────────────────────────
    'numpy.tests', 'numpy.testing',
    'scipy.tests', 'scipy.testing',

    # ── Unused scipy subpackages (keep optimize, cluster, spatial) ───
    'scipy.integrate', 'scipy.interpolate', 'scipy.io',
    'scipy.linalg', 'scipy.ndimage', 'scipy.odr',
    'scipy.signal', 'scipy.sparse', 'scipy.special',
    'scipy.stats', 'scipy.fft', 'scipy.misc',

    # ── Unused PyQt6 addon modules ───────────────────────────────────
    'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtCharts',
]

a = Analysis(
    ['quanta_finance/cli.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Our own package
        'quanta_finance', 'quanta_finance.data', 'quanta_finance.indicators',
        'quanta_finance.strategies', 'quanta_finance.risk', 'quanta_finance.sizing',
        'quanta_finance.orderbook', 'quanta_finance.backtest', 'quanta_finance.portfolio',
        'quanta_finance.market_data', 'quanta_finance.broker', 'quanta_finance.autotrader',
        'quanta_finance.gui', 'quanta_finance.gui.app',
        'quanta_finance.gui.pages.dashboard', 'quanta_finance.gui.pages.backtest_page',
        'quanta_finance.gui.pages.autotrader_page', 'quanta_finance.gui.pages.portfolio_page',
        'quanta_finance.gui.pages.market_data_page', 'quanta_finance.gui.pages.settings_page',
        # Actually-used third-party
        'numpy', 'scipy', 'scipy.optimize', 'scipy.cluster.hierarchy', 'scipy.spatial.distance',
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.sip',
    ],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='quanta-finance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
