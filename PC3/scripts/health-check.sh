#!/bin/bash

# PC3 Health Check Script
# Monitors the health of all PC3 services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[HEALTHY]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if services are running
check_service_status() {
    print_info "=== Service Status Check ==="
    
    services=("influxdb" "grafana" "telemetry-collector")
    
    for service in "${services[@]}"; do
        container_id=$(docker-compose ps -q $service 2>/dev/null)
        
        if [ -z "$container_id" ]; then
            print_error "$service: Not running"
            continue
        fi
        
        status=$(docker inspect --format='{{.State.Status}}' $container_id)
        health=$(docker inspect --format='{{.State.Health.Status}}' $container_id 2>/dev/null || echo "no-healthcheck")
        
        if [ "$status" = "running" ]; then
            if [ "$health" = "healthy" ] || [ "$health" = "no-healthcheck" ]; then
                print_status "$service: $status ($health)"
            else
                print_warning "$service: $status ($health)"
            fi
        else
            print_error "$service: $status"
        fi
    done
}

# Check service endpoints
check_endpoints() {
    print_info "=== Endpoint Health Check ==="
    
    # Check InfluxDB
    if curl -s http://localhost:8086/health > /dev/null; then
        print_status "InfluxDB API: Responding"
    else
        print_error "InfluxDB API: Not responding"
    fi
    
    # Check Grafana
    if curl -s http://localhost:3000/api/health > /dev/null; then
        print_status "Grafana API: Responding"
    else
        print_error "Grafana API: Not responding"
    fi
    
    # Check Telemetry Collector
    if curl -s http://localhost:8004/health > /dev/null; then
        print_status "Telemetry Collector API: Responding"
    else
        print_error "Telemetry Collector API: Not responding"
    fi
}

# Check resource usage
check_resources() {
    print_info "=== Resource Usage ==="
    
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" \
        $(docker-compose ps -q) 2>/dev/null || print_warning "Could not get resource usage"
}

# Check disk space
check_disk_space() {
    print_info "=== Disk Space ==="
    
    df -h | grep -E "(Filesystem|/dev/)" | head -5
    
    # Check docker volumes
    docker system df 2>/dev/null || print_warning "Could not get Docker system info"
}

# Check logs for errors
check_logs() {
    print_info "=== Recent Log Errors ==="
    
    services=("influxdb" "grafana" "telemetry-collector")
    
    for service in "${services[@]}"; do
        errors=$(docker-compose logs --tail=50 $service 2>&1 | grep -i error | wc -l)
        if [ "$errors" -gt 0 ]; then
            print_warning "$service: $errors error(s) in recent logs"
            docker-compose logs --tail=5 $service 2>&1 | grep -i error | tail -3
        else
            print_status "$service: No recent errors"
        fi
    done
}

# Check network connectivity
check_network() {
    print_info "=== Network Connectivity ==="
    
    # Check if containers can communicate
    if docker-compose exec telemetry-collector ping -c 1 influxdb > /dev/null 2>&1; then
        print_status "Telemetry Collector -> InfluxDB: Connected"
    else
        print_error "Telemetry Collector -> InfluxDB: Not connected"
    fi
    
    if docker-compose exec telemetry-collector ping -c 1 grafana > /dev/null 2>&1; then
        print_status "Telemetry Collector -> Grafana: Connected"
    else
        print_error "Telemetry Collector -> Grafana: Not connected"
    fi
}

# Database connectivity check
check_database() {
    print_info "=== Database Connectivity ==="
    
    # Check InfluxDB buckets
    if curl -s -X GET "http://localhost:8086/api/v2/buckets" \
        -H "Authorization: Token drone-telemetry-token" \
        -H "Accept: application/json" > /dev/null; then
        print_status "InfluxDB: Authentication working"
    else
        print_warning "InfluxDB: Authentication issue"
    fi
    
    # Check Grafana datasource
    if curl -s -X GET "http://localhost:3000/api/datasources" \
        -u admin:admin123 > /dev/null; then
        print_status "Grafana: API access working"
    else
        print_warning "Grafana: API access issue"
    fi
}

# Main health check
main() {
    echo "=== PC3 Health Check ==="
    echo "Time: $(date)"
    echo ""
    
    check_service_status
    echo ""
    check_endpoints
    echo ""
    check_resources
    echo ""
    check_disk_space
    echo ""
    check_logs
    echo ""
    check_network
    echo ""
    check_database
    
    echo ""
    print_info "Health check completed"
    echo "For detailed logs: docker-compose logs -f [service-name]"
}

# Run health check
main "$@"
