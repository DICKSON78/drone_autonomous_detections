/**
 * Utility functions for PC4 dashboard
 */

/**
 * Format timestamp to readable string
 */
export const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};

/**
 * Format timestamp to full date string
 */
export const formatDateTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleString();
};

/**
 * Format confidence percentage
 */
export const formatConfidence = (confidence) => {
  return `${(confidence * 100).toFixed(1)}%`;
};

/**
 * Get color for confidence level
 */
export const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#4caf50'; // green
  if (confidence >= 0.6) return '#ff9800'; // orange
  if (confidence >= 0.4) return '#ff6f00'; // deep orange
  return '#f44336'; // red
};

/**
 * Get color for priority level
 */
export const getPriorityColor = (priority) => {
  const colors = {
    emergency: '#f44336',
    high: '#ff9800',
    normal: '#2196f3',
    low: '#4caf50',
  };
  return colors[priority] || '#2196f3';
};

/**
 * Get priority label
 */
export const getPriorityLabel = (priority) => {
  const labels = {
    emergency: '🚨 EMERGENCY',
    high: '⚠️ WARNING',
    normal: 'ℹ️ INFO',
    low: '✓ LOW',
  };
  return labels[priority] || priority.toUpperCase();
};

/**
 * Calculate distance between two GPS coordinates (in meters)
 */
export const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371000; // Earth's radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

/**
 * Parse confidence threshold
 */
export const isConfidenceAboveThreshold = (confidence, threshold = 0.5) => {
  return confidence >= threshold;
};

/**
 * Debounce function
 */
export const debounce = (func, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

/**
 * Throttle function
 */
export const throttle = (func, limit) => {
  let inThrottle;
  return (...args) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

/**
 * Check if drone is in safe state
 */
export const isSafeState = (droneState) => {
  if (!droneState) return false;
  const battery = droneState.battery || {};
  const status = droneState.status || '';
  
  return (
    battery.percentage >= 0.2 && // At least 20% battery
    status !== 'ERROR' &&
    status !== 'EMERGENCY'
  );
};

export default {
  formatTime,
  formatDateTime,
  formatConfidence,
  getConfidenceColor,
  getPriorityColor,
  getPriorityLabel,
  calculateDistance,
  isConfidenceAboveThreshold,
  debounce,
  throttle,
  isSafeState,
};
