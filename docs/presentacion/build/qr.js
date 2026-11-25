// Genera assets/qr-repo.png (QR del repositorio): módulos tinta sobre papel. Uso: node build/qr.js
const path = require('path');
const QRCode = require('qrcode');

const URL_REPO = 'https://github.com/zmd-brnt/MELOXO';
const RUTA_QR = path.join(__dirname, '..', 'assets', 'qr-repo.png');

async function generarQr(ruta = RUTA_QR) {
  await QRCode.toFile(ruta, URL_REPO, { color: { dark: '#141317', light: '#F4F1EA' }, margin: 2, width: 1024 });
  return ruta;
}

if (require.main === module) generarQr().then(r => console.log('escrito ' + r));
module.exports = { generarQr, RUTA_QR, URL_REPO };
