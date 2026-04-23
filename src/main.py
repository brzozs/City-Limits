import asyncio
import pygame
import sys
import random
from intersection import Intersection, IntersectionType
from grid_network import IntersectionNetwork
from car import Car, CAR_SPEED
from traffic_data import get_spawn_interval, get_current_volume

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
GAME_DAY_LENGTH = 300.0  # 5 minutes for a full 24-hour cycle
MAX_LEVEL = 3
LEVEL_PASS_TARGETS = {
    1: 0.45,
    2: 0.55,
    3: 0.65,
}
UNDO_WINDOW_SECONDS = 4.0
TOUCH_ACTION_ORDER = ("rotate", "delete", "undo")
TOUCH_ACTION_LABELS = {
    "rotate": "Rotate",
    "delete": "Delete",
    "undo": "Undo",
}


def is_browser_runtime(platform_name=None):
    """Return True when running inside an Emscripten/pygbag browser build."""
    if platform_name is None:
        platform_name = sys.platform
    return platform_name == "emscripten"


def normalize_pointer_event(event, screen_width=WINDOW_WIDTH, screen_height=WINDOW_HEIGHT):
    """Convert mouse or touch input into a shared pointer event payload."""
    mouse_types = {
        pygame.MOUSEBUTTONDOWN: "down",
        pygame.MOUSEBUTTONUP: "up",
        pygame.MOUSEMOTION: "move",
    }
    touch_types = {
        pygame.FINGERDOWN: "down",
        pygame.FINGERUP: "up",
        pygame.FINGERMOTION: "move",
    }

    if event.type in mouse_types:
        return {
            "kind": mouse_types[event.type],
            "pos": getattr(event, "pos", pygame.mouse.get_pos()),
            "button": getattr(event, "button", 1),
            "pointer": "mouse",
        }

    if event.type in touch_types:
        return {
            "kind": touch_types[event.type],
            "pos": (screen_width * event.x, screen_height * event.y),
            "button": 1,
            "pointer": "touch",
        }

    return None


def get_touch_toolbar_button_rects(window_width=WINDOW_WIDTH, window_height=WINDOW_HEIGHT):
    """Return the fixed browser touch toolbar button layout."""
    button_width = 150
    button_height = 54
    gap = 12
    total_width = button_width * len(TOUCH_ACTION_ORDER) + gap * (len(TOUCH_ACTION_ORDER) - 1)
    start_x = (window_width - total_width) // 2
    top = window_height - button_height - 20

    return {
        name: pygame.Rect(
            start_x + index * (button_width + gap),
            top,
            button_width,
            button_height,
        )
        for index, name in enumerate(TOUCH_ACTION_ORDER)
    }


def get_touch_action_states(has_dragging, has_selected, can_undo):
    """Report which browser touch actions are currently available."""
    has_dragging = bool(has_dragging)
    has_selected = bool(has_selected)
    return {
        "rotate": has_dragging or has_selected,
        "delete": has_selected and not has_dragging,
        "undo": bool(can_undo),
    }

def calculate_flow_rate(completed_stats, spawn_attempts=0, spawn_successes=0):
    """Compute flow rate using the equation from the README:

    Flow Rate = (V_Avg / V_limit) x (T_Ideal / T_Actual) x (1 - T_Idle / T_Actual)

    completed_stats is a list of (path_length, travel_time, idle_time) tuples
    for every car that has reached its destination.

    spawn_attempts / spawn_successes are used to penalise incomplete networks:
    cars that cannot be routed drag the score down proportionally.
    """
    if not completed_stats:
        return 0.0

    total_dist   = sum(pl for pl, _, _  in completed_stats)
    total_actual = sum(tt for _,  tt, _ in completed_stats)
    total_idle   = sum(it for _,  _,  it in completed_stats)

    if total_actual == 0:
        return 0.0

    v_avg    = total_dist / total_actual          # average speed (px/s)
    v_ratio  = min(v_avg / CAR_SPEED, 1.0)        # V_Avg / V_limit
    t_ideal  = total_dist / CAR_SPEED             # ideal travel time at speed limit
    t_ratio  = min(t_ideal / total_actual, 1.0)   # T_Ideal / T_Actual
    idle_ratio = 1.0 - (total_idle / total_actual) # 1 - T_Idle / T_Actual

    base_rate = v_ratio * t_ratio * idle_ratio

    # Penalise missed routings — an incomplete network lowers the score
    if spawn_attempts > 0:
        routing_ratio = spawn_successes / spawn_attempts
        return base_rate * routing_ratio

    return base_rate


def get_grade(flow_rate):
    """Convert a 0–1 flow rate to a letter grade."""
    if flow_rate >= 0.80: return 'A'
    if flow_rate >= 0.65: return 'B'
    if flow_rate >= 0.45: return 'C'
    if flow_rate >= 0.25: return 'D'
    return 'F'


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


def compute_grid_origin(rows, cols, cell_size, left_ui_right_edge=240):
    """Compute a grid origin that avoids overlapping the left-side UI panel."""
    grid_width = cols * cell_size
    grid_height = rows * cell_size
    centered_x = (WINDOW_WIDTH - grid_width) // 2
    centered_y = (WINDOW_HEIGHT - grid_height) // 2

    marker_clearance = MARKER_OFFSET + MARKER_RADIUS
    min_x = left_ui_right_edge + marker_clearance
    max_x = WINDOW_WIDTH - grid_width - marker_clearance

    if max_x >= min_x:
        safe_x = max(min_x, min(centered_x, max_x))
    else:
        safe_x = centered_x

    return safe_x, centered_y


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
    end_counter = 1
    for i, idx in enumerate(chosen):
        side, index = perimeter[idx]
        px, py = edge_pixel(side, index, start_x, start_y, cell_size, rows, cols)
        is_start = i < num_starts
        m = {
            'type': 'start' if is_start else 'end',
            'side': side,
            'index': index,
            'x': px,
            'y': py,
        }
        if not is_start:
            m['number'] = end_counter
            end_counter += 1
        markers.append(m)
    return markers



