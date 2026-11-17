const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const mlDir = path.join(rootDir, 'ml-service');

// Candidate python paths
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

console.log(`[ML Tests] Using Python: ${pythonCmd}`);
const proc = spawnSync(pythonCmd, ['-m', 'pytest', 'tests/'], {
  cwd: mlDir,
  stdio: 'inherit',
  shell: true
});

process.exit(proc.status || 0);
