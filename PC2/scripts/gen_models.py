"""Generate proper Gazebo model directories for the Dodoma world.
Each model gets a model.config and model.sdf with detailed multi-part geometry.
"""
import os, shutil

MODELS_DIR = '/home/dickson/FYP/drone_autonomous/PC2/gazebo_models/dodoma'

def mkdir(path):
    os.makedirs(path, exist_ok=True)

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

# ---------------------------------------------------------------------------
# Building – multi-storey with windows, roof, entrance
# ---------------------------------------------------------------------------
BUILDING_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Dodoma Building</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Multi-storey building typical of Dodoma, Tanzania</description>
</model>'''

BUILDING_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="dodoma_building">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <geometry><box><size>14 12 10</size></box></geometry>
      </collision>
      <!-- Main walls -->
      <visual name="walls">
        <pose>0 0 5 0 0 0</pose>
        <geometry><box><size>14 12 10</size></box></geometry>
        <material>
          <ambient>0.7 0.65 0.6 1</ambient>
          <diffuse>0.75 0.7 0.65 1</diffuse>
          <specular>0.15 0.12 0.1 1</specular>
        </material>
      </visual>
      <!-- Front windows row 1 -->
      <visual name="front_w1">
        <pose>0 6.1 7 0 0 0</pose>
        <geometry><box><size>10 0.15 2.5</size></box></geometry>
        <material>
          <ambient>0.45 0.55 0.7 0.7</ambient>
          <diffuse>0.5 0.6 0.75 0.7</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Front windows row 2 -->
      <visual name="front_w2">
        <pose>0 6.1 4 0 0 0</pose>
        <geometry><box><size>10 0.15 2.5</size></box></geometry>
        <material>
          <ambient>0.45 0.55 0.7 0.7</ambient>
          <diffuse>0.5 0.6 0.75 0.7</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Back windows row 1 -->
      <visual name="back_w1">
        <pose>0 -6.1 7 0 0 0</pose>
        <geometry><box><size>10 0.15 2.5</size></box></geometry>
        <material>
          <ambient>0.45 0.55 0.7 0.7</ambient>
          <diffuse>0.5 0.6 0.75 0.7</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Back windows row 2 -->
      <visual name="back_w2">
        <pose>0 -6.1 4 0 0 0</pose>
        <geometry><box><size>10 0.15 2.5</size></box></geometry>
        <material>
          <ambient>0.45 0.55 0.7 0.7</ambient>
          <diffuse>0.5 0.6 0.75 0.7</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Side windows left -->
      <visual name="left_w1">
        <pose>-7.1 0 5.5 0 0 0</pose>
        <geometry><box><size>0.15 8 4</size></box></geometry>
        <material>
          <ambient>0.45 0.55 0.7 0.7</ambient>
          <diffuse>0.5 0.6 0.75 0.7</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Side windows right -->
      <visual name="right_w1">
        <pose>7.1 0 5.5 0 0 0</pose>
        <geometry><box><size>0.15 8 4</size></box></geometry>
        <material>
          <ambient>0.45 0.55 0.7 0.7</ambient>
          <diffuse>0.5 0.6 0.75 0.7</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Roof -->
      <visual name="roof">
        <pose>0 0 10.3 0 0 0</pose>
        <geometry><box><size>14.8 12.8 0.5</size></box></geometry>
        <material>
          <ambient>0.5 0.4 0.35 1</ambient>
          <diffuse>0.55 0.45 0.4 1</diffuse>
          <specular>0.1 0.08 0.05 1</specular>
        </material>
      </visual>
      <!-- Entrance -->
      <visual name="entrance">
        <pose>0 6.1 1.2 0 0 0</pose>
        <geometry><box><size>2.5 0.3 2</size></box></geometry>
        <material>
          <ambient>0.35 0.25 0.15 1</ambient>
          <diffuse>0.4 0.3 0.2 1</diffuse>
          <specular>0.1 0.08 0.05 1</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Acacia Tree – detailed trunk + flat umbrella canopy
# ---------------------------------------------------------------------------
TREE_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Acacia Tree</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Acacia tree common in Dodoma region, Tanzania</description>
</model>'''

