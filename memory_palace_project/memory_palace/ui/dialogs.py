from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QLabel, QMessageBox
# from PySide6.QtWidgets import ...

class NewTimelineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建时间轴")

        self.layout = QVBoxLayout(self)

        self.label = QLabel("请输入新时间轴的名称：")
        self.layout.addWidget(self.label)

        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("例如：英语单词学习")
        self.layout.addWidget(self.name_edit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        # 初始时OK按钮禁用，直到用户输入内容
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.name_edit.textChanged.connect(self.check_input)

    def check_input(self, text):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(text.strip()))

    def get_timeline_name(self):
        return self.name_edit.text().strip()

def confirm_dialog(parent, title, message) -> bool:
    """显示一个通用的确认对话框 (是/否)"""
    reply = QMessageBox.question(parent, title, message,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No) # 默认按钮是No
    return reply == QMessageBox.StandardButton.Yes