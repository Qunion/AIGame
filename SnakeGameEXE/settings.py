import pygame
import os

# --- Core Settings ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
WINDOW_TITLE = "增强版贪吃蛇" # Changed to Chinese
FPS = 60 # Target frames per second

# --- Grid & Canvas ---
# Canvas grid dimensions match the screen aspect ratio better
CANVAS_GRID_WIDTH = 71
CANVAS_GRID_HEIGHT = 40

# Calculate GRID_SIZE to fit the canvas onto the screen
# Use the dimension that restricts the size the most
GRID_SIZE_W = SCREEN_WIDTH // CANVAS_GRID_WIDTH
GRID_SIZE_H = SCREEN_HEIGHT // CANVAS_GRID_HEIGHT
GRID_SIZE = min(GRID_SIZE_W, GRID_SIZE_H) # Use the smaller size to ensure fit (likely 27)

# Canvas size in pixels is now the same as the grid dimensions * GRID_SIZE
# This might not perfectly match SCREEN_WIDTH/HEIGHT if GRID_SIZE caused rounding.
# We'll draw centered or with black bars if needed, handled in drawing.
CANVAS_WIDTH_PX = CANVAS_GRID_WIDTH * GRID_SIZE
CANVAS_HEIGHT_PX = CANVAS_GRID_HEIGHT * GRID_SIZE

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
YELLOW = (255, 255, 0)
DARK_YELLOW = (200, 200, 0) # Base snake color
GREY = (128, 128, 128)
# Adjusted alpha slightly for potentially smaller grid lines
GRID_COLOR = (200, 200, 200, 80) # Light grey with transparency

# --- Game Mechanics - TUNABLE PARAMETERS ---
INITIAL_SNAKE_LENGTH = 3
# Adjusted base speed: Since grid size is halved, double steps/sec for same visual speed
BASE_SNAKE_SPEED_PPS = 10.0 # Grids per second at the start 【调试编辑】<- Adjusted
ACCELERATION_FACTOR = 1.5 # Multiplier when Shift is pressed (50% increase) 【调试编辑】
SPLIT_MIN_LENGTH = 2
CORPSE_LIFESPAN_SECONDS = 43 # 【调试编辑】
CORPSE_FLICKER_START_OFFSET = 30 # 【调试编辑】
CORPSE_Flicker_DURATION_SECONDS = 3 # 【调试编辑】
CORPSE_FADE_DURATION_SECONDS = 10 # 【调试编辑】
REWIND_SECONDS = 10       # 【调试编辑】
GRADUAL_HEAT_INTERVAL_SECONDS = 10 # 【调试编辑】
GRADUAL_HEAT_INCREASE_PERCENT = 0.02 # 【调试编辑】
FRENZY_INTERVAL_SECONDS = 60 # 【调试编辑】
FRENZY_DURATION_SECONDS = 10   # 【调试编辑】
FRENZY_PEAK_BONUS_PERCENT = 0.20 # 【调试编辑】
FRENZY_RAMP_UP_SECONDS = 2     # 【调试编辑】
FRENZY_RAMP_DOWN_SECONDS = 2   # 【调试编辑】
FRUIT_SPAWN_INTERVAL_SECONDS = 5 # 【调试编辑】
MAX_FRUITS = 10            # 【调试编辑】
HEALTHY_FRUIT_DURATION_SECONDS = 30 # 【调试编辑】
BOMB_FRUIT_DURATION_SECONDS = 30    # 【调试编辑】
PINKY_SPAWN_LENGTH = 10    # 【调试编辑】
GHOST_BASE_SPEED_FACTOR = 0.5 # 【调试编辑】<- Relative speed remains same %
GHOST_TARGET_UPDATE_INTERVAL_MS = 500 # 【调试编辑】
PINKY_PREDICTION_DISTANCE = 4 # 【调试编辑】
GHOST_WARNING_DISTANCE_GRIDS = 3 # 【调试编辑】
SNAKE_ALPHA_DECREASE_PER_SEGMENT = 0.02 # 【调试编辑】
MERGE_IMMUNITY_SECONDS = 0.15 # Small delay after split before corpse can be merged 【调试编辑】 <- New setting for split/merge fix


# --- Asset Paths ---
ASSET_DIR = os.path.join(os.path.dirname(__file__), 'assets')
IMG_DIR = os.path.join(ASSET_DIR, 'images')
SOUND_DIR = os.path.join(ASSET_DIR, 'sounds')

# --- Game States ---
STATE_PLAYING = 0
STATE_GAME_OVER = 1
STATE_PAUSED = 2

