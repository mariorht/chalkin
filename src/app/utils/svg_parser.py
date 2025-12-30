"""
SVG Parser utility to extract and simplify paths from SVG files.
"""
import xml.etree.ElementTree as ET
import re
import math
from typing import List, Tuple


def parse_svg_path_commands(path_d: str):
    """
    Parse SVG path d attribute and extract basic drawing commands.
    Returns list of (command, params) tuples.
    """
    # Simple regex to extract commands and their parameters
    command_pattern = re.compile(r'([MLCQZHVSATmlcqzhvsat])\s*([-\d.,\s]+)?')
    matches = command_pattern.findall(path_d)
    
    commands = []
    for cmd, params_str in matches:
        if params_str:
            # Split parameters by comma or space
            params = [float(x) for x in re.findall(r'[-\d.]+', params_str)]
        else:
            params = []
        commands.append((cmd, params))
    
    return commands


def svg_to_points(path_d: str, num_points: int = 300) -> List[Tuple[float, float]]:
    """
    Convert SVG path to a list of (x, y) points.
    Handles basic path commands: M, L, H, V, C, Q, Z
    """
    commands = parse_svg_path_commands(path_d)
    points = []
    current_x, current_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    
    for cmd, params in commands:
        if cmd == 'M':  # Move to (absolute)
            current_x, current_y = params[0], params[1]
            start_x, start_y = current_x, current_y
            points.append((current_x, current_y))
            
        elif cmd == 'm':  # Move to (relative)
            current_x += params[0]
            current_y += params[1]
            start_x, start_y = current_x, current_y
            points.append((current_x, current_y))
            
        elif cmd == 'L':  # Line to (absolute)
            for i in range(0, len(params), 2):
                current_x, current_y = params[i], params[i+1]
                points.append((current_x, current_y))
                
        elif cmd == 'l':  # Line to (relative)
            for i in range(0, len(params), 2):
                current_x += params[i]
                current_y += params[i+1]
                points.append((current_x, current_y))
                
        elif cmd == 'H':  # Horizontal line (absolute)
            for x in params:
                current_x = x
                points.append((current_x, current_y))
                
        elif cmd == 'h':  # Horizontal line (relative)
            for dx in params:
                current_x += dx
                points.append((current_x, current_y))
                
        elif cmd == 'V':  # Vertical line (absolute)
            for y in params:
                current_y = y
                points.append((current_x, current_y))
                
        elif cmd == 'v':  # Vertical line (relative)
            for dy in params:
                current_y += dy
                points.append((current_x, current_y))
                
        elif cmd in ['C', 'c']:  # Cubic bezier curve
            # Sample the curve with a few points
            params_len = len(params)
            for i in range(0, params_len, 6):
                if i + 5 < params_len:
                    if cmd == 'C':
                        cp1_x, cp1_y = params[i], params[i+1]
                        cp2_x, cp2_y = params[i+2], params[i+3]
                        end_x, end_y = params[i+4], params[i+5]
                    else:  # relative
                        cp1_x = current_x + params[i]
                        cp1_y = current_y + params[i+1]
                        cp2_x = current_x + params[i+2]
                        cp2_y = current_y + params[i+3]
                        end_x = current_x + params[i+4]
                        end_y = current_y + params[i+5]
                    
                    # Sample the bezier curve
                    for t in [0.25, 0.5, 0.75, 1.0]:
                        # Cubic bezier formula
                        t2 = t * t
                        t3 = t2 * t
                        mt = 1 - t
                        mt2 = mt * mt
                        mt3 = mt2 * mt
                        
                        x = mt3 * current_x + 3 * mt2 * t * cp1_x + 3 * mt * t2 * cp2_x + t3 * end_x
                        y = mt3 * current_y + 3 * mt2 * t * cp1_y + 3 * mt * t2 * cp2_y + t3 * end_y
                        points.append((x, y))
                    
                    current_x, current_y = end_x, end_y
                    
        elif cmd in ['Z', 'z']:  # Close path
            if points:
                points.append((start_x, start_y))
                current_x, current_y = start_x, start_y
    
    # Resample to get approximately num_points
    if len(points) > num_points:
        step = max(1, len(points) // num_points)
        points = points[::step]
    elif len(points) < num_points and len(points) > 1:
        # Interpolate to get more points
        interpolated = []
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            steps = num_points // len(points)
            for j in range(steps):
                t = j / steps
                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t
                interpolated.append((x, y))
        interpolated.append(points[-1])
        points = interpolated[:num_points]
    
    return points


def extract_svg_paths(svg_file_path: str) -> List[str]:
    """
    Extract all path 'd' attributes from an SVG file.
    Ignores embedded images (raster data).
    """
    try:
        tree = ET.parse(svg_file_path)
        root = tree.getroot()
        
        # Define namespaces
        namespaces = {
            'svg': 'http://www.w3.org/2000/svg',
            '': 'http://www.w3.org/2000/svg'
        }
        
        path_data = []
        
        # Try with namespace
        for ns_prefix in ['svg:', '']:
            # Find path elements
            paths = root.findall(f'.//{ns_prefix}path', namespaces if ns_prefix else {})
            for path in paths:
                d = path.get('d', '')
                if d and len(d) > 10:  # Skip very short paths
                    path_data.append(d)
            
            # Find polygon elements
            polygons = root.findall(f'.//{ns_prefix}polygon', namespaces if ns_prefix else {})
            for polygon in polygons:
                points = polygon.get('points', '')
                if points:
                    # Convert polygon points to path
                    coords = points.strip().split()
                    if len(coords) >= 2:
                        path_d = "M " + coords[0]
                        for coord in coords[1:]:
                            path_d += " L " + coord
                        path_d += " Z"
                        path_data.append(path_d)
            
            # Find polyline elements
            polylines = root.findall(f'.//{ns_prefix}polyline', namespaces if ns_prefix else {})
            for polyline in polylines:
                points = polyline.get('points', '')
                if points:
                    coords = points.strip().split()
                    if len(coords) >= 2:
                        path_d = "M " + coords[0]
                        for coord in coords[1:]:
                            path_d += " L " + coord
                        path_data.append(path_d)
            
            # Find circle elements
            circles = root.findall(f'.//{ns_prefix}circle', namespaces if ns_prefix else {})
            for circle in circles:
                cx = float(circle.get('cx', 0))
                cy = float(circle.get('cy', 0))
                r = float(circle.get('r', 0))
                if r > 0:
                    # Convert circle to path (approximation with 4 bezier curves)
                    k = 0.552284749831  # Magic number for circle approximation
                    path_d = f"M {cx} {cy-r} "
                    path_d += f"C {cx+r*k} {cy-r} {cx+r} {cy-r*k} {cx+r} {cy} "
                    path_d += f"C {cx+r} {cy+r*k} {cx+r*k} {cy+r} {cx} {cy+r} "
                    path_d += f"C {cx-r*k} {cy+r} {cx-r} {cy+r*k} {cx-r} {cy} "
                    path_d += f"C {cx-r} {cy-r*k} {cx-r*k} {cy-r} {cx} {cy-r} Z"
                    path_data.append(path_d)
            
            # Find rect elements
            rects = root.findall(f'.//{ns_prefix}rect', namespaces if ns_prefix else {})
            for rect in rects:
                x = float(rect.get('x', 0))
                y = float(rect.get('y', 0))
                w = float(rect.get('width', 0))
                h = float(rect.get('height', 0))
                if w > 0 and h > 0:
                    path_d = f"M {x} {y} L {x+w} {y} L {x+w} {y+h} L {x} {y+h} Z"
                    path_data.append(path_d)
            
            if path_data:
                break  # Found some paths, no need to try other namespace
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for p in path_data:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)
        
        return unique_paths
        
    except Exception as e:
        print(f"Error parsing SVG file: {e}")
        import traceback
        traceback.print_exc()
        return []


