import {
  CAR_SPEED,
  CITIES,
  DIRECTION_DELTAS,
  GAME_DAY_LENGTH,
  LEVELS,
  LEVEL_TARGETS,
  START_TIME,
  TOOLS,
  TOOL_ORDER,
  calculateFlowRate,
  createSpentTools,
  getArms,
  getCurrentVolume,
  getSpawnInterval,
  getTimeLabel,
  gradeFromFlow,
  isRushHour,
  isToolSpent,
  spendTool,
} from "./game-logic.mjs";

const STORAGE_KEY = "city-limits-mobile-progress-v1";
const app = document.getElementById("app");

const state = {
  city: "Los Angeles",
  level: 1,
  selectedTool: "FOUR_WAY",
  selectedCell: null,
  lastTick: performance.now(),
  message: "Tap an intersection below, then tap a cell to place it.",
  unlockedLevels: loadProgress(),
};

Object.assign(state, createLevelState(state.city, state.level));

render();
requestAnimationFrame(loop);

function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return Object.fromEntries(CITIES.map((entry) => [entry.name, 1]));
    }
    const parsed = JSON.parse(raw);
    return Object.fromEntries(
      CITIES.map((entry) => [entry.name, Math.max(1, Math.min(3, Number(parsed?.[entry.name]) || 1))]),
    );
  } catch {
    return Object.fromEntries(CITIES.map((entry) => [entry.name, 1]));
  }
}

function saveProgress() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.unlockedLevels));
}

function createLevelState(city, level) {
  const config = LEVELS[level];
  return {
    rows: config.rows,
    cols: config.cols,
    markers: config.markers.map((marker) => ({ ...marker })),
    grid: Array.from({ length: config.rows }, () => Array.from({ length: config.cols }, () => null)),
    cars: [],
    completedStats: [],
    spawnAttempts: 0,
    spawnSuccesses: 0,
    spawnTimer: 0,
    gameTimer: START_TIME,
    flowRate: 0,
    running: false,
    paused: false,
    ended: false,
    resultUnlocked: false,
    delivered: 0,
    spentTools: createSpentTools(),
    city,
    level,
    levelNote: config.note,
  };
}

function resetLevel(message = "Level reset. Build a route and press Start.") {
  const preservedProgress = state.unlockedLevels;
  const preservedTool = state.selectedTool;
  Object.assign(state, createLevelState(state.city, state.level));
  state.unlockedLevels = preservedProgress;
  state.selectedTool = getNextAvailableTool(preservedTool);
  state.selectedCell = null;
  state.message = message;
  render();
}

function getNextAvailableTool(preferredTool = state.selectedTool) {
  if (preferredTool && !isToolSpent(state.spentTools, preferredTool)) {
    return preferredTool;
  }
  return TOOL_ORDER.find((toolKey) => !isToolSpent(state.spentTools, toolKey)) || preferredTool || TOOL_ORDER[0];
}

function selectCity(city) {
  state.city = city;
  state.level = Math.min(state.level, state.unlockedLevels[city] || 1);
  resetLevel(`${city} selected. Traffic patterns updated.`);
}

function selectLevel(level) {
  if (level > (state.unlockedLevels[state.city] || 1)) {
    state.message = "Finish the current city run to unlock higher levels.";
    renderResultOnly();
    return;
  }
  state.level = level;
  resetLevel(`Level ${level} ready. ${LEVELS[level].note}.`);
}

function setTool(tool) {
  if (isToolSpent(state.spentTools, tool)) {
    state.message = `${TOOLS[tool].label} is already used in this run. Reset to get it back.`;
    renderResultOnly();
    return;
  }
  state.selectedTool = tool;
  state.message = `${TOOLS[tool].label} selected.`;
  renderPaletteOnly();
}