def _find_nearest_intersection(network, x, y):
    """Find the nearest intersection to pixel coordinates (x, y)."""
    nearest = None
    min_dist = float('inf')
    
    for intersection in network.get_all_intersections():
        dist = ((intersection.x - x) ** 2 + (intersection.y - y) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            nearest = intersection
    
    return nearest



def draw_clock(screen, elapsed_seconds, font, center=(WINDOW_WIDTH // 2, 20)):
    """Draw the game clock at the top center of the screen.

    Cycles through a 24-hour day (midnight to midnight).
    Clock colour reflects the time of day:
      - Rush hours (07-09, 16-19): amber — high traffic expected
      - Overnight (00-05): dim gray — quiet period
      - All other hours: white
    Returns the current game hour so callers can branch on it.
    """
    time_in_cycle = elapsed_seconds % GAME_DAY_LENGTH
    hours = int((time_in_cycle / GAME_DAY_LENGTH) * 24)
    minutes = int(((time_in_cycle / GAME_DAY_LENGTH) * 24 - hours) * 60)
    time_str = f"{hours:02d}:{minutes:02d}"

    if (7 <= hours < 10) or (16 <= hours < 19):
        clock_color = (255, 165, 40)   # amber — rush hour
    elif hours < 5:
        clock_color = (140, 140, 140)  # dim gray — overnight
    else:
        clock_color = (255, 255, 255)  # white — normal hours

    clock_text = font.render(time_str, True, clock_color)
    text_rect = clock_text.get_rect(center=center)
    screen.blit(clock_text, text_rect)
    return hours


def draw_pause_controls(screen, start_button_rect, pause_button_rect, is_paused, is_started, small_font, mouse_pos):
    """Draw start/pause/quit buttons at the top of the screen."""
    # Start button (always show in game)
    start_hovered = start_button_rect.collidepoint(mouse_pos)
    start_color = BUTTON_HOVER_COLOR if start_hovered else BUTTON_COLOR
    pygame.draw.rect(screen, start_color, start_button_rect, border_radius=10)
    start_text_content = "Stop" if is_started else "Start"
    start_text = small_font.render(start_text_content, True, BUTTON_TEXT_COLOR)
    start_text_rect = start_text.get_rect(center=start_button_rect.center)
    screen.blit(start_text, start_text_rect)
    
    # Pause button (only show when game is started and not paused)
    if is_started and not is_paused:
        pause_hovered = pause_button_rect.collidepoint(mouse_pos)
        pause_color = BUTTON_HOVER_COLOR if pause_hovered else BUTTON_COLOR
        pygame.draw.rect(screen, pause_color, pause_button_rect, border_radius=10)
        pause_text_content = "Pause"
        pause_text = small_font.render(pause_text_content, True, BUTTON_TEXT_COLOR)
        pause_text_rect = pause_text.get_rect(center=pause_button_rect.center)
        screen.blit(pause_text, pause_text_rect)


def draw_quit_confirmation(screen, title_font, font):
    """Draw a quit confirmation dialog."""
    # Semi-transparent overlay
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(128)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Draw the quit confirmation dialog in the dialog
    dialog_width = 400
    dialog_height = 200
    dialog_x = (WINDOW_WIDTH - dialog_width) // 2
    dialog_y = (WINDOW_HEIGHT - dialog_height) // 2
    
    pygame.draw.rect(screen, (50, 50, 50), (dialog_x, dialog_y, dialog_width, dialog_height))
    pygame.draw.rect(screen, (100, 100, 100), (dialog_x, dialog_y, dialog_width, dialog_height), 3)
    
    # Message
    message = font.render("Return to main menu?", True, (255, 255, 255))
    message_rect = message.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 50))
    screen.blit(message, message_rect)
    
    # Yes and No buttons
    button_width = 100
    button_height = 40
    yes_button_rect = pygame.Rect(dialog_x + 50, dialog_y + 120, button_width, button_height)
    no_button_rect = pygame.Rect(dialog_x + dialog_width - 150, dialog_y + 120, button_width, button_height)
    
    mouse_pos = pygame.mouse.get_pos()
    
    # Yes button
    yes_hovered = yes_button_rect.collidepoint(mouse_pos)
    yes_color = BUTTON_HOVER_COLOR if yes_hovered else BUTTON_COLOR
    pygame.draw.rect(screen, yes_color, yes_button_rect, border_radius=10)
    yes_text = font.render("Yes", True, BUTTON_TEXT_COLOR)
    yes_text_rect = yes_text.get_rect(center=yes_button_rect.center)
    screen.blit(yes_text, yes_text_rect)
    
    # No button
    no_hovered = no_button_rect.collidepoint(mouse_pos)
    no_color = BUTTON_HOVER_COLOR if no_hovered else BUTTON_COLOR
    pygame.draw.rect(screen, no_color, no_button_rect, border_radius=10)
    no_text = font.render("No", True, BUTTON_TEXT_COLOR)
    no_text_rect = no_text.get_rect(center=no_button_rect.center)
    screen.blit(no_text, no_text_rect)
    
    return yes_button_rect, no_button_rect


def draw_pause_overlay(screen, selected_city, selected_level, font, small_font, mouse_pos, confirm_exit=False):
    """Draw the pause overlay card.

    Returns (resume_rect, restart_rect, menu_rect, confirm_rects).
    When confirm_exit is True the card shows a confirmation sub-screen and
    resume/restart/menu_rect are None; confirm_rects is (yes_rect, no_rect).
    """
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pw, ph = 340, 310
    px = (WINDOW_WIDTH - pw) // 2
    py = (WINDOW_HEIGHT - ph) // 2
    pygame.draw.rect(screen, (40, 40, 40), (px, py, pw, ph), border_radius=12)
    pygame.draw.rect(screen, (100, 100, 100), (px, py, pw, ph), 2, border_radius=12)

    header = font.render(f"{selected_city}  —  Level {selected_level}", True, (200, 200, 200))
    screen.blit(header, header.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 18))

    paused_surf = font.render("PAUSED", True, (255, 255, 255))
    screen.blit(paused_surf, paused_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 55))

    if not confirm_exit:
        bw, bh = 230, 44
        bx = (WINDOW_WIDTH - bw) // 2
        resume_rect  = pygame.Rect(bx, py + 120, bw, bh)
        restart_rect = pygame.Rect(bx, py + 178, bw, bh)
        menu_rect    = pygame.Rect(bx, py + 236, bw, bh)
        for rect, label in [(resume_rect, "Resume"), (restart_rect, "Restart"), (menu_rect, "Main Menu")]:
            hov = rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, BUTTON_HOVER_COLOR if hov else BUTTON_COLOR, rect, border_radius=10)
            surf = font.render(label, True, BUTTON_TEXT_COLOR)
            screen.blit(surf, surf.get_rect(center=rect.center))
        return resume_rect, restart_rect, menu_rect, None
    else:
        msg = small_font.render("Return to menu? Progress will be lost.", True, (220, 180, 80))
        screen.blit(msg, msg.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 120))
        bw, bh = 140, 44
        yes_rect = pygame.Rect(px + 40,           py + 210, bw, bh)
        no_rect  = pygame.Rect(px + pw - 40 - bw, py + 210, bw, bh)
        for rect, label in [(yes_rect, "Yes"), (no_rect, "No")]:
            hov = rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, BUTTON_HOVER_COLOR if hov else BUTTON_COLOR, rect, border_radius=10)
            surf = font.render(label, True, BUTTON_TEXT_COLOR)
            screen.blit(surf, surf.get_rect(center=rect.center))
        return None, None, None, (yes_rect, no_rect)


