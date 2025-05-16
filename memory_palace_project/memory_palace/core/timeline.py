from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Timeline:
    id: Optional[int] = None
    name: str = "未命名时间轴"
    default_memory_mode: Optional[str] = None # 例如 'view', 'edit', 'explore_fog'
    cover_icon_data: Optional[str] = None # 存储图标描述 (如SVG路径或参数)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 可以添加一些辅助方法，例如
    def __str__(self):
        return f"Timeline(id={self.id}, name='{self.name}')"