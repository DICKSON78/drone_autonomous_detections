#!/bin/bash
# Gazebo-PX4 custom entrypoint wrapper
# Ensures the Dodoma world and models are loaded in Gazebo Harmonic

set -e

# Ensure custom world is in PX4's standard world path
WORLD_SRC="/gazebo_worlds/dodoma/dodoma_tanzania.sdf"
WORLD_DST="/opt/px4-gazebo/share/gz/worlds/dodoma_tanzania.sdf"
if [ -f "$WORLD_SRC" ] && [ ! -f "$WORLD_DST" ]; then
    cp "$WORLD_SRC" "$WORLD_DST" 2>/dev/null || ln -sf "$WORLD_SRC" "$WORLD_DST" 2>/dev/null || true
fi

# Ensure custom models are in the resource path
if [ -d "/gazebo_models/dodoma" ]; then
    if [ -n "$GZ_SIM_RESOURCE_PATH" ]; then
        export GZ_SIM_RESOURCE_PATH="/gazebo_models/dodoma:$GZ_SIM_RESOURCE_PATH"
    else
        export GZ_SIM_RESOURCE_PATH="/gazebo_models/dodoma:/opt/px4-gazebo/share/gz/models:/opt/px4-gazebo/share/gz/worlds"
    fi
fi

# Execute the original command (PX4)
exec "$@"
