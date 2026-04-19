# PC3: Data & Monitoring

## Your Role
You are the Data & Monitoring Engineer! You are the brain of drone data.

### What You Do:
- **Collect everything** - GPS, battery, altitude, detections, commands
- **Store data smartly** - InfluxDB time-series database
- **Show insights** - Grafana dashboards with beautiful graphs

## Services You'll Run

```
Telemetry Collector      (Port 8004)
InfluxDB Database        (Port 8086)
Grafana Dashboard        (Port 3000)
```

##  Complete Integration Setup (10 Minutes)

### **Prerequisites**
- Docker and Docker Compose installed
- System with at least 4GB RAM
- Network access to PC1 and PC2

### **Step 1: Quick Setup Script**
```bash
# Navigate to PC3 directory
cd /home/dickson/FYP/drone_autonomous/PC3

# Make scripts executable
chmod +x scripts/setup.sh
chmod +x scripts/health-check.sh
chmod +x scripts/monitor.sh

# Run complete setup
./scripts/setup.sh
```

### **Step 2: Verify Integration**
```bash
# Check all services
docker-compose ps

# Run health check
./scripts/health-check.sh

# Test endpoints
curl http://localhost:8004/health    # Telemetry Collector
curl http://localhost:8086/health     # InfluxDB
curl http://localhost:3000/api/health # Grafana
```

### **Step 3: Access Services**

#### **Grafana Dashboard**
- **URL**: http://localhost:3000
- **Login**: admin / admin123
- **Features**: Real-time dashboards, alerts, data visualization

#### **InfluxDB Database**
- **URL**: http://localhost:8086
- **Organization**: drone-project
- **Bucket**: drone_telemetry
- **Token**: drone-telemetry-token

#### **Telemetry Collector API**
- **URL**: http://localhost:8004
- **Health**: http://localhost:8004/health
- **Status**: http://localhost:8004/status
- **Metrics**: http://localhost:8004/metrics

### **Step 1: Install Docker (If not installed)**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin -y
```

### **Step 2: Run Setup Script**
```bash
# Make script executable
chmod +x setup.sh

# Run setup (does everything automatically)
./setup.sh
```

### **Step 3: Enter Team IPs**
Script will ask for team member IPs:
```
PC1 IP [192.168.1.10]: 192.168.1.10
PC2 IP [192.168.1.11]: 192.168.1.11
PC3 IP (Your IP - press Enter): 
PC4 IP [192.168.1.13]: 192.168.1.13
```

### **Step 4: Wait for Setup**
- **Download time**: 3-5 minutes (InfluxDB + Grafana)
- **Build time**: 2-3 minutes
- **Start time**: 1 minute

**Total time: ~10 minutes first time, 2 minutes subsequent**

##  Test Your Services

After setup completes, test everything:

```bash
# Test Telemetry Collector
curl http://localhost:8004/health
# Should return: {"status": "healthy", "service": "telemetry-collector"}

# Test InfluxDB
curl http://localhost:8086/health
# Should return: {"name":"influxdb","message":"ready for queries"}

# Test Grafana (Open browser)
# URL: http://localhost:3000
# Username: admin
# Password: admin123
```

##  Access Grafana Dashboard

### **Open Grafana:**
1. **Open browser**: http://localhost:3000
2. **Login**: admin / admin123
3. **You should see**: Drone system dashboards

### **Default Dashboards:**
- **GPS Tracking** - Real-time drone position
- **Altitude Graph** - Height over time
- **Battery Monitor** - Power consumption
- **Object Detection** - Detection frequency
- **System Performance** - CPU, memory usage

##  InfluxDB Management

### **Check Database:**
```bash
# Access InfluxDB CLI
docker exec -it influxdb influx

# Show databases
show databases

# Use drone database
use drone_telemetry

# Show measurements
show measurements

# Query data
select * from gps_telemetry limit 10
```

### **Manual Data Insert:**
```bash
# Test data insertion
curl -X POST 'http://localhost:8086/api/v2/write?bucket=drone_telemetry&org=drone-project' \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: text/plain; charset=utf-8" \
  --data-binary 'gps_telemetry,drone_id=drone_001 latitude=-1.2921,longitude=36.8219,altitude=50.0'
```

##  Monitor Your Services

```bash
# Check all services status
docker-compose ps

# View logs (real-time)
docker-compose logs -f

# Check specific service logs
docker-compose logs -f telemetry-collector
docker-compose logs -f influxdb
docker-compose logs -f grafana
```

##  Common Issues & Solutions

### **Issue: "Grafana won't connect to InfluxDB"**
```bash
# Check InfluxDB status
docker exec influxdb influx ping

# Check Grafana configuration
docker exec grafana cat /etc/grafana/provisioning/datasources/influxdb.yml

