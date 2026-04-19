#!/bin/bash

# PC3 Test Data Generation Script
# Generates realistic drone telemetry data for testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Configuration
INFLUXDB_URL="http://localhost:8086"
ORG="drone-project"
BUCKET="drone_telemetry"
TOKEN="drone-telemetry-token"

# Drone configurations
declare -A DRONES=(
    ["drone_001"]="-1.2921,36.8219"
    ["drone_002"]="-1.2950,36.8250"
    ["drone_003"]="-1.2880,36.8180"
)

# Object classes for detection
OBJECT_CLASSES=("person" "car" "truck" "building" "tree" "animal" "bicycle" "motorcycle")

# Navigation actions
NAVIGATION_ACTIONS=("move_forward" "turn_left" "turn_right" "ascend" "descend" "hover" "land" "emergency_land")

# Generate random float
random_float() {
    local min=$1
    local max=$2
    echo "scale=2; $min + ($RANDOM / 32767) * ($max - $min)" | bc
}

# Generate random integer
random_int() {
    local min=$1
    local max=$2
    echo $((min + RANDOM % (max - min + 1)))
}

# Generate timestamp
generate_timestamp() {
    local minutes_ago=$1
    local timestamp=$(date -d "$minutes_ago minutes ago" +%s)000000000
    echo $timestamp
}