function handleCellPress(row, col) {
  const current = state.grid[row][col];
  const tool = state.selectedTool;
  state.selectedCell = { row, col };

  if (isToolSpent(state.spentTools, tool)) {
    state.message = `${TOOLS[tool].label} is already spent. Pick another library piece.`;
  } else if (!current) {
    state.grid[row][col] = { type: tool, rotation: 0 };
    state.spentTools = spendTool(state.spentTools, tool);
    state.selectedTool = getNextAvailableTool(tool);
    state.message = `${TOOLS[tool].label} placed.`;
  } else if (current.type === tool && TOOLS[tool].rotatable) {
    current.rotation = (current.rotation + 1) % 4;
    state.message = `${TOOLS[tool].label} rotated.`;
  } else if (current.type === tool && !TOOLS[tool].rotatable) {
    state.message = `${TOOLS[tool].label} is fixed. Choose a three-arm tile to rotate.`;
  } else {
    state.grid[row][col] = { type: tool, rotation: 0 };
    state.spentTools = spendTool(state.spentTools, tool);
    state.selectedTool = getNextAvailableTool(tool);
    state.message = `${TOOLS[tool].label} swapped in.`;
  }

  renderBoardAndPalette();
}

function rotateSelected() {
  if (!state.selectedCell) {
    state.message = "Select a cell first.";
    renderResultOnly();
    return;
  }
  const { row, col } = state.selectedCell;
  const tile = state.grid[row][col];
  if (!tile) {
    state.message = "That cell is empty.";
    renderResultOnly();
    return;
  }
  if (!TOOLS[tile.type].rotatable) {
    state.message = `${TOOLS[tile.type].label} does not rotate.`;
    renderResultOnly();
    return;
  }
  tile.rotation = (tile.rotation + 1) % 4;
  state.message = `${TOOLS[tile.type].label} rotated.`;
  renderBoardAndPalette();
}

function clearSelected() {
  if (!state.selectedCell) {
    state.message = "Select a cell to clear it.";
    renderResultOnly();
    return;
  }
  const { row, col } = state.selectedCell;
  if (!state.grid[row][col]) {
    state.message = "That cell is already empty.";
    renderResultOnly();
    return;
  }
  state.grid[row][col] = null;
  state.message = "Cell cleared. That library piece stays spent for this run.";
  renderBoardAndPalette();
}

function unlockAllLevels() {
  state.unlockedLevels = Object.fromEntries(CITIES.map((entry) => [entry.name, 3]));
  saveProgress();
  state.message = "All levels unlocked for quick playtesting.";
  render();
}

function toggleRun() {
  if (state.ended) {
    resetLevel("New run started.");
  }
  state.running = !state.running;
  state.paused = false;
  state.message = state.running
    ? "Traffic live. Keep routes connected while the day unfolds."
    : "Simulation stopped.";
  renderResultOnly();
}

function pauseRun() {
  if (!state.running || state.ended) {
    state.message = "Start the simulation first.";
    renderResultOnly();
    return;
  }
  state.paused = !state.paused;
  state.message = state.paused ? "Simulation paused." : "Simulation resumed.";
  renderResultOnly();
}

function loop(now) {
  const dt = Math.min((now - state.lastTick) / 1000, 0.08);
  state.lastTick = now;
  if (state.running && !state.paused && !state.ended) {
    updateSimulation(dt);
  }
  requestAnimationFrame(loop);
}

function updateSimulation(dt) {
  state.gameTimer += dt;
  state.spawnTimer += dt;

  const interval = getSpawnInterval(state.city, state.gameTimer, state.level);
  if (state.spawnTimer >= interval) {
    state.spawnTimer = 0;
    spawnCars();
  }

  const remaining = [];
  for (const car of state.cars) {
    updateCar(car, dt);
    if (car.done) {
      state.completedStats.push([car.pathLength, car.travelTime, car.idleTime]);
      state.delivered += 1;
    } else {
      remaining.push(car);
    }
  }
  state.cars = remaining;
  state.flowRate = calculateFlowRate(state.completedStats, state.spawnAttempts, state.spawnSuccesses);

  if (state.gameTimer >= GAME_DAY_LENGTH) {
    finishLevel();
  }

  renderHudAndBoard();
}

