#!/bin/bash

# PC1: Command & Control Setup Script
# This script automatically sets up everything for PC1

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[PC1]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[PC1]${NC} $1"
}

print_error() {
    echo -e "${RED}[PC1]${NC} $1"
}

print_header() {
    echo -e "${BLUE}====================================${NC}"
    echo -e "${BLUE}PC1: Command & Control Setup${NC}"
    echo -e "${BLUE}====================================${NC}"
}

# Get team IPs
get_team_ips() {
    print_status "Enter team member IP addresses:"
    echo ""
    
    read -p "PC1 IP (Your IP) [192.168.1.10]: " PC1_IP
    read -p "PC2 IP [192.168.1.11]: " PC2_IP
    read -p "PC3 IP [192.168.1.12]: " PC3_IP
    read -p "PC4 IP [192.168.1.13]: " PC4_IP
    
    # Set defaults
    PC1_IP=${PC1_IP:-"192.168.1.10"}
    PC2_IP=${PC2_IP:-"192.168.1.11"}
    PC3_IP=${PC3_IP:-"192.168.1.12"}
    PC4_IP=${PC4_IP:-"192.168.1.13"}
    
    print_status "Team IPs configured:"
    echo "PC1 (You): $PC1_IP"
    echo "PC2: $PC2_IP"
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
    
    print_status "Docker is ready ✓"
}

# Update configuration
update_config() {
    print_status "Updating configuration..."
    
    # Update docker-compose.yml
    sed -i "s/PC1/$PC1_IP/g" docker-compose.yml
    
    # Update hosts file if possible
    if [ -w "/etc/hosts" ]; then
        sudo sed -i '/# PC1 Drone System/,/# End PC1 System/d' /etc/hosts 2>/dev/null || true
        sudo tee -a /etc/hosts > /dev/null <<EOF
# PC1 Drone System
$PC1_IP PC1
$PC2_IP PC2
$PC3_IP PC3
$PC4_IP PC4
# End PC1 System
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
    print_status "Building Docker images (this takes 5-10 minutes)..."
    docker-compose up -d --build
    
    # Wait for services
    print_status "Waiting for services to start..."
    sleep 30
}

# Test services
test_services() {
    print_status "Testing services..."
    
    # Test Command Parser
    for i in {1..10}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            print_status "Command Parser is running ✓"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Command Parser not ready yet"
        fi
        sleep 5
    done
    
    # Test Flight Control
    for i in {1..10}; do
        if curl -s http://localhost:8001/health >/dev/null 2>&1; then
            print_status "Flight Control is running ✓"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Flight Control not ready yet"
        fi
        sleep 5
    done
    
    # Test Kafka
    for i in {1..10}; do
        if docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list >/dev/null 2>&1; then
            print_status "Kafka is running ✓"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Kafka not ready yet"
        fi
        sleep 5
    done
}

# Show results
show_results() {
    echo ""
    print_header
    echo ""
    print_status " PC1 Setup Complete!"
    echo ""
    echo "Your services are running:"
    echo " Command Parser: http://$PC1_IP:8000"
    echo " Flight Control: http://$PC1_IP:8001"
    echo " Kafka Broker: $PC1_IP:9092"
    echo ""
    print_status "Test your services:"
    echo "curl http://localhost:8000/health"
    echo "curl http://localhost:8001/health"
    echo ""
    print_status "Send test command:"
    echo "curl -X POST http://localhost:8000/parse-command \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"text\": \"Go to forest\", \"user_id\": \"test\"}'"
    echo ""
    print_status "View logs:"
    echo "docker-compose logs -f"
    echo ""
    print_status "Team can now connect to your services!"
    echo "Ready for autonomous drone operations! "
}

# Main setup
main() {
    print_header
    get_team_ips
    check_docker
    update_config
    
    # Use development setup script if available
    if [ -f "scripts/setup_dev.sh" ]; then
        print_status "Running development setup..."
        chmod +x scripts/setup_dev.sh
        scripts/setup_dev.sh
    fi
    
    build_services
    test_services
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
        echo "Usage: $0 {setup|test|logs|stop|restart|status}"
        echo "  setup   - Full setup (default)"
        echo "  test    - Test services"
        echo "  logs    - Show logs"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  status  - Show service status"
        exit 1
        ;;
esac
