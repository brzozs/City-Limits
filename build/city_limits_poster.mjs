const fs = await import("node:fs/promises");
const path = await import("node:path");
const { Presentation, PresentationFile } = await import("@oai/artifact-tool");

const W = 4608;
const H = 3456;

const DECK_ID = "city-limits-poster";
const OUT_DIR = "/Users/sebastian/Library/Mobile Documents/com~apple~CloudDocs/School/GitHub/City-Limits/outputs/city-limits-poster";
const ASSET_DIR = path.join(OUT_DIR, "assets");
const PLAY_URL = "https://brzozs.github.io/City-Limits/";
const SCRATCH_DIR = path.resolve(process.env.PPTX_SCRATCH_DIR || path.join("tmp", "slides", DECK_ID));
const PREVIEW_DIR = path.join(SCRATCH_DIR, "preview");
const VERIFICATION_DIR = path.join(SCRATCH_DIR, "verification");
const INSPECT_PATH = path.join(SCRATCH_DIR, "inspect.ndjson");

const BG = "#F6F1E8";
const BG2 = "#EDF4F8";
const PANEL = "#FFFFFF";
const PANEL_SOFT = "#F4F8FB";
const PANEL_DARK = "#EEF3F7";
const CARD = "#F6FAFD";
const STROKE = "#C7D6E2";
const GRID = "#D7E2EA";
const TEXT = "#102437";
const MUTED = "#4F6577";
const SUBTLE = "#728599";
const CYAN = "#2B84C6";
const AMBER = "#D9982B";
const GREEN = "#43A36A";
const RED = "#D8695F";
const WHITE = "#FFFFFF";
const TRANSPARENT = "#00000000";
const BAR_BG = "#D7E4ED";

const TITLE_FACE = "Poppins";
const BODY_FACE = "Lato";
const MONO_FACE = "Aptos Mono";

const HOURS = Array.from({ length: 24 }, (_, idx) => String(idx).padStart(2, "0"));

const TRAFFIC = {
  "New York City": [412, 278, 198, 165, 189, 367, 756, 1823, 2345, 1987, 1654, 1734, 1876, 1923, 1987, 2234, 2678, 3012, 2756, 2123, 1678, 1234, 876, 567],
  "Los Angeles": [389, 245, 167, 134, 198, 534, 1234, 2345, 2678, 2123, 1876, 1987, 2134, 2234, 2456, 2876, 3234, 3456, 3123, 2567, 1987, 1456, 987, 567],
  "Chicago": [356, 223, 156, 123, 167, 423, 987, 2012, 2345, 1876, 1567, 1654, 1789, 1876, 1954, 2234, 2678, 2867, 2456, 1876, 1456, 1089, 723, 445],
};

const DIFFICULTY = {
  "New York City": { label: "Normal", color: CYAN, peak: "3012 vph peak" },
  "Los Angeles": { label: "Hard", color: RED, peak: "3456 vph peak" },
  "Chicago": { label: "Easy", color: GREEN, peak: "2867 vph peak" },
};

const inspectRecords = [];

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function ensureDirs() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(SCRATCH_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(VERIFICATION_DIR, { recursive: true });
}

function lineConfig(fill = TRANSPARENT, width = 0) {
  return { style: "solid", fill, width };
}

function record(kind, payload) {
  inspectRecords.push({ kind, ...payload });
}

function addShape(slide, geometry, x, y, w, h, fill = TRANSPARENT, lineFill = TRANSPARENT, lineWidth = 0, meta = {}) {
  const shape = slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineConfig(lineFill, lineWidth),
  });
  if (meta.slideNo) {
    record("shape", {
      slide: meta.slideNo,
      role: meta.role || geometry,
      bbox: [x, y, w, h],
      id: shape?.id || `${meta.slideNo}-${meta.role || geometry}`,
    });
  }
  return shape;
}

