# #!/bin/bash

# Test runner script

echo "=========================================="
echo "PC1 Integration Tests"
echo "=========================================="

# Test Command Parser
echo -e "\n1. Testing Command Parser Service..."
curl -s http://localhost:8000/health | jq '.' || echo "Command Parser not running"

# Test Flight Control
echo -e "\n2. Testing Flight Control Service..."
curl -s http://localhost:8001/health | jq '.' || echo "Flight Control not running"

# Test Command Parsing
echo -e "\n3. Testing Command Parsing..."
curl -s -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Go to forest area", "user_id": "test"}' | jq '.'

# Test Kafka Topics
echo -e "\n4. Testing Kafka Topics..."
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Test Flight Control Command
echo -e "\n5. Testing Direct Flight Command..."
curl -s -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"command_type": "takeoff", "target_altitude": 10}' | jq '.'

echo -e "\n=========================================="
echo "Tests Complete"
echo "=========================================="est runner script for PC1 automated testing
