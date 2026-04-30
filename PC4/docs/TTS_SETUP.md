# Text-to-Speech Setup Guide for PC4

## Overview
PC4 provides Text-to-Speech (TTS) capabilities for the drone system, converting system messages into spoken audio for real-time feedback.

## Prerequisites

### Hardware Requirements
- **Audio Output**: Speakers or headphones connected to the system
- **Audio Device**: Default audio device (ALSA/PulseAudio on Linux)
- **System Memory**: Minimum 512MB RAM for TTS processing

### Software Requirements
- Docker and Docker Compose
- Python 3.10+ (for local development)
- Audio drivers (ALSA/PulseAudio)

## Installation

### Quick Setup (Docker)
```bash
# Navigate to PC4 directory
cd PC4

# Run setup script
./setup.sh

# The script will:
# 1. Check Docker installation
# 2. Configure audio permissions
# 3. Build and start the Feedback Service
# 4. Test TTS functionality
```

### Manual Setup
```bash
# 1. Add user to audio group
sudo usermod -aG audio $USER

# 2. Logout and login again for audio group changes to take effect

# 3. Build and start service
docker-compose up -d --build

# 4. Verify service is running
curl http://localhost:8005/health
```

## Configuration

### Voice Settings
Edit `config/tts_config.yaml` to customize voice parameters:

```yaml
tts:
  rate: 150              # Speech rate (words per minute)
  volume: 1.0            # Volume level (0.0 to 1.0)
  voice_index: 0         # Voice index to use
  pitch: 50              # Pitch adjustment (0-100)
  
  voice:
    language: "en"
    gender: "male"
    accent: "en-us"
```

### Priority Settings
Configure message priorities in `config/feedback_config.yaml`:

```yaml
priorities:
  - emergency  # Critical alerts
  - high       # Important warnings
  - normal     # Standard messages
  - low        # Informational messages
```

### Kafka Topics
Configure Kafka topics in `config/kafka_topics.yaml`:

```yaml
input_topics:
  - name: "drone.commands.feedback"
  - name: "drone.detections.objects"
  - name: "drone.navigation.result"
```

## Testing TTS

### Health Check
```bash
curl http://localhost:8005/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "feedback-service",
  "audio_ok": true,
  "queue_size": 0,
  "timestamp": 1234567890.0
}
```

### Test Speech
```bash
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, this is a test", "priority": "normal"}'
```

### Test Announcements
```bash
curl -X POST http://localhost:8005/announce \
  -H "Content-Type: application/json" \
  -d '{"event": "takeoff", "details": "Ready for flight"}'
```

### Available Events
- `startup` - Drone system starting up
- `shutdown` - Drone system shutting down
- `low_battery` - Battery level is low
- `obstacle` - Obstacle detected ahead
- `landing` - Drone is landing
- `takeoff` - Drone is taking off
- `mission_done` - Mission complete
- `emergency` - Emergency situation detected

### Check Available Voices
```bash
curl http://localhost:8005/voices
```

### Check Audio Devices
```bash
curl http://localhost:8005/audio-devices
```

## Troubleshooting

### No Audio Output

**Issue**: TTS processes messages but no sound is heard

**Solutions**:
1. Check audio device permissions:
```bash
groups $USER  # Should include 'audio'
sudo usermod -aG audio $USER
```

2. Test audio device:
```bash
docker exec feedback-service aplay -l
```

3. Check service logs:
```bash
docker-compose logs feedback-service
```

4. Verify audio device in container:
```bash
docker exec feedback-service ls -la /dev/snd/
```

### TTS Not Working

**Issue**: Service returns errors when trying to speak

**Solutions**:
1. Check TTS engine logs:
```bash
docker-compose logs feedback-service | grep -i tts
```

2. Test TTS manually in container:
```bash
docker exec -it feedback-service python -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('Test message')
engine.runAndWait()
"
```

