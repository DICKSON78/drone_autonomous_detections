# Grafana Custom Dashboard Creation Guide

## Quick Access

**Grafana URL**: http://localhost:3000  
**Login**: admin / admin123

## Step-by-Step Dashboard Creation

### Step 1: Access Grafana
1. Open your browser and go to http://localhost:3000
2. Login with username: `admin` and password: `admin123`
3. You'll see the Grafana home screen

### Step 2: Create New Dashboard
1. Click the **"+"** icon in the left sidebar
2. Select **"Dashboard"** from the dropdown menu
3. Click **"Add new panel"** to start creating your first panel

### Step 3: Configure Data Source
1. In the panel editor, click **"Select data source"**
2. Choose **"InfluxDB"** from the dropdown
3. The connection should already be configured

### Step 4: Create Flight Status Panel

#### Panel 1: GPS Position
1. **Panel Type**: Stat or Geomap
2. **Query** (Flux language):
```flux
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "flight_telemetry")
  |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude")
  |> last()
  |> yield(key: r._field, value: r._value)
```
3. **Title**: "GPS Position"
4. **Visualization**: Stat panel showing current coordinates

#### Panel 2: Altitude Gauge
1. **Panel Type**: Gauge
2. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "flight_telemetry")
  |> filter(fn: (r) => r._field == "altitude")
  |> last()
  |> yield(key: r._field, value: r._value)
```
3. **Title**: "Altitude"
4. **Unit**: meters (m)
5. **Thresholds**: 
   - Green: 0-100m
   - Yellow: 100-200m
   - Red: >200m

#### Panel 3: Speed Indicator
1. **Panel Type**: Gauge
2. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "flight_telemetry")
  |> filter(fn: (r) => r._field == "speed")
  |> last()
  |> yield(key: r._field, value: r._value)
```
3. **Title**: "Ground Speed"
4. **Unit**: m/s
5. **Thresholds**:
   - Green: 0-15 m/s
   - Yellow: 15-25 m/s
   - Red: >25 m/s

### Step 5: Create System Performance Panel

#### Panel 4: Battery Level
1. **Panel Type**: Gauge
2. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r._field == "battery_percentage")
  |> last()
  |> yield(key: r._field, value: r._value)
```
3. **Title**: "Battery Level"
4. **Unit**: percent (%)
5. **Thresholds**:
   - Green: >50%
   - Yellow: 20-50%
   - Red: <20%

#### Panel 5: CPU Usage Graph
1. **Panel Type**: Time Series
2. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r._field == "cpu_usage")
  |> aggregateWindow(every: 1m, fn: mean)
  |> yield(key: r._field, value: r._value)
```
3. **Title**: "CPU Usage"
4. **Unit**: percent (%)
5. **Legend**: Show current value

### Step 6: Create Object Detection Panel

#### Panel 6: Detection Count
1. **Panel Type**: Stat
2. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "object_detections")
  |> count()
  |> yield(key: "detection_count", value: r._value)
```
3. **Title**: "Total Detections (1h)"
4. **Unit**: short

#### Panel 7: Detection Confidence Heatmap
1. **Panel Type**: Heatmap
2. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "object_detections")
  |> filter(fn: (r) => r._field == "confidence")
  |> yield(key: r._field, value: r._value)
```
3. **Title**: "Detection Confidence"
4. **Unit**: percent (%)

### Step 7: Arrange Panels
1. **Drag and drop** panels to arrange them
2. **Resize panels** by dragging corners
3. **Grid layout** (6 columns x 12 rows recommended):
   - Row 1: GPS Position (6 cols), Altitude (3 cols), Speed (3 cols)
   - Row 2: Battery Level (6 cols), CPU Usage (6 cols)
   - Row 3: Detection Count (6 cols), Detection Confidence (6 cols)

### Step 8: Configure Dashboard Settings
1. Click **Dashboard settings** (gear icon)
2. **General tab**:
   - **Title**: "Drone System Overview"
   - **Tags**: drone, overview, telemetry
   - **Refresh**: Every 5 seconds
3. **Time settings**:
   - **Time range**: Last 1 hour
   - **Timezone**: Local browser time