TREE_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="acacia_tree">
    <static>true</static>
    <link name="trunk">
      <collision name="trunk_col">
        <geometry><cylinder><radius>0.2</radius><length>3.5</length></cylinder></geometry>
      </collision>
      <visual name="trunk_vis">
        <geometry><cylinder><radius>0.25</radius><length>3.5</length></cylinder></geometry>
        <material>
          <ambient>0.45 0.35 0.25 1</ambient>
          <diffuse>0.5 0.4 0.3 1</diffuse>
          <specular>0.05 0.05 0.05 1</specular>
        </material>
      </visual>
    </link>
    <link name="canopy">
      <pose>0 0 4.5 0 0 0</pose>
      <collision name="canopy_col">
        <geometry><cylinder><radius>3</radius><length>0.6</length></cylinder></geometry>
      </collision>
      <visual name="canopy_vis">
        <geometry><cylinder><radius>3.5</radius><length>0.8</length></cylinder></geometry>
        <material>
          <ambient>0.2 0.5 0.15 1</ambient>
          <diffuse>0.25 0.55 0.2 1</diffuse>
          <specular>0.15 0.3 0.1 1</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Baobab Tree – fat trunk, branches
# ---------------------------------------------------------------------------
BAOBAB_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Baobab Tree</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Baobab tree (Adansonia digitata) common in Tanzania</description>
</model>'''

BAOBAB_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="baobab_tree">
    <static>true</static>
    <link name="trunk">
      <collision name="trunk_col">
        <geometry><cylinder><radius>2</radius><length>6</length></cylinder></geometry>
      </collision>
      <visual name="trunk_vis">
        <geometry><cylinder><radius>2.5</radius><length>6</length></cylinder></geometry>
        <material>
          <ambient>0.55 0.45 0.35 1</ambient>
          <diffuse>0.6 0.5 0.4 1</diffuse>
          <specular>0.08 0.06 0.04 1</specular>
        </material>
      </visual>
    </link>
    <link name="canopy">
      <pose>0 0 5 0 0 0</pose>
      <collision name="canopy_col">
        <geometry><sphere><radius>3.5</radius></sphere></geometry>
      </collision>
      <visual name="canopy_vis">
        <geometry><sphere><radius>4</radius></sphere></geometry>
        <material>
          <ambient>0.2 0.4 0.15 1</ambient>
          <diffuse>0.25 0.45 0.2 1</diffuse>
          <specular>0.1 0.2 0.05 1</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Sedan Car – body, cabin, wheels, lights
# ---------------------------------------------------------------------------
CAR_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Sedan Car</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Sedan car as an obstacle object</description>
</model>'''

