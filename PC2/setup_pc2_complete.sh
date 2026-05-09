#!/bin/bash

# PC2 Complete Setup and Testing Script
# This script sets up and tests everything in PC2

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
    echo -e "${BLUE}  PC2 Complete Setup & Testing${NC}"
    echo -e "${BLUE}====================================${NC}"
}

# Check if we're in PC2 directory
check_directory() {
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "Please run this script from PC2 directory"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install basic dependencies
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        wget \
        git \
        build-essential \
        cmake \
        pkg-config \
        libjpeg-dev \
        libtiff5-dev \
        libpng-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libgtk-3-dev \
        libatlas-base-dev \
        gfortran \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        libgthread-2.0-0
    
    # Install Gazebo
    print_status "Installing Gazebo..."
    sudo apt install -y \
        gazebo11 \
        libgazebo11-dev \
        gazebo11-common \
        gazebo11-plugin-base \
        gazebo11-plugin-base-dev
    
    # Install PX4 (optional for advanced users)
    print_warning "PX4 installation skipped (requires manual setup)"
    print_warning "See: https://docs.px4.io/main/en/get_started/"
    
    print_status "✓ System dependencies installed"
}

# Setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        print_status "✓ Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies for all modules
    print_status "Installing Python dependencies..."
    
    # Object Detection dependencies
    pip install -r src/object-detection/requirements.txt
    
    # RL Navigation dependencies
    pip install -r src/rl-navigation/requirements.txt
    
    # Additional dependencies
    pip install \
        matplotlib \
        seaborn \
        tqdm \
        tensorboard \
        pytest \
        pytest-asyncio
    
    print_status "✓ Python dependencies installed"
}

