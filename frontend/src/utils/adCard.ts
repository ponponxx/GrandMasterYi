export type AdCardStyle = "zen" | "psychology";

type ComposeInput = {
  backgroundDataUrl: string;
  question: string;
  readingText: string;
  appName: string;
  style: AdCardStyle;
};

const STORY_WIDTH = 1080;
const STORY_HEIGHT = 1920;

const loadImage = (src: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("IMAGE_LOAD_FAILED"));
    image.src = src;
  });

const hashSeed = (text: string) => {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
  }
  return h >>> 0;
};

const drawDummyQr = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  seedText: string
) => {
  const modules = 29;
  const quiet = 2;
  const cell = size / (modules + quiet * 2);
  const seed = hashSeed(seedText);

  ctx.fillStyle = "#fff";
  ctx.fillRect(x, y, size, size);
  ctx.fillStyle = "#111";

  const isFinder = (r: number, c: number) => {
    const inTopLeft = r < 7 && c < 7;
    const inTopRight = r < 7 && c >= modules - 7;
    const inBottomLeft = r >= modules - 7 && c < 7;
    return inTopLeft || inTopRight || inBottomLeft;
  };

  const drawFinder = (row0: number, col0: number) => {
    const drawSquare = (offset: number, len: number) => {
      ctx.fillRect(
        x + (col0 + offset + quiet) * cell,
        y + (row0 + offset + quiet) * cell,
        len * cell,
        len * cell
      );
    };
    drawSquare(0, 7);
    ctx.fillStyle = "#fff";
    drawSquare(1, 5);
    ctx.fillStyle = "#111";
    drawSquare(2, 3);
  };

  drawFinder(0, 0);
  drawFinder(0, modules - 7);
  drawFinder(modules - 7, 0);

  for (let r = 0; r < modules; r += 1) {
    for (let c = 0; c < modules; c += 1) {
      if (isFinder(r, c)) {
        continue;
      }
      const n = ((seed + r * 131 + c * 197) ^ (r * c * 17)) & 0xff;
      const fill = n % 3 === 0 || (r + c) % 11 === 0;
      if (!fill) {
        continue;
      }
      ctx.fillRect(x + (c + quiet) * cell, y + (r + quiet) * cell, cell, cell);
    }
  }
};

const wrapText = (
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxLines: number
) => {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return y;
  }
  let line = "";
  let lines = 0;
  for (let i = 0; i < normalized.length; i += 1) {
    const test = line + normalized[i];
    const width = ctx.measureText(test).width;
    if (width > maxWidth && line) {
      ctx.fillText(line, x, y + lines * lineHeight);
      line = normalized[i];
      lines += 1;
      if (lines >= maxLines) {
        break;
      }
    } else {
      line = test;
    }
  }
  if (lines < maxLines && line) {
    if (lines === maxLines - 1 && ctx.measureText(line + "...").width > maxWidth) {
      while (line.length > 0 && ctx.measureText(line + "...").width > maxWidth) {
        line = line.slice(0, -1);
      }
      line += "...";
    }
    ctx.fillText(line, x, y + lines * lineHeight);
    lines += 1;
  }
  return y + lines * lineHeight;
};

export const composeAdCard = async (input: ComposeInput): Promise<string> => {
  const image = await loadImage(input.backgroundDataUrl);
  const canvas = document.createElement("canvas");
  canvas.width = STORY_WIDTH;
  canvas.height = STORY_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("CANVAS_UNAVAILABLE");
  }

  const scale = Math.max(STORY_WIDTH / image.width, STORY_HEIGHT / image.height);
  const dw = image.width * scale;
  const dh = image.height * scale;
  const dx = (STORY_WIDTH - dw) / 2;
  const dy = (STORY_HEIGHT - dh) / 2;
  ctx.drawImage(image, dx, dy, dw, dh);

  const gradient = ctx.createLinearGradient(0, 0, 0, STORY_HEIGHT);
  if (input.style === "psychology") {
    gradient.addColorStop(0, "rgba(18, 26, 38, 0.18)");
    gradient.addColorStop(1, "rgba(6, 10, 16, 0.66)");
  } else {
    gradient.addColorStop(0, "rgba(8, 10, 12, 0.12)");
    gradient.addColorStop(1, "rgba(10, 6, 4, 0.72)");
  }
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, STORY_WIDTH, STORY_HEIGHT);

  const panelX = 72;
  const panelY = 1020;
  const panelW = STORY_WIDTH - 144;
  const panelH = 760;
  ctx.fillStyle = "rgba(0, 0, 0, 0.38)";
  ctx.fillRect(panelX, panelY, panelW, panelH);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.28)";
  ctx.lineWidth = 2;
  ctx.strokeRect(panelX, panelY, panelW, panelH);

  ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
  ctx.font = input.style === "psychology" ? "600 42px Georgia" : "700 46px serif";
  const title = input.style === "psychology" ? "Insight Card" : "卦象心解";
  ctx.fillText(title, panelX + 44, panelY + 70);

  ctx.fillStyle = "rgba(255, 255, 255, 0.82)";
  ctx.font = "500 28px serif";
  const questionY = wrapText(
    ctx,
    `題問：${input.question}`,
    panelX + 44,
    panelY + 130,
    panelW - 88,
    42,
    4
  );

  ctx.fillStyle = "rgba(255, 255, 255, 0.96)";
  ctx.font = "500 34px serif";
  wrapText(
    ctx,
    input.readingText,
    panelX + 44,
    questionY + 28,
    panelW - 88,
    50,
    8
  );

  const qrSize = 190;
  const qrX = panelX + panelW - qrSize - 36;
  const qrY = panelY + panelH - qrSize - 36;
  drawDummyQr(ctx, qrX, qrY, qrSize, `${input.question}|${input.readingText}`);

  ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
  ctx.font = "700 28px sans-serif";
  ctx.fillText(input.appName, panelX + panelW - qrSize - 36, qrY - 22);
  ctx.font = "500 22px sans-serif";
  ctx.fillText("Scan to download (Dummy QR)", panelX + panelW - qrSize - 36, qrY + qrSize + 34);

  return canvas.toDataURL("image/png");
};

export const dataUrlToBlob = async (dataUrl: string): Promise<Blob> => {
  const response = await fetch(dataUrl);
  return response.blob();
};

export const downloadDataUrl = (dataUrl: string, filename: string) => {
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = filename;
  link.click();
};
