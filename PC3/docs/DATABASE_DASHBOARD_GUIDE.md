# PC3 Database & Dashboard Integration Guide

## Overview

This guide covers the complete setup of InfluxDB database and Grafana dashboards for the PC3 Data & Monitoring system. The integration provides real-time data collection, storage, and visualization for the autonomous drone system.

## Architecture

```
Telemetry Collector (Port 8004)
        |
        v
InfluxDB Database (Port 8086)
        |
        v
Grafana Dashboards (Port 3000)
```

## Database Schema

### Measurements and Fields

| Measurement | Fields | Tags | Description |
|-------------|--------|------|-------------|
| `flight_telemetry` | latitude, longitude, altitude, speed, heading, vertical_speed, ground_speed, status | drone_id, source_pc, flight_mode | Real-time flight data |
| `object_detections` | confidence, bbox_x, bbox_y, bbox_width, bbox_height, area | drone_id, source_pc, object_class, detection_id | Vision system detections |
| `navigation_telemetry` | next_action, confidence, estimated_time, path_length, obstacles_detected | drone_id, source_pc, navigation_mode | Navigation system data |
| `system_metrics` | battery_percentage, battery_voltage, battery_current, battery_temperature, cpu_usage, memory_usage, disk_usage, temperature | drone_id, source_pc, component | System performance metrics |
| `alerts` | message, threshold_value, actual_value, acknowledged | drone_id, source_pc, alert_type, severity | System alerts and notifications |

## Quick Setup (15 Minutes)

### Step 1: Initialize Database
```bash
# Navigate to PC3 directory
cd /home/dickson/FYP/drone_autonomous/PC3

# Make scripts executable
chmod +x scripts/init-database.sh
chmod +x scripts/setup-dashboards.sh
chmod +x scripts/generate-test-data.sh

# Start services
docker-compose up -d

# Initialize database
./scripts/init-database.sh
```

### Step 2: Setup Dashboards
```bash
# Wait for services to be ready (30 seconds)
sleep 30

# Setup Grafana dashboards
./scripts/setup-dashboards.sh
```

### Step 3: Generate Test Data
```bash
# Generate realistic test data
./scripts/generate-test-data.sh
```

### Step 4: Access Dashboards
```bash
# Open Grafana in browser
# URL: http://localhost:3000
# Username: admin
# Password: admin123
```

## Database Configuration

### InfluxDB Settings
- **Organization**: drone-project
- **Bucket**: drone_telemetry
- **Token**: drone-telemetry-token
- **Retention Policy**: 30 days (default)

### Database Initialization
The `init-database.sh` script creates:
- Organization and bucket
- Retention policies (7, 30, 90 days)
- Sample data for testing
- Database indexes for performance

### Data Flow
```
PC1/PC2 Services -> Kafka Topics -> Telemetry Collector -> InfluxDB -> Grafana
```

## Dashboard Configuration

### Available Dashboards

#### 1. Drone Flight Status
- **GPS Position**: Real-time location tracking
- **Altitude**: Current altitude gauge
- **Speed**: Ground speed indicator
- **Flight Status**: Current flight mode

#### 2. System Performance
- **Battery Level**: Real-time battery percentage
- **CPU Usage**: System CPU utilization
- **Memory Usage**: RAM consumption
- **Disk Usage**: Storage utilization

#### 3. Object Detection Analytics
- **Detection Count**: Total detections
- **Detection Confidence**: Confidence heatmap
- **Object Classes**: Detection by type
- **Detection Timeline**: Time-based detection graph

### Dashboard Features
- **Real-time updates** every 5 seconds
- **Interactive panels** with drill-down capabilities
- **Alert thresholds** with visual indicators
- **Historical data** analysis
- **Export capabilities** for reports

## Data Management

### Data Collection
The Telemetry Collector service automatically:
- Consumes data from Kafka topics
- Processes and validates data
- Writes to InfluxDB with proper tagging
- Handles errors and retries

### Data Retention
- **High-frequency data**: 7 days
- **Medium-frequency data**: 30 days
- **Low-frequency data**: 90 days
- **Alerts**: 90 days

### Data Backup
```bash
# Backup database
docker exec influxdb influx backup /tmp/backup
docker cp influxdb:/tmp/backup ./backup-$(date +%Y%m%d)

# Restore database
docker cp ./backup-20240101 influxdb:/tmp/
docker exec influxdb influx restore /tmp/backup-20240101
```

## Monitoring & Maintenance

### Health Checks
```bash
# Check database health
curl http://localhost:8086/health

# Check Grafana health
curl http://localhost:3000/api/health

# Check telemetry collector
curl http://localhost:8004/health
```

### Performance Monitoring
```bash
# Database performance
curl -X POST "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: application/vnd.flux" \
  --data 'from(bucket:"drone_telemetry") |> range(start: -1h) |> count()'

# Grafana metrics
curl -u admin:admin123 http://localhost:3000/api/health
```

### Log Monitoring
```bash
# View telemetry logs
docker-compose logs -f telemetry-collector

# View database logs
docker-compose logs -f influxdb

# View Grafana logs
docker-compose logs -f grafana
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check if InfluxDB is running
docker-compose ps influxdb

# Check network connectivity
docker exec telemetry-collector ping influxdb

# Test database access
curl -X GET "http://localhost:8086/api/v2/buckets" \
  -H "Authorization: Token drone-telemetry-token"
```

