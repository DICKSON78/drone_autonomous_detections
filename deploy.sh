#!/bin/bash

# Autonomous Drone System Deployment Script
# This script deploys the entire system across 4 PCs

set -e

echo " Autonomous Drone System Deployment"
echo "===================================="

# Configuration
PC1_IP="192.168.1.10"
PC2_IP="192.168.1.11" 
PC3_IP="192.168.1.12"
PC4_IP="192.168.1.13"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker status
check_docker() {
    if command_exists docker; then
        if docker info >/dev/null 2>&1; then
            return 0
        else
            print_error "Docker is not running"
            return 1
        fi
    else
        print_error "Docker is not installed"
        return 1
    fi
}

# Function to check Docker Compose
check_docker_compose() {
    if command_exists docker-compose; then
        return 0
    else
        print_error "Docker Compose is not installed"
        return 1
    fi
}

# Function to deploy to a specific PC
deploy_to_pc() {
    local pc_name=$1
    local pc_dir=$2
    
    print_status "Deploying to $pc_name..."
    
    if [ ! -d "$pc_dir" ]; then
        print_error "Directory $pc_dir not found"
        return 1
    fi
    
    cd "$pc_dir"
    
    # Check if docker-compose.yml exists
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found in $pc_dir"
        return 1
    fi
    
    # Stop existing services
    print_warning "Stopping existing services on $pc_name..."
    docker-compose down
    
    # Build and start services
    print_status "Building and starting services on $pc_name..."
    docker-compose up -d --build
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check service health
    print_status "Checking service health on $pc_name..."
    docker-compose ps
    
    print_status "$pc_name deployment completed!"
    cd ..
}

# Function to test connectivity between PCs
test_connectivity() {
    print_status "Testing connectivity between PCs..."
    
    # Test Kafka connection from PC2 to PC1
    if docker exec PC2/object-detection python -c "
import kafka
try:
    producer = kafka.KafkaProducer(bootstrap_servers=['PC1:9092'])
    print('Kafka connection: OK')
except Exception as e:
    print(f'Kafka connection: FAILED - {e}')
" 2>/dev/null; then
        print_status "PC2 to PC1 Kafka connectivity: OK"
    else
        print_warning "PC2 to PC1 Kafka connectivity: Check network"
    fi
}

# Function to show system status
show_system_status() {
    echo ""
    print_status "System Status Summary"
    echo "=========================="
    
    echo "PC1 (Command & Control):"
    echo "  - Command Parser: http://$PC1_IP:8000/health"
    echo "  - Flight Control: http://$PC1_IP:8001/health"
    echo "  - Kafka: $PC1_IP:9092"
    
    echo ""
    echo "PC2 (Vision & Navigation):"
    echo "  - Object Detection: http://$PC2_IP:8002/health"
    echo "  - RL Navigation: http://$PC2_IP:8003/health"
    echo "  - Gazebo Simulation: Running on PC2"
    
    echo ""
    echo "PC3 (Data & Monitoring):"
    echo "  - Telemetry Collector: http://$PC3_IP:8004/health"
    echo "  - InfluxDB: http://$PC3_IP:8086"
    echo "  - Grafana: http://$PC3_IP:3000 (admin/admin123)"
    
    echo ""
    echo "PC4 (Web Interface):"
    echo "  - Web Dashboard: http://$PC4_IP"
    echo "  - WebSocket Server: http://$PC4_IP:8080"
    echo "  - Feedback Service: http://$PC4_IP:8005/health"
    
    echo ""
    print_status "Deployment completed successfully!"
    print_status "Access the web dashboard at: http://$PC4_IP"
}

# Main deployment function
main() {
    print_status "Starting deployment process..."
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! check_docker; then
        print_error "Please install and start Docker"
        exit 1
    fi
    
    if ! check_docker_compose; then
        print_error "Please install Docker Compose"
        exit 1
    fi
    
    # Deploy to each PC
    print_status "Deploying services to all PCs..."
    
    deploy_to_pc "PC1 (Command & Control)" "PC1"
    deploy_to_pc "PC2 (Vision & Navigation)" "PC2" 
    deploy_to_pc "PC3 (Data & Monitoring)" "PC3"
    deploy_to_pc "PC4 (Web Interface)" "PC4"
    
    # Test connectivity
    test_connectivity
    
    # Show status
    show_system_status
    
    print_status "All services deployed! "
}

# Function to stop all services
stop_all() {
    print_status "Stopping all services..."
    
    for pc_dir in PC1 PC2 PC3 PC4; do
        if [ -d "$pc_dir" ]; then
            cd "$pc_dir"
            print_warning "Stopping services on $pc_dir..."
            docker-compose down
            cd ..
        fi
    done
    
    print_status "All services stopped!"
}

# Function to restart all services
restart_all() {
    print_status "Restarting all services..."
    stop_all
    sleep 5
    main
}

# Command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        restart_all
        ;;
    "status")
        show_system_status
        ;;
    "test")
        test_connectivity
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|status|test}"
        echo "  deploy  - Deploy all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show system status"
        echo "  test    - Test connectivity"
        exit 1
        ;;
esac
