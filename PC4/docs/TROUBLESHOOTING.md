# Troubleshooting Guide for PC4 Feedback Service

## Common Issues and Solutions

### Service Won't Start

#### Issue: Docker container fails to start

**Symptoms:**
- `docker-compose up` fails immediately
- Container exits with error code
- No logs available

**Solutions:**

1. Check Docker is running:
```bash
sudo systemctl status docker
sudo systemctl start docker
```

2. Check Docker Compose version:
```bash
docker-compose --version
# Should be 1.29+ or docker compose (v2)
```

3. Verify docker-compose.yml syntax:
```bash
docker-compose config
```

4. Check for port conflicts:
```bash
sudo netstat -tulpn | grep :8005
```

5. Rebuild from scratch:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

### No Audio Output

#### Issue: TTS processes messages but no sound is heard

**Symptoms:**
- Service responds to `/speak` requests
- Logs show message processed
- No audio from speakers

**Solutions:**

1. Verify user is in audio group:
```bash
groups $USER
# Should include 'audio'
sudo usermod -aG audio $USER
# Logout and login again
```

2. Check audio device permissions:
```bash
ls -la /dev/snd/
# Should show crw-rw----+ for audio devices
```

3. Test audio device in container:
```bash
docker exec feedback-service aplay -l
docker exec feedback-service speaker-test -t wav
```

4. Verify device mapping in docker-compose.yml:
```yaml
devices:
  - /dev/snd:/dev/snd
```

5. Check ALSA configuration:
```bash
docker exec feedback-service cat /etc/asound.conf
docker exec feedback-service alsamixer
```

6. Test audio outside Docker:
```bash
aplay /usr/share/sounds/alsa/Front_Center.wav
```

---

### TTS Engine Errors

#### Issue: pyttsx3 import errors or TTS failures

**Symptoms:**
- Logs show "ModuleNotFoundError: No module named 'pyttsx3'"
- TTS engine initialization fails
- Speak endpoint returns 500 error

**Solutions:**

1. Rebuild container to ensure dependencies installed:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

2. Verify pyttsx3 installation:
```bash
docker exec feedback-service python -c "import pyttsx3; print('OK')"
```

3. Test TTS manually:
```bash
docker exec -it feedback-service python -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('Test message')
engine.runAndWait()
"
```

4. Check for espeak-ng installation:
```bash
docker exec feedback-service espeak-ng --version
```

5. Reinstall dependencies:
```bash
docker exec feedback-service pip install --force-reinstall pyttsx3
```

---

### Kafka Connection Issues

#### Issue: Service can't connect to Kafka broker

**Symptoms:**
- Logs show Kafka connection errors
- Messages not consumed from topics
- Timeout errors

**Solutions:**

1. Verify Kafka is accessible:
```bash
curl http://PC1:9092  # Replace with actual IP
telnet PC1 9092
```

2. Check Kafka configuration:
```bash
cat config/kafka_topics.yaml
```

3. Verify environment variable:
```bash
docker exec feedback-service env | grep KAFKA
```

4. Test Kafka connection from container:
```bash
docker exec feedback-service python -c "
from kafka import KafkaProducer
producer = KafkaProducer(
    bootstrap_servers='PC1:9092',
    security_protocol='PLAINTEXT'
)
print('Connected')
"
```

5. Update docker-compose.yml with correct IP:
```yaml
environment:
  - KAFKA_BOOTSTRAP_SERVERS=192.168.1.10:9092  # Use actual IP
```

6. Check network connectivity:
```bash
docker exec feedback-service ping PC1
docker exec feedback-service nc -zv PC1 9092
```

---

### Health Check Failures

#### Issue: `/health` endpoint returns error or unhealthy status

**Symptoms:**
- Health check returns 500 error
- Status shows "unhealthy"
- Docker healthcheck fails

**Solutions:**

1. Check service logs:
```bash
docker-compose logs feedback-service
```

2. Test endpoint manually:
```bash
curl -v http://localhost:8005/health
```

3. Check if service is running:
```bash
docker-compose ps
```

4. Restart service:
```bash
docker-compose restart feedback-service
```

5. Verify healthcheck configuration:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
  interval: 10s
  timeout: 5s
  retries: 3
```

---

### Queue Backup

#### Issue: Messages accumulate in queue, not processed

**Symptoms:**
- Queue size keeps increasing
- Messages delayed or not spoken
- Stats show large queue

**Solutions:**

1. Check queue status:
```bash
curl http://localhost:8005/stats | jq .queue_stats
```

2. Clear queue (if needed):
```bash
docker-compose restart feedback-service
```

3. Reduce message rate:
```bash
# Check Kafka message rate
# Reduce detection frequency
```

4. Increase processing capacity:
```yaml
# In config/tts_config.yaml
performance:
  max_concurrent_speaks: 2  # Increase if needed
```

5. Check for stuck messages:
```bash
docker-compose logs feedback-service | grep -i error
```

---

### High CPU Usage

#### Issue: Feedback Service consuming excessive CPU

**Symptoms:**
- High CPU usage in top/htop
- System sluggish
- Container CPU at 100%

**Solutions:**

1. Monitor CPU usage:
```bash
docker stats feedback-service
```

2. Reduce TTS rate:
```yaml
# In config/tts_config.yaml
tts:
  rate: 130  # Lower from 150
