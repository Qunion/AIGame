from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal
# from PySide6.QtWidgets import ...
# from PySide6.QtCore import pyqtSignal
import logging

logger = logging.getLogger(__name__)

class TimelineListView(QWidget):
    # 信号：当一个时间轴被选中时发出，参数是timeline_id
    timeline_selected = pyqtSignal(int)

    def __init__(self, db_manager, config_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.parent_window = parent # 指向 MainWindow

        layout = QVBoxLayout(self)
        label = QLabel("时间轴列表视图 (Timeline List View - Placeholder)")
        layout.addWidget(label)

        # 示例按钮，用于触发信号
        self.test_button = QPushButton("选择时间轴 1 (测试)")
        self.test_button.clicked.connect(lambda: self.timeline_selected.emit(1)) # 发送测试ID
        layout.addWidget(self.test_button)

        logger.debug("TimelineListView initialized.")

    def load_data(self):
        logger.debug("TimelineListView loading data...")
        # TODO: 从数据库加载时间轴列表并显示
        pass