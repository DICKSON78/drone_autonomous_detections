#!/bin/bash

# PC4: Web Interface & Feedback Setup Script
# This script automatically sets up everything for PC4

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[PC4]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[PC4]${NC} $1"
}

print_error() {
    echo -e "${RED}[PC4]${NC} $1"
}

print_header() {
    echo -e "${BLUE}====================================${NC}"
    echo -e "${BLUE}PC4: Web Interface & Feedback Setup${NC}"
    echo -e "${BLUE}====================================${NC}"
}

# Get team IPs
get_team_ips() {
    print_status "Enter team member IP addresses:"
    echo ""
    
    read -p "PC1 IP [192.168.1.10]: " PC1_IP
    read -p "PC2 IP [192.168.1.11]: " PC2_IP
    read -p "PC3 IP [192.168.1.12]: " PC3_IP
    read -p "PC4 IP (Your IP) [192.168.1.13]: " PC4_IP
    
    # Set defaults
    PC1_IP=${PC1_IP:-"192.168.1.10"}
    PC2_IP=${PC2_IP:-"192.168.1.11"}
    PC3_IP=${PC3_IP:-"192.168.1.12"}
    PC4_IP=${PC4_IP:-"192.168.1.13"}
    
    print_status "Team IPs configured:"
    echo "PC1: $PC1_IP"
    echo "PC2: $PC2_IP"
    echo "PC3: $PC3_IP"
    echo "PC4 (You): $PC4_IP"
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

# Check audio permissions
check_audio() {
    print_status "Checking audio permissions..."
    
    # Add user to audio group
    if groups $USER | grep -q audio; then
        print_status "User already in audio group"
    else
        print_warning "Adding user to audio group (may require sudo)..."
        sudo usermod -aG audio $USER
        print_warning "You may need to logout and login again for audio to work"
    fi
}

# Update configuration
update_config() {
    print_status "Updating configuration..."
    
    # Update docker-compose.yml
    sed -i "s/PC1/$PC1_IP/g" docker-compose.yml
    sed -i "s/PC2/$PC2_IP/g" docker-compose.yml
    sed -i "s/PC3/$PC3_IP/g" docker-compose.yml
    sed -i "s/PC4/$PC4_IP/g" docker-compose.yml
    
    # Update hosts file if possible
    if [ -w "/etc/hosts" ]; then
        sudo sed -i '/# PC4 Drone System/,/# End PC4 System/d' /etc/hosts 2>/dev/null || true
        sudo tee -a /etc/hosts > /dev/null <<EOF
# PC4 Drone System
$PC1_IP PC1
$PC2_IP PC2
$PC3_IP PC3
$PC4_IP PC4
# End PC4 System
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
    
    # Test Web Dashboard
    for i in {1..10}; do
        if curl -s http://localhost >/dev/null 2>&1; then
            print_status "Web Dashboard is running"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Web Dashboard not ready yet"
        fi
        sleep 5
    done
    
    # Test WebSocket Server
    for i in {1..10}; do
        if curl -s http://localhost:8080 >/dev/null 2>&1; then
            print_status "WebSocket Server is running"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "WebSocket Server not ready yet"
        fi
        sleep 5
    done
    
    # Test Feedback Service
    for i in {1..10}; do
        if curl -s http://localhost:8005/health >/dev/null 2>&1; then
            print_status "Feedback Service is running"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Feedback Service not ready yet"
        fi
        sleep 5
    done
}

# Test TTS
test_tts() {
    print_status "Testing Text-to-Speech..."
    
    # Test TTS functionality
    curl -s -X POST http://localhost:8005/speak \
        -H "Content-Type: application/json" \
        -d '{"message": "Setup complete", "priority": "normal"}' >/dev/null 2>&1
    
    print_status "TTS test sent - you should hear 'Setup complete'"
}

# Show results
show_results() {
    echo ""
    print_header
    echo ""
    print_status "PC4 Setup Complete!"
    echo ""
    echo "Your services are running:"
    echo "Web Dashboard: http://$PC4_IP"
    echo "WebSocket Server: http://$PC4_IP:8080"
    echo "Feedback Service: http://$PC4_IP:8005"
    echo ""
    print_status "Test your services:"
    echo "curl http://localhost:8005/health"
    echo ""
    print_status "Open Web Dashboard:"
    echo "URL: http://localhost"
    echo "This is the main interface for the entire system"
    echo ""
    print_status "Test TTS:"
    echo "curl -X POST http://localhost:8005/speak \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"message\": \"Hello drone\", \"priority\": \"normal\"}'"
    echo ""
    print_status "View logs:"
    echo "docker-compose logs -f"
    echo ""
    print_status "Your system now has face and voice!"
    print_status "Ready for user interaction and control!"
}

# Open dashboard
open_dashboard() {
    print_status "Opening web dashboard..."
    
    # Try to open browser automatically
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost 2>/dev/null &
    elif command -v open >/dev/null 2>&1; then
        open http://localhost 2>/dev/null &
    else
        print_status "Please open http://localhost in your browser"
    fi
}

# Main setup
main() {
    print_header
    get_team_ips
    check_docker
    check_audio
    update_config
    build_services
    test_services
    test_tts
    show_results
    open_dashboard
    
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
    "dashboard")
        open_dashboard
        ;;
    "tts")
        test_tts
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
        echo "Usage: $0 {setup|test|logs|dashboard|tts|stop|restart|status}"
        echo "  setup     - Full setup (default)"
        echo "  test      - Test services"
        echo "  logs      - Show logs"
        echo "  dashboard - Open web dashboard"
        echo "  tts       - Test text-to-speech"
        echo "  stop      - Stop services"
        echo "  restart   - Restart services"
        echo "  status    - Show service status"
        exit 1
        ;;
esac
