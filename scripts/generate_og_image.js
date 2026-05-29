/**
 * Generate OG Image PNG from SVG
 * Run: node scripts/generate_og_image.js
 */
const sharp = require('sharp');
const path = require('path');
const fs = require('fs');

const svgPath = path.join(__dirname, '..', 'public', 'og-image.svg');
const pngPath = path.join(__dirname, '..', 'public', 'og-image.png');

async function main() {
  const svgBuffer = fs.readFileSync(svgPath);

  await sharp(svgBuffer)
    .resize(1200, 630)
    .png()
    .toFile(pngPath);

  const stats = fs.statSync(pngPath);
  console.log(`[OG] Generated og-image.png (${(stats.size / 1024).toFixed(1)} KB)`);
}

main().catch((err) => {
  console.error('[OG] Failed:', err.message);
  process.exit(1);
});
