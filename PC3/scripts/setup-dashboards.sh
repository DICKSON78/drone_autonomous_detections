#!/bin/bash

# PC3 Dashboard Setup Script
# Creates Grafana dashboards and data source integration

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
GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="admin123"
INFLUXDB_URL="http://influxdb:8086"
INFLUXDB_ORG="drone-project"
INFLUXDB_BUCKET="drone_telemetry"
INFLUXDB_TOKEN="drone-telemetry-token"

# Wait for Grafana to be ready
wait_for_grafana() {
    print_header "Waiting for Grafana"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$GRAFANA_URL/api/health" > /dev/null; then
            print_status "Grafana is ready"
            return 0
        fi
        
        print_warning "Attempt $attempt/$max_attempts: Grafana not ready, waiting..."
        sleep 5
        ((attempt++))
    done
    
    print_error "Grafana failed to start after $max_attempts attempts"
    exit 1
}

# Create InfluxDB data source
create_datasource() {
    print_header "Creating InfluxDB Data Source"
    
    # Check if datasource already exists
    local existing_ds=$(curl -s -X GET "$GRAFANA_URL/api/datasources" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" | \
        jq -r '.[] | select(.name=="InfluxDB") | .name' 2>/dev/null || echo "")
    
    if [ "$existing_ds" = "InfluxDB" ]; then
        print_status "InfluxDB datasource already exists"
        return 0
    fi
    
    # Create datasource
    print_status "Creating InfluxDB datasource..."
    local response=$(curl -s -X POST "$GRAFANA_URL/api/datasources" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"InfluxDB\",
            \"type\": \"influxdb\",
            \"access\": \"proxy\",
            \"url\": \"$INFLUXDB_URL\",
            \"database\": \"$INFLUXDB_BUCKET\",
            \"user\": \"admin\",
            \"password\": \"admin123\",
            \"isDefault\": true,
            \"jsonData\": {
                \"version\": \"Flux\",
                \"organization\": \"$INFLUXDB_ORG\",
                \"defaultBucket\": \"$INFLUXDB_BUCKET\",
                \"httpMode\": \"POST\"
            },
            \"secureJsonData\": {}
        }")
    
    if echo "$response" | grep -q "Datasource added"; then
        print_status "InfluxDB datasource created successfully"
    else
        print_error "Failed to create InfluxDB datasource"
        echo "$response"
        exit 1
    fi
}

# Create flight dashboard
create_flight_dashboard() {
    print_header "Creating Flight Dashboard"
    
    local dashboard_json='{
        "dashboard": {
            "id": null,
            "title": "Drone Flight Status",
            "tags": ["drone", "flight", "telemetry"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "5s",
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "GPS Position",
                    "type": "stat",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 0,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "A",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"flight_telemetry\")\n  |> filter(fn: (r) => r._field == \"latitude\" or r._field == \"longitude\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "location",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Altitude",
                    "type": "gauge",
                    "gridPos": {
                        "h": 8,
                        "w": 6,
                        "x": 12,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "B",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"flight_telemetry\")\n  |> filter(fn: (r) => r._field == \"altitude\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "m",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 100},
                                    {"color": "red", "value": 200}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "Speed",
                    "type": "gauge",
                    "gridPos": {
                        "h": 8,
                        "w": 6,
                        "x": 18,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "C",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"flight_telemetry\")\n  |> filter(fn: (r) => r._field == \"speed\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "m/s",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 20},
                                    {"color": "red", "value": 30}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 4,
                    "title": "Flight Status",
                    "type": "stat",
                    "gridPos": {
                        "h": 4,
                        "w": 12,
                        "x": 12,
                        "y": 8
                    },
                    "targets": [
                        {
                            "refId": "D",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"flight_telemetry\")\n  |> filter(fn: (r) => r._field == \"status\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [
                                {
                                    "options": {
                                        "flying": {"color": "green", "index": 0, "text": "Flying"},
                                        "landed": {"color": "blue", "index": 1, "text": "Landed"},
                                        "emergency": {"color": "red", "index": 2, "text": "Emergency"}
                                    },
                                    "type": "value"
                                }
                            ]
                        }
                    }
                }
            ]
        },
        "overwrite": false
    }'
    
    local response=$(curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" \
        -d "$dashboard_json")
    
    if echo "$response" | grep -q "success"; then
        print_status "Flight dashboard created successfully"
    else
        print_error "Failed to create flight dashboard"
        echo "$response"
    fi
}

