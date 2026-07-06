import argparse, itertools, os, sys
import mcschematic, numpy
from utils.geom_utils import process_coords
from .line_tool_util import arr_grid, block_type_to_block_info, construct_line, print_line, read_geojson_lines, read_kml_lines, read_kmz_lines
from pathlib import Path
from PIL import Image
from terrapyconvert import from_geo
from tqdm import tqdm

class LineTool:
    def __init__(self):
        return
    
    def __call__(self, *inps, **argv):
        out, verbose = argv["out"], argv["verbose"]

        # Get lines to convert
        lines = []
        if inps[0]:
            for i in range(len(inps)):
                p = Path(inps[i])
                if not p.exists():
                    print(f"Was not able to find file with name \"{inps[1]}\".")
                    return
                if p.is_dir():
                    print(f"\"{inps[1]}\" is a directory, not a file.")
                    return
                
                if p.suffix == ".geojson":
                    print("Reading geojson file.")
                    with p.open() as f:
                        lines += read_geojson_lines(f, print_contents=verbose)
                elif p.suffix == ".kml":
                    print("Reading kml file.")
                    fname = os.fspath(p)
                    lines += read_kml_lines(fname, print_contents=verbose)
                elif p.suffix == ".kmz":
                    print("Reading kmz file.")
                    fname = os.fspath(p)
                    lines += read_kmz_lines(fname, print_contents=verbose)
                else:
                    print(f"Unsupported file suffix: {p.suffix}")
        else:
            line = []
            coord = 0
            line_spec_flag = True
            while line_spec_flag:
                print(f"Please enter the IRL coordinates of the {"first" if coord == 0 else "second"} point of your line. When you are done, leave the line empty.")
                inp = input()
                if inp.strip() == "":
                    if coord == 0:
                        line_spec_flag = False
                        break
                    else:
                        print("Cannot continue until coordinates of second point of line is specified.")
                else:
                    pcoord = process_coords(inp)
                    if pcoord[2]:
                        pcoord = (pcoord[0], pcoord[1])
                        print(f"Coordinate specified ({inp}) cleaned up and parsed as {pcoord}.")
                        mccoord = from_geo(*pcoord)
                        print(f"IRL coordinates {pcoord} translates to in-game coordinates {mccoord}")
                        line.append(mccoord)
                        if coord == 1:
                            print(f"Adding line {line}.")
                            lines.append(line)
                            line = []
                        coord = (coord + 1) % 2
                        print()
                    else:
                        print("Unable to understand coordinate, please try again.\n")
            print(f"Final lines:\n\t{"\n\t".join([print_line(line) for line in lines])}\n")

        if len(lines) == 0:
            print("No lines detected, exiting.")
            return
        
        # Get points
        line_points = []
        print("Converting lines into list of discretized points")
        for i in tqdm(range(len(lines))):
            line_points.append(construct_line(lines[i]))

        # Base point to paste schematic from
        base_point = numpy.floor(lines[0][0]).astype(int)
        # Determine size bounds
        xs = []
        zs = []
        for i in range(len(line_points)):
            for point in line_points[i]:
                xs.append(point[0])
                zs.append(point[1])
        min_x = numpy.floor(min(xs)).astype(int)
        max_x = numpy.ceil(max(xs)).astype(int)
        print(f"x ranges between {str(min_x)} and {str(max_x)}")
        min_z = numpy.floor(min(zs)).astype(int)
        max_z = numpy.ceil(max(zs)).astype(int)
        print(f"z ranges between {str(min_z)} and {str(max_z)}")

        # === For schem ===
        print("\nConverting discretized points into schematic")
        schem_array = numpy.zeros((max_x - min_x, max_z - min_z)).astype(int)
        print("Adding lines to schematic array")
        for i in tqdm(range(len(line_points))):
            for point in line_points[i]:
                schem_point = numpy.floor(point).astype(int) - numpy.array([min_x, min_z])
                half_point_index = numpy.floor(2 * (point - numpy.floor(point))).astype(int)
                block_quarter_index = 1 << (2 * half_point_index[0] + half_point_index[1])
                schem_array[schem_point[0]][schem_point[1]] |= block_quarter_index
        
        print("Converting schematic array to schematic")
        schem = mcschematic.MCSchematic()
        for x, z in tqdm(itertools.product(range(max_x - min_x), range(max_z - min_z)), total=(max_x - min_x) * (max_z - min_z)):
            schem_point_offset = (x, z) - (base_point - [min_x, min_z])
            block_type = int(schem_array[x][z])
            schem.setBlock((schem_point_offset[0], -1, schem_point_offset[1]), block_type_to_block_info[block_type])
        schem.save("output/linetool", out, mcschematic.Version.JE_1_21_5)
        print(f"Saved schematic to output/linetool/{out}.schem. Upload schematic to server, load schematic, TP to {lines[0][0]}, and paste")

        # === For image ===
        print("\nConverting discretized points into image")
        x_scale = 2 * (max_x - min_x)
        z_scale = 2 * (max_z - min_z)
        front = numpy.zeros((z_scale,x_scale))
        back = numpy.zeros((z_scale,x_scale)) + 64
        
        print("Adding lines to image array")
        for i in tqdm(range(len(line_points))):
            for point in line_points[i]:
                lower = point - numpy.array([min_x, min_z])
                front_index = numpy.floor(2 * lower).astype(int)
                back_index = numpy.floor(lower).astype(int)
                back[2*(back_index[1]):2*(back_index[1]+1), 2*(back_index[0]):2*(back_index[0]+1)] = 128
                front[(front_index[1]):(front_index[1]+1), (front_index[0]):(front_index[0]+1)] = 255
        arr = numpy.maximum(back,front)

        print("Adding grid lines to array")
        grid_arr = arr_grid(arr)

        print("Converting image array to image")
        Image.fromarray(grid_arr.astype(numpy.uint8)).convert("RGB").save(f"output/linetool/{out}.png")

        print(f"Saved image to output/linetool/{out}.png\n")