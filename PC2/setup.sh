#!/bin/bash

# PC2: Vision & Navigation Setup Script
# This script automatically sets up everything for PC2

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[PC2]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[PC2]${NC} $1"
}

print_error() {
    echo -e "${RED}[PC2]${NC} $1"
}

print_header() {
    echo -e "${BLUE}====================================${NC}"
    echo -e "${BLUE}  PC2: Vision & Navigation Setup${NC}"
    echo -e "${BLUE}====================================${NC}"
}

# Check graphics drivers
check_graphics() {
    print_status "Checking graphics drivers..."
    
    if ! glxinfo >/dev/null 2>&1; then
        print_warning "Installing graphics utilities..."
        sudo apt update
        sudo apt install -y mesa-utils libgl1-mesa-glx libglu1-mesa
    fi
    
    # Check for NVIDIA
    if lspci | grep -i nvidia >/dev/null; then
        print_status "NVIDIA GPU detected"
        if ! nvidia-smi >/dev/null 2>&1; then
            print_warning "Installing NVIDIA drivers..."
            sudo apt install -y nvidia-driver-470
            print_warning "Please reboot after setup: sudo reboot"
        fi
    else
        print_status "Using Intel/AMD graphics"
    fi
}

# Get team IPs
get_team_ips() {
    print_status "Enter team member IP addresses:"
    echo ""
    
    read -p "PC1 IP [192.168.1.10]: " PC1_IP
    read -p "PC2 IP (Your IP) [192.168.1.11]: " PC2_IP
    read -p "PC3 IP [192.168.1.12]: " PC3_IP
    read -p "PC4 IP [192.168.1.13]: " PC4_IP
    
    # Set defaults
    PC1_IP=${PC1_IP:-"192.168.1.10"}
    PC2_IP=${PC2_IP:-"192.168.1.11"}
    PC3_IP=${PC3_IP:-"192.168.1.12"}
    PC4_IP=${PC4_IP:-"192.168.1.13"}
    
    print_status "Team IPs configured:"
    echo "PC1: $PC1_IP"
    echo "PC2 (You): $PC2_IP"
    echo "PC3: $PC3_IP"
    echo "PC4: $PC4_IP"
}

# Check Docker
check_docker() {
    print_status "Checking Docker..."
    
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker not installed. Installing..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_warning "Please run: newgrp docker && ./setup.sh"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker not running. Starting..."
        sudo systemctl start docker
        sudo usermod -aG docker $USER
        print_warning "Please run: newgrp docker && ./setup.sh"
        exit 1
    fi
    
    # Check for NVIDIA Docker runtime
    if lspci | grep -i nvidia >/dev/null; then
        if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi >/dev/null 2>&1; then
            print_warning "NVIDIA Docker runtime not available"
            print_status "CPU mode will be used (slower but functional)"
        else
            print_status "NVIDIA Docker runtime available ✓"
        fi
    fi
    
    print_status "Docker is ready ✓"
}

# Update configuration
update_config() {
    print_status "Updating configuration..."
    
    # Update docker-compose.yml
    sed -i "s/PC1/$PC1_IP/g" docker-compose.yml
    sed -i "s/PC2/$PC2_IP/g" docker-compose.yml
    
    # Enable X11 forwarding for Gazebo
    xhost +local:docker 2>/dev/null || true
    
    # Update hosts file if possible
    if [ -w "/etc/hosts" ]; then
        sudo sed -i '/# PC2 Drone System/,/# End PC2 System/d' /etc/hosts 2>/dev/null || true
        sudo tee -a /etc/hosts > /dev/null <<EOF
# PC2 Drone System
$PC1_IP PC1
$PC2_IP PC2
$PC3_IP PC3
$PC4_IP PC4
# End PC2 System
EOF
        print_status "Updated /etc/hosts ✓"
    fi
}

