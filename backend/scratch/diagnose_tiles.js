const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

function get(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

class CDP {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
    this.networkLogs = [];

    this.ready = new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      } else if (msg.method && msg.method.startsWith('Network.')) {
        this.networkLogs.push(msg);
      }
    };
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expr) {
    const res = await this.send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise: false
    });
    if (res.exceptionDetails) {
      throw new Error(JSON.stringify(res.exceptionDetails));
    }
    return res.result.value;
  }
}

async function run() {
  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const userDataDir = 'C:\\Users\\admin\\AppData\\Local\\Temp\\chrome_diag_' + Date.now();

  console.log('Spawning Chrome...');
  const chrome = spawn(chromePath, [
    '--headless=new',
    '--remote-debugging-port=9444',
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,800',
    'about:blank'
  ], { stdio: 'ignore' });

  try {
    console.log('Waiting for Chrome CDP on 9444...');
    let connected = false;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 500));
      try {
        await get('http://127.0.0.1:9444/json/version');
        connected = true;
        break;
      } catch (e) {}
    }

    if (!connected) {
      throw new Error('Could not connect to Chrome CDP');
    }
    console.log('Chrome CDP connected!');

    const pagesRaw = await get('http://127.0.0.1:9444/json/list');
    const pages = JSON.parse(pagesRaw);
    const targetPage = pages.find(p => p.type === 'page') || pages[0];
    console.log('Using target page:', targetPage.id, targetPage.url);

    const cdp = new CDP(targetPage.webSocketDebuggerUrl);
    await cdp.ready;

    await cdp.send('Page.enable');
    await cdp.send('DOM.enable');
    await cdp.send('Network.enable');

    console.log('Navigating to http://localhost:5173/...');
    await cdp.send('Page.navigate', { url: 'http://localhost:5173/' });
    await new Promise(r => setTimeout(r, 3000));

    console.log('Entering chat...');
    await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const launch = btns.find(b => b.textContent && b.textContent.includes('Launch Platform'));
        if (launch) launch.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 1500));

    console.log('Setting demo location...');
    await cdp.eval(`
      (() => {
        const demoBtn = document.querySelector('.orca-loc-demo-btn');
        if (demoBtn) demoBtn.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 800));

    console.log('Sending spatial query: "Show my current location"...');
    await cdp.eval(`
      (() => {
        const ta = document.querySelector('textarea.chat-input-textarea');
        if (ta) {
          ta.value = 'Show my current location';
          ta.dispatchEvent(new Event('input', { bubbles: true }));
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 300));

    await cdp.eval(`
      (() => {
        const btn = document.querySelector('.chat-send-btn');
        if (btn) btn.click();
      })()
    `);

    console.log('Waiting for compact map card...');
    let cardFound = false;
    for (let i = 0; i < 25; i++) {
      await new Promise(r => setTimeout(r, 1000));
      cardFound = await cdp.eval(`!!document.querySelector('.orca-spatial-card')`);
      if (cardFound) {
        console.log(`Map card found after ${i+1}s!`);
        break;
      }
    }

    if (!cardFound) {
      console.log('Card not found in time!');
    }

    // Wait 3s for tiles to load
    await new Promise(r => setTimeout(r, 3000));

    // Inspect compact map tiles
    const compactTiles = await cdp.eval(`
      (() => {
        const container = document.querySelector('.orca-spatial-card .leaflet-container');
        const containerStyle = container ? window.getComputedStyle(container) : null;
        const tiles = Array.from(document.querySelectorAll('.orca-spatial-card .leaflet-tile'));
        return {
          containerBackground: containerStyle ? containerStyle.backgroundColor : null,
          tilesCount: tiles.length,
          tiles: tiles.map(t => {
            const s = window.getComputedStyle(t);
            const r = t.getBoundingClientRect();
            return {
              src: t.src,
              naturalWidth: t.naturalWidth,
              naturalHeight: t.naturalHeight,
              width: s.width,
              height: s.height,
              opacity: s.opacity,
              visibility: s.visibility,
              display: s.display,
              mixBlendMode: s.mixBlendMode,
              top: r.top,
              left: r.left,
              rectWidth: r.width,
              rectHeight: r.height,
              complete: t.complete
            };
          })
        };
      })()
    `);
    console.log('\n--- COMPACT MAP TILES ---');
    console.log(JSON.stringify(compactTiles, null, 2));

    const shot1 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'diag_compact.png'), Buffer.from(shot1.data, 'base64'));
    console.log('Saved diag_compact.png');

    // Click Expand Map
    console.log('\nClicking "Expand Map"...');
    await cdp.eval(`
      (() => {
        const btn = document.querySelector('.orca-spatial-expand-btn');
        if (btn) btn.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 2000));

    // Inspect expanded map
    const expandedInitial = await cdp.eval(`
      (() => {
        const container = document.querySelector('.orca-map-modal-container .leaflet-container');
        const containerStyle = container ? window.getComputedStyle(container) : null;
        const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile'));
        return {
          containerBackground: containerStyle ? containerStyle.backgroundColor : null,
          tilesCount: tiles.length,
          tiles: tiles.map(t => {
            const s = window.getComputedStyle(t);
            const r = t.getBoundingClientRect();
            return {
              src: t.src,
              naturalWidth: t.naturalWidth,
              naturalHeight: t.naturalHeight,
              width: s.width,
              height: s.height,
              opacity: s.opacity,
              visibility: s.visibility,
              display: s.display,
              mixBlendMode: s.mixBlendMode,
              top: r.top,
              left: r.left,
              rectWidth: r.width,
              rectHeight: r.height,
              complete: t.complete
            };
          })
        };
      })()
    `);
    console.log('\n--- EXPANDED MODAL (INITIAL) TILES ---');
    console.log(JSON.stringify(expandedInitial, null, 2));

    const shot2 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'diag_expanded_initial.png'), Buffer.from(shot2.data, 'base64'));
    console.log('Saved diag_expanded_initial.png');

    // Click Zoom In 3 times
    console.log('\nZooming in 3 times...');
    await cdp.eval(`
      (() => {
        const zoomIn = document.querySelector('.orca-map-modal-container .leaflet-control-zoom-in');
        if (zoomIn) {
          zoomIn.click();
          setTimeout(() => zoomIn.click(), 400);
          setTimeout(() => zoomIn.click(), 800);
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 3500));

    // Inspect after zoom in
    const expandedZoomed = await cdp.eval(`
      (() => {
        const container = document.querySelector('.orca-map-modal-container .leaflet-container');
        const containerStyle = container ? window.getComputedStyle(container) : null;
        const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile'));
        const mapPane = document.querySelector('.orca-map-modal-container .leaflet-map-pane');
        const tilePane = document.querySelector('.orca-map-modal-container .leaflet-tile-pane');
        return {
          containerBackground: containerStyle ? containerStyle.backgroundColor : null,
          mapPaneTransform: mapPane ? window.getComputedStyle(mapPane).transform : null,
          tilePaneTransform: tilePane ? window.getComputedStyle(tilePane).transform : null,
          tilesCount: tiles.length,
          tiles: tiles.map(t => {
            const s = window.getComputedStyle(t);
            const r = t.getBoundingClientRect();
            return {
              src: t.src,
              naturalWidth: t.naturalWidth,
              naturalHeight: t.naturalHeight,
              width: s.width,
              height: s.height,
              opacity: s.opacity,
              visibility: s.visibility,
              display: s.display,
              mixBlendMode: s.mixBlendMode,
              top: r.top,
              left: r.left,
              rectWidth: r.width,
              rectHeight: r.height,
              complete: t.complete
            };
          })
        };
      })()
    `);
    console.log('\n--- EXPANDED MODAL (ZOOMED) TILES ---');
    console.log(JSON.stringify(expandedZoomed, null, 2));

    const shot3 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'diag_expanded_zoomed.png'), Buffer.from(shot3.data, 'base64'));
    console.log('Saved diag_expanded_zoomed.png');

    // Save full JSON report
    fs.writeFileSync(
      path.join(__dirname, 'tile_diagnosis_report.json'),
      JSON.stringify({ compactTiles, expandedInitial, expandedZoomed }, null, 2)
    );
    console.log('\nSaved tile_diagnosis_report.json successfully!');

  } finally {
    console.log('Terminating Chrome...');
    chrome.kill('SIGKILL');
  }
}

run().catch(err => {
  console.error('DIAGNOSIS ERROR:', err);
  process.exit(1);
});