function addText(
  slide,
  slideNo,
  text,
  x,
  y,
  w,
  h,
  {
    size = 28,
    color = TEXT,
    bold = false,
    face = BODY_FACE,
    align = "left",
    fill = TRANSPARENT,
    lineFill = TRANSPARENT,
    lineWidth = 0,
    role = "text",
    autoFit = "shrinkText",
  } = {},
) {
  const box = addShape(slide, "rect", x, y, w, h, fill, lineFill, lineWidth, { slideNo, role });
  box.text = String(text ?? "");
  box.text.fontSize = size;
  box.text.color = color;
  box.text.bold = Boolean(bold);
  box.text.typeface = face;
  box.text.alignment = align;
  box.text.verticalAlignment = "top";
  box.text.insets = { left: 0, right: 0, top: 0, bottom: 0 };
  if (autoFit) {
    box.text.autoFit = autoFit;
  }
  record("textbox", {
    slide: slideNo,
    role,
    text: String(text ?? ""),
    bbox: [x, y, w, h],
    id: box?.id || `${slideNo}-${role}`,
  });
  return box;
}

async function addImage(slide, slideNo, filePath, x, y, w, h, { fit = "cover", role = "image", alt = "Poster image" } = {}) {
  const image = slide.images.add({
    blob: await readImageBlob(filePath),
    fit,
    alt,
  });
  image.position = { left: x, top: y, width: w, height: h };
  record("image", {
    slide: slideNo,
    role,
    bbox: [x, y, w, h],
    path: filePath,
    id: image?.id || `${slideNo}-${role}`,
  });
  return image;
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  return {
    r: Number.parseInt(value.slice(0, 2), 16),
    g: Number.parseInt(value.slice(2, 4), 16),
    b: Number.parseInt(value.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }) {
  return `#${[r, g, b].map((part) => Math.max(0, Math.min(255, Math.round(part))).toString(16).padStart(2, "0")).join("")}`;
}

function mixColors(a, b, t) {
  const from = hexToRgb(a);
  const to = hexToRgb(b);
  return rgbToHex({
    r: from.r + (to.r - from.r) * t,
    g: from.g + (to.g - from.g) * t,
    b: from.b + (to.b - from.b) * t,
  });
}

function addPanel(slide, slideNo, x, y, w, h, accent = CYAN) {
  addShape(slide, "roundRect", x, y, w, h, PANEL, STROKE, 3, { slideNo, role: "panel" });
  addShape(slide, "rect", x, y, w, 10, accent, TRANSPARENT, 0, { slideNo, role: "panel accent" });
}

function addTag(slide, slideNo, text, x, y, w, accent, fill = "#17324A") {
  addShape(slide, "roundRect", x, y, w, 58, fill, accent, 2, { slideNo, role: "tag" });
  addText(slide, slideNo, text, x + 22, y + 13, w - 44, 30, {
    size: 22,
    color: WHITE,
    bold: true,
    face: BODY_FACE,
    role: "tag text",
  });
}

function addMetricCard(slide, slideNo, x, y, w, h, value, label, accent) {
  addShape(slide, "roundRect", x, y, w, h, CARD, STROKE, 2.5, { slideNo, role: "metric card" });
  addShape(slide, "rect", x, y, 8, h, accent, TRANSPARENT, 0, { slideNo, role: "metric accent" });
  addText(slide, slideNo, value, x + 30, y + 24, w - 60, 88, {
    size: 70,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "metric value",
  });
  addText(slide, slideNo, label, x + 30, y + 108, w - 60, 70, {
    size: 28,
    color: MUTED,
    face: BODY_FACE,
    role: "metric label",
  });
}

function addFeatureRow(slide, slideNo, x, y, w, h, title, body, accent, fill = WHITE) {
  addShape(slide, "roundRect", x, y, w, h, fill, STROKE, 2, { slideNo, role: "feature row" });
  addShape(slide, "rect", x, y, 10, h, accent, TRANSPARENT, 0, { slideNo, role: "feature accent" });
  addText(slide, slideNo, title, x + 28, y + 18, w - 56, 32, {
    size: 26,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "feature title",
  });
  addText(slide, slideNo, body, x + 28, y + 54, w - 56, h - 70, {
    size: 20,
    color: MUTED,
    face: BODY_FACE,
    role: "feature body",
  });
}

function addStepCard(slide, slideNo, x, y, w, h, step, title, body, accent) {
  addShape(slide, "roundRect", x, y, w, h, CARD, STROKE, 2, { slideNo, role: "step card" });
  addShape(slide, "ellipse", x + 28, y + 28, 52, 52, accent, TRANSPARENT, 0, { slideNo, role: "step badge" });
  addText(slide, slideNo, step, x + 43, y + 40, 22, 24, {
    size: 22,
    color: BG,
    bold: true,
    face: MONO_FACE,
    align: "center",
    role: "step number",
  });
  addText(slide, slideNo, title, x + 98, y + 28, w - 124, 36, {
    size: 30,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "step title",
  });
  addText(slide, slideNo, body, x + 28, y + 96, w - 56, h - 120, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "step body",
  });
}

