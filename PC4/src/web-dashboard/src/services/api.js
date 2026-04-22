/**
 * API service layer for PC4 dashboard
 * Handles HTTP requests to feedback and websocket services
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || `http://${window.location.hostname}`;
const FEEDBACK_API = `${API_BASE_URL}/api/feedback`;
const WS_API = `${API_BASE_URL}/api/websocket`;

/**
 * Feedback Service API calls
 */
export const feedbackAPI = {
  /**
   * Check feedback service health
   */
  async getHealth() {
    try {
      const response = await fetch(`${FEEDBACK_API}/health`);
      if (!response.ok) throw new Error('Health check failed');
      return await response.json();
    } catch (error) {
      console.error('Feedback health check error:', error);
      throw error;
    }
  },

  /**
   * Send text-to-speech message
   */
  async speak(message, priority = 'normal', asyncMode = true) {
    try {
      const response = await fetch(`${FEEDBACK_API}/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          priority,
          async_mode: asyncMode,
        }),
      });
      if (!response.ok) throw new Error('Speak request failed');
      return await response.json();
    } catch (error) {
      console.error('Speak error:', error);
      throw error;
    }
  },

  /**
   * Announce an event
   */
  async announce(event, details = '') {
    try {
      const response = await fetch(`${FEEDBACK_API}/announce`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, details }),
      });
      if (!response.ok) throw new Error('Announce request failed');
      return await response.json();
    } catch (error) {
      console.error('Announce error:', error);
      throw error;
    }
  },

  /**
   * Get available TTS voices
   */
  async getVoices() {
    try {
      const response = await fetch(`${FEEDBACK_API}/voices`);
      if (!response.ok) throw new Error('Get voices failed');
      return await response.json();
    } catch (error) {
      console.error('Get voices error:', error);
      throw error;
    }
  },

  /**
   * Get feedback statistics
   */
  async getStats() {
    try {
      const response = await fetch(`${FEEDBACK_API}/stats`);
      if (!response.ok) throw new Error('Get stats failed');
      return await response.json();
    } catch (error) {
      console.error('Get stats error:', error);
      throw error;
    }
  },

  /**
   * Get audio devices
   */
  async getAudioDevices() {
    try {
      const response = await fetch(`${FEEDBACK_API}/audio-devices`);
      if (!response.ok) throw new Error('Get audio devices failed');
      return await response.json();
    } catch (error) {
      console.error('Get audio devices error:', error);
      throw error;
    }
  },
};

/**
 * WebSocket Server API calls
 */
export const websocketAPI = {
  /**
   * Check websocket server health
   */
  async getHealth() {
    try {
      const response = await fetch(`${WS_API}/health`);
      if (!response.ok) throw new Error('WebSocket health check failed');
      return await response.json();
    } catch (error) {
      console.error('WebSocket health check error:', error);
      throw error;
    }
  },

  /**
   * Get list of connected clients
   */
  async getClients() {
    try {
      const response = await fetch(`${WS_API}/clients`);
      if (!response.ok) throw new Error('Get clients failed');
      return await response.json();
    } catch (error) {
      console.error('Get clients error:', error);
      throw error;
    }
  },

  /**
   * Broadcast a message to all clients
   */
  async broadcast(type, data) {
    try {
      const response = await fetch(`${WS_API}/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, data }),
      });
      if (!response.ok) throw new Error('Broadcast failed');
      return await response.json();
    } catch (error) {
      console.error('Broadcast error:', error);
      throw error;
    }
  },
};

export default {
  feedbackAPI,
  websocketAPI,
};
