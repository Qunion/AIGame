import os
from appdirs import user_data_dir

APP_NAME = "MemoryPalace"
APP_AUTHOR = "YourOrganization" # 替换或留空

# 获取用户特定的数据目录
# 例如 Windows: C:\Users\<User>\AppData\Local\YourOrganization\MemoryPalace
# macOS: ~/Library/Application Support/MemoryPalace
# Linux: ~/.local/share/MemoryPalace
DATA_DIR = user_data_dir(APP_NAME, APP_AUTHOR)
DATABASE_NAME = "memory_palace.sqlite"
DATABASE_PATH = os.path.join(DATA_DIR, "database", DATABASE_NAME) # 完整的数据库文件路径
LOG_DIR = os.path.join(DATA_DIR, "logs")
LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")

SETTINGS_FILE_NAME = "settings.json"
# settings.json 可以放在项目根目录与源代码一起分发，或者也放在DATA_DIR
# 为了方便开发和用户修改，放在项目根目录可能更直接
SETTINGS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), SETTINGS_FILE_NAME)
# 上面这行是假设constants.py在 memory_palace/utils/ 下，settings.json在项目根目录
# 如果settings.json也想放在DATA_DIR，则：
# SETTINGS_FILE_PATH = os.path.join(DATA_DIR, SETTINGS_FILE_NAME)

# 默认资源路径 (用于代码中引用)
DEFAULT_SEGMENT_BACKGROUND_ALIAS = ":/assets/images/default_segment_background.png"
DEFAULT_SOUND_RECITE_SUCCESS_ALIAS = ":/assets/sounds/recite_success.wav"


# 最大宽度常量等可以放在这里或settings.json
DEFAULT_NODE_MAX_WIDTH_PX = 300
