import { useState, useEffect, useRef, useCallback } from "react";

const MAX_HISTORY  = 100;
const RECONNECT_MS = 3000;

/**
 * useWebSocket — manages a WebSocket connection with auto-reconnect.
 * Maintains separate state slices for each drone data type.
 */
export function useWebSocket(url) {
  const [connected,       setConnected]       = useState(false);
  const [messages,        setMessages]        = useState([]);
  const [telemetry,       setTelemetry]       = useState(null);
  const [detections,      setDetections]      = useState([]);
  const [navigationEvents,setNavigationEvents]= useState([]);
  const [feedbackHistory, setFeedbackHistory] = useState([]);
  const [messageCount,    setMessageCount]    = useState(0);

  const wsRef      = useRef(null);
  const reconnectRef = useRef(null);
  const mountedRef = useRef(true);

  const pushCapped = useCallback((setter, item) => {
    setter((prev) => [item, ...prev].slice(0, MAX_HISTORY));
  }, []);

  const handleMessage = useCallback((raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    setMessageCount((c) => c + 1);
    setMessages((prev) => [msg, ...prev].slice(0, MAX_HISTORY));

    switch (msg.type) {
      case "telemetry":
        setTelemetry({ ...msg.data, _ts: msg.timestamp });
        break;
      case "detection":
        pushCapped(setDetections, { ...msg.data, _ts: msg.timestamp });
        break;
      case "navigation":
        pushCapped(setNavigationEvents, { ...msg.data, _ts: msg.timestamp });
        break;
      case "feedback":
      case "command":
        pushCapped(setFeedbackHistory, { ...msg.data, type: msg.type, _ts: msg.timestamp });
        break;
      default:
        break;
    }
  }, [pushCapped]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        // Subscribe to all types
        ws.send(JSON.stringify({ type: "subscribe", data: { types: [] } }));
      };

      ws.onmessage = (e) => handleMessage(e.data);

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        reconnectRef.current = setTimeout(connect, RECONNECT_MS);
      };

      ws.onerror = (err) => {
        console.error("[useWebSocket] error:", err);
        ws.close();
      };
    } catch (err) {
      console.error("[useWebSocket] connect error:", err);
      reconnectRef.current = setTimeout(connect, RECONNECT_MS);
    }
  }, [url, handleMessage]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return {
    connected,
    messages,
    telemetry,
    detections,
    navigationEvents,
    feedbackHistory,
    messageCount,
  };
}
