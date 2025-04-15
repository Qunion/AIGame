import pygame
from settings import *
from typing import TYPE_CHECKING
from typing import Optional, Tuple # 导入需要用到的类型提示

if TYPE_CHECKING:
    from player import Player
    from assets import AssetManager

def draw_text(surface: pygame.Surface, text: str, size: int, x: int, y: int,
              color: Tuple[int, int, int] = WHITE,
              font_name: Optional[str] = FONT_NAME, align: str = "topleft"):
    """在指定位置绘制文本。"""
    if font_name is None: # 如果 settings 里 FONT_NAME 匹配失败，会是 None
        font = pygame.font.Font(None, size) # 使用 Pygame 默认字体
    else:
        try:
            font = pygame.font.Font(font_name, size)
        except IOError: # 如果指定的字体文件找不到
            print(f"警告：找不到字体 {font_name}，使用默认字体。")
            font = pygame.font.Font(None, size)

    text_surface = font.render(text, True, color) # 创建文本表面 (抗锯齿)
    text_rect = text_surface.get_rect()       # 获取文本矩形

    # 根据对齐方式设置文本矩形的位置
    if align == "topleft":
        text_rect.topleft = (x, y)
    elif align == "topright":
        text_rect.topright = (x, y)
    elif align == "midtop":
        text_rect.midtop = (x, y)
    elif align == "center":
        text_rect.center = (x, y)
    elif align == "midbottom":
        text_rect.midbottom = (x, y)
    elif align == "bottomleft":
        text_rect.bottomleft = (x, y)
    elif align == "bottomright":
        text_rect.bottomright = (x, y)
    # 可以添加更多对齐选项如 "midleft", "midright"

    surface.blit(text_surface, text_rect) # 将文本绘制到目标表面


