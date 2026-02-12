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

# Game states
STATE_MENU = "menu"
STATE_GAME = "game"

def draw_menu(screen, font, title_font):
    """Draw the main menu with city selection"""
    screen.fill(BACKGROUND_COLOR)

    # Title
    title = title_font.render("City Limits", True, (255, 255, 255))
    title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
    screen.blit(title, title_rect)

    # City buttons
    button_width = 300
    button_height = 60
    button_spacing = 80
    start_y = 250

    city_names = ["New York City", "Los Angeles", "Chicago"]
    buttons = []
    mouse_pos = pygame.mouse.get_pos()

    for i in range(3):
        button_y = start_y + i * button_spacing
        button_rect = pygame.Rect(
            (WINDOW_WIDTH - button_width) // 2,
            button_y,
            button_width,
            button_height
        )

        # Check hover
        is_hovered = button_rect.collidepoint(mouse_pos)
        button_color = BUTTON_HOVER_COLOR if is_hovered else BUTTON_COLOR

        # Draw button
        pygame.draw.rect(screen, button_color, button_rect, border_radius=10)

        # Draw text
        button_text = font.render(city_names[i], True, BUTTON_TEXT_COLOR)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

        buttons.append(button_rect)

    return buttons

def run_game(screen, selected_city):
    """Run the game for the selected city"""
    pygame.display.set_caption(f"City Limits - {selected_city}")

    # Grid configurations: (rows, cols)
    grid_configs = [(1, 3), (2, 3), (3, 3)]
    current_grid_index = 0
    
    # Button setup
    back_button_rect = pygame.Rect(20, 20, 150, 40)
    level_button_rect = pygame.Rect(300, 20, 200, 50)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 28)

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
        back_button_hovered = back_button_rect.collidepoint(mouse_pos)
        level_button_hovered = level_button_rect.collidepoint(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # Exit entire game
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_hovered:
                    return True  # Return to menu
                elif level_button_hovered:
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

        # Draw back button
        back_button_color = BUTTON_HOVER_COLOR if back_button_hovered else BUTTON_COLOR
        pygame.draw.rect(screen, back_button_color, back_button_rect, border_radius=10)
        back_text = small_font.render("Back", True, BUTTON_TEXT_COLOR)
        back_text_rect = back_text.get_rect(center=back_button_rect.center)
        screen.blit(back_text, back_text_rect)

        # Draw level button
        level_button_color = BUTTON_HOVER_COLOR if level_button_hovered else BUTTON_COLOR
        pygame.draw.rect(screen, level_button_color, level_button_rect, border_radius=10)
        button_text = font.render("Level", True, BUTTON_TEXT_COLOR)
        text_rect = button_text.get_rect(center=level_button_rect.center)
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

    return True  # Return to menu

def main():
    """Main function managing game states"""
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("City Limits")

    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 72)

    city_names = ["New York City", "Los Angeles", "Chicago"]
    current_state = STATE_MENU
    selected_city = None

    running = True
    while running:
        if current_state == STATE_MENU:
            # Draw menu and get button rects
            city_buttons = draw_menu(screen, font, title_font)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    # Check which city button was clicked
                    for i, button in enumerate(city_buttons):
                        if button.collidepoint(mouse_pos):
                            selected_city = city_names[i]
                            current_state = STATE_GAME
                            break

            pygame.display.flip()

        elif current_state == STATE_GAME:
            # Run game, returns True if should return to menu, False if should quit
            should_continue = run_game(screen, selected_city)
            if should_continue:
                current_state = STATE_MENU
            else:
                running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
