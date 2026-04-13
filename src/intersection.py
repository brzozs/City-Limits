import pygame
from enum import Enum

class IntersectionType(Enum):
    T_INTERSECTION     = "T-Intersection"
    TRUMPET            = "Trumpet"
    Y_INTERSECTION     = "Y-Intersection"
    FOUR_WAY           = "4-Way"
    ROUNDABOUT         = "Roundabout"
    CLOVERLEAF         = "Cloverleaf"
    DIAMOND            = "Diamond"
    PARTIAL_CLOVERLEAF = "Partial Cloverleaf"

_ALL_ARMS = frozenset({'N', 'S', 'E', 'W'})
_THREE_ARM_TYPES = frozenset({
    IntersectionType.T_INTERSECTION,
    IntersectionType.TRUMPET,
    IntersectionType.Y_INTERSECTION,
})
# rotation index → which arm is missing
_MISSING_BY_ROTATION = {0: 'S', 1: 'W', 2: 'N', 3: 'E'}

class Intersection:
    """Represents a typed intersection on the grid."""

    def __init__(self, row, col, x, y, intersection_type=None):
        """
        Initialize a 4-way intersection.

        Args:
            row: Grid row position (or None if not placed)
            col: Grid column position (or None if not placed)
            x: Screen x coordinate (center of intersection)
            y: Screen y coordinate (center of intersection)
            intersection_type: IntersectionType enum value (default: FOUR_WAY)
        """
        self.row = row
        self.col = col
        self.x = x
        self.y = y
        self.intersection_type = intersection_type or IntersectionType.FOUR_WAY
        self.rotation = 0
        self.neighbors = {}  # {'up': Intersection, 'down': Intersection, 'left': Intersection, 'right': Intersection}
        self.width = 30
        self.height = 30
        self.dragging = False
        self.snapped = False
        self.snapped_row = None
        self.snapped_col = None

    def get_arms(self):
        """Return frozenset of active arm directions ('N','S','E','W')."""
        if self.intersection_type in _THREE_ARM_TYPES:
            missing = _MISSING_BY_ROTATION[self.rotation % 4]
            return _ALL_ARMS - {missing}
        return _ALL_ARMS

    def rotate(self):
        """Rotate 90° clockwise. Only has effect on 3-arm types."""
        if self.intersection_type in _THREE_ARM_TYPES:
            self.rotation = (self.rotation + 1) % 4

    def draw(self, screen, highlighted=False):
        """Draw intersection using type-specific visual."""
        cx, cy = int(self.x), int(self.y)
        road_color = (100, 100, 100)
        road_w = 12
        arm_len = 30
        center_color = (150, 200, 150) if highlighted else (120, 120, 120)
        outline_color = (200, 200, 200)

        arms = self.get_arms()
        arm_endpoints = {
            'N': (cx, cy - arm_len),
            'S': (cx, cy + arm_len),
            'E': (cx + arm_len, cy),
            'W': (cx - arm_len, cy),
        }
        for arm, endpoint in arm_endpoints.items():
            if arm in arms:
                pygame.draw.line(screen, road_color, (cx, cy), endpoint, road_w)

        t = self.intersection_type

        if t == IntersectionType.ROUNDABOUT:
            pygame.draw.circle(screen, center_color, (cx, cy), 10)
            pygame.draw.circle(screen, outline_color, (cx, cy), 10, 2)

        elif t == IntersectionType.CLOVERLEAF:
            pygame.draw.circle(screen, center_color, (cx, cy), 7)
            for dx, dy in [(-14, -14), (14, -14), (14, 14), (-14, 14)]:
                pygame.draw.circle(screen, road_color, (cx + dx, cy + dy), 7, 3)

        elif t == IntersectionType.PARTIAL_CLOVERLEAF:
            pygame.draw.circle(screen, center_color, (cx, cy), 7)
            for dx, dy in [(-14, -14), (14, 14)]:
                pygame.draw.circle(screen, road_color, (cx + dx, cy + dy), 7, 3)

        elif t == IntersectionType.DIAMOND:
            pygame.draw.circle(screen, center_color, (cx, cy), 5)
            pts = [(cx, cy - 11), (cx + 11, cy), (cx, cy + 11), (cx - 11, cy)]
            pygame.draw.polygon(screen, road_color, pts, 2)

        elif t == IntersectionType.TRUMPET:
            pygame.draw.circle(screen, center_color, (cx, cy), 7)
            pygame.draw.circle(screen, outline_color, (cx, cy), 7, 2)
            missing = _MISSING_BY_ROTATION[self.rotation % 4]
            offsets = {'S': (0, 16), 'N': (0, -16), 'E': (16, 0), 'W': (-16, 0)}
            ox, oy = offsets[missing]
            pygame.draw.circle(screen, road_color, (cx + ox, cy + oy), 8, 3)

        elif t == IntersectionType.Y_INTERSECTION:
            pygame.draw.circle(screen, center_color, (cx, cy), 7)
            pygame.draw.circle(screen, outline_color, (cx, cy), 7, 2)
            pygame.draw.line(screen, outline_color, (cx - 5, cy - 5), (cx + 5, cy + 5), 2)
            pygame.draw.line(screen, outline_color, (cx + 5, cy - 5), (cx - 5, cy + 5), 2)

        else:
            # T_INTERSECTION, FOUR_WAY
            pygame.draw.circle(screen, center_color, (cx, cy), 8)
            pygame.draw.circle(screen, outline_color, (cx, cy), 8, 2)

    def connect(self, direction, neighbor):
        """Connect this intersection to a neighbor in a given direction."""
        self.neighbors[direction] = neighbor

    def get_neighbor(self, direction):
        """Get the neighbor in a given direction."""
        return self.neighbors.get(direction)

    def is_clicked(self, mouse_pos):
        """Check if the intersection is clicked."""
        rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2,
                          self.width, self.height)
        return rect.collidepoint(mouse_pos)

    def update_position(self, mouse_pos):
        """Update position while dragging."""
        self.x = mouse_pos[0]
        self.y = mouse_pos[1]

    def snap_to_grid(self, start_x, start_y, cell_size, rows, cols):
        """Snap intersection to the nearest grid cell."""
        # Calculate which cell the intersection is over
        rel_x = self.x - start_x
        rel_y = self.y - start_y

        if rel_x < 0 or rel_y < 0:
            return False

        col = int(rel_x / cell_size)
        row = int(rel_y / cell_size)

        # Check if within grid bounds
        if 0 <= row < rows and 0 <= col < cols:
            # Snap to center of cell
            self.x = start_x + col * cell_size + cell_size // 2
            self.y = start_y + row * cell_size + cell_size // 2
            self.snapped = True
            self.snapped_row = row
            self.snapped_col = col
            self.row = row
            self.col = col
            return True

        self.snapped = False
        return False
