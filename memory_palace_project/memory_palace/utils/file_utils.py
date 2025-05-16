import os
import shutil
import uuid
import logging
from PyQt6.QtGui import QImage, QPixmap, QIcon # QIcon 可能不需要在这里，但在UI部分需要
from PyQt6.QtCore import QFile, QIODevice, Qt # Qt 可能不需要在这里
from typing import Optional, Tuple # <<<<<<<<<<<<<<<<<<<<<<<<<<<< 确保导入了 Optional 和 Tuple

from .constants import DATA_DIR

logger = logging.getLogger(__name__)

def get_timeline_data_dir(timeline_id_str: str) -> str:
    """获取特定时间轴的数据存储目录"""
    return os.path.join(DATA_DIR, "timelines", timeline_id_str)

def get_timeline_background_images_dir(timeline_id_str: str) -> str:
    """获取特定时间轴的背景图片存储目录"""
    return os.path.join(get_timeline_data_dir(timeline_id_str), "background_images")

def copy_image_to_data_dir(source_path_or_qresource_alias: str,
                           timeline_id_str: str,
                           original_filename: Optional[str] = None) -> Tuple[Optional[str], Optional[int], Optional[int]]: # 使用 Tuple
    """
    将图片文件复制到应用数据目录下对应时间轴的背景图片文件夹中。
    返回 (新的文件路径, 原始宽度, 原始高度) 或 (None, None, None) 如果失败。
    source_path_or_qresource_alias: 可以是本地文件系统路径，也可以是Qt资源路径 (e.g., ":/assets/images/default.png")
    """
    target_dir = get_timeline_background_images_dir(timeline_id_str)
    os.makedirs(target_dir, exist_ok=True)

    _, ext = os.path.splitext(original_filename if original_filename else source_path_or_qresource_alias)
    if not ext:
        ext = ".png"

    new_filename = f"segment_bg_{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(target_dir, new_filename)

    width, height = None, None

    try:
        if source_path_or_qresource_alias.startswith(":/"):
            qfile = QFile(source_path_or_qresource_alias)
            if qfile.open(QIODevice.OpenModeFlag.ReadOnly):
                image_data = qfile.readAll().data()
                qfile.close()

                img = QImage()
                if img.loadFromData(image_data):
                    width = img.width()
                    height = img.height()
                    if img.save(target_path):
                        logger.info(f"Image from Qt resource '{source_path_or_qresource_alias}' copied to '{target_path}'")
                        return target_path, width, height
                    else:
                        logger.error(f"Failed to save image data from Qt resource to '{target_path}'")
                else:
                    logger.error(f"Failed to load image data from Qt resource: {source_path_or_qresource_alias}")
            else:
                logger.error(f"Failed to open Qt resource file: {source_path_or_qresource_alias}, Error: {qfile.errorString()}")
        else:
            if os.path.exists(source_path_or_qresource_alias):
                try:
                    img = QImage(source_path_or_qresource_alias)
                    if not img.isNull():
                        width = img.width()
                        height = img.height()
                    else:
                        pix = QPixmap(source_path_or_qresource_alias)
                        if not pix.isNull():
                            width = pix.width()
                            height = pix.height()
                        else:
                             logger.warning(f"Could not determine dimensions of image: {source_path_or_qresource_alias}")
                except Exception as e_img:
                    logger.warning(f"Error getting image dimensions for {source_path_or_qresource_alias}: {e_img}")

                shutil.copy2(source_path_or_qresource_alias, target_path)
                logger.info(f"Image '{source_path_or_qresource_alias}' copied to '{target_path}'")
                return target_path, width, height
            else:
                logger.error(f"Source image file not found: {source_path_or_qresource_alias}")

    except Exception as e:
        logger.error(f"Error copying image to data directory: {e}")

    return None, None, None


def delete_app_data_file(file_path_in_data_dir: str) -> bool:
    """
    删除应用数据目录下的文件 (通常是背景图)。
    file_path_in_data_dir 是相对于 DATA_DIR 的完整路径。
    """
    # if not file_path_in_data_dir or not file_path_in_data_dir.startswith(DATA_DIR):
    #     logger.warning(f"Attempted to delete file outside of data directory or invalid path: {file_path_in_data_dir}")
    #     return False
    # 考虑到 file_path_in_data_dir 可能是由程序生成的绝对路径，直接判断是否存在即可

    try:
        if os.path.exists(file_path_in_data_dir):
            os.remove(file_path_in_data_dir)
            logger.info(f"File deleted: {file_path_in_data_dir}")
            return True
        else:
            logger.warning(f"File not found for deletion: {file_path_in_data_dir}")
            return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path_in_data_dir}: {e}")
        return False