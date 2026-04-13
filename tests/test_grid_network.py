import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pygame
pygame.init()

from intersection import Intersection, IntersectionType
from grid_network import IntersectionNetwork


def _place(network, row, col, itype=IntersectionType.FOUR_WAY, rotation=0):
    cell_size = network.cell_size
    x = network.start_x + col * cell_size + cell_size // 2
    y = network.start_y + row * cell_size + cell_size // 2
    i = Intersection(row, col, x, y, intersection_type=itype)
    i.rotation = rotation
    i.snapped = True
    network.add_intersection(i)
    return i


def test_two_four_way_intersections_connect():
    net = IntersectionNetwork(2, 2, 0, 0, 150)
    a = _place(net, 0, 0)
    b = _place(net, 0, 1)
    assert b in a.neighbors.values(), "4-way next to 4-way should connect"


def test_t_intersection_missing_arm_blocks_connection():
    net = IntersectionNetwork(2, 2, 0, 0, 150)
    # rotation=0 → missing S → no down connection
    a = _place(net, 0, 0, IntersectionType.T_INTERSECTION, rotation=0)
    b = _place(net, 1, 0)
    assert b not in a.neighbors.values(), "T missing S should not connect downward"


def test_t_intersection_present_arm_connects():
    net = IntersectionNetwork(2, 2, 0, 0, 150)
    # rotation=0 → arms N,E,W → east arm present → connects right
    a = _place(net, 0, 0, IntersectionType.T_INTERSECTION, rotation=0)
    b = _place(net, 0, 1)
    assert b in a.neighbors.values(), "T with E arm should connect rightward"


def test_two_t_intersections_both_need_matching_arm():
    net = IntersectionNetwork(2, 2, 0, 0, 150)
    # a rot=0 → missing S; b rot=2 → missing N → neither faces the other
    a = _place(net, 0, 0, IntersectionType.T_INTERSECTION, rotation=0)
    b = _place(net, 1, 0, IntersectionType.T_INTERSECTION, rotation=2)
    assert b not in a.neighbors.values()
    assert a not in b.neighbors.values()


def test_remove_intersection_tears_down_connection():
    net = IntersectionNetwork(2, 2, 0, 0, 150)
    a = _place(net, 0, 0)
    b = _place(net, 0, 1)
    assert b in a.neighbors.values()
    net.remove_intersection(b)
    assert b not in a.neighbors.values()


def test_remove_intersection_clears_from_network():
    net = IntersectionNetwork(2, 2, 0, 0, 150)
    a = _place(net, 0, 0)
    net.remove_intersection(a)
    assert (0, 0) not in net.placed_intersections
    assert net.grid[0][0] is None
