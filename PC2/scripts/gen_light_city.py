#!/usr/bin/env python3
"""Generate a lightweight Dodoma city SDF for drone simulation.
Uses Fuel mesh models for key buildings, inline geometry for the rest."""

import re, math
SDF_PATH = "/home/dickson/FYP/drone_autonomous/PC2/gazebo_worlds/dodoma/dodoma_tanzania.sdf"

with open(SDF_PATH) as f:
    base = f.read()
base = base.replace('<world name="dodoma_city_realistic">', '<world name="dodoma_tanzania">')

world_end = "</world>"
idx = base.rfind(world_end)
header = base[:idx]
footer = base[idx:]

# -- Insert GUI config after </scene> --
gui_block = """    <!-- GUI CONFIG - Camera follows x500_0 -->
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
"""
scene_end = header.rfind("</scene>")
if scene_end != -1:
    eol = header.find("\n", scene_end)
    header = header[:eol+1] + "\n" + gui_block + header[eol+1:]

# -- Replace inline buildings with Fuel mesh models --
def replace_block(text, model_name, new_block):
    start = text.find(f'<model name="{model_name}"')
    if start == -1: return text
    depth = 0
    for i in range(start, len(text)):
        if text[i:i+7] in ('<model ', '<model>'): depth += 1
        elif text[i:i+8] == '</model>':
            depth -= 1
            if depth == 0: return text[:start] + new_block + text[i+8:]
    return text

header = replace_block(header, "office_building_1", f"""    <model name="office_building_1"><pose>30 -30 0 0 0 0</pose><static>true</static><include><uri>office_building</uri></include></model>\n""")
header = replace_block(header, "apartment_1", f"""    <model name="apartment_1"><pose>-30 30 0 0 0 0</pose><static>true</static><include><uri>apartment</uri></include></model>\n""")
header = replace_block(header, "apartment_2", f"""    <model name="apartment_2"><pose>-30 -30 0 0 0 0</pose><static>true</static><include><uri>chapulina_apartment</uri></include></model>\n""")
header = replace_block(header, "bunge_tanzania", f"""    <model name="bunge_tanzania"><pose>0 40 0 0 0 0</pose><static>true</static><include><uri>post_office</uri></include></model>\n""")

# -- Add limited obstacle models (inline geometry for performance) --
models = []
def sphere_marker(name, x, y, z, radius, color):
    return f"""    <model name="{name}">
      <pose>{x} {y} {z} 0 0 0</pose>
      <static>true</static>
      <link name="body">
        <visual name="visual"><geometry><sphere><radius>{radius}</radius></sphere></geometry>
          <material><ambient>{color}</ambient><diffuse>{color}</diffuse></material>
        </visual>
        <collision name="col"><geometry><sphere><radius>{radius}</radius></sphere></geometry></collision>
      </link>
    </model>"""

def cylinder_pole(name, x, y, h, r, color):
    return f"""    <model name="{name}">
      <pose>{x} {y} 0 0 0 0</pose>
      <static>true</static>
      <link name="body">
        <visual name="visual"><geometry><cylinder><radius>{r}</radius><length>{h}</length></cylinder></geometry>
          <material><ambient>{color}</ambient><diffuse>{color}</diffuse></material>
        </visual>
        <collision name="col"><geometry><cylinder><radius>{r}</radius><length>{h}</length></cylinder></geometry></collision>
      </link>
    </model>"""

def box(name, x, y, sx, sy, sz, color, z=0):
    return f"""    <model name="{name}">
      <pose>{x} {y} {z} 0 0 0</pose>
      <static>true</static>
      <link name="body">
        <visual name="visual"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
          <material><ambient>{color}</ambient><diffuse>{color}</diffuse></material>
        </visual>
        <collision name="col"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision>
      </link>
    </model>"""

# Street trees (cylinder trunk + sphere canopy) - 12 total
for i, (x, y) in enumerate([
    (20, -50), (30, -50), (-20, -50), (-30, -50),
    (20, 50), (-20, 50), (-30, 50),
    (50, -20), (50, 20),
    (-50, -20), (-50, 20),
][:8]):
    models.append(f"""    <model name="tree_{i+1}">
      <pose>{x} {y} 0 0 0 0</pose>
      <static>true</static>
      <link name="trunk">
        <visual name="trunk_v"><geometry><cylinder><radius>0.15</radius><length>2.5</length></cylinder></geometry>
          <material><ambient>0.35 0.25 0.15 1</ambient><diffuse>0.4 0.3 0.2 1</diffuse></material>
        </visual>
         <visual name="canopy"><pose>0 0 2.8 0 0 0</pose><geometry><sphere><radius>1.8</radius></sphere></geometry>
          <material><ambient>0.15 0.5 0.1 1</ambient><diffuse>0.2 0.55 0.15 1</diffuse></material>
        </visual>
        <collision name="col"><geometry><cylinder><radius>0.15</radius><length>2.5</length></cylinder></geometry></collision>
      </link>
    </model>""")

