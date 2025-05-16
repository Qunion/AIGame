from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,QListWidget, QListWidgetItem, QInputDialog, QMenu, QMessageBox) # 增加QMenu, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon # <<<<<<<<<<<<<<<<<<<<<<<<<<<< 添加 QIcon 导入

import logging
from typing import Optional # <<<<<<<<<<<<<<<<<<<<<<<<<<<< 添加 Optional 导入
from ..core.timeline import Timeline
from .dialogs import NewTimelineDialog, confirm_dialog

logger = logging.getLogger(__name__)

class TimelineListItem(QListWidgetItem):
    def __init__(self, timeline: Timeline, parent=None):
        super().__init__(timeline.name, parent)
        self.timeline = timeline

class TimelineListView(QWidget):
    timeline_selected = pyqtSignal(int)
    new_timeline_created_and_selected = pyqtSignal(int, bool)

    def __init__(self, db_manager, config_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.parent_window = parent

        main_layout = QVBoxLayout(self)

        top_button_layout = QHBoxLayout()
        self.add_timeline_button = QPushButton(" 新建时间轴") # 加空格
        self.add_timeline_button.setIcon(QIcon(":/assets/icons/common_add.png")) # << MODIFIED
        self.add_timeline_button.clicked.connect(self.handle_add_timeline)
        top_button_layout.addWidget(self.add_timeline_button)
        top_button_layout.addStretch()
        main_layout.addLayout(top_button_layout)

        self.timeline_list_widget = QListWidget()
        self.timeline_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }")
        self.timeline_list_widget.itemDoubleClicked.connect(self.handle_timeline_double_clicked)
        # 启用右键菜单策略
        self.timeline_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.timeline_list_widget.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.timeline_list_widget)

        bottom_button_layout = QHBoxLayout()
        self.settings_button = QPushButton(" 设置") # 加空格
        self.settings_button.setIcon(QIcon(":/assets/icons/common_settings.png")) # << MODIFIED
        self.dev_info_button = QPushButton(" 开发者信息") # 加空格
        self.dev_info_button.setIcon(QIcon(":/assets/icons/common_developer_info.png")) # << MODIFIED
        self.settings_button.setEnabled(False)
        self.dev_info_button.setEnabled(False)
        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.settings_button)
        bottom_button_layout.addWidget(self.dev_info_button)
        main_layout.addLayout(bottom_button_layout)

        logger.debug("TimelineListView initialized.")
        self.load_data()

    def load_data(self):
        logger.debug("TimelineListView loading data...")
        self.timeline_list_widget.clear()
        timelines = self.db_manager.get_all_timelines()
        if not timelines:
            no_timeline_item = QListWidgetItem("没有时间轴，点击上方按钮创建新的记忆宫殿吧！")
            no_timeline_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            no_timeline_item.setFlags(no_timeline_item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled) # 不可选，灰色
            self.timeline_list_widget.addItem(no_timeline_item)
        for tl in timelines:
            item = TimelineListItem(tl)
            self.timeline_list_widget.addItem

    def handle_add_timeline(self):
        logger.debug("Add timeline button clicked.")
        dialog = NewTimelineDialog(self)
        if dialog.exec():
            timeline_name = dialog.get_timeline_name()
            if timeline_name:
                new_timeline = Timeline(name=timeline_name, default_memory_mode="view")
                new_timeline_id = self.db_manager.add_timeline(new_timeline)
                if new_timeline_id is not None:
                    default_segment_id = self.db_manager.create_default_segment_for_timeline(
                        new_timeline_id, self.config_manager
                    )
                    if default_segment_id:
                        logger.info(f"Default segment (ID: {default_segment_id}) created for new timeline '{timeline_name}'.")
                    else:
                        logger.warning(f"Could not create default segment for new timeline '{timeline_name}'.")

                    logger.info(f"New timeline '{timeline_name}' created with ID: {new_timeline_id}.")
                    self.load_data()
                    self.new_timeline_created_and_selected.emit(new_timeline_id, True)
                else:
                    QMessageBox.critical(self, "错误", f"创建时间轴 '{timeline_name}' 失败。")
            else:
                QMessageBox.warning(self, "警告", "时间轴名称不能为空。")

    def handle_timeline_double_clicked(self, item: QListWidgetItem): # 参数类型改为 QListWidgetItem
        if isinstance(item, TimelineListItem) and item.timeline.id is not None:
            logger.debug(f"Timeline item double-clicked: {item.timeline.name} (ID: {item.timeline.id})")
            self.timeline_selected.emit(item.timeline.id)
        elif not isinstance(item, TimelineListItem) and item.flags() & Qt.ItemFlag.ItemIsEnabled:
            logger.debug(f"Non-TimelineListItem double-clicked: {item.text()}")
            # 如果是其他类型的可点击项（虽然目前没有），可以在这里处理
        else:
            logger.warning(f"Invalid item double-clicked or timeline ID is None. Item text: {item.text()}")


    def show_context_menu(self, position):
        item = self.timeline_list_widget.itemAt(position)
        if isinstance(item, TimelineListItem) and item.timeline.id is not None: # 确保是有效的时间轴项
            menu = QMenu(self)
            rename_action = menu.addAction(QIcon(":/assets/icons/common_edit_pencil.png"), "重命名") # 添加图标
            delete_action = menu.addAction(QIcon(":/assets/icons/common_delete_trash.png"), "删除") # 添加图标
            
            # 可以在这里添加更多操作，例如 "设为默认" 等
            # duplicate_action = menu.addAction("复制时间轴")
            # export_action = menu.addAction("导出时间轴")

            action = menu.exec(self.timeline_list_widget.mapToGlobal(position))

            if action == rename_action:
                self.handle_rename_timeline(item.timeline)
            elif action == delete_action:
                self.handle_delete_timeline(item.timeline)
            # elif action == duplicate_action:
                # self.handle_duplicate_timeline(item.timeline)
            # elif action == export_action:
                # self.handle_export_timeline(item.timeline)


    def handle_rename_timeline(self, timeline: Timeline):
        if timeline.id is None: return
        new_name, ok = QInputDialog.getText(self, "重命名时间轴", "新名称:", QLineEdit.EchoMode.Normal, timeline.name)
        if ok and new_name.strip() and new_name.strip() != timeline.name:
            old_name = timeline.name
            timeline.name = new_name.strip()
            if self.db_manager.update_timeline(timeline):
                self.load_data()
                logger.info(f"Timeline ID {timeline.id} renamed from '{old_name}' to '{timeline.name}'.")
            else:
                QMessageBox.critical(self, "错误", f"重命名时间轴 '{timeline.name}' 失败。")
                timeline.name = old_name # 恢复，以防UI和服务端不一致
        elif ok and not new_name.strip():
            QMessageBox.warning(self, "警告", "时间轴名称不能为空。")


    def handle_delete_timeline(self, timeline: Timeline):
        if timeline.id is None: return
        if confirm_dialog(self, "确认删除", f"确定要删除时间轴 '{timeline.name}' 吗？\n此操作将同时删除其下所有片段和节点，且无法恢复。"):
            timeline_id_to_delete = timeline.id
            timeline_name_deleted = timeline.name
            if self.db_manager.delete_timeline(timeline_id_to_delete):
                self.load_data()
                logger.info(f"Timeline ID {timeline_id_to_delete} ('{timeline_name_deleted}') deleted.")
            else:
                QMessageBox.critical(self, "错误", f"删除时间轴 '{timeline_name_deleted}' 失败。")