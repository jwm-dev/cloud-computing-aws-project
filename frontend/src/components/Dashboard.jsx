import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Link } from 'react-router-dom'

const cardStyle = {
  border: '1px solid #ccc',
  borderRadius: '8px',
  padding: '1rem',
  marginBottom: '1rem',
  background: '#f9f9f9',
}

const statusColor = {
  queued: '#888',
  running: '#2196f3',
  completed: '#4caf50',
  failed: '#f44336',
}

export default function Dashboard() {
  const [experiments, setExperiments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchExperiments = () => {
    setLoading(true)
    axios
      .get('/experiments')
      .then((res) => {
        setExperiments(res.data)
        setError(null)
      })
      .catch(() => setError('Failed to load experiments'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchExperiments()
    const interval = setInterval(fetchExperiments, 5000)
    return () => clearInterval(interval)
  }, [])

  const deleteExperiment = (id) => {
    axios.delete(`/experiments/${id}`).then(fetchExperiments)
  }

  if (loading && experiments.length === 0) return <p>Loading experiments…</p>
  if (error) return <p style={{ color: 'red' }}>{error}</p>

  return (
    <div>
      <h2>Dashboard</h2>
      <p>
        <Link to="/dispatch">
          <button>+ New Experiment</button>
        </Link>
      </p>
      {experiments.length === 0 && <p>No experiments yet. Dispatch one to get started.</p>}
      {experiments.map((exp) => (
        <div key={exp.experiment_id} style={cardStyle}>
          <strong>{exp.experiment_id}</strong>
          {exp.description && <span> — {exp.description}</span>}
          <br />
          Status:{' '}
          <span style={{ color: statusColor[exp.status] || '#333', fontWeight: 'bold' }}>
            {exp.status}
          </span>
          <br />
          Episodes: {exp.episodes_completed} / {exp.episodes_total}
          <br />
          Created: {exp.created_at}
          <br />
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
            <Link to={`/analytics/${exp.experiment_id}`}>
              <button>Analytics</button>
            </Link>
            <Link to={`/replay/${exp.experiment_id}`}>
              <button>Replay</button>
            </Link>
            <button
              onClick={() => deleteExperiment(exp.experiment_id)}
              style={{ color: 'red' }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