# Create directories and setup configuration
setup_directories() {
    print_status "Creating directories and configuration..."
    
    # Create necessary directories
    mkdir -p worlds models data/detection_images data/rl_training logs
    
    # Make scripts executable
    chmod +x scripts/*.sh
    chmod +x setup_pc2_complete.sh
    chmod +x test_locally.py
    chmod +x launch_gazebo_gui.py
    
    print_status "✓ Directories and permissions set"
}

# Fix configuration files
fix_configurations() {
    print_status "Fixing configuration files..."
    
    # Update environment file
    cat > config/environment.env << EOF
# PC2 Environment Configuration
PC1_IP=192.168.1.10
PC2_IP=192.168.1.11
PC3_IP=192.168.1.12
PC4_IP=192.168.1.13

# Service Ports
OBJECT_DETECTION_PORT=8002
RL_NAVIGATION_PORT=8003
GAZEBO_PORT=11345

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=pc1:9092

# Model Paths
YOLO_MODEL_PATH=/app/models/yolov8n.pt
RL_MODEL_PATH=/app/models/rl_navigation.pth
EOF
    
    print_status "✓ Configuration files updated"
}

# Download models
download_models() {
    print_status "Downloading AI models..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Download YOLOv8 model
    cd models
    python3 -c "
from ultralytics import YOLO
try:
    model = YOLO('yolov8n.pt')
    print('✓ YOLOv8n model downloaded successfully')
except Exception as e:
    print(f'YOLO download failed: {e}')
"
    cd ..
    
    print_status "✓ Models downloaded"
}

# Test modules locally
test_modules_locally() {
    print_status "Testing modules locally..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run module tests
    python3 test_locally.py modules
    
    print_status "✓ Module tests completed"
}

# Start services locally
start_local_services() {
    print_status "Starting services locally..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Start services in background
    python3 test_locally.py services &
    SERVICES_PID=$!
    
    # Wait for services to start
    sleep 10
    
    # Test APIs
    python3 test_locally.py api
    
    print_status "✓ Local services tested"
    
    # Stop services
    kill $SERVICES_PID 2>/dev/null || true
    wait $SERVICES_PID 2>/dev/null || true
}

# Launch Gazebo GUI
launch_gazebo() {
    print_status "Launching Gazebo GUI environment..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Setup X11
    export DISPLAY=${DISPLAY:-:0}
    xhost +local:docker 2>/dev/null || true
    
    # Launch Gazebo with our custom launcher
    python3 launch_gazebo_gui.py
    
    print_status "✓ Gazebo GUI launched"
}

# Setup Docker (optional)
setup_docker() {
    print_status "Setting up Docker environment..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_status "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_warning "Please run: newgrp docker && ./setup_pc2_complete.sh"
        exit 0
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_status "Installing Docker Compose..."
        sudo apt install -y docker-compose-plugin
    fi
    
    print_status "✓ Docker environment ready"
}

# Build Docker images
build_docker_images() {
    print_status "Building Docker images..."
    
    # Build object detection image
    cd src/object-detection
    docker build -t pc2-object-detection .
    cd ../..
    
    # Build RL navigation image
    cd src/rl-navigation
    docker build -t pc2-rl-navigation .
    cd ../..
    
    print_status "✓ Docker images built"
}

# Test Docker deployment
test_docker_deployment() {
    print_status "Testing Docker deployment..."
    
    # Stop existing containers
    docker-compose down 2>/dev/null || true
    
    # Start services
    docker-compose up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 30
    
    # Test services
    print_status "Testing Object Detection..."
    if curl -s http://localhost:8002/health > /dev/null; then
        print_status "✓ Object Detection service healthy"
    else
        print_error "✗ Object Detection service failed"
    fi
    
    print_status "Testing RL Navigation..."
    if curl -s http://localhost:8003/health > /dev/null; then
        print_status "✓ RL Navigation service healthy"
    else
        print_error "✗ RL Navigation service failed"
    fi
    
    print_status "✓ Docker deployment test completed"
}

# Show usage information
show_usage() {
    echo ""
    print_header
    echo "PC2 Setup Complete! Here's what you can do:"
    echo ""
    echo -e "${CYAN}Local Testing:${NC}"
    echo "  • Test modules:     ./setup_pc2_complete.sh modules"
    echo "  • Test services:    ./setup_pc2_complete.sh services"
    echo "  • Test APIs:        ./setup_pc2_complete.sh api"
    echo ""
    echo -e "${CYAN}Gazebo Simulation:${NC}"
    echo "  • Launch GUI:       ./setup_pc2_complete.sh gazebo"
    echo "  • Custom launcher:   python3 launch_gazebo_gui.py"
    echo ""
    echo -e "${CYAN}Docker Deployment:${NC}"
    echo "  • Setup Docker:     ./setup_pc2_complete.sh docker-setup"
    echo "  • Build images:     ./setup_pc2_complete.sh docker-build"
    echo "  • Test deployment:  ./setup_pc2_complete.sh docker-test"
    echo "  • Start services:    docker-compose up -d"
    echo ""
    echo -e "${CYAN}Service URLs:${NC}"
    echo "  • Object Detection: http://localhost:8002"
    echo "  • RL Navigation:    http://localhost:8003"
    echo "  • Health Checks:    curl http://localhost:8002/health"
    echo "                      curl http://localhost:8003/health"
    echo ""
    echo -e "${CYAN}Testing Commands:${NC}"
    echo "  • Module tests:     python3 test_locally.py modules"
    echo "  • Full test suite:   python3 test_locally.py"
    echo ""
}

# Main function
main() {
    print_header
    
    # Check directory
    check_directory
    
    case "${1:-all}" in
        "deps"|"dependencies")
            install_dependencies
            setup_python_env
            ;;
        "modules")
            setup_directories
            fix_configurations
            download_models
            test_modules_locally
            ;;
        "services")
            start_local_services
            ;;
        "api")
            source venv/bin/activate
            python3 test_locally.py api
            ;;
        "gazebo")
            setup_directories
            launch_gazebo
            ;;
        "docker-setup")
            setup_docker
            ;;
        "docker-build")
            build_docker_images
            ;;
        "docker-test")
            test_docker_deployment
            ;;
        "all")
            print_status "Running complete PC2 setup..."
            install_dependencies
            setup_python_env
            setup_directories
            fix_configurations
            download_models
            test_modules_locally
            start_local_services
            print_status "✓ Complete PC2 setup finished!"
            show_usage
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  deps, dependencies  - Install system and Python dependencies"
            echo "  modules              - Setup and test modules"
            echo "  services             - Start local services"
            echo "  api                  - Test API endpoints"
            echo "  gazebo               - Launch Gazebo GUI"
            echo "  docker-setup         - Setup Docker environment"
            echo "  docker-build         - Build Docker images"
            echo "  docker-test          - Test Docker deployment"
            echo "  all                  - Run complete setup (default)"
            echo "  help                 - Show this help"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
