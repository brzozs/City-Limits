import pygame
import random
import math

CAR_COLORS = [
    (255, 220, 30),   # yellow
    (50, 160, 255),   # blue
    (255, 80, 60),    # red
    (80, 220, 100),   # green
    (255, 155, 30),   # orange
    (220, 100, 255),  # purple
    (255, 255, 255),  # white
]

CAR_W = 14
CAR_H = 8
CAR_SPEED = 80  # pixels per second


class Car:
    """A car that follows a pixel-coordinate path."""

    def __init__(self, path_pixels, speed=CAR_SPEED):
        self.path = path_pixels          # list of (x, y) waypoints
        self.path_index = 1              # index of next waypoint to reach
        self.x = float(path_pixels[0][0])
        self.y = float(path_pixels[0][1])
        self.speed = speed
        self.done = False
        self.color = random.choice(CAR_COLORS)
        self.angle = 0.0                 # degrees, 0 = right

        # Scoring metrics
        self.travel_time = 0.0           # total seconds this car has been alive
        self.idle_time = 0.0             # seconds spent stationary (speed = 0)
        self.path_length = self._calc_path_length()  # total pixel distance

    def _calc_path_length(self):
        total = 0.0
        for i in range(len(self.path) - 1):
            dx = self.path[i + 1][0] - self.path[i][0]
            dy = self.path[i + 1][1] - self.path[i][1]
            total += math.hypot(dx, dy)
        return total

    def update(self, dt):
        if self.done:
            return
        if self.path_index >= len(self.path):
            self.done = True
            return

        self.travel_time += dt

        tx, ty = self.path[self.path_index]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 0:
            self.angle = math.degrees(math.atan2(dy, dx))

        move = self.speed * dt
        if dist <= move:
            self.x, self.y = float(tx), float(ty)
            self.path_index += 1
        else:
            self.x += move * dx / dist
            self.y += move * dy / dist

        # Track idle time (car is blocked if it hasn't moved enough)
        if move == 0 or dist == 0:
            self.idle_time += dt

    def draw(self, screen):
        surf = pygame.Surface((CAR_W, CAR_H), pygame.SRCALPHA)

        # Body
        pygame.draw.rect(surf, self.color, (0, 0, CAR_W, CAR_H), border_radius=2)
        # Outline
        pygame.draw.rect(surf, (20, 20, 20), (0, 0, CAR_W, CAR_H), 1, border_radius=2)
        # Windshield (front-right of surface = front of car)
        pygame.draw.rect(surf, (180, 225, 255, 210), (CAR_W - 5, 1, 4, CAR_H - 2),
                         border_radius=1)

        rotated = pygame.transform.rotate(surf, -self.angle)
        screen.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))
