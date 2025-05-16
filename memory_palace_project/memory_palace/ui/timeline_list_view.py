from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QInputDialog
from PyQt6.QtCore import pyqtSignal, Qt
# from PySide6.QtWidgets import ...
# from PySide6.QtCore import pyqtSignal, Qt

import logging
from ..core.timeline import Timeline # 导入Timeline数据类
from .dialogs import NewTimelineDialog, confirm_dialog # 导入对话框

logger = logging.getLogger(__name__)

class TimelineListItem(QListWidgetItem): # 自定义列表项，方便存储Timeline对象
    def __init__(self, timeline: Timeline, parent=None):
        super().__init__(timeline.name, parent) # 显示名称
        self.timeline = timeline # 关联Timeline对象

class TimelineListView(QWidget):
    timeline_selected = pyqtSignal(int) # timeline_id
    # 新增信号，当时间轴创建后，需要主窗口切换并传递新时间轴ID和是否进入编辑状态的标志
    new_timeline_created_and_selected = pyqtSignal(int, bool) # timeline_id, edit_name_mode

    def __init__(self, db_manager, config_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.parent_window = parent

        main_layout = QVBoxLayout(self)

        # 顶部操作按钮区域
        top_button_layout = QHBoxLayout()
        self.add_timeline_button = QPushButton("新建时间轴 (+)")
        self.add_timeline_button.clicked.connect(self.handle_add_timeline)
        top_button_layout.addWidget(self.add_timeline_button)
        top_button_layout.addStretch() # 将按钮推到左边
        main_layout.addLayout(top_button_layout)


        self.timeline_list_widget = QListWidget()
        self.timeline_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }") # 简单样式
        # self.timeline_list_widget.itemClicked.connect(self.handle_timeline_clicked) # 单击选中
        self.timeline_list_widget.itemDoubleClicked.connect(self.handle_timeline_double_clicked) # 双击打开
        main_layout.addWidget(self.timeline_list_widget)

        # (可选的) 底部状态栏或信息区域
        # status_label = QLabel("双击时间轴以打开")
        # main_layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # (可选的) 设置和开发者信息按钮 (与主界面设计图对应)
        bottom_button_layout = QHBoxLayout()
        self.settings_button = QPushButton("设置")
        self.dev_info_button = QPushButton("开发者信息")
        # TODO: 实现这两个按钮的功能
        self.settings_button.setEnabled(False) # MVP 阶段可禁用
        self.dev_info_button.setEnabled(False) # MVP 阶段可禁用
        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.settings_button)
        bottom_button_layout.addWidget(self.dev_info_button)
        main_layout.addLayout(bottom_button_layout)


        logger.debug("TimelineListView initialized.")
        self.load_data() # 初始化时加载数据

    def load_data(self):
        logger.debug("TimelineListView loading data...")
        self.timeline_list_widget.clear()
        timelines = self.db_manager.get_all_timelines()
        if not timelines:
            # 可以显示一个提示，如 "还没有时间轴，点击'新建时间轴'来创建一个吧！"
            # self.timeline_list_widget.addItem(QListWidgetItem("没有时间轴"))
            # self.timeline_list_widget.item(0).setFlags(Qt.ItemFlag.NoItemFlags) # 不可选择
            pass
        for tl in timelines:
            item = TimelineListItem(tl)
            self.timeline_list_widget.addItem(item)
        logger.info(f"Loaded {len(timelines)} timelines.")


    def handle_add_timeline(self):
        logger.debug("Add timeline button clicked.")
        dialog = NewTimelineDialog(self)
        if dialog.exec(): # QDialog.Accepted
            timeline_name = dialog.get_timeline_name()
            if timeline_name:
                # 创建 Timeline 对象
                new_timeline = Timeline(name=timeline_name, default_memory_mode="view") # 默认进入查看模式
                new_id = self.db_manager.add_timeline(new_timeline)
                if new_id is not None:
                    logger.info(f"New timeline '{timeline_name}' created with ID: {new_id}.")
                    self.load_data() # 刷新列表
                    # 切换到新创建的时间轴的片段概览视图，并使其名称进入编辑状态
                    self.new_timeline_created_and_selected.emit(new_id, True) # True表示进入名称编辑模式
                else:
                    QMessageBox.critical(self, "错误", f"创建时间轴 '{timeline_name}' 失败。")
            else:
                QMessageBox.warning(self, "警告", "时间轴名称不能为空。")

    # def handle_timeline_clicked(self, item: TimelineListItem):
    #     if isinstance(item, TimelineListItem):
    #         logger.debug(f"Timeline item clicked: {item.timeline.name} (ID: {item.timeline.id})")
    #         # 可以在这里做一些选中高亮等操作，但主要通过双击打开

    def handle_timeline_double_clicked(self, item: TimelineListItem):
        if isinstance(item, TimelineListItem) and item.timeline.id is not None:
            logger.debug(f"Timeline item double-clicked: {item.timeline.name} (ID: {item.timeline.id})")
            self.timeline_selected.emit(item.timeline.id) # 发送信号给主窗口切换视图
        else:
            logger.warning("Invalid item double-clicked or timeline ID is None.")

    # --- (可选) 重命名和删除功能 ---
    def contextMenuEvent(self, event): # 右键菜单示例
        item = self.timeline_list_widget.itemAt(event.pos())
        if isinstance(item, TimelineListItem):
            menu = QMenu(self)
            rename_action = menu.addAction("重命名")
            delete_action = menu.addAction("删除")
            action = menu.exec(self.mapToGlobal(event.pos()))

            if action == rename_action and item.timeline.id is not None:
                self.handle_rename_timeline(item.timeline)
            elif action == delete_action and item.timeline.id is not None:
                self.handle_delete_timeline(item.timeline)

    def handle_rename_timeline(self, timeline: Timeline):
        if timeline.id is None: return
        new_name, ok = QInputDialog.getText(self, "重命名时间轴", "新名称:", QLineEdit.EchoMode.Normal, timeline.name)
        if ok and new_name.strip() and new_name.strip() != timeline.name:
            timeline.name = new_name.strip()
            if self.db_manager.update_timeline(timeline):
                self.load_data() # 刷新列表
                logger.info(f"Timeline ID {timeline.id} renamed to '{timeline.name}'.")
            else:
                QMessageBox.critical(self, "错误", f"重命名时间轴 '{timeline.name}' 失败。")
        elif ok and not new_name.strip():
            QMessageBox.warning(self, "警告", "时间轴名称不能为空。")


    def handle_delete_timeline(self, timeline: Timeline):
        if timeline.id is None: return
        if confirm_dialog(self, "确认删除", f"确定要删除时间轴 '{timeline.name}' 吗？\n此操作将同时删除其下所有片段和节点，且无法恢复。"):
            if self.db_manager.delete_timeline(timeline.id):
                self.load_data() # 刷新列表
                logger.info(f"Timeline ID {timeline.id} ('{timeline.name}') deleted.")
            else:
                QMessageBox.critical(self, "错误", f"删除时间轴 '{timeline.name}' 失败。")