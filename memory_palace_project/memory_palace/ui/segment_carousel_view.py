from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QSizePolicy, QSpacerItem, QMessageBox, QInputDialog) # 增加导入
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon # <<<<<<<<<<<<<<<<<<<<<<<<<<<< 添加 QIcon 导入
# from PySide6.QtWidgets import ...
# from PySide6.QtCore import pyqtSignal, Qt

import logging
from typing import Optional # <<<<<<<<<<<<<<<<<<<<<<<<<<<< 添加 Optional 导入 (如果之前没有)
from ..core.timeline import Timeline
from ..core.segment import Segment # 导入Segment (为后续显示片段做准备)
from .dialogs import confirm_dialog # 导入确认对话框

logger = logging.getLogger(__name__)

class SegmentCarouselView(QWidget):
    segment_selected = pyqtSignal(int, int)
    back_to_timeline_list = pyqtSignal()
    timeline_updated_or_deleted = pyqtSignal()

    def __init__(self, db_manager, config_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.parent_window = parent
        self.current_timeline: Optional[Timeline] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10,10,10,10)

        top_bar_layout = QHBoxLayout()

        self.timeline_name_label = QLabel("时间轴：未加载")
        font = self.timeline_name_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.timeline_name_label.setFont(font)
        top_bar_layout.addWidget(self.timeline_name_label)

        self.timeline_name_edit = QLineEdit()
        self.timeline_name_edit.setFont(font)
        self.timeline_name_edit.hide()
        self.timeline_name_edit.editingFinished.connect(self.save_timeline_name_edit)
        top_bar_layout.addWidget(self.timeline_name_edit)

        self.edit_timeline_name_button = QPushButton()
        self.edit_timeline_name_button.setIcon(QIcon(":/assets/icons/common_edit_pencil.png")) # << MODIFIED
        self.edit_timeline_name_button.setToolTip("编辑时间轴名称")
        self.edit_timeline_name_button.clicked.connect(self.toggle_timeline_name_edit_mode)
        top_bar_layout.addWidget(self.edit_timeline_name_button)

        self.delete_timeline_button = QPushButton()
        self.delete_timeline_button.setIcon(QIcon(":/assets/icons/common_delete_trash.png")) # << MODIFIED
        self.delete_timeline_button.setToolTip("删除当前时间轴")
        self.delete_timeline_button.clicked.connect(self.handle_delete_timeline)
        self.delete_timeline_button.hide()
        top_bar_layout.addWidget(self.delete_timeline_button)

        top_bar_layout.addStretch()

        self.back_button = QPushButton(" 返回列表") # 加空格让图标和文字有间隔
        self.back_button.setIcon(QIcon(":/assets/icons/common_back_arrow.png")) # << MODIFIED
        self.back_button.clicked.connect(self.on_back_button_clicked)
        top_bar_layout.addWidget(self.back_button)

        main_layout.addLayout(top_bar_layout)

        self.carousel_area_label = QLabel("片段轮播区域 (Placeholder)")
        self.carousel_area_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.carousel_area_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.carousel_area_label.setStyleSheet("QLabel { border: 1px solid lightgray; background-color: #f0f0f0; }")
        main_layout.addWidget(self.carousel_area_label)

        bottom_bar_layout = QHBoxLayout()
        self.add_segment_button_bottom_left = QPushButton(" 新建片段") # 加空格
        self.add_segment_button_bottom_left.setIcon(QIcon(":/assets/icons/common_add.png")) # << MODIFIED
        self.add_segment_button_bottom_left.clicked.connect(self.handle_add_segment)
        bottom_bar_layout.addWidget(self.add_segment_button_bottom_left, alignment=Qt.AlignmentFlag.AlignLeft)
        bottom_bar_layout.addStretch()
        main_layout.addLayout(bottom_bar_layout)

        # 移除或注释掉测试按钮，因为它现在可能因为没有片段而报错
        # self.test_button = QPushButton("选择片段 1 (测试)")
        # self.test_button.clicked.connect(self.on_test_button_clicked)
        # layout.addWidget(self.test_button) # layout 变量未定义，这行之前也有问题，已修正
        # main_layout.addWidget(self.test_button) # 将测试按钮添加到主布局

        logger.debug("SegmentCarouselView initialized.")

    def load_data(self, timeline_id: int, edit_name_mode: bool = False):
        self.current_timeline = self.db_manager.get_timeline(timeline_id)
        if not self.current_timeline:
            logger.error(f"Timeline with ID {timeline_id} not found when loading SegmentCarouselView.")
            QMessageBox.critical(self.parent_window, "错误", f"无法加载时间轴 (ID: {timeline_id})。")
            self.back_to_timeline_list.emit()
            return

        logger.debug(f"SegmentCarouselView loading data for timeline: {self.current_timeline.name} (ID: {self.current_timeline.id}), edit_name_mode: {edit_name_mode}...")
        self.update_timeline_name_display()

        if edit_name_mode:
            self.enter_timeline_name_edit_mode()
        else:
            self.exit_timeline_name_edit_mode()

        self.load_segments_for_carousel(self.current_timeline.id)

    def update_timeline_name_display(self):
        if self.current_timeline:
            self.timeline_name_label.setText(f"时间轴：{self.current_timeline.name}")
            self.timeline_name_edit.setText(self.current_timeline.name)

    def toggle_timeline_name_edit_mode(self):
        if self.timeline_name_edit.isVisible():
            self.save_timeline_name_edit()
            # save_timeline_name_edit 内部会调用 exit_timeline_name_edit_mode
        else:
            self.enter_timeline_name_edit_mode()

    def enter_timeline_name_edit_mode(self):
        if not self.current_timeline: return
        self.timeline_name_label.hide()
        self.timeline_name_edit.setText(self.current_timeline.name)
        self.timeline_name_edit.show()
        self.timeline_name_edit.selectAll()
        self.timeline_name_edit.setFocus()
        self.edit_timeline_name_button.setText("保存") # 或者用图标 QIcon(":/assets/icons/common_save.png")
        self.edit_timeline_name_button.setIcon(QIcon()) # 清除编辑图标，或换成保存图标
        self.delete_timeline_button.show()

    def exit_timeline_name_edit_mode(self):
        self.timeline_name_edit.hide()
        self.timeline_name_label.show()
        self.update_timeline_name_display()
        self.edit_timeline_name_button.setText("") # 清除文本
        self.edit_timeline_name_button.setIcon(QIcon(":/assets/icons/common_edit_pencil.png")) # 恢复编辑图标
        self.delete_timeline_button.hide()

    def save_timeline_name_edit(self):
        if not self.current_timeline or not self.timeline_name_edit.isVisible():
            self.exit_timeline_name_edit_mode() # 确保退出编辑模式
            return

        new_name = self.timeline_name_edit.text().strip()
        # 只有当名称实际改变时才保存
        if new_name and new_name != self.current_timeline.name:
            old_name = self.current_timeline.name
            self.current_timeline.name = new_name
            if self.db_manager.update_timeline(self.current_timeline):
                logger.info(f"Timeline ID {self.current_timeline.id} renamed from '{old_name}' to '{new_name}'.")
                self.timeline_updated_or_deleted.emit()
            else:
                QMessageBox.critical(self, "错误", f"重命名时间轴 '{new_name}' 失败。")
                self.current_timeline.name = old_name # 恢复
        elif not new_name and self.current_timeline.name: # 不允许空名称
             QMessageBox.warning(self, "警告", "时间轴名称不能为空。")
             # 不做任何更改，让编辑框保留原名或用户尝试的空名，由exit_timeline_name_edit_mode恢复
        
        self.exit_timeline_name_edit_mode()


    def handle_delete_timeline(self):
        if not self.current_timeline or self.current_timeline.id is None:
            return
        if confirm_dialog(self, "确认删除", f"确定要删除时间轴 '{self.current_timeline.name}' 吗？\n此操作将同时删除其下所有片段和节点，且无法恢复。"):
            timeline_id_to_delete = self.current_timeline.id
            timeline_name_deleted = self.current_timeline.name
            if self.db_manager.delete_timeline(timeline_id_to_delete):
                logger.info(f"Timeline ID {timeline_id_to_delete} ('{timeline_name_deleted}') deleted from SegmentCarouselView.")
                self.current_timeline = None
                self.timeline_updated_or_deleted.emit()
            else:
                QMessageBox.critical(self, "错误", f"删除时间轴 '{timeline_name_deleted}' 失败。")

    def on_back_button_clicked(self):
        if self.timeline_name_edit.isVisible():
            self.save_timeline_name_edit()
        self.back_to_timeline_list.emit()

    def load_segments_for_carousel(self, timeline_id: int):
        logger.debug(f"Loading segments for timeline {timeline_id} into carousel...")
        segments = self.db_manager.get_segments_for_timeline(timeline_id)
        self.carousel_area_label.setText(f"时间轴ID: {timeline_id} - 包含 {len(segments)} 个片段 (轮播区占位)")
        if not segments:
            logger.info(f"No segments found for timeline {timeline_id}.")
        # TODO: 将segments渲染到轮播区域

    def handle_add_segment(self):
        if not self.current_timeline or self.current_timeline.id is None:
            QMessageBox.warning(self, "提示", "请先确保当前已加载一个时间轴。")
            return

        logger.debug(f"Add segment button clicked for timeline: {self.current_timeline.name}")
        new_segment_id = self.db_manager.create_default_segment_for_timeline(
            self.current_timeline.id, self.config_manager
        )
        if new_segment_id:
            logger.info(f"New default segment (ID: {new_segment_id}) added to timeline '{self.current_timeline.name}'.")
            self.load_segments_for_carousel(self.current_timeline.id)
        else:
            QMessageBox.critical(self, "错误", "创建新片段失败。")

    # 占位符方法，用于响应测试按钮
    def on_test_button_clicked(self):
        if self.current_timeline and self.current_timeline.id is not None:
            segments = self.db_manager.get_segments_for_timeline(self.current_timeline.id)
            if segments:
                first_segment_id = segments[0].id
                if first_segment_id is not None:
                     self.segment_selected.emit(first_segment_id, self.current_timeline.id)
                else:
                    logger.warning("First segment has no ID.")
            else:
                QMessageBox.information(self, "提示", "当前时间轴还没有片段。请先新建一个片段。")
                logger.warning(f"No segments in timeline {self.current_timeline.id} to select for test.")
        else:
            logger.warning("Cannot select segment: current_timeline is not set or has no ID.")