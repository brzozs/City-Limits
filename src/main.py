import pygame
import sys
from intersection import Intersection

# Initialize pygame
#(runs the game) python src/main.py
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 150
BACKGROUND_COLOR = (30, 30, 30)
GRID_COLOR = (100, 100, 100)
CELL_COLOR = (50, 50, 50)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 160, 210)
BUTTON_TEXT_COLOR = (255, 255, 255)

def main():
    # Create window
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("City Limits - Level 1")
    
    # Grid configurations: (rows, cols)
    grid_configs = [(1, 3), (2, 3), (3, 3)]
    current_grid_index = 0
    
    # Button setup
    button_rect = pygame.Rect(300, 20, 200, 50)
    font = pygame.font.Font(None, 36)

    # Create a simple placeholder sprite for intersections
    placeholder_sprite = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(placeholder_sprite, (255, 100, 100), (20, 20), 20)
    pygame.draw.circle(placeholder_sprite, (255, 255, 255), (20, 20), 20, 2)

    # Create some intersection placeholders at the bottom
    intersections = [
        Intersection(100, 500, placeholder_sprite),
        Intersection(200, 500, placeholder_sprite),
        Intersection(300, 500, placeholder_sprite),
    ]
    dragging_intersection = None

    # Game loop
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        button_hovered = button_rect.collidepoint(mouse_pos)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_hovered:
                    current_grid_index = (current_grid_index + 1) % len(grid_configs)
                else:
                    # Check if clicking on an intersection
                    for intersection in intersections:
                        if intersection.is_clicked(mouse_pos):
                            intersection.dragging = True
                            dragging_intersection = intersection
                            break
            if event.type == pygame.MOUSEBUTTONUP:
                # Release the dragged intersection
                if dragging_intersection:
                    rows, cols = grid_configs[current_grid_index]
                    grid_width = cols * CELL_SIZE
                    start_x = (WINDOW_WIDTH - grid_width) // 2
                    start_y = 120
                    dragging_intersection.snap_to_grid(start_x, start_y, CELL_SIZE, rows, cols)
                    dragging_intersection.dragging = False
                    dragging_intersection = None

        # Update dragging position
        if dragging_intersection:
            dragging_intersection.update_position(mouse_pos)

        # Clear screen
        screen.fill(BACKGROUND_COLOR)
        
        # Draw button
        button_color = BUTTON_HOVER_COLOR if button_hovered else BUTTON_COLOR
        pygame.draw.rect(screen, button_color, button_rect, border_radius=10)
        button_text = font.render("Level", True, BUTTON_TEXT_COLOR)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)
        
        # Draw grid
        rows, cols = grid_configs[current_grid_index]
        grid_width = cols * CELL_SIZE
        grid_height = rows * CELL_SIZE
        start_x = (WINDOW_WIDTH - grid_width) // 2
        start_y = 120
        
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * CELL_SIZE
                y = start_y + row * CELL_SIZE
                pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)

        # Draw intersections
        for intersection in intersections:
            intersection.draw(screen)

        # Update display
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