CAR_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="sedan_car">
    <static>true</static>
    <link name="body">
      <collision name="col">
        <geometry><box><size>2 4 0.6</size></box></geometry>
      </collision>
      <!-- Main body -->
      <visual name="body_vis">
        <geometry><box><size>2 4 0.6</size></box></geometry>
        <material>
          <ambient>0.15 0.15 0.5 1</ambient>
          <diffuse>0.2 0.2 0.55 1</diffuse>
          <specular>0.5 0.5 0.5 1</specular>
        </material>
      </visual>
      <!-- Cabin/roof -->
      <visual name="cabin">
        <pose>0 -0.3 0.5 0 0 0</pose>
        <geometry><box><size>1.8 2.2 0.35</size></box></geometry>
        <material>
          <ambient>0.3 0.35 0.4 1</ambient>
          <diffuse>0.35 0.4 0.45 1</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Windows -->
      <visual name="windshield">
        <pose>0 -2.15 0.5 0 0 0</pose>
        <geometry><box><size>1.6 0.08 0.3</size></box></geometry>
        <material>
          <ambient>0.4 0.5 0.7 0.6</ambient>
          <diffuse>0.45 0.55 0.75 0.6</diffuse>
          <specular>0.5 0.5 0.5 1</specular>
        </material>
      </visual>
      <!-- 4 wheels -->
      <visual name="wheel_fl">
        <pose>-1.15 1.3 0.12 0 0 0</pose>
        <geometry><cylinder><radius>0.25</radius><length>0.2</length></cylinder></geometry>
        <material>
          <ambient>0.08 0.08 0.08 1</ambient>
          <diffuse>0.12 0.12 0.12 1</diffuse>
          <specular>0.05 0.05 0.05 1</specular>
        </material>
      </visual>
      <visual name="wheel_fr">
        <pose>1.15 1.3 0.12 0 0 0</pose>
        <geometry><cylinder><radius>0.25</radius><length>0.2</length></cylinder></geometry>
        <material>
          <ambient>0.08 0.08 0.08 1</ambient>
          <diffuse>0.12 0.12 0.12 1</diffuse>
          <specular>0.05 0.05 0.05 1</specular>
        </material>
      </visual>
      <visual name="wheel_rl">
        <pose>-1.15 -1.3 0.12 0 0 0</pose>
        <geometry><cylinder><radius>0.25</radius><length>0.2</length></cylinder></geometry>
        <material>
          <ambient>0.08 0.08 0.08 1</ambient>
          <diffuse>0.12 0.12 0.12 1</diffuse>
          <specular>0.05 0.05 0.05 1</specular>
        </material>
      </visual>
      <visual name="wheel_rr">
        <pose>1.15 -1.3 0.12 0 0 0</pose>
        <geometry><cylinder><radius>0.25</radius><length>0.2</length></cylinder></geometry>
        <material>
          <ambient>0.08 0.08 0.08 1</ambient>
          <diffuse>0.12 0.12 0.12 1</diffuse>
          <specular>0.05 0.05 0.05 1</specular>
        </material>
      </visual>
      <!-- Headlights -->
      <visual name="headlight_l">
        <pose>-0.6 -2.05 0.15 0 0 0</pose>
        <geometry><box><size>0.3 0.1 0.12</size></box></geometry>
        <material>
          <ambient>1 0.9 0.6 1</ambient>
          <diffuse>1 0.95 0.7 1</diffuse>
          <emissive>0.3 0.25 0.1 1</emissive>
        </material>
      </visual>
      <visual name="headlight_r">
        <pose>0.6 -2.05 0.15 0 0 0</pose>
        <geometry><box><size>0.3 0.1 0.12</size></box></geometry>
        <material>
          <ambient>1 0.9 0.6 1</ambient>
          <diffuse>1 0.95 0.7 1</diffuse>
          <emissive>0.3 0.25 0.1 1</emissive>
        </material>
      </visual>
      <!-- Tail lights -->
      <visual name="taillight_l">
        <pose>-0.6 2.05 0.15 0 0 0</pose>
        <geometry><box><size>0.3 0.1 0.1</size></box></geometry>
        <material>
          <ambient>0.6 0.1 0.1 1</ambient>
          <diffuse>0.7 0.15 0.15 1</diffuse>
          <emissive>0.2 0.05 0.05 1</emissive>
        </material>
      </visual>
      <visual name="taillight_r">
        <pose>0.6 2.05 0.15 0 0 0</pose>
        <geometry><box><size>0.3 0.1 0.1</size></box></geometry>
        <material>
          <ambient>0.6 0.1 0.1 1</ambient>
          <diffuse>0.7 0.15 0.15 1</diffuse>
          <emissive>0.2 0.05 0.05 1</emissive>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Jersey Barrier
