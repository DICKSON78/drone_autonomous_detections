#!/usr/bin/env python3
"""Generate a clean Dodoma city SDF with performance-optimized model count."""

import re, math, random
random.seed(42)

SDF_PATH = "/home/dickson/FYP/drone_autonomous/PC2/gazebo_worlds/dodoma/dodoma_tanzania.sdf"
MODEL_DIR = "/home/dickson/FYP/drone_autonomous/PC2/gazebo_models/dodoma"

# ---------------------------------------------------------------------------
# 1. Read base SDF (everything before </world>)
# ---------------------------------------------------------------------------
with open(SDF_PATH) as f:
    base = f.read()

# Normalize world name to what PX4 expects
base = base.replace('<world name="dodoma_city_realistic">', '<world name="dodoma_tanzania">')

# ---------------------------------------------------------------------------
# 2b. Replace inline building blocks with Fuel mesh-based models
# ---------------------------------------------------------------------------
def replace_model_block(text, model_name, new_block):
    """Replace a model block in the SDF text by finding start/end tags."""
    start_marker = f'<model name="{model_name}"'
    start = text.find(start_marker)
    if start == -1:
        print(f"  WARNING: Model '{model_name}' not found")
        return text
    # Find the matching </model>
    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i:i+7] == '<model ' or text[i:i+7] == '<model>':
            depth += 1
        elif text[i:i+8] == '</model>':
            depth -= 1
            if depth == 0:
                end = i + 8
                break
    if end == start:
        print(f"  WARNING: Could not find closing tag for '{model_name}'")
        return text
    return text[:start] + new_block + text[end:]

# Replace inline office_building_1 with office_building Fuel model
office_replace = f"""    <model name="office_building_1">
      <pose>30 -30 0 0 0 0</pose>
      <static>true</static>
      <include>
        <uri>office_building</uri>
      </include>
    </model>
"""
base = replace_model_block(base, "office_building_1", office_replace)

# Replace inline apartment_1 and apartment_2 with apartment Fuel model
apt1_replace = f"""    <model name="apartment_1">
      <pose>-30 30 0 0 0 0</pose>
      <static>true</static>
      <include>
        <uri>apartment</uri>
      </include>
    </model>
"""
base = replace_model_block(base, "apartment_1", apt1_replace)

apt2_replace = f"""    <model name="apartment_2">
      <pose>-30 -30 0 0 0 0</pose>
      <static>true</static>
      <include>
        <uri>chapulina_apartment</uri>
      </include>
    </model>
"""
base = replace_model_block(base, "apartment_2", apt2_replace)

# Replace inline bunge_tanzania with post_office Fuel model
bunge_replace = f"""    <model name="bunge_tanzania">
      <pose>0 40 0 0 0 0</pose>
      <static>true</static>
      <include>
        <uri>post_office</uri>
      </include>
    </model>
"""
base = replace_model_block(base, "bunge_tanzania", bunge_replace)

# bank_building and govt_building_1: keep inline (no suitable Fuel model available)

print("  Building replacements done")

# Split at the closing </world> tag
world_end_marker = "</world>"
idx = base.rfind(world_end_marker)
if idx == -1:
    raise RuntimeError("Cannot find </world> in SDF")

header = base[:idx]  # everything before </world>
footer = base[idx:]   # </world>\n</sdf>

# ---------------------------------------------------------------------------
# 2. Insert GUI config after scene/light section
# ---------------------------------------------------------------------------
gui_block = """    <!-- ============================================================ -->
    <!-- GUI CONFIG - Camera tracking on x500_0 drone                -->
    <!-- ============================================================ -->
    <gui fullscreen="false">
      <plugin filename="MinimalScene" name="3D View">
        <gz-gui>
          <title>3D View</title>
          <property key="showTitleBar" type="bool">false</property>
          <property key="state" type="string">docked</property>
        </gz-gui>
        <engine>ogre2</engine>
        <scene>scene</scene>
        <ambient_light>0.4 0.4 0.45</ambient_light>
        <background_color>0.3 0.35 0.4</background_color>
        <camera_pose>-12 -12 15 0 0.6 0.785</camera_pose>
        <camera_clip><near>0.25</near><far>25000</far></camera_clip>
      </plugin>
      <plugin filename="EntityContextMenuPlugin" name="Entity context menu">
        <gz-gui><property key="state" type="string">floating</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
      <plugin filename="GzSceneManager" name="Scene Manager">
        <gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
      <plugin filename="InteractiveViewControl" name="Interactive view control">
        <gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
      <plugin filename="CameraTracking" name="Camera Tracking">
        <gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
      <plugin filename="SelectEntities" name="Select Entities">
        <gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
      <plugin filename="WorldControl" name="World Control">
        <gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
      <plugin filename="WorldStats" name="World Stats">
        <gz-gui><property key="resizable" type="bool">false</property><property key="width" type="double">5</property><property key="height" type="double">5</property><property key="state" type="string">floating</property><property key="showTitleBar" type="bool">false</property></gz-gui>
      </plugin>
    </gui>

"""

