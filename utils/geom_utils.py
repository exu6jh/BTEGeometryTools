import re

# Parse coordinates as returned by Google Earth
def process_coords(cstr):
    cstr = cstr.strip()
    coord_re = re.search(r"(-?\d+\.\d+)[°,]?\s*(-?\d+\.\d+)°?", cstr)
    if coord_re:
        lat = float(coord_re.group(1))
        long = float(coord_re.group(2))
        return (lat, long, True)
    else:
        return (-1.0, -1.0, False)