function addHeatmapRow(slide, slideNo, x, y, w, city, accent) {
  const labelW = 270;
  const peakW = 180;
  const cellsX = x + labelW;
  const cellY = y + 50;
  const cellH = 32;
  const values = TRAFFIC[city];
  const peak = Math.max(...values);
  const meta = DIFFICULTY[city];

  addText(slide, slideNo, city, x, y, 240, 34, {
    size: 28,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "city label",
  });
  addTag(slide, slideNo, meta.label, x, y + 36, 130, meta.color, "#102132");
  addText(slide, slideNo, meta.peak, x + 144, y + 48, 120, 22, {
    size: 18,
    color: SUBTLE,
    face: MONO_FACE,
    role: "peak label",
  });

  let cursor = cellsX;
  values.forEach((value, idx) => {
    const ratio = value / 3456;
    const cellColor = mixColors(BAR_BG, accent, 0.15 + ratio * 0.85);
    addShape(slide, "roundRect", cursor, cellY, 34, cellH, cellColor, "#27435D", 1, {
      slideNo,
      role: "traffic cell",
    });
    cursor += 40;
    if (idx === 5 || idx === 11 || idx === 17) {
      cursor += 10;
    }
  });

  addText(slide, slideNo, `Peak ${peak}`, x + w - peakW, y + 18, peakW, 34, {
    size: 24,
    color: meta.color,
    bold: true,
    face: MONO_FACE,
    align: "right",
    role: "peak metric",
  });
}

function addAxisLabels(slide, slideNo, x, y) {
  const labels = [
    { hour: "00", offset: 0 },
    { hour: "06", offset: 250 },
    { hour: "12", offset: 500 },
    { hour: "18", offset: 750 },
    { hour: "23", offset: 970 },
  ];
  labels.forEach(({ hour, offset }) => {
    addText(slide, slideNo, hour, x + offset, y, 60, 20, {
      size: 16,
      color: SUBTLE,
      face: MONO_FACE,
      role: "axis label",
    });
  });
}

function addEquationRow(slide, slideNo, x, y, label, body, accent) {
  addShape(slide, "roundRect", x, y, 1540, 118, CARD, STROKE, 2, { slideNo, role: "equation point" });
  addShape(slide, "rect", x, y, 8, 118, accent, TRANSPARENT, 0, { slideNo, role: "equation accent" });
  addText(slide, slideNo, label, x + 32, y + 26, 320, 30, {
    size: 26,
    color: accent,
    bold: true,
    face: MONO_FACE,
    role: "equation label",
  });
  addText(slide, slideNo, body, x + 32, y + 58, 1460, 30, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "equation body",
  });
}

