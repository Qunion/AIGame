import pickle
import os
import pygame # 需要导入pygame来处理Vector2等
from settings import *
# 导入 pathfinding Grid 用于恢复寻路网格
from pathfinding.core.grid import Grid
# 导入基础物品类用于类型检查和状态恢复
from items import Item, MatchItem, FoodItem, WeaponItem
# 导入怪物类用于状态恢复
from monster import Monster

# 导入 Marker 类
from markers import Marker # 假设 Marker 在 markers.py

# 解决类型提示的循环导入问题
from typing import TYPE_CHECKING, Dict, Any, List, Tuple, Optional
if TYPE_CHECKING:
    # 这部分只在类型检查时执行，避免运行时循环导入
    from main import Game
    # 定义更具体的类型别名（可选，但有助于可读性）
    GameState = Dict[str, Any]
    PlayerState = Dict[str, Any]
    ItemState = Dict[str, Any]
    MonsterState = Dict[str, Any]
    MazeState = Dict[str, Any]
    LightingState = Dict[str, Any]
    PlacedMarkerState = Dict[str, Any] # 定义放置标记物的状态类型


def save_game(game_state: 'GameState', filename: str = SAVE_FILE):
    """将当前游戏状态保存到文件。"""
    try:
        with open(filename, 'wb') as f:
            pickle.dump(game_state, f, pickle.HIGHEST_PROTOCOL)
        print(f"游戏状态已保存至 {filename}")
    except Exception as e:
        print(f"保存游戏状态时出错: {e}")

def load_game(filename: str = SAVE_FILE) -> Optional['GameState']:
    """从文件加载游戏状态。"""
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                # 类型注解帮助调用者理解返回值类型
                game_state: 'GameState' = pickle.load(f)
            print(f"游戏状态已从 {filename} 加载")
            return game_state
        except Exception as e:
            print(f"加载游戏状态时出错: {e}")
            # 如果加载失败，可以考虑删除损坏的存档文件
            # try:
            #     os.remove(filename)
            # except OSError:
            #     pass
            return None
    else:
        print("未找到存档文件。")
        return None

def capture_game_state(game: 'Game') -> 'GameState':
    """创建一个代表当前游戏状态的字典以供保存。"""
    player_state: 'PlayerState' = {
        'pos': tuple(game.player.pos), # Vector2 不能直接序列化，转为元组
        'hunger': game.player.hunger,
        'matches': list(game.player.matches), # 保存剩余帧数列表
        'current_match_index': game.player.current_match_index,
        'inventory': {
            'weapons': [ # 保存武器类型和剩余使用次数
                {'type': w.weapon_type, 'uses': w.uses}
                for w in game.player.inventory['weapons']
            ]
        },
        'markers': list(game.player.markers), # 新增：保存持有的标记物列表
        'speed_boost_timer': game.player.speed_boost_timer,
        'magic_match_timer': game.player.magic_match_timer,
        # 不保存速度、各种计时器（如hunger_decay_timer），这些在加载时重置或重新计算
    }
    items_state: List['ItemState'] = [
        {'type': item.item_type, 'pos': tuple(item.pos), # 位置转为元组
         'food_type': getattr(item, 'food_type', None), # 安全地获取属性
         'weapon_type': getattr(item, 'weapon_type', None)
         }
        for item in game.items # 保存仍在地面上的物品
    ]
    monsters_state: List['MonsterState'] = [
        {'name': m.name, 'type': m.monster_type, 'pos': tuple(m.pos), 'health': m.health, # 位置转为元组
         'is_active': m.is_active, 'target_pos': tuple(m.target_pos) if m.target_pos else None} # 目标位置也转为元组
        for m in game.monsters
    ]
        # --- 新增：保存已放置的标记物状态 ---
    placed_markers_state: List['PlacedMarkerState'] = [
        {'marker_id': m.marker_id, 'pos': tuple(m.pos)} # 保存 ID 和位置
        for m in game.markers_placed # 遍历已放置标记物组
    ]
    # ---------------------------------
    maze_state = {
        'grid_data': [[tile.is_wall for tile in col] for col in game.maze.grid_cells], # 保存墙体布局
        'exit_pos': game.maze.exit_pos,
        # 新增：保存地形和装饰物信息 (如果需要精确恢复)
        'biome_ids': [[tile.biome_id for tile in col] for col in game.maze.grid_cells],
        'decoration_ids': [[tile.decoration_id for tile in col] for col in game.maze.grid_cells], # 注意 tile.decoration_id 现在是字符串或None
    }
    lighting_state: 'LightingState' = {
        'memory_tiles': dict(game.lighting.memory_tiles) # 保存记忆字典 (pos -> (timestamp, brightness))
        # 可见瓦片每帧都会重新计算，无需保存
    }
    state: 'GameState' = {
        'player_state': player_state,
        'items_state': items_state,
        'monsters_state': monsters_state,
        'placed_markers_state': placed_markers_state, # 新增
        'maze_state': maze_state,
        'lighting_state': lighting_state,
        'game_time': pygame.time.get_ticks() # 保存当前游戏时间戳，用于恢复计时器
    }
    return state

