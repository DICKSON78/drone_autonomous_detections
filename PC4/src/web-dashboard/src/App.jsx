import React, { useState, useEffect } from 'react';
import './styles/app.css';
import useWebSocket from './hooks/useWebSocket';
import Dashboard from './pages/Dashboard';
import Detections from './pages/Detections';
import Navigation from './pages/Navigation';
import Feedback from './pages/Feedback';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const { messages, isConnected, error } = useWebSocket();
  const [stats, setStats] = useState({
    totalMessages: 0,
    detections: [],
    telemetry: null,
    feedback: [],
  });

  // Update stats as messages arrive
  useEffect(() => {
    messages.forEach((msg) => {
      setStats((prev) => {
        const updated = { ...prev, totalMessages: prev.totalMessages + 1 };
        
        if (msg.type === 'detection') {
          updated.detections = [msg, ...prev.detections.slice(0, 49)];
        } else if (msg.type === 'telemetry') {
          updated.telemetry = msg;
        } else if (msg.type === 'feedback') {
          updated.feedback = [msg, ...prev.feedback.slice(0, 49)];
        }
        
        return updated;
      });
    });
  }, [messages]);

  const pages = {
    dashboard: <Dashboard stats={stats} isConnected={isConnected} />,
    detections: <Detections detections={stats.detections} />,
    navigation: <Navigation messages={messages.filter(m => m.type === 'navigation')} />,
    feedback: <Feedback feedbackMessages={stats.feedback} />,
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>🚁 Drone Autonomous Detection</h1>
          <div className="header-stats">
            <span className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
            <span className="message-count">Messages: {stats.totalMessages}</span>
          </div>
        </div>
      </header>

      <nav className="navbar">
        <button 
          className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentPage('dashboard')}
        >
          📊 Dashboard
        </button>
        <button 
          className={`nav-btn ${currentPage === 'detections' ? 'active' : ''}`}
          onClick={() => setCurrentPage('detections')}
        >
          🎯 Detections
        </button>
        <button 
          className={`nav-btn ${currentPage === 'navigation' ? 'active' : ''}`}
          onClick={() => setCurrentPage('navigation')}
        >
          🧭 Navigation
        </button>
        <button 
          className={`nav-btn ${currentPage === 'feedback' ? 'active' : ''}`}
          onClick={() => setCurrentPage('feedback')}
        >
          🔊 Feedback
        </button>
      </nav>

      <main className="main-content">
        {error && <div className="error-banner">{error}</div>}
        {pages[currentPage]}
      </main>

      <footer className="footer">
        <p>FYP - Drone Autonomous Detection System | Real-time Dashboard</p>
      </footer>
    </div>
  );
}

export default App;
