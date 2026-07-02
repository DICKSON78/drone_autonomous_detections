const { app, BrowserWindow, shell, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess = null;

function startBackend() {
  return new Promise((resolve) => {
    // Check if backend already running (e.g. from Docker)
    http.get('http://localhost:8007/api/health', (res) => {
      if (res.statusCode === 200) {
        console.log('[backend] Already running on :8007');
        resolve(true);
      }
    }).on('error', () => {
      // No existing backend — spawn one
      const backendDir = path.join(__dirname, 'backend');
      const nlpPath = path.join(__dirname, '..', '..', 'PC2', 'src');
      const env = { ...process.env, APP_PORT: '8007', PYTHONPATH: `${backendDir}:${nlpPath}:${process.env.PYTHONPATH || ''}` };

      backendProcess = spawn('python3', ['-m', 'uvicorn', 'server:app', '--host', '0.0.0.0', '--port', '8007', '--log-level', 'warning'], {
        cwd: backendDir,
        stdio: ['pipe', 'pipe', 'pipe'],
        env,
      });

      backendProcess.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`));
      backendProcess.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`));
      backendProcess.on('close', (code) => {
        if (code !== 0) console.log(`Backend exited: ${code}`);
      });
      resolve(false);
    });
  });
}

function waitForBackend(retries = 20) {
  return new Promise((resolve) => {
    const check = (n) => {
      http.get('http://localhost:8007/api/health', (res) => {
        resolve(true);
      }).on('error', () => {
        if (n <= 0) { resolve(false); return; }
        setTimeout(() => check(n - 1), 500);
      });
    };
    check(retries);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#080b17',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL('http://localhost:8007/index.html');
  mainWindow.on('closed', () => { mainWindow = null; });
  mainWindow.on('maximize', () => mainWindow?.webContents.send('window-maximized'));
  mainWindow.on('unmaximize', () => mainWindow?.webContents.send('window-unmaximized'));
  mainWindow.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
}

ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow?.maximize());
ipcMain.on('window-close', () => mainWindow?.close());
ipcMain.handle('window-is-maximized', () => mainWindow?.isMaximized() ?? false);

app.whenReady().then(async () => {
  await startBackend();
  const ok = await waitForBackend();
  if (ok) {
    createWindow();
  } else {
    console.error('Backend failed to start');
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0 && mainWindow === null) {
    createWindow();
  }
});