# ---------------------------------------------------------------------------
BARRIER_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Jersey Barrier</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Concrete Jersey traffic barrier</description>
</model>'''

BARRIER_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="jersey_barrier">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <geometry><box><size>2 0.5 0.6</size></box></geometry>
      </collision>
      <visual name="concrete">
        <pose>0 0 0.3 0 0 0</pose>
        <geometry><box><size>2 0.5 0.6</size></box></geometry>
        <material>
          <ambient>0.65 0.62 0.58 1</ambient>
          <diffuse>0.7 0.67 0.63 1</diffuse>
          <specular>0.1 0.1 0.1 1</specular>
        </material>
      </visual>
      <!-- Yellow stripe -->
      <visual name="stripe">
        <pose>0 0 0.55 0 0 0</pose>
        <geometry><box><size>1.8 0.3 0.08</size></box></geometry>
        <material>
          <ambient>0.85 0.7 0.1 1</ambient>
          <diffuse>0.9 0.75 0.15 1</diffuse>
          <emissive>0.15 0.1 0.02 1</emissive>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Traffic Cone
# ---------------------------------------------------------------------------
CONE_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Traffic Cone</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Orange traffic safety cone</description>
</model>'''

CONE_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="traffic_cone">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <geometry><box><size>0.4 0.4 0.5</size></box></geometry>
      </collision>
      <visual name="cone_base">
        <pose>0 0 0.06 0 0 0</pose>
        <geometry><box><size>0.4 0.4 0.08</size></box></geometry>
        <material>
          <ambient>0.9 0.5 0.05 1</ambient>
          <diffuse>0.95 0.55 0.1 1</diffuse>
          <specular>0.15 0.08 0.02 1</specular>
        </material>
      </visual>
      <visual name="cone_body">
        <pose>0 0 0.3 0 0 0</pose>
        <geometry><cylinder><radius>0.15</radius><length>0.4</length></cylinder></geometry>
        <material>
          <ambient>0.9 0.5 0.05 1</ambient>
          <diffuse>0.95 0.55 0.1 1</diffuse>
          <specular>0.1 0.05 0.01 1</specular>
        </material>
      </visual>
      <!-- White reflective band -->
      <visual name="reflective_band">
        <pose>0 0 0.3 0 0 0</pose>
        <geometry><cylinder><radius>0.16</radius><length>0.08</length></cylinder></geometry>
        <material>
          <ambient>0.85 0.85 0.85 1</ambient>
          <diffuse>0.9 0.9 0.9 1</diffuse>
          <emissive>0.1 0.1 0.1 1</emissive>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Street Lamp
# ---------------------------------------------------------------------------
LAMP_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Street Lamp</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Street lamp post common in Dodoma city</description>
</model>'''

LAMP_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="street_lamp">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <geometry><cylinder><radius>0.2</radius><length>6</length></cylinder></geometry>
      </collision>
      <!-- Pole -->
      <visual name="pole">
        <pose>0 0 3 0 0 0</pose>
        <geometry><cylinder><radius>0.15</radius><length>6</length></cylinder></geometry>
        <material>
          <ambient>0.5 0.5 0.5 1</ambient>
          <diffuse>0.55 0.55 0.55 1</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Arm -->
      <visual name="arm">
        <pose>0 0.6 6 0 0 0</pose>
        <geometry><box><size>0.08 1.2 0.08</size></box></geometry>
        <material>
          <ambient>0.45 0.45 0.45 1</ambient>
          <diffuse>0.5 0.5 0.5 1</diffuse>
          <specular>0.3 0.3 0.3 1</specular>
        </material>
      </visual>
      <!-- Light fixture -->
      <visual name="light_fixture">
        <pose>0 1.3 5.95 0 0 0</pose>
        <geometry><box><size>0.15 0.2 0.15</size></box></geometry>
        <material>
          <ambient>0.9 0.9 0.6 1</ambient>
          <diffuse>1 1 0.8 1</diffuse>
          <emissive>0.5 0.5 0.2 1</emissive>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Bush
# ---------------------------------------------------------------------------
BUSH_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Bush</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Small bush/shrub vegetation</description>
</model>'''