# Restart Grafana
docker-compose restart grafana

# Wait 30 seconds and refresh browser
```

### **Issue: "No data in dashboards"**
```bash
# Check if data is being received
docker logs telemetry-collector | grep "Published"

# Check InfluxDB for data
docker exec -it influxdb influx
use drone_telemetry
show series

# Manually insert test data
curl -X POST 'http://localhost:8086/api/v2/write?bucket=drone_telemetry&org=drone-project' \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: text/plain; charset=utf-8" \
  --data-binary 'gps_telemetry,drone_id=test latitude=-1.0,longitude=36.0,altitude=100.0'
```

### **Issue: "High memory usage"**
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

### **Issue: "Port conflicts"**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :8086

# Kill conflicting processes
sudo kill -9 [PID]

# Restart services
docker-compose down && docker-compose up -d
```

##  What You Should See

### **Successful Setup:**
```bash
# docker-compose ps output should show:
NAME                COMMAND                  SERVICE             STATUS              PORTS
telemetry-collector  "python telemetry.py"    telemetry-collector  running             0.0.0.0:8004->8004/tcp
influxdb            "/entrypoint.sh infl..."   influxdb             running             0.0.0.0:8086->8086/tcp
grafana             "/run.sh"                grafana              running             0.0.0.0:3000->3000/tcp
```

### **Grafana Dashboard:**
- **Login successful** at http://localhost:3000
- **Data sources connected** (InfluxDB)
- **Dashboards visible** with graphs
- **Real-time updates** when data flows

### **Health Check Results:**
```bash
# All should return "healthy"
curl http://localhost:8004/health  ✓
curl http://localhost:8086/health  ✓
```

##  Daily Workflow

### **Every Morning:**
```bash
cd /path/to/PC3
docker-compose ps  # Check services
open http://localhost:3000  # Open Grafana
```

### **When Monitoring:**
```bash
# Watch data flow
docker-compose logs -f telemetry-collector

# Check database size
docker exec influxdb du -sh /var/lib/influxdb2/

# Monitor system performance
docker stats
```

### **When Analyzing:**
```bash
# Query data directly
docker exec -it influxdb influx
use drone_telemetry
select mean(*) from gps_telemetry where time > now() - 1h group by time(1m)

# Export data
docker exec influxdb influx query 'select * into csv from gps_telemetry' > export.csv
```

##  Creating Custom Dashboards

### **Add New Dashboard:**
1. **Open Grafana**: http://localhost:3000
2. **Click**: + → Dashboard
3. **Add Panel**: Choose visualization
4. **Select Data**: InfluxDB → drone_telemetry
5. **Write Query**: Use Flux or InfluxQL
6. **Save Dashboard**: Give it a name

### **Example Queries:**
```flux
// GPS position over time
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gps_telemetry")
  |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude")
```

```flux
// Object detection frequency
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "object_detections")
  |> count()
```

##  Success Indicators

You're successful when:
- [ ] All 3 services are running
- [ ] Health endpoints return "healthy"
- [ ] Grafana connects to InfluxDB
- [ ] Dashboards display data
- [ ] Real-time updates work
- [ ] Team can access analytics

##  Team Communication

### **You Coordinate With:**
- **PC1**: Collect command logs, provide system status
- **PC2**: Store detection data, receive navigation info
- **PC4**: Provide dashboard data, receive user analytics

### **Your Critical Functions:**
- **Data collection** - All system data flows through you
- **Storage** - Long-term data persistence
- **Analytics** - Performance insights and trends

##  Next Steps

Once your PC3 is running:
1. **Explore Grafana** - Create custom dashboards
2. **Set up alerts** - Notification rules
3. **Analyze patterns** - Flight behavior insights
4. **Export reports** - Performance metrics

##  Fun Things to Try

### **Set Up Alerts:**
```bash
# In Grafana: Alerting → New Alert Rule
# Low battery alert
# High altitude alert
# Detection frequency alert
```

### **Data Analysis:**
```bash
# Export data for analysis
docker exec influxdb influx query 'select * into csv from gps_telemetry where time > now() - 24h' > daily_flight.csv

# Analyze in Python or Excel
```

### **Performance Monitoring:**
```bash
# Monitor database performance
docker exec influxdb influx stats

# Check query performance
docker exec influxdb influx query 'show stats for httpd'
```

##  You're Ready!

When everything is working:
```bash
# Your services are running
curl http://localhost:8004/health  ✓
curl http://localhost:8086/health  ✓

# Grafana is open with live dashboards
# Data is flowing from all PCs
# Team can see insights and analytics
# System has memory and intelligence! 💾
```

**Need help? Check logs: `docker-compose logs -f`**
