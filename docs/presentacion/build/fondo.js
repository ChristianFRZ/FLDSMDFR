// Genera assets/fondo-puntos.png: tinta #141317 con puntos #34323B cada 32 px (como el fondo de la app).
const path = require('path');
const sharp = require('sharp');

async function generarFondo(destino) {
  let puntos = '';
  for (let y = 16; y < 1080; y += 32) {
    for (let x = 16; x < 1920; x += 32) puntos += `<circle cx="${x}" cy="${y}" r="2.4" fill="#34323B"/>`;
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><rect width="1920" height="1080" fill="#141317"/>${puntos}</svg>`;
  await sharp(Buffer.from(svg)).png().toFile(destino);
}

module.exports = { generarFondo, RUTA_FONDO: path.join(__dirname, '..', 'assets', 'fondo-puntos.png') };

if (require.main === module) generarFondo(module.exports.RUTA_FONDO).then(() => console.log('fondo listo'));