# Create system dashboard
create_system_dashboard() {
    print_header "Creating System Dashboard"
    
    local dashboard_json='{
        "dashboard": {
            "id": null,
            "title": "System Performance",
            "tags": ["drone", "system", "performance"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "10s",
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Battery Level",
                    "type": "gauge",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 0,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "A",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"system_metrics\")\n  |> filter(fn: (r) => r._field == \"battery_percentage\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 20},
                                    {"color": "red", "value": 10}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "CPU Usage",
                    "type": "graph",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 12,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "B",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"system_metrics\")\n  |> filter(fn: (r) => r._field == \"cpu_usage\")\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 70},
                                    {"color": "red", "value": 85}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "Memory Usage",
                    "type": "graph",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 0,
                        "y": 8
                    },
                    "targets": [
                        {
                            "refId": "C",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"system_metrics\")\n  |> filter(fn: (r) => r._field == \"memory_usage\")\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 70},
                                    {"color": "red", "value": 85}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 4,
                    "title": "Disk Usage",
                    "type": "graph",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 12,
                        "y": 8
                    },
                    "targets": [
                        {
                            "refId": "D",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"system_metrics\")\n  |> filter(fn: (r) => r._field == \"disk_usage\")\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 80},
                                    {"color": "red", "value": 90}
                                ]
                            }
                        }
                    }
                }
            ]
        },
        "overwrite": false
    }'
    
    local response=$(curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" \
        -d "$dashboard_json")
    
    if echo "$response" | grep -q "success"; then
        print_status "System dashboard created successfully"
    else
        print_error "Failed to create system dashboard"
        echo "$response"
    fi
}

# Create detection dashboard
create_detection_dashboard() {
    print_header "Creating Detection Dashboard"
    
    local dashboard_json='{
        "dashboard": {
            "id": null,
            "title": "Object Detection Analytics",
            "tags": ["drone", "detection", "vision"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "5s",
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Detection Count",
                    "type": "stat",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 0,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "A",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"object_detections\")\n  |> count()\n  |> yield(key: \"detection_count\", value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null},
                                    {"color": "yellow", "value": 5},
                                    {"color": "red", "value": 10}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Detection Confidence",
                    "type": "heatmap",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 12,
                        "y": 0
                    },
                    "targets": [
                        {
                            "refId": "B",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"object_detections\")\n  |> filter(fn: (r) => r._field == \"confidence\")\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "steps": [
                                    {"color": "blue", "value": null},
                                    {"color": "green", "value": 0.5},
                                    {"color": "yellow", "value": 0.8},
                                    {"color": "red", "value": 0.9}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "Object Classes",
                    "type": "piechart",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 0,
                        "y": 8
                    },
                    "targets": [
                        {
                            "refId": "C",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"object_detections\")\n  |> group(columns: [\"object_class\"])\n  |> count()\n  |> yield(key: \"object_class\", value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ]
                },
                {
                    "id": 4,
                    "title": "Detection Timeline",
                    "type": "timeseries",
                    "gridPos": {
                        "h": 8,
                        "w": 12,
                        "x": 12,
                        "y": 8
                    },
                    "targets": [
                        {
                            "refId": "D",
                            "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"object_detections\")\n  |> filter(fn: (r) => r._field == \"confidence\")\n  |> yield(key: r._field, value: r._value)",
                            "datasource": {
                                "type": "influxdb",
                                "uid": "InfluxDB"
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": null}
                                ]
                            }
                        }
                    }
                }
            ]
        },
        "overwrite": false
    }'
    
    local response=$(curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" \
        -d "$dashboard_json")
    
    if echo "$response" | grep -q "success"; then
        print_status "Detection dashboard created successfully"
    else
        print_error "Failed to create detection dashboard"
        echo "$response"
    fi
}

