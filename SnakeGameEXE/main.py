import pygame
from game import Game # Import the Game class from game.py

if __name__ == '__main__':
    # Ensure Pygame is initialized (Game class does this, but good practice)
    if not pygame.get_init():
        pygame.init()
        pygame.mixer.init()

    # Check if display is available (optional robustness)
    try:
         pygame.display.set_mode((100, 50)) # Try creating a small temporary window
         pygame.display.quit() # Close it immediately
    except pygame.error as e:
         print(f"Error: Could not initialize display. Is a display connected? Pygame error: {e}")
         # Optionally, fall back to a headless mode or exit gracefully
         exit()


    print("Starting Enhanced Snake Game...")
    game_instance = Game()
    game_instance.run()
    print("Game exited.")