def wrap_text_lines(text, font, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_words = []

    for word in words:
        trial = " ".join(current_words + [word])
        if font.size(trial)[0] <= max_width:
            current_words.append(word)
        else:
            if current_words:
                lines.append(" ".join(current_words))
            current_words = [word]

    if current_words:
        lines.append(" ".join(current_words))

    return lines


def draw_intro_overlay(screen, font, small_font, mouse_pos):
    """Draw the first-time tutorial card. Returns got_it_rect."""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(210)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pw, ph = 540, 290
    px = (WINDOW_WIDTH - pw) // 2
    py = (WINDOW_HEIGHT - ph) // 2
    pygame.draw.rect(screen, (40, 40, 40), (px, py, pw, ph), border_radius=12)
    pygame.draw.rect(screen, (100, 100, 100), (px, py, pw, ph), 2, border_radius=12)

    title_font_temp = pygame.font.Font(None, 42)
    title = title_font_temp.render("How to Play", True, (255, 255, 255))
    screen.blit(title, title.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 20))

    goal_text = "Connect spawn points to exit points so cars can flow through the city."
    goal_lines = wrap_text_lines(goal_text, small_font, pw - 60)
    goal_top = py + 65
    line_height = small_font.get_linesize()
    for i, line in enumerate(goal_lines):
        goal = small_font.render(line, True, (200, 200, 200))
        screen.blit(goal, goal.get_rect(centerx=WINDOW_WIDTH // 2, top=goal_top + i * line_height))

    icons = [
        (START_COLOR,       "IN — Cars start here"),
        ((130, 130, 130),   "Drag intersections to build roads"),
        (END_COLOR,         "OUT — Cars must reach here"),
    ]
    col_xs = [px + 90, px + 270, px + 450]
    for (color, caption), cx in zip(icons, col_xs):
        pygame.draw.circle(screen, color, (cx, py + 155), 14)
        pygame.draw.circle(screen, (255, 255, 255), (cx, py + 155), 14, 2)
        caption_lines = wrap_text_lines(caption, small_font, 150)
        for line_index, line in enumerate(caption_lines[:2]):
            s_line = small_font.render(line, True, (180, 180, 180))
            screen.blit(s_line, s_line.get_rect(centerx=cx, top=py + 176 + line_index * 20))

    bw, bh = 220, 44
    got_it_rect = pygame.Rect((WINDOW_WIDTH - bw) // 2, py + ph - 62, bw, bh)
    hov = got_it_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, BUTTON_HOVER_COLOR if hov else BUTTON_COLOR, got_it_rect, border_radius=10)
    btn = font.render("Got it & Start", True, BUTTON_TEXT_COLOR)
    screen.blit(btn, btn.get_rect(center=got_it_rect.center))
    return got_it_rect


def draw_spawn_markers(screen, markers, font, label_alpha=255):
    """Draw start/end markers just outside the grid edge."""
    for m in markers:
        x, y = m['x'], m['y']
        side = m['side']
        is_start = m['type'] == 'start'
        color = START_COLOR if is_start else END_COLOR
        label = 'S' if is_start else str(m['number'])

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

        # Place IN / OUT labels toward the grid so edge labels stay on-screen.
        tag = "IN" if is_start else "OUT"
        tag_surf = font.render(tag, True, color)
        tag_surf.set_alpha(int(label_alpha))

        if side == 'top':
            tag_center = (mx, my + MARKER_RADIUS + 8)
        elif side == 'bottom':
            tag_center = (mx, my - MARKER_RADIUS - 8)
        elif side == 'left':
            tag_center = (mx + MARKER_RADIUS + 12, my)
        else:  # right
            tag_center = (mx - MARKER_RADIUS - 12, my)

        screen.blit(tag_surf, tag_surf.get_rect(center=tag_center))


def draw_menu(screen, font, title_font, all_unlocked=False):
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

    # Small utility button for quickly unlocking all levels.
    small_font = pygame.font.Font(None, 24)
    unlock_w, unlock_h = 126, 32
    unlock_button_rect = pygame.Rect(WINDOW_WIDTH - unlock_w - 14, 14, unlock_w, unlock_h)
    unlock_hovered = unlock_button_rect.collidepoint(mouse_pos)

    if all_unlocked:
        base_color = (78, 145, 90)
        hover_color = (96, 168, 108)
        button_label = "All Unlocked"
    else:
        base_color = (85, 85, 85)
        hover_color = (110, 110, 110)
        button_label = "Unlock All"

    unlock_color = hover_color if unlock_hovered else base_color
    pygame.draw.rect(screen, unlock_color, unlock_button_rect, border_radius=8)
    unlock_text = small_font.render(button_label, True, BUTTON_TEXT_COLOR)
    screen.blit(unlock_text, unlock_text.get_rect(center=unlock_button_rect.center))

    return buttons, unlock_button_rect

def draw_level_menu(screen, font, title_font, selected_city, max_unlocked_level=1):
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

    small_font = pygame.font.Font(None, 28)
    unlocked_text = small_font.render(f"Unlocked Levels: 1-{max_unlocked_level}", True, (180, 180, 180))
    unlocked_text_rect = unlocked_text.get_rect(center=(WINDOW_WIDTH // 2, 182))
    screen.blit(unlocked_text, unlocked_text_rect)

    # Level buttons
    button_width = 200
    button_height = 60
    button_spacing = 80
    start_y = 230

    level_names = ["1", "2", "3"]
    buttons = []
    mouse_pos = pygame.mouse.get_pos()

    for i in range(3):
        level_num = i + 1
        is_unlocked = level_num <= max_unlocked_level
        button_y = start_y + i * button_spacing
        button_rect = pygame.Rect(
            (WINDOW_WIDTH - button_width) // 2,
            button_y,
            button_width,
            button_height
        )

        # Check hover
        if is_unlocked:
            is_hovered = button_rect.collidepoint(mouse_pos)
            button_color = BUTTON_HOVER_COLOR if is_hovered else BUTTON_COLOR
            text_color = BUTTON_TEXT_COLOR
        else:
            button_color = (65, 65, 65)
            text_color = (140, 140, 140)

        # Draw button
        pygame.draw.rect(screen, button_color, button_rect, border_radius=10)

        # Draw text
        if is_unlocked:
            button_text = font.render(f"Level {level_names[i]}", True, text_color)
            text_rect = button_text.get_rect(center=button_rect.center)
            screen.blit(button_text, text_rect)
        else:
            level_text = small_font.render(f"Level {level_names[i]}", True, text_color)
            level_rect = level_text.get_rect(center=(button_rect.centerx, button_rect.centery - 10))
            screen.blit(level_text, level_rect)
            lock_text = small_font.render("Locked", True, (170, 170, 170))
            lock_rect = lock_text.get_rect(center=(button_rect.centerx, button_rect.centery + 12))
            screen.blit(lock_text, lock_rect)

        buttons.append(button_rect)

    # Back button
    back_button_rect = pygame.Rect(20, 20, 150, 40)
    back_button_hovered = back_button_rect.collidepoint(mouse_pos)
    back_button_color = BUTTON_HOVER_COLOR if back_button_hovered else BUTTON_COLOR
    pygame.draw.rect(screen, back_button_color, back_button_rect, border_radius=10)
    back_text = small_font.render("Back", True, BUTTON_TEXT_COLOR)
    back_text_rect = back_text.get_rect(center=back_button_rect.center)
    screen.blit(back_text, back_text_rect)

    return buttons, back_button_rect


def draw_undo_prompt(screen, small_font, undo_timer, anchor_x=150):
    """Draw a temporary undo prompt after deleting an intersection."""
    msg = f"Deleted. Press U to undo ({undo_timer:.1f}s)"
    msg_surf = small_font.render(msg, True, (245, 245, 245))
    msg_rect = msg_surf.get_rect(center=(anchor_x, WINDOW_HEIGHT - 105))
    box_rect = msg_rect.inflate(20, 12)
    pygame.draw.rect(screen, (20, 20, 20), box_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 170, 90), box_rect, 2, border_radius=10)
    screen.blit(msg_surf, msg_rect)


def draw_control_hint_strip(screen, hint_font):
    """Draw a compact control hint strip for new players."""
    msg = "R rotate | Right-click delete | U undo | P/Esc pause"
    msg_surf = hint_font.render(msg, True, (225, 225, 225))
    strip_rect = msg_surf.get_rect(bottomleft=(18, WINDOW_HEIGHT - 14))
    bg_rect = strip_rect.inflate(20, 10)
    pygame.draw.rect(screen, (25, 25, 25), bg_rect, border_radius=8)
    pygame.draw.rect(screen, (85, 85, 85), bg_rect, 1, border_radius=8)
    screen.blit(msg_surf, strip_rect)


def draw_button_tooltip(screen, small_font, rect, text):
    """Draw a simple tooltip below a hovered control button."""
    tip_surf = small_font.render(text, True, (245, 245, 245))
    tip_rect = tip_surf.get_rect(midtop=(rect.centerx, rect.bottom + 6))
    bg_rect = tip_rect.inflate(14, 8)
    pygame.draw.rect(screen, (20, 20, 20), bg_rect, border_radius=6)
    pygame.draw.rect(screen, (95, 95, 95), bg_rect, 1, border_radius=6)
    screen.blit(tip_surf, tip_rect)


def draw_touch_toolbar(screen, label_font, mouse_pos, action_states):
    """Draw browser-only touch controls for rotate/delete/undo."""
    button_rects = get_touch_toolbar_button_rects()
    heading = label_font.render("Touch Controls", True, (205, 205, 205))
    heading_rect = heading.get_rect(midbottom=(WINDOW_WIDTH // 2, button_rects["rotate"].top - 8))
    screen.blit(heading, heading_rect)

    for name in TOUCH_ACTION_ORDER:
        rect = button_rects[name]
        active = action_states[name]
        hovered = active and rect.collidepoint(mouse_pos)
        if active:
            fill = BUTTON_HOVER_COLOR if hovered else BUTTON_COLOR
            border = (185, 220, 245)
            text_color = BUTTON_TEXT_COLOR
        else:
            fill = (58, 58, 58)
            border = (88, 88, 88)
            text_color = (150, 150, 150)

        pygame.draw.rect(screen, fill, rect, border_radius=12)
        pygame.draw.rect(screen, border, rect, 2, border_radius=12)
        label = label_font.render(TOUCH_ACTION_LABELS[name], True, text_color)
        screen.blit(label, label.get_rect(center=rect.center))

    return button_rects


def _palette_slot_rect(panel_rect, index, slot_h, header_h, margin=10):
    """Return the rect for one intersection slot inside the side panel."""
    return pygame.Rect(
        panel_rect.x + margin,
        panel_rect.y + header_h + margin + index * slot_h,
        panel_rect.width - margin * 2,
        slot_h - 6,
    )


def draw_palette_toggle_button(screen, button_rect, is_open, small_font, mouse_pos):
    """Draw the left-side button that toggles the intersection menu."""
    hovered = button_rect.collidepoint(mouse_pos)
    color = BUTTON_HOVER_COLOR if hovered else BUTTON_COLOR
    pygame.draw.rect(screen, color, button_rect, border_radius=10)
    label = "Close Menu" if is_open else "Intersections"
    text = small_font.render(label, True, BUTTON_TEXT_COLOR)
    screen.blit(text, text.get_rect(center=button_rect.center))


def draw_palette_menu(screen, panel_rect, palette_types, used_types,
                      slot_h, header_h, label_font, mouse_pos, preview_cache=None):
    """Draw the expandable left-side intersection menu."""
    pygame.draw.rect(screen, (28, 28, 28), panel_rect, border_radius=12)
    pygame.draw.rect(screen, (95, 95, 95), panel_rect, 2, border_radius=12)

    remaining = len(palette_types) - len(used_types)
    title = label_font.render(f"Intersections ({remaining} left)", True, (225, 225, 225))
    screen.blit(title, title.get_rect(x=panel_rect.x + 12, y=panel_rect.y + 8))

    for i, itype in enumerate(palette_types):
        slot_rect = _palette_slot_rect(panel_rect, i, slot_h, header_h)
        used = itype in used_types
        hovered = slot_rect.collidepoint(mouse_pos) and not used

        if used:
            bg = (45, 45, 45)
            border = (85, 85, 85)
            text_color = (140, 140, 140)
        else:
            bg = (72, 72, 72) if hovered else (56, 56, 56)
            border = (120, 120, 120)
            text_color = (220, 220, 220)

        pygame.draw.rect(screen, bg, slot_rect, border_radius=8)
        pygame.draw.rect(screen, border, slot_rect, 1, border_radius=8)

        icon_x = slot_rect.x + 30
        icon_y = slot_rect.centery
        if preview_cache and itype in preview_cache:
            preview = preview_cache[itype]
            preview.x = icon_x
            preview.y = icon_y
            preview.draw(screen)
        else:
            Intersection(None, None, icon_x, icon_y, intersection_type=itype).draw(screen)

        label = label_font.render(itype.value, True, text_color)
        if label.get_width() > slot_rect.width - 104:
            short = itype.value.split()[0]
            label = label_font.render(short, True, text_color)
        screen.blit(label, label.get_rect(midleft=(slot_rect.x + 62, slot_rect.centery)))

        if used:
            used_surf = label_font.render("USED", True, (255, 120, 120))
            screen.blit(used_surf, used_surf.get_rect(midright=(slot_rect.right - 8, slot_rect.centery)))


def _find_clicked_placed_intersection(placed_intersections, pos):
    """Return the top-most placed intersection under the pointer, if any."""
    for placed in reversed(placed_intersections):
        if placed.is_clicked(pos):
            return placed
    return None


def _delete_placed_intersection(placed, network, placed_intersections):
    """Delete an intersection and capture undo metadata."""
    pending_undo_data = {
        'row': placed.row,
        'col': placed.col,
        'rotation': placed.rotation,
        'intersection_type': placed.intersection_type,
        'x': float(placed.x),
        'y': float(placed.y),
    }
    network.remove_intersection(placed)
    if placed in placed_intersections:
        placed_intersections.remove(placed)
    return pending_undo_data


def _restore_deleted_intersection(pending_undo_data, network, placed_intersections,
                                  grid_start_x, grid_start_y, cell_size):
    """Restore the most recently deleted intersection if its cell is still open."""
    row = pending_undo_data['row']
    col = pending_undo_data['col']
    restore_key = (row, col)
    if restore_key in network.placed_intersections:
        return None

    restored = Intersection(
        row,
        col,
        grid_start_x + col * cell_size + cell_size // 2,
        grid_start_y + row * cell_size + cell_size // 2,
        intersection_type=pending_undo_data['intersection_type'],
    )
    restored.rotation = pending_undo_data['rotation']
    restored.snapped = True
    restored.snapped_row = row
    restored.snapped_col = col
    network.add_intersection(restored)
    placed_intersections.append(restored)
    return restored


def _place_dragging_intersection(dragging_intersection, network, placed_intersections,
                                 used_palette_types, grid_start_x, grid_start_y,
                                 cell_size, rows, cols):
    """Attempt to place the currently dragged intersection on the grid."""
    if not dragging_intersection.snap_to_grid(
        grid_start_x, grid_start_y, cell_size, rows, cols
    ):
        return False

    placed_type = dragging_intersection.intersection_type
    existing_key = (dragging_intersection.row, dragging_intersection.col)
    if existing_key in network.placed_intersections:
        old = network.placed_intersections[existing_key]
        if old in placed_intersections:
            placed_intersections.remove(old)
    network.add_intersection(dragging_intersection)
    placed_intersections.append(dragging_intersection)
    used_palette_types.add(placed_type)
    return True


def draw_end_screen(screen, flow_rate, delivered, city, level, target_flow, passed,
                    has_next_level, font, title_font, small_font, mouse_pos):
    """Draw end-of-day results. Returns (again_rect, menu_rect, next_rect)."""
    grade = get_grade(flow_rate)
    grade_colors = {
        'A': (80, 220, 80),
        'B': (150, 220, 80),
        'C': (255, 210, 50),
        'D': (255, 130, 50),
        'F': (255, 80, 80),
    }
    grade_color = grade_colors[grade]

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pw, ph = 500, 330
    px = (WINDOW_WIDTH - pw) // 2
    py = (WINDOW_HEIGHT - ph) // 2
    pygame.draw.rect(screen, (40, 40, 40), (px, py, pw, ph), border_radius=12)
    pygame.draw.rect(screen, (100, 100, 100), (px, py, pw, ph), 2, border_radius=12)

    header = font.render(f"{city}  —  Level {level}", True, (200, 200, 200))
    screen.blit(header, header.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 18))

    grade_surf = title_font.render(grade, True, grade_color)
    screen.blit(grade_surf, grade_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 55))

    fr_surf = font.render(f"Flow Rate: {flow_rate:.2f}", True, grade_color)
    screen.blit(fr_surf, fr_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 130))

    target_surf = small_font.render(f"Target: {target_flow:.2f}", True, (210, 210, 210))
    screen.blit(target_surf, target_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 168))

    if passed and has_next_level:
        result_text = "PASS - Next level unlocked"
        result_color = (90, 230, 120)
    elif passed:
        result_text = "CITY COMPLETE"
        result_color = (90, 230, 120)
    else:
        result_text = "Below target - try again"
        result_color = (255, 120, 90)
    result_surf = small_font.render(result_text, True, result_color)
    screen.blit(result_surf, result_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 194))

    del_surf = small_font.render(f"Cars Delivered:  {delivered}", True, (200, 200, 200))
    screen.blit(del_surf, del_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 222))

    bh = 44
    by = py + ph - 60

    if has_next_level:
        bw = 150
        gap = 10
        total_w = bw * 3 + gap * 2
        bx = (WINDOW_WIDTH - total_w) // 2

        again_rect = pygame.Rect(bx, by, bw, bh)
        again_hov = again_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, BUTTON_HOVER_COLOR if again_hov else BUTTON_COLOR,
                         again_rect, border_radius=10)
        again_label = font.render("Play Again", True, BUTTON_TEXT_COLOR)
        screen.blit(again_label, again_label.get_rect(center=again_rect.center))

        next_rect = pygame.Rect(bx + bw + gap, by, bw, bh)
        next_hov = next_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, BUTTON_HOVER_COLOR if next_hov else BUTTON_COLOR,
                         next_rect, border_radius=10)
        next_label = font.render("Next Level", True, BUTTON_TEXT_COLOR)
        screen.blit(next_label, next_label.get_rect(center=next_rect.center))

        menu_rect = pygame.Rect(bx + 2 * (bw + gap), by, bw, bh)
        menu_hov = menu_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, BUTTON_HOVER_COLOR if menu_hov else BUTTON_COLOR,
                         menu_rect, border_radius=10)
        menu_label = font.render("Main Menu", True, BUTTON_TEXT_COLOR)
        screen.blit(menu_label, menu_label.get_rect(center=menu_rect.center))
    else:
        bw = 180
        gap = 18
        total_w = bw * 2 + gap
        bx = (WINDOW_WIDTH - total_w) // 2

        again_rect = pygame.Rect(bx, by, bw, bh)
        again_hov = again_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, BUTTON_HOVER_COLOR if again_hov else BUTTON_COLOR,
                         again_rect, border_radius=10)
        again_label = font.render("Play Again", True, BUTTON_TEXT_COLOR)
        screen.blit(again_label, again_label.get_rect(center=again_rect.center))

        menu_rect = pygame.Rect(bx + bw + gap, by, bw, bh)
        menu_hov = menu_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, BUTTON_HOVER_COLOR if menu_hov else BUTTON_COLOR,
                         menu_rect, border_radius=10)
        menu_label = font.render("Main Menu", True, BUTTON_TEXT_COLOR)
        screen.blit(menu_label, menu_label.get_rect(center=menu_rect.center))

        next_rect = None

    return again_rect, menu_rect, next_rect