BUSH_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="bush">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <geometry><box><size>1 1 0.6</size></box></geometry>
      </collision>
      <visual name="bush_vis">
        <pose>0 0 0.4 0 0 0</pose>
        <geometry><sphere><radius>0.8</radius></sphere></geometry>
        <material>
          <ambient>0.2 0.45 0.15 1</ambient>
          <diffuse>0.25 0.5 0.2 1</diffuse>
          <specular>0.1 0.2 0.05 1</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Bus
# ---------------------------------------------------------------------------
BUS_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Bus</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name><email>fyp@droneproject</email></author>
  <description>Minibus (dala-dala) common in Tanzania</description>
</model>'''

BUS_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="bus">
    <static>true</static>
    <link name="body">
      <collision name="col">
        <geometry><box><size>2.5 5.5 1.2</size></box></geometry>
      </collision>
      <visual name="body_vis">
        <pose>0 0 0.6 0 0 0</pose>
        <geometry><box><size>2.5 5.5 1.2</size></box></geometry>
        <material>
          <ambient>0.85 0.7 0.1 1</ambient>
          <diffuse>0.9 0.75 0.15 1</diffuse>
          <specular>0.3 0.25 0.05 1</specular>
        </material>
      </visual>
      <!-- Cabin -->
      <visual name="cabin">
        <pose>0 -0.5 1.3 0 0 0</pose>
        <geometry><box><size>2.3 3.5 0.7</size></box></geometry>
        <material>
          <ambient>0.35 0.4 0.45 1</ambient>
          <diffuse>0.4 0.45 0.5 1</diffuse>
          <specular>0.3 0.3 0.3 1</specular>
        </material>
      </visual>
      <!-- Windows -->
      <visual name="windows">
        <pose>0 -0.5 1.3 0 0 0</pose>
        <geometry><box><size>2.1 3.3 0.5</size></box></geometry>
        <material>
          <ambient>0.4 0.5 0.7 0.6</ambient>
          <diffuse>0.45 0.55 0.75 0.6</diffuse>
          <specular>0.4 0.4 0.4 1</specular>
        </material>
      </visual>
      <!-- Wheels -->
      <visual name="wheel_fl">
        <pose>-1.4 1.7 0.15 0 0 0</pose>
        <geometry><cylinder><radius>0.3</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.12 0.12 0.12 1</diffuse></material>
      </visual>
      <visual name="wheel_fr">
        <pose>1.4 1.7 0.15 0 0 0</pose>
        <geometry><cylinder><radius>0.3</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.12 0.12 0.12 1</diffuse></material>
      </visual>
      <visual name="wheel_rl">
        <pose>-1.4 -1.7 0.15 0 0 0</pose>
        <geometry><cylinder><radius>0.3</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.12 0.12 0.12 1</diffuse></material>
      </visual>
      <visual name="wheel_rr">
        <pose>1.4 -1.7 0.15 0 0 0</pose>
        <geometry><cylinder><radius>0.3</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.12 0.12 0.12 1</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>'''

# ---------------------------------------------------------------------------
# Create all model directories
# ---------------------------------------------------------------------------
models = {
    'building':      (BUILDING_CONFIG, BUILDING_SDF),
    'acacia_tree':   (TREE_CONFIG, TREE_SDF),
    'baobab_tree':   (BAOBAB_CONFIG, BAOBAB_SDF),
    'sedan_car':     (CAR_CONFIG, CAR_SDF),
    'jersey_barrier':(BARRIER_CONFIG, BARRIER_SDF),
    'traffic_cone':  (CONE_CONFIG, CONE_SDF),
    'street_lamp':   (LAMP_CONFIG, LAMP_SDF),
    'bush':          (BUSH_CONFIG, BUSH_SDF),
    'bus':           (BUS_CONFIG, BUS_SDF),
}

for name, (config, sdf) in models.items():
    d = os.path.join(MODELS_DIR, name)
    mkdir(d)
    write_file(os.path.join(d, 'model.config'), config)
    write_file(os.path.join(d, 'model.sdf'), sdf)
    print(f'Created model: {name}')

print(f'\nAll models created in {MODELS_DIR}')
