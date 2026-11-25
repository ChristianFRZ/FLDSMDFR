// Ensambla las láminas en orden y escribe meloxo.pptx. Uso: node build/build.js (desde docs/presentacion/).
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const pptxgen = require('pptxgenjs');
const { generarFondo, RUTA_FONDO } = require('./fondo');
const tema = require('./tema');
const { generarQr, RUTA_QR } = require('./qr');

const RAIZ = path.join(__dirname, '..');
const SALIDA = path.join(RAIZ, 'meloxo.pptx');

async function main() {
  if (!fs.existsSync(RUTA_FONDO)) await generarFondo(RUTA_FONDO);
  if (!fs.existsSync(RUTA_QR)) await generarQr(RUTA_QR);
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  pres.title = 'MELOXO - Tu casetera de confianza';
  pres.author = 'FLDSMDFR';
  tema.iniciar(pres);
  for (const lado of ['lado-a1', 'lado-a2', 'lado-b1', 'lado-b2']) require('./' + lado).agregar(pres);
  await pres.writeFile({ fileName: SALIDA });
  // quita las entradas de directorio del zip (Canva y validate las rechazan)
  try { execSync(`zip -dq "${SALIDA}" '*/'`, { stdio: 'ignore' }); } catch (e) { /* sin entradas de directorio: zip sale con 12 */ }
  console.log('escrito ' + SALIDA);
}

main().catch(e => { console.error(e); process.exit(1); });
