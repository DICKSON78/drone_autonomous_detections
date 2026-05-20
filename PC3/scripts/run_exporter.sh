#!/bin/bash
# Run the drone exporter persistently
while true; do
    python3 /home/dickson/FYP/drone_autonomous/PC3/scripts/drone_exporter.py
    echo "Exporter crashed at $(date), restarting in 2s..."
    sleep 2
done