function finishLevel() {
  state.running = false;
  state.ended = true;
  const passed = state.flowRate >= LEVEL_TARGETS[state.level];
  if (passed && state.level < 3 && !state.resultUnlocked) {
    state.unlockedLevels[state.city] = Math.max(state.unlockedLevels[state.city] || 1, state.level + 1);
    saveProgress();
    state.resultUnlocked = true;
  }
  state.message = passed
    ? `Level cleared. ${state.level < 3 ? "Next level unlocked." : "You completed this city."}`
    : "Below target. Reset the level and try a cleaner route.";
  render();
}

function spawnCars() {
  const placed = getPlacedCells();
  if (!placed.length) {
    return;
  }
  const starts = state.markers.filter((marker) => marker.type === "start");
  const ends = state.markers.filter((marker) => marker.type === "end");

  starts.forEach((startMarker) => {
    const endMarker = ends[Math.floor(Math.random() * ends.length)];
    state.spawnAttempts += 1;

    const startCell = findNearestPlacedCell(startMarker);
    const endCell = findNearestPlacedCell(endMarker);

    if (!startCell || !endCell) {
      return;
    }

    const path = findPath(startCell, endCell);
    if (!path.length) {
      return;
    }

    const points = [markerToPoint(startMarker), ...path.map(cellToPoint), markerToPoint(endMarker)];
    state.spawnSuccesses += 1;
    state.cars.push(createCar(points));
  });
}

function createCar(path) {
  const palette = ["#ffd24d", "#5cd5ff", "#ff7367", "#56d870", "#d78cff"];
  return {
    path,
    segment: 1,
    x: path[0].x,
    y: path[0].y,
    speed: CAR_SPEED,
    color: palette[Math.floor(Math.random() * palette.length)],
    done: false,
    travelTime: 0,
    idleTime: 0,
    pathLength: pathDistance(path),
  };
}

function updateCar(car, dt) {
  if (car.done) return;
  if (car.segment >= car.path.length) {
    car.done = true;
    return;
  }

  car.travelTime += dt;

  const target = car.path[car.segment];
  const dx = target.x - car.x;
  const dy = target.y - car.y;
  const dist = Math.hypot(dx, dy);
  const move = car.speed * dt;

  if (dist === 0 || move === 0) {
    car.idleTime += dt;
  }

  if (dist <= move) {
    car.x = target.x;
    car.y = target.y;
    car.segment += 1;
    if (car.segment >= car.path.length) {
      car.done = true;
    }
  } else {
    car.x += (move * dx) / dist;
    car.y += (move * dy) / dist;
  }
}

function getPlacedCells() {
  const cells = [];
  state.grid.forEach((row, rowIndex) => {
    row.forEach((cell, colIndex) => {
      if (cell) {
        cells.push({ row: rowIndex, col: colIndex, cell });
      }
    });
  });
  return cells;
}

function findNearestPlacedCell(marker) {
  const point = markerToPoint(marker);
  let best = null;
  let bestDistance = Infinity;
  for (const entry of getPlacedCells()) {
    const target = cellToPoint(entry);
    const distance = Math.hypot(target.x - point.x, target.y - point.y);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = entry;
    }
  }
  return best;
}

function findPath(startCell, endCell) {
  const startKey = keyFor(startCell.row, startCell.col);
  const targetKey = keyFor(endCell.row, endCell.col);
  if (startKey === targetKey) {
    return [startCell];
  }

  const queue = [[startCell, [startCell]]];
  const visited = new Set([startKey]);

  while (queue.length) {
    const [current, path] = queue.shift();
    const arms = getArms(current.cell);

    for (const [direction, [dr, dc, myArm, theirArm]] of Object.entries(DIRECTION_DELTAS)) {
      if (!arms.includes(myArm)) continue;
      const nextRow = current.row + dr;
      const nextCol = current.col + dc;
      if (nextRow < 0 || nextRow >= state.rows || nextCol < 0 || nextCol >= state.cols) continue;
      const nextCell = state.grid[nextRow][nextCol];
      if (!nextCell) continue;
      if (!getArms(nextCell).includes(theirArm)) continue;

      const nextKey = keyFor(nextRow, nextCol);
      if (visited.has(nextKey)) continue;

      const entry = { row: nextRow, col: nextCol, cell: nextCell, direction };
      const nextPath = [...path, entry];
      if (nextKey === targetKey) {
        return nextPath;
      }
      visited.add(nextKey);
      queue.push([entry, nextPath]);
    }
  }

  return [];
}

