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

2. Circle literal:
    zone_name = (cx,cy,radius)
    - Defines a circular zone centered at (cx, cy) with radius "radius" (float).

3. Set operations on two zones (only two at a time):
    zone3 = zone1 U zone2    # union
    zone4 = zone1 I zone2    # intersection
    zone5 = zone1 - zone2    # difference (zone1 minus zone2)
    zone6 = zone1 ^ zone2    # symmetric difference

4. Comments and blank lines:
    - Anything after a '#' on a line is ignored.
    - Empty or whitespace-only lines are skipped.

Example Usage:
    code = '''
    zone1 = [(0,0),(10,0),(10,10),(0,10)]
    cir = (5,5,3)
    union_z = zone1 U cir
    '''
    zh = ZonesHandler(code)
    print(zh.get_zones())           # ['zone1','cir','union_z']
    print(zh.in_zone('cir',(7,5)))   # True

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

    Supported shape definitions:
        - Polygon: [(x1,y1),...]
        - Circle:  (cx,cy,r)

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

    def __init__(self, code_str: str, circle_resolution: int = 64):
        """
        Initialize the handler and parse DSL.

        Parameters:
            code_str (str): Multiline string with zone definitions and operations.
            circle_resolution (int): Number of segments used to approximate circles.
        Raises:
            ValueError: if syntax is invalid, coordinates malformed,
                        unknown zone referenced, or resulting zone empty.
        """
        self.zones = {}
        self._circle_res = circle_resolution

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
            # strip comments and whitespace
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue

            m = assign_re.match(line)
            if not m:
                raise ValueError(f"Syntax error on line {idx}: {line!r}")

            name, expr = m.groups()

            # Polygon literal
            if expr.startswith('['):
                coords = self._parse_coords(expr, name, idx)
                poly = Polygon(coords)
                if not poly.is_valid:
                    raise ValueError(f"Polygon '{name}' is invalid on line {idx}")
                self.zones[name] = poly

            # Circle literal
            elif expr.startswith('(') and expr.endswith(')'):
                circ = self._parse_circle(expr, name, idx)
                self.zones[name] = circ

            # Set operation
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

    def _parse_coords(self, expr: str, name: str, idx: int):
        """
        Safely parse a list/tuple literal of 2-tuples.
        """
        try:
            coords = ast.literal_eval(expr)
        except Exception as e:
            raise ValueError(f"Invalid coords for '{name}' on line {idx}: {e}")
        if (
            not isinstance(coords, (list, tuple)) or
            not all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in coords)
        ):
            raise ValueError(f"Coords for '{name}' must be list of (x,y) pairs on line {idx}")
        return coords

    def _parse_circle(self, expr: str, name: str, idx: int):
        """
        Parse a circle literal (cx,cy,r) and return a Polygon approximation.
        """
        try:
            vals = ast.literal_eval(expr)
        except Exception as e:
            raise ValueError(f"Invalid circle for '{name}' on line {idx}: {e}")
        if (
            not isinstance(vals, (list, tuple)) or
            len(vals) != 3 or
            not all(isinstance(v, (int, float)) for v in vals)
        ):
            raise ValueError(f"Circle '{name}' must be (cx,cy,radius) on line {idx}")
        cx, cy, r = vals
        if r <= 0:
            raise ValueError(f"Circle '{name}' must have positive radius on line {idx}")
        # buffer a point to approximate a circle
        circ = Point(cx, cy).buffer(r, resolution=self._circle_res)
        return circ

    def in_zone(self, zone_name: str, pt: tuple) -> bool:
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
    # Quick test & example
    code = '''
    zone1 = [(0,0),(10,0),(10,10),(0,10)]
    cir = (5,5,3)
    union_z = zone1 U cir
    '''
    zh = ZonesHandler(code)
    print("Zones:", zh.get_zones())
    print("Circle contains (7,5):", zh.in_zone('cir',(7,5)))
