# PC3 - Telemetry & Dashboard System Structure

This document outlines the organized structure of the PC3 microservice suite.

## 📂 Directory Layout

### 🏗️ Core Services (`src/`)
- **`api-gateway/`**: Node.js Express server.
  - `src/`: Source code (routes, controllers, services, middleware).
  - `tests/`: Jest integration tests.
  - `Dockerfile`: Production container definition.
- **`telemetry-collector/`**: Python data ingestion service.
  - `telemetry.py`: Main async service (Kafka → InfluxDB).
  - `tests/`: Unit tests for data processing logic.
  - `Dockerfile`: Container definition.
- **`analytics-engine/`**: Python analytics scripts for report generation.
- **`grafana-integration/`**: Automation scripts for Grafana provisioning.

### ⚙️ Configuration (`config/`)
- `alert_rules.yaml`: Threshold definitions for system alerts.
- `influxdb_config.yaml`: Database connection parameters.
- `grafana_config.yaml`: Dashboard and datasource provisioning.

### 📊 Monitoring & Data (`grafana/`, `influxdb/`, `data/`)
- **`grafana/`**: 
  - `provisioning/`: Auto-loading for dashboards and datasources.
  - `dashboards/`: JSON definitions for drone telemetry views.
- **`influxdb/`**: Database initialization and schema definitions.
- **`data/`**: Persistent storage for reports and backups.

### 📜 Documentation (`docs/`)
- `INTEGRATION_GUIDE.md`: How PC3 connects to other PCs.
- `DATABASE_DASHBOARD_GUIDE.md`: Detailed guide for InfluxDB/Grafana.
- `CUSTOM_DASHBOARD_GUIDE.md`: How to build new views.

### 🛠️ Utilities (`scripts/`)
- `start_pc3.sh`: Main entry point to launch the full stack.
- `stop_all.sh`: Gracefully shuts down all containers and processes.
- `health-check.sh`: Verifies status of all PC3 components.

---

## 🚀 Getting Started

To launch the entire PC3 environment, run:
```bash
./setup.sh
```
*(This is a symbolic link to `scripts/start_pc3.sh`)*

## 🧩 Clean Architecture
- **Stateless Services**: API Gateway and Collector are stateless, allowing for easy scaling.
- **Unified Data Sink**: All telemetry flows into InfluxDB for a single source of truth.
- **Event-Driven**: Kafka ensures loose coupling between PC3 and other drone microservices.
