from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox


class AlertDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        layout = QVBoxLayout()
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        okBtn = QDialogButtonBox(QDialogButtonBox.Ok)
        okBtn.accepted.connect(self.close)
        layout.addWidget(okBtn)
        self.setLayout(layout)
