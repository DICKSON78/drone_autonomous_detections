# PC3 Data & Monitoring - Complete Integration Guide

## Overview

PC3 provides the data collection, storage, and visualization layer for the autonomous drone system. It integrates InfluxDB (time-series database), Grafana (dashboards), and a Telemetry Collector service.

## Architecture

```
PC1 (Command & Control)     PC2 (Vision & Navigation)     PC3 (Data & Monitoring)
     |                              |                              |
     +------------------------------+------------------------------+
     |                              |                              |
Kafka Topics (drone.telemetry.*)  |                              |
     |                              |                              |
     +------------------------------+------------------------------+
     |                              |                              |
Telemetry Collector (PC3) ----> InfluxDB (PC3) ----> Grafana (PC3)
     |                              |                              |
     +------------------------------+------------------------------+
     |                              |                              |
Real-time Dashboards & Analytics  |                              |
```

## Services

| Service | Port | Purpose | Technology |
|---------|------|---------|------------|
| Telemetry Collector | 8004 | Kafka consumer & data processor | FastAPI + Python |
| InfluxDB | 8086 | Time-series database | InfluxDB 2.7 |
| Grafana | 3000 | Visualization dashboards | Grafana 10.2.0 |

## Quick Start (10 Minutes)

### Prerequisites
```bash
# Check Docker installation
docker --version
docker-compose --version

# Minimum system requirements
# - 4GB RAM
# - 10GB disk space
# - Network access to PC1 and PC2
```

### Step 1: Setup Environment
```bash
# Navigate to PC3 directory
cd /home/dickson/FYP/drone_autonomous/PC3

# Make scripts executable
chmod +x scripts/setup.sh
chmod +x scripts/health-check.sh
chmod +x scripts/monitor.sh
```

### Step 2: Run Setup Script
```bash
# Complete automated setup
./scripts/setup.sh
```

The setup script will:
- Create necessary directories
- Build Docker images
- Start services in correct order
- Verify service health
- Display access information

### Step 3: Verify Integration
```bash
# Check service status
docker-compose ps

# Run health check
./scripts/health-check.sh

# Test endpoints
curl http://localhost:8004/health    # Telemetry Collector
curl http://localhost:8086/health     # InfluxDB
curl http://localhost:3000/api/health # Grafana
```

## Service Access

### Grafana Dashboard
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin123
- **Features**: Real-time dashboards, alerts, data visualization

### InfluxDB Database
- **URL**: http://localhost:8086
- **Organization**: drone-project
- **Bucket**: drone_telemetry
- **Token**: drone-telemetry-token
- **CLI Access**: `docker exec -it influxdb influx`

### Telemetry Collector API
- **URL**: http://localhost:8004
- **Health**: http://localhost:8004/health
- **Status**: http://localhost:8004/status
- **Metrics**: http://localhost:8004/metrics

## Data Flow Integration

### Kafka Topics Consumed
```
drone.telemetry.flight      -> Flight telemetry (GPS, altitude, speed)
drone.telemetry.detections  -> Object detection results
drone.telemetry.navigation  -> Navigation telemetry
drone.alerts.system        -> System alerts and metrics
```

### InfluxDB Schema
```
Measurements:
- flight_telemetry (latitude, longitude, altitude, speed, heading)
- object_detections (confidence, bbox, object_class)
- navigation_telemetry (next_action, confidence, path_length)
- system_metrics (battery_percentage, cpu_usage, memory_usage)
- alerts (alert_type, severity, message)
```

### Grafana Dashboards
1. **Drone System Overview** - Main status dashboard
2. **Flight Analytics** - GPS tracking and flight metrics
3. **Object Detection** - Detection frequency and confidence
4. **System Performance** - Resource usage and health
5. **Alert Management** - System alerts and notifications

## Monitoring & Management

### Health Monitoring
```bash
# Real-time health check
./scripts/health-check.sh

# Interactive monitoring
./scripts/monitor.sh

# View specific logs
docker-compose logs -f telemetry-collector
docker-compose logs -f influxdb
docker-compose logs -f grafana
```

### Service Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart telemetry-collector

# Rebuild service
docker-compose up -d --build telemetry-collector
```

### Performance Monitoring
```bash
# Resource usage
docker stats

# Disk usage
docker system df

# Database size
docker exec influxdb du -sh /var/lib/influxdb2/
```

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check what's using ports
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :8086
sudo netstat -tulpn | grep :8004

# Kill conflicting processes
sudo kill -9 [PID]

# Restart services
docker-compose down && docker-compose up -d
```

