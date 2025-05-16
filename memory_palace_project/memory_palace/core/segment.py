from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Segment:
    id: Optional[int] = None
    timeline_id: Optional[int] = None # 必须关联一个时间轴
    order_index: int = 0 # 片段在时间轴中的顺序
    background_image_path: Optional[str] = None # 存储在应用数据目录中的背景图副本路径
    background_image_original_width: Optional[int] = None
    background_image_original_height: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    # 未来可以添加字段，如片段名称/摘要 (如果需要直接显示在carousel上)

    def __str__(self):
        return f"Segment(id={self.id}, timeline_id={self.timeline_id}, order={self.order_index}, bg='{self.background_image_path}')"