# Cars (inline boxes) - 5 total
for i, (x, y, yaw) in enumerate([
    (30, -48, 0), (-30, -48, 0), (48, 30, 1.57), (30, 48, 0), (-48, 30, 1.57),
]):
    models.append(f"""    <model name="car_{i+1}">
      <pose>{x} {y} 0.15 0 0 {yaw}</pose>
      <static>true</static>
      <link name="body">
        <visual name="body_v"><geometry><box><size>1.8 0.9 0.5</size></box></geometry>
          <material><ambient>0.1 0.3 0.6 1</ambient><diffuse>0.15 0.35 0.65 1</diffuse></material>
        </visual>
        <visual name="roof"><pose>0 0 0.4 0 0 0</pose><geometry><box><size>1.2 0.8 0.25</size></box></geometry>
          <material><ambient>0.3 0.55 0.8 0.5</ambient><diffuse>0.35 0.6 0.85 0.5</diffuse></material>
        </visual>
        <collision name="col"><geometry><box><size>1.8 0.9 0.5</size></box></geometry></collision>
      </link>
    </model>""")

# People (small cylinders + sphere heads) - 8 total  
for i, (x, y) in enumerate([
    (18, 18), (22, -18), (-18, 22), (-22, -20),
    (35, 35), (-35, -35),
]):
    models.append(f"""    <model name="person_{i+1}">
      <pose>{x} {y} 0 0 0 0</pose>
      <static>true</static>
      <link name="body">
        <visual name="torso"><geometry><cylinder><radius>0.15</radius><length>0.8</length></cylinder></geometry>
          <material><ambient>0.8 0.6 0.4 1</ambient><diffuse>0.85 0.65 0.45 1</diffuse></material>
        </visual>
        <visual name="head"><pose>0 0 0.55 0 0 0</pose><geometry><sphere><radius>0.12</radius></sphere></geometry>
          <material><ambient>0.9 0.75 0.6 1</ambient><diffuse>0.95 0.8 0.65 1</diffuse></material>
        </visual>
        <collision name="col"><geometry><cylinder><radius>0.15</radius><length>0.8</length></cylinder></geometry></collision>
      </link>
    </model>""")

# Poles (tall cylinders) - 6 total
for i, (x, y) in enumerate([
    (25, -50), (-25, -50), (50, -25), (50, 25),
]):
    models.append(cylinder_pole(f"pole_{i+1}", x, y, 4, 0.1, "0.3 0.3 0.3 1"))

# Barriers (long boxes) - 4 total
for i, (x, y, yaw) in enumerate([(8, -48, 0), (48, 8, 1.57), (-8, 48, 0), (-48, -8, 1.57)]):
    models.append(box(f"barrier_{i+1}", x, y, 2, 0.4, 0.5, "1 0.7 0.1 1", 0.25))

# Animals (small spheres) - 4 total
for i, (x, y) in enumerate([(25, 10), (30, 12), (-10, 25), (40, 40)]):
    models.append(sphere_marker(f"animal_{i+1}", x, y, 0.3, 0.3, "0.6 0.4 0.2 1"))

# Lamps (thin cylinder + sphere top) - 6 total
for i, (x, y) in enumerate([(0, -50), (15, -50), (0, 50), (50, 0)]):
    models.append(f"""    <model name="lamp_{i+1}">
      <pose>{x} {y} 0 0 0 0</pose>
      <static>true</static>
      <link name="post">
        <visual name="post_v"><geometry><cylinder><radius>0.05</radius><length>2.5</length></cylinder></geometry>
          <material><ambient>0.2 0.2 0.2 1</ambient><diffuse>0.25 0.25 0.25 1</diffuse></material>
        </visual>
        <visual name="lamp_top"><pose>0 0 2.5 0 0 0</pose><geometry><sphere><radius>0.15</radius></sphere></geometry>
          <material><ambient>1 0.9 0.6 1</ambient><diffuse>1 0.95 0.7 1</diffuse></material>
        </visual>
        <collision name="col"><geometry><cylinder><radius>0.05</radius><length>2.5</length></cylinder></geometry></collision>
      </link>
    </model>""")

# Hospital (Fuel mesh - one extra building)
models.append(f"""    <model name="central_hospital"><pose>0 -80 0 0 0 0</pose><static>true</static><include><uri>hospital</uri></include></model>""")

# -- Write final SDF --
models_block = "\n".join(models)
footer_clean = footer.rstrip() + "\n"

base_model_count = len(re.findall(r'<model ', header))
total_count = base_model_count + len(re.findall(r'<model ', models_block))
mesh_include_count = models_block.count("<include>") + header.count("<include>")

sdf = header + "\n" + models_block + "\n\n" + footer_clean
with open(SDF_PATH, "w") as f:
    f.write(sdf)

print(f"Base models: {base_model_count}")
print(f"Added obstacles: {len(re.findall(r'<model ', models_block))}")
print(f"Total models: {total_count}")
print(f"Mesh includes: {mesh_include_count}")
print(f"Lines: {len(sdf.split(chr(10)))}")
