#!/usr/bin/env python3
"""Add objects to Webots world files for object detection training.

Reads a .wbt world file and adds specified objects at random or specific positions.
Objects are added using EXTERNPROTO declarations for Webots built-in objects.

Usage:
    python3 add_world_objects.py --world world.wbt --objects buildings,cars,trees

The script modifies the .wbt file to include additional objects.
"""

import re
import random
import argparse
import os

OBJECT_TEMPLATES = {
    "building": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/buildings/protos/SimpleBuilding.proto"\n',
        'SimpleBuilding {{ translation {x} {y} 0 rotation 0 0 1 {rot} }}\n'
    ),
    "tall_building": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/buildings/protos/TallBuilding.proto"\n',
        'TallBuilding {{ translation {x} {y} 0 }}\n'
    ),
    "house": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/buildings/protos/SmallManor.proto"\n',
        'SmallManor {{ translation {x} {y} 0 rotation 0 0 1 {rot} }}\n'
    ),
    "tree": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/trees/protos/Pine.proto"\n',
        'Pine {{ translation {x} {y} 0 }}\n'
    ),
    "car": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/vehicles/protos/tesla/TeslaModel3Simple.proto"\n',
        'TeslaModel3Simple {{ translation {x} {y} 0.31 rotation 0 0 1 {rot} }}\n'
    ),
    "cone": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/traffic/protos/TrafficCone.proto"\n',
        'TrafficCone {{ translation {x} {y} 0 }}\n'
    ),
    "box": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/factory/containers/protos/CardboardBox.proto"\n',
        'CardboardBox {{ translation {x} {y} 0.3 }}\n'
    ),
    "bush": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/plants/protos/FlowerBush.proto"\n',
        'FlowerBush {{ translation {x} {y} 0 }}\n'
    ),
    "road": (
        'EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/road/protos/Road.proto"\n',
        'Road {{ translation {x} {y} 0.01 rotation 0 0 1 {rot} width 3 wayPoints [0 0 0, 50 0 0] appearance Pavement {{ type "black stone" }} }}\n'
    ),
}


def add_objects_to_world(world_path, objects_to_add, count=5, radius=50):
    with open(world_path, 'r') as f:
        content = f.read()

    existing_protos = set(re.findall(r'EXTERNPROTO.*?proto\)', content))
    nodes = []

    for obj_type in objects_to_add:
        if obj_type not in OBJECT_TEMPLATES:
            print(f"  Unknown object type: {obj_type}")
            continue

        proto_template, node_template = OBJECT_TEMPLATES[obj_type]
        if proto_template.strip() not in existing_protos:
            nodes.append(proto_template)

        obj_count = count
        for i in range(obj_count):
            x = random.uniform(-radius, radius)
            y = random.uniform(-radius, radius)
            rot = random.uniform(0, 6.2832)
            # Avoid origin (drone takeoff zone)
            if abs(x) < 5 and abs(y) < 5:
                x += 10 if x >= 0 else -10
                y += 10 if y >= 0 else -10
            nodes.append(node_template.format(x=x, y=y, rot=rot))

    # Insert nodes before the Mavic2Pro or last significant node
    insert_point = content.rfind("Mavic2Pro {")
    if insert_point < 0:
        insert_point = content.rfind("}") - 10

    new_content = content[:insert_point] + "".join(nodes) + "\n" + content[insert_point:]

    with open(world_path, 'w') as f:
        f.write(new_content)

    print(f"  Added {len(nodes)} objects to {world_path}")
    print(f"  Object types: {', '.join(objects_to_add)}")


def main():
    parser = argparse.ArgumentParser(description="Add objects to Webots world files")
    parser.add_argument("--world", default=None, help="Path to .wbt world file")
    parser.add_argument("--objects", default="building,tree,cone,box",
                        help="Comma-separated object types: building,house,car,cone,box,tree,bush")
    parser.add_argument("--count", type=int, default=5, help="Number of each object to add")
    parser.add_argument("--radius", type=float, default=50, help="Spawn radius from origin")
    args = parser.parse_args()

    world_path = args.world
    if not world_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        world_path = os.path.join(script_dir, "..", "webots", "worlds", "mavic2pro_px4.wbt")

    if not os.path.exists(world_path):
        print(f"World not found: {world_path}")
        return

    objects = [o.strip() for o in args.objects.split(",") if o.strip()]
    print(f"Adding objects to: {world_path}")
    add_objects_to_world(world_path, objects, args.count, args.radius)
    print("Done! Open the world in Webots to see the changes.")


if __name__ == "__main__":
    main()
