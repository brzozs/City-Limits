import pygame
import sys
import random
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

# Spawn/end marker colours and size
START_COLOR = (0, 210, 80)
END_COLOR = (210, 50, 50)
MARKER_RADIUS = 14
MARKER_OFFSET = 22  # pixels outside the grid edge

# Game states
STATE_MENU = "menu"
STATE_LEVEL_SELECT = "level_select"
STATE_GAME = "game"

def get_perimeter_positions(rows, cols):
    """Return all grid-edge positions in clockwise order as (side, index) tuples.

    Indices refer to which cell along that side (0-based).
    Order: top L→R, right T→B, bottom R→L, left B→T.
    """
    positions = []
    for c in range(cols):
        positions.append(('top', c))
    for r in range(rows):
        positions.append(('right', r))
    for c in range(cols - 1, -1, -1):
        positions.append(('bottom', c))
    for r in range(rows - 1, -1, -1):
        positions.append(('left', r))
    return positions


def perimeter_distance(a, b, total):
    """Shortest clockwise/counter-clockwise distance between two perimeter indices."""
    diff = abs(a - b)
    return min(diff, total - diff)


def edge_pixel(side, index, start_x, start_y, cell_size, rows, cols):
    """Pixel coordinate at the midpoint of the outer face of an edge cell."""
    half = cell_size // 2
    if side == 'top':
        return (start_x + index * cell_size + half, start_y)
    elif side == 'bottom':
        return (start_x + index * cell_size + half, start_y + rows * cell_size)
    elif side == 'left':
        return (start_x, start_y + index * cell_size + half)
    else:  # right
        return (start_x + cols * cell_size, start_y + index * cell_size + half)


def generate_spawn_points(level, rows, cols, start_x, start_y, cell_size):
    """Return a list of marker dicts for the given level.

    Each dict has: type ('start'/'end'), side, index, x, y.
    Points are placed on the grid perimeter with a minimum spacing to
    ensure they are never adjacent.
    """
    spawn_configs = {
        1: (1, 1),  # 1 start, 1 end
        2: (1, 2),  # 1 start, 2 ends
        3: (2, 2),  # 2 starts, 2 ends
    }
    num_starts, num_ends = spawn_configs[level]
    total_points = num_starts + num_ends

    perimeter = get_perimeter_positions(rows, cols)
    total = len(perimeter)

    # Minimum spacing: spread points as evenly as possible around the perimeter
    min_dist = max(2, total // total_points)

    chosen = []
    for _ in range(5000):  # retry budget
        idx = random.randint(0, total - 1)
        if all(perimeter_distance(idx, c, total) >= min_dist for c in chosen):
            chosen.append(idx)
        if len(chosen) == total_points:
            break

    # Fallback: relax spacing if we still don't have enough points
    if len(chosen) < total_points:
        remaining = [i for i in range(total) if i not in chosen]
        random.shuffle(remaining)
        chosen.extend(remaining[: total_points - len(chosen)])

    random.shuffle(chosen)

    markers = []
    for i, idx in enumerate(chosen):
        side, index = perimeter[idx]
        px, py = edge_pixel(side, index, start_x, start_y, cell_size, rows, cols)
        markers.append({
            'type': 'start' if i < num_starts else 'end',
            'side': side,
            'index': index,
            'x': px,
            'y': py,
        })
    return markers


def draw_spawn_markers(screen, markers, font):
    """Draw start/end markers just outside the grid edge."""
    for m in markers:
        x, y = m['x'], m['y']
        side = m['side']
        is_start = m['type'] == 'start'
        color = START_COLOR if is_start else END_COLOR
        label = 'S' if is_start else 'E'

        # Offset the circle centre outside the grid
        if side == 'top':
            mx, my = x, y - MARKER_OFFSET
        elif side == 'bottom':
            mx, my = x, y + MARKER_OFFSET
        elif side == 'left':
            mx, my = x - MARKER_OFFSET, y
        else:  # right
            mx, my = x + MARKER_OFFSET, y

        # Connector line from circle edge to grid border
        pygame.draw.line(screen, color, (mx, my), (x, y), 2)

        # Filled circle with white outline
        pygame.draw.circle(screen, color, (mx, my), MARKER_RADIUS)
        pygame.draw.circle(screen, (255, 255, 255), (mx, my), MARKER_RADIUS, 2)

        # S / E label
        text = font.render(label, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=(mx, my)))


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

