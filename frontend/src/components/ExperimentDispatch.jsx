import React, { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const formStyle = {
  display: 'flex',
  flexDirection: 'column',
  maxWidth: '480px',
  gap: '0.75rem',
}

const fieldStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.25rem',
}

export default function ExperimentDispatch() {
  const navigate = useNavigate()
  const [config, setConfig] = useState({
    n_players: 5,
    n_impostors: 1,
    n_episodes: 3,
    random_policy: true,
    description: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setConfig((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? Number(value) : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    axios
      .post('/experiments', config)
      .then((res) => {
        navigate(`/analytics/${res.data.experiment_id}`)
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Failed to dispatch experiment')
        setSubmitting(false)
      })
  }

  return (
    <div>
      <h2>Dispatch Experiment</h2>
      <form style={formStyle} onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <label>Players</label>
          <input
            type="number"
            name="n_players"
            min={3}
            max={10}
            value={config.n_players}
            onChange={handleChange}
          />
        </div>
        <div style={fieldStyle}>
          <label>Impostors</label>
          <input
            type="number"
            name="n_impostors"
            min={1}
            max={3}
            value={config.n_impostors}
            onChange={handleChange}
          />
        </div>
        <div style={fieldStyle}>
          <label>Episodes</label>
          <input
            type="number"
            name="n_episodes"
            min={1}
            max={100}
            value={config.n_episodes}
            onChange={handleChange}
          />
        </div>
        <div style={fieldStyle}>
          <label>
            <input
              type="checkbox"
              name="random_policy"
              checked={config.random_policy}
              onChange={handleChange}
            />{' '}
            Use random policy (baseline)
          </label>
        </div>
        <div style={fieldStyle}>
          <label>Description (optional)</label>
          <input
            type="text"
            name="description"
            value={config.description}
            onChange={handleChange}
            placeholder="e.g. baseline run #1"
          />
        </div>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Dispatching…' : 'Launch Experiment'}
        </button>
      </form>
    </div>
  )
}