function drawMiniGrid(slide, slideNo, x, y, rows, cols, title, subtitle, accent) {
  addShape(slide, "roundRect", x, y, 450, 620, CARD, STROKE, 2.5, { slideNo, role: "level card" });
  addText(slide, slideNo, title, x + 28, y + 26, 220, 36, {
    size: 32,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "level title",
  });
  addText(slide, slideNo, subtitle, x + 28, y + 74, 394, 54, {
    size: 22,
    color: MUTED,
    face: BODY_FACE,
    role: "level subtitle",
  });

  const cell = 88;
  const gridW = cols * cell;
  const gridH = rows * cell;
  const startX = x + (450 - gridW) / 2;
  const startY = y + 170 + (264 - gridH) / 2;
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      addShape(slide, "rect", startX + col * cell, startY + row * cell, cell - 4, cell - 4, "#DDEAF3", "#B7CBD9", 2, {
        slideNo,
        role: "level grid cell",
      });
    }
  }

  addShape(slide, "ellipse", startX - 26, startY + gridH / 2 - 26, 52, 52, GREEN, WHITE, 2, { slideNo, role: "in marker" });
  addText(slide, slideNo, "IN", startX - 16, startY + gridH / 2 - 12, 30, 20, {
    size: 14,
    color: BG,
    bold: true,
    face: MONO_FACE,
    align: "center",
    role: "in label",
  });
  addShape(slide, "ellipse", startX + gridW - 26, startY + gridH / 2 - 26, 52, 52, RED, WHITE, 2, { slideNo, role: "out marker" });
  addText(slide, slideNo, "OUT", startX + gridW - 16, startY + gridH / 2 - 12, 34, 20, {
    size: 12,
    color: BG,
    bold: true,
    face: MONO_FACE,
    align: "center",
    role: "out label",
  });

  addShape(slide, "roundRect", x + 28, y + 488, 394, 92, PANEL_SOFT, accent, 2, { slideNo, role: "level note" });
  addText(slide, slideNo, subtitle, x + 46, y + 510, 358, 52, {
    size: 22,
    color: TEXT,
    face: BODY_FACE,
    role: "level note text",
  });
}

function addQrPlaceholder(slide, slideNo, x, y, size) {
  addShape(slide, "roundRect", x, y, size, size, WHITE, TEXT, 3, { slideNo, role: "qr placeholder" });
  const corner = 116;
  [
    [x + 40, y + 40],
    [x + size - corner - 40, y + 40],
    [x + 40, y + size - corner - 40],
  ].forEach(([cx, cy]) => {
    addShape(slide, "roundRect", cx, cy, corner, corner, TRANSPARENT, TEXT, 6, { slideNo, role: "qr corner" });
    addShape(slide, "roundRect", cx + 28, cy + 28, 60, 60, TEXT, TRANSPARENT, 0, { slideNo, role: "qr corner fill" });
  });
  addText(slide, slideNo, "QR CODE", x, y + size / 2 - 26, size, 44, {
    size: 44,
    color: TEXT,
    bold: true,
    face: MONO_FACE,
    align: "center",
    role: "qr label",
  });
}

async function addQrCode(slide, slideNo, filePath, x, y, size) {
  addShape(slide, "roundRect", x, y, size, size, WHITE, TEXT, 3, { slideNo, role: "qr frame" });
  addShape(slide, "roundRect", x + 20, y + 20, size - 40, size - 40, WHITE, TRANSPARENT, 0, { slideNo, role: "qr backing" });
  await addImage(slide, slideNo, filePath, x + 24, y + 24, size - 48, size - 48, {
    fit: "contain",
    role: "qr image",
    alt: "QR code for the live City Limits mobile demo",
  });
}

function addBackground(slide, slideNo) {
  slide.background.fill = BG;
  addShape(slide, "rect", 0, 0, W, H, BG, TRANSPARENT, 0, { slideNo, role: "background" });

  for (let x = 80; x < W; x += 220) {
    addShape(slide, "rect", x, 0, 2, H, "#D7E2EA99", TRANSPARENT, 0, { slideNo, role: "bg vertical" });
  }
  for (let y = 80; y < H; y += 220) {
    addShape(slide, "rect", 0, y, W, 2, "#E2EAF088", TRANSPARENT, 0, { slideNo, role: "bg horizontal" });
  }

  addShape(slide, "ellipse", -320, -280, 1600, 1200, "#D9EBF680", TRANSPARENT, 0, { slideNo, role: "bg glow" });
  addShape(slide, "ellipse", 2800, -240, 1800, 1200, "#F7E4CC88", TRANSPARENT, 0, { slideNo, role: "bg glow" });
  addShape(slide, "ellipse", 2200, 2300, 1600, 900, "#DDEFE380", TRANSPARENT, 0, { slideNo, role: "bg glow" });
  addShape(slide, "roundRect", 0, H - 180, W, 180, "#EEF3F7CC", TRANSPARENT, 0, { slideNo, role: "footer fade" });
}

