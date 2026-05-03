# Gazebo environment setup script


#!/bin/bash
echo "=== PC2 Gazebo + PX4 Setup ==="

# Create necessary directories
mkdir -p /app/worlds /app/models /app/data/detection_images /app/logs

# Generate default world if not exists
if [ ! -f "/app/worlds/drone_world.world" ]; then
    echo "Generating default Gazebo world..."
    python -c "
from src.gazebo_integration.world_builder import WorldBuilder
builder = WorldBuilder()
builder.generate_urban_world('/app/worlds/drone_world.world', num_buildings=12)
builder.generate_forest_world('/app/worlds/forest_world.world', num_trees=25)
print('Worlds generated successfully')
"
fi

echo "PC2 Setup completed!"