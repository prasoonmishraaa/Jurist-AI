const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const pythonOutputFile = path.join(rootDir, 'scripts', 'parity_python_output.json');

// Require the compiled localInference engine from backend/dist
const { localInferenceEngine } = require(path.join(rootDir, 'backend', 'dist', 'integrations', 'localInference.js'));

function runParityCheck() {
  console.log('==================================================================');
  console.log('   PYTHON vs TYPESCRIPT MATHEMATICAL & DOMAIN PARITY AUDIT        ');
  console.log('==================================================================\n');

  if (!fs.existsSync(pythonOutputFile)) {
    console.error(`Missing Python output file: ${pythonOutputFile}`);
    process.exit(1);
  }

  const pyData = JSON.parse(fs.readFileSync(pythonOutputFile, 'utf8'));
  let maxScoreDiff = 0;
  let allMatched = true;

  pyData.forEach((testCase, idx) => {
    console.log(`[Test Case ${idx + 1}] ${testCase.name}`);
    console.log(`  Category: ${testCase.category}`);

    const tsRes = localInferenceEngine.predictOutcome(testCase.text, testCase.category);

    console.log(`  Domain Detected: Py="${testCase.domainDetected}" | TS="${tsRes.domainDetected}"`);
    if (testCase.domainDetected !== tsRes.domainDetected) {
      console.error(`  FAIL: Domain mismatch!`);
      allMatched = false;
    }

    // Model A Verification
    console.log(`  Model A Prediction: Py="${testCase.modelA.prediction}" | TS="${tsRes.modelA.prediction}"`);
    if (testCase.modelA.prediction !== tsRes.modelA.prediction) {
      console.error(`  FAIL: Model A prediction mismatch!`);
      allMatched = false;
    }

    // Model A Scores comparison
    const pyScoresA = testCase.modelA.rawScores || testCase.modelA.uncalibratedScores;
    const tsScoresA = tsRes.modelA.rawScores || tsRes.modelA.uncalibratedScores;
    console.log(`  Model A Classes & Raw Scores:`);
    for (const cls of testCase.modelA.classes) {
      const pScore = pyScoresA[cls] || 0;
      const tScore = tsScoresA[cls] || 0;
      const diff = Math.abs(pScore - tScore);
      if (diff > maxScoreDiff) maxScoreDiff = diff;
      console.log(`    - ${cls.padEnd(20)}: Py=${pScore.toFixed(7)} | TS=${tScore.toFixed(7)} | Diff=${diff.toExponential(2)}`);
      if (diff > 1e-4) {
        console.error(`    FAIL: Score difference too large for ${cls}`);
        allMatched = false;
      }
    }

    // Model B Verification
    console.log(`  Model B Prediction: Py="${testCase.modelB.prediction}" | TS="${tsRes.modelB.prediction}"`);
    console.log(`  Model B Abstained: Py=${Boolean(testCase.modelB.abstained)} | TS=${Boolean(tsRes.modelB.abstained)}`);
    console.log(`  Model B Domain Status: Py="${testCase.modelB.domainStatus}" | TS="${tsRes.modelB.domainStatus}"`);
    if (testCase.modelB.prediction !== tsRes.modelB.prediction) {
      console.error(`  FAIL: Model B prediction mismatch!`);
      allMatched = false;
    }
    if (Boolean(testCase.modelB.abstained) !== Boolean(tsRes.modelB.abstained)) {
      console.error(`  FAIL: Model B abstained flag mismatch!`);
      allMatched = false;
    }

    // Model B Scores comparison
    const pyScoresB = testCase.modelB.rawScores || testCase.modelB.uncalibratedScores;
    const tsScoresB = tsRes.modelB.rawScores || tsRes.modelB.uncalibratedScores;
    console.log(`  Model B Classes & Raw Scores:`);
    for (const cls of testCase.modelB.classes) {
      const pScore = pyScoresB[cls] || 0;
      const tScore = tsScoresB[cls] || 0;
      const diff = Math.abs(pScore - tScore);
      if (diff > maxScoreDiff) maxScoreDiff = diff;
      console.log(`    - ${cls.padEnd(20)}: Py=${pScore.toFixed(7)} | TS=${tScore.toFixed(7)} | Diff=${diff.toExponential(2)}`);
      if (diff > 1e-4) {
        console.error(`    FAIL: Score difference too large for ${cls}`);
        allMatched = false;
      }
    }

    console.log('');
  });

  console.log('------------------------------------------------------------------');
  console.log(`Overall Max Score Difference (IEEE-754 Float64): ${maxScoreDiff.toExponential(4)}`);
  if (allMatched && maxScoreDiff < 1e-4) {
    console.log('✓ MATHEMATICAL & BEHAVIORAL PARITY VERIFIED: 100% PASS');
  } else {
    console.error('✗ PARITY AUDIT FAILED');
    process.exit(1);
  }
}

runParityCheck();
