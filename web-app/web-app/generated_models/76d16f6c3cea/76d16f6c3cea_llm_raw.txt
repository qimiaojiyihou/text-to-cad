from build123d import *

def gen_step():
    outer_diameter = 70.0
    inner_diameter = 60.0
    length = 500.0
    hole_diameter = 10.0
    hole_edge_distance = 50.0
    hole_spacing = 100.0
    hole_count = 5
    
    outer_radius = outer_diameter / 2.0
    inner_radius = inner_diameter / 2.0
    hole_radius = hole_diameter / 2.0
    
    hole_z_positions = [hole_edge_distance + i * hole_spacing for i in range(hole_count)]
    
    with BuildPart() as part:
        with Locations((0.0, 0.0, length / 2.0)):
            Cylinder(radius=outer_radius, height=length)
            Cylinder(radius=inner_radius, height=length + 1.0, mode=Mode.SUBTRACT)
        
        hole_locations = [(outer_radius, 0.0, z) for z in hole_z_positions]
        
        with Locations(*hole_locations):
            Cylinder(radius=hole_radius, height=outer_diameter, rotation=Rotation((0.0, 90.0, 0.0)), mode=Mode.SUBTRACT)
    
    return part.part