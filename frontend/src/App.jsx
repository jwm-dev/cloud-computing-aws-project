import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './components/Dashboard.jsx'
import ExperimentDispatch from './components/ExperimentDispatch.jsx'
import Analytics from './components/Analytics.jsx'
import ReplayViewer from './components/ReplayViewer.jsx'

const navStyle = {
  display: 'flex',
  gap: '1.5rem',
  padding: '0.75rem 1.5rem',
  background: '#1a1a2e',
  color: '#eee',
}

const linkStyle = ({ isActive }) => ({
  color: isActive ? '#e94560' : '#eee',
  textDecoration: 'none',
  fontWeight: isActive ? 'bold' : 'normal',
})

export default function App() {
  return (
    <BrowserRouter>
      <nav style={navStyle}>
        <span style={{ fontWeight: 'bold', color: '#e94560' }}>
          Hidden Agenda RL Gym
        </span>
        <NavLink to="/" style={linkStyle} end>
          Dashboard
        </NavLink>
        <NavLink to="/dispatch" style={linkStyle}>
          Dispatch
        </NavLink>
        <NavLink to="/analytics" style={linkStyle}>
          Analytics
        </NavLink>
        <NavLink to="/replay" style={linkStyle}>
          Replay
        </NavLink>
      </nav>
      <main style={{ padding: '1.5rem', fontFamily: 'sans-serif' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dispatch" element={<ExperimentDispatch />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/analytics/:experimentId" element={<Analytics />} />
          <Route path="/replay" element={<ReplayViewer />} />
          <Route path="/replay/:experimentId/:episodeId" element={<ReplayViewer />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
