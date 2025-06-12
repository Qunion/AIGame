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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._is_mouse_over_menu_icon(event.pos):
                self.is_menu_open = not self.is_menu_open
                return True

            if self.is_menu_open and self.menu_rect and self.menu_rect.collidepoint(event.pos):
                self._handle_menu_click(event.pos)
                self.is_menu_open = False
                return True
        return False

    def _handle_menu_click(self, pos):
        item_height = 40
        if pos[1] < self.menu_rect.top + item_height:
            self.sim.add_new_group()
            return
        
        for i, group in enumerate(self.sim.neuron_groups):
            item_y = self.menu_rect.top + (i + 1) * item_height
            if item_y < pos[1] < item_y + item_height:
                self.sim.switch_group(i)
                break
    
    def _is_mouse_over_menu_icon(self, mouse_pos):
        dist_sq = ((mouse_pos[0] - config.GROUP_MENU_ICON_POS[0])**2 + 
                   (mouse_pos[1] - config.GROUP_MENU_ICON_POS[1])**2)
        return dist_sq < config.GROUP_MENU_HOVER_RADIUS**2

    def draw(self, surface, mouse_pos):
        self.draw_info_panel(surface)
        self.draw_group_menu_icon(surface, mouse_pos)
        if self.is_menu_open:
            self.draw_group_menu(surface)

    def draw_info_panel(self, surface):
        """MODIFIED: 使用新的 render_text_ui 函数"""
        panel_rect = pygame.Rect(10, 10, 250, 100)
        pygame.draw.rect(surface, config.INFO_PANEL_COLOR, panel_rect, border_radius=10)

        if self.sim.is_loading: status_text = "加载中..."
        elif self.sim.paused and self.sim.held_neuron: status_text = f"控制中: {self.sim.held_neuron.text}"
        elif self.sim.paused and self.sim.new_neuron_preview: status_text = "添加节点"
        elif self.sim.paused: status_text = "已暂停"
        else: status_text = "运行中"
            
        group_name = self.sim.neuron_groups[self.sim.active_group_index]['name']
        
        title_rect = pygame.Rect(panel_rect.x, panel_rect.y + 5, panel_rect.width, 25)
        utils.render_text_ui(surface, config.TITLE, title_rect, config.TEXT_COLOR, font_size=18)
        
        group_rect = pygame.Rect(panel_rect.x, panel_rect.y + 30, panel_rect.width, 20)
        utils.render_text_ui(surface, f"组: {group_name}", group_rect, config.TEXT_COLOR, font_size=14)

        count_rect = pygame.Rect(panel_rect.x, panel_rect.y + 50, panel_rect.width, 20)
        utils.render_text_ui(surface, f"数量: {len(self.sim.neurons)}", count_rect, config.TEXT_COLOR, font_size=14)
        
        status_rect = pygame.Rect(panel_rect.x, panel_rect.y + 70, panel_rect.width, 20)
        utils.render_text_ui(surface, f"状态: {status_text}", status_rect, config.TEXT_COLOR, font_size=14)

    def draw_group_menu_icon(self, surface, mouse_pos):
        alpha = 200 if self._is_mouse_over_menu_icon(mouse_pos) else 100
        color = (*config.HELD_NEURON_BORDER_COLOR[:3], alpha)
        
        pos = config.GROUP_MENU_ICON_POS
        for i in range(3):
            y = pos[1] + (i - 1) * 8
            pygame.draw.line(surface, color, (pos[0] - 12, y), (pos[0] + 12, y), 3)

    def draw_group_menu(self, surface):
        """MODIFIED: 使用新的 render_text_ui 函数"""
        item_height = 40
        num_items = len(self.sim.neuron_groups) + 1
        menu_height = num_items * item_height
        self.menu_rect = pygame.Rect(self.screen_rect.width - 220, 60, 200, menu_height)

        pygame.draw.rect(surface, config.GROUP_MENU_COLOR, self.menu_rect, border_radius=10)

        add_rect = pygame.Rect(self.menu_rect.left, self.menu_rect.top, self.menu_rect.width, item_height)
        utils.render_text_ui(surface, "【添加空白节点组】", add_rect, config.TEXT_COLOR)

        for i, group in enumerate(self.sim.neuron_groups):
            y_pos = self.menu_rect.top + (i + 1) * item_height
            item_rect = pygame.Rect(self.menu_rect.left, y_pos, self.menu_rect.width, item_height)
            if i == self.sim.active_group_index:
                pygame.draw.rect(surface, (255, 255, 255, 30), item_rect)
            utils.render_text_ui(surface, group['name'], item_rect, config.TEXT_COLOR)
            if i < len(self.sim.neuron_groups) - 1:
                pygame.draw.line(surface, (255,255,255, 50), (item_rect.left + 10, item_rect.bottom), (item_rect.right - 10, item_rect.bottom))