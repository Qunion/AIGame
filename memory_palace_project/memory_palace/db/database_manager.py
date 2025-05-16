import sqlite3
import os
import logging
from ..utils.constants import DATABASE_PATH, DATA_DIR

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self._ensure_db_directory_exists()
        self.conn = None # 连接将在需要时建立
        self._create_tables_if_not_exists()

    def _ensure_db_directory_exists(self):
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
                logger.info(f"Database directory created at: {db_dir}")
            except OSError as e:
                logger.error(f"Error creating database directory {db_dir}: {e}")
                # 在这种情况下，应用可能无法正常运行，可以考虑抛出异常或退出

    def get_connection(self):
        """获取数据库连接，如果不存在则创建"""
        if self.conn is None or self.conn.total_changes == -1: # 检查连接是否关闭
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row # 允许按列名访问数据
                logger.info(f"Database connection established to: {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Error connecting to database {self.db_path}: {e}")
                self.conn = None # 确保连接状态正确
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
            conn.rollback() # 出错时回滚
            return False
        # finally: # 不在这里关闭连接，让调用者管理
        #     self.close_connection()


    def _create_tables_if_not_exists(self):
        # 使用PRAGMA foreign_keys=ON; 来启用外键约束
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
            background_image_path TEXT,
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
            detail TEXT,
            anchor_x_percent REAL NOT NULL CHECK(anchor_x_percent >= 0 AND anchor_x_percent <= 1),
            anchor_y_percent REAL NOT NULL CHECK(anchor_y_percent >= 0 AND anchor_y_percent <= 1),
            current_width_px REAL,
            current_height_px REAL,
            max_width_px REAL,
            order_in_segment INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            visual_style_json TEXT,
            FOREIGN KEY (segment_id) REFERENCES Segments(id) ON DELETE CASCADE
        );
        """
        nodememoryprogress_table = """
        CREATE TABLE IF NOT EXISTS NodeMemoryProgress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            timeline_id INTEGER NOT NULL, /* Denormalized for easier querying, ensure consistency */
            user_id INTEGER DEFAULT 1,
            mode TEXT NOT NULL CHECK(mode IN ('explore_fog', 'review_memory', 'recite_dictation')),
            is_completed BOOLEAN DEFAULT FALSE,
            last_completed_at DATETIME,
            extra_data TEXT,
            FOREIGN KEY (node_id) REFERENCES Nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (timeline_id) REFERENCES Timelines(id) ON DELETE CASCADE,
            UNIQUE(node_id, mode) /* 一个节点在一个模式下只有一条进度记录 */
        );
        """
        # 启用外键的PRAGMA应该在每次连接时执行，或者数据库初始化时确保已设置
        # 这里我们通过在脚本开头加入 PRAGMA foreign_keys=ON; 来确保其在表创建时有效
        script = f"""
        PRAGMA foreign_keys=ON;
        {timelines_table}
        {segments_table}
        {nodes_table}
        {nodememoryprogress_table}
        """
        if self._execute_script(script):
            logger.info("Database tables checked/created successfully.")
        else:
            logger.error("Failed to check/create database tables.")

    # --- Placeholder CRUD methods (will be filled later) ---
    def add_timeline(self, name, default_mode=None, cover_icon_data=None):
        # ...
        return None # Return new timeline id or object

    # ... many more CRUD methods to come ...

# 单独测试时使用
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # 测试数据库目录和文件创建
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"DATABASE_PATH: {DATABASE_PATH}")
    db_manager = DatabaseManager()
    # 你可以尝试添加一些数据并查询来验证
    # db_manager.add_timeline("Test Timeline")
    # ...
    db_manager.close_connection()
    print("DatabaseManager test finished.")