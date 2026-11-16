const fs = require('fs');
const path = require('path');

const srcDir = path.resolve(__dirname, '..', 'src', 'integrations', 'artifacts');
const destDir = path.resolve(__dirname, '..', 'dist', 'integrations', 'artifacts');

// Ensure unified corpus manifest is also mirrored into backend artifacts
const manifestSource = path.resolve(__dirname, '..', '..', 'ml-service', 'app', 'datasets', 'unified_corpus_manifest.json');
if (fs.existsSync(manifestSource)) {
  fs.mkdirSync(srcDir, { recursive: true });
  fs.copyFileSync(manifestSource, path.join(srcDir, 'unified_corpus_manifest.json'));
}

// Ensure dual model artifacts are mirrored into backend artifacts
const dualModelSource = path.resolve(__dirname, '..', '..', 'ml-service', 'app', 'models', 'dual_model_artifacts.json');
if (fs.existsSync(dualModelSource)) {
  fs.mkdirSync(srcDir, { recursive: true });
  fs.copyFileSync(dualModelSource, path.join(srcDir, 'dual_model_artifacts.json'));
}

if (fs.existsSync(srcDir)) {
  fs.mkdirSync(destDir, { recursive: true });
  fs.cpSync(srcDir, destDir, { recursive: true });
  console.log(`[build] Successfully copied artifacts from ${srcDir} to ${destDir}`);
} else {
  console.warn(`[build] Artifacts source directory does not exist: ${srcDir}`);
}
