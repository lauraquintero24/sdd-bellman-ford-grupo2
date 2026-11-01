// Capturas de la interfaz /ui en un navegador real (C-32, FR-14). Opcional: requiere Node.js y Playwright
// (npm install playwright; npx playwright install chromium). Lo invoca scripts/demo_nodes.py --screenshots.
// Uso: node scripts/capture_ui.js http://127.0.0.1:8000/ui demo-evidence/c32-modo-nodo
const { chromium } = require('playwright');

(async () => {
  const [url, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const rows = (selector) => page.$$eval(selector, (trs) => trs.map((tr) => tr.innerText.replace(/\s+/g, ' ').trim()));
  const tableVersion = (v) => page.waitForFunction(
    (version) => document.querySelector('#table-meta').textContent.includes('versión de topología ' + version), v, { timeout: 15000 });

  await page.goto(url);
  await page.waitForFunction(() => document.querySelectorAll('#routers tbody tr').length > 0 &&
    [...document.querySelectorAll('#routers tbody tr')].every((tr) => tr.textContent.includes('en línea')), null, { timeout: 20000 });
  console.log('Routers mostrados:', JSON.stringify(await rows('#routers tbody tr')));
  await page.click('#routers tbody tr:nth-child(2)');
  await page.waitForFunction(() => document.querySelector('#table-router').textContent === 'B');
  const version = await page.$eval('#topology-version', (e) => Number(e.textContent));
  await tableVersion(version);
  console.log('Tabla de B (v' + version + '):', JSON.stringify(await rows('#forwarding-table tbody tr')));
  await page.screenshot({ path: out + '/ui-1-tabla-B.png', fullPage: true });

  await page.selectOption('#send-source', 'A');
  await page.selectOption('#send-destination', 'D');
  await page.click('#send-form button');
  await page.waitForFunction(() => /Reenviado|failed|HTTP/.test(document.querySelector('#send-result').textContent));
  console.log('Envío A→D:', await page.$eval('#send-result', (e) => e.innerText.replace(/\s+/g, ' ')));
  await page.screenshot({ path: out + '/ui-2-envio-A-D.png', fullPage: true });

  await page.locator('#links tbody tr', { hasText: /B (—|→) D/ }).locator('button').click();
  await tableVersion(version + 1);
  console.log('Tabla de B tras fallar B–D (v' + (version + 1) + '):', JSON.stringify(await rows('#forwarding-table tbody tr')));
  await page.click('#send-form button');
  await page.waitForFunction(() => document.querySelector('#history').children.length === 2);
  console.log('Envío A→D tras el fallo:', await page.$eval('#send-result', (e) => e.innerText.replace(/\s+/g, ' ')));
  await page.screenshot({ path: out + '/ui-3-fallo-B-D.png', fullPage: true });

  await page.locator('#links tbody tr', { hasText: /B (—|→) D/ }).locator('button').click();
  await tableVersion(version + 2);
  console.log('Tabla de B tras restaurar (v' + (version + 2) + '):', JSON.stringify(await rows('#forwarding-table tbody tr')));
  await page.screenshot({ path: out + '/ui-4-restauracion.png', fullPage: true });
  await browser.close();
})().catch((error) => { console.error('FALLO:', error.message); process.exit(1); });
