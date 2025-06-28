# Author: Aman Rathore
# Contact: amanr.me | amanrathore9753 <at> gmail <dot> com
# Created on: Saturday, June 28, 2025 at 13:46
"""
zones_handling.py

ZonesHandler: parse and manage 2D "zones" defined in a small DSL string.

DSL Grammar:
1. Polygon literal:
    zone_name = [(x1,y1),(x2,y2),...,(xn,yn)]
    - List of 2-tuples defining a non-self-intersecting closed polygon.

2. Set operations on two zones (only two at a time):
    zone3 = zone1 U zone2    # union
    zone4 = zone1 I zone2    # intersection
    zone5 = zone1 - zone2    # difference (zone1 minus zone2)
    zone6 = zone1 ^ zone2    # symmetric difference

3. Comments and blank lines:
    - Anything after a '#' on a line is ignored.
    - Empty or whitespace-only lines are skipped.

Example Usage:
    code = '''
    zone1 = [(0,0),(10,0),(10,10),(0,10)]
    zone2 = [(5,5),(15,5),(15,15),(5,15)]
    union_z = zone1 U zone2
    '''
    zh = ZonesHandler(code)
    print(zh.get_zones())           # ['zone1','zone2','union_z']
    print(zh.in_zone('union_z',(7,7)))  # True

Dependencies:
    pip install shapely
"""

import re
import ast
import json
from shapely.geometry import Polygon, Point

class ZonesHandler:
    """
    Parse and manage 2D "zones" defined in a small DSL via a string.

    Supported set operations on two zones:
        - U  = union
        - I  = intersection
        - -  = difference
        - ^  = symmetric difference

    Methods:
        - in_zone(name, pt)      Check if point is inside or on border of zone.
        - get_zones()            Return list of all zone names.
        - get_area(name)         Return area of zone.
        - get_perimeter(name)    Return perimeter of zone.
        - get_bounds(name)       Return bounding box (minx, miny, maxx, maxy).
    """

    def __init__(self, code_str: str):
        """
        Initialize the handler and parse DSL.

        Parameters:
            code_str (str): Multiline string with zone definitions and operations.
        Raises:
            ValueError: if syntax is invalid, coordinates malformed,
                        unknown zone referenced, or resulting zone empty.
        """
        self.zones = {}

        # Map operation symbol to Shapely method
        op_map = {
            'U': lambda A, B: A.union(B),
            'I': lambda A, B: A.intersection(B),
            '-': lambda A, B: A.difference(B),
            '^': lambda A, B: A.symmetric_difference(B),
        }

        # Regex for assignment and set-operation expressions
        assign_re = re.compile(r'^(\w+)\s*=\s*(.+)$')
        op_re     = re.compile(r'^(\w+)\s*([UI\-\^])\s*(\w+)$')

        for idx, raw in enumerate(code_str.strip().splitlines(), 1):
            # Remove inline comments and surrounding whitespace
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue

            m = assign_re.match(line)
            if not m:
                raise ValueError(f"Syntax error on line {idx}: {line!r}")

            name, expr = m.groups()

            # Case 1: Literal polygon coords
            if expr.startswith('['):
                try:
                    coords = ast.literal_eval(expr)
                except Exception as e:
                    raise ValueError(f"Invalid coords for '{name}' on line {idx}: {e}")

                # Validate shape of coords
                if (
                    not isinstance(coords, (list, tuple)) or
                    not all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in coords)
                ):
                    raise ValueError(
                        f"Coords for '{name}' must be list of (x,y) pairs on line {idx}"
                    )

                poly = Polygon(coords)
                if not poly.is_valid:
                    raise ValueError(f"Polygon '{name}' is invalid (self-intersecting?) on line {idx}")
                self.zones[name] = poly

            # Case 2: Set operation between two existing zones
            else:
                m2 = op_re.match(expr)
                if not m2:
                    raise ValueError(f"Invalid expression for '{name}' on line {idx}: {expr!r}")

                left, op, right = m2.groups()
                if left not in self.zones:
                    raise ValueError(f"Unknown zone '{left}' referenced on line {idx}")
                if right not in self.zones:
                    raise ValueError(f"Unknown zone '{right}' referenced on line {idx}")

                result = op_map[op](self.zones[left], self.zones[right])
                if result.is_empty:
                    raise ValueError(f"Resulting zone '{name}' is empty on line {idx}")
                self.zones[name] = result

    def in_zone(self, zone_name: str, pt: tuple) -> bool:
        """
        Check if a point lies inside or on the border of a zone.

        Parameters:
            zone_name (str): Name of zone to test.
            pt (tuple): (x, y) coordinates of point.
        Returns:
            bool: True if point is within or on boundary.
        Raises:
            KeyError: if zone_name not defined.
        """
        if zone_name not in self.zones:
            raise KeyError(f"Zone '{zone_name}' not found")
        return self.zones[zone_name].covers(Point(pt))

    def get_zones(self) -> list:
        """
        Return list of all defined zone names (in order of definition).

        Returns:
            List[str]
        """
        return list(self.zones.keys())

    def get_area(self, zone_name: str) -> float:
        """
        Get the area of a zone.

        Parameters:
            zone_name (str)
        Returns:
            float: polygon area.
        Raises:
            KeyError: if zone_name not defined.
        """
        if zone_name not in self.zones:
            raise KeyError(f"Zone '{zone_name}' not found")
        return self.zones[zone_name].area

    def get_perimeter(self, zone_name: str) -> float:
        """
        Get the perimeter (boundary length) of a zone.

        Parameters:
            zone_name (str)
        Returns:
            float
        """
        if zone_name not in self.zones:
            raise KeyError(f"Zone '{zone_name}' not found")
        return self.zones[zone_name].length

    def get_bounds(self, zone_name: str) -> tuple:
        """
        Get axis-aligned bounding box of a zone.

        Parameters:
            zone_name (str)
        Returns:
            (minx, miny, maxx, maxy)
        """
        if zone_name not in self.zones:
            raise KeyError(f"Zone '{zone_name}' not found")
        return self.zones[zone_name].bounds

if __name__ == "__main__":
    code = """
    # a 5-point star (concave)
    star = [(5,9),(6,6),(9,6),(7,4),(8,1),(5,3),(2,1),(3,4),(1,6),(4,6)]

    # a larger convex “hexagon”
    hull = [(2,2),(8,2),(12,7),(8,12),(2,12),(-2,7)]

    # a “donut” ring = big square minus a smaller square hole
    outer = [(-1,-1),(13,-1),(13,13),(-1,13)]
    inner = [(4,4),(8,4),(8,8),(4,8)]
    ring = outer - inner

    # now do all set operations between star and hull
    union1     = star U hull
    intersect1 = star I hull
    diff1      = hull - star
    symdiff1   = star ^ hull

    # and combine the ring with the hull
    combo = ring U hull
    """


    zh = ZonesHandler(code)

    # List what you’ve got
    print("Defined zones:", zh.get_zones())

    # Inspect areas
    for name in zh.get_zones():
        print(f"{name:10s} area = {zh.get_area(name):7.2f}")

    # Check bounds of the final combo
    print("combo bounds:", zh.get_bounds("combo"))

    # Point-in-zone examples
    pts = [(5,5),(10,10),(0,0)]
    for pt in pts:
        inside = [z for z in zh.get_zones() if zh.in_zone(z, pt)]
        print(f"Point {pt} is in: {inside or ['none']}")
