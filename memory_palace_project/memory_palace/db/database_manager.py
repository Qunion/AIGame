import sqlite3
import os
import logging
from datetime import datetime, timezone # timezone 用于 UTC
from ..utils.constants import DATABASE_PATH, DATA_DIR
from ..core.timeline import Timeline # 导入Timeline数据类
from typing import Optional, List # 如果你后面也会用到 List 类型提示，可以一并导入

logger = logging.getLogger(__name__)

def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-aware ISO 8601 string."""
    return val.astimezone(timezone.utc).isoformat()

def convert_datetime_iso(val):
    """Convert ISO 8601 string to datetime.datetime object."""
    return datetime.fromisoformat(val.decode())

sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("DATETIME", convert_datetime_iso) # 注意这里的 "DATETIME" 必须与你在CREATE TABLE中使用的类型匹配，或者用一个通用名

class DatabaseManager:
    # ... (之前的 __init__, _ensure_db_directory_exists, get_connection, close_connection, _execute_script, _create_tables_if_not_exists 方法保持不变) ...
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        if self.db_path != ":memory:": # <<<<<<<<<<<< 添加这个判断
            self._ensure_db_directory_exists()
        self.conn = None
        self._create_tables_if_not_exists()

    def _ensure_db_directory_exists(self):
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
                logger.info(f"Database directory created at: {db_dir}")
            except OSError as e:
                logger.error(f"Error creating database directory {db_dir}: {e}")

    def get_connection(self):
        if self.conn is None or self.conn.total_changes == -1:
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
                # 启用外键约束，应该在每次获取新连接时执行
                self.conn.execute("PRAGMA foreign_keys = ON;")
                logger.info(f"Database connection established to: {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Error connecting to database {self.db_path}: {e}")
                self.conn = None
        return self.conn

    def close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed.")

    def _execute_script(self, script):
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.executescript(script)
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error executing script: {e}")
            conn.rollback()
            return False

    def _create_tables_if_not_exists(self):
        timelines_table = """
        CREATE TABLE IF NOT EXISTS Timelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            default_memory_mode TEXT CHECK(default_memory_mode IN ('explore_fog', 'review_memory', 'recite_dictation', 'view', 'edit')),
            cover_icon_data TEXT
        );
        """
        segments_table = """
        CREATE TABLE IF NOT EXISTS Segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeline_id INTEGER NOT NULL,
            order_index INTEGER NOT NULL,
            background_image_path TEXT, /* 实际存储的是复制到应用数据目录后的路径 */
            background_image_original_width INTEGER,
            background_image_original_height INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (timeline_id) REFERENCES Timelines(id) ON DELETE CASCADE
        );
        """
        nodes_table = """
        CREATE TABLE IF NOT EXISTS Nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail TEXT, /* MVP 阶段纯文本 */
            anchor_x_percent REAL NOT NULL CHECK(anchor_x_percent >= 0 AND anchor_x_percent <= 1),
            anchor_y_percent REAL NOT NULL CHECK(anchor_y_percent >= 0 AND anchor_y_percent <= 1),
            current_width_px REAL, /* 当前渲染宽度，可用于恢复状态 */
            current_height_px REAL, /* 当前渲染高度，可用于恢复状态 */
            max_width_px REAL, /* 节点卡片最大宽度，可从settings.json读取默认值 */
            order_in_segment INTEGER NOT NULL, /* 节点在片段内的排序，用于记忆模式 */
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            visual_style_json TEXT, /* 存储节点特定的视觉样式覆盖，JSON格式 */
            FOREIGN KEY (segment_id) REFERENCES Segments(id) ON DELETE CASCADE
        );
        """
        nodememoryprogress_table = """
        CREATE TABLE IF NOT EXISTS NodeMemoryProgress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            timeline_id INTEGER NOT NULL, /* 为了方便查询，冗余存储，确保与node所属timeline一致 */
            user_id INTEGER DEFAULT 1, /* MVP阶段单用户默认为1 */
            mode TEXT NOT NULL CHECK(mode IN ('explore_fog', 'review_memory', 'recite_dictation')),
            is_completed BOOLEAN DEFAULT FALSE,
            last_completed_at DATETIME, /* 上次完成该节点在该模式下的时间 */
            extra_data TEXT, /* JSON格式，用于存储特定模式的额外进度信息，如尝试次数等 */
            FOREIGN KEY (node_id) REFERENCES Nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (timeline_id) REFERENCES Timelines(id) ON DELETE CASCADE,
            UNIQUE(node_id, timeline_id, mode) /* 一个节点在一个时间轴的一个模式下只有一条进度记录 */
        );
        """

        script = f"""
        {timelines_table}
        {segments_table}
        {nodes_table}
        {nodememoryprogress_table}
        """ # 注意：PRAGMA foreign_keys=ON; 移动到 get_connection 中更好
        if self._execute_script(script): # 此处执行时，get_connection会启用外键
            logger.info("Database tables checked/created successfully.")
        else:
            logger.error("Failed to check/create database tables.")


    # --- Timeline CRUD ---
    def add_timeline(self, timeline: Timeline) -> Optional[int]:
        """添加一个新的时间轴到数据库"""
        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Timelines (name, default_memory_mode, cover_icon_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (timeline.name, timeline.default_memory_mode, timeline.cover_icon_data,
                  timeline.created_at, timeline.updated_at))
            conn.commit()
            new_id = cursor.lastrowid
            logger.info(f"Timeline added with id: {new_id}, name: {timeline.name}")
            return new_id
        except sqlite3.Error as e:
            logger.error(f"Error adding timeline '{timeline.name}': {e}")
            conn.rollback()
            return None

    def get_timeline(self, timeline_id: int) -> Optional[Timeline]:
        """根据ID获取一个时间轴"""
        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Timelines WHERE id = ?", (timeline_id,))
            row = cursor.fetchone()
            if row:
                return Timeline(**dict(row)) # 将行数据解包到Timeline对象
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting timeline with id {timeline_id}: {e}")
            return None

    def get_all_timelines(self) -> list[Timeline]:
        """获取所有时间轴"""
        conn = self.get_connection()
        if not conn: return []
        timelines = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Timelines ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                timelines.append(Timeline(**dict(row)))
            return timelines
        except sqlite3.Error as e:
            logger.error(f"Error getting all timelines: {e}")
            return []

    def update_timeline(self, timeline: Timeline) -> bool:
        """更新一个已存在的时间轴"""
        conn = self.get_connection()
        if not conn or timeline.id is None: return False
        timeline.updated_at = datetime.now() # 更新修改时间
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Timelines
                SET name = ?, default_memory_mode = ?, cover_icon_data = ?, updated_at = ?
                WHERE id = ?
            """, (timeline.name, timeline.default_memory_mode, timeline.cover_icon_data,
                  timeline.updated_at, timeline.id))
            conn.commit()
            logger.info(f"Timeline updated with id: {timeline.id}, name: {timeline.name}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating timeline with id {timeline.id}: {e}")
            conn.rollback()
            return False

    def delete_timeline(self, timeline_id: int) -> bool:
        """删除一个时间轴及其所有相关数据 (通过外键的级联删除实现)"""
        conn = self.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            # 由于设置了 ON DELETE CASCADE，删除Timeline会自动删除其Segments, Nodes, NodeMemoryProgress
            cursor.execute("DELETE FROM Timelines WHERE id = ?", (timeline_id,))
            conn.commit()
            logger.info(f"Timeline deleted with id: {timeline_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting timeline with id {timeline_id}: {e}")
            conn.rollback()
            return False

    # --- Segment CRUD (骨架，后续填充) ---
    def add_segment(self, segment): # ...
        pass
    # ...

    # --- Node CRUD (骨架，后续填充) ---
    def add_node(self, node): # ...
        pass
    # ...

    # --- NodeMemoryProgress CRUD (骨架，后续填充) ---
    def update_node_progress(self, progress): # ...
        pass
    # ...

