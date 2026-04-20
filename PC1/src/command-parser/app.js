const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { Kafka } = require('kafkajs');
const natural = require('natural');
const nlp = require('compromise');

require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Kafka setup
const kafka = new Kafka({
  clientId: 'command-parser',
  brokers: [process.env.KAFKA_BOOTSTRAP_SERVERS || 'kafka:9092']
});

const producer = kafka.producer();

// Location mappings for GPS coordinates
const locationMappings = {
  'forest': { lat: -1.2921, lon: 36.8219 },
  'lake': { lat: -1.2850, lon: 36.8300 },
  'field': { lat: -1.3000, lon: 36.8100 },
  'home': { lat: -1.2920, lon: 36.8200 },
  'base': { lat: -1.2920, lon: 36.8200 },
  'river': { lat: -1.2880, lon: 36.8350 },
  'mountain': { lat: -1.2950, lon: 36.8150 }
};

// Action keywords
const actionKeywords = {
  'go': 'navigate',
  'fly': 'navigate',
  'navigate': 'navigate',
  'inspect': 'inspect',
  'monitor': 'monitor',
  'search': 'search',
  'return': 'return',
  'land': 'land',
  'takeoff': 'takeoff',
  'hover': 'hover'
};

function parseCommandToGPS(commandText) {
  const doc = nlp(commandText.toLowerCase());
  const tokens = commandText.toLowerCase().split(/\s+/);
  
  let detectedLocation = null;
  let detectedAction = 'navigate'; // default action
  let altitude = 50.0; // default altitude
  
  // Detect location
  for (const token of tokens) {
    if (locationMappings[token]) {
      detectedLocation = locationMappings[token];
      break;
    }
  }
  
  // Detect action
  for (const token of tokens) {
    if (actionKeywords[token]) {
      detectedAction = actionKeywords[token];
      break;
    }
  }
  
  // Extract altitude if mentioned
  const altitudeMatch = commandText.match(/(\d+)\s*(?:meter|metre|m|feet|ft)/i);
  if (altitudeMatch) {
    altitude = parseFloat(altitudeMatch[1]);
    if (commandText.toLowerCase().includes('feet') || commandText.toLowerCase().includes('ft')) {
      altitude = altitude * 0.3048; // Convert feet to meters
    }
  }
  
  // Default location if none detected
  if (!detectedLocation) {
    detectedLocation = locationMappings['home'];
  }
  
  return {
    command: commandText,
    target_gps: detectedLocation,
    altitude: altitude,
    action: detectedAction,
    confidence: calculateConfidence(commandText, detectedLocation, detectedAction)
  };
}

function calculateConfidence(commandText, location, action) {
  let confidence = 0.5; // Base confidence
  
  // Increase confidence if we found a known location
  if (location && location !== locationMappings['home']) {
    confidence += 0.3;
  }
  
  // Increase confidence if we found a known action
  if (action && action !== 'navigate') {
    confidence += 0.1;
  }
  
  // Increase confidence for longer, more specific commands
  if (commandText.length > 20) {
    confidence += 0.1;
  }
  
  return Math.min(confidence, 1.0);
}

// Routes
app.post('/parse-command', async (req, res) => {
  try {
    const { text, user_id } = req.body;
    
    if (!text || !user_id) {
      return res.status(400).json({
        status: 'error',
        message: 'Missing required fields: text and user_id'
      });
    }
    
    const parsedCommand = parseCommandToGPS(text);
    
    // Add metadata
    const commandWithMetadata = {
      ...parsedCommand,
      user_id,
      timestamp: new Date().toISOString(),
      command_id: `cmd_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
    
    // Send to Kafka
    await producer.connect();
    await producer.send({
      topic: 'drone.commands.flight',
      messages: [{
        key: commandWithMetadata.command_id,
        value: JSON.stringify(commandWithMetadata)
      }]
    });
    await producer.disconnect();
    
    console.log(`Published command: ${JSON.stringify(commandWithMetadata)}`);
    
    res.json({
      status: 'success',
      parsed_command: commandWithMetadata,
      message: 'Command sent to drone'
    });
    
  } catch (error) {
    console.error('Error processing command:', error);
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'command-parser',
    timestamp: new Date().toISOString()
  });
});

app.get('/locations', (req, res) => {
  res.json({
    locations: locationMappings,
    actions: Object.keys(actionKeywords)
  });
});

// Start server
app.listen(PORT, async () => {
  console.log(`Command Parser Service running on port ${PORT}`);
  
  // Test Kafka connection on startup
  try {
    await producer.connect();
    console.log('Kafka producer connected successfully');
    await producer.disconnect();
  } catch (error) {
    console.error('Failed to connect to Kafka:', error);
  }
});

module.exports = app;