#### 2. Dashboard Not Showing Data
```bash
# Check if data exists
curl -X POST "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: application/vnd.flux" \
  --data 'from(bucket:"drone_telemetry") |> range(start: -1h) |> limit(n:10)'

# Check Grafana datasource
curl -u admin:admin123 http://localhost:3000/api/datasources

# Regenerate test data
./scripts/generate-test-data.sh
```

#### 3. High Memory Usage
```bash
# Check resource usage
docker stats

# Clean old data
docker exec influxdb influx delete \
  --bucket drone_telemetry \
  --start '1970-01-01T00:00:00Z' \
  --stop '2024-01-01T00:00:00Z' \
  --predicate '_measurement="*"'

# Restart services
docker-compose restart
```

#### 4. Dashboard Errors
```bash
# Check Grafana logs for errors
docker-compose logs grafana | grep -i error

# Recreate dashboards
./scripts/setup-dashboards.sh

# Clear Grafana cache
docker-compose restart grafana
```

## Advanced Configuration

### Custom Queries

#### Flight Path Analysis
```flux
// Flight path over last hour
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "flight_telemetry")
  |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude")
  |> aggregateWindow(every: 1m, fn: mean)
```

#### Battery Performance
```flux
// Battery percentage trend
from(bucket: "drone_telemetry")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r._field == "battery_percentage")
  |> filter(fn: (r) => r.component == "battery")
  |> aggregateWindow(every: 5m, fn: mean)
```

#### Detection Frequency
```flux
// Detection count by object class
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "object_detections")
  |> group(columns: ["object_class"])
  |> count()
```

### Alert Configuration

#### Battery Alert
```json
{
  "name": "Low Battery Alert",
  "condition": "A",
  "data": [
    {
      "refId": "A",
      "queryType": "",
      "datasourceUid": "InfluxDB",
      "model": {
        "expr": "from(bucket: \"drone_telemetry\") |> range($range) |> filter(fn: (r) => r._measurement == \"system_metrics\") |> filter(fn: (r) => r._field == \"battery_percentage\") |> last()",
        "thresholds": [
          {"value": 20, "color": "red", "op": "lt"}
        ]
      }
    }
  ],
  "for": "5m"
}
```

#### GPS Signal Alert
```json
{
  "name": "GPS Signal Lost",
  "condition": "A",
  "data": [
    {
      "refId": "A",
      "queryType": "",
      "datasourceUid": "InfluxDB",
      "model": {
        "expr": "from(bucket: \"drone_telemetry\") |> range($range) |> filter(fn: (r) => r._measurement == \"flight_telemetry\") |> filter(fn: (r) => r._field == \"latitude\") |> last()",
        "thresholds": [
          {"value": 0, "color": "red", "op": "eq"}
        ]
      }
    }
  ],
  "for": "30s"
}
```

## Performance Optimization

### Database Optimization
```yaml
# In influxdb_config.yaml
influxdb:
  batch_size: 1000
  flush_interval: 1000
  max_series_per_database: 1000000
  max_values_per_tag: 100000
```

### Grafana Optimization
```ini
# In grafana.ini
[database]
max_idle_conn = 10
max_open_conn = 100
conn_max_lifetime = 14400

[query]
max_concurrent_queries = 10
timeout = 60
```

### Query Optimization
- Use appropriate time ranges
- Filter by tags before fields
- Use aggregate functions for large datasets
- Create indexes for common queries

## Security Configuration

### Database Security
```yaml
# Enable authentication
influxdb:
  auth:
    enabled: true
    token_rotation_days: 90
  
  # Network security
  network:
    enable_tls: false
    allowed_networks: ["0.0.0.0/0"]
```

### Grafana Security
```ini
# Authentication
[auth.basic]
enabled = true

[auth.anonymous]
enabled = false

# Session management
[security]
disable_initial_admin_creation = false
admin_user = admin
admin_password = admin123
```

## Integration Testing

### Test Data Generation
The `generate-test-data.sh` script creates:
- Realistic flight telemetry for 3 drones
- Object detection data with various classes
- Navigation telemetry with different actions
- System metrics with performance data
- Alerts with different severities

### Verification Commands
```bash
# Verify data points
curl -X POST "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: application/vnd.flux" \
  --data 'from(bucket:"drone_telemetry") |> range(start: -1h) |> count()'

# Verify dashboards
curl -u admin:admin123 http://localhost:3000/api/search | jq '.[].title'

# Verify data sources
curl -u admin:admin123 http://localhost:3000/api/datasources | jq '.[].name'
```

## Success Indicators

Your database and dashboard integration is successful when:
- [ ] InfluxDB is running and healthy
- [ ] Grafana connects to InfluxDB successfully
- [ ] All dashboards display data
- [ ] Real-time updates work correctly
- [ ] Alert rules are configured
- [ ] Test data appears in dashboards
- [ ] Queries return expected results
- [ ] Performance is acceptable (<2s query time)

## Next Steps

Once integration is complete:
1. **Customize dashboards** for specific metrics
2. **Set up alert notifications** (email, Slack)
3. **Configure data retention** policies
4. **Implement backup procedures**
5. **Monitor performance** and optimize queries
6. **Train users** on dashboard usage

## Support

For database and dashboard issues:
1. Check service logs
2. Verify network connectivity
3. Test database queries
4. Check Grafana configuration
5. Review data schema

**PC3 Database & Dashboard integration is now ready for production use!**