# Generate flight telemetry data
generate_flight_data() {
    print_header "Generating Flight Telemetry Data"
    
    local drone_id=$1
    local base_coords=$2
    local latitude=$(echo $base_coords | cut -d',' -f1)
    local longitude=$(echo $base_coords | cut -d',' -f2)
    
    print_status "Generating flight data for $drone_id"
    
    # Generate 100 data points over the last hour
    for i in {1..100}; do
        local minutes_ago=$((60 - i))
        local timestamp=$(generate_timestamp $minutes_ago)
        
        # Simulate drone movement
        local lat_offset=$(random_float -0.01 0.01)
        local lon_offset=$(random_float -0.01 0.01)
        local current_lat=$(echo "$latitude + $lat_offset" | bc)
        local current_lon=$(echo "$longitude + $lon_offset" | bc)
        
        # Generate realistic flight parameters
        local altitude=$(random_float 20 150)
        local speed=$(random_float 5 25)
        local heading=$(random_float 0 360)
        local vertical_speed=$(random_float -5 5)
        local ground_speed=$(random_float 0 30)
        
        # Flight status (mostly flying, occasional landed)
        local status="flying"
        if [ $((i % 20)) -eq 0 ]; then
            status="landed"
        fi
        
        # Insert data
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "flight_telemetry,drone_id=$drone_id,source_pc=PC1,flight_mode=auto latitude=$current_lat,longitude=$current_lon,altitude=$altitude,speed=$speed,heading=$heading,vertical_speed=$vertical_speed,ground_speed=$ground_speed,status=\"$status\" $timestamp" > /dev/null
        
        if [ $((i % 20)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""
    print_status "Flight telemetry data generated for $drone_id"
}

# Generate object detection data
generate_detection_data() {
    print_header "Generating Object Detection Data"
    
    local drone_id=$1
    
    print_status "Generating detection data for $drone_id"
    
    # Generate 50 detection events over the last hour
    for i in {1..50}; do
        local minutes_ago=$((60 - i * 2))
        local timestamp=$(generate_timestamp $minutes_ago)
        
        # Random object class
        local object_class=${OBJECT_CLASSES[$((RANDOM % ${#OBJECT_CLASSES[@]}))]}
        
        # Detection confidence (higher for some objects)
        local confidence
        case $object_class in
            "person"|"car"|"truck")
                confidence=$(random_float 0.7 0.95)
                ;;
            "building"|"tree")
                confidence=$(random_float 0.8 0.98)
                ;;
            *)
                confidence=$(random_float 0.5 0.85)
                ;;
        esac
        
        # Bounding box
        local bbox_x=$(random_int 50 300)
        local bbox_y=$(random_int 50 200)
        local bbox_width=$(random_int 30 100)
        local bbox_height=$(random_int 30 100)
        local area=$((bbox_width * bbox_height))
        
        # Insert data
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "object_detections,drone_id=$drone_id,source_pc=PC2,object_class=$object_class,confidence=$confidence bbox_x=$bbox_x,bbox_y=$bbox_y,bbox_width=$bbox_width,bbox_height=$bbox_height,area=$area $timestamp" > /dev/null
        
        if [ $((i % 10)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""
    print_status "Object detection data generated for $drone_id"
}

# Generate navigation telemetry data
generate_navigation_data() {
    print_header "Generating Navigation Telemetry Data"
    
    local drone_id=$1
    
    print_status "Generating navigation data for $drone_id"
    
    # Generate 30 navigation events over the last hour
    for i in {1..30}; do
        local minutes_ago=$((60 - i * 2))
        local timestamp=$(generate_timestamp $minutes_ago)
        
        # Navigation action
        local action=${NAVIGATION_ACTIONS[$((RANDOM % ${#NAVIGATION_ACTIONS[@]}))]}
        
        # Confidence and timing
        local confidence=$(random_float 0.6 0.95)
        local estimated_time=$(random_float 5 60)
        local path_length=$(random_int 1 10)
        local obstacles_detected=$(random_int 0 5)
        
        # Insert data
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "navigation_telemetry,drone_id=$drone_id,source_pc=PC2,action=$action next_action=\"$action\",confidence=$confidence,estimated_time=$estimated_time,path_length=$path_length,obstacles_detected=$obstacles_detected $timestamp" > /dev/null
        
        if [ $((i % 10)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""
    print_status "Navigation telemetry data generated for $drone_id"
}

# Generate system metrics data
generate_system_data() {
    print_header "Generating System Metrics Data"
    
    local drone_id=$1
    
    print_status "Generating system metrics for $drone_id"
    
    # Generate 120 system metric data points (every 30 seconds for 1 hour)
    for i in {1..120}; do
        local minutes_ago=$((60 - i / 2))
        local timestamp=$(generate_timestamp $minutes_ago)
        
        # Battery metrics (gradually decreasing)
        local battery_percentage=$(random_float 75 95)
        if [ $i -gt 60 ]; then
            battery_percentage=$(random_float 65 85)
        fi
        if [ $i -gt 100 ]; then
            battery_percentage=$(random_float 55 75)
        fi
        
        local battery_voltage=$(random_float 11.5 12.8)
        local battery_current=$(random_float 1.5 3.5)
        local battery_temperature=$(random_float 20 45)
        
        # System performance
        local cpu_usage=$(random_float 15 45)
        local memory_usage=$(random_float 30 60)
        local disk_usage=$(random_float 25 40)
        local temperature=$(random_float 35 65)
        
        # Network metrics
        local network_rx=$(random_int 1000 5000)
        local network_tx=$(random_int 500 2000)
        
        # Insert battery data
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "system_metrics,drone_id=$drone_id,source_pc=PC1,component=battery battery_percentage=$battery_percentage,battery_voltage=$battery_voltage,battery_current=$battery_current,battery_temperature=$battery_temperature $timestamp" > /dev/null
        
        # Insert performance data
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "system_metrics,drone_id=$drone_id,source_pc=PC1,component=performance cpu_usage=$cpu_usage,memory_usage=$memory_usage,disk_usage=$disk_usage,temperature=$temperature $timestamp" > /dev/null
        
        # Insert network data
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "system_metrics,drone_id=$drone_id,source_pc=PC1,component=network network_rx=$network_rx,network_tx=$network_tx $timestamp" > /dev/null
        
        if [ $((i % 20)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""
    print_status "System metrics data generated for $drone_id"
}

# Generate alerts
generate_alerts() {
    print_header "Generating Alert Data"
    
    local drone_id=$1
    
    print_status "Generating alerts for $drone_id"
    
    # Generate various alert types
    local alert_types=("battery_low" "high_cpu" "gps_signal_lost" "obstacle_detected" "navigation_error")
    local severities=("warning" "critical" "info" "warning" "critical")
    
    for i in {1..15}; do
        local minutes_ago=$((60 - i * 4))
        local timestamp=$(generate_timestamp $minutes_ago)
        
        local alert_index=$((RANDOM % ${#alert_types[@]}))
        local alert_type=${alert_types[$alert_index]}
        local severity=${severities[$alert_index]}
        
        # Alert messages
        local message
        case $alert_type in
            "battery_low")
                message="Battery level below 20%"
                ;;
            "high_cpu")
                message="CPU usage above 80%"
                ;;
            "gps_signal_lost")
                message="GPS signal lost for 30 seconds"
                ;;
            "obstacle_detected")
                message="Obstacle detected in flight path"
                ;;
            "navigation_error")
                message="Navigation system error"
                ;;
        esac
        
        # Threshold and actual values
        local threshold_value=$(random_float 15 25)
        local actual_value=$(random_float 10 30)
        local acknowledged=false
        
        # Insert alert
        curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: text/plain; charset=utf-8" \
            --data-binary "alerts,drone_id=$drone_id,source_pc=PC1,alert_type=$alert_type,severity=$severity message=\"$message\",threshold_value=$threshold_value,actual_value=$actual_value,acknowledged=$acknowledged $timestamp" > /dev/null
    done
    
    print_status "Alert data generated for $drone_id"
}

# Verify data generation
verify_data() {
    print_header "Verifying Generated Data"
    
    # Count data points
    local flight_count=$(curl -s -X POST "$INFLUXDB_URL/api/v2/query" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/vnd.flux" \
        --data "from(bucket:\"$BUCKET\") |> range(start: -2h) |> filter(fn: (r) => r._measurement == \"flight_telemetry\") |> count()" | \
        jq -r '.[0].data[0][1]' 2>/dev/null || echo "0")
    
    local detection_count=$(curl -s -X POST "$INFLUXDB_URL/api/v2/query" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/vnd.flux" \
        --data "from(bucket:\"$BUCKET\") |> range(start: -2h) |> filter(fn: (r) => r._measurement == \"object_detections\") |> count()" | \
        jq -r '.[0].data[0][1]' 2>/dev/null || echo "0")
    
    local system_count=$(curl -s -X POST "$INFLUXDB_URL/api/v2/query" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/vnd.flux" \
        --data "from(bucket:\"$BUCKET\") |> range(start: -2h) |> filter(fn: (r) => r._measurement == \"system_metrics\") |> count()" | \
        jq -r '.[0].data[0][1]' 2>/dev/null || echo "0")
    
    local alert_count=$(curl -s -X POST "$INFLUXDB_URL/api/v2/query" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/vnd.flux" \
        --data "from(bucket:\"$BUCKET\") |> range(start: -2h) |> filter(fn: (r) => r._measurement == \"alerts\") |> count()" | \
        jq -r '.[0].data[0][1]' 2>/dev/null || echo "0")
    
    print_status "Data Generation Summary:"
    echo "  Flight telemetry: $flight_count points"
    echo "  Object detections: $detection_count points"
    echo "  System metrics: $system_count points"
    echo "  Alerts: $alert_count points"
    
    local total=$((flight_count + detection_count + system_count + alert_count))
    print_status "Total data points generated: $total"
    
    if [ $total -gt 0 ]; then
        print_status "Data generation successful!"
    else
        print_error "No data generated - check InfluxDB connection"
    fi
}

# Main execution
main() {
    print_header "PC3 Test Data Generation"
    echo "Time: $(date)"
    echo ""
    
    # Check if InfluxDB is available
    if ! curl -s "$INFLUXDB_URL/health" > /dev/null; then
        print_error "InfluxDB is not available at $INFLUXDB_URL"
        print_status "Please start InfluxDB first: docker-compose up -d influxdb"
        exit 1
    fi
    
    # Generate data for each drone
    for drone_id in "${!DRONES[@]}"; do
        echo ""
        print_status "Processing $drone_id..."
        
        generate_flight_data "$drone_id" "${DRONES[$drone_id]}"
        generate_detection_data "$drone_id"
        generate_navigation_data "$drone_id"
        generate_system_data "$drone_id"
        generate_alerts "$drone_id"
        
        print_status "Data generation completed for $drone_id"
    done
    
    echo ""
    verify_data
    
    echo ""
    print_status "Test data generation completed!"
    echo ""
    print_status "You can now view the data in Grafana dashboards:"
    echo "  URL: http://localhost:3000"
    echo "  Username: admin"
    echo "  Password: admin123"
}

# Run data generation
main "$@"
