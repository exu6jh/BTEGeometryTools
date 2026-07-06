import json, zipfile
import numpy
from fastkml import find_all, kml, LineString
from terrapyconvert import from_geo

# Read GeoJSON through simple JSON parsing
def read_geojson_lines(file, print_contents=False):
    lines = []
    data = json.load(file)
    if "features" in data and isinstance(data["features"], list):
        for feature in data["features"]:
            if "geometry" in feature:
                geometry = feature["geometry"]
                if "type" in geometry and geometry["type"] == "LineString" and "coordinates" in geometry and isinstance(geometry["coordinates"], list):
                    if print_contents:
                        print("Lines translated into Minecraft coordinates:")
                    prev_point = None
                    for point in geometry["coordinates"]:
                        point = from_geo(point[0], point[1])
                        if prev_point:
                            conv_line = [prev_point, point]
                            lines.append(conv_line)
                            if print_contents:
                                print_line(conv_line)
                        prev_point = point
        if print_contents:
            print()
    return lines

# Read KML using fastkml
def read_kml_lines(file, print_contents=False):
    lines = []
    with open(file, 'rb') as f:
        kml_doc = f.read()
        k = kml.KML.from_string(kml_doc)
        k_lines = list(find_all(k, of_type=LineString))
        if print_contents:
            print("Lines translated into Minecraft coordinates:")
        for line in k_lines:
            k_coords = line.kml_coordinates.coords
            prev_point = None
            for point in k_coords:
                point = from_geo(point[1], point[0])
                if prev_point:
                    conv_line = [prev_point, point]
                    lines.append(conv_line)
                    if print_contents:
                        print_line(conv_line)
                prev_point = point
        if print_contents:
            print()
    return lines

# Read KMZ using ZIP extraction and fastkml
def read_kmz_lines(file, print_contents=False):
    lines = []
    with zipfile.ZipFile(file, 'r') as f:
        kml_doc = f.open('doc.kml', 'r').read()
        k = kml.KML.from_string(kml_doc)
        k_lines = list(find_all(k, of_type=LineString))
        if print_contents:
            print("Lines translated into Minecraft coordinates:")
        for line in k_lines:
            k_coords = line.kml_coordinates.coords
            prev_point = None
            for point in k_coords:
                point = from_geo(point[1], point[0])
                if prev_point:
                    conv_line = [prev_point, point]
                    lines.append(conv_line)
                    if print_contents:
                        print_line(conv_line)
                prev_point = point
        if print_contents:
            print()
    return lines

# Take two points in a line, then construct a list of points
# (rounded to half-block centers) along the line
def construct_line(line):
    p1 = numpy.array(line[0])
    p2 = numpy.array(line[1])

    # For clarity
    x0 = p1[0]
    x1 = p2[0]
    z0 = p1[1]
    z1 = p2[1]

    # To simplify, we apply a canonical reversible transformation such that
    # dx, dz >= 0, and dz < dx.
    (dx, dz) = (x1 - x0, z1 - z0)

    x_flip = False
    if dx < 0:
        (x0, x1, dx) = (-x0, -x1, -dx)
        x_flip = True

    z_flip = False
    if dz < 0:
        (z0, z1, dz) = (-z0, -z1, -dz)
        z_flip = True

    xz_flip = False
    if dz > dx:
        (x0, z0, x1, z1, dx, dz) = (z0, x0, z1, x1, dz, dx)
        xz_flip = True

    # Actually get the points; the linspace is a bit weird but that's just my
    # preference on what I feel constitutes a half block being "in" a line.
    points = []
    for halfblock_x in numpy.linspace((numpy.floor(2 * x0 + 0.25) + 0.5) / 2, (numpy.ceil(2 * x1 - 0.25) - 0.5) / 2, numpy.ceil(2 * x1 - 0.25).astype(int) - numpy.floor(2 * x0 + 0.25).astype(int)):
        # Get z value on line
        linear_z = dz/dx * (halfblock_x - x0) + z0
        # Rounds z to the nearest half-block center
        halfblock_z = numpy.round(2 * linear_z - 0.5) / 2 + 0.25
        if xz_flip:
            (halfblock_x, halfblock_z) = (halfblock_z, halfblock_x)
        if z_flip:
            halfblock_z = -halfblock_z
        if x_flip:
            halfblock_x = -halfblock_x
        r_point = numpy.array([halfblock_x, halfblock_z])
        points.append(r_point)
    return points


# For schematic
# Index is sum of the value corresponding to each corner:
# 1: northwest corner
# 2: southwest corner
# 4: northeast corner
# 8: southeast corner
block_type_to_block_info = {
    0: "minecraft:air",
    1: "minecraft:prismarine_brick_stairs[facing=north,shape=outer_left]", # Northwest corner stair
    2: "minecraft:prismarine_brick_stairs[facing=south,shape=outer_right]", # Southwest corner stair
    3: "minecraft:prismarine_brick_stairs[facing=west]", # West stair
    4: "minecraft:prismarine_brick_stairs[facing=north,shape=outer_right]", # Northeast corner stair
    5: "minecraft:prismarine_brick_stairs[facing=north]", # North stair
    6: "minecraft:yellow_wool", # Diagonal northeast/southwest block
    7: "minecraft:prismarine_brick_stairs[facing=north,shape=inner_left]", # Stair minus southeast corner
    8: "minecraft:prismarine_brick_stairs[facing=south,shape=outer_left]", # Southeast corner
    9: "minecraft:red_wool", # Diagonal northwest/southeast corner
    10: "minecraft:prismarine_brick_stairs[facing=south]", # South stair
    11: "minecraft:prismarine_brick_stairs[facing=south,shape=inner_right]", # Stair minus northeast corner
    12: "minecraft:prismarine_brick_stairs[facing=east]", # East stair
    13: "minecraft:prismarine_brick_stairs[facing=north,shape=inner_right]", # Stair minus southwest corner
    14: "minecraft:prismarine_brick_stairs[facing=south,shape=inner_left]", # Stair minus northwest corner
    15: "minecraft:diamond_block", # Full block
}

# For image
# Take a numpy array of block heights, where each 2 x 2 block is assumed to be one block
# Then scale the array and add "gridlines" (regions of height = 0) in between
def arr_grid(arr,halfsize=2):
    blocksize = 2 * halfsize
    height = arr.shape[0] // 2
    width = arr.shape[1] // 2
    new_height = height * (blocksize + 1) + 1
    new_width = width * (blocksize + 1) + 1
    new_arr = numpy.zeros((new_height, new_width))
    for i in range(height):
        for j in range(width):
            new_arr[(blocksize+1)*i+1:(blocksize+1)*(i+1), (blocksize+1)*j+1:(blocksize+1)*(j+1)] = numpy.kron(arr[2*i:2*i+2, 2*j:2*j+2], numpy.ones((halfsize, halfsize)))
    return new_arr

# Pretty-print lines
def print_line(line):
    print(f"{line[0]} -> {line[1]}")