def restore_game_state(game: 'Game', state: 'GameState') -> bool:
    """从加载的状态字典恢复游戏。"""
    if not state:
        print("无法从空状态恢复。")
        return False

    print("正在恢复游戏状态...")
    try:
        # --- 恢复玩家 ---
        player_state = state['player_state']
        game.player.pos = pygame.Vector2(player_state['pos']) # 从元组恢复 Vector2
        game.player.hunger = player_state['hunger']
        game.player.matches = list(player_state['matches'])
        game.player.current_match_index = player_state['current_match_index']
        game.player.markers = list(player_state.get('markers', [])) # 新增：恢复持有的标记物 (使用 get 提供向后兼容)
        game.player.speed_boost_timer = player_state['speed_boost_timer']
        game.player.magic_match_timer = player_state['magic_match_timer']
        # 恢复武器
        game.player.inventory['weapons'] = []
        for w_data in player_state['inventory']['weapons']:
            # 为了简化，这里重新创建武器对象实例
            # 注意：这会创建一个新的Sprite，需要立即从所有组中移除，只保留在库存列表中
            # (WeaponItem构造函数会自动添加到组中)
            temp_weapon = WeaponItem(game, (0,0), w_data['type']) # 位置无关紧要
            temp_weapon.uses = w_data['uses']
            game.player.inventory['weapons'].append(temp_weapon) # 添加到逻辑库存
            temp_weapon.kill() # 立即从所有精灵组中移除
        game.player.speed_boost_timer = player_state['speed_boost_timer']
        game.player.magic_match_timer = player_state['magic_match_timer']
        # ... (重置状态和计时器) ...

        # 更新玩家位置相关的rect
        game.player.rect.center = game.player.pos
        game.player.hit_rect.center = game.player.rect.center
        # 重置状态
        game.player.is_dead = False
        game.player.death_reason = ""
        game.player.vel = pygame.Vector2(0, 0) # 速度清零
        game.player.hunger_decay_timer = 0 # 重置计时器
        game.player.hunger_warn_timer = 0
        game.player.match_out_timer = 0
        game.player.footstep_timer = 0.0 # 重置脚步声计时器

        # --- 恢复迷宫 ---
        maze_state = state['maze_state']
        # 基于保存的墙体数据重建迷宫网格
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                game.maze.grid_cells[x][y].is_wall = maze_state['grid_data'][x][y]
                # 恢复地形和装饰物 ID (如果保存了)
                if 'biome_ids' in maze_state:
                    game.maze.grid_cells[x][y].biome_id = maze_state['biome_ids'][x][y]
                if 'decoration_ids' in maze_state:
                    game.maze.grid_cells[x][y].decoration_id = maze_state['decoration_ids'][x][y]
                    # --- 注意：这里没有重新创建 Decoration 精灵 ---
                    # 如果装饰物是精灵，需要在下面单独恢复
        game.maze.exit_pos = maze_state['exit_pos']
        # 重建寻路网格矩阵和Grid对象
        game.maze.pathfinding_grid_matrix = game.maze._create_pathfinding_matrix()
        # 现在 Grid 已导入，这里可以正常工作了
        game.maze.pathfinding_grid = Grid(matrix=game.maze.pathfinding_grid_matrix)


        # --- 恢复物品 ---
        # 清理现有的地面物品精灵，然后从保存的状态重新创建
        for item in game.items:
            item.kill()
        game.items.empty() # 确保组为空
        for item_data in state['items_state']:
            pos = pygame.Vector2(item_data['pos']) # 恢复 Vector2
            item_type = item_data['type']
            if item_type == 'match':
                MatchItem(game, pos)
            elif item_type == 'food':
                FoodItem(game, pos, item_data['food_type'])
            elif item_type == 'weapon':
                # 检查这个武器是否已经被玩家拥有 (通过对比类型和位置? 复杂)
                # 简单处理：只恢复尚未被拾取的武器
                # 或者，假设保存时地上的武器就是未拾取的
                WeaponItem(game, pos, item_data['weapon_type'])


        # --- 恢复怪物 ---
        # 清理现有怪物精灵，然后重新创建
        for m in game.monsters:
            m.kill()
        game.monsters.empty() # 确保组为空
        monster_name_map = { name: mtype for name, mtype in zip(MONSTER_NAMES, MONSTER_TYPES)}
        for m_data in state['monsters_state']:
            m_type = monster_name_map.get(m_data['name'], 'warrior') # 如果名称不匹配则默认
            monster = Monster(game, pygame.Vector2(m_data['pos']), m_data['name'], m_type) # 恢复 Vector2
            monster.health = m_data['health']
            monster.is_active = m_data['is_active']
            monster.target_pos = pygame.Vector2(m_data['target_pos']) if m_data['target_pos'] else None # 恢复 Vector2
            # 更新怪物位置相关的rect
            monster.rect.center = monster.pos
            monster.hit_rect.center = monster.rect.center
        
        # --- 新增：恢复已放置的标记物 ---
        # 先清空现有的（以防万一）
        for m in game.markers_placed: m.kill()
        game.markers_placed.empty()
        # 从状态中重新创建
        if 'placed_markers_state' in state:
            for m_data in state['placed_markers_state']:
                Marker(game, pygame.Vector2(m_data['pos']), m_data['marker_id'])
        # --- 恢复装饰物精灵 (如果之前是精灵的话) ---
        # 如果 Decoration 是精灵，这里需要类似逻辑恢复它们
        # for deco_data in state['decorations_state']:
        #    Decoration(game, ...)

        # --- 恢复光照记忆 ---
        saved_time = state.get('game_time', 0)
        current_time = pygame.time.get_ticks()
        time_diff = current_time - saved_time # 计算离线时间

        game.lighting.memory_tiles.clear()
        # 加载时调整记忆时间戳
        if 'lighting_state' in state and 'memory_tiles' in state['lighting_state']:
            for pos, (timestamp, brightness) in state['lighting_state']['memory_tiles'].items():
                # 将离线时间加到保存的时间戳上
                adjusted_timestamp = timestamp + time_diff
                # 检查在离线期间记忆是否会过期
                # FOW_FORGET_TIME_FRAMES 需要转换为毫秒
                if current_time - adjusted_timestamp < FOW_FORGET_TIME_FRAMES * (1000 / FPS):
                    game.lighting.memory_tiles[pos] = (adjusted_timestamp, brightness)

        # --- 加载后首次更新时重新计算FoV ---
        game.lighting.update(game.player) # 确保视野是最新的

        print("游戏状态恢复成功。")
        return True

    except Exception as e:
        print(f"恢复游戏状态时出错: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误信息        # 可以选择删除损坏的存档文件
        # if os.path.exists(SAVE_FILE):
        #     try: os.remove(SAVE_FILE)
        #     except OSError: pass
        return False