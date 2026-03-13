"""Grid-based intersection network and pathfinding."""

from collections import deque
from intersection import Intersection


class IntersectionNetwork:
    """Manages a grid of 4-way intersections and pathfinding between them."""
    
    def __init__(self, rows, cols, start_x, start_y, cell_size):
        """
        Initialize the intersection network.
        
        Args:
            rows: Number of rows in the grid
            cols: Number of columns in the grid
            start_x: Screen x coordinate of grid top-left
            start_y: Screen y coordinate of grid top-left
            cell_size: Size of each cell in pixels
        """
        self.rows = rows
        self.cols = cols
        self.start_x = start_x
        self.start_y = start_y
        self.cell_size = cell_size
        
        # Create the grid structure (all cells)
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]
        self.placed_intersections = {}  # {(row, col): Intersection}
    
    def add_intersection(self, intersection):
        """Add a placed intersection to the network."""
        if intersection.snapped and intersection.row is not None and intersection.col is not None:
            self.grid[intersection.row][intersection.col] = intersection
            self.placed_intersections[(intersection.row, intersection.col)] = intersection
            self._reconnect_neighbors()
    
    def _reconnect_neighbors(self):
        """Reconnect all intersections to their neighbors."""
        # Clear existing connections
        for intersection in self.placed_intersections.values():
            intersection.neighbors = {}
        
        # Add new connections
        for (row, col), intersection in self.placed_intersections.items():
            # Up
            if row > 0 and (row - 1, col) in self.placed_intersections:
                intersection.connect('up', self.placed_intersections[(row - 1, col)])
            
            # Down
            if row < self.rows - 1 and (row + 1, col) in self.placed_intersections:
                intersection.connect('down', self.placed_intersections[(row + 1, col)])
            
            # Left
            if col > 0 and (row, col - 1) in self.placed_intersections:
                intersection.connect('left', self.placed_intersections[(row, col - 1)])
            
            # Right
            if col < self.cols - 1 and (row, col + 1) in self.placed_intersections:
                intersection.connect('right', self.placed_intersections[(row, col + 1)])
    
    def get_intersection(self, row, col):
        """Get an intersection by grid position."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return None
    
    def get_all_intersections(self):
        """Get a flat list of all placed intersections."""
        return list(self.placed_intersections.values())
    
    def find_path(self, start_intersection, end_intersection):
        """
        Find shortest path between two intersections using BFS.
        
        Returns a list of Intersection objects from start to end.
        """
        if start_intersection is None or end_intersection is None:
            return []
        
        if start_intersection == end_intersection:
            return [start_intersection]
        
        queue = deque([(start_intersection, [start_intersection])])
        visited = {start_intersection}
        
        while queue:
            current, path = queue.popleft()
            
            # Check all 4 neighbors
            for direction in ['up', 'down', 'left', 'right']:
                neighbor = current.get_neighbor(direction)
                
                if neighbor and neighbor not in visited:
                    new_path = path + [neighbor]
                    
                    if neighbor == end_intersection:
                        return new_path
                    
                    visited.add(neighbor)
                    queue.append((neighbor, new_path))
        
        return []  # No path found
    
    def intersections_to_pixels(self, intersection_path):
        """
        Convert a list of intersections to pixel coordinates for cars to follow.
        
        Returns a list of (x, y) tuples.
        """
        if not intersection_path:
            return []
        
        pixel_path = []
        for intersection in intersection_path:
            pixel_path.append((intersection.x, intersection.y))
        
        return pixel_path
    
    def draw(self, screen, highlighted_intersection=None):
        """Draw all intersections in the network."""
        for intersection in self.get_all_intersections():
            is_highlighted = intersection == highlighted_intersection
            intersection.draw(screen, highlighted=is_highlighted)
