"""Create additional custom models for the Dodoma city environment."""
import os

BASE = '/home/dickson/FYP/drone_autonomous/PC2/gazebo_models/dodoma'

def mkdir(p):
    os.makedirs(p, exist_ok=True)

def write(path, content):
    with open(path, 'w') as f:
        f.write(content)

# =========================================================================
# PERSON (standing humanoid)
# =========================================================================
PERSON_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Person</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name></author>
  <description>Standing person (pedestrian)</description>
</model>'''

PERSON_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="person">
    <static>true</static>
    <!-- Body/torso -->
    <link name="torso">
      <visual name="body">
        <pose>0 0 0.85 0 0 0</pose>
        <geometry><cylinder><radius>0.2</radius><length>0.7</length></cylinder></geometry>
        <material>
          <ambient>0.2 0.3 0.6 1</ambient>
          <diffuse>0.25 0.35 0.65 1</diffuse>
        </material>
      </visual>
      <!-- Head -->
      <visual name="head">
        <pose>0 0 1.25 0 0 0</pose>
        <geometry><sphere><radius>0.15</radius></sphere></geometry>
        <material>
          <ambient>0.85 0.75 0.65 1</ambient>
          <diffuse>0.9 0.8 0.7 1</diffuse>
        </material>
      </visual>
      <!-- Left leg -->
      <visual name="leg_l">
        <pose>-0.08 0 0.4 0 0 0</pose>
        <geometry><cylinder><radius>0.06</radius><length>0.7</length></cylinder></geometry>
        <material>
          <ambient>0.15 0.15 0.15 1</ambient>
          <diffuse>0.2 0.2 0.2 1</diffuse>
        </material>
      </visual>
      <!-- Right leg -->
      <visual name="leg_r">
        <pose>0.08 0 0.4 0 0 0</pose>
        <geometry><cylinder><radius>0.06</radius><length>0.7</length></cylinder></geometry>
        <material>
          <ambient>0.15 0.15 0.15 1</ambient>
          <diffuse>0.2 0.2 0.2 1</diffuse>
        </material>
      </visual>
      <!-- Left arm -->
      <visual name="arm_l">
        <pose>-0.25 0 0.9 0 0 0.3</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.5</length></cylinder></geometry>
        <material>
          <ambient>0.85 0.75 0.65 1</ambient>
          <diffuse>0.9 0.8 0.7 1</diffuse>
        </material>
      </visual>
      <!-- Right arm -->
      <visual name="arm_r">
        <pose>0.25 0 0.9 0 0 -0.3</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.5</length></cylinder></geometry>
        <material>
          <ambient>0.85 0.75 0.65 1</ambient>
          <diffuse>0.9 0.8 0.7 1</diffuse>
        </material>
      </visual>
      <collision name="col">
        <pose>0 0 0.85 0 0 0</pose>
        <geometry><cylinder><radius>0.25</radius><length>1.5</length></cylinder></geometry>
      </collision>
    </link>
  </model>
</sdf>'''

# =========================================================================
# ELECTRICAL POLE
# =========================================================================
POLE_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Electrical Pole</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name></author>
  <description>Concrete electrical utility pole with crossbars</description>
