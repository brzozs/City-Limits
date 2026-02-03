import pygame
import sys

# Initialize pygame
#(runs the game) python src/main.py
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 400
CELL_SIZE = 200
BACKGROUND_COLOR = (30, 30, 30)
GRID_COLOR = (100, 100, 100)
CELL_COLOR = (50, 50, 50)

def main():
    # Create window
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("City Limits - Level 1")
    
    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Clear screen
        screen.fill(BACKGROUND_COLOR)
        
        # Draw 3x1 grid
        for i in range(3):
            x = i * CELL_SIZE + 100
            y = 100
            pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)
        
        # Update display
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
