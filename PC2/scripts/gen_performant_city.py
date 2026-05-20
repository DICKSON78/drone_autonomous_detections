#!/usr/bin/env python3
"""Generate a performant Dodoma city SDF (~45 models, Fuel meshes for visuals)."""

import math, random
random.seed(42)

SDF_PATH = "/home/dickson/FYP/drone_autonomous/PC2/gazebo_worlds/dodoma/dodoma_tanzania.sdf"

HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<sdf version="1.9">
  <world name="dodoma_tanzania">

    <physics type="ode">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>250</real_time_update_rate>
      <gravity>0 0 -9.81</gravity>
    </physics>

    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>-6.1629</latitude_deg>
      <longitude_deg>35.7516</longitude_deg>
      <elevation>1120</elevation>
      <heading_deg>0</heading_deg>
    </spherical_coordinates>

    <scene>
      <grid>false</grid>
      <sky>
        <time>12.0</time>
        <clouds>
          <speed>3</speed>
          <humidity>0.4</humidity>
        </clouds>
      </sky>
      <ambient>0.5 0.5 0.5 1</ambient>
      <background>0.45 0.55 0.75 1</background>
      <shadows>true</shadows>
    </scene>

    <gui fullscreen="false">
      <plugin filename="MinimalScene" name="3D View">
        <gz-gui><title>3D View</title><property key="showTitleBar" type="bool">false</property><property key="state" type="string">docked</property></gz-gui>
        <engine>ogre2</engine><scene>scene</scene>
        <ambient_light>0.4 0.4 0.45</ambient_light><background_color>0.3 0.35 0.4</background_color>
        <camera_pose>-12 -12 15 0 0.6 0.785</camera_pose>
        <camera_clip><near>0.25</near><far>25000</far></camera_clip>
      </plugin>
      <plugin filename="EntityContextMenuPlugin" name="Entity context menu"><gz-gui><property key="state" type="string">floating</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
      <plugin filename="GzSceneManager" name="Scene Manager"><gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
      <plugin filename="InteractiveViewControl" name="Interactive view control"><gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
      <plugin filename="CameraTracking" name="Camera Tracking"><gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
      <plugin filename="SelectEntities" name="Select Entities"><gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
      <plugin filename="WorldControl" name="World Control"><gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
      <plugin filename="WorldStats" name="World Stats"><gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui></plugin>
    </gui>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 100 0 0 0</pose>
      <diffuse>1 0.95 0.9 1</diffuse>
      <direction>-0.3 0.1 -0.95</direction>
    </light>

    <!-- GROUND -->
    <model name="dodoma_ground">
      <static>true</static>
      <link name="ground">
        <collision name="collision">
          <geometry><plane><normal>0 0 1</normal><size>1500 1500</size></plane></geometry>
        </collision>
        <visual name="soil">
          <geometry><plane><normal>0 0 1</normal><size>1500 1500</size></plane></geometry>
          <material><ambient>0.55 0.45 0.35 1</ambient><diffuse>0.6 0.5 0.4 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ROAD NETWORK -->
    <model name="india_road"><pose>0 0 0.12 0 0 0</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>160 10 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>160 10 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="uhuru_street"><pose>0 0 0.12 0 0 0</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>10 160 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>10 160 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="jamhuri_street"><pose>-2.5 -2.5 0.12 0 0 0</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>100 8 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>100 8 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="azikiwe_street"><pose>2.5 -2.5 0.12 0 0 0</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>8 100 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>8 100 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="connector_1"><pose>35 35 0.12 0 0 0.785</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>18 8 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>18 8 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="connector_2"><pose>-35 35 0.12 0 0 -0.785</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>18 8 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>18 8 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="connector_3"><pose>35 -35 0.12 0 0 -0.785</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>18 8 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>18 8 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="connector_4"><pose>-35 -35 0.12 0 0 0.785</pose><static>true</static>
      <link name="road"><collision name="collision"><geometry><box><size>18 8 0.2</size></box></geometry></collision>
      <visual name="tarmac"><geometry><box><size>18 8 0.2</size></box></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>

    <model name="central_roundabout"><pose>0 0 0.12 0 0 0</pose><static>true</static>
      <link name="surface"><collision name="collision"><geometry><cylinder><radius>8</radius><length>0.2</length></cylinder></geometry></collision>
      <visual name="tarmac"><geometry><cylinder><radius>8</radius><length>0.2</length></cylinder></geometry>
      <material><ambient>0.18 0.18 0.2 1</ambient><diffuse>0.2 0.2 0.22 1</diffuse></material></visual></link></model>
