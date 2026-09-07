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
    this.events = [];
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

  async eval(expr, awaitPromise = false) {
    const res = await this.send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise
    });
    if (res.exceptionDetails) {
      throw new Error(JSON.stringify(res.exceptionDetails));
    }
    return res.result.value;
  }
}

async function main() {
  console.log('Connecting to Chrome CDP on port 9333...');
  const listRaw = await get('http://127.0.0.1:9333/json/list');
  const pages = JSON.parse(listRaw);
  const targetPage = pages.find(p => p.type === 'page') || pages[0];
  console.log('Target page:', targetPage.url, targetPage.id, targetPage.type);

  const cdp = new CDP(targetPage.webSocketDebuggerUrl);
  await cdp.ready;
  console.log('WebSocket connected!');

  await cdp.send('Page.enable');
  await cdp.send('DOM.enable');
  await cdp.send('Network.enable');

  // Navigate to http://localhost:5173/ if not already there
  console.log('Navigating to http://localhost:5173/...');
  await cdp.send('Page.navigate', { url: 'http://localhost:5173/' });
  await new Promise(r => setTimeout(r, 2000));

  // Click Launch Platform to enter chat
  console.log('Clicking "Launch Platform"...');
  await cdp.eval(`
    (() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const launchBtn = buttons.find(b => b.textContent && b.textContent.includes('Launch Platform'));
      if (launchBtn) { launchBtn.click(); return true; }
      return false;
    })()
  `);
  await new Promise(r => setTimeout(r, 1500));

  // Click Demo Location button if location is unavailable
  console.log('Setting demo location...');
  await cdp.eval(`
    (() => {
      const demoBtn = document.querySelector('.orca-loc-demo-btn');
      if (demoBtn) { demoBtn.click(); return 'Clicked demo button'; }
      return 'Demo button not found';
    })()
  `);
  await new Promise(r => setTimeout(r, 1000));

  // Send spatial query: "Show me a route from Chennai to Pondicherry"
  console.log('Typing query...');
  await cdp.eval(`
    (() => {
      const textarea = document.querySelector('textarea.chat-input-textarea');
      if (!textarea) return 'Textarea not found';
      textarea.value = 'Show me a route from Chennai to Pondicherry';
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      return 'OK';
    })()
  `);
  await new Promise(r => setTimeout(r, 500));

  // Click send button
  console.log('Submitting query...');
  await cdp.eval(`
    (() => {
      const sendBtn = document.querySelector('.chat-send-btn');
      if (sendBtn) { sendBtn.click(); return 'Clicked send'; }
      return 'Send button not found';
    })()
  `);

  // Wait for response and map card to render
  console.log('Waiting for map card to appear...');
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const cardExists = await cdp.eval(`!!document.querySelector('.orca-spatial-card')`);
    if (cardExists) {
      console.log('Map card rendered in compact view!');
      break;
    }
  }

  // Wait 3 seconds for Leaflet tiles to load
  await new Promise(r => setTimeout(r, 3000));

  // Inspect compact map tiles
  console.log('\n================ INSPECTING COMPACT MAP TILES ================');
  const compactTilesInfo = await cdp.eval(`
    (() => {
      const tiles = Array.from(document.querySelectorAll('.orca-spatial-card .leaflet-tile'));
      return tiles.map((t, idx) => {
        const style = window.getComputedStyle(t);
        const rect = t.getBoundingClientRect();
        return {
          idx,
          src: t.src,
          naturalWidth: t.naturalWidth,
          naturalHeight: t.naturalHeight,
          computedWidth: style.width,
          computedHeight: style.height,
          opacity: style.opacity,
          visibility: style.visibility,
          display: style.display,
          mixBlendMode: style.mixBlendMode,
          transform: style.transform,
          rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
          isComplete: t.complete
        };
      });
    })()
  `);
  console.log('Compact tiles found:', compactTilesInfo.length);
  console.log(JSON.stringify(compactTilesInfo, null, 2));

  // Capture screenshot of compact view
  const compactScreenshot = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(__dirname, 'compact_view.png'), Buffer.from(compactScreenshot.data, 'base64'));
  console.log('Saved compact_view.png');

  // Click "Expand Map"
  console.log('\nClicking "Expand Map"...');
  await cdp.eval(`
    (() => {
      const expandBtn = document.querySelector('.orca-spatial-expand-btn');
      if (expandBtn) { expandBtn.click(); return true; }
      return false;
    })()
  `);

  // Wait 2 seconds for modal to open and tiles to load
  await new Promise(r => setTimeout(r, 2000));

  console.log('\n================ INSPECTING EXPANDED MODAL TILES (INITIAL ZOOM) ================');
  const modalTilesInfo = await cdp.eval(`
    (() => {
      const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile, .orca-map-modal-backdrop .leaflet-tile'));
      return tiles.map((t, idx) => {
        const style = window.getComputedStyle(t);
        const rect = t.getBoundingClientRect();
        return {
          idx,
          src: t.src,
          naturalWidth: t.naturalWidth,
          naturalHeight: t.naturalHeight,
          computedWidth: style.width,
          computedHeight: style.height,
          opacity: style.opacity,
          visibility: style.visibility,
          display: style.display,
          mixBlendMode: style.mixBlendMode,
          transform: style.transform,
          rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
          isComplete: t.complete
        };
      });
    })()
  `);
  console.log('Modal initial tiles found:', modalTilesInfo.length);
  console.log(JSON.stringify(modalTilesInfo, null, 2));

  // Capture screenshot of expanded initial view
  const modalScreenshot1 = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(__dirname, 'modal_view_initial.png'), Buffer.from(modalScreenshot1.data, 'base64'));
  console.log('Saved modal_view_initial.png');

  // Click Zoom In button twice
  console.log('\nClicking Zoom In (+) twice...');
  await cdp.eval(`
    (() => {
      const zoomIn = document.querySelector('.orca-map-modal-container .leaflet-control-zoom-in');
      if (zoomIn) {
        zoomIn.click();
        setTimeout(() => zoomIn.click(), 400);
        return true;
      }
      return false;
    })()
  `);

  // Wait 3 seconds for new zoom tiles to load
  await new Promise(r => setTimeout(r, 3000));

  console.log('\n================ INSPECTING EXPANDED MODAL TILES (AFTER ZOOM IN) ================');
  const zoomedTilesInfo = await cdp.eval(`
    (() => {
      const tiles = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-tile, .orca-map-modal-backdrop .leaflet-tile'));
      return tiles.map((t, idx) => {
        const style = window.getComputedStyle(t);
        const rect = t.getBoundingClientRect();
        return {
          idx,
          src: t.src,
          naturalWidth: t.naturalWidth,
          naturalHeight: t.naturalHeight,
          computedWidth: style.width,
          computedHeight: style.height,
          opacity: style.opacity,
          visibility: style.visibility,
          display: style.display,
          mixBlendMode: style.mixBlendMode,
          transform: style.transform,
          rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
          isComplete: t.complete
        };
      });
    })()
  `);
  console.log('Modal zoomed tiles found:', zoomedTilesInfo.length);
  console.log(JSON.stringify(zoomedTilesInfo, null, 2));

  // Check tile panes and layers
  const paneInfo = await cdp.eval(`
    (() => {
      const panes = Array.from(document.querySelectorAll('.orca-map-modal-container .leaflet-pane, .orca-map-modal-container .leaflet-tile-pane, .orca-map-modal-container .leaflet-tile-container'));
      return panes.map(p => ({
        className: p.className,
        style: p.getAttribute('style'),
        childrenCount: p.children.length,
        rect: p.getBoundingClientRect()
      }));
    })()
  `);
  console.log('\nPane & Container Structure:', JSON.stringify(paneInfo, null, 2));

  // Check all network tile requests
  console.log('\n================ TILE NETWORK REQUESTS ================');
  const tileReqs = cdp.networkLogs.filter(n => n.params && n.params.response && n.params.response.url && n.params.response.url.includes('basemaps.cartocdn.com'));
  console.log('Total tile requests logged:', tileReqs.length);
  tileReqs.forEach(r => {
    console.log(`URL: ${r.params.response.url} -> Status: ${r.params.response.status}, mime: ${r.params.response.mimeType}`);
  });

  // Capture screenshot of zoomed modal
  const modalScreenshot2 = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(__dirname, 'modal_view_zoomed.png'), Buffer.from(modalScreenshot2.data, 'base64'));
  console.log('Saved modal_view_zoomed.png');

  console.log('\nDOM Inspection Complete!');
  process.exit(0);
}

main().catch(err => {
  console.error('ERROR in inspection script:', err);
  process.exit(1);
});