# Insert after the last </scene> or light section
insert_after = "</scene>"
# Find the LAST occurrence of </scene> before the world_end_marker
scene_end = header.rfind(insert_after)
if scene_end != -1:
    # Find the end of that line
    eol = header.find("\n", scene_end)
    if eol != -1:
        header = header[:eol+1] + "\n" + gui_block + header[eol+1:]

# ---------------------------------------------------------------------------
# 3. Generate model blocks at 1/5 density
# ---------------------------------------------------------------------------
# Road boundaries: roads extend roughly -80 to 80 in x and y
# We'll place models along roads, in parks, and near landmarks

def model_tag(name, include_uri, x, y, z=0, r=0, p=0, yaw=0, static=True):
    return f"""    <model name="{name}">
      <pose>{x} {y} {z} {r} {p} {yaw}</pose>
      <static>{"true" if static else "false"}</static>
      <include>
        <uri>{include_uri}</uri>
      </include>
    </model>"""

models = []
counter = {"tree": 0, "pole": 0, "person": 0, "car": 0, "animal": 0,
           "barrier": 0, "cone": 0, "bush": 0, "lamp": 0, "flower": 0}

# Road-aligned positions (every 10m along roads)
road_positions = []
# Main axis roads
for i in range(-70, 75, 10):  # India Road / Jamhuri (x axis)
    road_positions.append((i, -45, 0))
    road_positions.append((i, 45, 0))
for i in range(-70, 75, 10):  # Uhuru / Azikiwe (y axis)
    road_positions.append((-45, i, 1.57))
    road_positions.append((45, i, 1.57))
# Cross streets
for i in range(-70, 75, 10):
    road_positions.append((i, -25, 0))
    road_positions.append((i, 25, 0))
    road_positions.append((-25, i, 1.57))
    road_positions.append((25, i, 1.57))

# ---- TREES (street trees - every 5th) ----
for i, (x, y, yaw) in enumerate(road_positions):
    if i % 5 != 0:
        continue
    # Offset from road center
    ox = 3.0 if abs(y) > 20 else -3.0  # offset to sidewalk
    oy = 3.0 if abs(x) > 20 else -3.0
    tx = x + (ox if abs(yaw - 1.57) > 0.5 else 0)
    ty = y + (oy if abs(yaw - 1.57) < 0.5 else 0)
    # Skip if too close to center (roundabout)
    if math.hypot(tx, ty) < 15:
        continue
    # Skip if too close to buildings
    if abs(tx) < 20 and abs(ty) < 20:
        continue
    tree_type = random.choice(["oak_tree", "pine_tree"])
    counter["tree"] += 1
    models.append(model_tag(f"street_tree_{counter['tree']}", tree_type, tx, ty))

# ---- ELECTRICAL POLES (every 5th) ----
for i, (x, y, yaw) in enumerate(road_positions):
    if i % 5 != 0 or i % 3 == 0:
        continue
    ox = 4.5 if abs(y) > 20 else -4.5
    oy = 4.5 if abs(x) > 20 else -4.5
    px = x + (ox if abs(yaw - 1.57) > 0.5 else 0)
    py = y + (oy if abs(yaw - 1.57) < 0.5 else 0)
    if math.hypot(px, py) < 18:
        continue
    counter["pole"] += 1
    models.append(model_tag(f"elec_pole_{counter['pole']}", "electrical_pole", px, py))

# ---- PEOPLE near buildings and intersections ----
person_positions = [
    (18, 18), (22, -18), (-18, 22), (-22, -20),
    (35, 35), (35, -35), (-35, 35), (-35, -35),
    (0, 15), (15, 0), (-15, 0), (0, -15),
    (20, 40), (-20, 40), (40, 20), (40, -20),
    (30, -30), (-30, -30), (-40, 0), (0, -40),
]
for px, py in person_positions:
    counter["person"] += 1
    models.append(model_tag(f"person_{counter['person']}", "person", px, py))

