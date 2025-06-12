# FILENAME: ui_manager.py

import pygame
import config
import utils

class UIManager:
    def __init__(self, simulation):
        self.sim = simulation
        self.screen_rect = self.sim.screen.get_rect()
        self.is_menu_open = False
        self.menu_rect = None

    def handle_event(self, event):
        """处理与UI相关的事件"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 点击菜单图标
            if self.is_mouse_over_menu_icon(event.pos):
                self.is_menu_open = not self.is_menu_open
                return True

            # 如果菜单打开，处理菜单点击
            if self.is_menu_open and self.menu_rect.collidepoint(event.pos):
                self._handle_menu_click(event.pos)
                self.is_menu_open = False # 点击后关闭
                return True
        return False

    def _handle_menu_click(self, pos):
        """处理在菜单项上的点击"""
        item_height = 40
        # "添加" 按钮
        if pos[1] < self.menu_rect.top + item_height:
            self.sim.add_new_group()
            return
        
        # 组列表
        for i, group in enumerate(self.sim.neuron_groups):
            item_y = self.menu_rect.top + (i + 1) * item_height
            if item_y < pos[1] < item_y + item_height:
                self.sim.switch_group(i)
                break
    
    def is_mouse_over_menu_icon(self, mouse_pos):
        dist_sq = (
            (mouse_pos[0] - config.GROUP_MENU_ICON_POS[0])**2 +
            (mouse_pos[1] - config.GROUP_MENU_ICON_POS[1])**2
        )
        return dist_sq < config.GROUP_MENU_HOVER_RADIUS**2

    def draw(self, surface, mouse_pos):
        """绘制所有UI元素"""
        self.draw_info_panel(surface)
        self.draw_group_menu_icon(surface, mouse_pos)
        if self.is_menu_open:
            self.draw_group_menu(surface)

    def draw_info_panel(self, surface):
        """绘制左上角的信息面板"""
        panel_rect = pygame.Rect(10, 10, 250, 100)
        pygame.draw.rect(surface, config.INFO_PANEL_COLOR, panel_rect, border_radius=10)

        # 动态获取状态文本
        if self.sim.is_loading:
            status_text = "加载中 (Loading)..."
        elif self.sim.paused and self.sim.held_neuron:
            status_text = f"控制中: {self.sim.held_neuron.text}"
        elif self.sim.paused and self.sim.new_neuron_preview:
            status_text = "添加神经元 (Adding Neuron)"
        elif self.sim.paused:
            status_text = "已暂停 (Paused)"
        else:
            status_text = "运行中 (Running)"
            
        group_name = self.sim.neuron_groups[self.sim.active_group_index]['name']
        
        utils.render_text(surface, config.TITLE, (135, 30), 18)
        utils.render_text(surface, f"组: {group_name}", (135, 55), 14)
        utils.render_text(surface, f"数量: {len(self.sim.neurons)}", (135, 75), 14)
        utils.render_text(surface, f"状态: {status_text}", (135, 95), 14)

    def draw_group_menu_icon(self, surface, mouse_pos):
        """绘制右上角的菜单图标"""
        alpha = 200 if self.is_mouse_over_menu_icon(mouse_pos) else 100
        color = (*config.HELD_NEURON_BORDER_COLOR[:3], alpha)
        
        # 绘制汉堡菜单图标
        pos = config.GROUP_MENU_ICON_POS
        for i in range(3):
            y = pos[1] + (i - 1) * 8
            pygame.draw.line(surface, color, (pos[0] - 12, y), (pos[0] + 12, y), 3)

    def draw_group_menu(self, surface):
        """绘制神经元组选择菜单"""
        item_height = 40
        num_items = len(self.sim.neuron_groups) + 1
        menu_height = num_items * item_height
        self.menu_rect = pygame.Rect(self.screen_rect.width - 220, 60, 200, menu_height)

        pygame.draw.rect(surface, config.GROUP_MENU_COLOR, self.menu_rect, border_radius=10)

        # 绘制菜单项
        # 1. 添加新组
        add_rect = pygame.Rect(self.menu_rect.left, self.menu_rect.top, self.menu_rect.width, item_height)
        utils.render_text(surface, "【添加空白神经元组】", add_rect.center, 16)

        # 2. 组列表
        for i, group in enumerate(self.sim.neuron_groups):
            y_pos = self.menu_rect.top + (i + 1) * item_height
            item_rect = pygame.Rect(self.menu_rect.left, y_pos, self.menu_rect.width, item_height)
            if i == self.sim.active_group_index:
                pygame.draw.rect(surface, (255, 255, 255, 30), item_rect) # 高亮当前组
            utils.render_text(surface, group['name'], item_rect.center, 16)
            if i < len(self.sim.neuron_groups) -1 :
                pygame.draw.line(surface, (255,255,255, 50), (item_rect.left + 10, item_rect.bottom), (item_rect.right - 10, item_rect.bottom))