async def run_game(screen, selected_city, selected_level, unlocked_levels=None):
    """Run the game for the selected city."""
    pygame.display.set_caption(f"City Limits - {selected_city} - Level {selected_level}")

    grid_configs = {
        1: (1, 3),
        2: (2, 3),
        3: (3, 3),
    }
    rows, cols = grid_configs[selected_level]
    grid_start_x, grid_start_y = compute_grid_origin(rows, cols, CELL_SIZE, left_ui_right_edge=240)
    network = IntersectionNetwork(rows, cols, grid_start_x, grid_start_y, CELL_SIZE)

    spawn_markers = generate_spawn_points(
        selected_level, rows, cols, grid_start_x, grid_start_y, CELL_SIZE
    )
    starts = [m for m in spawn_markers if m['type'] == 'start']
    ends = [m for m in spawn_markers if m['type'] == 'end']

    back_button_rect = pygame.Rect(20, 20, 100, 40)
    start_button_rect = pygame.Rect(130, 20, 100, 40)
    pause_button_rect = pygame.Rect(WINDOW_WIDTH - 100, 20, 100, 40)
    clock_anchor = (WINDOW_WIDTH // 2, 20)
    rush_anchor = (260, 38)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 28)
    hud_font = pygame.font.Font(None, 22)
    marker_font = pygame.font.Font(None, 24)
    hint_font = pygame.font.Font(None, 24)
    touch_font = pygame.font.Font(None, 24)

    PALETTE_TYPES = [
        IntersectionType.T_INTERSECTION,
        IntersectionType.TRUMPET,
        IntersectionType.Y_INTERSECTION,
        IntersectionType.FOUR_WAY,
        IntersectionType.ROUNDABOUT,
        IntersectionType.CLOVERLEAF,
        IntersectionType.DIAMOND,
        IntersectionType.PARTIAL_CLOVERLEAF,
    ]
    PALETTE_SLOT_H = 58
    PALETTE_HEADER_H = 34
    PALETTE_PANEL_W = 220
    palette_toggle_rect = pygame.Rect(20, WINDOW_HEIGHT // 2 - 22, 160, 44)
    palette_panel_rect = pygame.Rect(
        20,
        72,
        PALETTE_PANEL_W,
        PALETTE_HEADER_H + 20 + len(PALETTE_TYPES) * PALETTE_SLOT_H,
    )
    palette_open = False
    used_palette_types = set()

    _palette_previews = {
        itype: Intersection(None, None, 0, 0, intersection_type=itype)
        for itype in PALETTE_TYPES
    }

    placed_intersections = []
    dragging_intersection = None
    selected_intersection = None

    cars = []
    clock = pygame.time.Clock()
    spawn_timer = 0.0

    completed_stats = []
    flow_rate = 0.0
    spawn_attempts = 0
    spawn_successes = 0
    _stats_len = 0
    _prev_attempts = 0

    prev_flow_rate = 0.0
    score_delta = 0.0
    delta_alpha = 0.0
    delta_y_offset = 0.0

    game_timer = GAME_DAY_LENGTH * 7 / 24
    is_started = False
    is_paused = False
    pause_confirm_exit = False
    showing_intro = selected_level == 1
    game_ended = False
    level_target = LEVEL_PASS_TARGETS.get(selected_level, LEVEL_PASS_TARGETS[1])
    progress_recorded = False
    label_alpha = 255.0
    first_car_spawned = False
    hint_particles = []
    pending_undo_data = None
    undo_timer = 0.0
    title_font = pygame.font.Font(None, 72)

    browser_mode = is_browser_runtime()
    pointer_pos = pygame.mouse.get_pos()
    last_touch_event_ms = -1000

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.1)

        if is_started and not is_paused:
            game_timer += dt
            if first_car_spawned and label_alpha > 0:
                label_alpha = max(0.0, label_alpha - 127.5 * dt)

        if undo_timer > 0.0:
            undo_timer = max(0.0, undo_timer - dt)
            if undo_timer == 0.0:
                pending_undo_data = None

        if is_started and not is_paused and not game_ended and game_timer >= GAME_DAY_LENGTH:
            game_ended = True
            is_started = False

        if selected_intersection and selected_intersection not in placed_intersections:
            selected_intersection = None

        mouse_pos = pointer_pos
        back_button_hovered = back_button_rect.collidepoint(mouse_pos)
        start_button_hovered = start_button_rect.collidepoint(mouse_pos)
        pause_button_hovered = pause_button_rect.collidepoint(mouse_pos)
        touch_action_states = get_touch_action_states(
            dragging_intersection is not None,
            selected_intersection is not None,
            pending_undo_data and undo_timer > 0.0,
        )

        if is_paused and not game_ended:
            screen.fill(BACKGROUND_COLOR)
            pause_hour = draw_clock(screen, game_timer, font, center=clock_anchor)
            if (7 <= pause_hour < 10) or (16 <= pause_hour < 19):
                rh_surf = small_font.render("RUSH HOUR", True, (255, 165, 40))
                screen.blit(rh_surf, rh_surf.get_rect(center=rush_anchor))

            draw_pause_controls(
                screen, start_button_rect, pause_button_rect, is_paused, is_started, small_font, mouse_pos
            )
            back_col = BUTTON_HOVER_COLOR if back_button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
            pygame.draw.rect(screen, back_col, back_button_rect, border_radius=10)
            back_surf = small_font.render("Back", True, BUTTON_TEXT_COLOR)
            screen.blit(back_surf, back_surf.get_rect(center=back_button_rect.center))

            for row in range(rows):
                for col in range(cols):
                    x = grid_start_x + col * CELL_SIZE
                    y = grid_start_y + row * CELL_SIZE
                    pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                    pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)

            network.draw(screen, highlighted_intersection=selected_intersection)
            draw_spawn_markers(screen, spawn_markers, marker_font, label_alpha)
            for car in cars:
                car.draw(screen)

            draw_palette_toggle_button(screen, palette_toggle_rect, palette_open, marker_font, mouse_pos)
            if palette_open:
                draw_palette_menu(
                    screen,
                    palette_panel_rect,
                    PALETTE_TYPES,
                    used_palette_types,
                    PALETTE_SLOT_H,
                    PALETTE_HEADER_H,
                    marker_font,
                    mouse_pos,
                    _palette_previews,
                )

            resume_r, restart_r, menu_r, conf = draw_pause_overlay(
                screen, selected_city, selected_level, font, small_font, mouse_pos, pause_confirm_exit
            )

            for event in pygame.event.get():
                normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)
                if normalized and normalized["pointer"] == "touch":
                    last_touch_event_ms = pygame.time.get_ticks()
                elif normalized and browser_mode and normalized["pointer"] == "mouse":
                    if pygame.time.get_ticks() - last_touch_event_ms < 250:
                        normalized = None

                if normalized:
                    mouse_pos = normalized["pos"]
                    pointer_pos = mouse_pos

                if event.type == pygame.QUIT:
                    return False
                if normalized and normalized["kind"] == "down" and normalized["button"] == 1:
                    pos = normalized["pos"]
                    if not pause_confirm_exit:
                        if resume_r.collidepoint(pos):
                            is_paused = False
                        elif restart_r.collidepoint(pos):
                            return "REPLAY"
                        elif menu_r.collidepoint(pos):
                            pause_confirm_exit = True
                    else:
                        yes_r, no_r = conf
                        if yes_r.collidepoint(pos):
                            return True
                        if no_r.collidepoint(pos):
                            pause_confirm_exit = False
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    if not pause_confirm_exit:
                        is_paused = False

            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        if showing_intro:
            screen.fill(BACKGROUND_COLOR)
            for row in range(rows):
                for col in range(cols):
                    x = grid_start_x + col * CELL_SIZE
                    y = grid_start_y + row * CELL_SIZE
                    pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                    pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)
            draw_spawn_markers(screen, spawn_markers, marker_font, label_alpha)
            got_it_rect = draw_intro_overlay(screen, font, small_font, mouse_pos)

            for event in pygame.event.get():
                normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)
                if normalized and normalized["pointer"] == "touch":
                    last_touch_event_ms = pygame.time.get_ticks()
                elif normalized and browser_mode and normalized["pointer"] == "mouse":
                    if pygame.time.get_ticks() - last_touch_event_ms < 250:
                        normalized = None

                if normalized:
                    mouse_pos = normalized["pos"]
                    pointer_pos = mouse_pos

                if event.type == pygame.QUIT:
                    return False
                if normalized and normalized["kind"] == "down" and normalized["button"] == 1:
                    if got_it_rect.collidepoint(normalized["pos"]):
                        showing_intro = False
                        is_started = True
                        is_paused = False
                        spawn_timer = 0.0

            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        current_spawn_interval = get_spawn_interval(selected_city, game_timer, GAME_DAY_LENGTH, selected_level)
        spawn_timer += dt if (is_started and not is_paused) else 0.0
        if spawn_timer >= current_spawn_interval and ends and is_started:
            spawn_timer = 0.0
            for start_m in starts:
                end_m = random.choice(ends)
                if network.get_all_intersections():
                    spawn_attempts += 1
                    start_int = _find_nearest_intersection(network, start_m['x'], start_m['y'])
                    end_int = _find_nearest_intersection(network, end_m['x'], end_m['y'])

                    if start_int and end_int:
                        intersection_path = network.find_path(start_int, end_int)
                        if intersection_path:
                            pixel_path = network.intersections_to_pixels(intersection_path)
                            cars.append(Car(pixel_path))
                            spawn_successes += 1
                        else:
                            hint_particles.append({
                                'text': '?',
                                'color': (255, 160, 30),
                                'x': float(start_m['x']),
                                'y': float(start_m['y']),
                                'alpha': 255.0,
                                'vy': -40.0,
                            })
                    else:
                        hint_particles.append({
                            'text': '?',
                            'color': (255, 160, 30),
                            'x': float(start_m['x']),
                            'y': float(start_m['y']),
                            'alpha': 255.0,
                            'vy': -40.0,
                        })

        for car in cars:
            if car.done:
                completed_stats.append((car.path_length, car.travel_time, car.idle_time))
                first_car_spawned = True
                hint_particles.append({
                    'text': '+1',
                    'color': (80, 220, 80),
                    'x': float(car.x),
                    'y': float(car.y),
                    'alpha': 255.0,
                    'vy': -60.0,
                })
        cars = [c for c in cars if not c.done]

        if len(completed_stats) != _stats_len or spawn_attempts != _prev_attempts:
            new_flow_rate = calculate_flow_rate(completed_stats, spawn_attempts, spawn_successes)
            _stats_len = len(completed_stats)
            _prev_attempts = spawn_attempts
            if abs(new_flow_rate - prev_flow_rate) > 0.001:
                score_delta = new_flow_rate - prev_flow_rate
                delta_alpha = 255.0
                delta_y_offset = 0.0
                prev_flow_rate = new_flow_rate
            flow_rate = new_flow_rate

        if delta_alpha > 0:
            delta_alpha = max(0.0, delta_alpha - 127.5 * dt)
            delta_y_offset -= 25.0 * dt

        if not game_ended:
            for event in pygame.event.get():
                normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)
                if normalized and normalized["pointer"] == "touch":
                    last_touch_event_ms = pygame.time.get_ticks()
                elif normalized and browser_mode and normalized["pointer"] == "mouse":
                    if pygame.time.get_ticks() - last_touch_event_ms < 250:
                        normalized = None

                if normalized:
                    mouse_pos = normalized["pos"]
                    pointer_pos = mouse_pos

                if event.type == pygame.QUIT:
                    return False

                if normalized and normalized["kind"] == "down" and normalized["button"] == 1:
                    pos = normalized["pos"]

                    if browser_mode:
                        touch_buttons = get_touch_toolbar_button_rects()
                        if touch_action_states["rotate"] and touch_buttons["rotate"].collidepoint(pos):
                            if dragging_intersection:
                                dragging_intersection.rotate()
                            elif selected_intersection:
                                selected_intersection.rotate()
                                network.add_intersection(selected_intersection)
                            continue
                        if touch_action_states["delete"] and touch_buttons["delete"].collidepoint(pos):
                            pending_undo_data = _delete_placed_intersection(
                                selected_intersection, network, placed_intersections
                            )
                            selected_intersection = None
                            undo_timer = UNDO_WINDOW_SECONDS
                            continue
                        if touch_action_states["undo"] and touch_buttons["undo"].collidepoint(pos):
                            restored = _restore_deleted_intersection(
                                pending_undo_data,
                                network,
                                placed_intersections,
                                grid_start_x,
                                grid_start_y,
                                CELL_SIZE,
                            )
                            if restored:
                                hint_particles.append({
                                    'text': 'U',
                                    'color': (80, 220, 80),
                                    'x': pending_undo_data['x'],
                                    'y': pending_undo_data['y'],
                                    'alpha': 255.0,
                                    'vy': -55.0,
                                })
                                selected_intersection = restored
                            else:
                                hint_particles.append({
                                    'text': 'X',
                                    'color': (255, 100, 100),
                                    'x': pending_undo_data['x'],
                                    'y': pending_undo_data['y'],
                                    'alpha': 255.0,
                                    'vy': -45.0,
                                })
                            pending_undo_data = None
                            undo_timer = 0.0
                            continue

                    if back_button_rect.collidepoint(pos):
                        return True
                    if start_button_rect.collidepoint(pos):
                        is_started = not is_started
                        is_paused = False
                        spawn_timer = 0.0
                        continue
                    if pause_button_rect.collidepoint(pos):
                        if is_started and not is_paused:
                            is_paused = True
                        continue
                    if palette_toggle_rect.collidepoint(pos):
                        palette_open = not palette_open
                        if palette_open:
                            selected_intersection = None
                        continue

                    if palette_open:
                        handled_palette_click = False
                        for i, itype in enumerate(PALETTE_TYPES):
                            slot_rect = _palette_slot_rect(
                                palette_panel_rect,
                                i,
                                PALETTE_SLOT_H,
                                PALETTE_HEADER_H,
                            )
                            if slot_rect.collidepoint(pos):
                                handled_palette_click = True
                                if itype in used_palette_types:
                                    hint_particles.append({
                                        'text': 'USED',
                                        'color': (255, 120, 120),
                                        'x': float(slot_rect.centerx),
                                        'y': float(slot_rect.centery),
                                        'alpha': 255.0,
                                        'vy': -36.0,
                                    })
                                else:
                                    dragging_intersection = Intersection(
                                        None, None, pos[0], pos[1], intersection_type=itype
                                    )
                                    selected_intersection = None
                                    palette_open = False
                                break
                        if handled_palette_click:
                            continue

                    if dragging_intersection and normalized["pointer"] == "touch":
                        dragging_intersection.update_position(pos)
                        continue

                    clicked = _find_clicked_placed_intersection(placed_intersections, pos)
                    selected_intersection = clicked

                if normalized and normalized["kind"] == "up" and normalized["button"] == 1:
                    if dragging_intersection:
                        dragging_intersection.update_position(normalized["pos"])
                        placed_ok = _place_dragging_intersection(
                            dragging_intersection,
                            network,
                            placed_intersections,
                            used_palette_types,
                            grid_start_x,
                            grid_start_y,
                            CELL_SIZE,
                            rows,
                            cols,
                        )
                        if placed_ok:
                            selected_intersection = dragging_intersection
                            dragging_intersection.dragging = False
                            dragging_intersection = None
                        elif normalized["pointer"] == "mouse":
                            dragging_intersection.dragging = False
                            dragging_intersection = None

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if dragging_intersection:
                            dragging_intersection.rotate()
                        elif selected_intersection:
                            selected_intersection.rotate()
                            network.add_intersection(selected_intersection)
                    elif event.key == pygame.K_u and pending_undo_data and undo_timer > 0.0:
                        restored = _restore_deleted_intersection(
                            pending_undo_data,
                            network,
                            placed_intersections,
                            grid_start_x,
                            grid_start_y,
                            CELL_SIZE,
                        )
                        if restored:
                            hint_particles.append({
                                'text': 'U',
                                'color': (80, 220, 80),
                                'x': pending_undo_data['x'],
                                'y': pending_undo_data['y'],
                                'alpha': 255.0,
                                'vy': -55.0,
                            })
                            selected_intersection = restored
                        else:
                            hint_particles.append({
                                'text': 'X',
                                'color': (255, 100, 100),
                                'x': pending_undo_data['x'],
                                'y': pending_undo_data['y'],
                                'alpha': 255.0,
                                'vy': -45.0,
                            })
                        pending_undo_data = None
                        undo_timer = 0.0
                    elif event.key in (pygame.K_ESCAPE, pygame.K_p):
                        if is_started and not is_paused:
                            is_paused = True

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    clicked = _find_clicked_placed_intersection(placed_intersections, event.pos)
                    if clicked:
                        pending_undo_data = _delete_placed_intersection(clicked, network, placed_intersections)
                        if selected_intersection == clicked:
                            selected_intersection = None
                        undo_timer = UNDO_WINDOW_SECONDS

        if dragging_intersection:
            dragging_intersection.update_position(mouse_pos)

        if is_started and not is_paused:
            for car in cars:
                car.update(dt)

        screen.fill(BACKGROUND_COLOR)
        game_hour = draw_clock(screen, game_timer, font, center=clock_anchor)
        if (7 <= game_hour < 10) or (16 <= game_hour < 19):
            rh_surf = small_font.render("RUSH HOUR", True, (255, 165, 40))
            screen.blit(rh_surf, rh_surf.get_rect(center=rush_anchor))

        if flow_rate >= 0.75:
            fr_color = (80, 220, 80)
        elif flow_rate >= 0.45:
            fr_color = (255, 210, 50)
        else:
            fr_color = (255, 80, 80)

        bar_w, bar_h = 130, 8
        bar_x = WINDOW_WIDTH - 10 - bar_w
        bar_y = WINDOW_HEIGHT - 14
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * min(flow_rate, 1.0))
        if fill_w > 0:
            pygame.draw.rect(screen, fr_color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        fr_text = hud_font.render(f"Flow: {flow_rate:.2f}", True, fr_color)
        screen.blit(fr_text, fr_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 25)))

        vol = get_current_volume(selected_city, game_timer, GAME_DAY_LENGTH)
        vol_text = hud_font.render(f"Traffic: {vol}", True, (200, 200, 200))
        screen.blit(vol_text, vol_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 45)))

        active_text = hud_font.render(f"Cars: {len(cars)}", True, (200, 200, 200))
        screen.blit(active_text, active_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 65)))

        done_text = hud_font.render(f"Delivered: {len(completed_stats)}", True, (200, 200, 200))
        screen.blit(done_text, done_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 85)))

        diff_labels = {
            "New York City": ("Normal", (200, 200, 200)),
            "Los Angeles": ("Hard", (255, 100, 80)),
            "Chicago": ("Easy", (80, 210, 120)),
        }
        diff_label, diff_color = diff_labels.get(selected_city, ("Normal", (200, 200, 200)))
        diff_text = hud_font.render(f"Diff: {diff_label}", True, diff_color)
        screen.blit(diff_text, diff_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 105)))

        if delta_alpha > 0:
            sign = "+" if score_delta > 0 else ""
            delta_color = (80, 220, 80) if score_delta > 0 else (255, 80, 80)
            delta_surf = hud_font.render(f"{sign}{score_delta:.2f}", True, delta_color)
            delta_surf.set_alpha(int(delta_alpha))
            base_y = WINDOW_HEIGHT - 25
            screen.blit(
                delta_surf,
                delta_surf.get_rect(bottomright=(WINDOW_WIDTH - 10, int(base_y + delta_y_offset))),
            )

        if pending_undo_data and undo_timer > 0.0 and not game_ended:
            draw_undo_prompt(screen, small_font, undo_timer, anchor_x=150)

        draw_pause_controls(screen, start_button_rect, pause_button_rect, is_paused, is_started, small_font, mouse_pos)

        if not game_ended and not browser_mode:
            draw_control_hint_strip(screen, hint_font)
            if back_button_hovered:
                draw_button_tooltip(screen, marker_font, back_button_rect, "Back to level select")
            elif start_button_hovered:
                start_tip = "Start traffic" if not is_started else "Stop traffic"
                draw_button_tooltip(screen, marker_font, start_button_rect, start_tip)
            elif pause_button_hovered and is_started and not is_paused:
                draw_button_tooltip(screen, marker_font, pause_button_rect, "Pause (P/Esc)")
            elif palette_toggle_rect.collidepoint(mouse_pos):
                menu_tip = "Close intersection menu" if palette_open else "Open intersection menu"
                draw_button_tooltip(screen, marker_font, palette_toggle_rect, menu_tip)

        back_button_color = BUTTON_HOVER_COLOR if back_button_hovered else BUTTON_COLOR
        pygame.draw.rect(screen, back_button_color, back_button_rect, border_radius=10)
        back_text = small_font.render("Back", True, BUTTON_TEXT_COLOR)
        screen.blit(back_text, back_text.get_rect(center=back_button_rect.center))

        draw_palette_toggle_button(screen, palette_toggle_rect, palette_open, marker_font, mouse_pos)
        if palette_open:
            draw_palette_menu(
                screen,
                palette_panel_rect,
                PALETTE_TYPES,
                used_palette_types,
                PALETTE_SLOT_H,
                PALETTE_HEADER_H,
                marker_font,
                mouse_pos,
                _palette_previews,
            )

        for row in range(rows):
            for col in range(cols):
                x = grid_start_x + col * CELL_SIZE
                y = grid_start_y + row * CELL_SIZE
                pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)

        network.draw(screen, highlighted_intersection=selected_intersection)
        draw_spawn_markers(screen, spawn_markers, marker_font, label_alpha)

        for car in cars:
            car.draw(screen)

        for particle in hint_particles:
            particle['y'] += particle['vy'] * dt
            particle['alpha'] = max(0.0, particle['alpha'] - 255.0 * dt)
        hint_particles = [particle for particle in hint_particles if particle['alpha'] > 0]
        for particle in hint_particles:
            particle_surf = marker_font.render(particle['text'], True, particle['color'])
            particle_surf.set_alpha(int(particle['alpha']))
            screen.blit(
                particle_surf,
                particle_surf.get_rect(center=(int(particle['x']), int(particle['y']))),
            )

        if dragging_intersection:
            dragging_intersection.draw(screen)

        if browser_mode and not game_ended:
            draw_touch_toolbar(screen, touch_font, mouse_pos, touch_action_states)

        if game_ended:
            level_passed = flow_rate >= level_target
            has_next_level = level_passed and selected_level < MAX_LEVEL

            if not progress_recorded:
                if level_passed and unlocked_levels is not None and selected_level < MAX_LEVEL:
                    unlocked_levels[selected_city] = max(
                        unlocked_levels.get(selected_city, 1),
                        selected_level + 1,
                    )
                progress_recorded = True

            again_rect, menu_rect, next_rect = draw_end_screen(
                screen,
                flow_rate,
                len(completed_stats),
                selected_city,
                selected_level,
                level_target,
                level_passed,
                has_next_level,
                font,
                title_font,
                small_font,
                mouse_pos,
            )

            for event in pygame.event.get():
                normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)
                if normalized and normalized["pointer"] == "touch":
                    last_touch_event_ms = pygame.time.get_ticks()
                elif normalized and browser_mode and normalized["pointer"] == "mouse":
                    if pygame.time.get_ticks() - last_touch_event_ms < 250:
                        normalized = None

                if normalized:
                    mouse_pos = normalized["pos"]
                    pointer_pos = mouse_pos

                if event.type == pygame.QUIT:
                    return False
                if normalized and normalized["kind"] == "down" and normalized["button"] == 1:
                    pos = normalized["pos"]
                    if again_rect.collidepoint(pos):
                        return "REPLAY"
                    if next_rect and next_rect.collidepoint(pos):
                        return "NEXT_LEVEL"
                    if menu_rect.collidepoint(pos):
                        return True

        pygame.display.flip()
        await asyncio.sleep(0)

    return True