async function buildPoster() {
  const slideNo = 1;
  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  const slide = presentation.slides.add();
  addBackground(slide, slideNo);

  const M = 120;
  const G = 48;

  const topY = 120;
  const topH = 1240;
  const leftTopW = 1710;
  const rightTopX = M + leftTopW + G;
  const rightTopW = 2610;

  const midY = topY + topH + G;
  const midH = 984;
  const mid1W = 1400;
  const mid2W = 1500;
  const mid3W = 1372;
  const mid2X = M + mid1W + G;
  const mid3X = mid2X + mid2W + G;

  const bottomY = midY + midH + G;
  const bottomH = 896;
  const bottom1W = 1700;
  const bottom2W = 1460;
  const bottom3W = 1112;
  const bottom2X = M + bottom1W + G;
  const bottom3X = bottom2X + bottom2W + G;

  addPanel(slide, slideNo, M, topY, leftTopW, topH, CYAN);
  addText(slide, slideNo, "DATA-DRIVEN TRAFFIC SIM", M + 56, topY + 54, 1000, 90, {
    size: 34,
    color: CYAN,
    bold: true,
    face: MONO_FACE,
    role: "kicker",
  });
  addText(slide, slideNo, "City Limits", M + 56, topY + 112, 1480, 170, {
    size: 168,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "title",
  });
  addText(slide, slideNo, "Build better intersections before rush hour wins.", M + 60, topY + 280, 1500, 134, {
    size: 74,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "title",
  });
  addText(
    slide,
    slideNo,
    "City Limits is a top-down traffic simulation game where players choose a city, place real-world intersection types on a constrained grid, and keep flow rates high as hourly traffic surges across the day.",
    M + 60,
    topY + 438,
    1540,
    190,
    {
      size: 38,
      color: MUTED,
      face: BODY_FACE,
      role: "summary",
    },
  );

  addTag(slide, slideNo, "Python", M + 60, topY + 650, 170, CYAN);
  addTag(slide, slideNo, "Pygame", M + 250, topY + 650, 190, AMBER);
  addTag(slide, slideNo, "Real Traffic Data", M + 460, topY + 650, 330, GREEN);

  addText(slide, slideNo, "github.com/brzozs/City-Limits", M + 60, topY + 730, 720, 36, {
    size: 26,
    color: SUBTLE,
    face: MONO_FACE,
    role: "repo",
  });
  addText(slide, slideNo, "Educational traffic design + urban planning", M + 60, topY + 780, 800, 34, {
    size: 26,
    color: CYAN,
    face: BODY_FACE,
    role: "subhead",
  });

  const metricY = topY + 928;
  addMetricCard(slide, slideNo, M + 56, metricY, 500, 220, "3", "city traffic profiles", CYAN);
  addMetricCard(slide, slideNo, M + 584, metricY, 500, 220, "8", "intersection types", AMBER);
  addMetricCard(slide, slideNo, M + 1112, metricY, 500, 220, "3", "progressive levels", GREEN);

  addPanel(slide, slideNo, rightTopX, topY, rightTopW, topH, CYAN);
  const heroInfoX = rightTopX + 28;
  const heroInfoY = topY + 26;
  const heroInfoW = 860;
  const heroInnerH = topH - 52;
  const heroShotX = heroInfoX + heroInfoW + 28;
  const heroShotW = rightTopX + rightTopW - heroShotX - 28;
  addShape(slide, "roundRect", heroInfoX, heroInfoY, heroInfoW, heroInnerH, PANEL_SOFT, STROKE, 2, { slideNo, role: "hero info panel" });
  addText(slide, slideNo, "Live Gameplay", heroInfoX + 38, heroInfoY + 34, heroInfoW - 76, 48, {
    size: 50,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "hero info title",
  });
  addText(slide, slideNo, "A single board shows the live clock, route endpoints, and the intersections players can place to keep traffic moving.", heroInfoX + 38, heroInfoY + 98, heroInfoW - 76, 108, {
    size: 26,
    color: MUTED,
    face: BODY_FACE,
    role: "hero info summary",
  });
  addFeatureRow(slide, slideNo, heroInfoX + 38, heroInfoY + 246, heroInfoW - 76, 154, "Clock + rush hour", "Time-of-day pressure rises and falls through the day, so layouts must survive both calm and peak traffic.", CYAN, WHITE);
  addFeatureRow(slide, slideNo, heroInfoX + 38, heroInfoY + 426, heroInfoW - 76, 154, "Build on the grid", "Players drag intersection types onto open tiles and rotate pieces until a valid route connects every required path.", AMBER, WHITE);
  addFeatureRow(slide, slideNo, heroInfoX + 38, heroInfoY + 606, heroInfoW - 76, 154, "Score the flow", "Efficient paths keep cars moving, reduce idle time, and raise the flow-rate score shown elsewhere on the poster.", GREEN, WHITE);
  addShape(slide, "roundRect", heroShotX, heroInfoY, heroShotW, heroInnerH, PANEL_DARK, STROKE, 2, { slideNo, role: "hero frame" });
  await addImage(slide, slideNo, path.join(ASSET_DIR, "gameplay.png"), heroShotX + 16, heroInfoY + 16, heroShotW - 32, heroInnerH - 32, {
    fit: "cover",
    role: "hero gameplay",
    alt: "City Limits gameplay screenshot",
  });

  addPanel(slide, slideNo, M, midY, mid1W, midH, CYAN);
  addText(slide, slideNo, "Core Loop", M + 40, midY + 34, 360, 42, {
    size: 46,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "panel title",
  });
  addText(slide, slideNo, "Pick a city, build a route network, then survive the traffic curve.", M + 40, midY + 86, 1200, 40, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "panel subtitle",
  });
  addStepCard(slide, slideNo, M + 40, midY + 150, 1320, 180, "1", "Pick a city", "New York City, Los Angeles, and Chicago each change the hourly volume curve and overall difficulty.", CYAN);
  addStepCard(slide, slideNo, M + 40, midY + 350, 1320, 180, "2", "Build the network", "Place and rotate intersections so start and end markers connect through a valid path across the grid.", AMBER);
  addStepCard(slide, slideNo, M + 40, midY + 550, 1320, 180, "3", "React to rush hour", "Morning and evening peaks shorten spawn intervals and punish layouts that create idle time or dead ends.", GREEN);
  addShape(slide, "roundRect", M + 40, midY + 764, 1320, 176, PANEL_SOFT, STROKE, 2, { slideNo, role: "city difficulty strip" });
  addText(slide, slideNo, "City choice changes the challenge.", M + 68, midY + 792, 330, 34, {
    size: 28,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "city difficulty title",
  });
  addText(slide, slideNo, "Each city uses a different hourly traffic curve, so the same road design can feel balanced, punishing, or beginner-friendly depending on where you start.", M + 68, midY + 836, 340, 74, {
    size: 18,
    color: MUTED,
    face: BODY_FACE,
    role: "city difficulty body",
  });
  addTag(slide, slideNo, "New York City", M + 460, midY + 786, 260, CYAN);
  addText(slide, slideNo, "Balanced AM + PM peaks", M + 460, midY + 850, 260, 28, {
    size: 18,
    color: MUTED,
    face: BODY_FACE,
    align: "center",
    role: "city difficulty note",
  });
  addTag(slide, slideNo, "Los Angeles", M + 748, midY + 786, 260, RED);
  addText(slide, slideNo, "Hardest rush-hour load", M + 748, midY + 850, 260, 28, {
    size: 18,
    color: MUTED,
    face: BODY_FACE,
    align: "center",
    role: "city difficulty note",
  });
  addTag(slide, slideNo, "Chicago", M + 1036, midY + 786, 260, GREEN);
  addText(slide, slideNo, "Best first-play starting point", M + 1036, midY + 850, 260, 28, {
    size: 18,
    color: MUTED,
    face: BODY_FACE,
    align: "center",
    role: "city difficulty note",
  });

  addPanel(slide, slideNo, mid2X, midY, mid2W, midH, AMBER);
  addText(slide, slideNo, "Traffic Profiles", mid2X + 40, midY + 34, 420, 42, {
    size: 46,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "panel title",
  });
  addText(slide, slideNo, "Hourly real-world volume data drives spawn timing, rush-hour spikes, and city difficulty.", mid2X + 40, midY + 86, 1320, 42, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "panel subtitle",
  });
  addAxisLabels(slide, slideNo, mid2X + 310, midY + 170);
  addHeatmapRow(slide, slideNo, mid2X + 40, midY + 220, mid2W - 80, "New York City", CYAN);
  addHeatmapRow(slide, slideNo, mid2X + 40, midY + 430, mid2W - 80, "Los Angeles", RED);
  addHeatmapRow(slide, slideNo, mid2X + 40, midY + 640, mid2W - 80, "Chicago", GREEN);
  addShape(slide, "roundRect", mid2X + 40, midY + 810, 1420, 118, CARD, STROKE, 2, { slideNo, role: "traffic caption" });
  addText(slide, slideNo, "Rush-hour design insight: Los Angeles creates the heaviest peak pressure, Chicago is the easiest lane to learn on, and New York stays balanced through both AM and PM surges.", mid2X + 66, midY + 842, 1368, 48, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "traffic caption text",
  });

  addPanel(slide, slideNo, mid3X, midY, mid3W, midH, GREEN);
  addText(slide, slideNo, "Intersection Toolkit", mid3X + 40, midY + 34, 500, 42, {
    size: 46,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "panel title",
  });
  addText(slide, slideNo, "Players drag from a library that mixes everyday junctions with more advanced highway-style designs.", mid3X + 40, midY + 86, 1260, 64, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "panel subtitle",
  });
  addShape(slide, "roundRect", mid3X + 40, midY + 160, mid3W - 80, 610, PANEL_SOFT, STROKE, 2, { slideNo, role: "palette frame" });
  await addImage(slide, slideNo, path.join(ASSET_DIR, "toolkit.png"), mid3X + 58, midY + 178, mid3W - 116, 574, {
    fit: "contain",
    role: "toolkit plate",
    alt: "City Limits intersection toolkit",
  });
  addText(slide, slideNo, "T-Intersections, trumpets, Y-intersections, and partial cloverleafs expand the route design space at higher complexity.", mid3X + 44, midY + 888, mid3W - 88, 46, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "toolkit note",
  });

  addPanel(slide, slideNo, M, bottomY, bottom1W, bottomH, AMBER);
  addText(slide, slideNo, "Scoring Model", M + 40, bottomY + 34, 420, 42, {
    size: 46,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "panel title",
  });
  addText(slide, slideNo, "Flow rate rewards fast movement, efficient routing, and low idle time.", M + 40, bottomY + 86, 1220, 40, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "panel subtitle",
  });
  addShape(slide, "roundRect", M + 40, bottomY + 154, 1620, 210, PANEL_DARK, STROKE, 2.5, { slideNo, role: "equation frame" });
  addText(slide, slideNo, "Flow Rate = (Vavg / Vlimit) x (Tideal / Tactual) x (1 - Tidle / Tactual)", M + 82, bottomY + 220, 1540, 66, {
    size: 42,
    color: TEXT,
    bold: true,
    face: MONO_FACE,
    role: "equation",
  });
  addEquationRow(slide, slideNo, M + 40, bottomY + 402, "Speed", "Average speed is compared against the speed limit so efficient layouts score higher.", CYAN);
  addEquationRow(slide, slideNo, M + 40, bottomY + 538, "Travel Time", "Ideal travel time is measured against actual travel time to reward shorter, cleaner routes.", GREEN);
  addEquationRow(slide, slideNo, M + 40, bottomY + 674, "Idle Time + Routing", "Stopped cars and failed paths drag the score down, so broken networks are visibly punished.", RED);

  addPanel(slide, slideNo, bottom2X, bottomY, bottom2W, bottomH, CYAN);
  addText(slide, slideNo, "Levels Scale Up", bottom2X + 40, bottomY + 34, 420, 42, {
    size: 46,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "panel title",
  });
  addText(slide, slideNo, "Each stage increases the grid size, travel points, and target flow rate.", bottom2X + 40, bottomY + 86, 1200, 40, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "panel subtitle",
  });
  drawMiniGrid(slide, slideNo, bottom2X + 28, bottomY + 170, 1, 3, "Level 1", "2 travel points | target 0.45", CYAN);
  drawMiniGrid(slide, slideNo, bottom2X + 504, bottomY + 170, 2, 3, "Level 2", "3 travel points | target 0.55", AMBER);
  drawMiniGrid(slide, slideNo, bottom2X + 980, bottomY + 170, 3, 3, "Level 3", "4 travel points | target 0.65", GREEN);

  addPanel(slide, slideNo, bottom3X, bottomY, bottom3W, bottomH, GREEN);
  addText(slide, slideNo, "Try The Game", bottom3X + 40, bottomY + 34, 320, 42, {
    size: 46,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    role: "panel title",
  });
  addText(slide, slideNo, "Scan the live phone demo and play City Limits straight from your browser.", bottom3X + 40, bottomY + 86, 1020, 82, {
    size: 24,
    color: MUTED,
    face: BODY_FACE,
    role: "panel subtitle",
  });
  await addQrCode(slide, slideNo, path.join(ASSET_DIR, "play-qr.png"), bottom3X + 276, bottomY + 192, 560);
  addText(slide, slideNo, "Scan to play", bottom3X + 140, bottomY + 780, 832, 40, {
    size: 34,
    color: TEXT,
    bold: true,
    face: TITLE_FACE,
    align: "center",
    role: "cta",
  });
  addText(slide, slideNo, "Live now on GitHub Pages.", bottom3X + 70, bottomY + 826, 972, 34, {
    size: 22,
    color: SUBTLE,
    face: BODY_FACE,
    align: "center",
    role: "cta note",
  });
  addText(slide, slideNo, PLAY_URL, bottom3X + 70, bottomY + 862, 972, 54, {
    size: 22,
    color: CYAN,
    face: MONO_FACE,
    align: "center",
    role: "cta link",
  });

  slide.speakerNotes.setText(
    [
      "City Limits poster.",
      "Sources: README.md, src/main.py, src/intersection.py, src/traffic_data.py, and local screenshots rendered from the game code.",
      `Planned QR destination after publish: ${PLAY_URL}`,
    ].join("\n"),
  );

  return presentation;
}

