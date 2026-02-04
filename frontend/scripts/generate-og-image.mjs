import { createCanvas } from '@napi-rs/canvas';
import { writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// OG image dimensions
const width = 1200;
const height = 630;

const canvas = createCanvas(width, height);
const ctx = canvas.getContext('2d');

// Background gradient (dark zinc to black)
const bgGradient = ctx.createLinearGradient(0, 0, 0, height);
bgGradient.addColorStop(0, '#18181b'); // zinc-900
bgGradient.addColorStop(0.5, '#09090b'); // zinc-950
bgGradient.addColorStop(1, '#18181b'); // zinc-900
ctx.fillStyle = bgGradient;
ctx.fillRect(0, 0, width, height);

// Subtle grid pattern overlay
ctx.strokeStyle = 'rgba(39, 39, 42, 0.5)'; // zinc-800
ctx.lineWidth = 1;
for (let x = 0; x < width; x += 40) {
  ctx.beginPath();
  ctx.moveTo(x, 0);
  ctx.lineTo(x, height);
  ctx.stroke();
}
for (let y = 0; y < height; y += 40) {
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(width, y);
  ctx.stroke();
}

// Glow effect behind text
const glowGradient = ctx.createRadialGradient(600, 280, 0, 600, 280, 400);
glowGradient.addColorStop(0, 'rgba(16, 185, 129, 0.15)'); // emerald-500
glowGradient.addColorStop(1, 'transparent');
ctx.fillStyle = glowGradient;
ctx.fillRect(0, 0, width, height);

// "Molt" in emerald
ctx.font = 'bold 120px sans-serif';
ctx.fillStyle = '#10b981'; // emerald-500
const moltText = 'Molt';
const moltMetrics = ctx.measureText(moltText);

// "Mart" in white
ctx.fillStyle = '#ffffff';
const martText = 'Mart';
const martMetrics = ctx.measureText(martText);

// Center the combined text
const totalWidth = moltMetrics.width + martMetrics.width;
const startX = (width - totalWidth) / 2;
const textY = 280;

// Draw "Molt" in emerald
ctx.fillStyle = '#10b981';
ctx.fillText(moltText, startX, textY);

// Draw "Mart" in white
ctx.fillStyle = '#ffffff';
ctx.fillText(martText, startX + moltMetrics.width, textY);

// Tagline
ctx.font = '36px sans-serif';
ctx.fillStyle = '#a1a1aa'; // zinc-400
const tagline = 'The Marketplace for AI Agent Services';
const tagMetrics = ctx.measureText(tagline);
ctx.fillText(tagline, (width - tagMetrics.width) / 2, 360);

// Bottom badge
ctx.font = 'bold 24px sans-serif';
ctx.fillStyle = '#10b981';
const badge = '🤖 x402 Payments • ERC-8004 Identity • USDC on Base';
const badgeMetrics = ctx.measureText(badge);
ctx.fillText(badge, (width - badgeMetrics.width) / 2, 520);

// Border accent at bottom
const borderGradient = ctx.createLinearGradient(0, height - 4, width, height - 4);
borderGradient.addColorStop(0, '#10b981'); // emerald-500
borderGradient.addColorStop(0.5, '#14b8a6'); // teal-500
borderGradient.addColorStop(1, '#10b981');
ctx.fillStyle = borderGradient;
ctx.fillRect(0, height - 4, width, 4);

// Save to public folder
const outputPath = join(__dirname, '..', 'public', 'og-image.png');
const buffer = canvas.toBuffer('image/png');
writeFileSync(outputPath, buffer);

console.log(`✅ OG image generated: ${outputPath}`);
console.log(`   Dimensions: ${width}x${height}`);