#### 2. Grafana Won't Connect to InfluxDB
```bash
# Check InfluxDB status
curl http://localhost:8086/health

# Check Grafana configuration
docker exec grafana cat /etc/grafana/provisioning/datasources/influxdb.yml

# Restart Grafana
docker-compose restart grafana
```

#### 3. No Data in Dashboards
```bash
# Check if data is being received
docker logs telemetry-collector | grep "Processed"

# Check InfluxDB for data
curl -X GET "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: application/vnd.flux" \
  --data 'from(bucket:"drone_telemetry") |> range(start: -1h) |> limit(n:10)'

# Manually insert test data
curl -X POST 'http://localhost:8086/api/v2/write?bucket=drone_telemetry&org=drone-project' \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: text/plain; charset=utf-8" \
  --data-binary 'flight_telemetry,drone_id=test latitude=-1.2921,longitude=36.8219,altitude=50.0'
```

#### 4. High Memory Usage
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

## Integration with Other PCs

### Network Configuration
```yaml
# Update PC1 and PC2 configurations to point to PC3
PC1_KAFKA_BOOTSTRAP_SERVERS: "PC3:9092"
PC2_KAFKA_BOOTSTRAP_SERVERS: "PC3:9092"
```

### Data Validation
```bash
# Test data flow from PC1
curl -X POST http://localhost:8004/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2024-01-01T00:00:00Z",
    "drone_id": "test_drone",
    "source_pc": "PC1",
    "data_type": "flight",
    "measurements": {
      "latitude": -1.2921,
      "longitude": 36.8219,
      "altitude": 50.0
    }
  }'
```

## Advanced Configuration

### Custom Dashboards
1. Open Grafana: http://localhost:3000
2. Click + > Dashboard
3. Add panels with InfluxDB queries
4. Save dashboard

### Alert Configuration
```bash
# Configure alerts in Grafana
# Navigate to Alerting > New Alert Rule
# Set conditions for battery, altitude, etc.
```

### Database Retention
```bash
# Modify retention policies
docker exec -it influxdb influx
> create retention policy "30days" on "drone_telemetry" duration 30d replication 1 default
```

## Performance Optimization

### InfluxDB Tuning
```yaml
# In config/influxdb_config.yaml
influxdb:
  batch_size: 1000
  flush_interval: 1000
  max_series_per_database: 1000000
```

### Grafana Optimization
```yaml
# In grafana/grafana.ini
[database]
max_idle_conn = 10
max_open_conn = 100
conn_max_lifetime = 14400
```

## Backup & Recovery

### Data Backup
```bash
# Backup InfluxDB data
docker exec influxdb influx backup /tmp/backup
docker cp influxdb:/tmp/backup ./backup-$(date +%Y%m%d)

# Backup Grafana configuration
docker exec grafana tar -czf /tmp/grafana-backup.tar.gz /etc/grafana
docker cp grafana:/tmp/grafana-backup.tar.gz ./grafana-backup-$(date +%Y%m%d).tar.gz
```

### Data Recovery
```bash
# Restore InfluxDB
docker cp ./backup-20240101 influxdb:/tmp/
docker exec influxdb influx restore /tmp/backup-20240101

# Restore Grafana
docker cp ./grafana-backup-20240101.tar.gz grafana:/tmp/
docker exec grafana tar -xzf /tmp/grafana-backup-20240101.tar.gz -C /
```

## Success Indicators

Your PC3 integration is successful when:
- [ ] All 3 services are running and healthy
- [ ] Grafana connects to InfluxDB successfully
- [ ] Dashboards display real-time data
- [ ] Health endpoints return "healthy" status
- [ ] Data flows from PC1 and PC2 via Kafka
- [ ] Alerts and notifications work correctly
- [ ] Team can access analytics from PC4

## Support

For issues:
1. Check logs: `docker-compose logs -f [service]`
2. Run health check: `./scripts/health-check.sh`
3. Verify network connectivity
4. Check system resources

## Next Steps

Once PC3 is integrated:
1. Configure custom dashboards for specific metrics
2. Set up alert rules for critical events
3. Analyze historical data patterns
4. Export reports for team analysis
5. Optimize performance based on usage patterns

**PC3 Data & Monitoring is now ready to serve as the brain of your autonomous drone system!**