function keyFor(row, col) {
  return `${row}:${col}`;
}

function cellToPoint(entry) {
  return { x: entry.col * 100 + 50, y: entry.row * 100 + 50 };
}

function markerToPoint(marker) {
  const rows = state.rows;
  const cols = state.cols;
  if (marker.side === "top") return { x: marker.index * 100 + 50, y: -18 };
  if (marker.side === "bottom") return { x: marker.index * 100 + 50, y: rows * 100 + 18 };
  if (marker.side === "left") return { x: -18, y: marker.index * 100 + 50 };
  return { x: cols * 100 + 18, y: marker.index * 100 + 50 };
}

function pathDistance(path) {
  let total = 0;
  for (let idx = 0; idx < path.length - 1; idx += 1) {
    total += Math.hypot(path[idx + 1].x - path[idx].x, path[idx + 1].y - path[idx].y);
  }
  return total;
}

function render() {
  app.innerHTML = `
    <section class="panel selection-panel">
      <div class="selection-grid">
        <div class="selector-group">
          <div class="panel-header">
            <div>
              <h2>Choose Your City</h2>
              <p>Each city changes difficulty and the shape of the traffic curve.</p>
            </div>
          </div>
          <div class="chip-row">
            ${CITIES.map(renderCityChip).join("")}
          </div>
        </div>
        <div class="selector-group">
          <div class="panel-header compact">
            <div>
              <span class="selector-label">Level Progression</span>
            </div>
            <button class="ghost-btn" data-action="unlock-all">
              ${Object.values(state.unlockedLevels).every((level) => level >= 3) ? "All Unlocked" : "Unlock All"}
            </button>
          </div>
          <div class="chip-row">
            ${[1, 2, 3].map(renderLevelChip).join("")}
          </div>
          <p class="helper-text">
            <strong>Tip:</strong> the mobile library is single-use per run, matching the Python game.
            Rotate three-arm pieces after placing them, and reset if you burn through the toolkit.
          </p>
        </div>
      </div>
    </section>

    <section class="panel hud-panel">
      <div class="panel-header">
        <div>
          <h3>Live Run</h3>
          <p>${state.city} · Level ${state.level} · ${state.levelNote}</p>
        </div>
        <div class="status-pill">${isRushHour(state.gameTimer) ? "Rush Hour" : "Normal Flow"}</div>
      </div>
      <div class="hud-grid">
        ${renderStatCard("Clock", getTimeLabel(state.gameTimer), state.running ? "Simulation live" : "Build before you start", "#5cd5ff")}
        ${renderStatCard("Traffic", `${getCurrentVolume(state.city, state.gameTimer)} vph`, CITIES.find((entry) => entry.name === state.city)?.label || "", "#ffb84f")}
        ${renderStatCard("Flow Rate", state.flowRate.toFixed(2), `Grade ${gradeFromFlow(state.flowRate)}`, flowColor(state.flowRate), true)}
        ${renderStatCard("Delivered", String(state.delivered), `Target ${LEVEL_TARGETS[state.level].toFixed(2)}`, "#56d870")}
      </div>
    </section>

    <section class="panel board-panel">
      <div>
        <div class="panel-header">
          <div>
            <h3>Touch Board</h3>
            <p>${state.message}</p>
          </div>
        </div>
        <div class="action-row">
          <button class="action-btn primary" data-action="toggle-run">${state.running && !state.ended ? "Stop Run" : "Start Run"}</button>
          <button class="action-btn" data-action="pause-run">${state.paused ? "Resume" : "Pause"}</button>
          <button class="action-btn" data-action="rotate-selected">Rotate</button>
          <button class="action-btn warn" data-action="clear-selected">Clear Cell</button>
          <button class="action-btn" data-action="reset-level">Reset Level</button>
        </div>
        <div class="board-shell">
          <div class="board-frame">
            <div
              class="board-grid"
              id="board-grid"
              style="grid-template-columns: repeat(${state.cols}, minmax(0, 1fr));"
            >
              ${renderBoardCells()}
            </div>
            <svg
              class="board-overlay"
              id="board-overlay"
              viewBox="${-40} ${-40} ${state.cols * 100 + 80} ${state.rows * 100 + 80}"
              aria-hidden="true"
            >
              ${renderMarkers()}
              ${renderCars()}
            </svg>
          </div>
        </div>
      </div>

      <div>
        <section class="panel palette-panel">
          <div class="panel-header">
            <div>
              <h3>Intersection Library</h3>
              <p>Each piece can be used once per run, just like the desktop build.</p>
            </div>
          </div>
          <div class="palette-grid">
            ${TOOL_ORDER.map(renderToolCard).join("")}
          </div>
        </section>

        <section class="panel formula-panel">
          <div class="panel-header">
            <div>
              <h3>Flow Rate</h3>
              <p>Fast cars, short routes, and low idle time push the score up.</p>
            </div>
          </div>
          <div class="formula-card">
            <code>Flow Rate = (Vavg / Vlimit) × (Tideal / Tactual) × (1 - Tidle / Tactual)</code>
          </div>
          <div class="formula-list">
            <div class="formula-item" style="color:#5cd5ff">
              <strong>Speed</strong>
              <span>Average speed compared to the speed limit rewards efficient layouts.</span>
            </div>
            <div class="formula-item" style="color:#56d870">
              <strong>Travel Time</strong>
              <span>Cleaner routes score better because actual time stays closer to ideal time.</span>
            </div>
            <div class="formula-item" style="color:#ff7367">
              <strong>Idle Time</strong>
              <span>Blocked or broken paths drain your score fast during peak traffic windows.</span>
            </div>
          </div>
        </section>
      </div>
    </section>

    <section class="panel result-panel">
      ${renderResultBanner()}
      <p class="footer-note">
        Built for phone play. If this opened from a QR code, you are already in the live mobile demo.
      </p>
    </section>
  `;

  bindActions();
}

