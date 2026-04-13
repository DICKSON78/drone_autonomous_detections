# PC3 Project Structure

## Directory Overview
This is the standardized structure for PC3 (Data & Monitoring) development.

## Folders and Their Purpose

```
PC3/
├── 📁 src/                    # Source code files
│   ├── telemetry-collector/    # Data collection logic
│   │   ├── telemetry.py       # Main FastAPI service
│   │   ├── kafka_consumer.py  # Kafka message consumer
│   │   ├── data_processor.py # Data transformation
│   │   ├── influxdb_writer.py # Database interface
│   │   └── tests/           # Unit tests for collection
│   │
│   ├── grafana-integration/   # Dashboard integration
│   │   ├── dashboard_builder.py # Grafana API client
│   │   ├── panel_configurer.py # Panel setup automation
│   │   ├── datasource_manager.py # Data source management
│   │   └── tests/           # Integration tests
│   │
│   └── analytics-engine/      # Analytics processing
│       ├── data_analyzer.py  # Statistical analysis
│       ├── alert_manager.py  # Alert system
│       ├── report_generator.py # Automated reports
│       └── tests/           # Analytics tests
│
├── 📁 config/                # Configuration files
│   ├── influxdb_config.yaml # Database configuration
│   ├── grafana_config.yaml # Dashboard settings
│   ├── kafka_topics.yaml   # Kafka topic mappings
│   ├── alert_rules.yaml   # Alert definitions
│   └── environment.env    # Environment variables
│
├── 📁 data/                  # Data storage and exports
│   ├── backups/            # Database backups
│   ├── exports/            # Data exports
│   ├── reports/            # Generated reports
│   └── analytics_cache/    # Cached analytics results
│
├── 📁 grafana/               # Grafana configuration
│   ├── dashboards/         # Dashboard JSON files
│   ├── datasources/        # Data source definitions
│   ├── plugins/            # Custom Grafana plugins
│   └── provisioning/      # Auto-provisioning configs
│
├── 📁 influxdb/              # InfluxDB configuration
│   ├── influxdb.conf      # Database configuration
│   ├── init_scripts/       # Database initialization
│   ├── schemas/           # Data schemas and retention
│   └── queries/           # Common query templates
│
├── 📁 docs/                 # Documentation
│   ├── DATA_SCHEMAS.md   # Database schema documentation
│   ├── GRAFANA_SETUP.md  # Dashboard setup guide
│   ├── API_DOCS.md       # API documentation
│   └── TROUBLESHOOTING.md # Common issues
│
├── 📁 logs/                 # Log files
│   ├── telemetry.log       # Telemetry service logs
│   ├── influxdb.log       # Database logs
│   ├── grafana.log       # Grafana service logs
│   └── analytics.log      # Analytics engine logs
│
├── 📁 tests/                # Integration tests
│   ├── test_telemetry.py   # Data collection tests
│   ├── test_database.py    # Database tests
│   ├── test_grafana.py     # Dashboard tests
│   └── test_integration.py # End-to-end tests
│
├── 📁 scripts/              # Utility scripts
│   ├── backup_db.sh       # Database backup script
│   ├── restore_db.sh      # Database restore script
│   ├── setup_grafana.sh   # Grafana setup script
│   ├── run_tests.sh       # Test runner
│   └── deploy.sh         # Deployment script
│
├── 📁 docker-compose.yml    # Docker orchestration
├── 📄 Dockerfile           # Container definition
├── 📄 requirements.txt      # Python dependencies
├── 📄 README.md            # Main documentation
├── 📄 setup.sh             # Automated setup script
└── 📄 PROJECT_STRUCTURE.md  # This file
```

## File Naming Conventions

### Source Code Files:
- **Python files**: `snake_case.py` (e.g., `telemetry_collector.py`)
- **Configuration**: `descriptive_name.yaml` (e.g., `influxdb_config.yaml`)
- **Tests**: `test_*.py` (e.g., `test_telemetry.py`)
- **Documentation**: `UPPER_CASE.md` (e.g., `DATA_SCHEMAS.md`)
- **Scripts**: `action_object.sh` (e.g., `backup_db.sh`)

### Directory Naming:
- **Source code**: `kebab-case` (e.g., `telemetry-collector`)
- **Configuration**: `config`
- **Data**: `data`
- **Documentation**: `docs`
- **Tests**: `tests`
- **Grafana**: `grafana`
- **InfluxDB**: `influxdb`

## Developer Responsibilities

### What You'll Work On:
1. **Telemetry Collection Service** (`src/telemetry-collector/`)
   - Collect data from Kafka topics
   - Process and transform telemetry data
   - Write to InfluxDB time-series database
   - Handle data validation and error correction

2. **Grafana Integration** (`src/grafana-integration/`)
   - Create and manage Grafana dashboards
   - Configure data sources and panels
   - Set up automated provisioning
   - Optimize query performance

3. **Analytics Engine** (`src/analytics-engine/`)
   - Process collected data for insights
   - Generate automated reports
   - Implement alerting system
   - Provide performance analytics

### Development Workflow:

