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
        self.hovered_group_index = None
        self.group_marked_for_deletion = None

    def handle_event(self, event):
        mouse_pos = event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos()
        
        if self.is_menu_open and self.menu_rect:
            self._update_hover_state(mouse_pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_menu_open:
                if self.menu_rect and self.menu_rect.collidepoint(mouse_pos):
                    self._handle_menu_click(mouse_pos)
                else:
                    self.is_menu_open = False
                    self.group_marked_for_deletion = None
                return True

            if self._is_mouse_over_menu_icon(mouse_pos):
                self.is_menu_open = True
                return True

        return False

    def _update_hover_state(self, mouse_pos):
        self.hovered_group_index = None
        item_height = 40
        for i in range(len(self.sim.neuron_groups)):
            item_y = self.menu_rect.top + (i + 1) * item_height
            item_rect = pygame.Rect(self.menu_rect.left, item_y, self.menu_rect.width, item_height)
            if item_rect.collidepoint(mouse_pos):
                self.hovered_group_index = i
                break

    def _handle_menu_click(self, pos):
        item_height = 40
        if pos[1] < self.menu_rect.top + item_height:
            self.sim.add_new_group()
            self.is_menu_open = False
            return
        
        if self.hovered_group_index is not None:
            delete_icon_rect = self._get_delete_icon_rect(self.hovered_group_index)
            if delete_icon_rect.collidepoint(pos):
                if self.group_marked_for_deletion and self.group_marked_for_deletion[0] == self.hovered_group_index:
                    self.sim.delete_group(self.hovered_group_index)
                    self.group_marked_for_deletion = None
                    self.is_menu_open = False
                else:
                    self.group_marked_for_deletion = (self.hovered_group_index, delete_icon_rect.copy())
                return

        if self.hovered_group_index is not None:
             self.sim.switch_group(self.hovered_group_index)
        
        self.group_marked_for_deletion = None
        self.is_menu_open = False

    def _is_mouse_over_menu_icon(self, mouse_pos):
        dist_sq = ((mouse_pos[0] - config.GROUP_MENU_ICON_POS[0])**2 + (mouse_pos[1] - config.GROUP_MENU_ICON_POS[1])**2)
        return dist_sq < config.GROUP_MENU_HOVER_RADIUS**2

    def draw(self, surface, mouse_pos):
        if self.sim.held_neuron:
            self.draw_delete_zone(surface)
            
        self.draw_info_panel(surface)
        self.draw_group_menu_icon(surface, mouse_pos) # 这个调用导致了错误
        if self.is_menu_open:
            self.draw_group_menu(surface, mouse_pos)
            
    def draw_delete_zone(self, surface):
        rect = config.DELETE_ZONE_RECT
        color = config.DELETE_COLOR if rect.collidepoint(self.sim.held_neuron.position) else (100, 100, 100)
        pygame.draw.rect(surface, color, rect, 3, 10)
        utils.render_text_ui(surface, "删除", rect, color, font_size=30)

    # BUG FIX: 恢复被误删的 draw_group_menu_icon 方法
    def draw_group_menu_icon(self, surface, mouse_pos):
        """绘制右上角的菜单图标（汉堡菜单）。"""
        alpha = 200 if self._is_mouse_over_menu_icon(mouse_pos) or self.is_menu_open else 100
        color = (*config.HELD_NEURON_BORDER_COLOR[:3], alpha)
        
        pos = config.GROUP_MENU_ICON_POS
        for i in range(3):
            y = pos[1] + (i - 1) * 8
            pygame.draw.line(surface, color, (pos[0] - 12, y), (pos[0] + 12, y), 3)
        
    def draw_group_menu(self, surface, mouse_pos):
        item_height = 40; num_items = len(self.sim.neuron_groups) + 1
        menu_height = num_items * item_height
        self.menu_rect = pygame.Rect(self.screen_rect.width - 220, 60, 200, menu_height)
        pygame.draw.rect(surface, config.GROUP_MENU_COLOR, self.menu_rect, border_radius=10)

        add_rect = pygame.Rect(self.menu_rect.left, self.menu_rect.top, self.menu_rect.width, item_height)
        utils.render_text_ui(surface, "【添加空白节点组】", add_rect, config.TEXT_COLOR)

        for i, group in enumerate(self.sim.neuron_groups):
            item_y = self.menu_rect.top + (i + 1) * item_height
            item_rect = pygame.Rect(self.menu_rect.left, item_y, self.menu_rect.width, item_height)
            if i == self.sim.active_group_index: pygame.draw.rect(surface, (255, 255, 255, 30), item_rect)
            utils.render_text_ui(surface, group['name'], item_rect, config.TEXT_COLOR)
            
            if self.hovered_group_index == i:
                delete_icon_rect = self._get_delete_icon_rect(i)
                if self.group_marked_for_deletion and self.group_marked_for_deletion[0] == i:
                    utils.render_text_ui(surface, "!", delete_icon_rect, config.WARNING_COLOR, font_size=24)
                else:
                    utils.render_text_ui(surface, "🗑️", delete_icon_rect, config.DELETE_COLOR, font_size=20)

            if i < len(self.sim.neuron_groups) - 1:
                pygame.draw.line(surface, (255,255,255, 50), (item_rect.left + 10, item_rect.bottom), (item_rect.right - 10, item_rect.bottom))
    
    def _get_delete_icon_rect(self, index):
        item_height = 40
        item_y = self.menu_rect.top + (index + 1) * item_height
        return pygame.Rect(self.menu_rect.right - 40, item_y, 40, item_height)
        
    def draw_info_panel(self, surface):
        panel_rect = pygame.Rect(10, 10, 250, 100)
        pygame.draw.rect(surface, config.INFO_PANEL_COLOR, panel_rect, border_radius=10)
        status_text = "用户交互中" if self.sim.paused_by_user else "运行中"
        try: group_name = self.sim.neuron_groups[self.sim.active_group_index]['name']
        except IndexError: group_name = "无"
        utils.render_text_ui(surface, config.TITLE, pygame.Rect(panel_rect.x, panel_rect.y + 5, panel_rect.width, 25), config.TEXT_COLOR, 18)
        utils.render_text_ui(surface, f"组: {group_name}", pygame.Rect(panel_rect.x, panel_rect.y + 30, panel_rect.width, 20), config.TEXT_COLOR, 14)
        utils.render_text_ui(surface, f"数量: {len(self.sim.neurons)}", pygame.Rect(panel_rect.x, panel_rect.y + 50, panel_rect.width, 20), config.TEXT_COLOR, 14)
        utils.render_text_ui(surface, f"状态: {status_text}", pygame.Rect(panel_rect.x, panel_rect.y + 70, panel_rect.width, 20), config.TEXT_COLOR, 14)