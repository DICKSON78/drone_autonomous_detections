const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { Kafka } = require('kafkajs');
const axios = require('axios');
const WebSocket = require('ws');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 8001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Kafka setup
const kafka = new Kafka({
  clientId: 'flight-control',
  brokers: [process.env.KAFKA_BOOTSTRAP_SERVERS || 'kafka:9092']
});

const consumer = kafka.consumer({ groupId: 'flight-control-group' });
const producer = kafka.producer();

// Drone state
let droneState = {
  position: { lat: -1.2920, lon: 36.8200, altitude: 0 },
  status: 'landed', // landed, takeoff, flying, landing, emergency
  battery: 100,
  speed: 0,
  heading: 0,
  last_update: new Date().toISOString()
};

// WebSocket for real-time updates
const wss = new WebSocket.Server({ port: 8081 });

wss.on('connection', (ws) => {
  console.log('Client connected to flight control WebSocket');
  
  // Send current state on connection
  ws.send(JSON.stringify({
    type: 'state_update',
    data: droneState
  }));
  
  ws.on('close', () => {
    console.log('Client disconnected from flight control WebSocket');
  });
});

function broadcastStateUpdate() {
  const message = JSON.stringify({
    type: 'state_update',
    data: droneState
  });
  
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

function updateDroneState(updates) {
  droneState = {
    ...droneState,
    ...updates,
    last_update: new Date().toISOString()
  };
  broadcastStateUpdate();
}

async function executeFlightCommand(command) {
  try {
    console.log(`Executing flight command: ${command.command}`);
    
    switch (command.action) {
      case 'navigate':
        return await navigateToTarget(command);
      case 'takeoff':
        return await takeoff(command);
      case 'land':
        return await land(command);
      case 'hover':
        return await hover(command);
      case 'return':
        return await returnToBase(command);
      default:
        throw new Error(`Unknown action: ${command.action}`);
    }
  } catch (error) {
    console.error('Flight command execution error:', error);
    updateDroneState({ status: 'emergency' });
    throw error;
  }
}

async function navigateToTarget(command) {
  updateDroneState({ status: 'flying' });
  
  // Simulate navigation
  const target = command.target_gps;
  const altitude = command.altitude || 50;
  
  // Simulate flight time based on distance
  const distance = calculateDistance(droneState.position, target);
  const flightTime = Math.max(5, distance * 100); // Simulated flight time
  
  console.log(`Navigating to ${target.lat}, ${target.lon} at ${altitude}m altitude`);
  
  // Update position gradually (simulation)
  const steps = 10;
  for (let i = 0; i < steps; i++) {
    await new Promise(resolve => setTimeout(resolve, flightTime * 1000 / steps));
    
    const progress = (i + 1) / steps;
    updateDroneState({
      position: {
        lat: droneState.position.lat + (target.lat - droneState.position.lat) * progress,
        lon: droneState.position.lon + (target.lon - droneState.position.lon) * progress,
        altitude: altitude
      },
      speed: 15, // m/s
      battery: Math.max(20, droneState.battery - (distance * 0.1))
    });
  }
  
  updateDroneState({ 
    status: 'hovering',
    speed: 0
  });
  
  return {
    status: 'success',
    message: `Reached target location`,
    position: droneState.position
  };
}

async function takeoff(command) {
  if (droneState.status !== 'landed') {
    throw new Error('Drone is already in flight');
  }
  
  updateDroneState({ status: 'takeoff' });
  
  // Simulate takeoff
  for (let altitude = 0; altitude <= 10; altitude += 2) {
    await new Promise(resolve => setTimeout(resolve, 500));
    updateDroneState({
      position: { ...droneState.position, altitude },
      speed: 5
    });
  }
  
  updateDroneState({ 
    status: 'hovering',
    speed: 0
  });
  
  return {
    status: 'success',
    message: 'Drone has taken off successfully'
  };
}

async function land(command) {
  if (droneState.status === 'landed') {
    throw new Error('Drone is already landed');
  }
  
  updateDroneState({ status: 'landing' });
  
  // Simulate landing
  const currentAltitude = droneState.position.altitude;
  for (let altitude = currentAltitude; altitude >= 0; altitude -= 2) {
    await new Promise(resolve => setTimeout(resolve, 300));
    updateDroneState({
      position: { ...droneState.position, altitude },
      speed: 3
    });
  }
  
  updateDroneState({ 
    status: 'landed',
    speed: 0
  });
  
  return {
    status: 'success',
    message: 'Drone has landed successfully'
  };
}

async function hover(command) {
  if (droneState.status === 'landed') {
    throw new Error('Drone must be in flight to hover');
  }
  
  updateDroneState({ status: 'hovering', speed: 0 });
  
  return {
    status: 'success',
    message: 'Drone is now hovering'
  };
}

async function returnToBase(command) {
  const baseLocation = { lat: -1.2920, lon: 36.8200 };
  
  return await navigateToTarget({
    ...command,
    action: 'navigate',
    target_gps: baseLocation,
    altitude: 50
  });
}

function calculateDistance(pos1, pos2) {
  // Simple Euclidean distance (in real system, use Haversine formula)
  const latDiff = pos2.lat - pos1.lat;
  const lonDiff = pos2.lon - pos1.lon;
  return Math.sqrt(latDiff * latDiff + lonDiff * lonDiff);
}

// Kafka message consumption
async function startKafkaConsumer() {
  await consumer.connect();
  await consumer.subscribe({ topic: 'drone.commands.flight', fromBeginning: false });
  
  await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
      try {
        const command = JSON.parse(message.value.toString());
        console.log(`Received command: ${command.command}`);
        
        const result = await executeFlightCommand(command);
        
        // Send result to telemetry topic
        await producer.connect();
        await producer.send({
          topic: 'drone.telemetry.flight',
          messages: [{
            key: command.command_id,
            value: JSON.stringify({
              command_id: command.command_id,
              result,
              drone_state: droneState,
              timestamp: new Date().toISOString()
            })
          }]
        });
        await producer.disconnect();
        
      } catch (error) {
        console.error('Error processing command:', error);
      }
    },
  });
}

// REST API Routes
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'flight-control',
    drone_state: droneState,
    timestamp: new Date().toISOString()
  });
});

app.get('/status', (req, res) => {
  res.json({
    drone_state: droneState,
    timestamp: new Date().toISOString()
  });
});

app.post('/emergency', async (req, res) => {
  try {
    updateDroneState({ status: 'emergency' });
    
    // Send emergency notification
    await producer.connect();
    await producer.send({
      topic: 'drone.alerts.emergency',
      messages: [{
        key: 'emergency',
        value: JSON.stringify({
          type: 'emergency',
          message: 'Emergency landing initiated',
          drone_state: droneState,
          timestamp: new Date().toISOString()
        })
      }]
    });
    await producer.disconnect();
    
    // Perform emergency landing
    await land({});
    
    res.json({
      status: 'success',
      message: 'Emergency landing completed'
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

// Start server
app.listen(PORT, async () => {
  console.log(`Flight Control Service running on port ${PORT}`);
  console.log(`WebSocket server running on port 8081`);
  
  // Start Kafka consumer
  startKafkaConsumer().catch(console.error);
});

module.exports = app;