#### 1. Setting Up Data Collection:
```bash
# Configure Kafka topics
cd config/
# Edit kafka_topics.yaml for new data sources

# Update InfluxDB schema
cd influxdb/schemas/
# Create new measurement definitions

# Test data flow
cd tests/
python test_telemetry.py
```

#### 2. Creating Grafana Dashboards:
```bash
# Design dashboard
cd grafana/dashboards/
# Create new dashboard JSON

# Auto-provision dashboard
cd src/grafana-integration/
python dashboard_builder.py --create-dashboard my_dashboard

# Test dashboard
# Access: http://localhost:3000
```

#### 3. Managing Data:
```bash
# Backup database
cd scripts/
./backup_db.sh

# Export data
cd src/telemetry-collector/
python data_processor.py --export --format csv

# Analyze data
cd src/analytics-engine/
python data_analyzer.py --time-range 24h
```

## Important Files and Their Purpose

### Core Application Files:
- `src/telemetry-collector/telemetry.py`: Main FastAPI service for data collection
- `src/grafana-integration/dashboard_builder.py`: Grafana dashboard management
- `src/analytics-engine/data_analyzer.py`: Data analytics and processing

### Configuration Files:
- `config/influxdb_config.yaml`: Database connection and retention settings
- `config/grafana_config.yaml`: Dashboard and data source configuration
- `config/kafka_topics.yaml`: Kafka topic mappings and consumer groups
- `config/alert_rules.yaml`: Alert conditions and notifications

### Database Files:
- `influxdb/influxdb.conf`: InfluxDB server configuration
- `influxdb/schemas/`: Data measurement schemas and retention policies
- `influxdb/queries/`: Common query templates and examples

### Grafana Files:
- `grafana/dashboards/`: Dashboard JSON definitions
- `grafana/datasources/`: Data source configurations
- `grafana/provisioning/`: Automatic setup configurations

## Data Schema Standards

### Measurement Naming:
- **GPS data**: `gps_telemetry`
- **Battery data**: `battery_telemetry`
- **Detection data**: `object_detections`
- **Flight data**: `flight_status`
- **System data**: `system_metrics`

### Field Naming:
- **GPS fields**: `latitude`, `longitude`, `altitude`, `speed`
- **Battery fields**: `voltage`, `current`, `percentage`, `temperature`
- **Detection fields**: `object_class`, `confidence`, `bbox_x`, `bbox_y`
- **System fields**: `cpu_usage`, `memory_usage`, `disk_usage`

### Tag Standards:
- **Drone ID**: `drone_id`
- **Source PC**: `source_pc`
- **Data type**: `data_type`
- **Timestamp**: Always included as primary timestamp

## Coding Standards

### Python Code Style:
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Maximum line length: 88 characters
- Include type hints for database operations
- Document query logic and data transformations

### Database Standards:
- Use proper data types for fields
- Set appropriate retention policies
- Index frequently queried fields
- Document measurement schemas
- Handle connection errors gracefully

### Dashboard Standards:
- Use consistent color schemes
- Include proper time range controls
- Add descriptive titles and descriptions
- Optimize queries for performance
- Include alert thresholds

## Common Tasks

### Adding New Data Source:
1. Update `config/kafka_topics.yaml` with new topic
2. Add consumer logic in `src/telemetry-collector/kafka_consumer.py`
3. Define measurement schema in `influxdb/schemas/`
4. Create Grafana dashboard in `grafana/dashboards/`
5. Add tests in `tests/test_telemetry.py`

### Creating New Dashboard:
1. Design dashboard layout
2. Create JSON configuration in `grafana/dashboards/`
3. Add panels with proper queries
4. Set up auto-provisioning in `grafana/provisioning/`
5. Test dashboard functionality

### Setting Up Alerts:
1. Define alert conditions in `config/alert_rules.yaml`
2. Implement alert logic in `src/analytics-engine/alert_manager.py`
3. Configure notification channels
4. Test alert triggers
5. Monitor alert performance

## Performance Optimization

### Database Optimization:
- Use appropriate retention policies
- Index tag fields for faster queries
- Batch write operations
- Monitor query performance
- Regular maintenance and cleanup

### Dashboard Performance:
- Optimize query time ranges
- Use efficient query patterns
- Cache frequently accessed data
- Limit panel refresh rates
- Monitor dashboard load times

## Getting Help

### For Database Issues:
1. Check InfluxDB logs in `logs/influxdb.log`
2. Verify configuration in `influxdb/influxdb.conf`
3. Test database connection: `curl http://localhost:8086/health`
4. Review schema definitions in `influxdb/schemas/`

### For Grafana Issues:
1. Check Grafana logs in `logs/grafana.log`
2. Verify data source connections
3. Test dashboard provisioning
4. Review `docs/GRAFANA_SETUP.md`

### For Data Collection Issues:
1. Check telemetry logs in `logs/telemetry.log`
2. Verify Kafka connectivity
3. Test data processing pipeline
4. Review `config/kafka_topics.yaml`

---

**This structure ensures organized data management and effective monitoring capabilities.**
