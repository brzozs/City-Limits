import pygame

class Intersection:
    """Represents a draggable intersection placeholder."""

    def __init__(self, x, y, sprite=None):
        self.x = x
        self.y = y
        self.sprite = sprite  # Will hold preset image/sprite
        self.width = 40
        self.height = 40
        self.dragging = False
        self.snapped = False
        self.snapped_row = None
        self.snapped_col = None

    def draw(self, screen):
        """Draw the intersection sprite."""
        if self.sprite:
            rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(self.sprite, rect)

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
            return True

        self.snapped = False
        return False
