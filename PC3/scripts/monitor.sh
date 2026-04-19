#!/bin/bash

# PC3 Monitoring Script
# Real-time monitoring of all PC3 services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

# Show real-time logs
show_logs() {
    local service=$1
    print_header "Real-time Logs: $service"
    docker-compose logs -f $service
}

# Show service metrics
show_metrics() {
    print_header "Service Metrics"
    echo "Press Ctrl+C to stop monitoring"
    echo ""
    
    while true; do
        clear
        print_header "PC3 Service Metrics - $(date)"
        
        # Service status
        print_info "Service Status:"
        docker-compose ps
        echo ""
        
        # Resource usage
        print_info "Resource Usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
            $(docker-compose ps -q) 2>/dev/null || echo "Could not get resource stats"
        echo ""
        
        # Disk usage
        print_info "Disk Usage:"
        df -h | grep -E "(Filesystem|/dev/)" | head -3
        echo ""
        
        sleep 5
    done
}

# Show network activity
show_network() {
    print_header "Network Activity"
    
    while true; do
        clear
        print_header "Network Activity - $(date)"
        
        # Container network stats
        docker stats --no-stream --format "table {{.Container}}\t{{.NetIO}}\t{{.BlockIO}}" \
            $(docker-compose ps -q) 2>/dev/null || echo "Could not get network stats"
        echo ""
        
        # Port status
        print_info "Port Status:"
        netstat -tlnp 2>/dev/null | grep -E "(3000|8086|8004)" || echo "Port check failed"
        echo ""
        
        sleep 10
    done
}

# Show database status
show_database() {
    print_header "Database Status"
    
    while true; do
        clear
        print_header "InfluxDB Status - $(date)"
        
        # Check InfluxDB health
        if curl -s http://localhost:8086/health | jq . 2>/dev/null; then
            print_status "InfluxDB is healthy"
        else
            print_error "InfluxDB health check failed"
        fi
        echo ""
        
        # Database size
        print_info "Database Information:"
        curl -s -X GET "http://localhost:8086/api/v2/buckets" \
            -H "Authorization: Token drone-telemetry-token" \
            -H "Accept: application/json" 2>/dev/null | \
            jq '.buckets[] | {name: .name, orgID: .orgID, retentionRules: .retentionRules}' 2>/dev/null || echo "Could not fetch bucket info"
        echo ""
        
        sleep 30
    done
}

# Show Grafana status
show_grafana() {
    print_header "Grafana Status"
    
    while true; do
        clear
        print_header "Grafana Status - $(date)"
        
        # Check Grafana health
        if curl -s http://localhost:3000/api/health | jq . 2>/dev/null; then
            print_status "Grafana is healthy"
        else
            print_error "Grafana health check failed"
        fi
        echo ""
        
        # Check datasources
        print_info "Data Sources:"
        curl -s -X GET "http://localhost:3000/api/datasources" \
            -u admin:admin123 2>/dev/null | \
            jq '.[] | {name: .name, type: .type, access: .access}' 2>/dev/null || echo "Could not fetch datasources"
        echo ""
        
        # Check dashboards
        print_info "Dashboards:"
        curl -s -X GET "http://localhost:3000/api/search" \
            -u admin:admin123 2>/dev/null | \
            jq '.[] | {title: .title, uid: .uid, type: .type}' 2>/dev/null || echo "Could not fetch dashboards"
        echo ""
        
        sleep 30
    done
}

# Show telemetry collector status
show_telemetry() {
    print_header "Telemetry Collector Status"
    
    while true; do
        clear
        print_header "Telemetry Collector - $(date)"
        
        # Check API health
        if curl -s http://localhost:8004/health | jq . 2>/dev/null; then
            print_status "Telemetry Collector is healthy"
        else
            print_error "Telemetry Collector health check failed"
        fi
        echo ""
        
        # Get detailed status
        print_info "Service Status:"
        curl -s http://localhost:8004/status | jq . 2>/dev/null || echo "Could not fetch status"
        echo ""
        
        # Get metrics
        print_info "Metrics:"
        curl -s http://localhost:8004/metrics | jq . 2>/dev/null || echo "Could not fetch metrics"
        echo ""
        
        sleep 15
    done
}

# Interactive menu
show_menu() {
    while true; do
        clear
        print_header "PC3 Monitoring Menu"
        echo "1. Real-time Logs"
        echo "2. Service Metrics"
        echo "3. Network Activity"
        echo "4. Database Status"
        echo "5. Grafana Status"
        echo "6. Telemetry Collector Status"
        echo "7. All Services Overview"
        echo "8. Exit"
        echo ""
        read -p "Select option (1-8): " choice
        
        case $choice in
            1)
                echo "Select service:"
                echo "1) influxdb"
                echo "2) grafana"
                echo "3) telemetry-collector"
                read -p "Choice (1-3): " log_choice
                case $log_choice in
                    1) show_logs influxdb ;;
                    2) show_logs grafana ;;
                    3) show_logs telemetry-collector ;;
                    *) print_error "Invalid choice" ;;
                esac
                ;;
            2)
                show_metrics
                ;;
            3)
                show_network
                ;;
            4)
                show_database
                ;;
            5)
                show_grafana
                ;;
            6)
                show_telemetry
                ;;
            7)
                print_header "All Services Overview"
                docker-compose ps
                echo ""
                docker stats --no-stream $(docker-compose ps -q) 2>/dev/null || echo "Could not get stats"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            8)
                print_info "Exiting monitoring..."
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                sleep 2
                ;;
        esac
    done
}

# Command line argument handling
case "${1:-}" in
    logs)
        if [ -z "$2" ]; then
            print_error "Please specify a service: influxdb, grafana, telemetry-collector"
            exit 1
        fi
        show_logs "$2"
        ;;
    metrics)
        show_metrics
        ;;
    network)
        show_network
        ;;
    database)
        show_database
        ;;
    grafana)
        show_grafana
        ;;
    telemetry)
        show_telemetry
        ;;
    *)
        show_menu
        ;;
esac
