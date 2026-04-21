import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Detections from './pages/Detections';
import Navigation from './pages/Navigation';
import Feedback from './pages/Feedback';
import { useWebSocket } from './hooks/useWebSocket';
import './styles/app.css';

export default function App() {
  const { connected, lastMessage } = useWebSocket(
    `ws://${window.location.hostname}:8006`
  );

  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>Drone Control Dashboard</h1>
          <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </header>

        <nav className="app-nav">
          <NavLink to="/"           end>Dashboard</NavLink>
          <NavLink to="/detections">Detections</NavLink>
          <NavLink to="/navigation">Navigation</NavLink>
          <NavLink to="/feedback">Feedback</NavLink>
        </nav>

        <main className="app-main">
          <Routes>
            <Route path="/"           element={<Dashboard lastMessage={lastMessage} />} />
            <Route path="/detections" element={<Detections lastMessage={lastMessage} />} />
            <Route path="/navigation" element={<Navigation lastMessage={lastMessage} />} />
            <Route path="/feedback"   element={<Feedback />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}