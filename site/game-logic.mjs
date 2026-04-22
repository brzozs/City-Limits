export const CITY_DATA = {
  "New York City": [412, 278, 198, 165, 189, 367, 756, 1823, 2345, 1987, 1654, 1734, 1876, 1923, 1987, 2234, 2678, 3012, 2756, 2123, 1678, 1234, 876, 567],
  "Los Angeles": [389, 245, 167, 134, 198, 534, 1234, 2345, 2678, 2123, 1876, 1987, 2134, 2234, 2456, 2876, 3234, 3456, 3123, 2567, 1987, 1456, 987, 567],
  "Chicago": [356, 223, 156, 123, 167, 423, 987, 2012, 2345, 1876, 1567, 1654, 1789, 1876, 1954, 2234, 2678, 2867, 2456, 1876, 1456, 1089, 723, 445],
};

export const GLOBAL_MAX_VOLUME = 3456;
export const GAME_DAY_LENGTH = 75;
export const START_TIME = (GAME_DAY_LENGTH * 7) / 24;
export const CAR_SPEED = 80;
export const LEVEL_TARGETS = { 1: 0.45, 2: 0.55, 3: 0.65 };

// Mobile-tuned spawn windows that preserve the Python game's relative difficulty.
export const LEVEL_INTERVALS = {
  1: [1.4, 5.8],
  2: [1.0, 4.4],
  3: [0.65, 2.8],
};

export const CITY_DIFFICULTY = {
  "New York City": 1.0,
  "Los Angeles": 0.85,
  "Chicago": 1.2,
};

export const CITIES = [
  { name: "New York City", label: "Balanced", color: "#5cd5ff" },
  { name: "Los Angeles", label: "Hard", color: "#ff7367" },
  { name: "Chicago", label: "Easy", color: "#56d870" },
];

export const LEVELS = {
  1: {
    rows: 1,
    cols: 3,
    markers: [
      { type: "start", side: "left", index: 0, label: "S" },
      { type: "end", side: "right", index: 0, label: "1" },
    ],
    note: "2 travel points",
  },
  2: {
    rows: 2,
    cols: 3,
    markers: [
      { type: "start", side: "left", index: 0, label: "S" },
      { type: "end", side: "right", index: 1, label: "1" },
      { type: "end", side: "top", index: 2, label: "2" },
    ],
    note: "3 travel points",
  },
  3: {
    rows: 3,
    cols: 3,
    markers: [
      { type: "start", side: "left", index: 1, label: "S1" },
      { type: "start", side: "top", index: 2, label: "S2" },
      { type: "end", side: "right", index: 1, label: "1" },
      { type: "end", side: "bottom", index: 0, label: "2" },
    ],
    note: "4 travel points",
  },
};

export const TOOL_ORDER = [
  "T_INTERSECTION",
  "TRUMPET",
  "Y_INTERSECTION",
  "FOUR_WAY",
  "ROUNDABOUT",
  "CLOVERLEAF",
  "DIAMOND",
  "PARTIAL_CLOVERLEAF",
];

export const TOOLS = {
  T_INTERSECTION: {
    label: "T-Intersection",
    description: "Three-arm starter tile. Rotate after placing to match the route.",
    color: "#5cd5ff",
    missingByRotation: ["S", "W", "N", "E"],
    kind: "tee",
    rotatable: true,
  },
  TRUMPET: {
    label: "Trumpet",
    description: "Three-arm highway merge with one looping branch.",
    color: "#ffb84f",
    missingByRotation: ["S", "W", "N", "E"],
    kind: "trumpet",
    rotatable: true,
  },
  Y_INTERSECTION: {
    label: "Y-Intersection",
    description: "Three-arm split for angled traffic decisions.",
    color: "#56d870",
    missingByRotation: ["S", "W", "N", "E"],
    kind: "y",
    rotatable: true,
  },
  FOUR_WAY: {
    label: "4-Way",
    description: "Every arm is open. Reliable for clean starter routes.",
    color: "#5cd5ff",
    arms: ["N", "S", "E", "W"],
    kind: "cross",
    rotatable: false,
  },
  ROUNDABOUT: {
    label: "Roundabout",
    description: "All arms connect through a calm circular core.",
    color: "#56d870",
    arms: ["N", "S", "E", "W"],
    kind: "roundabout",
    rotatable: false,
  },
  CLOVERLEAF: {
    label: "Cloverleaf",
    description: "High-capacity interchange with a loop-heavy visual.",
    color: "#ffb84f",
    arms: ["N", "S", "E", "W"],
    kind: "cloverleaf",
    rotatable: false,
  },
  DIAMOND: {
    label: "Diamond",
    description: "Compact all-way option with a distinct center diamond.",
    color: "#ff7367",
    arms: ["N", "S", "E", "W"],
    kind: "diamond",
    rotatable: false,
  },
  PARTIAL_CLOVERLEAF: {
    label: "Partial Cloverleaf",
    description: "Three-arm hybrid with two loop accents.",
    color: "#ff7367",
    missingByRotation: ["S", "W", "N", "E"],
    kind: "partial",
    rotatable: true,
  },
};

