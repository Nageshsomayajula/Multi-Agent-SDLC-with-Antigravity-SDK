// Node script that opens Google Meet and records tab audio by injecting a recorder
// Usage: node meet_recorder.js <MEET_URL> <WS_SERVER_URL> <FILENAME>

const puppeteer = require('puppeteer');

async function run(meetUrl, wsServer, filename) {
  const browser = await puppeteer.launch({
    headless: false,
    args: [
      '--use-fake-ui-for-media-stream',
      '--enable-experimental-web-platform-features',
      '--auto-select-desktop-capture-source=Entire screen'
    ],
  });
  const page = await browser.newPage();
  await page.goto(meetUrl, { waitUntil: 'networkidle2' });

  // Inject recorder that captures display audio (tab/system) and streams to backend websocket
  await page.evaluate(({ wsServer, filename }) => {
    (async () => {
      const ws = new WebSocket(wsServer);
      ws.binaryType = 'arraybuffer';
      ws.onopen = async () => {
        try {
          const stream = await navigator.mediaDevices.getDisplayMedia({ audio: true, video: false });
          const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
          recorder.ondataavailable = async (ev) => {
            if (!ev.data || ev.data.size === 0) return;
            const arrBuf = await ev.data.arrayBuffer();
            const b64 = btoa(String.fromCharCode(...new Uint8Array(arrBuf)));
            ws.send(JSON.stringify({ filename, chunk: b64, final: false }));
          };
          recorder.onstop = () => {
            ws.send(JSON.stringify({ filename, final: true }));
          };
          recorder.start(2000);
          // Stop after 1 hour by default
          setTimeout(() => recorder.stop(), 1000 * 60 * 60);
        } catch (e) {
          console.error('capture failed', e);
        }
      };
    })();
  }, { wsServer, filename });

  console.log('Recorder injected. Use the browser window to join the call if needed.');
}

if (require.main === module) {
  const [,, meetUrl, wsServer, filename] = process.argv;
  if (!meetUrl || !wsServer || !filename) {
    console.error('Usage: node meet_recorder.js <MEET_URL> <WS_SERVER_URL> <FILENAME>');
    process.exit(2);
  }
  run(meetUrl, wsServer, filename).catch(err => {
    console.error(err);
    process.exit(1);
  });
}