async def async_main():
    """Main function managing menu, level-select, and gameplay states."""
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("City Limits")

    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 72)
    frame_clock = pygame.time.Clock()
    browser_mode = is_browser_runtime()
    last_touch_event_ms = -1000

    current_state = STATE_MENU
    selected_city = None
    selected_level = None
    city_names = ["New York City", "Los Angeles", "Chicago"]
    unlocked_levels = {city: 1 for city in city_names}

    running = True
    while running:
        frame_clock.tick(60)

        if current_state == STATE_MENU:
            all_unlocked = all(level >= MAX_LEVEL for level in unlocked_levels.values())
            city_buttons, unlock_button = draw_menu(
                screen,
                font,
                title_font,
                all_unlocked=all_unlocked,
            )

            for event in pygame.event.get():
                normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)
                if normalized and normalized["pointer"] == "touch":
                    last_touch_event_ms = pygame.time.get_ticks()
                elif normalized and browser_mode and normalized["pointer"] == "mouse":
                    if pygame.time.get_ticks() - last_touch_event_ms < 250:
                        normalized = None

                if event.type == pygame.QUIT:
                    running = False
                elif normalized and normalized["kind"] == "down" and normalized["button"] == 1:
                    pos = normalized["pos"]
                    if unlock_button.collidepoint(pos):
                        for city in city_names:
                            unlocked_levels[city] = MAX_LEVEL
                        continue
                    for i, button in enumerate(city_buttons):
                        if button.collidepoint(pos):
                            selected_city = city_names[i]
                            current_state = STATE_LEVEL_SELECT
                            break

            pygame.display.flip()
            await asyncio.sleep(0)

        elif current_state == STATE_LEVEL_SELECT:
            max_unlocked_level = unlocked_levels.get(selected_city, 1)
            level_buttons, back_button = draw_level_menu(
                screen,
                font,
                title_font,
                selected_city,
                max_unlocked_level=max_unlocked_level,
            )

            for event in pygame.event.get():
                normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)
                if normalized and normalized["pointer"] == "touch":
                    last_touch_event_ms = pygame.time.get_ticks()
                elif normalized and browser_mode and normalized["pointer"] == "mouse":
                    if pygame.time.get_ticks() - last_touch_event_ms < 250:
                        normalized = None

                if event.type == pygame.QUIT:
                    running = False
                elif normalized and normalized["kind"] == "down" and normalized["button"] == 1:
                    pos = normalized["pos"]
                    if back_button.collidepoint(pos):
                        current_state = STATE_MENU
                    else:
                        for i, button in enumerate(level_buttons):
                            level_num = i + 1
                            if button.collidepoint(pos) and level_num <= max_unlocked_level:
                                selected_level = level_num
                                current_state = STATE_GAME
                                break

            pygame.display.flip()
            await asyncio.sleep(0)

        elif current_state == STATE_GAME:
            result = await run_game(screen, selected_city, selected_level, unlocked_levels)
            while result == "REPLAY":
                result = await run_game(screen, selected_city, selected_level, unlocked_levels)
            if result == "NEXT_LEVEL":
                selected_level = min(MAX_LEVEL, selected_level + 1)
                current_state = STATE_GAME
            elif result:
                current_state = STATE_LEVEL_SELECT
            else:
                running = False

    pygame.quit()
    raise SystemExit


def main():
    """Launch the game on desktop or in the browser."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
