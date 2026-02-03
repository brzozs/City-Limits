class Grid:
    """Represents the grid for the game."""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def display(self):
        """Display the grid."""
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                row += "[ ]"
            print(row)
