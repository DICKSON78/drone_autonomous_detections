#!/bin/bash

echo "===================================="
echo "PC1: Command & Control Setup"
echo "===================================="

# Get IP addresses
echo "[PC1] Enter team member IP addresses:"
read -p "PC1 IP (Your IP) [192.168.1.10]: " PC1_IP
PC1_IP=${PC1_IP:-192.168.1.10}

read -p "PC2 IP [192.168.1.11]: " PC2_IP
PC2_IP=${PC2_IP:-192.168.1.11}

read -p "PC3 IP [192.168.1.12]: " PC3_IP
PC3_IP=${PC3_IP:-192.168.1.12}

read -p "PC4 IP [192.168.1.13]: " PC4_IP
PC4_IP=${PC4_IP:-192.168.1.13}

echo "[PC1] Team IPs configured:"
echo "PC1 (You): $PC1_IP"
echo "PC2: $PC2_IP"
echo "PC3: $PC3_IP"
echo "PC4: $PC4_IP"

# Check Docker
echo "[PC1] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "[PC1] ERROR: Docker is not installed"
    exit 1
fi
echo "[PC1] Docker is ready ✓"

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "[PC1] Using 'docker compose' command"
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Create .env file with IPs
echo "[PC1] Creating .env file..."
cat > .env << ENVEOF
PC1_IP=${PC1_IP}
PC2_IP=${PC2_IP}
PC3_IP=${PC3_IP}
PC4_IP=${PC4_IP}
ENVEOF

# Check if docker-compose.yml needs IP configuration
if [ -f "docker-compose.yml" ]; then
    echo "[PC1] Checking docker-compose.yml..."
    # Backup original
    cp docker-compose.yml docker-compose.yml.bak
    
    # Check if we need to add IP environment variables
    if ! grep -q "PC1_IP" docker-compose.yml; then
        echo "[PC1] Adding IP configuration to services..."
        
        # Add IP environment variables to command-parser service
        sed -i '/command-parser:/,/environment:/ {
            /environment:/ {
                a\      - PC1_IP=${PC1_IP}
                a\      - PC2_IP=${PC2_IP}
                a\      - PC3_IP=${PC3_IP}
                a\      - PC4_IP=${PC4_IP}
            }
        }' docker-compose.yml
        
        # Add IP environment variables to flight-control service
        sed -i '/flight-control:/,/environment:/ {
            /environment:/ {
                a\      - PC1_IP=${PC1_IP}
                a\      - PC2_IP=${PC2_IP}
                a\      - PC3_IP=${PC3_IP}
                a\      - PC4_IP=${PC4_IP}
            }
        }' docker-compose.yml
    else
        echo "[PC1] IP configuration already exists in docker-compose.yml"
    fi
    
    echo "[PC1] docker-compose.yml checked ✓"
fi

# Update any config files
if [ -d "config" ]; then
    echo "[PC1] Updating config files..."
    
    # Update any JSON config files with IPs
    for config_file in config/*.json; do
        if [ -f "$config_file" ]; then
            # Create backup
            cp "$config_file" "${config_file}.bak"
            
            # Update IPs in JSON files (if they exist as keys)
            sed -i "s/\"pc1_ip\": \"[^\"]*\"/\"pc1_ip\": \"${PC1_IP}\"/g" "$config_file" 2>/dev/null
            sed -i "s/\"pc2_ip\": \"[^\"]*\"/\"pc2_ip\": \"${PC2_IP}\"/g" "$config_file" 2>/dev/null
            sed -i "s/\"pc3_ip\": \"[^\"]*\"/\"pc3_ip\": \"${PC3_IP}\"/g" "$config_file" 2>/dev/null
            sed -i "s/\"pc4_ip\": \"[^\"]*\"/\"pc4_ip\": \"${PC4_IP}\"/g" "$config_file" 2>/dev/null
            
            echo "[PC1] Updated $(basename $config_file) ✓"
        fi
    done
    
    # Create/update config/ips.json if it doesn't exist
    if [ ! -f "config/ips.json" ]; then
        cat > config/ips.json << JSONEOF
{
  "pc1": "${PC1_IP}",
  "pc2": "${PC2_IP}",
  "pc3": "${PC3_IP}",
  "pc4": "${PC4_IP}"
}
JSONEOF
        echo "[PC1] Created config/ips.json ✓"
    fi
fi

echo "[PC1] Setup complete! ✓"
echo ""
echo "[PC1] Configuration summary:"
echo "  - Your IP: ${PC1_IP}"
echo "  - Team IPs saved in .env file"
echo "  - Configuration saved in config/ips.json"
echo ""
echo "[PC1] Next steps:"
echo "  1. Review the configuration: cat .env"
echo "  2. Review config/ips.json: cat config/ips.json"
echo "  3. Start the services: ${DOCKER_COMPOSE} up -d"
echo "  4. Check logs: ${DOCKER_COMPOSE} logs -f"
