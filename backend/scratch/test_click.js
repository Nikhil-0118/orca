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
  const userDataDir = 'C:\\Users\\admin\\AppData\\Local\Temp\\chrome_diag_' + Date.now();

  const chrome = spawn(chromePath, [
    '--headless=new',
    '--remote-debugging-port=9555',
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
        await get('http://127.0.0.1:9555/json/version');
        break;
      } catch (e) {}
    }

    const pagesRaw = await get('http://127.0.0.1:9555/json/list');
    const pages = JSON.parse(pagesRaw);
    const targetPage = pages.find(p => p.type === 'page') || pages[0];

    const cdp = new CDP(targetPage.webSocketDebuggerUrl);
    await cdp.ready;
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');

    console.log('Navigating to http://localhost:5173/...');
    const loadPromise = new Promise(resolve => {
      cdp.onEvent = (method) => {
        if (method === 'Page.loadEventFired') resolve();
      };
    });
    await cdp.send('Page.navigate', { url: 'http://localhost:5173/' });
    await loadPromise;
    await new Promise(r => setTimeout(r, 2000));

    // Get position of Launch Platform button
    const btnRect = await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const launch = btns.find(b => b.textContent && b.textContent.includes('Launch Platform'));
        if (!launch) return null;
        const r = launch.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      })()
    `);
    console.log('Button position:', btnRect);

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

    const inChat = await cdp.eval(`!!document.querySelector('.chat-workspace')`);
    console.log('Now in chat workspace:', inChat);

    const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'test_chat_screen.png'), Buffer.from(shot.data, 'base64'));
    console.log('Saved test_chat_screen.png');

  } finally {
    chrome.kill('SIGKILL');
  }
}

run().catch(e => console.error(e));
