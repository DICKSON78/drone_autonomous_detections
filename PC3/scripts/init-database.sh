#!/bin/bash

# PC3 Database Initialization Script
# Creates InfluxDB database, schemas, and initial data

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

# Wait for InfluxDB to be ready
wait_for_influxdb() {
    print_header "Waiting for InfluxDB"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$INFLUXDB_URL/health" > /dev/null; then
            print_status "InfluxDB is ready"
            return 0
        fi
        
        print_warning "Attempt $attempt/$max_attempts: InfluxDB not ready, waiting..."
        sleep 5
        ((attempt++))
    done
    
    print_error "InfluxDB failed to start after $max_attempts attempts"
    exit 1
}

# Create organization and bucket
create_organization_bucket() {
    print_header "Creating Organization and Bucket"
    
    # Check if organization exists
    if curl -s -X GET "$INFLUXDB_URL/api/v2/orgs" \
        -H "Authorization: Token $TOKEN" \
        -H "Accept: application/json" | grep -q "$ORG"; then
        print_status "Organization '$ORG' already exists"
    else
        print_status "Creating organization '$ORG'..."
        curl -s -X POST "$INFLUXDB_URL/api/v2/orgs" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"$ORG\"}" > /dev/null
        print_status "Organization created"
    fi
    
    # Check if bucket exists
    if curl -s -X GET "$INFLUXDB_URL/api/v2/buckets" \
        -H "Authorization: Token $TOKEN" \
        -H "Accept: application/json" | grep -q "$BUCKET"; then
        print_status "Bucket '$BUCKET' already exists"
    else
        print_status "Creating bucket '$BUCKET'..."
        curl -s -X POST "$INFLUXDB_URL/api/v2/buckets" \
            -H "Authorization: Token $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"org\":\"$ORG\",\"name\":\"$BUCKET\",\"retentionRules\":[{\"type\":\"expire\",\"everySeconds\":2592000}]}" > /dev/null
        print_status "Bucket created"
    fi
}

# Create retention policies
create_retention_policies() {
    print_header "Creating Retention Policies"
    
    # High-frequency data (7 days)
    print_status "Creating high-frequency retention policy..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/buckets" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"org\":\"$ORG\",\"name\":\"drone_telemetry_high_freq\",\"retentionRules\":[{\"type\":\"expire\",\"everySeconds\":604800}]}" > /dev/null
    
    # Medium-frequency data (30 days)
    print_status "Creating medium-frequency retention policy..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/buckets" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"org\":\"$ORG\",\"name\":\"drone_telemetry_medium_freq\",\"retentionRules\":[{\"type\":\"expire\",\"everySeconds\":2592000}]}" > /dev/null
    
    # Low-frequency data (90 days)
    print_status "Creating low-frequency retention policy..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/buckets" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"org\":\"$ORG\",\"name\":\"drone_telemetry_low_freq\",\"retentionRules\":[{\"type\":\"expire\",\"everySeconds\":7776000}]}" > /dev/null
    
    print_status "Retention policies created"
}

# Insert sample data for testing
insert_sample_data() {
    print_header "Inserting Sample Data"
    
    # Flight telemetry sample data
    print_status "Inserting flight telemetry data..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'flight_telemetry,drone_id=drone_001,source_pc=PC1 latitude=-1.2921,longitude=36.8219,altitude=50.5,speed=15.2,heading=90.0,status=flying 1640995200000000000' > /dev/null
    
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'flight_telemetry,drone_id=drone_001,source_pc=PC1 latitude=-1.2925,longitude=36.8225,altitude=55.0,speed=14.8,heading=95.0,status=flying 1640995260000000000' > /dev/null
    
    # Object detection sample data
    print_status "Inserting object detection data..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'object_detections,drone_id=drone_001,source_pc=PC2,object_class=person,confidence=0.85 bbox_x=100,bbox_y=150,bbox_width=50,bbox_height=100 1640995200000000000' > /dev/null
    
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'object_detections,drone_id=drone_001,source_pc=PC2,object_class=car,confidence=0.92 bbox_x=200,bbox_y=180,bbox_width=80,bbox_height=60 1640995260000000000' > /dev/null
    
    # Navigation telemetry sample data
    print_status "Inserting navigation telemetry data..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'navigation_telemetry,drone_id=drone_001,source_pc=PC2 next_action="move_forward",confidence=0.88,estimated_time=15.5,path_length=3 1640995200000000000' > /dev/null
    
    # System metrics sample data
    print_status "Inserting system metrics data..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'system_metrics,drone_id=drone_001,source_pc=PC1,component=battery battery_percentage=85.2,battery_voltage=12.6,battery_current=2.1 1640995200000000000' > /dev/null
    
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'system_metrics,drone_id=drone_001,source_pc=PC1,component=cpu cpu_usage=25.5,memory_usage=45.8,disk_usage=35.2 1640995200000000000' > /dev/null
    
    # Alerts sample data
    print_status "Inserting alerts data..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/write?bucket=$BUCKET&org=$ORG" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: text/plain; charset=utf-8" \
        --data-binary 'alerts,drone_id=drone_001,source_pc=PC1,alert_type=battery_low,severity=warning message="Battery level below 20%",threshold_value=20.0,actual_value=18.5,acknowledged=false 1640995200000000000' > /dev/null
    
    print_status "Sample data inserted successfully"
}

# Create database indexes
create_indexes() {
    print_header "Creating Database Indexes"
    
    # Create indexes for common queries
    print_status "Creating indexes for drone_id..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/queries" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"CREATE INDEX ON drone_id\",\"org\":\"$ORG\"}" > /dev/null
    
    print_status "Creating indexes for timestamp..."
    curl -s -X POST "$INFLUXDB_URL/api/v2/queries" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"CREATE INDEX ON time\",\"org\":\"$ORG\"}" > /dev/null
    
    print_status "Database indexes created"
}

# Verify database setup
verify_setup() {
    print_header "Verifying Database Setup"
    
    # Check if data exists
    local data_count=$(curl -s -X POST "$INFLUXDB_URL/api/v2/query" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/vnd.flux" \
        --data "from(bucket:\"$BUCKET\") |> range(start: -1h) |> count()" | \
        jq -r '.[0].data[0][1]' 2>/dev/null || echo "0")
    
    if [ "$data_count" -gt 0 ]; then
        print_status "Database setup verified - $data_count data points found"
    else
        print_warning "No data found in database - this may be normal if services haven't started yet"
    fi
    
    # Test query
    print_status "Testing query performance..."
    local query_time=$(curl -s -X POST "$INFLUXDB_URL/api/v2/query" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/vnd.flux" \
        --data "from(bucket:\"$BUCKET\") |> range(start: -1h) |> limit(n: 10)" | \
        jq -r '.[0].data[0][0]' 2>/dev/null || echo "Query failed")
    
    print_status "Database setup completed successfully"
}

# Main execution
main() {
    print_header "PC3 Database Initialization"
    echo "Time: $(date)"
    echo ""
    
    wait_for_influxdb
    create_organization_bucket
    create_retention_policies
    insert_sample_data
    create_indexes
    verify_setup
    
    echo ""
    print_status "Database initialization completed!"
    echo ""
    echo "Database Details:"
    echo "  URL: $INFLUXDB_URL"
    echo "  Organization: $ORG"
    echo "  Bucket: $BUCKET"
    echo "  Token: $TOKEN"
    echo ""
    print_status "You can now start the Grafana dashboard integration"
}

# Run database initialization
main "$@"
