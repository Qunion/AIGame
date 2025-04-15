import pickle
import os
from settings import *
# Import necessary classes - adjust if structure changes
from player import Player
from items import Item, MatchItem, FoodItem, WeaponItem
from monster import Monster # Assuming monster state needs saving

def save_game(game_state, filename=SAVE_FILE):
    """Saves the current game state to a file."""
    try:
        with open(filename, 'wb') as f:
            pickle.dump(game_state, f, pickle.HIGHEST_PROTOCOL)
        print(f"Game state saved to {filename}")
    except Exception as e:
        print(f"Error saving game state: {e}")

def load_game(filename=SAVE_FILE):
    """Loads the game state from a file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                game_state = pickle.load(f)
            print(f"Game state loaded from {filename}")
            return game_state
        except Exception as e:
            print(f"Error loading game state: {e}")
            return None
    else:
        print("No save file found.")
        return None

def capture_game_state(game):
    """Creates a dictionary representing the current state to be saved."""
    state = {
        'player_state': {
            'pos': game.player.pos,
            'hunger': game.player.hunger,
            'matches': list(game.player.matches), # Save remaining frames list
            'current_match_index': game.player.current_match_index,
            'inventory': {
                'weapons': [ # Save weapon type and remaining uses
                    {'type': w.weapon_type, 'uses': w.uses}
                    for w in game.player.inventory['weapons']
                 ]
            },
            'speed_boost_timer': game.player.speed_boost_timer,
            'magic_match_timer': game.player.magic_match_timer,
            # Don't save velocity, timers like hunger_decay_timer (recalculate on load)
        },
        'items_state': [
            {'type': item.item_type, 'pos': item.pos,
             'food_type': getattr(item, 'food_type', None), # getattr safe check
             'weapon_type': getattr(item, 'weapon_type', None)
            }
            for item in game.items # Save items still on the ground
        ],
        'monsters_state': [
             {'name': m.name, 'type': m.monster_type, 'pos': m.pos, 'health': m.health, 'is_active': m.is_active, 'target_pos': m.target_pos}
             for m in game.monsters
        ],
        'maze_state': { # Save essential non-procedural maze info
            'grid_data': [[tile.is_wall for tile in col] for col in game.maze.grid_cells], # Save wall layout
            'exit_pos': game.maze.exit_pos,
            # Player start pos is determined on load or new game
        },
        'lighting_state': {
             'memory_tiles': dict(game.lighting.memory_tiles) # Save memory dict (pos -> (timestamp, brightness))
             # Visible tiles recalculate each frame
        },
        'game_time': pygame.time.get_ticks() # Save current game time for timestamp calculations
    }
    return state

def restore_game_state(game, state):
    """Restores the game from a loaded state dictionary."""
    if not state:
        print("Cannot restore from empty state.")
        return False

    print("Restoring game state...")
    try:
        # --- Restore Player ---
        player_state = state['player_state']
        game.player.pos = pygame.Vector2(player_state['pos'])
        game.player.hunger = player_state['hunger']
        game.player.matches = list(player_state['matches'])
        game.player.current_match_index = player_state['current_match_index']
        game.player.speed_boost_timer = player_state['speed_boost_timer']
        game.player.magic_match_timer = player_state['magic_match_timer']
        # Restore weapons
        game.player.inventory['weapons'] = []
        for w_data in player_state['inventory']['weapons']:
             # Need to create WeaponItem instances again - maybe store only data?
             # For simplicity here, just store data. If WeaponItem instance needed, adjust saving.
             # OR: Assume player picks up *new* items on load? Less ideal.
             # Let's recreate dummy WeaponItem for state tracking:
             temp_weapon = WeaponItem(game, (0,0), w_data['type']) # Pos doesn't matter here
             temp_weapon.uses = w_data['uses']
             game.player.add_weapon(temp_weapon)
             temp_weapon.kill() # Remove from sprite groups, just keep in inventory list

        game.player.rect.center = game.player.pos
        game.player.hit_rect.center = game.player.rect.center
        game.player.is_dead = False # Ensure player is alive on load
        game.player.death_reason = ""


        # --- Restore Maze ---
        maze_state = state['maze_state']
        # Rebuild maze grid based on saved wall data
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                game.maze.grid_cells[x][y].is_wall = maze_state['grid_data'][x][y]
        game.maze.exit_pos = maze_state['exit_pos']
        # Rebuild pathfinding grid
        game.maze.pathfinding_grid_matrix = game.maze._create_pathfinding_matrix()
        game.maze.pathfinding_grid = Grid(matrix=game.maze.pathfinding_grid_matrix)


        # --- Restore Items ---
        # Clear existing items and recreate from saved state
        for item in game.items:
            item.kill()
        for item_data in state['items_state']:
            pos = item_data['pos']
            item_type = item_data['type']
            if item_type == 'match':
                MatchItem(game, pos)
            elif item_type == 'food':
                FoodItem(game, pos, item_data['food_type'])
            elif item_type == 'weapon':
                WeaponItem(game, pos, item_data['weapon_type'])


        # --- Restore Monsters ---
        for m in game.monsters:
             m.kill()
        monster_name_map = { name: mtype for name, mtype in zip(MONSTER_NAMES, MONSTER_TYPES)}
        for m_data in state['monsters_state']:
             # Find the type based on the saved name
             m_type = monster_name_map.get(m_data['name'], 'warrior') # Default guess if name mismatch
             monster = Monster(game, m_data['pos'], m_data['name'], m_type)
             monster.health = m_data['health']
             monster.is_active = m_data['is_active']
             monster.target_pos = pygame.Vector2(m_data['target_pos']) if m_data['target_pos'] else None
             monster.pos = pygame.Vector2(m_data['pos']) # Ensure pos is Vector2
             monster.rect.center = monster.pos
             monster.hit_rect.center = monster.rect.center


        # --- Restore Lighting Memory ---
        saved_time = state.get('game_time', 0)
        current_time = pygame.time.get_ticks()
        time_diff = current_time - saved_time

        game.lighting.memory_tiles.clear()
        # Adjust timestamps when loading
        for pos, (timestamp, brightness) in state['lighting_state']['memory_tiles'].items():
             # Add time elapsed since save to the timestamp
             adjusted_timestamp = timestamp + time_diff
             # Check if memory would have expired during the offline time
             if current_time - adjusted_timestamp < FOW_FORGET_TIME_FRAMES * 1000:
                  game.lighting.memory_tiles[pos] = (adjusted_timestamp, brightness)

        # --- Recalculate FoV on first frame after load ---
        game.lighting.update(game.player)

        print("Game state restored successfully.")
        return True

    except Exception as e:
        print(f"Error restoring game state: {e}")
        # Optionally: Delete the corrupt save file?
        # if os.path.exists(SAVE_FILE):
        #     os.remove(SAVE_FILE)
        return False