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



def draw_clock(screen, elapsed_seconds, font):
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
    text_rect = clock_text.get_rect(center=(WINDOW_WIDTH // 2, 20))
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

    goal = small_font.render(
        "Connect spawn points to exit points so cars can flow through the city.",
        True, (200, 200, 200))
    screen.blit(goal, goal.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 65))

    icons = [
        (START_COLOR,       "IN — Cars start here"),
        ((130, 130, 130),   "Drag intersections to build roads"),
        (END_COLOR,         "OUT — Cars must reach here"),
    ]
    col_xs = [px + 90, px + 270, px + 450]
    for (color, caption), cx in zip(icons, col_xs):
        pygame.draw.circle(screen, color, (cx, py + 155), 14)
        pygame.draw.circle(screen, (255, 255, 255), (cx, py + 155), 14, 2)
        words = caption.split()
        line1 = " ".join(words[:3])
        line2 = " ".join(words[3:])
        s1 = small_font.render(line1, True, (180, 180, 180))
        screen.blit(s1, s1.get_rect(centerx=cx, top=py + 176))
        if line2:
            s2 = small_font.render(line2, True, (180, 180, 180))
            screen.blit(s2, s2.get_rect(centerx=cx, top=py + 196))

    bw, bh = 220, 44
    got_it_rect = pygame.Rect((WINDOW_WIDTH - bw) // 2, py + ph - 62, bw, bh)
    hov = got_it_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, BUTTON_HOVER_COLOR if hov else BUTTON_COLOR, got_it_rect, border_radius=10)
    btn = font.render("Got it!", True, BUTTON_TEXT_COLOR)
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

        # IN / OUT label below the circle
        tag = "IN" if is_start else "OUT"
        tag_surf = font.render(tag, True, color)
        tag_surf.set_alpha(int(label_alpha))
        screen.blit(tag_surf, tag_surf.get_rect(center=(mx, my + MARKER_RADIUS + 8)))


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


def draw_palette(screen, palette_types, palette_start_x, palette_y,
                 slot_w, slot_h, small_font, mouse_pos, preview_cache=None):
    """Draw the intersection type palette strip at the bottom of the screen."""
    for i, itype in enumerate(palette_types):
        sx = palette_start_x + i * slot_w
        rect = pygame.Rect(sx, palette_y, slot_w, slot_h)

        bg = (70, 70, 70) if rect.collidepoint(mouse_pos) else (50, 50, 50)
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, (90, 90, 90), rect, 1)

        if preview_cache and itype in preview_cache:
            preview_cache[itype].draw(screen)
        else:
            Intersection(None, None, sx + slot_w // 2, palette_y + 28,
                         intersection_type=itype).draw(screen)

        label = small_font.render(itype.value, True, (180, 180, 180))
        if label.get_width() > slot_w - 4:
            short = itype.value.split()[0]
            label = small_font.render(short, True, (180, 180, 180))
        screen.blit(label, label.get_rect(centerx=sx + slot_w // 2,
                                          top=palette_y + 52))