"""

FOOTER = """  </world>
</sdf>
"""

def model_tag(name, uri, x, y, z=0, r=0, p=0, yaw=0, static=True):
    return f"""    <model name="{name}">
      <pose>{x} {y} {z} {r} {p} {yaw}</pose>
      <static>{"true" if static else "false"}</static>
      <include>
        <uri>{uri}</uri>
      </include>
    </model>"""

models = []
counter = {"tree": 0, "person": 0, "car": 0, "building": 0}

road_positions = []
for i in range(-70, 75, 10):
    road_positions.append((i, -45, 0))
    road_positions.append((i, 45, 0))
for i in range(-70, 75, 10):
    road_positions.append((-45, i, 1.57))
    road_positions.append((45, i, 1.57))
for i in range(-70, 75, 10):
    road_positions.append((i, -25, 0))
    road_positions.append((i, 25, 0))
    road_positions.append((-25, i, 1.57))
    road_positions.append((25, i, 1.57))

def dist(x, y):
    return math.hypot(x, y)

# ---- KEY BUILDINGS (Fuel mesh) ----
buildings = [
    ("office_building_1", "office_building", 30, -30),
    ("apartment_1", "apartment", -30, 30),
    ("apartment_2", "chapulina_apartment", -30, -30),
    ("bunge_tanzania", "post_office", 0, 40),
    ("central_hospital", "hospital", 0, -80),
    ("bank_building", "office_building", 55, -55),
    ("shop_center", "apartment", 55, 55),
    ("mall_complex", "office_building", -55, -55),
    ("house_dodoma_1", "apartment", -55, 0),
    ("house_dodoma_2", "apartment", 0, -55),
    ("residential_1", "chapulina_apartment", 55, 0),
    ("residential_2", "chapulina_apartment", 0, 55),
    ("govt_building_1", "post_office", -55, 55),
]
for name, uri, x, y in buildings:
    counter["building"] += 1
    models.append(model_tag(name, uri, x, y))

# ---- TREES (Fuel mesh: oak_tree, pine_tree) - ~12 along roads ----
for i, (x, y, yaw) in enumerate(road_positions):
    if i % 8 != 0:
        continue
    ox = 3.0 if abs(y) > 20 else -3.0
    oy = 3.0 if abs(x) > 20 else -3.0
    tx = x + (ox if abs(yaw - 1.57) > 0.5 else 0)
    ty = y + (oy if abs(yaw - 1.57) < 0.5 else 0)
    if dist(tx, ty) < 15:
        continue
    if abs(tx) < 20 and abs(ty) < 20:
        continue
    tree_type = random.choice(["oak_tree", "pine_tree"])
    counter["tree"] += 1
    models.append(model_tag(f"street_tree_{counter['tree']}", tree_type, tx, ty))

# ---- PEOPLE near buildings & intersections - 8 total ----
person_positions = [
    (18, 18), (22, -18), (-18, 22), (-22, -20),
    (35, 35), (35, -35), (-35, 35), (-35, -35),
]
for px, py in person_positions:
    counter["person"] += 1
    models.append(model_tag(f"person_{counter['person']}", "person", px, py))

# ---- CARS along roads - 8 total ----
car_positions = [
    (30, -48, 0), (30, -42, 0), (-30, -48, 0),
    (48, -30, 1.57), (48, 30, 1.57), (-48, -30, 1.57),
    (30, 48, 0), (-30, 48, 0),
]
for cx, cy, cyaw in car_positions:
    counter["car"] += 1
    models.append(model_tag(f"street_car_{counter['car']}", "prius_hybrid", cx, cy, yaw=cyaw))

# ---- Write final SDF ----
models_block = "\n".join(models)

base_count = len([l for l in HEADER.split("\n") if "<model" in l])
added_count = len([l for l in models_block.split("\n") if "<model" in l])
total_count = base_count + added_count

sdf = HEADER + "\n" + models_block + "\n\n" + FOOTER

with open(SDF_PATH, "w") as f:
    f.write(sdf)

print("=== Performant City Generation Complete ===")
print(f"  Base models (ground + roads): {base_count}")
print(f"  Fuel mesh models added: {added_count}")
print(f"  Total models: {total_count}")
print(f"  Breakdown:")
for k, v in sorted(counter.items()):
    print(f"    {k}: {v}")
print(f"  SDF lines: {len(sdf.split(chr(10)))}")