function renderCityChip(entry) {
  return `
    <button class="chip ${state.city === entry.name ? "selected" : ""}" data-city="${entry.name}">
      ${entry.name}
      <small>${entry.label}</small>
    </button>
  `;
}

function renderLevelChip(level) {
  const unlocked = level <= (state.unlockedLevels[state.city] || 1);
  return `
    <button class="chip ${state.level === level ? "selected" : ""} ${unlocked ? "" : "locked"}" data-level="${level}">
      Level ${level}
      <small>${LEVELS[level].note}</small>
    </button>
  `;
}

function renderStatCard(label, value, sub, color, meter = false) {
  return `
    <article class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value" style="color:${color}">${value}</div>
      <div class="stat-sub">${sub}</div>
      ${meter ? `<div class="flow-meter"><span style="width:${Math.min(state.flowRate, 1) * 100}%; background:${color}"></span></div>` : ""}
    </article>
  `;
}

function renderBoardCells() {
  return state.grid
    .flatMap((row, rowIndex) =>
      row.map((cell, colIndex) => {
        const selected = state.selectedCell?.row === rowIndex && state.selectedCell?.col === colIndex;
        const hasMarker = cellHasMarker(rowIndex, colIndex);
        return `
          <button
            class="cell ${cell ? "" : "empty"} ${hasMarker ? "edge-slot" : ""} ${selected ? "selected" : ""}"
            data-cell="${rowIndex}:${colIndex}"
            aria-label="Grid cell ${rowIndex + 1}, ${colIndex + 1}"
          >
            ${cell ? drawTile(cell.type, cell.rotation) : hasMarker ? "" : '<span class="cell-hint">Place</span>'}
          </button>
        `;
      }),
    )
    .join("");
}

