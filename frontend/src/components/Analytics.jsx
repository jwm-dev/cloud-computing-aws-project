import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts'

const COLORS = ['#4caf50', '#2196f3', '#f44336', '#ff9800']

export default function Analytics() {
  const { experimentId } = useParams()
  const [summary, setSummary] = useState(null)
  const [episodes, setEpisodes] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!experimentId) return
    setLoading(true)
    Promise.all([
      axios.get(`/analytics/${experimentId}/summary`),
      axios.get(`/analytics/${experimentId}`),
    ])
      .then(([sumRes, epRes]) => {
        setSummary(sumRes.data)
        setEpisodes(epRes.data)
        setError(null)
      })
      .catch(() => setError('Failed to load analytics'))
      .finally(() => setLoading(false))
  }, [experimentId])

  if (!experimentId)
    return <p>Select an experiment from the Dashboard to view analytics.</p>
  if (loading) return <p>Loading analytics…</p>
  if (error) return <p style={{ color: 'red' }}>{error}</p>
  if (!summary) return null

  const pieData = Object.entries(summary.winner_distribution).map(([name, value]) => ({
    name,
    value: Math.round(value * 100),
  }))

  const stepsData = episodes.map((ep, i) => ({
    episode: i + 1,
    steps: ep.steps,
    fuel: ep.fuel_deposited,
  }))

  return (
    <div>
      <h2>Analytics — {experimentId}</h2>
      <p>
        <strong>Episodes:</strong> {summary.episodes} &nbsp;|&nbsp;
        <strong>Avg steps:</strong> {summary.avg_steps_per_episode.toFixed(1)} &nbsp;|&nbsp;
        <strong>Avg fuel deposited:</strong> {summary.avg_fuel_deposited.toFixed(2)}
      </p>

      <h3>Win distribution</h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={pieData} dataKey="value" nameKey="name" label={({ name, value }) => `${name}: ${value}%`}>
            {pieData.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v) => `${v}%`} />
        </PieChart>
      </ResponsiveContainer>

      <h3>Steps &amp; fuel per episode</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={stepsData}>
          <XAxis dataKey="episode" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Bar yAxisId="left" dataKey="steps" fill="#2196f3" name="Steps" />
          <Bar yAxisId="right" dataKey="fuel" fill="#4caf50" name="Fuel deposited" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
