#!/bin/bash

# PC3: Data & Monitoring Setup Script
# This script automatically sets up everything for PC3

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[PC3]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[PC3]${NC} $1"
}

print_error() {
    echo -e "${RED}[PC3]${NC} $1"
}

print_header() {
    echo -e "${BLUE}====================================${NC}"
    echo -e "${BLUE}PC3: Data & Monitoring Setup${NC}"
    echo -e "${BLUE}====================================${NC}"
}

# Get team IPs
get_team_ips() {
    print_status "Enter team member IP addresses:"
    echo ""
    
    read -p "PC1 IP [192.168.1.10]: " PC1_IP
    read -p "PC2 IP [192.168.1.11]: " PC2_IP
    read -p "PC3 IP (Your IP) [192.168.1.12]: " PC3_IP
    read -p "PC4 IP [192.168.1.13]: " PC4_IP
    
    # Set defaults
    PC1_IP=${PC1_IP:-"192.168.1.10"}
    PC2_IP=${PC2_IP:-"192.168.1.11"}
    PC3_IP=${PC3_IP:-"192.168.1.12"}
    PC4_IP=${PC4_IP:-"192.168.1.13"}
    
    print_status "Team IPs configured:"
    echo "PC1: $PC1_IP"
    echo "PC2: $PC2_IP"
    echo "PC3 (You): $PC3_IP"
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
    
    print_status "Docker is ready"
}

# Update configuration
update_config() {
    print_status "Updating configuration..."
    
    # Update docker-compose.yml
    sed -i "s/PC1/$PC1_IP/g" docker-compose.yml
    sed -i "s/PC2/$PC2_IP/g" docker-compose.yml
    sed -i "s/PC3/$PC3_IP/g" docker-compose.yml
    
    # Update hosts file if possible
    if [ -w "/etc/hosts" ]; then
        sudo sed -i '/# PC3 Drone System/,/# End PC3 System/d' /etc/hosts 2>/dev/null || true
        sudo tee -a /etc/hosts > /dev/null <<EOF
# PC3 Drone System
$PC1_IP PC1
$PC2_IP PC2
$PC3_IP PC3
$PC4_IP PC4
# End PC3 System
EOF
        print_status "Updated /etc/hosts"
    fi
}

# Build and start services
build_services() {
    print_status "Building and starting services..."
    
    # Stop existing services
    docker-compose down 2>/dev/null || true
    
    # Build and start
    print_status "Building Docker images (this takes 5-8 minutes)..."
    docker-compose up -d --build
    
    # Wait for services
    print_status "Waiting for services to start..."
    sleep 30
}

# Test services
test_services() {
    print_status "Testing services..."
    
    # Test Telemetry Collector
    for i in {1..10}; do
        if curl -s http://localhost:8004/health >/dev/null 2>&1; then
            print_status "Telemetry Collector is running"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Telemetry Collector not ready yet"
        fi
        sleep 5
    done
    
    # Test InfluxDB
    for i in {1..10}; do
        if curl -s http://localhost:8086/health >/dev/null 2>&1; then
            print_status "InfluxDB is running"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "InfluxDB not ready yet"
        fi
        sleep 5
    done
    
    # Test Grafana
    for i in {1..10}; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            print_status "Grafana is running"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Grafana not ready yet"
        fi
        sleep 5
    done
}

# Show results
show_results() {
    echo ""
    print_header
    echo ""
    print_status "PC3 Setup Complete!"
    echo ""
    echo "Your services are running:"
    echo "Telemetry Collector: http://$PC3_IP:8004"
    echo "InfluxDB: http://$PC3_IP:8086"
    echo "Grafana Dashboard: http://$PC3_IP:3000 (admin/admin123)"
    echo ""
    print_status "Test your services:"
    echo "curl http://localhost:8004/health"
    echo "curl http://localhost:8086/health"
    echo ""
    print_status "Open Grafana:"
    echo "URL: http://localhost:3000"
    echo "Username: admin"
    echo "Password: admin123"
    echo ""
    print_status "View logs:"
    echo "docker-compose logs -f"
    echo ""
    print_status "Your system now has memory and intelligence!"
    print_status "Ready for data analytics and monitoring!"
}

# Main setup
main() {
    print_header
    get_team_ips
    check_docker
    update_config
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
    "grafana")
        echo "Opening Grafana at http://localhost:3000"
        xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || echo "Please open http://localhost:3000 in your browser"
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
        echo "Usage: $0 {setup|test|logs|grafana|stop|restart|status}"
        echo "  setup   - Full setup (default)"
        echo "  test    - Test services"
        echo "  logs    - Show logs"
        echo "  grafana - Open Grafana dashboard"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  status  - Show service status"
        exit 1
        ;;
esac