def draw_player_hud(surface: pygame.Surface, player: 'Player', assets: 'AssetManager'):
    """绘制玩家状态信息的 HUD (Heads-Up Display)。"""

    # --- 绘制饱食度 ---
    hunger_icon_base = assets.get_image('ui_hunger') # 获取饱食度图标底图
    if hunger_icon_base:
        icon_rect = hunger_icon_base.get_rect()
        icon_rect.top = UI_PADDING
        icon_rect.right = WIDTH // 2 - UI_PADDING * 2 # 在中线左边留出一些间距

        # --- 修改开始: 使用单独的图层进行混合 ---
        # 1. 创建最终要绘制到屏幕上的复合 Surface (SRCALPHA 以支持最终的整体透明度)
        hunger_composite_surface = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
        hunger_composite_surface.fill((0, 0, 0, 0)) # 透明背景

        # 2. 将原始图标绘制到复合 Surface 上 (作为最底层)
        hunger_composite_surface.blit(hunger_icon_base, (0, 0))

        # 3. 创建一个 *单独* 的 Surface 用于绘制进度条本身 (SRCALPHA)
        progress_bar_layer = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
        progress_bar_layer.fill((0, 0, 0, 0)) # 透明背景

        # 4. 计算进度条填充比例和高度 (垂直，从下往上填充)
        fill_ratio = max(0.0, min(1.0, player.hunger / PLAYER_MAX_HUNGER))
        fill_height = int(icon_rect.height * fill_ratio)

        # 5. 定义 *完全不透明* 的进度条颜色 (稍后通过设置 Surface alpha 实现透明)
        HUNGER_COLOR_FG = (185, 165, 0) # 橙色
        HUNGER_COLOR_BG = GREY         # 灰色

        # 6. 在 *进度条图层* 上绘制 *不透明* 的进度条矩形
        # 背景/消耗部分 (在顶部)
        rect_bg = pygame.Rect(0, 0, icon_rect.width, icon_rect.height - fill_height)
        # 填充部分 (在底部)
        rect_fg = pygame.Rect(0, icon_rect.height - fill_height, icon_rect.width, fill_height)

        pygame.draw.rect(progress_bar_layer, HUNGER_COLOR_BG, rect_bg)
        pygame.draw.rect(progress_bar_layer, HUNGER_COLOR_FG, rect_fg)

        # 7. 设置这个 *进度条图层* 的整体透明度为 50% (实现方案 B)
        progress_bar_layer.set_alpha(128)

        # 8. 将这个半透明的进度条图层 *blit* 到复合 Surface 上 (覆盖在图标之上)
        #    blit 会正确地将半透明的进度条与下方的图标进行混合
        hunger_composite_surface.blit(progress_bar_layer, (0, 0))

        # 9. 设置这个 *复合后* 的 Surface (图标 + 半透明进度条) 的整体透明度为 80%
        overall_alpha = int(255 * 0.8) # 约 204
        hunger_composite_surface.set_alpha(overall_alpha)

        # 10. 将最终处理过的、整体半透明的组合元素绘制到主屏幕
        surface.blit(hunger_composite_surface, icon_rect.topleft)

        # 11. 在 *主屏幕* 上，位于 UI 元素位置的正中间，绘制 *不透明* 的饱食度数值文本
        hunger_value = int(player.hunger)
        text_color = WHITE # 数值用白色
        draw_text(surface, f"{hunger_value}", UI_FONT_SIZE + 10, # 文本大小
                  icon_rect.centerx, icon_rect.centery,         # 文本中心位置
                  color=text_color, align="center")             # 文本对齐方式
        # --- 修改结束 ---
        # --- 修改结束 ---

    # --- 绘制火柴 ---
    match_icon = assets.get_image('ui_match')
    if match_icon: # 确保图标已加载
        num_matches = player.get_total_match_count() # 获取火柴总数
        current_burn_percent = player.get_current_match_burn_percentage() # 获取当前燃烧百分比
        # current_match_index 是燃烧中火柴在列表中的索引（从左到右计数）
        # UI 显示是从左到右，列表也是从左到右（0是最新获取，len-1是最旧/燃烧中）
        burning_match_display_index = player.current_match_index # 要显示进度条的图标索引

        # 计算第一个火柴图标的起始 x 坐标（在中线右侧）
        # total_match_width = num_matches * UI_MATCH_WIDTH + max(0, num_matches - 1) * UI_MATCH_SPACING
        start_x = WIDTH // 2 + UI_PADDING * 2 # 在中线右边留出一些间距

        # 绘制每个火柴图标
        for i in range(num_matches):
            match_rect = match_icon.get_rect()
            # 计算当前图标的位置
            match_rect.left = start_x + i * (UI_MATCH_WIDTH + UI_MATCH_SPACING)
            match_rect.top = UI_PADDING

            # 绘制火柴底图
            surface.blit(match_icon, match_rect)

            # 如果这是当前正在燃烧的火柴，绘制进度条覆盖
            if i == burning_match_display_index:
                # --- 修改开始: 使用临时 Surface 实现透明度和新方向 ---
                # 创建一个与火柴图标同样大小，支持 alpha 通道的临时 Surface
                progress_surface = pygame.Surface(match_rect.size, pygame.SRCALPHA)
                progress_surface.fill((0, 0, 0, 0)) # 填充完全透明背景

                # 计算已消耗部分（灰色）的高度，从顶部开始
                consumed_height = int(match_rect.height * (1.0 - current_burn_percent))
                # 计算剩余部分（绿色）的高度
                remaining_height = match_rect.height - consumed_height

                # 定义灰色和绿色矩形在 *临时 Surface* 上的位置
                # 灰色矩形 (已消耗)，在顶部
                rect_consumed = pygame.Rect(0, 0, match_rect.width, consumed_height)
                # 绿色矩形 (剩余)，在灰色下方
                rect_remaining = pygame.Rect(0, consumed_height, match_rect.width, remaining_height)

                # 在临时 Surface 上绘制不透明的进度条颜色
                pygame.draw.rect(progress_surface, UI_MATCH_PROGRESS_COLOR_BG, rect_consumed) # 灰色
                pygame.draw.rect(progress_surface, UI_MATCH_PROGRESS_COLOR_FG, rect_remaining) # 绿色

                # 设置整个临时 Surface 的透明度为 50% (128 / 255)
                progress_surface.set_alpha(128)

                # 将半透明的进度条 Surface 绘制到主屏幕上，覆盖在火柴底图之上
                surface.blit(progress_surface, match_rect.topleft)
                # --- 修改结束 ---

    # --- 绘制武器指示器 (可选) ---
    if player.inventory['weapons']: # 如果玩家有武器
         weapon = player.inventory['weapons'][0] # 获取第一把武器（按获取顺序）
         # 根据武器类型获取对应图片
         weapon_key = 'weapon_sword_broken' if weapon.weapon_type == 'broken' else 'weapon_sword_good'
         weapon_img_orig = assets.get_image(weapon_key)
         if weapon_img_orig:
              # 为 HUD 缩小武器图标
              hud_weapon_img = pygame.transform.scale(weapon_img_orig, (UI_MATCH_WIDTH * 2, UI_MATCH_HEIGHT // 2))
              hud_weapon_rect = hud_weapon_img.get_rect()
              # 定位在屏幕右下角
              hud_weapon_rect.bottomright = (WIDTH - UI_PADDING, HEIGHT - UI_PADDING)
              surface.blit(hud_weapon_img, hud_weapon_rect)
              # 在旁边显示剩余使用次数
              draw_text(surface, f"x{weapon.uses}", UI_FONT_SIZE,
                        hud_weapon_rect.left - UI_PADDING, hud_weapon_rect.centery, align="midright")


def draw_game_over_screen(surface: pygame.Surface, reason: str, assets: 'AssetManager'):
    """绘制游戏结束画面。"""
    # 绘制一个半透明的黑色遮罩层
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA) # 支持透明度
    overlay.fill((0, 0, 0, 180)) # 黑色，约 70% 不透明度
    surface.blit(overlay, (0, 0))
    # 绘制标题文字
    draw_text(surface, "游戏结束", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 4, color=RED, align="center")
    # 绘制死亡原因
    draw_text(surface, reason, MESSAGE_FONT_SIZE, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
    # 绘制提示信息
    draw_text(surface, "按 R 重新开始, 按 Q 退出", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")

def draw_win_screen(surface: pygame.Surface, assets: 'AssetManager'):
    """绘制游戏胜利画面。"""
    # 绘制一个半透明的绿色遮罩层
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 100, 0, 180)) # 绿色，约 70% 不透明度
    surface.blit(overlay, (0, 0))
    # 绘制胜利标题
    draw_text(surface, "你成功了!", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 4, color=YELLOW, align="center")
    # 绘制胜利信息
    draw_text(surface, "你走出了饥荒迷宫!", MESSAGE_FONT_SIZE, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
    # 绘制提示信息
    draw_text(surface, "按 R 重新开始, 按 Q 退出", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")

def draw_pause_screen(surface: pygame.Surface, assets: 'AssetManager'):
    """绘制游戏暂停画面。"""
    # 绘制一个半透明的灰色遮罩层
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((50, 50, 50, 180)) # 深灰色，约 70% 不透明度
    surface.blit(overlay, (0, 0))
    # 绘制暂停标题
    draw_text(surface, "游戏暂停", MESSAGE_FONT_SIZE * 2, WIDTH / 2, HEIGHT / 2, color=WHITE, align="center")
    # 绘制继续提示
    draw_text(surface, "按 空格键 继续", UI_FONT_SIZE, WIDTH / 2, HEIGHT * 3 / 4, color=WHITE, align="center")