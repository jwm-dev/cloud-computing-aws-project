const canvas = document.getElementById('board');
const context = canvas.getContext('2d');
const viewerTitle = document.getElementById('viewerTitle');
const summaryFrame = document.getElementById('summaryFrame');
const summaryPhase = document.getElementById('summaryPhase');
const summaryFuel = document.getElementById('summaryFuel');
const summaryActive = document.getElementById('summaryActive');
const timelineScrub = document.getElementById('timelineScrub');
const timelineList = document.getElementById('timelineList');
const timelineCount = document.getElementById('timelineCount');
const playButton = document.getElementById('playButton');
const prevButton = document.getElementById('prevButton');
const nextButton = document.getElementById('nextButton');
const speedSelect = document.getElementById('speedSelect');

const gameId = window.location.pathname.split('/').filter(Boolean).pop();
const frameCache = new Map();
let gameData = null;
let currentFrame = 0;
let playTimer = null;

function actionLabel(value) {
  const labels = [
    'forward',
    'backward',
    'left',
    'right',
    'rotate left',
    'rotate right',
    'interact',
    'freeze',
  ];
  return labels[value] || `action ${value}`;
}

function actionsSummary(actions = {}) {
  const entries = Object.entries(actions)
    .map(([playerId, action]) => `P${playerId}: ${actionLabel(Number(action))}`);
  return entries.length ? entries.join(' · ') : 'No actions recorded';
}

function setCurrentFrame(frameIndex) {
  const maxFrame = Math.max(0, (gameData?.step_count || 0));
  currentFrame = Math.max(0, Math.min(frameIndex, maxFrame));
  timelineScrub.value = String(currentFrame);
  loadFrame(currentFrame).catch((error) => {
    viewerTitle.textContent = error.message;
  });
}

function stopPlayback() {
  if (playTimer) {
    clearInterval(playTimer);
    playTimer = null;
  }
  playButton.textContent = 'Play';
}

function drawGrid(frame) {
  const grid = frame.grid || [];
  const players = frame.players || [];
  const cols = grid.length;
  const rows = cols > 0 ? grid[0].length : 0;
  const width = canvas.width;
  const height = canvas.height;
  const cellWidth = width / cols;
  const cellHeight = height / rows;

  context.clearRect(0, 0, width, height);
  context.fillStyle = '#050b14';
  context.fillRect(0, 0, width, height);

  for (let x = 0; x < cols; x += 1) {
    for (let y = 0; y < rows; y += 1) {
      const cell = grid[x][y];
      let fill = '#101827';
      if (cell === -1) fill = '#060b12';
      if (cell === 1) fill = '#d7b34d';
      if (cell === 2) fill = '#5aac6b';
      if (cell === 3) fill = '#6676d8';
      context.fillStyle = fill;
      context.fillRect(x * cellWidth, y * cellHeight, cellWidth + 0.5, cellHeight + 0.5);
    }
  }

  context.strokeStyle = 'rgba(255,255,255,0.05)';
  context.lineWidth = 1;
  context.strokeRect(0, 0, width, height);

  players.forEach((player) => {
    const [px, py] = player.position;
    const cx = (px + 0.5) * cellWidth;
    const cy = (py + 0.5) * cellHeight;
    context.beginPath();
    context.arc(cx, cy, Math.min(cellWidth, cellHeight) * 0.33, 0, Math.PI * 2);
    context.fillStyle = player.active ? (player.role === 'IMPOSTOR' ? '#ff7d5a' : '#dfe7f4') : '#6b7480';
    context.fill();
    context.lineWidth = 2;
    context.strokeStyle = '#0a0f19';
    context.stroke();

    context.fillStyle = '#08101d';
    context.font = 'bold 14px Trebuchet MS';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(String(player.id), cx, cy + 0.5);
  });
}

function renderTimeline(frame) {
  const steps = gameData.steps || [];
  timelineList.innerHTML = steps.map((step, index) => {
    const activeClass = index === frame ? 'timeline-item active' : 'timeline-item';
    return `
      <div class="${activeClass}" data-frame="${index}">
        <div class="meta">
          <span>Frame ${index + 1}</span>
          <span>${step.phase || 'UNKNOWN'}</span>
        </div>
        <div class="actions">${actionsSummary(step.actions || {})}</div>
      </div>
    `;
  }).join('');

  timelineList.querySelectorAll('[data-frame]').forEach((item) => {
    item.addEventListener('click', () => {
      stopPlayback();
      setCurrentFrame(Number(item.dataset.frame));
    });
  });
  timelineCount.textContent = `${steps.length} frame${steps.length === 1 ? '' : 's'}`;
}

async function loadFrame(frameIndex) {
  if (frameCache.has(frameIndex)) {
    const cached = frameCache.get(frameIndex);
    updateViewer(cached, frameIndex);
    return;
  }
  const response = await fetch(`/games/${gameId}/frame/${frameIndex}`);
  if (!response.ok) {
    throw new Error(`Failed to load frame ${frameIndex}`);
  }
  const frame = await response.json();
  frameCache.set(frameIndex, frame);
  updateViewer(frame, frameIndex);
}

function updateViewer(frame, frameIndex) {
  const activeCount = (frame.players || []).filter((player) => player.active).length;
  viewerTitle.textContent = `Run ${frame.game_id} · seed ${frame.seed}`;
  summaryFrame.textContent = String(frameIndex);
  summaryPhase.textContent = frame.phase || '-';
  summaryFuel.textContent = String(frame.fuel_progress ?? 0);
  summaryActive.textContent = String(activeCount);
  drawGrid(frame);
  renderTimeline(frameIndex);
}

async function loadGame() {
  const response = await fetch(`/games/${gameId}`);
  if (!response.ok) {
    throw new Error(`Run ${gameId} was not found`);
  }
  gameData = await response.json();
  const totalFrames = gameData.step_count || 0;
  timelineScrub.max = String(totalFrames);
  timelineScrub.value = '0';
  timelineCount.textContent = `${totalFrames} frame${totalFrames === 1 ? '' : 's'}`;
  viewerTitle.textContent = `Run ${gameData.game_id} · seed ${gameData.seed}`;
  renderTimeline(0);
  await loadFrame(0);
}

playButton.addEventListener('click', () => {
  if (playTimer) {
    stopPlayback();
    return;
  }
  const delay = Number(speedSelect.value || 800);
  playButton.textContent = 'Pause';
  playTimer = setInterval(() => {
    const totalFrames = gameData?.step_count || 0;
    if (currentFrame >= totalFrames) {
      stopPlayback();
      return;
    }
    currentFrame += 1;
    setCurrentFrame(currentFrame);
  }, delay);
});

prevButton.addEventListener('click', () => {
  stopPlayback();
  setCurrentFrame(currentFrame - 1);
});

nextButton.addEventListener('click', () => {
  stopPlayback();
  setCurrentFrame(currentFrame + 1);
});

timelineScrub.addEventListener('input', () => {
  stopPlayback();
  setCurrentFrame(Number(timelineScrub.value || 0));
});

speedSelect.addEventListener('change', () => {
  if (!playTimer) {
    return;
  }
  stopPlayback();
  playButton.click();
});

loadGame().catch((error) => {
  viewerTitle.textContent = error.message;
});