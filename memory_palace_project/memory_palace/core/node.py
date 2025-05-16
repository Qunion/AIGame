from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Node:
    id: Optional[int] = None
    segment_id: Optional[int] = None # 必须关联一个片段
    name: str = "新节点"
    detail: str = ""
    anchor_x_percent: float = 0.5  # 默认居中
    anchor_y_percent: float = 0.5  # 默认居中
    current_width_px: Optional[float] = None
    current_height_px: Optional[float] = None
    max_width_px: Optional[float] = None # 将从settings读取
    order_in_segment: int = 0 # 节点在片段内的排序
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    visual_style_json: Optional[str] = None

    def __str__(self):
        return f"Node(id={self.id}, segment_id={self.segment_id}, name='{self.name}')"