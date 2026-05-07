const runStatus = document.getElementById('runStatus');
const runRows = document.getElementById('runRows');
const runCount = document.getElementById('runCount');
const seedInput = document.getElementById('seed');
const numGamesInput = document.getElementById('numGames');
const configInput = document.getElementById('config');
const refreshButton = document.getElementById('refreshRuns');
const runSingleButton = document.getElementById('runSingle');
const runBatchButton = document.getElementById('runBatch');

function setStatus(text, kind = '') {
  runStatus.textContent = text;
  runStatus.className = kind ? `status ${kind}` : 'status';
}

function formatCreatedAt(value) {
  if (!value) {
    return 'just now';
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function parseConfig() {
  try {
    return JSON.parse(configInput.value || '{}');
  } catch (error) {
    throw new Error('Config must be valid JSON.');
  }
}

function actionButtonLabel(item) {
  return item.viewer_url ? 'Open viewer' : 'Open';
}

function rowMarkup(item) {
  const stepCount = item.steps ?? 'pending';
  return `
    <tr>
      <td>
        <div style="font-weight: 700;">${item.game_id}</div>
        <div class="muted" style="margin-top: 4px; word-break: break-word;">${item.path || ''}</div>
      </td>
      <td>${item.seed ?? 'n/a'}</td>
      <td>${stepCount}</td>
      <td>${formatCreatedAt(item.created_at)}</td>
      <td><a class="button" href="${item.viewer_url || `/viewer/${item.game_id}`}">${actionButtonLabel(item)}</a></td>
    </tr>
  `;
}

async function loadRuns() {
  const response = await fetch('/games');
  const runs = await response.json();
  runRows.innerHTML = runs.length
    ? runs.map(rowMarkup).join('')
    : '<tr><td colspan="5" class="muted">No runs yet. Dispatch one to populate the dashboard.</td></tr>';
  runCount.textContent = `${runs.length} run${runs.length === 1 ? '' : 's'}`;
}

async function dispatchRun(numGames) {
  const config = parseConfig();
  if (!('seed' in config)) {
    config.seed = Number(seedInput.value || 0);
  }
  setStatus('Dispatching simulation jobs...', 'pending');
  const response = await fetch('/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      num_games: numGames,
      config,
    }),
  });
  if (!response.ok) {
    throw new Error(`Run request failed with ${response.status}`);
  }
  setStatus(`Queued ${numGames} game${numGames === 1 ? '' : 's'}.`, 'success');
  await loadRuns();
}

runSingleButton.addEventListener('click', async () => {
  try {
    await dispatchRun(1);
  } catch (error) {
    setStatus(error.message, 'pending');
  }
});

runBatchButton.addEventListener('click', async () => {
  try {
    const numGames = Math.max(1, Number(numGamesInput.value || 1));
    await dispatchRun(numGames);
  } catch (error) {
    setStatus(error.message, 'pending');
  }
});

refreshButton.addEventListener('click', () => {
  loadRuns().catch((error) => setStatus(error.message, 'pending'));
});

seedInput.addEventListener('input', () => {
  const seed = Number(seedInput.value || 0);
  try {
    const config = parseConfig();
    config.seed = seed;
    configInput.value = JSON.stringify(config, null, 2);
  } catch {
    configInput.value = JSON.stringify({ seed }, null, 2);
  }
});

loadRuns().catch((error) => setStatus(error.message, 'pending'));
setInterval(() => {
  loadRuns().catch(() => {});
}, 5000);