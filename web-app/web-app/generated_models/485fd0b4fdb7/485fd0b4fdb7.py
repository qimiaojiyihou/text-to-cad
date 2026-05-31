from build123d import *

def gen_step():
    length = 50.0
    width = 50.0
    height = 10.0
    hole_dia = 5.0
    hole_offset = 20.0

    with BuildPart() as part:
        with Locations((0, 0, height / 2)):
            Box(length, width, height)
        with Locations(
            ( hole_offset,  hole_offset, 0),
            (-hole_offset,  hole_offset, 0),
            ( hole_offset, -hole_offset, 0),
            (-hole_offset, -hole_offset, 0),
        ):
            Cylinder(radius=hole_dia / 2, height=height + 1, mode=Mode.SUBTRACT)
    return part.part