def draw_level_menu(screen, font, title_font, selected_city):
    """Draw the level selection menu for the selected city"""
    screen.fill(BACKGROUND_COLOR)

    # Title
    title = title_font.render(selected_city, True, (255, 255, 255))
    title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 80))
    screen.blit(title, title_rect)

    # Subtitle
    subtitle = font.render("Select Level", True, (200, 200, 200))
    subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 150))
    screen.blit(subtitle, subtitle_rect)

    # Level buttons
    button_width = 200
    button_height = 60
    button_spacing = 80
    start_y = 230

    level_names = ["1", "2", "3"]
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
        button_text = font.render(f"Level {level_names[i]}", True, BUTTON_TEXT_COLOR)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

        buttons.append(button_rect)

    # Back button
    back_button_rect = pygame.Rect(20, 20, 150, 40)
    back_button_hovered = back_button_rect.collidepoint(mouse_pos)
    back_button_color = BUTTON_HOVER_COLOR if back_button_hovered else BUTTON_COLOR
    pygame.draw.rect(screen, back_button_color, back_button_rect, border_radius=10)
    small_font = pygame.font.Font(None, 28)
    back_text = small_font.render("Back", True, BUTTON_TEXT_COLOR)
    back_text_rect = back_text.get_rect(center=back_button_rect.center)
    screen.blit(back_text, back_text_rect)

    return buttons, back_button_rect

def run_game(screen, selected_city, selected_level):
    """Run the game for the selected city"""
    pygame.display.set_caption(f"City Limits - {selected_city} - Level {selected_level}")

    # Grid configurations: (rows, cols) for each level
    # Level 1: 1x3 (1 row, 3 columns)
    # Level 2: 2x3 (2 rows, 3 columns)
    # Level 3: 3x3 (3 rows, 3 columns)
    grid_configs = {
        1: (1, 3),
        2: (2, 3),
        3: (3, 3)
    }

    # Get the grid configuration for the selected level
    current_grid = grid_configs[selected_level]
    rows, cols = current_grid

    # Compute grid screen position (used throughout this function)
    grid_start_x = (WINDOW_WIDTH - cols * CELL_SIZE) // 2
    grid_start_y = 120

    # Generate spawn/end markers once for this level
    spawn_markers = generate_spawn_points(
        selected_level, rows, cols, grid_start_x, grid_start_y, CELL_SIZE
    )

    # Button setup
    back_button_rect = pygame.Rect(20, 20, 150, 40)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 28)
    marker_font = pygame.font.Font(None, 24)

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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # Exit entire game
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_hovered:
                    return True  # Return to level select
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
                    dragging_intersection.snap_to_grid(grid_start_x, grid_start_y, CELL_SIZE, rows, cols)
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

        # Draw grid
        for row in range(rows):
            for col in range(cols):
                x = grid_start_x + col * CELL_SIZE
                y = grid_start_y + row * CELL_SIZE
                pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)

        # Draw spawn/end markers
        draw_spawn_markers(screen, spawn_markers, marker_font)

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

    current_state = STATE_MENU
    selected_city = None
    selected_level = None
    city_names = ["New York City", "Los Angeles", "Chicago"]

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
                            current_state = STATE_LEVEL_SELECT
                            break

            pygame.display.flip()

        elif current_state == STATE_LEVEL_SELECT:
            # Draw level selection menu
            level_buttons, back_button = draw_level_menu(screen, font, title_font, selected_city)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    # Check if back button was clicked
                    if back_button.collidepoint(mouse_pos):
                        current_state = STATE_MENU
                    else:
                        # Check which level button was clicked
                        for i, button in enumerate(level_buttons):
                            if button.collidepoint(mouse_pos):
                                selected_level = i + 1  # Levels 1, 2, 3
                                current_state = STATE_GAME
                                break

            pygame.display.flip()

        elif current_state == STATE_GAME:
            # Run game, returns True if should return to level select, False if should quit
            should_continue = run_game(screen, selected_city, selected_level)
            if should_continue:
                current_state = STATE_LEVEL_SELECT
            else:
                running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