```

3. Enable caching:
```yaml
performance:
  enable_caching: true
  cache_size: 100
```

4. Reduce concurrent operations:
```yaml
performance:
  max_concurrent_speaks: 1
```

5. Check for infinite loops in code:
```bash
docker-compose logs feedback-service | tail -100
```

---

### Memory Leaks

#### Issue: Memory usage increases over time

**Symptoms:**
- Memory usage grows continuously
- Container gets killed by OOM killer
- System becomes slow

**Solutions:**

1. Monitor memory usage:
```bash
docker stats feedback-service
```

2. Restart service periodically:
```bash
docker-compose restart feedback-service
```

3. Check for memory leaks:
```bash
docker exec feedback-service python -m memory_profiler feedback.py
```

4. Limit memory in docker-compose.yml:
```yaml
services:
  feedback-service:
    deploy:
      resources:
        limits:
          memory: 512M
```

5. Clear caches:
```bash
# Restart to clear memory
docker-compose restart feedback-service
```

---

### Port Already in Use

#### Issue: Port 8005 already bound to another process

**Symptoms:**
- Docker compose fails with "port already allocated"
- Can't start service

**Solutions:**

1. Find process using port:
```bash
sudo netstat -tulpn | grep :8005
sudo lsof -i :8005
```

2. Kill conflicting process:
```bash
sudo kill -9 [PID]
```

3. Or use different port:
```yaml
ports:
  - "8006:8005"  # Use different host port
```

4. Check for zombie containers:
```bash
docker ps -a
docker rm -f [container_id]
```

---

### Configuration Not Loading

#### Issue: Changes to config files not reflected

**Symptoms:**
- Config changes ignored
- Old settings still in effect
- Default values used

**Solutions:**

1. Restart service after config change:
```bash
docker-compose restart feedback-service
```

2. Verify config file syntax:
```bash
python -c "import yaml; yaml.safe_load(open('config/tts_config.yaml'))"
```

3. Check config volume mount:
```bash
docker exec feedback-service ls -la /app/config
```

4. Rebuild to apply changes:
```bash
docker-compose down
docker-compose up -d --build
```

5. Check environment variables:
```bash
docker exec feedback-service env | grep TTS
```

---

### Docker Permission Issues

#### Issue: Permission denied when running docker commands

**Symptoms:**
- "permission denied" error
- Need sudo for docker commands
- Can't run docker-compose

**Solutions:**

1. Add user to docker group:
```bash
sudo usermod -aG docker $USER
# Logout and login again
```

2. Verify group membership:
```bash
groups $USER
# Should include 'docker'
```

3. Check docker socket permissions:
```bash
sudo ls -la /var/run/docker.sock
# Should be docker:docker
```

4. Fix permissions if needed:
```bash
sudo chown root:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock
```

---

### Logs Not Writing

#### Issue: No logs generated or logs not accessible

**Symptoms:**
- `docker-compose logs` empty
- Logs directory empty
- Can't see service logs

**Solutions:**

1. Check logs directory:
```bash
ls -la logs/
mkdir -p logs
chmod 777 logs
```

2. Verify volume mount:
```yaml
volumes:
  - ./logs:/app/logs
```

3. Check container logs:
```bash
docker logs feedback-service
```

4. Enable debug logging:
```yaml
environment:
  - DEBUG=true
```

5. Check log rotation:
```bash
# Add to docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

### Getting Help

If none of these solutions work:

1. **Collect diagnostic information:**
```bash
docker-compose ps
docker-compose logs --tail=100
docker stats --no-stream
curl http://localhost:8005/health
curl http://localhost:8005/stats
```

2. **Check configuration files:**
```bash
cat config/tts_config.yaml
cat config/feedback_config.yaml
cat config/kafka_topics.yaml
```

3. **Review documentation:**
- README.md
- docs/TTS_SETUP.md
- docs/API_DOCS.md

4. **Check system resources:**
```bash
free -h
df -h
top
```

5. **Rebuild from scratch:**
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Debug Mode

Enable debug mode for more detailed logging:

```yaml
environment:
  - DEBUG=true
  - LOG_LEVEL=debug
```

Then check logs:
```bash
docker-compose logs -f feedback-service
```

## Performance Issues

### Slow TTS Response

**Symptoms:**
- Long delay between request and speech
- Queue builds up
- High latency

**Solutions:**
1. Lower TTS rate: `rate: 120`
2. Enable caching: `enable_caching: true`
3. Reduce message length
4. Use faster voice: `voice_index: 0`

### Intermittent Audio

**Symptoms:**
- Some messages spoken, others not
- Random audio dropouts
- Inconsistent behavior

**Solutions:**
1. Check audio device stability
2. Reduce concurrent operations: `max_concurrent_speaks: 1`
3. Add cooldown between messages: `cooldown_seconds: 2`
4. Check system load
5. Verify audio cable/connection

## Network Issues

### Can't Access from Other PCs

**Symptoms:**
- Service works locally but not from other machines
- Connection refused errors
- Firewall blocking

**Solutions:**
1. Check binding:
```yaml
environment:
  - HOST=0.0.0.0  # Bind to all interfaces
```

2. Check firewall:
```bash
sudo ufw status
sudo ufw allow 8005
```

3. Test from other PC:
```bash
curl http://PC4_IP:8005/health
```

4. Check docker network:
```bash
docker network inspect PC4_drone-network
```
