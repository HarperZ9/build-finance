def launch():
    import sys
    from PyQt6.QtWidgets import QApplication
    from quanta_finance.gui.app import QuantaFinanceWindow
    app = QApplication(sys.argv)
    window = QuantaFinanceWindow()
    window.show()
    return app.exec()