function renderMarkers() {
  return state.markers
    .map((marker) => {
      const point = markerToPoint(marker);
      const fill = marker.type === "start" ? "#56d870" : "#ff7367";
      const label = marker.type === "start" ? "IN" : `OUT ${marker.label}`;
      const { x: textX, y: textY, anchor } = markerLabelPosition(marker, point);
      return `
        <g class="marker-ring">
          <line x1="${point.x}" y1="${point.y}" x2="${clamp(point.x, 0, state.cols * 100)}" y2="${clamp(point.y, 0, state.rows * 100)}" stroke="${fill}" stroke-width="5" opacity="0.82" />
          <circle cx="${point.x}" cy="${point.y}" r="18" fill="${fill}" stroke="#ffffff" stroke-width="4" />
          <text x="${point.x}" y="${point.y + 6}" fill="#07131f" font-size="12" font-family="SF Mono, monospace" font-weight="800" text-anchor="middle">
            ${marker.type === "start" ? "S" : marker.label}
          </text>
          <text x="${textX}" y="${textY}" fill="${fill}" font-size="13" font-family="SF Mono, monospace" font-weight="800" text-anchor="${anchor}">
            ${label}
          </text>
        </g>
      `;
    })
    .join("");
}

function markerLabelPosition(marker, point) {
  if (marker.side === "left") {
    return { x: -38, y: point.y + 5, anchor: "end" };
  }
  if (marker.side === "right") {
    return { x: state.cols * 100 + 38, y: point.y + 5, anchor: "start" };
  }
  if (marker.side === "top") {
    if (marker.index === 0) {
      return { x: point.x - 18, y: -38, anchor: "end" };
    }
    if (marker.index === state.cols - 1) {
      return { x: point.x + 18, y: -38, anchor: "start" };
    }
    return { x: point.x, y: -38, anchor: "middle" };
  }
  if (marker.index === 0) {
    return { x: point.x - 20, y: state.rows * 100 + 32, anchor: "end" };
  }
  if (marker.index === state.cols - 1) {
    return { x: point.x + 20, y: state.rows * 100 + 32, anchor: "start" };
  }
  return { x: point.x, y: state.rows * 100 + 38, anchor: "middle" };
}

function cellHasMarker(row, col) {
  return state.markers.some((marker) => {
    if (marker.side === "top") return row === 0 && col === marker.index;
    if (marker.side === "bottom") return row === state.rows - 1 && col === marker.index;
    if (marker.side === "left") return row === marker.index && col === 0;
    return row === marker.index && col === state.cols - 1;
  });
}

function renderCars() {
  return state.cars
    .map(
      (car) => `
        <g transform="translate(${car.x}, ${car.y})">
          <rect x="-8" y="-5" width="16" height="10" rx="3" fill="${car.color}" stroke="#07131f" stroke-width="2" />
        </g>
      `,
    )
    .join("");
}

function renderToolCard(toolKey) {
  const tool = TOOLS[toolKey];
  const spent = isToolSpent(state.spentTools, toolKey);
  const selected = state.selectedTool === toolKey && !spent;
  return `
    <button class="tool-card ${selected ? "selected" : ""} ${spent ? "spent" : ""}" data-tool="${toolKey}" ${spent ? "disabled" : ""}>
      ${drawTile(toolKey, 0)}
      <div>
        <h4>${tool.label}</h4>
        <p>${tool.description}</p>
        <span class="tool-state">${spent ? "Used this run" : "Available"}</span>
      </div>
    </button>
  `;
}

function renderResultBanner() {
  const passed = state.flowRate >= LEVEL_TARGETS[state.level];
  const title = state.ended ? (passed ? "Level Clear" : "Try Another Layout") : "How To Win";
  const body = state.ended
    ? passed
      ? state.level < 3
        ? "You hit the target flow rate and unlocked the next level for this city."
        : "You cleared the hardest level in this city. Try a different traffic profile next."
      : "Your network lost too much speed or left routes disconnected. Reset and rebuild with fewer dead ends."
    : "Use the live traffic curve, keep all markers connected, and aim for the target score before the one-minute day ends.";
  return `
    <article class="result-banner ${passed ? "good" : "bad"}">
      <h3>${title}</h3>
      <p>${body}</p>
    </article>
  `;
}

