import pygame
import os

# --- Core Settings ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
WINDOW_TITLE = "Enhanced Snake Game"
FPS = 60 # Target frames per second

# --- Grid & Canvas ---
# Calculate grid size based on screen height (aiming for 40 rows vertically in the full canvas)
# The viewable area is roughly 20 rows high.
CANVAS_GRID_WIDTH = 71
CANVAS_GRID_HEIGHT = 40
GRID_SIZE = SCREEN_HEIGHT // 20 # Size of each grid cell in pixels
# Adjust screen size slightly if needed to perfectly fit grid size
# SCREEN_WIDTH = (SCREEN_WIDTH // GRID_SIZE) * GRID_SIZE # Optional: Force screen width to be multiple of GRID_SIZE
# SCREEN_HEIGHT = (SCREEN_HEIGHT // GRID_SIZE) * GRID_SIZE # Optional: Force screen height to be multiple of GRID_SIZE

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
GRID_COLOR = (200, 200, 200, 100) # Light grey with transparency

# --- Game Mechanics - TUNABLE PARAMETERS ---
INITIAL_SNAKE_LENGTH = 3 # Starting length
BASE_SNAKE_SPEED_PPS = 5.0 # Grids per second at the start
ACCELERATION_FACTOR = 1.5 # Multiplier when Shift is pressed (50% increase) 【调试编辑】
SPLIT_MIN_LENGTH = 2     # Minimum length required to split
CORPSE_LIFESPAN_SECONDS = 43 # Total time corpse exists (30s static + 3s flicker + 10s fade) 【调试编辑】
CORPSE_FLICKER_START_OFFSET = 30 # Seconds before flicker starts 【调试编辑】
CORPSE_Flicker_DURATION_SECONDS = 3 # Duration of flickering 【调试编辑】
CORPSE_FADE_DURATION_SECONDS = 10 # Duration of fade out after flicker 【调试编辑】
REWIND_SECONDS = 10       # How far back to rewind 【调试编辑】
GRADUAL_HEAT_INTERVAL_SECONDS = 10 # Time interval for speed increase 【调试编辑】
GRADUAL_HEAT_INCREASE_PERCENT = 0.02 # Speed increase percentage per interval (2%) 【调试编辑】
FRENZY_INTERVAL_SECONDS = 60 # Time between frenzy moments 【调试编辑】
FRENZY_DURATION_SECONDS = 10   # Duration of frenzy 【调试编辑】
FRENZY_PEAK_BONUS_PERCENT = 0.20 # Max speed bonus during frenzy (20%) 【调试编辑】
FRENZY_RAMP_UP_SECONDS = 2     # Time to reach peak frenzy bonus 【调试编辑】
FRENZY_RAMP_DOWN_SECONDS = 2   # Time to return to normal from frenzy 【调试编辑】
FRUIT_SPAWN_INTERVAL_SECONDS = 5 # Interval for spawning new fruits 【调试编辑】
MAX_FRUITS = 10            # Maximum number of fruits on screen 【调试编辑】
HEALTHY_FRUIT_DURATION_SECONDS = 30 # Time healthy fruit stays 【调试编辑】
BOMB_FRUIT_DURATION_SECONDS = 30    # Time bomb fruit stays 【调试编辑】
PINKY_SPAWN_LENGTH = 10    # Length at which Pinky appears 【调试编辑】
GHOST_BASE_SPEED_FACTOR = 0.5 # Ghost speed relative to snake base speed (50%) 【调试编辑】
GHOST_TARGET_UPDATE_INTERVAL_MS = 500 # How often ghosts recalculate target (milliseconds) 【调试编辑】
PINKY_PREDICTION_DISTANCE = 4 # How many grids ahead Pinky targets 【调试编辑】
GHOST_WARNING_DISTANCE_GRIDS = 3 # Distance to trigger warning sound 【调试编辑】
SNAKE_ALPHA_DECREASE_PER_SEGMENT = 0.02 # Transparency increase per segment (2%) 【调试编辑】

# --- Asset Paths ---
ASSET_DIR = os.path.join(os.path.dirname(__file__), 'assets')
IMG_DIR = os.path.join(ASSET_DIR, 'images')
SOUND_DIR = os.path.join(ASSET_DIR, 'sounds')

# --- Game States ---
STATE_PLAYING = 0
STATE_GAME_OVER = 1
STATE_PAUSED = 2 # Optional: If you want pausing

# --- Helper Functions ---
def scale_image(image, size):
    """Scales a Pygame surface."""
    return pygame.transform.scale(image, (size, size))

def load_image(filename, size=None, use_alpha=True):
    """Loads an image, scales it, and handles errors."""
    path = os.path.join(IMG_DIR, filename)
    try:
        image = pygame.image.load(path)
        if use_alpha:
            image = image.convert_alpha() # Use transparency
        else:
            image = image.convert() # No transparency needed (like background)
        if size:
            image = scale_image(image, size)
        return image
    except pygame.error as e:
        print(f"Warning: Could not load image '{filename}': {e}")
        # Create a placeholder surface if loading fails
        placeholder = pygame.Surface((size if size else GRID_SIZE, size if size else GRID_SIZE))
        placeholder.fill(RED) # Fill with red to indicate error
        pygame.draw.line(placeholder, BLACK, (0,0), (placeholder.get_width(), placeholder.get_height()), 2)
        pygame.draw.line(placeholder, BLACK, (0, placeholder.get_height()), (placeholder.get_width(), 0), 2)
        return placeholder
    except FileNotFoundError:
        print(f"Warning: Image file not found '{filename}'")
        # Create a placeholder surface if file not found
        placeholder = pygame.Surface((size if size else GRID_SIZE, size if size else GRID_SIZE))
        placeholder.fill(BLUE) # Fill with blue to indicate error
        pygame.draw.line(placeholder, WHITE, (0,0), (placeholder.get_width(), placeholder.get_height()), 2)
        pygame.draw.line(placeholder, WHITE, (0, placeholder.get_height()), (placeholder.get_width(), 0), 2)
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
def get_font(size):
    # Attempt to load a common font, fallback to default
    try:
        return pygame.font.Font(pygame.font.match_font('arial'), size)
    except:
        return pygame.font.Font(None, size + 4) # Default font might need size adjustment

# --- Direction Vectors ---
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)