def draw_end_screen(screen, flow_rate, delivered, city, level, font, title_font, small_font, mouse_pos):
    """Draw the end-of-day results overlay. Returns (again_rect, menu_rect)."""
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

    pw, ph = 420, 280
    px = (WINDOW_WIDTH - pw) // 2
    py = (WINDOW_HEIGHT - ph) // 2
    pygame.draw.rect(screen, (40, 40, 40), (px, py, pw, ph), border_radius=12)
    pygame.draw.rect(screen, (100, 100, 100), (px, py, pw, ph), 2, border_radius=12)

    header = font.render(f"{city}  —  Level {level}", True, (200, 200, 200))
    screen.blit(header, header.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 18))

    grade_surf = title_font.render(grade, True, grade_color)
    screen.blit(grade_surf, grade_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 55))

    fr_surf = font.render(f"Flow Rate:  {flow_rate:.2f}", True, grade_color)
    screen.blit(fr_surf, fr_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 130))

    del_surf = small_font.render(f"Cars Delivered:  {delivered}", True, (200, 200, 200))
    screen.blit(del_surf, del_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=py + 165))

    bw, bh = 160, 44

    again_rect = pygame.Rect(px + 30, py + ph - 60, bw, bh)
    again_hov = again_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, BUTTON_HOVER_COLOR if again_hov else BUTTON_COLOR,
                     again_rect, border_radius=10)
    again_label = font.render("Play Again", True, BUTTON_TEXT_COLOR)
    screen.blit(again_label, again_label.get_rect(center=again_rect.center))

    menu_rect = pygame.Rect(px + pw - 30 - bw, py + ph - 60, bw, bh)
    menu_hov = menu_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, BUTTON_HOVER_COLOR if menu_hov else BUTTON_COLOR,
                     menu_rect, border_radius=10)
    menu_label = font.render("Main Menu", True, BUTTON_TEXT_COLOR)
    screen.blit(menu_label, menu_label.get_rect(center=menu_rect.center))

    return again_rect, menu_rect


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

    # Compute grid screen position — always centered on screen
    grid_start_x = (WINDOW_WIDTH - cols * CELL_SIZE) // 2
    grid_start_y = (WINDOW_HEIGHT - rows * CELL_SIZE) // 2

    # Create the intersection network
    network = IntersectionNetwork(rows, cols, grid_start_x, grid_start_y, CELL_SIZE)

    # Generate spawn/end markers once for this level
    spawn_markers = generate_spawn_points(
        selected_level, rows, cols, grid_start_x, grid_start_y, CELL_SIZE
    )
    starts = [m for m in spawn_markers if m['type'] == 'start']
    ends   = [m for m in spawn_markers if m['type'] == 'end']

    # Button setup
    back_button_rect = pygame.Rect(20, 20, 100, 40)
    start_button_rect = pygame.Rect(130, 20, 100, 40)
    pause_button_rect = pygame.Rect(WINDOW_WIDTH - 100, 20, 100, 40)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 28)
    marker_font = pygame.font.Font(None, 24)

    # --- Intersection palette (replaces old 5-node tray) ---
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
    PALETTE_SLOT_W = 80
    PALETTE_SLOT_H = 70
    palette_start_x = (WINDOW_WIDTH - len(PALETTE_TYPES) * PALETTE_SLOT_W) // 2
    palette_y = WINDOW_HEIGHT - PALETTE_SLOT_H

    # Cache one Intersection preview per palette type — avoids ~480 allocs/sec
    _palette_previews = {
        itype: Intersection(
            None, None,
            palette_start_x + i * PALETTE_SLOT_W + PALETTE_SLOT_W // 2,
            palette_y + 28,
            intersection_type=itype,
        )
        for i, itype in enumerate(PALETTE_TYPES)
    }

    placed_intersections = []   # all intersections currently on the grid
    dragging_intersection = None

    # Car spawn system
    cars = []
    clock = pygame.time.Clock()
    spawn_timer = 0.0

    # Scoring
    completed_stats = []   # (path_length, travel_time, idle_time) per finished car
    flow_rate = 0.0
    spawn_attempts = 0     # how many cars the network tried to route
    spawn_successes = 0    # how many cars actually found a valid path
    _stats_len = 0         # cached length of completed_stats for change detection
    _prev_attempts = 0     # cached spawn_attempts for change detection

    # Visual feedback state for score change indicator
    prev_flow_rate = 0.0
    score_delta = 0.0
    delta_alpha = 0.0      # 0–255; fades to 0 over ~2 seconds
    delta_y_offset = 0.0   # floats upward as it fades

    # Clock system — start at 07:00 so morning rush begins immediately
    game_timer = GAME_DAY_LENGTH * 7 / 24  # 07:00 start so morning rush begins immediately

    # Pause/Start system
    is_started = False
    is_paused = False
    pause_confirm_exit = False      # True when confirmation sub-card is showing
    showing_intro = True            # Show tutorial card before player sets up
    game_ended = False

    # Marker label fade
    label_alpha = 255.0       # fades to 0 over 2s after first car spawns
    first_car_spawned = False

    # Hint particles: list of dicts {text, color, x, y, alpha, vy}
    hint_particles = []

    # Title font for end screen grade display
    title_font = pygame.font.Font(None, 72)

    # Game loop
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.1)  # cap at 100 ms to prevent lag-spike glitches
        
        # Only increment timer if game is started and not paused
        if is_started and not is_paused:
            game_timer += dt
            if first_car_spawned and label_alpha > 0:
                label_alpha = max(0.0, label_alpha - 127.5 * dt)  # fades over ~2 s

        if is_started and not is_paused and not game_ended and game_timer >= GAME_DAY_LENGTH:
            game_ended = True
            is_started = False

        mouse_pos = pygame.mouse.get_pos()
        back_button_hovered = back_button_rect.collidepoint(mouse_pos)
        start_button_hovered = start_button_rect.collidepoint(mouse_pos)
        pause_button_hovered = pause_button_rect.collidepoint(mouse_pos)

        # Pause overlay — draw game state, then overlay; handle only pause events.
        if is_paused and not game_ended:
            screen.fill(BACKGROUND_COLOR)
            _ph = draw_clock(screen, game_timer, font)
            if (7 <= _ph < 10) or (16 <= _ph < 19):
                rh_s = small_font.render("RUSH HOUR", True, (255, 165, 40))
                screen.blit(rh_s, rh_s.get_rect(center=(WINDOW_WIDTH // 2, 38)))
            draw_pause_controls(screen, start_button_rect, pause_button_rect,
                                is_paused, is_started, small_font, mouse_pos)
            back_col = BUTTON_HOVER_COLOR if back_button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
            pygame.draw.rect(screen, back_col, back_button_rect, border_radius=10)
            screen.blit(small_font.render("Back", True, BUTTON_TEXT_COLOR),
                        small_font.render("Back", True, BUTTON_TEXT_COLOR).get_rect(center=back_button_rect.center))
            for row in range(rows):
                for col in range(cols):
                    x = grid_start_x + col * CELL_SIZE
                    y = grid_start_y + row * CELL_SIZE
                    pygame.draw.rect(screen, CELL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                    pygame.draw.rect(screen, GRID_COLOR, (x, y, CELL_SIZE, CELL_SIZE), 3)
            network.draw(screen)
            draw_spawn_markers(screen, spawn_markers, marker_font, label_alpha)
            for car in cars:
                car.draw(screen)
            draw_palette(screen, PALETTE_TYPES, palette_start_x, palette_y,
                         PALETTE_SLOT_W, PALETTE_SLOT_H, small_font, mouse_pos, _palette_previews)
            resume_r, restart_r, menu_r, conf = draw_pause_overlay(
                screen, selected_city, selected_level, font, small_font, mouse_pos, pause_confirm_exit)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
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
                        elif no_r.collidepoint(pos):
                            pause_confirm_exit = False
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    if not pause_confirm_exit:
                        is_paused = False
            pygame.display.flip()
            continue

        # Intro overlay — shown at level start, before the player sets up
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
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if got_it_rect.collidepoint(pygame.mouse.get_pos()):
                        showing_intro = False
            pygame.display.flip()
            continue

        # Spawn a new wave of cars when the timer fires.
        # Interval is derived from real traffic volume at the current game hour:
        # peak hours (rush hour) → short interval; overnight → long interval.
        current_spawn_interval = get_spawn_interval(selected_city, game_timer, GAME_DAY_LENGTH, selected_level)
        spawn_timer += dt if (is_started and not is_paused) else 0
        if spawn_timer >= current_spawn_interval and ends and is_started:
            spawn_timer = 0.0
            for start_m in starts:
                end_m = random.choice(ends)

                # Only count attempts once the player has placed intersections
                if network.get_all_intersections():
                    spawn_attempts += 1
                    start_int = _find_nearest_intersection(network, start_m['x'], start_m['y'])
                    end_int = _find_nearest_intersection(network, end_m['x'], end_m['y'])

                    if start_int and end_int:
                        # Find path through intersection network
                        intersection_path = network.find_path(start_int, end_int)
                        if intersection_path:
                            # Convert to pixel coordinates
                            pixel_path = network.intersections_to_pixels(intersection_path)
                            cars.append(Car(pixel_path))
                            spawn_successes += 1
                        else:
                            hint_particles.append({
                                'text': '?', 'color': (255, 160, 30),
                                'x': float(start_m['x']), 'y': float(start_m['y']),
                                'alpha': 255.0, 'vy': -40.0,
                            })
                    else:
                        hint_particles.append({
                            'text': '?', 'color': (255, 160, 30),
                            'x': float(start_m['x']), 'y': float(start_m['y']),
                            'alpha': 255.0, 'vy': -40.0,
                        })

        # Collect stats from finished cars then remove them
        for car in cars:
            if car.done:
                completed_stats.append((car.path_length, car.travel_time, car.idle_time))
                first_car_spawned = True
                hint_particles.append({
                    'text': '+1', 'color': (80, 220, 80),
                    'x': float(car.x), 'y': float(car.y),
                    'alpha': 255.0, 'vy': -60.0,
                })
        cars = [c for c in cars if not c.done]

        # Recalculate flow rate only when the underlying data has changed
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

        # Advance delta animation
        if delta_alpha > 0:
            delta_alpha = max(0.0, delta_alpha - 127.5 * dt)  # fades over ~2 s
            delta_y_offset -= 25.0 * dt                       # floats upward

        if not game_ended:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False  # Exit entire game
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if back_button_hovered:
                        return True  # Return to level select
                    elif start_button_hovered:
                        is_started = not is_started
                        is_paused = False  # Unpause when starting
                        spawn_timer = 0.0  # reset on both start and stop
                    elif pause_button_hovered:
                        if is_started and not is_paused:
                            is_paused = True
                    else:
                        # Check palette — start dragging a new intersection of the clicked type
                        for i, itype in enumerate(PALETTE_TYPES):
                            sx = palette_start_x + i * PALETTE_SLOT_W
                            slot_rect = pygame.Rect(sx, palette_y, PALETTE_SLOT_W, PALETTE_SLOT_H)
                            if slot_rect.collidepoint(mouse_pos):
                                dragging_intersection = Intersection(
                                    None, None, mouse_pos[0], mouse_pos[1],
                                    intersection_type=itype
                                )
                                break
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if dragging_intersection:
                        if dragging_intersection.snap_to_grid(
                                grid_start_x, grid_start_y, CELL_SIZE, rows, cols):
                            existing_key = (dragging_intersection.row, dragging_intersection.col)
                            if existing_key in network.placed_intersections:
                                old = network.placed_intersections[existing_key]
                                if old in placed_intersections:
                                    placed_intersections.remove(old)
                            network.add_intersection(dragging_intersection)
                            placed_intersections.append(dragging_intersection)
                        dragging_intersection.dragging = False
                        dragging_intersection = None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and dragging_intersection:
                        dragging_intersection.rotate()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    for placed in placed_intersections:
                        if placed.is_clicked(mouse_pos):
                            network.remove_intersection(placed)
                            placed_intersections.remove(placed)
                            break

        # Update dragging position
        if dragging_intersection:
            dragging_intersection.update_position(mouse_pos)

        # Update all cars only while the simulation is running
        if is_started and not is_paused:
            for car in cars:
                car.update(dt)

        # Clear screen
        screen.fill(BACKGROUND_COLOR)

        # Draw clock at top; returns current game hour for rush-hour indicator
        game_hour = draw_clock(screen, game_timer, font)

        # Rush hour indicator — shown just below the clock during peak periods
        if (7 <= game_hour < 10) or (16 <= game_hour < 19):
            rh_surf = small_font.render("RUSH HOUR", True, (255, 165, 40))
            screen.blit(rh_surf, rh_surf.get_rect(center=(WINDOW_WIDTH // 2, 38)))

        # --- Score panel (bottom-right) ---
        # Colour reflects performance: green = good, yellow = mid, red = poor
        if flow_rate >= 0.75:
            fr_color = (80, 220, 80)
        elif flow_rate >= 0.45:
            fr_color = (255, 210, 50)
        else:
            fr_color = (255, 80, 80)

        # Progress bar
        bar_w, bar_h = 130, 8
        bar_x = WINDOW_WIDTH - 10 - bar_w
        bar_y = WINDOW_HEIGHT - 14
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * min(flow_rate, 1.0))
        if fill_w > 0:
            pygame.draw.rect(screen, fr_color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        # Flow rate text
        fr_text = small_font.render(f"Flow Rate: {flow_rate:.2f}", True, fr_color)
        screen.blit(fr_text, fr_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 25)))

        # Traffic volume
        vol = get_current_volume(selected_city, game_timer, GAME_DAY_LENGTH)
        vol_text = small_font.render(f"Traffic: {vol} vph", True, (200, 200, 200))
        screen.blit(vol_text, vol_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 45)))

        # Active car count
        active_text = small_font.render(f"Active: {len(cars)}", True, (200, 200, 200))
        screen.blit(active_text, active_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 65)))

        # Completed cars count
        done_text = small_font.render(f"Delivered: {len(completed_stats)}", True, (200, 200, 200))
        screen.blit(done_text, done_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 85)))

        # City difficulty label
        _diff_labels = {"New York City": ("Normal", (200, 200, 200)),
                        "Los Angeles":   ("Hard",   (255, 100, 80)),
                        "Chicago":       ("Easy",   (80, 210, 120))}
        diff_label, diff_color = _diff_labels.get(selected_city, ("Normal", (200, 200, 200)))
        diff_text = small_font.render(f"Difficulty: {diff_label}", True, diff_color)
        screen.blit(diff_text, diff_text.get_rect(bottomright=(WINDOW_WIDTH - 10, WINDOW_HEIGHT - 105)))

        # Floating delta indicator (fades and rises after each score change)
        if delta_alpha > 0:
            sign = "+" if score_delta > 0 else ""
            delta_color = (80, 220, 80) if score_delta > 0 else (255, 80, 80)
            delta_surf = small_font.render(f"{sign}{score_delta:.2f}", True, delta_color)
            delta_surf.set_alpha(int(delta_alpha))
            base_y = WINDOW_HEIGHT - 25
            screen.blit(delta_surf, delta_surf.get_rect(
                bottomright=(WINDOW_WIDTH - 10, int(base_y + delta_y_offset))))

        # Draw pause controls
        draw_pause_controls(screen, start_button_rect, pause_button_rect, is_paused, is_started, small_font, mouse_pos)

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

        # Draw placed intersections (from the network)
        network.draw(screen)

        # Draw spawn/end markers
        draw_spawn_markers(screen, spawn_markers, marker_font, label_alpha)

        # Draw cars
        for car in cars:
            car.draw(screen)

        # Update and draw hint particles
        for p in hint_particles:
            p['y'] += p['vy'] * dt
            p['alpha'] = max(0.0, p['alpha'] - 255.0 * dt)
        hint_particles = [p for p in hint_particles if p['alpha'] > 0]
        for p in hint_particles:
            p_surf = marker_font.render(p['text'], True, p['color'])
            p_surf.set_alpha(int(p['alpha']))
            screen.blit(p_surf, p_surf.get_rect(center=(int(p['x']), int(p['y']))))

        # Draw palette and any intersection being dragged
        draw_palette(screen, PALETTE_TYPES, palette_start_x, palette_y,
                     PALETTE_SLOT_W, PALETTE_SLOT_H, small_font, mouse_pos, _palette_previews)
        if dragging_intersection:
            dragging_intersection.draw(screen)

        if game_ended:
            again_rect, menu_rect = draw_end_screen(
                screen, flow_rate, len(completed_stats),
                selected_city, selected_level, font, title_font, small_font, mouse_pos
            )
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if again_rect.collidepoint(pos):
                        return "REPLAY"
                    if menu_rect.collidepoint(pos):
                        return True

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
            result = run_game(screen, selected_city, selected_level)
            while result == "REPLAY":
                result = run_game(screen, selected_city, selected_level)
            if result:
                current_state = STATE_LEVEL_SELECT
            else:
                running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