export const DIRECTION_DELTAS = {
  up: [-1, 0, "N", "S"],
  down: [1, 0, "S", "N"],
  left: [0, -1, "W", "E"],
  right: [0, 1, "E", "W"],
};

export function createSpentTools() {
  return [];
}

export function spendTool(spentTools, toolKey) {
  if (spentTools.includes(toolKey)) {
    return spentTools;
  }
  return [...spentTools, toolKey];
}

export function isToolSpent(spentTools, toolKey) {
  return spentTools.includes(toolKey);
}

export function getArms(tile) {
  const tool = TOOLS[tile.type];
  if (!tool.rotatable) {
    return tool.arms;
  }
  const missing = tool.missingByRotation[tile.rotation % 4];
  return ["N", "S", "E", "W"].filter((arm) => arm !== missing);
}

export function calculateFlowRate(completedStats, spawnAttempts, spawnSuccesses) {
  if (!completedStats.length) return 0;

  const totals = completedStats.reduce(
    (acc, [distance, travelTime, idleTime]) => {
      acc.distance += distance;
      acc.travelTime += travelTime;
      acc.idleTime += idleTime;
      return acc;
    },
    { distance: 0, travelTime: 0, idleTime: 0 },
  );

  if (totals.travelTime === 0) return 0;

  const vAvg = totals.distance / totals.travelTime;
  const vRatio = Math.min(vAvg / CAR_SPEED, 1);
  const tIdeal = totals.distance / CAR_SPEED;
  const tRatio = Math.min(tIdeal / totals.travelTime, 1);
  const idleRatio = 1 - totals.idleTime / totals.travelTime;
  const base = vRatio * tRatio * idleRatio;

  if (spawnAttempts > 0) {
    return base * (spawnSuccesses / spawnAttempts);
  }
  return base;
}

export function getSpawnInterval(city, gameTimer, level) {
  const values = CITY_DATA[city] || CITY_DATA["New York City"];
  const timeFrac = ((gameTimer % GAME_DAY_LENGTH) / GAME_DAY_LENGTH) * 24;
  const hour = Math.floor(timeFrac) % 24;
  const nextHour = (hour + 1) % 24;
  const blend = timeFrac - Math.floor(timeFrac);
  const volume = values[hour] * (1 - blend) + values[nextHour] * blend;
  const [minInterval, maxInterval] = LEVEL_INTERVALS[level];
  const normalized = Math.min(volume / GLOBAL_MAX_VOLUME, 1);
  const baseInterval = maxInterval - normalized * (maxInterval - minInterval);
  const difficulty = CITY_DIFFICULTY[city] ?? 1;
  return Math.max(0.45, baseInterval * difficulty);
}

export function getCurrentVolume(city, gameTimer) {
  const values = CITY_DATA[city] || CITY_DATA["New York City"];
  const timeFrac = ((gameTimer % GAME_DAY_LENGTH) / GAME_DAY_LENGTH) * 24;
  const hour = Math.floor(timeFrac) % 24;
  const nextHour = (hour + 1) % 24;
  const blend = timeFrac - Math.floor(timeFrac);
  return Math.round(values[hour] * (1 - blend) + values[nextHour] * blend);
}

export function getTimeLabel(gameTimer) {
  const timeFrac = ((gameTimer % GAME_DAY_LENGTH) / GAME_DAY_LENGTH) * 24;
  const hours = Math.floor(timeFrac) % 24;
  const minutes = Math.floor((timeFrac - hours) * 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function isRushHour(gameTimer) {
  const hour = Number.parseInt(getTimeLabel(gameTimer).slice(0, 2), 10);
  return (hour >= 7 && hour < 10) || (hour >= 16 && hour < 19);
}

export function gradeFromFlow(flow) {
  if (flow >= 0.8) return "A";
  if (flow >= 0.65) return "B";
  if (flow >= 0.45) return "C";
  if (flow >= 0.25) return "D";
  return "F";
}