3. Verify pyttsx3 installation:
```bash
docker exec feedback-service python -c "import pyttsx3; print('OK')"
```

### Port Conflicts

**Issue**: Port 8005 already in use

**Solutions**:
1. Check what's using the port:
```bash
sudo netstat -tulpn | grep :8005
```

2. Kill conflicting process:
```bash
sudo kill -9 [PID]
```

3. Or change port in docker-compose.yml:
```yaml
ports:
  - "8006:8005"  # Use different host port
```

### Kafka Connection Issues

**Issue**: Service can't connect to Kafka

**Solutions**:
1. Verify Kafka is running:
```bash
curl http://PC1:9092  # Replace PC1 with actual IP
```

2. Check Kafka configuration:
```bash
cat config/kafka_topics.yaml
```

3. Update KAFKA_BOOTSTRAP_SERVERS in docker-compose.yml:
```yaml
environment:
  - KAFKA_BOOTSTRAP_SERVERS=192.168.1.10:9092  # Use actual IP
```

## Performance Tuning

### Reduce Latency
- Lower TTS rate in config: `rate: 120`
- Reduce queue size: `max_queue_size: 50`
- Enable audio caching: `enable_caching: true`

### Improve Audio Quality
- Increase sample rate: `sample_rate: 48000`
- Adjust volume: `volume: 0.9`
- Use higher quality voice: `voice_index: 1`

### Reduce CPU Usage
- Lower speech rate: `rate: 130`
- Reduce concurrent operations: `max_concurrent_speaks: 1`
- Enable caching: `enable_caching: true`

## Advanced Configuration

### Custom Voice Messages
Edit message templates in `config/tts_config.yaml`:

```yaml
message_templates:
  detection:
    single: "{count} {class_name} detected"
    multiple: "{count} objects detected"
```

### Priority-Specific Voice Settings
```yaml
voice_settings:
  emergency:
    rate: 120      # Slower for clarity
    volume: 1.0    # Maximum volume
    pitch: 60      # Higher pitch
  normal:
    rate: 150
    volume: 0.8
    pitch: 50
```

### Custom Event Messages
Add custom events in `src/feedback-service/feedback.py`:

```python
EVENT_MESSAGES = {
    "custom_event": ("Custom message here", "normal"),
    # ... existing events
}
```

## Integration with Other PCs

### PC1 (Commands)
PC4 receives command feedback from PC1 via Kafka topic `drone.commands.feedback`

### PC2 (Detections)
PC4 receives detection alerts from PC2 via Kafka topic `drone.detections.objects`

### PC3 (Navigation)
PC4 receives navigation results from PC3 via Kafka topic `drone.navigation.result`

## Monitoring

### Service Health
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f feedback-service

# Check statistics
curl http://localhost:8005/stats
```

### Performance Metrics
```bash
# Monitor queue size
curl http://localhost:8005/stats | jq .queue_stats

# Check audio status
curl http://localhost:8005/health | jq .audio_ok
```

## Best Practices

1. **Test audio before deployment** - Always test TTS with a simple message
2. **Monitor queue size** - Large queues indicate performance issues
3. **Use appropriate priorities** - Don't mark everything as emergency
4. **Keep messages short** - Under 200 characters for best performance
5. **Handle audio errors gracefully** - Service should continue even if audio fails
6. **Monitor resource usage** - TTS can be CPU-intensive
7. **Test with different voices** - Find the clearest voice for your use case
8. **Adjust volume appropriately** - Too loud can be annoying, too soft inaudible

## Security Considerations

- Audio device access requires proper permissions
- Kafka connections should use authentication in production
- Rate limiting prevents abuse of TTS endpoint
- Consider adding API keys for TTS endpoints in production

## Support

For issues not covered here:
1. Check service logs: `docker-compose logs -f`
2. Review configuration files in `config/`
3. Consult main README.md
4. Check troubleshooting guide: `docs/TROUBLESHOOTING.md`
