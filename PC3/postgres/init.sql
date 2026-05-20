-- PostgreSQL initialization script for LGADS
-- Creates tables for mission logs, users, and system events

CREATE TABLE IF NOT EXISTS mission_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    mission_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    target_lat DOUBLE PRECISION,
    target_lon DOUBLE PRECISION,
    target_alt DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_event_logs (
    id SERIAL PRIMARY KEY,
    log_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    service_name VARCHAR(100),
    mission_id INTEGER,
    severity VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'operator',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_models (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500),
    trained_on TIMESTAMP,
    accuracy DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS configurations (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kafka_topics (
    id SERIAL PRIMARY KEY,
    topic_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@lgads.local', '$2b$12$LJ3m4ys3Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8Lk8', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Insert default Kafka topics
INSERT INTO kafka_topics (topic_name, description) VALUES
    ('drone.telemetry.gps', 'GPS position telemetry'),
    ('drone.telemetry.battery', 'Battery status telemetry'),
    ('drone.telemetry.attitude', 'Attitude (roll/pitch/yaw) telemetry'),
    ('drone.telemetry.velocity', 'Velocity (N/E/D) telemetry'),
    ('drone.commands.flight', 'Flight commands from NLP parser'),
    ('drone.commands.parsed', 'Parsed NLP commands'),
    ('drone.detections.objects', 'YOLO object detection results'),
    ('drone.navigation.decisions', 'RL navigation decisions'),
    ('drone.feedback.spoken', 'TTS feedback messages'),
    ('drone.status.flight', 'Flight status updates')
ON CONFLICT (topic_name) DO NOTHING;

-- Insert default configurations
INSERT INTO configurations (config_key, config_value) VALUES
    ('system.name', 'LGADS'),
    ('system.version', '1.0.0'),
    ('drone.home_lat', '-6.1630'),
    ('drone.home_lon', '35.7516'),
    ('drone.home_alt', '1120'),
    ('telemetry.collection_rate_hz', '1'),
    ('detection.confidence_threshold', '0.45')
ON CONFLICT (config_key) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_mission_history_user_id ON mission_history(user_id);
CREATE INDEX IF NOT EXISTS idx_mission_history_status ON mission_history(status);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_mission_id ON system_event_logs(mission_id);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_created_at ON system_event_logs(created_at);