</model>'''

POLE_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="electrical_pole">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <pose>0 0 4 0 0 0</pose>
        <geometry><cylinder><radius>0.15</radius><length>8</length></cylinder></geometry>
      </collision>
      <!-- Pole -->
      <visual name="pole">
        <pose>0 0 4 0 0 0</pose>
        <geometry><cylinder><radius>0.15</radius><length>8</length></cylinder></geometry>
        <material>
          <ambient>0.5 0.5 0.5 1</ambient>
          <diffuse>0.55 0.55 0.55 1</diffuse>
          <specular>0.1 0.1 0.1 1</specular>
        </material>
      </visual>
      <!-- Crossarm 1 (top, along X) -->
      <visual name="crossarm_x">
        <pose>0 0 7.5 0 0 0</pose>
        <geometry><box><size>2 0.08 0.08</size></box></geometry>
        <material>
          <ambient>0.3 0.3 0.3 1</ambient>
          <diffuse>0.35 0.35 0.35 1</diffuse>
        </material>
      </visual>
      <!-- Crossarm 2 (middle, along Y) -->
      <visual name="crossarm_y">
        <pose>0 0 7 0 0 0</pose>
        <geometry><box><size>0.08 2 0.08</size></box></geometry>
        <material>
          <ambient>0.3 0.3 0.3 1</ambient>
          <diffuse>0.35 0.35 0.35 1</diffuse>
        </material>
      </visual>
      <!-- Insulators on crossarm 1 -->
      <visual name="insulator_x1">
        <pose>-1 0 7.55 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.06</length></cylinder></geometry>
        <material><ambient>0.8 0.8 0.8 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material>
      </visual>
      <visual name="insulator_x2">
        <pose>1 0 7.55 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.06</length></cylinder></geometry>
        <material><ambient>0.8 0.8 0.8 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material>
      </visual>
      <!-- Insulators on crossarm 2 -->
      <visual name="insulator_y1">
        <pose>0 -1 7.05 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.06</length></cylinder></geometry>
        <material><ambient>0.8 0.8 0.8 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material>
      </visual>
      <visual name="insulator_y2">
        <pose>0 1 7.05 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.06</length></cylinder></geometry>
        <material><ambient>0.8 0.8 0.8 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>'''

# =========================================================================
# COW / GOAT (generic farm animal)
# =========================================================================
ANIMAL_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Farm Animal</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name></author>
  <description>Farm animal (goat/cow) common in Tanzanian villages</description>
</model>'''

ANIMAL_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="farm_animal">
    <static>true</static>
    <link name="body">
      <collision name="col">
        <pose>0 0 0.35 0 0 0</pose>
        <geometry><box><size>0.6 1.0 0.5</size></box></geometry>
      </collision>
      <!-- Body -->
      <visual name="body_vis">
        <pose>0 0 0.35 0 0 0</pose>
        <geometry><box><size>0.5 0.9 0.35</size></box></geometry>
        <material>
          <ambient>0.7 0.6 0.5 1</ambient>
          <diffuse>0.75 0.65 0.55 1</diffuse>
        </material>
      </visual>
      <!-- Head -->
      <visual name="head">
        <pose>0 -0.55 0.45 0 0 0</pose>
        <geometry><sphere><radius>0.15</radius></sphere></geometry>
        <material>
          <ambient>0.7 0.6 0.5 1</ambient>
          <diffuse>0.75 0.65 0.55 1</diffuse>
        </material>
      </visual>
      <!-- 4 legs -->
      <visual name="leg_fl">
        <pose>-0.2 0.35 0.1 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.6 0.5 0.4 1</ambient><diffuse>0.65 0.55 0.45 1</diffuse></material>
      </visual>
      <visual name="leg_fr">
        <pose>0.2 0.35 0.1 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.6 0.5 0.4 1</ambient><diffuse>0.65 0.55 0.45 1</diffuse></material>
      </visual>
      <visual name="leg_rl">
        <pose>-0.2 -0.35 0.1 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.6 0.5 0.4 1</ambient><diffuse>0.65 0.55 0.45 1</diffuse></material>
      </visual>
      <visual name="leg_rr">
        <pose>0.2 -0.35 0.1 0 0 0</pose>
        <geometry><cylinder><radius>0.04</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.6 0.5 0.4 1</ambient><diffuse>0.65 0.55 0.45 1</diffuse></material>
      </visual>
      <!-- Horns -->
      <visual name="horn_l">
        <pose>-0.08 -0.62 0.55 0 0 0.4</pose>
        <geometry><cylinder><radius>0.02</radius><length>0.15</length></cylinder></geometry>
        <material><ambient>0.4 0.35 0.3 1</ambient><diffuse>0.45 0.4 0.35 1</diffuse></material>
      </visual>
      <visual name="horn_r">
        <pose>0.08 -0.62 0.55 0 0 -0.4</pose>
        <geometry><cylinder><radius>0.02</radius><length>0.15</length></cylinder></geometry>
        <material><ambient>0.4 0.35 0.3 1</ambient><diffuse>0.45 0.4 0.35 1</diffuse></material>
      </visual>
      <!-- Tail -->
      <visual name="tail">
        <pose>0 0.55 0.35 0 0 0</pose>
        <geometry><cylinder><radius>0.02</radius><length>0.2</length></cylinder></geometry>
        <material><ambient>0.5 0.4 0.3 1</ambient><diffuse>0.55 0.45 0.35 1</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>'''