async function writeInspectArtifact() {
  const lines = [
    JSON.stringify({ kind: "deck", id: DECK_ID, slideCount: 1, slideSize: { width: W, height: H } }),
    JSON.stringify({ kind: "slide", slide: 1, id: "slide-1" }),
    ...inspectRecords.map((entry) => JSON.stringify(entry)),
  ];
  await fs.writeFile(INSPECT_PATH, `${lines.join("\n")}\n`, "utf8");
}

async function saveBlobToFile(blob, filePath) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  await fs.writeFile(filePath, bytes);
}

async function exportDeck(presentation) {
  await ensureDirs();
  await writeInspectArtifact();
  const preview = await presentation.export({ slide: presentation.slides.items[0], format: "png", scale: 0.25 });
  const previewPath = path.join(PREVIEW_DIR, "slide-01.png");
  await saveBlobToFile(preview, previewPath);
  const pptxBlob = await PresentationFile.exportPptx(presentation);
  const pptxPath = path.join(OUT_DIR, "City-Limits-Poster-Print-Friendly.pptx");
  await pptxBlob.save(pptxPath);
  await fs.copyFile(pptxPath, path.join(OUT_DIR, "output.pptx"));
  await fs.copyFile(pptxPath, path.join(OUT_DIR, "City-Limits-Poster.pptx"));
  return { pptxPath, previewPath };
}

const presentation = await buildPoster();
const result = await exportDeck(presentation);
console.log(result.pptxPath);
