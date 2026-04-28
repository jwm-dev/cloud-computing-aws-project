import React, { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'

const CELL_SIZE = 14
const MAP_W = 40
const MAP_H = 31

const ROLE_COLORS = {
  IMPOSTOR: '#e53935',
  CREWMATE: '#1e88e5',
}

function drawFrame(canvas, frame) {
  if (!canvas || !frame) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Background
  ctx.fillStyle = '#1a1a2e'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Deposit zone
  const dX = Math.floor(MAP_W / 2)
  const dY = Math.floor(MAP_H / 2)
  ctx.fillStyle = '#ffd600'
  ctx.fillRect(dX * CELL_SIZE - CELL_SIZE, dY * CELL_SIZE - CELL_SIZE, CELL_SIZE * 3, CELL_SIZE * 3)

  // Fuel cells
  ctx.fillStyle = '#69f0ae'
  for (const cell of frame.fuel_cells || []) {
    ctx.fillRect(cell.x * CELL_SIZE + 2, cell.y * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
  }

  // Players
  for (const p of frame.players || []) {
    ctx.fillStyle = p.active ? ROLE_COLORS[p.role] || '#aaa' : '#555'
    ctx.beginPath()
    ctx.arc(
      p.position.x * CELL_SIZE + CELL_SIZE / 2,
      p.position.y * CELL_SIZE + CELL_SIZE / 2,
      CELL_SIZE / 2 - 1,
      0,
      Math.PI * 2
    )
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = '8px monospace'
    ctx.fillText(p.player_id, p.position.x * CELL_SIZE + 4, p.position.y * CELL_SIZE + 10)
  }
}

export default function ReplayViewer() {
  const { experimentId, episodeId } = useParams()
  const canvasRef = useRef(null)

  const [expId, setExpId] = useState(experimentId || '')
  const [epId, setEpId] = useState(episodeId || '')
  const [replay, setReplay] = useState(null)
  const [frameIdx, setFrameIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(100)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (replay) {
      drawFrame(canvasRef.current, replay.frames[frameIdx])
    }
  }, [replay, frameIdx])

  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        setFrameIdx((i) => {
          if (i >= replay.frames.length - 1) {
            setPlaying(false)
            return i
          }
          return i + 1
        })
      }, speed)
    }
    return () => clearInterval(intervalRef.current)
  }, [playing, speed, replay])

  const loadReplay = () => {
    if (!expId || !epId) return
    setError(null)
    axios
      .get(`/replays/${expId}/${epId}`)
      .then((res) => {
        setReplay(res.data)
        setFrameIdx(0)
        setPlaying(false)
      })
      .catch(() => setError('Failed to load replay'))
  }

  const frame = replay?.frames?.[frameIdx]

  return (
    <div>
      <h2>Replay Viewer</h2>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <input
          placeholder="Experiment ID"
          value={expId}
          onChange={(e) => setExpId(e.target.value)}
          style={{ width: '280px' }}
        />
        <input
          placeholder="Episode ID"
          value={epId}
          onChange={(e) => setEpId(e.target.value)}
          style={{ width: '280px' }}
        />
        <button onClick={loadReplay}>Load</button>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {replay && (
        <>
          <p>
            <strong>Episode:</strong> {replay.episode_id} &nbsp;|&nbsp;
            <strong>Frames:</strong> {replay.frames.length} &nbsp;|&nbsp;
            <strong>Frame:</strong> {frameIdx + 1}
          </p>
          {frame && (
            <p>
              Phase: <strong>{frame.phase}</strong> &nbsp;|&nbsp; Tick:{' '}
              <strong>{frame.tick}</strong> &nbsp;|&nbsp; Fuel deposited:{' '}
              <strong>{frame.fuel_deposited}</strong> &nbsp;|&nbsp; Winner:{' '}
              <strong>{frame.winner || '—'}</strong>
            </p>
          )}
          <canvas
            ref={canvasRef}
            width={MAP_W * CELL_SIZE}
            height={MAP_H * CELL_SIZE}
            style={{ border: '1px solid #333', display: 'block', marginBottom: '0.75rem' }}
          />
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button onClick={() => setFrameIdx(0)}>⏮</button>
            <button onClick={() => setFrameIdx((i) => Math.max(0, i - 1))}>◀</button>
            <button onClick={() => setPlaying((p) => !p)}>
              {playing ? '⏸' : '▶'}
            </button>
            <button
              onClick={() =>
                setFrameIdx((i) => Math.min(replay.frames.length - 1, i + 1))
              }
            >
              ▶
            </button>
            <button onClick={() => setFrameIdx(replay.frames.length - 1)}>⏭</button>
            <label>
              Speed (ms/frame):{' '}
              <input
                type="range"
                min={50}
                max={500}
                step={50}
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
              />
              {speed}
            </label>
          </div>
          <input
            type="range"
            min={0}
            max={replay.frames.length - 1}
            value={frameIdx}
            onChange={(e) => {
              setPlaying(false)
              setFrameIdx(Number(e.target.value))
            }}
            style={{ width: '100%', marginTop: '0.5rem' }}
          />
        </>
      )}
    </div>
  )
}