function renderBoardAndPalette() {
  const boardGrid = document.getElementById("board-grid");
  const boardOverlay = document.getElementById("board-overlay");
  if (boardGrid && boardOverlay) {
    boardGrid.innerHTML = renderBoardCells();
    boardOverlay.setAttribute("viewBox", `${-40} ${-40} ${state.cols * 100 + 80} ${state.rows * 100 + 80}`);
    boardOverlay.innerHTML = `${renderMarkers()}${renderCars()}`;
  }
  const palette = document.querySelector(".palette-grid");
  if (palette) {
    palette.innerHTML = TOOL_ORDER.map(renderToolCard).join("");
  }
  renderResultOnly();
  bindActions();
}

function renderPaletteOnly() {
  const palette = document.querySelector(".palette-grid");
  if (palette) {
    palette.innerHTML = TOOL_ORDER.map(renderToolCard).join("");
  }
  renderResultOnly();
  bindActions();
}

function renderHudAndBoard() {
  const hud = document.querySelector(".hud-grid");
  if (hud) {
    hud.innerHTML = [
      renderStatCard("Clock", getTimeLabel(state.gameTimer), state.running ? "Simulation live" : "Build before you start", "#5cd5ff"),
      renderStatCard("Traffic", `${getCurrentVolume(state.city, state.gameTimer)} vph`, CITIES.find((entry) => entry.name === state.city)?.label || "", "#ffb84f"),
      renderStatCard("Flow Rate", state.flowRate.toFixed(2), `Grade ${gradeFromFlow(state.flowRate)}`, flowColor(state.flowRate), true),
      renderStatCard("Delivered", String(state.delivered), `Target ${LEVEL_TARGETS[state.level].toFixed(2)}`, "#56d870"),
    ].join("");
  }
  const overlay = document.getElementById("board-overlay");
  if (overlay) {
    overlay.innerHTML = `${renderMarkers()}${renderCars()}`;
  }
  renderResultOnly();
}

function renderResultOnly() {
  const boardHeader = document.querySelector(".board-panel .panel-header p");
  if (boardHeader) {
    boardHeader.textContent = state.message;
  }
  const actionButtons = document.querySelectorAll(".action-row .action-btn");
  if (actionButtons.length) {
    actionButtons[0].textContent = state.running && !state.ended ? "Stop Run" : "Start Run";
    actionButtons[1].textContent = state.paused ? "Resume" : "Pause";
  }
  const rushPill = document.querySelector(".hud-panel .status-pill");
  if (rushPill) {
    rushPill.textContent = isRushHour(state.gameTimer) ? "Rush Hour" : "Normal Flow";
  }
  const resultPanel = document.querySelector(".result-panel");
  if (resultPanel) {
    resultPanel.innerHTML = `${renderResultBanner()}<p class="footer-note">Built for phone play. If this opened from a QR code, you are already in the live mobile demo.</p>`;
  }
}

function bindActions() {
  app.querySelectorAll("[data-city]").forEach((button) => {
    button.onclick = () => selectCity(button.dataset.city);
  });
  app.querySelectorAll("[data-level]").forEach((button) => {
    button.onclick = () => selectLevel(Number(button.dataset.level));
  });
  app.querySelectorAll("[data-tool]").forEach((button) => {
    button.onclick = () => setTool(button.dataset.tool);
  });
  app.querySelectorAll("[data-cell]").forEach((button) => {
    button.onclick = () => {
      const [row, col] = button.dataset.cell.split(":").map(Number);
      handleCellPress(row, col);
    };
  });
  app.querySelectorAll("[data-action]").forEach((button) => {
    button.onclick = () => {
      const action = button.dataset.action;
      if (action === "toggle-run") toggleRun();
      if (action === "pause-run") pauseRun();
      if (action === "rotate-selected") rotateSelected();
      if (action === "clear-selected") clearSelected();
      if (action === "reset-level") resetLevel();
      if (action === "unlock-all") unlockAllLevels();
    };
  });
}

