import { useState, useEffect, useCallback, useRef } from 'react';

const WS_URL = process.env.REACT_APP_WS_URL || `ws://${window.location.hostname}:8006`;
const RECONNECT_INTERVAL = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Custom hook for managing WebSocket connection to the relay server.
 * Automatically reconnects on disconnect and buffers messages.
 */
function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const messageBufferRef = useRef([]);

  const connect = useCallback(() => {
    try {
      setError(null);
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WS] Connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        
        // Send initial subscription to all message types
        ws.send(JSON.stringify({
          type: 'subscribe',
          data: { types: ['telemetry', 'detection', 'navigation', 'feedback', 'command'] }
        }));

        // Flush buffered messages
        if (messageBufferRef.current.length > 0) {
          setMessages((prev) => [...messageBufferRef.current, ...prev]);
          messageBufferRef.current = [];
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'connected') {
            console.log('[WS] Client ID:', message.clientId);
          } else {
            setMessages((prev) => [message, ...prev.slice(0, 499)]);
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onerror = (event) => {
        console.error('[WS] Error:', event);
        setError('WebSocket error occurred');
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          console.log(`[WS] Reconnecting (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`);
          reconnectTimeoutRef.current = setTimeout(() => connect(), RECONNECT_INTERVAL);
        } else {
          setError('Failed to connect after maximum attempts');
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      setError('Failed to establish WebSocket connection');
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Send a message through the WebSocket
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  return { isConnected, messages, error, sendMessage };
}

export default useWebSocket;
