"""Transform dodoma_tanzania.sdf to use mesh-based Fuel models via <include>."""
import re, os

SDF_PATH = '/home/dickson/FYP/drone_autonomous/PC2/gazebo_worlds/dodoma/dodoma_tanzania.sdf'
BACKUP_PATH = SDF_PATH + '.bak'

with open(SDF_PATH) as f:
    sdf = f.read()

# Backup
if not os.path.exists(BACKUP_PATH):
    with open(BACKUP_PATH, 'w') as f:
        f.write(sdf)
    print(f"Backup saved to {BACKUP_PATH}")

replacements = []

# ------------------------------------------------------------------
# Helper: build an <include> block for a model
# ------------------------------------------------------------------
def include_block(model_name, static=True):
    s = f'    <include>\n      <uri>{model_name}</uri>\n'
    if static:
        s += '      <static>true</static>\n'
    s += '    </include>'
    return s

# ------------------------------------------------------------------
# SEDAN -> prius_hybrid
# ------------------------------------------------------------------
sedan_models = [
    ('sedan_1', '15 15 0.08 0 0 1.57'),
    ('sedan_2', '-15 -15 0.08 0 0 0'),
    ('sedan_3', '85 -30 0.08 0 0 1.57'),
]

for old_name, pose in sedan_models:
    old_block = re.search(
        r'<model name="' + old_name + r'">.*?</model>',
        sdf, re.DOTALL
    )
    if old_block:
        new_block = (
            f'    <model name="{old_name}">\n'
            f'      <pose>{pose}</pose>\n'
            f'      <include>\n'
            f'        <uri>prius_hybrid</uri>\n'
            f'        <static>true</static>\n'
            f'      </include>\n'
            f'    </model>'
        )
        sdf = sdf.replace(old_block.group(0), new_block)
        print(f"Replaced {old_name} with prius_hybrid")

# ------------------------------------------------------------------
# BARRIERS -> jersey_barrier
# ------------------------------------------------------------------
barrier_models = [
    ('barrier_ew_1', '-30 -10 0 0 0 0'),
    ('barrier_ew_2', '-10 -10 0 0 0 0'),
    ('barrier_ew_3', '10 -10 0 0 0 0'),
    ('barrier_ew_4', '30 -10 0 0 0 0'),
    ('barrier_ns_1', '-20 10 0 0 0 1.57'),
    ('barrier_ns_2', '-20 30 0 0 0 1.57'),
    ('barrier_ns_3', '20 30 0 0 0 1.57'),
    ('barrier_ns_4', '20 10 0 0 0 1.57'),
]

for old_name, pose in barrier_models:
    old_block = re.search(
        r'<model name="' + old_name + r'">.*?</model>',
        sdf, re.DOTALL
    )
    if old_block:
        new_block = (
            f'    <model name="{old_name}">\n'
            f'      <pose>{pose}</pose>\n'
            f'      <include>\n'
            f'        <uri>jersey_barrier</uri>\n'
            f'        <static>true</static>\n'
            f'      </include>\n'
            f'    </model>'
        )
        sdf = sdf.replace(old_block.group(0), new_block)
        print(f"Replaced {old_name} with jersey_barrier")

# ------------------------------------------------------------------
# CONES -> traffic_cone (custom model)
# ------------------------------------------------------------------
cone_models = [
    ('cone_1', '0 8 0 0 0 0'),
    ('cone_2', '2 -8 0 0 0 0'),
    ('cone_3', '-2 -8 0 0 0 0'),
    ('cone_4', '8 0 0 0 0 0'),
    ('cone_5', '-8 0 0 0 0 0'),
    ('cone_6', '0 -8 0 0 0 0'),
]

for old_name, pose in cone_models:
    old_block = re.search(
        r'<model name="' + old_name + r'">.*?</model>',
        sdf, re.DOTALL
    )
    if old_block:
        new_block = (
            f'    <model name="{old_name}">\n'
            f'      <pose>{pose}</pose>\n'
            f'      <include>\n'
            f'        <uri>traffic_cone</uri>\n'
            f'        <static>true</static>\n'
            f'      </include>\n'
            f'    </model>'
        )
        sdf = sdf.replace(old_block.group(0), new_block)
        print(f"Replaced {old_name} with traffic_cone")

# ------------------------------------------------------------------
# TREES - Replace roundabout_tree and scattered trees with oak/pine
# ------------------------------------------------------------------
# Roundabout tree -> oak
tree_replace = {
    'roundabout_tree': '0 0 0',
}

for old_name, pose in tree_replace.items():
    old_block = re.search(
        r'<model name="' + old_name + r'">.*?</model>',
        sdf, re.DOTALL
    )
    if old_block:
        new_block = (
            f'    <model name="roundabout_tree">\n'
            f'      <pose>0 0 0</pose>\n'
            f'      <include>\n'
            f'        <uri>oak_tree</uri>\n'
            f'        <static>true</static>\n'
            f'      </include>\n'
            f'    </model>'
        )
        sdf = sdf.replace(old_block.group(0), new_block)
        print(f"Replaced {old_name} with oak_tree")

# ------------------------------------------------------------------
# BUILDINGS - Replace main buildings with Fuel mesh models
# ------------------------------------------------------------------
building_replace = [
    # (model_name, pose, fuel_model)
    ('bank_building_1', '-20 20 0', 'office_building',
     'Bank building'),
    ('shopping_mall', '-30 -25 0', 'chapulina_apartment',
     'Shopping mall'),
    ('govt_building', '20 -65 0', 'post_office',
     'Government building'),
    ('office_block', '20 20 0', 'apartment',
     'Office block'),
]

for old_name, pose, fuel_model, desc in building_replace:
    old_block = re.search(
        r'<model name="' + old_name + r'">.*?</model>',
        sdf, re.DOTALL
    )
    if old_block:
        new_block = (
            f'    <model name="{old_name}">\n'
            f'      <pose>{pose}</pose>\n'
            f'      <include>\n'
            f'        <uri>{fuel_model}</uri>\n'
            f'        <static>true</static>\n'
            f'      </include>\n'
            f'    </model>'
        )
        sdf = sdf.replace(old_block.group(0), new_block)
        print(f"Replaced {old_name} ({desc}) with {fuel_model}")

# ------------------------------------------------------------------
# LAMPS -> street_lamp (custom model)
# ------------------------------------------------------------------
lamp_models = [
    ('lamp_post_1', '15 15 0'),
    ('lamp_post_2', '-15 15 0'),
    ('lamp_post_3', '-15 -15 0'),
    ('lamp_post_4', '15 -15 0'),
]

for old_name, pose in lamp_models:
    old_block = re.search(
        r'<model name="' + old_name + r'">.*?</model>',
        sdf, re.DOTALL
    )
    if old_block:
        new_block = (
            f'    <model name="{old_name}">\n'
            f'      <pose>{pose}</pose>\n'
            f'      <include>\n'
            f'        <uri>street_lamp</uri>\n'
            f'        <static>true</static>\n'
            f'      </include>\n'
            f'    </model>'
        )
        sdf = sdf.replace(old_block.group(0), new_block)
        print(f"Replaced {old_name} with street_lamp")

# ------------------------------------------------------------------
# Write the result
# ------------------------------------------------------------------
with open(SDF_PATH, 'w') as f:
    f.write(sdf)

print("\nSDF transformation complete!")
print(f"File written: {SDF_PATH}")
