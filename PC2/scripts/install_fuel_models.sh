#!/bin/bash
# Copy downloaded Fuel models into the volume-mounted /gazebo_models/dodoma dir
# This runs entirely inside the container

CONTAINER="gazebo-px4"
MODELS_DEST="/gazebo_models/dodoma"

# First, create the model directories and copy files inside the container
docker exec "$CONTAINER" bash -c '
models_dest="/gazebo_models/dodoma"
fuel_cache="/root/.gz/fuel/fuel.gazebosim.org"

# OpenRobotics models to copy
declare -A models
models["prius%20hybrid"]="prius_hybrid"
models["jersey%20barrier"]="jersey_barrier"
models["oak%20tree"]="oak_tree"
models["pine%20tree"]="pine_tree"
models["office%20building"]="office_building"
models["apartment"]="apartment"
models["post%20office"]="post_office"

for cache_name in "${!models[@]}"; do
    dest_name="${models[$cache_name]}"
    version=$(ls "$fuel_cache/openrobotics/models/$cache_name/" | sort -n | tail -1)
    echo "Copying $cache_name (v$version) -> $models_dest/$dest_name"
    
    mkdir -p "$models_dest/$dest_name"
    cp -r "$fuel_cache/openrobotics/models/$cache_name/$version/"* "$models_dest/$dest_name/"
    
    # Fix mesh/material URIs in model.sdf
    sdf_file="$models_dest/$dest_name/model.sdf"
    if [ -f "$sdf_file" ]; then
        old_url="https://fuel.gazebosim.org/1.0/openrobotics/models/$cache_name/$version/files/"
        sed -i "s|$old_url|./|g" "$sdf_file"
        sed -i "s|$old_url|./|g" "$sdf_file"  # materials too
        echo "  Fixed URIs in $dest_name"
    fi
done

# Copy chapulina apartment
chap_cache="/root/.gz/fuel/fuel.gazebosim.org/chapulina/models/apartment"
if [ -d "$chap_cache" ]; then
    chap_ver=$(ls "$chap_cache/" | sort -n | tail -1)
    echo "Copying chapulina/apartment (v$chap_ver) -> $models_dest/chapulina_apartment"
    mkdir -p "$models_dest/chapulina_apartment"
    cp -r "$chap_cache/$chap_ver/"* "$models_dest/chapulina_apartment/"
    sdf_file="$models_dest/chapulina_apartment/model.sdf"
    if [ -f "$sdf_file" ]; then
        sed -i "s|https://[^\"]*fuel\.gazebosim\.org[^\"]*/files/|./|g" "$sdf_file"
        echo "  Fixed URIs in chapulina_apartment"
    fi
fi

echo ""
echo "Models installed in $models_dest:"
ls -d "$models_dest"/*/
'