### Step 9: Save Dashboard
1. Click **Save** (floppy disk icon)
2. **Dashboard name**: "Drone System Overview"
3. **Folder**: General
4. Click **Save**

## Advanced Panel Configurations

### Multi-Drone Dashboard
If you have multiple drones, add filters:

#### Drone Filter Variable
1. **Dashboard settings** > **Variables** > **Add variable**
2. **Name**: `drone_id`
3. **Type**: Query
4. **Query**:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "flight_telemetry")
  |> group(columns: ["drone_id"])
  |> distinct(column: "drone_id")
  |> keep(columns: ["drone_id"])
```
5. **Multi-value**: Enabled
6. **Include All option**: Enabled

#### Update Queries with Variable
Add `drone_id` filter to all queries:
```flux
from(bucket: "drone_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "flight_telemetry")
  |> filter(fn: (r) => r.drone_id == "${drone_id}")
  |> filter(fn: (r) => r._field == "altitude")
  |> last()
  |> yield(key: r._field, value: r._value)
```

### Alert Configuration

#### Battery Alert
1. **Panel settings** > **Alert**
2. **Alert name**: "Low Battery"
3. **Condition**: Battery < 20%
4. **For**: 5 minutes
5. **Notifications**: Add email/webhook

#### GPS Alert
1. **Alert name**: "GPS Signal Lost"
2. **Condition**: Latitude = 0 AND Longitude = 0
3. **For**: 30 seconds
4. **Severity**: Critical

## Customization Tips

### Visual Customization
1. **Colors**: Use consistent color scheme
2. **Units**: Always specify units (m, m/s, %)
3. **Thresholds**: Set meaningful thresholds
4. **Tooltips**: Enable tooltips for better UX

### Performance Optimization
1. **Time ranges**: Use appropriate time ranges
2. **Queries**: Filter by tags before fields
3. **Aggregation**: Use aggregate functions for large datasets
4. **Refresh rate**: Don't refresh too frequently

### Best Practices
1. **Panel titles**: Be descriptive and consistent
2. **Query comments**: Add comments to complex queries
3. **Documentation**: Document dashboard purpose
4. **Testing**: Test with different time ranges

## Troubleshooting

### No Data Showing
1. Check if InfluxDB has data:
```bash
curl -X POST "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token drone-telemetry-token" \
  -H "Content-Type: application/vnd.flux" \
  --data 'from(bucket:"drone_telemetry") |> range(start: -1h) |> limit(n:10)'
```

2. Generate test data:
```bash
./scripts/generate-test-data.sh
```

### Query Errors
1. Check syntax in Flux query
2. Verify measurement and field names
3. Check time range settings

### Performance Issues
1. Reduce time range
2. Add aggregation functions
3. Optimize queries with proper filtering

## Example Complete Dashboard

Here's a complete dashboard JSON you can import:

```json
{
  "dashboard": {
    "id": null,
    "title": "Drone System Overview",
    "tags": ["drone", "overview", "telemetry"],
    "timezone": "browser",
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
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
        "targets": [
          {
            "refId": "A",
            "expr": "from(bucket: \"drone_telemetry\")\n  |> range(start: -5m)\n  |> filter(fn: (r) => r._measurement == \"flight_telemetry\")\n  |> filter(fn: (r) => r._field == \"latitude\" or r._field == \"longitude\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
            "datasource": {"type": "influxdb", "uid": "InfluxDB"}
          }
        ]
      },
      {
        "id": 2,
        "title": "Altitude",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
        "targets": [
          {
            "refId": "B",
            "expr": "from(bucket: \"drone_telemetry\")\n  |> range(start: -5m)\n  |> filter(fn: (r) => r._measurement == \"flight_telemetry\")\n  |> filter(fn: (r) => r._field == \"altitude\")\n  |> last()\n  |> yield(key: r._field, value: r._value)",
            "datasource": {"type": "influxdb", "uid": "InfluxDB"}
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
      }
    ]
  }
}
```

## Next Steps

Once your dashboard is created:
1. **Test with real data** from your drone system
2. **Add alerts** for critical metrics
3. **Create additional dashboards** for specific use cases
4. **Share with team members**
5. **Monitor performance** and optimize queries

**Your custom Grafana dashboard is now ready!**