function flowColor(flow) {
  if (flow >= 0.75) return "#56d870";
  if (flow >= 0.45) return "#ffb84f";
  return "#ff7367";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function drawTile(type, rotation = 0) {
  const tool = TOOLS[type];
  const arms = tool.rotatable ? getArms({ type, rotation }) : tool.arms;
  const lines = [];
  if (arms.includes("N")) lines.push('<line x1="50" y1="8" x2="50" y2="42" stroke="rgba(255,255,255,0.92)" stroke-width="10" stroke-linecap="round" />');
  if (arms.includes("S")) lines.push('<line x1="50" y1="58" x2="50" y2="92" stroke="rgba(255,255,255,0.92)" stroke-width="10" stroke-linecap="round" />');
  if (arms.includes("W")) lines.push('<line x1="8" y1="50" x2="42" y2="50" stroke="rgba(255,255,255,0.92)" stroke-width="10" stroke-linecap="round" />');
  if (arms.includes("E")) lines.push('<line x1="58" y1="50" x2="92" y2="50" stroke="rgba(255,255,255,0.92)" stroke-width="10" stroke-linecap="round" />');

  const accent = tool.color;
  let center = `<circle cx="50" cy="50" r="10" fill="${accent}" stroke="#07131f" stroke-width="4" />`;

  if (tool.kind === "roundabout") {
    center = `
      <circle cx="50" cy="50" r="15" fill="none" stroke="${accent}" stroke-width="6" />
      <circle cx="50" cy="50" r="7" fill="#07131f" />
    `;
  } else if (tool.kind === "cloverleaf") {
    center = `
      <circle cx="34" cy="34" r="8" fill="none" stroke="${accent}" stroke-width="4" />
      <circle cx="66" cy="34" r="8" fill="none" stroke="${accent}" stroke-width="4" />
      <circle cx="34" cy="66" r="8" fill="none" stroke="${accent}" stroke-width="4" />
      <circle cx="66" cy="66" r="8" fill="none" stroke="${accent}" stroke-width="4" />
      <circle cx="50" cy="50" r="9" fill="${accent}" stroke="#07131f" stroke-width="4" />
    `;
  } else if (tool.kind === "diamond") {
    center = `
      <polygon points="50,30 70,50 50,70 30,50" fill="none" stroke="${accent}" stroke-width="5" />
      <circle cx="50" cy="50" r="6" fill="${accent}" />
    `;
  } else if (tool.kind === "trumpet") {
    const offset = trumpetOffset(rotation);
    center = `
      <circle cx="50" cy="50" r="9" fill="${accent}" stroke="#07131f" stroke-width="4" />
      <circle cx="${offset.x}" cy="${offset.y}" r="10" fill="none" stroke="${accent}" stroke-width="4" />
    `;
  } else if (tool.kind === "y") {
    center = `
      <circle cx="50" cy="50" r="8" fill="${accent}" stroke="#07131f" stroke-width="4" />
      <line x1="41" y1="41" x2="59" y2="59" stroke="${accent}" stroke-width="4" stroke-linecap="round" />
      <line x1="59" y1="41" x2="41" y2="59" stroke="${accent}" stroke-width="4" stroke-linecap="round" />
    `;
  } else if (tool.kind === "partial") {
    const loops = partialLoops(rotation);
    center = `
      <circle cx="50" cy="50" r="9" fill="${accent}" stroke="#07131f" stroke-width="4" />
      <circle cx="${loops[0].x}" cy="${loops[0].y}" r="8" fill="none" stroke="${accent}" stroke-width="4" />
      <circle cx="${loops[1].x}" cy="${loops[1].y}" r="8" fill="none" stroke="${accent}" stroke-width="4" />
    `;
  }

  return `
    <svg class="tile-svg" viewBox="0 0 100 100" aria-hidden="true">
      ${lines.join("")}
      ${center}
    </svg>
  `;
}

function trumpetOffset(rotation) {
  return [
    { x: 50, y: 76 },
    { x: 24, y: 50 },
    { x: 50, y: 24 },
    { x: 76, y: 50 },
  ][rotation % 4];
}

function partialLoops(rotation) {
  return [
    [
      { x: 32, y: 32 },
      { x: 68, y: 68 },
    ],
    [
      { x: 32, y: 68 },
      { x: 68, y: 32 },
    ],
    [
      { x: 68, y: 68 },
      { x: 32, y: 32 },
    ],
    [
      { x: 68, y: 32 },
      { x: 32, y: 68 },
    ],
  ][rotation % 4];
}
