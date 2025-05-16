import sys
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt
# from PySide6.QtWidgets import ...
# from PySide6.QtCore import Qt

from ..db.database_manager import DatabaseManager
from ..utils.config_manager import ConfigManager
from ..utils.constants import APP_NAME

# 导入空的视图类 (稍后创建它们的骨架)
from .timeline_list_view import TimelineListView
from .segment_carousel_view import SegmentCarouselView
from .segment_detail_view import SegmentDetailView
import logging # 导入logging

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)

        self.db_manager = DatabaseManager() # 初始化数据库管理器
        self.config_manager = ConfigManager() # 加载settings.json

        window_settings = self.config_manager.get_setting("window", {})
        self.setGeometry(
            window_settings.get("default_x", 100),
            window_settings.get("default_y", 100),
            window_settings.get("default_width", 1280),
            window_settings.get("default_height", 720)
        )
        self.setMinimumSize(
            window_settings.get("min_width", 800),
            window_settings.get("min_height", 600)
        )

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 初始化视图 (现在只是骨架)
        self.timeline_list_view = TimelineListView(self.db_manager, self.config_manager, self)
        self.segment_carousel_view = SegmentCarouselView(self.db_manager, self.config_manager, self)
        self.segment_detail_view = SegmentDetailView(self.db_manager, self.config_manager, self)

        self.stacked_widget.addWidget(self.timeline_list_view)
        self.stacked_widget.addWidget(self.segment_carousel_view)
        self.stacked_widget.addWidget(self.segment_detail_view)

        # 连接视图切换的信号 (示例，具体信号在视图类中定义)
        self.timeline_list_view.timeline_selected.connect(self.show_segment_carousel)
        self.segment_carousel_view.segment_selected.connect(self.show_segment_detail)
        self.segment_carousel_view.back_to_timeline_list.connect(self.show_timeline_list)
        self.segment_detail_view.back_to_carousel.connect(self.show_segment_carousel_from_detail)


        self.show_timeline_list() # 初始显示时间轴列表
        logger.info(f"{APP_NAME} MainWindow initialized.")

    def show_timeline_list(self):
        logger.debug("Showing Timeline List View")
        self.stacked_widget.setCurrentWidget(self.timeline_list_view)
        if hasattr(self.timeline_list_view, 'load_data'): # 检查方法是否存在
            self.timeline_list_view.load_data() # 视图加载/刷新数据

    def show_segment_carousel(self, timeline_id):
        logger.debug(f"Showing Segment Carousel View for timeline_id: {timeline_id}")
        self.stacked_widget.setCurrentWidget(self.segment_carousel_view)
        if hasattr(self.segment_carousel_view, 'load_data'):
            self.segment_carousel_view.load_data(timeline_id)

    def show_segment_carousel_from_detail(self, timeline_id): # 从详情返回时
        self.show_segment_carousel(timeline_id)


    def show_segment_detail(self, segment_id, timeline_id, initial_mode=None): # 添加timeline_id
        logger.debug(f"Showing Segment Detail View for segment_id: {segment_id}, timeline_id: {timeline_id}")
        self.stacked_widget.setCurrentWidget(self.segment_detail_view)
        if hasattr(self.segment_detail_view, 'load_data'):
            self.segment_detail_view.load_data(segment_id, timeline_id, initial_mode)


    def closeEvent(self, event):
        """确保在关闭窗口时关闭数据库连接"""
        logger.info("Closing application...")
        self.db_manager.close_connection()
        event.accept()