# --- Helper Functions ---
def scale_image(image, size):
    """Scales a Pygame surface."""
    # Ensure size is at least 1x1
    safe_size = max(1, size)
    return pygame.transform.scale(image, (safe_size, safe_size))

def load_image(filename, size=None, use_alpha=True):
    """Loads an image, scales it using GRID_SIZE if size is not specified, and handles errors."""
    path = os.path.join(IMG_DIR, filename)
    effective_size = size if size is not None else GRID_SIZE # Use GRID_SIZE if no specific size given

    try:
        image = pygame.image.load(path)
        if use_alpha:
            image = image.convert_alpha()
        else:
            image = image.convert()
        if effective_size: # Scale if an effective size is determined
            image = scale_image(image, effective_size)
        return image
    except pygame.error as e:
        print(f"Warning: Could not load image '{filename}': {e}")
        placeholder = pygame.Surface((effective_size if effective_size else 10, effective_size if effective_size else 10))
        placeholder.fill(RED)
        # Draw lines only if size is large enough
        if placeholder.get_width() > 1 and placeholder.get_height() > 1:
            pygame.draw.line(placeholder, BLACK, (0,0), (placeholder.get_width()-1, placeholder.get_height()-1), 1)
            pygame.draw.line(placeholder, BLACK, (0, placeholder.get_height()-1), (placeholder.get_width()-1, 0), 1)
        return placeholder
    except FileNotFoundError:
        print(f"Warning: Image file not found '{filename}'")
        placeholder = pygame.Surface((effective_size if effective_size else 10, effective_size if effective_size else 10))
        placeholder.fill(BLUE)
        if placeholder.get_width() > 1 and placeholder.get_height() > 1:
             pygame.draw.line(placeholder, WHITE, (0,0), (placeholder.get_width()-1, placeholder.get_height()-1), 1)
             pygame.draw.line(placeholder, WHITE, (0, placeholder.get_height()-1), (placeholder.get_width()-1, 0), 1)
        return placeholder


def load_sound(filename):
    """Loads a sound and handles errors."""
    path = os.path.join(SOUND_DIR, filename)
    if not pygame.mixer or not pygame.mixer.get_init():
        print("Warning: Mixer module not initialized. Cannot load sound.")
        return None
    try:
        sound = pygame.mixer.Sound(path)
        return sound
    except pygame.error as e:
        print(f"Warning: Could not load sound '{filename}': {e}")
        return None
    except FileNotFoundError:
        print(f"Warning: Sound file not found '{filename}'")
        return None

def load_music(filename):
    """Loads background music."""
    path = os.path.join(SOUND_DIR, filename)
    if not pygame.mixer or not pygame.mixer.get_init():
        print("Warning: Mixer module not initialized. Cannot load music.")
        return False
    try:
        pygame.mixer.music.load(path)
        return True
    except pygame.error as e:
        print(f"Warning: Could not load music '{filename}': {e}")
        return False
    except FileNotFoundError:
        print(f"Warning: Music file not found '{filename}'")
        return False

# --- Font ---
# Specify paths to common Chinese fonts on Windows. Adjust if needed for your system.
# SimHei is often available. Microsoft YaHei ('msyh.ttc') is also common.
PRIMARY_FONT_NAME = "simhei.ttf" # Try SimHei first
FALLBACK_FONT_NAME = "msyh.ttc" # Try Microsoft YaHei if SimHei fails

def get_font(size):
    """Attempts to load a Chinese font, falling back to Pygame default."""
    try:
        # Try primary font directly by name (may work if installed system-wide)
        font = pygame.font.SysFont(PRIMARY_FONT_NAME, size)
        print(f"Loaded system font: {PRIMARY_FONT_NAME}")
        return font
    except:
        try:
             # Try fallback font directly by name
            font = pygame.font.SysFont(FALLBACK_FONT_NAME, size)
            print(f"Loaded system font: {FALLBACK_FONT_NAME}")
            return font
        except:
             try:
                 # Try loading primary font from file (relative path)
                 font_path = os.path.join(os.path.dirname(__file__), PRIMARY_FONT_NAME) # Assumes font file is in the same directory
                 if os.path.exists(font_path):
                     font = pygame.font.Font(font_path, size)
                     print(f"Loaded font file: {font_path}")
                     return font
             except Exception as e1:
                 print(f"Could not load font file {PRIMARY_FONT_NAME}: {e1}")
                 pass # Continue to final fallback

             # Final fallback to Pygame's default font
             print(f"Warning: Could not load specified Chinese fonts ({PRIMARY_FONT_NAME}, {FALLBACK_FONT_NAME}). Falling back to default font. Chinese characters may not display correctly.")
             return pygame.font.Font(None, size + 4) # Default font might need size adjustment


# --- Direction Vectors ---
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)