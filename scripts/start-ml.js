const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const mlDir = path.join(rootDir, 'ml-service');
const isWin = process.platform === 'win32';

const candidatePythons = [
  path.join(mlDir, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python'),
  isWin ? 'python' : 'python3',
  'python'
];

let pythonCmd = null;
for (const cand of candidatePythons) {
  if (path.isAbsolute(cand)) {
    if (fs.existsSync(cand)) {
      pythonCmd = cand;
      break;
    }
  } else {
    pythonCmd = cand;
    break;
  }
}

console.log(`[JURIST AI] Starting ML Service using ${pythonCmd}...`);
const apiScript = path.join('app', 'services', 'api.py');

const mlProc = spawn(pythonCmd, [apiScript], {
  cwd: mlDir,
  stdio: 'inherit',
  shell: true,
  env: {
    ...process.env,
    PYTHONPATH: mlDir
  }
});

mlProc.on('exit', (code, signal) => {
  console.log(`[JURIST AI] ML Service exited with code ${code} (${signal})`);
  process.exit(code || 0);
});

process.on('SIGINT', () => mlProc.kill('SIGINT'));
process.on('SIGTERM', () => mlProc.kill('SIGTERM'));