# ---- CARS along roads ----
car_positions = [
    (30, -48, 0), (30, -42, 0), (-30, -48, 0),
    (48, -30, 1.57), (48, 30, 1.57), (-48, -30, 1.57),
    (30, 48, 0), (-30, 48, 0), (-48, 30, 1.57),
    (10, -48, 0), (-10, -48, 0),
    (48, -10, 1.57), (48, 10, 1.57),
]
for cx, cy, cyaw in car_positions:
    counter["car"] += 1
    car_model = "prius_hybrid"
    models.append(model_tag(f"street_car_{counter['car']}", car_model, cx, cy, yaw=cyaw))

# ---- ANIMALS in the park/garden area ----
animal_positions = [
    (25, 10), (30, 12), (22, 15),
    (-10, 25), (-12, 30), (-15, 22),
    (40, 40), (-40, -40),
]
for ax, ay in animal_positions:
    counter["animal"] += 1
    models.append(model_tag(f"animal_{counter['animal']}", "farm_animal", ax, ay))

# ---- BARRIERS near road edges ----
barrier_positions = [
    (8, -48, 0), (12, -48, 0),
    (48, 8, 1.57), (48, 12, 1.57),
    (-8, 48, 0), (-12, 48, 0),
    (-48, -8, 1.57), (-48, -12, 1.57),
]
for bx, by, byaw in barrier_positions:
    counter["barrier"] += 1
    models.append(model_tag(f"add_barrier_{counter['barrier']}", "jersey_barrier", bx, by, yaw=byaw))

# ---- TRAFFIC CONES ----
cone_positions = [(14, -48), (45, 14), (-14, 48), (-45, -14)]
for cx, cy in cone_positions:
    counter["cone"] += 1
    models.append(model_tag(f"traffic_cone_{counter['cone']}", "traffic_cone", cx, cy))

# ---- BUSHES ----
bush_positions = [
    (-20, -10), (-22, -8), (-25, -12), (-18, -15),
    (35, 0), (37, -2), (33, 2),
]
for bx, by in bush_positions:
    counter["bush"] += 1
    # Start from 4 because base SDF already has bush_1..bush_3
    bush_id = counter["bush"] + 3
    models.append(model_tag(f"bush_{bush_id}", "bush", bx, by))

# ---- STREET LAMPS (few along main roads) ----
lamp_positions = [
    (0, -50), (15, -50), (30, -50), (-15, -50), (-30, -50),
    (0, 50), (15, 50), (-15, 50),
    (50, 0), (50, 15), (50, -15),
    (-50, 0), (-50, 15), (-50, -15),
]
for lx, ly in lamp_positions:
    counter["lamp"] += 1
    models.append(model_tag(f"street_lamp_{counter['lamp']}", "street_lamp", lx, ly))

# ---- HOSPITAL (Southern district) ----
models.append(model_tag("central_hospital", "hospital", 0, -80, yaw=0))

# ---- EXTRA PRIUS CARS (parking lots) ----
extra_car_positions = [
    (42, 42, 1.0), (44, 40, 1.5), (40, 44, 0.5),
    (-42, -42, 0), (-44, -40, 3.0),
]
for cx, cy, cyaw in extra_car_positions:
    counter["car"] += 1
    models.append(model_tag(f"extra_car_{counter['car']}", "prius_hybrid", cx, cy, yaw=cyaw))

# ---------------------------------------------------------------------------
# 4. Write the final SDF
# ---------------------------------------------------------------------------
models_block = "\n".join(models)
footer_clean = footer.rstrip() + "\n"

total_models_before = len([l for l in header.split("\n") if "<model" in l])

sdf = header + "\n" + models_block + "\n\n" + footer_clean

with open(SDF_PATH, "w") as f:
    f.write(sdf)

total_models_after = len([l for l in sdf.split("\n") if "<model" in l])

print("=== Dodoma City Generation Complete ===")
print(f"  Base models: {total_models_before}")
print(f"  Added models: {sum(counter.values())}")
print(f"  Total models: {total_models_after}")
print(f"  Breakdown:")
for k, v in sorted(counter.items()):
    print(f"    {k}: {v}")
print(f"  SDF lines: {len(sdf.split(chr(10)))}")
