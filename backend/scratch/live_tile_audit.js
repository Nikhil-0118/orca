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
      } else if (msg.method) {
        if (this.onEvent) this.onEvent(msg.method, msg.params);
        if (msg.method.startsWith('Network.')) {
          this.networkLogs.push(msg);
        }
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
      returnByValue: true
    });
    if (res.exceptionDetails) {
      throw new Error(JSON.stringify(res.exceptionDetails));
    }
    return res.result.value;
  }
}

async function run() {
  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const userDataDir = 'C:\\Users\\admin\\AppData\\Local\\Temp\\chrome_audit_' + Date.now();

  console.log('1. Spawning Chrome...');
  const chrome = spawn(chromePath, [
    '--headless=new',
    '--remote-debugging-port=9666',
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,800',
    'about:blank'
  ], { stdio: 'ignore' });

  try {
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 500));
      try {
        await get('http://127.0.0.1:9666/json/version');
        break;
      } catch (e) {}
    }

    const pagesRaw = await get('http://127.0.0.1:9666/json/list');
    const pages = JSON.parse(pagesRaw);
    const targetPage = pages.find(p => p.type === 'page') || pages[0];

    const cdp = new CDP(targetPage.webSocketDebuggerUrl);
    await cdp.ready;
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Network.enable');

    console.log('2. Navigating to http://localhost:5173/...');
    const loadPromise = new Promise(resolve => {
      cdp.onEvent = (method) => {
        if (method === 'Page.loadEventFired') resolve();
      };
    });
    await cdp.send('Page.navigate', { url: 'http://localhost:5173/' });
    await loadPromise;
    await new Promise(r => setTimeout(r, 2000));

    // Click Launch Platform
    console.log('3. Clicking Launch Platform...');
    const btnRect = await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const launch = btns.find(b => b.textContent && b.textContent.includes('Launch Platform'));
        if (!launch) return null;
        const r = launch.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      })()
    `);

    if (btnRect) {
      await cdp.send('Input.dispatchMouseEvent', {
        type: 'mousePressed',
        x: btnRect.x,
        y: btnRect.y,
        button: 'left',
        clickCount: 1
      });
      await cdp.send('Input.dispatchMouseEvent', {
        type: 'mouseReleased',
        x: btnRect.x,
        y: btnRect.y,
        button: 'left',
        clickCount: 1
      });
    }
    await new Promise(r => setTimeout(r, 2000));

    // Click Use Demo button
    console.log('4. Clicking Use Demo button...');
    await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const demo = btns.find(b => b.textContent && b.textContent.includes('Use Demo'));
        if (demo) demo.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 1000));

    // Type query: "Show my current location"
    console.log('5. Typing and sending query...');
    const typed = await cdp.eval(`
      (() => {
        const ta = document.querySelector('textarea.chat-input-textarea');
        if (!ta) return 'textarea not found';
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(ta, 'Show my current location');
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        return 'typed: ' + ta.value;
      })()
    `);
    console.log('Typing status:', typed);
    await new Promise(r => setTimeout(r, 600));

    // Click send or press Enter
    const sent = await cdp.eval(`
      (() => {
        const ta = document.querySelector('textarea.chat-input-textarea');
        const btns = Array.from(document.querySelectorAll('button'));
        const sendBtn = btns.find(b => b.classList.contains('chat-send-btn') || b.querySelector('svg.lucide-arrow-up'));
        if (sendBtn && !sendBtn.disabled) {
          sendBtn.click();
          return 'clicked sendBtn';
        }
        if (ta) {
          ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
          return 'pressed Enter';
        }
        return 'no send trigger found';
      })()
    `);
    console.log('Send status:', sent);

    console.log('6. Waiting for spatial card to render...');
    let cardFound = false;
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 1000));
      cardFound = await cdp.eval(`!!document.querySelector('.orca-spatial-card')`);
      if (cardFound) {
        console.log(`Spatial card found after ${i + 1}s!`);
        break;
      }
    }

    if (!cardFound) {
      throw new Error('Spatial card never rendered!');
    }

    // Wait 4s for Leaflet tiles to load
    await new Promise(r => setTimeout(r, 4000));

    // Capture compact map screenshot
    const shot1 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'audit_compact.png'), Buffer.from(shot1.data, 'base64'));
    console.log('Saved audit_compact.png');

    // Inspect compact map tiles
    const compactInspection = await cdp.eval(`
      (() => {
        const container = document.querySelector('.orca-spatial-card .leaflet-container');
        const containerStyle = container ? window.getComputedStyle(container) : null;
        const tilePane = document.querySelector('.orca-spatial-card .leaflet-tile-pane');
        const tiles = Array.from(document.querySelectorAll('.orca-spatial-card .leaflet-tile'));
        const markers = Array.from(document.querySelectorAll('.orca-spatial-card .leaflet-marker-icon'));
        return {
          containerBg: containerStyle ? containerStyle.backgroundColor : null,
          tilePaneStyle: tilePane ? tilePane.getAttribute('style') : null,
          markersCount: markers.length,
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
    console.log('\n=== COMPACT MAP INSPECTION ===');
    console.log(JSON.stringify(compactInspection, null, 2));

    // Click Expand Map
    console.log('\n7. Clicking Expand Map...');
    await cdp.eval(`
      (() => {
        const expandBtn = document.querySelector('.orca-spatial-expand-btn');
        if (expandBtn) expandBtn.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 3000));

    // Capture initial expanded modal screenshot
    const shot2 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'audit_expanded_initial.png'), Buffer.from(shot2.data, 'base64'));
    console.log('Saved audit_expanded_initial.png');

    const expandedInitial = await cdp.eval(`
      (() => {
        const modal = document.querySelector('.orca-map-modal-container');
        const container = document.querySelector('.orca-map-modal-container .leaflet-container');
        const containerStyle = container ? window.getComputedStyle(container) : null;
        const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile'));
        const markers = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-marker-icon'));
        return {
          containerBg: containerStyle ? containerStyle.backgroundColor : null,
          markersCount: markers.length,
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
    console.log('\n=== EXPANDED MODAL (INITIAL) INSPECTION ===');
    console.log(JSON.stringify(expandedInitial, null, 2));

    // Zoom in 2 times
    console.log('\n8. Zooming in twice...');
    await cdp.eval(`
      (() => {
        const zoomIn = document.querySelector('.orca-map-modal-container .leaflet-control-zoom-in');
        if (zoomIn) {
          zoomIn.click();
          setTimeout(() => zoomIn.click(), 500);
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 4000));

    // Capture zoomed modal screenshot
    const shot3 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'audit_expanded_zoomed.png'), Buffer.from(shot3.data, 'base64'));
    console.log('Saved audit_expanded_zoomed.png');

    const expandedZoomed = await cdp.eval(`
      (() => {
        const container = document.querySelector('.orca-map-modal-container .leaflet-container');
        const containerStyle = container ? window.getComputedStyle(container) : null;
        const mapPane = document.querySelector('.orca-map-modal-container .leaflet-map-pane');
        const tilePane = document.querySelector('.orca-map-modal-container .leaflet-tile-pane');
        const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile'));
        const markers = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-marker-icon'));
        const tileContainers = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile-container'));
        return {
          containerBg: containerStyle ? containerStyle.backgroundColor : null,
          tileContainersCount: tileContainers.length,
          tileContainers: tileContainers.map(tc => ({
            style: tc.getAttribute('style'),
            transform: window.getComputedStyle(tc).transform,
            children: tc.children.length
          })),
          markersCount: markers.length,
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
    console.log('\n=== EXPANDED MODAL (ZOOMED) INSPECTION ===');
    console.log(JSON.stringify(expandedZoomed, null, 2));

    // Pan the map
    console.log('\n9. Panning map...');
    const mapPos = await cdp.eval(`
      (() => {
        const el = document.querySelector('.orca-map-modal-container .leaflet-container');
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      })()
    `);
    if (mapPos) {
      await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: mapPos.x, y: mapPos.y, button: 'left' });
      await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: mapPos.x - 180, y: mapPos.y - 100, button: 'left' });
      await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: mapPos.x - 180, y: mapPos.y - 100, button: 'left' });
    }
    await new Promise(r => setTimeout(r, 3000));

    const shot4 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'audit_expanded_panned.png'), Buffer.from(shot4.data, 'base64'));
    console.log('Saved audit_expanded_panned.png');

    const expandedPanned = await cdp.eval(`
      (() => {
        const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile'));
        const loaded = tiles.filter(t => t.naturalWidth > 0 && window.getComputedStyle(t).visibility === 'visible');
        const broken = tiles.filter(t => t.naturalWidth === 0 || window.getComputedStyle(t).visibility === 'hidden');
        return {
          tilesCount: tiles.length,
          loadedCount: loaded.length,
          brokenCount: broken.length,
          brokenUrls: broken.map(t => t.src)
        };
      })()
    `);
    console.log('\n=== EXPANDED MODAL (PANNED) INSPECTION ===');
    console.log(JSON.stringify(expandedPanned, null, 2));

    // Zoom out
    console.log('\n10. Zooming out...');
    await cdp.eval(`
      (() => {
        const zoomOut = document.querySelector('.orca-map-modal-container .leaflet-control-zoom-out');
        if (zoomOut) zoomOut.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 3000));

    const shot5 = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'audit_expanded_zoom_out.png'), Buffer.from(shot5.data, 'base64'));
    console.log('Saved audit_expanded_zoom_out.png');

    const expandedZoomOut = await cdp.eval(`
      (() => {
        const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile'));
        const loaded = tiles.filter(t => t.naturalWidth > 0 && window.getComputedStyle(t).visibility === 'visible');
        const broken = tiles.filter(t => t.naturalWidth === 0 || window.getComputedStyle(t).visibility === 'hidden');
        return {
          tilesCount: tiles.length,
          loadedCount: loaded.length,
          brokenCount: broken.length,
          brokenUrls: broken.map(t => t.src)
        };
      })()
    `);
    console.log('\n=== EXPANDED MODAL (ZOOM OUT) INSPECTION ===');
    console.log(JSON.stringify(expandedZoomOut, null, 2));

    fs.writeFileSync(
      path.join(__dirname, 'live_audit_report.json'),
      JSON.stringify({ compactInspection, expandedInitial, expandedZoomed, expandedPanned, expandedZoomOut }, null, 2)
    );
    console.log('\nSaved live_audit_report.json successfully!');

  } finally {
    console.log('Cleaning up Chrome...');
    chrome.kill('SIGKILL');
  }
}

run().catch(err => {
  console.error('AUDIT SCRIPT ERROR:', err);
  process.exit(1);
});
