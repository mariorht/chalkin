#!/usr/bin/env python3
"""
Test script to extract SVG paths and generate GPX files.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.svg_parser import (
    extract_svg_paths,
    svg_to_points,
    scale_and_center_points
)
from datetime import datetime, timedelta


def generate_test_gpx(points, filename="test.gpx"):
    """Generate a test GPX file."""
    start_time = datetime.utcnow()
    duration = 3600
    time_per_point = duration / len(points) if len(points) > 1 else duration
    
    gpx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Chalkin Test" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Chalkin Logo Test</name>
    <time>{start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}</time>
  </metadata>
  <trk>
    <name>Chalkin Logo</name>
    <type>RockClimbing</type>
    <trkseg>
'''
    
    for i, (lat, lon) in enumerate(points):
        point_time = start_time + timedelta(seconds=i * time_per_point)
        time_str = point_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        gpx_content += f'      <trkpt lat="{lat}" lon="{lon}">\n        <time>{time_str}</time>\n      </trkpt>\n'
    
    gpx_content += '''    </trkseg>
  </trk>
</gpx>'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(gpx_content)
    
    print(f"✓ Generated {filename}")
    return gpx_content


def test_simple_shape():
    """Test with a simple triangle."""
    print("\n=== Testing Simple Triangle ===")
    path_d = "M 50 10 L 90 90 L 10 90 Z"
    
    points = svg_to_points(path_d, num_points=100)
    print(f"Generated {len(points)} points from SVG path")
    
    # Madrid coordinates
    center_lat = 40.416775
    center_lon = -3.703790
    
    gps_points = scale_and_center_points(points, center_lat, center_lon, scale_meters=100)
    print(f"Converted to {len(gps_points)} GPS points")
    print(f"First point: ({gps_points[0][0]:.6f}, {gps_points[0][1]:.6f})")
    print(f"Last point: ({gps_points[-1][0]:.6f}, {gps_points[-1][1]:.6f})")
    
    generate_test_gpx(gps_points, "test_triangle.gpx")


def test_logo_shape():
    """Test with simplified Chalkin logo."""
    print("\n=== Testing Chalkin Logo ===")
    
    # Try to parse the real SVG file
    svg_path = "app/static/icons/logoChalkin_invertido_simple.svg"
    
    if os.path.exists(svg_path):
        print(f"Parsing SVG file: {svg_path}")
        paths = extract_svg_paths(svg_path)
        print(f"Found {len(paths)} path elements in SVG")
        
        if paths:
            # Try each path and combine them
            all_points = []
            for i, path_d in enumerate(paths):
                print(f"\nPath {i+1}: {path_d[:100]}..." if len(path_d) > 100 else f"\nPath {i+1}: {path_d}")
                try:
                    points = svg_to_points(path_d, num_points=500)
                    if points:
                        all_points.extend(points)
                        print(f"  ✓ Generated {len(points)} points")
                except Exception as e:
                    print(f"  ✗ Error parsing path: {e}")
            
            if all_points:
                print(f"\nTotal points from all paths: {len(all_points)}")
                
                # Madrid coordinates (example)
                center_lat = 43.546253
                center_lon = -5.870037
                
                gps_points = scale_and_center_points(all_points, center_lat, center_lon, scale_meters=50)
                print(f"Converted to {len(gps_points)} GPS points")
                print(f"First point: ({gps_points[0][0]:.6f}, {gps_points[0][1]:.6f})")
                print(f"Last point: ({gps_points[-1][0]:.6f}, {gps_points[-1][1]:.6f})")
                
                generate_test_gpx(gps_points, "test_logo.gpx")
                return
    
    # Fallback to simplified logo if file not found or no paths
    print("\nUsing fallback simplified logo")
    from app.utils.svg_parser import CHALKIN_LOGO_SIMPLIFIED
    
    points = svg_to_points(CHALKIN_LOGO_SIMPLIFIED, num_points=2000)
    print(f"Generated {len(points)} points from logo path")
    
    # Madrid coordinates (example)
    center_lat = 43.507508
    center_lon = -5.683314
    
    gps_points = scale_and_center_points(points, center_lat, center_lon, scale_meters=150)
    print(f"Converted to {len(gps_points)} GPS points")
    print(f"First point: ({gps_points[0][0]:.6f}, {gps_points[0][1]:.6f})")
    print(f"Last point: ({gps_points[-1][0]:.6f}, {gps_points[-1][1]:.6f})")
    
    generate_test_gpx(gps_points, "test_logo.gpx")


def main():
    print("Chalkin SVG to GPX Converter Test")
    print("=" * 50)
    
    test_simple_shape()
    test_logo_shape()
    
    print("\n" + "=" * 50)
    print("Test complete! Check the generated GPX files:")
    print("  - test_triangle.gpx")
    print("  - test_logo.gpx")
    print("\nYou can upload these to https://www.gpsvisualizer.com/map_input")
    print("or open them with a GPX viewer to see the shapes.")


if __name__ == "__main__":
    main()
