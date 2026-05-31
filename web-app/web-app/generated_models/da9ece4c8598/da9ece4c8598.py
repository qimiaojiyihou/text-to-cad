from build123d import *

def gen_step():
    size = 10.0
    
    with BuildPart() as part:
        with Locations((0, 0, size / 2)):
            Box(size, size, size)
    
    return part.part