def scale_and_center_points(
    points: List[Tuple[float, float]], 
    center_lat: float, 
    center_lon: float, 
    scale_meters: float = 100
) -> List[Tuple[float, float]]:
    """
    Scale SVG points and convert to GPS coordinates centered at a location.
    
    Args:
        points: List of (x, y) tuples from SVG
        center_lat: Center latitude
        center_lon: Center longitude
        scale_meters: Approximate size of the shape in meters
    
    Returns:
        List of (lat, lon) tuples
    """
    if not points:
        return []
    
    # Find bounding box
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    width = max_x - min_x
    height = max_y - min_y
    
    if width == 0 or height == 0:
        return [(center_lat, center_lon)]
    
    max_dim = max(width, height)
    
    # Normalize to [-1, 1] range
    normalized = []
    for x, y in points:
        norm_x = (x - min_x - width/2) / max_dim * 2
        norm_y = (y - min_y - height/2) / max_dim * 2
        # Flip Y axis (SVG has Y increasing downward)
        normalized.append((norm_x, -norm_y))
    
    # Convert to lat/lon offsets
    # Rough approximation: 1 degree latitude ≈ 111km
    # 1 degree longitude ≈ 111km * cos(lat)
    meters_per_degree_lat = 111000
    meters_per_degree_lon = 111000 * math.cos(math.radians(center_lat))
    
    gps_points = []
    for norm_x, norm_y in normalized:
        # Scale normalized coordinates to meters
        offset_x_meters = norm_x * scale_meters / 2
        offset_y_meters = norm_y * scale_meters / 2
        
        # Convert to degrees
        lat = center_lat + (offset_y_meters / meters_per_degree_lat)
        lon = center_lon + (offset_x_meters / meters_per_degree_lon)
        
        gps_points.append((lat, lon))
    
    return gps_points


# Simplified Chalkin logo path - Hand holding shape (climbing hold)
# This represents a hand gripping a climbing hold - iconic for bouldering
CHALKIN_LOGO_SIMPLIFIED = """
M 50 10 
C 40 10 30 15 25 25
L 20 40
C 18 50 20 60 25 65
L 30 70
L 25 80
C 23 85 25 90 30 92
L 40 95
C 50 98 60 98 70 95
L 80 92
C 85 90 87 85 85 80
L 80 70
L 85 65
C 90 60 92 50 90 40
L 85 25
C 80 15 70 10 60 10
L 50 10
Z
M 45 35
C 40 35 35 40 35 45
C 35 50 40 55 45 55
C 50 55 55 50 55 45
C 55 40 50 35 45 35
Z
M 65 35
C 60 35 55 40 55 45
C 55 50 60 55 65 55
C 70 55 75 50 75 45
C 75 40 70 35 65 35
Z
M 50 60
L 45 65
L 55 65
L 50 60
Z
"""

# Alternative: Simple circle logo (for testing)
CHALKIN_LOGO_CIRCLE = """
M 50 10
C 30 10 10 30 10 50
C 10 70 30 90 50 90
C 70 90 90 70 90 50
C 90 30 70 10 50 10
Z
"""