# ... (之前的 if __name__ == '__main__': 测试代码可以保留或修改) ...
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    db_manager = DatabaseManager(db_path=":memory:") # 使用内存数据库进行快速测试

    # 测试 Timeline CRUD
    print("\n--- Testing Timeline CRUD ---")
    new_tl = Timeline(name="My First Awesome Timeline", default_memory_mode="view")
    tl_id = db_manager.add_timeline(new_tl)
    print(f"Added timeline ID: {tl_id}")

    if tl_id:
        retrieved_tl = db_manager.get_timeline(tl_id)
        print(f"Retrieved: {retrieved_tl}")
        assert retrieved_tl is not None and retrieved_tl.name == "My First Awesome Timeline"

        retrieved_tl.name = "My Updated Awesome Timeline"
        retrieved_tl.default_memory_mode = "edit"
        update_success = db_manager.update_timeline(retrieved_tl)
        print(f"Update success: {update_success}")
        if update_success:
            updated_tl_check = db_manager.get_timeline(tl_id)
            print(f"After update: {updated_tl_check}")
            assert updated_tl_check is not None and updated_tl_check.name == "My Updated Awesome Timeline"

    # 测试获取所有
    db_manager.add_timeline(Timeline(name="Another Timeline"))
    all_timelines = db_manager.get_all_timelines()
    print(f"\nAll timelines ({len(all_timelines)}):")
    for tl in all_timelines:
        print(tl)
    assert len(all_timelines) >= 2

    # 测试删除
    if tl_id:
        delete_success = db_manager.delete_timeline(tl_id)
        print(f"\nDelete timeline ID {tl_id} success: {delete_success}")
        assert delete_success
        deleted_tl_check = db_manager.get_timeline(tl_id)
        print(f"After delete, retrieved: {deleted_tl_check}")
        assert deleted_tl_check is None
        all_timelines_after_delete = db_manager.get_all_timelines()
        print(f"All timelines after delete ({len(all_timelines_after_delete)}):")
        for tl in all_timelines_after_delete:
            print(tl)


    db_manager.close_connection()
    print("\nDatabaseManager Timeline CRUD test finished.")