# Create alert rules
create_alert_rules() {
    print_header "Creating Alert Rules"
    
    # Low battery alert
    local battery_alert='{
        "name": "Low Battery Alert",
        "folderId": 1,
        "ruleGroup": "Drone Alerts",
        "for": "5m",
        "labels": {
            "severity": "warning",
            "service": "drone"
        },
        "annotations": {
            "summary": "Drone battery is below 20%",
            "description": "Drone {{ .Labels.drone_id }} battery level is {{ .Values.A }}%"
        },
        "condition": "A",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {
                    "from": 300,
                    "to": 0
                },
                "datasourceUid": "InfluxDB",
                "model": {
                    "expr": "from(bucket: \"drone_telemetry\")\n  |> range($range)\n  |> filter(fn: (r) => r._measurement == \"system_metrics\")\n  |> filter(fn: (r) => r._field == \"battery_percentage\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
                    "refId": "A",
                    "hide": false,
                    "type": "time_series_query"
                },
                "datasource": {
                    "type": "influxdb",
                    "uid": "InfluxDB"
                },
                "reduce": {
                    "reducer": "lastNotNull",
                    "type": "reduce"
                },
                "thresholds": [
                    {
                        "value": 20,
                        "color": "red",
                        "op": "lt"
                    }
                ]
            }
        ],
        "noDataState": "NoData",
        "execErrState": "Alerting",
        "for": "5m"
    }'
    
    local response=$(curl -s -X POST "$GRAFANA_URL/api/provisioning/alert-rules" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" \
        -d "$battery_alert")
    
    if echo "$response" | grep -q "id"; then
        print_status "Battery alert rule created successfully"
    else
        print_warning "Failed to create battery alert rule"
    fi
}

# Verify dashboard setup
verify_setup() {
    print_header "Verifying Dashboard Setup"
    
    # Check datasource
    local ds_check=$(curl -s -X GET "$GRAFANA_URL/api/datasources" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" | \
        jq -r '.[] | select(.name=="InfluxDB") | .name' 2>/dev/null || echo "")
    
    if [ "$ds_check" = "InfluxDB" ]; then
        print_status "InfluxDB datasource verified"
    else
        print_error "InfluxDB datasource not found"
    fi
    
    # Check dashboards
    local dashboard_count=$(curl -s -X GET "$GRAFANA_URL/api/search" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" | \
        jq '. | length' 2>/dev/null || echo "0")
    
    print_status "$dashboard_count dashboards found"
    
    # Test dashboard access
    local dashboards=$(curl -s -X GET "$GRAFANA_URL/api/search" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" | \
        jq -r '.[].title' 2>/dev/null || echo "")
    
    if echo "$dashboards" | grep -q "Drone Flight Status"; then
        print_status "Flight dashboard accessible"
    fi
    
    if echo "$dashboards" | grep -q "System Performance"; then
        print_status "System dashboard accessible"
    fi
    
    if echo "$dashboards" | grep -q "Object Detection Analytics"; then
        print_status "Detection dashboard accessible"
    fi
    
    print_status "Dashboard setup verification completed"
}

# Main execution
main() {
    print_header "PC3 Dashboard Setup"
    echo "Time: $(date)"
    echo ""
    
    wait_for_grafana
    create_datasource
    create_flight_dashboard
    create_system_dashboard
    create_detection_dashboard
    create_alert_rules
    verify_setup
    
    echo ""
    print_status "Dashboard setup completed!"
    echo ""
    echo "Access Information:"
    echo "  Grafana URL: $GRAFANA_URL"
    echo "  Username: $GRAFANA_USER"
    echo "  Password: $GRAFANA_PASSWORD"
    echo ""
    print_status "Dashboards are ready for use"
}

# Run dashboard setup
main "$@"