# =========================================================================
# HOSPITAL BUILDING
# =========================================================================
HOSPITAL_CONFIG = '''<?xml version="1.0"?>
<model>
  <name>Hospital Building</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>FYP Team</name></author>
  <description>Hospital building with medical cross landmark</description>
</model>'''

HOSPITAL_SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="hospital">
    <static>true</static>
    <link name="main">
      <collision name="col">
        <pose>0 0 6 0 0 0</pose>
        <geometry><box><size>20 15 12</size></box></geometry>
      </collision>
      <!-- Main building -->
      <visual name="walls">
        <pose>0 0 6 0 0 0</pose>
        <geometry><box><size>20 15 12</size></box></geometry>
        <material>
          <ambient>0.85 0.85 0.85 1</ambient>
          <diffuse>0.9 0.9 0.9 1</diffuse>
          <specular>0.1 0.1 0.1 1</specular>
        </material>
      </visual>
      <!-- Windows front row 1 -->
      <visual name="w_front_1">
        <pose>0 7.6 8 0 0 0</pose>
        <geometry><box><size>16 0.2 4</size></box></geometry>
        <material>
          <ambient>0.4 0.5 0.7 0.6</ambient>
          <diffuse>0.45 0.55 0.75 0.6</diffuse>
          <specular>0.3 0.3 0.3 1</specular>
        </material>
      </visual>
      <!-- Windows front row 2 -->
      <visual name="w_front_2">
        <pose>0 7.6 3 0 0 0</pose>
        <geometry><box><size>16 0.2 4</size></box></geometry>
        <material>
          <ambient>0.4 0.5 0.7 0.6</ambient>
          <diffuse>0.45 0.55 0.75 0.6</diffuse>
          <specular>0.3 0.3 0.3 1</specular>
        </material>
      </visual>
      <!-- Roof -->
      <visual name="roof">
        <pose>0 0 12.3 0 0 0</pose>
        <geometry><box><size>20.8 15.8 0.5</size></box></geometry>
        <material>
          <ambient>0.5 0.45 0.4 1</ambient>
          <diffuse>0.55 0.5 0.45 1</diffuse>
        </material>
      </visual>
      <!-- Red cross on roof -->
      <visual name="cross_h">
        <pose>0 4 12.8 0 0 0</pose>
        <geometry><box><size>3 0.8 0.1</size></box></geometry>
        <material>
          <ambient>0.9 0.1 0.1 1</ambient>
          <diffuse>1 0.15 0.15 1</diffuse>
          <emissive>0.3 0.05 0.05 1</emissive>
        </material>
      </visual>
      <visual name="cross_v">
        <pose>0 4 12.8 0 0 0</pose>
        <geometry><box><size>0.8 3 0.1</size></box></geometry>
        <material>
          <ambient>0.9 0.1 0.1 1</ambient>
          <diffuse>1 0.15 0.15 1</diffuse>
          <emissive>0.3 0.05 0.05 1</emissive>
        </material>
      </visual>
      <!-- Entrance -->
      <visual name="entrance">
        <pose>0 7.6 1.5 0 0 0</pose>
        <geometry><box><size>3 0.3 2.5</size></box></geometry>
        <material>
          <ambient>0.3 0.6 0.3 1</ambient>
          <diffuse>0.35 0.65 0.35 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>'''

# =========================================================================
# GENERATE ALL MODELS
# =========================================================================
models = {
    'person':          (PERSON_CONFIG, PERSON_SDF),
    'electrical_pole': (POLE_CONFIG, POLE_SDF),
    'farm_animal':     (ANIMAL_CONFIG, ANIMAL_SDF),
    'hospital':        (HOSPITAL_CONFIG, HOSPITAL_SDF),
}

for name, (config, sdf) in models.items():
    d = os.path.join(BASE, name)
    mkdir(d)
    write(os.path.join(d, 'model.config'), config)
    write(os.path.join(d, 'model.sdf'), sdf)
    print(f'Created model: {name}')

print('\\nAll custom city models created!')