# Build and start services
build_services() {
    print_status "Building and starting services..."
    
    # Stop existing services
    docker-compose down 2>/dev/null || true
    
    # Build and start
    print_status "Building Docker images (this takes 10-15 minutes)..."
    print_status "Downloading YOLOv5 model and Gazebo components..."
    
    docker-compose up -d --build
    
    # Wait for services
    print_status "Waiting for services to start..."
    sleep 45
}

# Test services
test_services() {
    print_status "Testing services..."
    
    # Test Object Detection
    for i in {1..15}; do
        if curl -s http://localhost:8002/health >/dev/null 2>&1; then
            print_status "Object Detection is running ✓"
            break
        fi
        if [ $i -eq 15 ]; then
            print_warning "Object Detection not ready yet"
        fi
        sleep 10
    done
    
    # Test RL Navigation
    for i in {1..15}; do
        if curl -s http://localhost:8003/health >/dev/null 2>&1; then
            print_status "RL Navigation is running ✓"
            break
        fi
        if [ $i -eq 15 ]; then
            print_warning "RL Navigation not ready yet"
        fi
        sleep 10
    done
    
    # Test Gazebo
    for i in {1..10}; do
        if docker exec gazebo-px4 pgrep -f gazebo >/dev/null 2>&1; then
            print_status "Gazebo is running ✓"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Gazebo not ready yet"
        fi
        sleep 5
    done
}

# Open Gazebo GUI
open_gazebo() {
    print_status "Opening Gazebo GUI..."
    
    # Try to open Gazebo GUI
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --text="Gazebo is starting. The GUI window should open automatically." --width=300
    fi
    
    # Open Gazebo with display
    DISPLAY=$DISPLAY docker exec -e DISPLAY=$DISPLAY gazebo-px4 gazebo &
    
    print_status "If Gazebo doesn't open, run:"
    echo "docker exec -it gazebo-px4 gazebo"
}

# Show results
show_results() {
    echo ""
    print_header
    echo ""
    print_status " PC2 Setup Complete!"
    echo ""
    echo "Your services are running:"
    echo " Object Detection: http://$PC2_IP:8002"
    echo " RL Navigation: http://$PC2_IP:8003"
    echo " Gazebo Simulation: Running on your PC"
    echo ""
    print_status "Test your services:"
    echo "curl http://localhost:8002/health"
    echo "curl http://localhost:8003/health"
    echo ""
    print_status "Open Gazebo GUI:"
    echo "docker exec -it gazebo-px4 gazebo"
    echo ""
    print_status "Test object detection:"
    echo "curl -X POST http://localhost:8002/detect \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"image\": \"base64_image_data\"}'"
    echo ""
    print_status "View logs:"
    echo "docker-compose logs -f"
    echo ""
    print_status "Your drone can now see and think! "
    print_status "Ready for autonomous navigation! "
}

# Main setup
main() {
    print_header
    check_graphics
    get_team_ips
    check_docker
    update_config
    build_services
    test_services
    open_gazebo
    show_results
    
    echo ""
    read -p "View service logs? (y/n): " show_logs
    if [[ $show_logs =~ ^[Yy]$ ]]; then
        docker-compose logs -f
    fi
}

# Command options
case "${1:-setup}" in
    "setup")
        main
        ;;
    "test")
        test_services
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "gazebo")
        docker exec -it gazebo-px4 gazebo
        ;;
    "stop")
        docker-compose down
        print_status "Services stopped"
        ;;
    "restart")
        docker-compose restart
        print_status "Services restarted"
        ;;
    "status")
        docker-compose ps
        ;;
    *)
        echo "Usage: $0 {setup|test|logs|gazebo|stop|restart|status}"
        echo "  setup   - Full setup (default)"
        echo "  test    - Test services"
        echo "  logs    - Show logs"
        echo "  gazebo  - Open Gazebo GUI"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  status  - Show service status"
        exit 1
        ;;
esac
