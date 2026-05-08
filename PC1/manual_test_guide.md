# PC1 AI Drone System - Manual Testing Guide

## Current Status
The enhanced AI system has been implemented but Docker builds are experiencing network timeout issues. Here's how to test the system components manually.

## Testing Approach

### 1. Quick Service Health Check
```bash
# Check if services are running
docker compose ps

# Start services if needed
docker compose up -d
```

### 2. Test Individual Components

#### A. Command Parser Testing
```bash
# Test basic command parsing
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Go to forest area", "user_id": "test_user"}'

# Test search commands
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Search for missing person in the forest", "user_id": "test_search"}'

# Test emergency commands
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Emergency land now", "user_id": "test_emergency"}'
```

#### B. Flight Control Testing
```bash
# Check flight control health
curl http://localhost:8001/health

# Check drone status
curl http://localhost:8001/status
```

#### C. Kafka Message Flow Testing
```bash
# Check Kafka topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Monitor Kafka messages
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic drone.commands.flight --from-beginning
```

### 3. Enhanced AI Components Testing

#### Test Commands for AI Features:

**Natural Language Processing:**
```bash
# Complex navigation
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Navigate from forest to lake while avoiding obstacles", "user_id": "test_nav"}'

# Object detection search
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Search for missing person in the dense forest area", "user_id": "test_person"}'

# Surveillance mission
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Monitor the building perimeter for suspicious activity", "user_id": "test_surveillance"}'

# Tracking mission
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Track the red car moving through the forest", "user_id": "test_track"}'
```

### 4. Expected Results

#### Command Parser Should Return:
```json
{
  "status": "success",
  "parsed_command": {
    "command": "Search for missing person in the forest",
    "intent": "search",
    "target_gps": {"lat": -1.2921, "lon": 36.8219},
    "search_objects": ["person"],
    "flight_parameters": {
      "altitude": 30.0,
      "speed": 8.0,
      "hover_time": 30.0
    },
    "confidence": 0.9,
    "user_id": "test_user",
    "timestamp": "2026-05-06T...",
    "command_id": "cmd_..."
  },
  "message": "Command sent to drone"
}
```

#### Flight Control Should Return:
```json
{
  "status": "healthy",
  "service": "flight-control",
  "drone_state": {
    "position": {"lat": -1.292, "lon": 36.82, "altitude": 0},
    "status": "landed",
    "battery": 100,
    "speed": 0,
    "heading": 0
  }
}
```

### 5. AI Component Verification

#### NLP Features to Verify:
- ✅ Intent classification (navigate, search, surveillance, emergency_land, etc.)
- ✅ Entity extraction (locations, objects, actions)
- ✅ GPS coordinate mapping
- ✅ Flight parameter adjustment based on intent
- ✅ Confidence scoring

#### YOLO Detection Features (Mock):
- ✅ Object detection results in command processing
- ✅ Search object identification
- ✅ Target tracking capabilities

#### RL Controller Features (Mock):
- ✅ Autonomous flight command generation
- ✅ State-based decision making
- ✅ Safety parameter enforcement

### 6. Integration Testing

#### End-to-End Workflow:
1. Send natural language command → Command Parser
2. NLP processing → Intent classification & entity extraction
3. Kafka message → Flight Control Service
4. RL controller → Flight command generation
5. YOLO integration → Object detection processing
6. Response back through Kafka

#### Test the Full Flow:
```bash
# Send complex command
curl -X POST http://localhost:8000/parse-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Search for missing person in forest and return if found", "user_id": "test_e2e"}'

# Monitor Kafka for message flow
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic drone.commands.flight --from-beginning --max-messages 5
```

### 7. Performance Testing

#### Load Testing:
```bash
# Send multiple commands rapidly
for i in {1..10}; do
  curl -X POST http://localhost:8000/parse-command \
    -H "Content-Type: application/json" \
    -d '{"text": "Test command '$i'", "user_id": "load_test"}' &
done
wait
```

### 8. Troubleshooting

#### Common Issues:
1. **Services not starting**: Check Docker logs
   ```bash
   docker compose logs command-parser
   docker compose logs flight-control
   ```

2. **Connection refused**: Services not running
   ```bash
   docker compose up -d
   ```

3. **Kafka not responding**: Restart Kafka
   ```bash
   docker compose restart kafka
   ```

4. **NLP not working**: Check spaCy model download
   ```bash
   docker exec command-parser python -c "import spacy; print(spacy.load('en_core_web_sm'))"
   ```

### 9. Success Criteria

Your AI system is working correctly when:

- ✅ All services respond to health checks
- ✅ Commands are parsed with correct intents
- ✅ GPS coordinates are assigned based on locations
- ✅ Objects are extracted for search missions
- ✅ Flight parameters adjust based on command type
- ✅ Kafka messages flow between services
- ✅ Error handling works for edge cases
- ✅ Response times are under 2 seconds

### 10. Advanced Testing Scenarios

#### Test Complex Commands:
- "Search the forest area for missing person and return if found"
- "Monitor the building perimeter while hovering at 100 meters"
- "Track the vehicle from forest to lake area"
- "Emergency land immediately due to low battery"

#### Test Error Handling:
- Empty commands
- Invalid JSON
- Very long commands
- Special characters
- Missing required fields

This testing guide will help you verify all the AI components are working correctly in your guided language drone system.
