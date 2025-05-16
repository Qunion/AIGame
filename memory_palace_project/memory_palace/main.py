import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QResource # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< IMPORT QResource

# 不再需要导入 assets_rc.py:
# from . import assets_rc # <--- REMOVE OR COMMENT OUT THIS LINE

from .ui.main_window import MainWindow
from .utils.constants import APP_NAME, APP_AUTHOR, LOG_DIR, LOG_FILE_PATH
from .utils.config_manager import ConfigManager

# compiled_assets.rcc 相对于 main.py 的路径
# 假设 main.py 在 memory_palace/ 目录下，compiled_assets.rcc 也在 memory_palace/ 目录下
COMPILED_RESOURCES_PATH = os.path.join(os.path.dirname(__file__), "compiled_assets.rcc")


def setup_logging(config_manager):
    # ... (日志配置代码保持不变) ...
    log_level_str = config_manager.get_setting("logging_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


def main():
    config_manager = ConfigManager()
    setup_logging(config_manager)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {APP_NAME}...")

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< REGISTER THE RESOURCE FILE
    if os.path.exists(COMPILED_RESOURCES_PATH):
        if QResource.registerResource(COMPILED_RESOURCES_PATH):
            logger.info(f"Successfully registered resource file: {COMPILED_RESOURCES_PATH}")
        else:
            logger.error(f"Failed to register resource file: {COMPILED_RESOURCES_PATH}")
            # 可以考虑在这里退出或给出更严重的警告
    else:
        logger.error(f"Compiled resource file not found: {COMPILED_RESOURCES_PATH}. Please run rcc.exe.")
        # 必须要有资源文件才能正常显示图标等
        # sys.exit(1) # 或者让程序继续运行但图标缺失

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    if APP_AUTHOR:
        app.setOrganizationName(APP_AUTHOR)

    main_win = MainWindow()
    main_win.show()

    logger.info(f"{APP_NAME} started successfully.")
    result = app.exec()

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< UNREGISTER THE RESOURCE FILE (可选但良好实践)
    if os.path.exists(COMPILED_RESOURCES_PATH):
        if QResource.unregisterResource(COMPILED_RESOURCES_PATH):
            logger.info(f"Successfully unregistered resource file: {COMPILED_RESOURCES_PATH}")
        else:
            logger.warning(f"Failed to unregister resource file (might have already been unregistered or never registered): {COMPILED_RESOURCES_PATH}")


    sys.exit(result)

if __name__ == '__main__':
    main()