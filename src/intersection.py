import pygame

class Intersection:
    """Represents a 4-way intersection on the grid."""

    def __init__(self, row, col, x, y):
        """
        Initialize a 4-way intersection.
        
        Args:
            row: Grid row position (or None if not placed)
            col: Grid column position (or None if not placed)
            x: Screen x coordinate (center of intersection)
            y: Screen y coordinate (center of intersection)
        """
        self.row = row
        self.col = col
        self.x = x
        self.y = y
        self.neighbors = {}  # {'up': Intersection, 'down': Intersection, 'left': Intersection, 'right': Intersection}
        self.width = 30
        self.height = 30
        self.dragging = False
        self.snapped = False
        self.snapped_row = None
        self.snapped_col = None

    def draw(self, screen, highlighted=False):
        """Draw the 4-way intersection with all 4 road arms always visible."""
        # Draw road segments in all 4 directions (always)
        road_width = 12
        road_color = (100, 100, 100)
        
        # Up
        pygame.draw.line(screen, road_color,
                       (int(self.x), int(self.y) - 30),
                       (int(self.x), int(self.y)), road_width)
        
        # Down
        pygame.draw.line(screen, road_color,
                       (int(self.x), int(self.y)),
                       (int(self.x), int(self.y) + 30), road_width)
        
        # Left
        pygame.draw.line(screen, road_color,
                       (int(self.x) - 30, int(self.y)),
                       (int(self.x), int(self.y)), road_width)
        
        # Right
        pygame.draw.line(screen, road_color,
                       (int(self.x), int(self.y)),
                       (int(self.x) + 30, int(self.y)), road_width)
        
        # Draw the center junction circle
        center_color = (150, 200, 150) if highlighted else (120, 120, 120)
        pygame.draw.circle(screen, center_color, (int(self.x), int(self.y)), 10)
        pygame.draw.circle(screen, (200, 200, 200), (int(self.x), int(self.y)), 10, 2)

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
