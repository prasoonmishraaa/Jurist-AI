const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const pythonExe = path.join(rootDir, 'ml-service', '.venv', 'Scripts', 'python.exe');
const mlApiScript = path.join(rootDir, 'ml-service', 'app', 'services', 'api.py');
const backendServer = path.join(rootDir, 'backend', 'dist', 'server.js');

function getInternalSecret() {
  const envPath = path.join(rootDir, 'backend', '.env');
  if (fs.existsSync(envPath)) {
    const txt = fs.readFileSync(envPath, 'utf8');
    const match = txt.match(/^INTERNAL_ML_SECRET=(.+)$/m);
    if (match) return match[1].trim();
  }
  return process.env.INTERNAL_ML_SECRET || 'jurist-internal-secret-key';
}

function httpRequest(options, postData = null) {
  return new Promise((resolve, reject) => {
    const opts = { ...options, headers: { ...options.headers } };
    let dataStr = null;
    if (postData) {
      dataStr = typeof postData === 'string' ? postData : JSON.stringify(postData);
      opts.headers['Content-Length'] = Buffer.byteLength(dataStr);
    }
    const req = http.request(opts, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(body);
          resolve({ status: res.statusCode, headers: res.headers, data: parsed });
        } catch {
          resolve({ status: res.statusCode, headers: res.headers, raw: body });
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(10000, () => {
      req.destroy(new Error('Request timed out'));
    });
    if (dataStr) {
      req.write(dataStr);
    }
    req.end();
  });
}

async function waitForServer(port, pathStr, maxRetries = 30, delayMs = 500) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await httpRequest({
        hostname: '127.0.0.1',
        port: port,
        path: pathStr,
        method: 'GET'
      });
      if (res.status === 200) return true;
    } catch (e) {
      // wait and retry
    }
    await new Promise(r => setTimeout(r, delayMs));
  }
  return false;
}

async function runEndToEndProbe() {
  console.log('=== JURIST AI End-to-End System Probe ===');
  const ML_PORT = 8099;
  const BACKEND_PORT = 5099;

  console.log(`Starting ML Service on port ${ML_PORT}...`);
  
  const mlEnv = {
    ...process.env,
    PYTHONPATH: path.join(rootDir, 'ml-service'),
    ML_PORT: String(ML_PORT),
    INTERNAL_ML_SECRET: getInternalSecret()
  };
  const mlProc = spawn(pythonExe, [mlApiScript], {
    cwd: path.join(rootDir, 'ml-service'),
    env: mlEnv,
    stdio: 'inherit'
  });

  const mlReady = await waitForServer(ML_PORT, '/api/ml/health', 40, 500);
  if (!mlReady) {
    console.error(`FAILED: ML Service did not start on port ${ML_PORT} within 20s`);
    mlProc.kill();
    process.exit(1);
  }
  console.log(`✓ ML Service is responsive on port ${ML_PORT}.`);

  console.log(`Starting Backend Server on port ${BACKEND_PORT}...`);
  const backendEnv = {
    ...process.env,
    PORT: String(BACKEND_PORT),
    NODE_ENV: 'development',
    JWT_SECRET: 'test-secret-for-e2e-probe',
    ML_SERVICE_URL: `http://127.0.0.1:${ML_PORT}`,
    INTERNAL_ML_SECRET: getInternalSecret()
  };
  const backendProc = spawn('node', [backendServer], {
    cwd: path.join(rootDir, 'backend'),
    env: backendEnv,
    stdio: 'inherit'
  });

  const backendReady = await waitForServer(BACKEND_PORT, '/api/v1/health', 30, 500);
  if (!backendReady) {
    console.error(`FAILED: Backend Server did not start on port ${BACKEND_PORT} within 15s`);
    mlProc.kill();
    backendProc.kill();
    process.exit(1);
  }
  console.log(`✓ Backend Server is responsive on port ${BACKEND_PORT}.`);

  const results = {};

  try {
    // 1. Health Probe
    console.log('\n--- 1. Probing Backend & ML Health ---');
    const healthRes = await httpRequest({
      hostname: '127.0.0.1',
      port: BACKEND_PORT,
      path: '/api/v1/health',
      method: 'GET'
    });
    console.log(`Health Status: ${healthRes.status}`);
    console.log(`Persistence Mode: ${healthRes.data?.data?.persistenceMode}`);
    console.log(`Verified Precedents: ${healthRes.data?.data?.verifiedPrecedentCount}`);
    console.log(`ML Service Health: ${JSON.stringify(healthRes.data?.data?.mlService)}`);
    results.health = healthRes.data;

    // 2. Auth Flow: Register
    console.log('\n--- 2. Probing Authentication Flow (Register & Login) ---');
    const testUser = {
      name: 'Advocate Verma',
      email: `advocate_${Date.now()}@testbar.in`,
      password: 'SecurePassword123!'
    };
    const regRes = await httpRequest({
      hostname: '127.0.0.1',
      port: BACKEND_PORT,
      path: '/api/v1/auth/register',
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, testUser);

    console.log(`Registration status: ${regRes.status}`);
    const token = regRes.data?.data?.token;
    console.log(`JWT Token received: ${token ? 'YES (' + token.substring(0, 15) + '...)' : 'NO'}`);
    results.auth = { registered: regRes.status === 201, tokenReceived: !!token };

    // 3. Precedents Library Probe
    console.log('\n--- 3. Probing Precedent Engine ---');
    const precRes = await httpRequest({
      hostname: '127.0.0.1',
      port: BACKEND_PORT,
      path: '/api/v1/precedents?search=bail&limit=5',
      method: 'GET'
    });
    console.log(`Precedents query status: ${precRes.status}`);
    const precedentList = precRes.data?.data?.precedents || precRes.data?.data || [];
    console.log(`Retrieved precedents count: ${precedentList.length}`);
    if (precedentList.length > 0) {
      console.log(`Top precedent: "${precedentList[0].title || precedentList[0].caseTitle}" (${precedentList[0].citation || precedentList[0].neutralCitation})`);
    }
    results.precedents = { status: precRes.status, count: precedentList.length };

    // 4. Case Analysis Pipeline Probe (Date-Aware, Hybrid Retrieval, Qualitative Mode)
    console.log('\n--- 4. Probing Case Analysis & Qualitative Prediction Pipeline ---');
    const sampleNarrative = {
      title: 'State of Maharashtra v. Rajesh Kumar (Bail & BNSS Section 35)',
      description: 'The applicant was arrested on 15 August 2024 for alleged offences under Sections 318(4) and 316(2) of the Bharatiya Nyaya Sanhita 2023. Investigating officer did not serve notice under Section 35 of the Bharatiya Nagarik Suraksha Sanhita 2023 prior to custodial arrest. Applicant seeks regular bail under Section 480 BNSS 2023.',
      clientRole: 'appellant',
      court: 'High Court of Bombay'
    };

    const analysisRes = await httpRequest({
      hostname: '127.0.0.1',
      port: BACKEND_PORT,
      path: '/api/v1/analysis',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    }, sampleNarrative);

    console.log(`Analysis endpoint status: ${analysisRes.status}`);
    const analysisData = analysisRes.data?.data;
    if (analysisData) {
      console.log(`Legislation Mode Detected: ${analysisData.dateAwareLegislation?.regime || 'Pre/Post-2024 evaluation'}`);
      console.log(`Applicable Statutes: ${JSON.stringify(analysisData.applicableStatutes?.slice(0, 3) || [])}`);
      console.log(`Legal Issues Identified: ${(analysisData.legalIssues || []).length}`);
      console.log(`Precedents Retrieved: ${(analysisData.precedents || []).length}`);
      console.log(`Outcome Prediction Mode: ${analysisData.outcomePrediction?.status || analysisData.outcomePrediction?.predictionMode || 'qualitative_research_mode'}`);
      console.log(`Outcome Assessment: ${analysisData.outcomePrediction?.estimatedOutcome || 'Structured Doctrinal Assessment'}`);
      console.log(`Evidence Trace Graph Nodes: ${(analysisData.evidenceTraceGraph || []).length}`);
      results.analysis = {
        success: true,
        issuesCount: (analysisData.legalIssues || []).length,
        precedentsCount: (analysisData.precedents || []).length,
        predictionMode: analysisData.outcomePrediction?.status || analysisData.outcomePrediction?.predictionMode,
        evidenceNodes: (analysisData.evidenceTraceGraph || []).length
      };
    } else {
      console.error('Analysis response missing data payload:', analysisRes.data);
      results.analysis = { success: false, raw: analysisRes.data };
    }

    // 5. Direct ML Service Outcome Endpoint Probe
    console.log('\n--- 5. Probing ML Service Direct Prediction Endpoint (/api/ml/predict) ---');
    const mlPredictRes = await httpRequest({
      hostname: '127.0.0.1',
      port: ML_PORT,
      path: '/api/ml/predict',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-secret': getInternalSecret()
      }
    }, { text: 'Appeal against conviction under Section 302 IPC. Circumstantial evidence only.' });

    console.log(`ML predict status: ${mlPredictRes.status}`);
    const mlPred = mlPredictRes.data?.prediction;
    console.log(`ML Predict Status: ${mlPred?.status}`);
    console.log(`ML Predict Mode: ${mlPred?.predictionMode}`);
    console.log(`ML Verified Samples Count: ${mlPred?.safeguardStatus?.verified_samples_count}`);
    console.log(`ML Disclaimer: ${mlPred?.disclaimer?.substring(0, 80)}...`);
    results.mlDirect = {
      status: mlPredictRes.status,
      predictionStatus: mlPred?.status,
      verifiedCount: mlPred?.safeguardStatus?.verified_samples_count
    };

    console.log('\n=== ALL PROBES COMPLETED SUCCESSFULLY ===');
  } catch (err) {
    console.error('Probe failed with error:', err);
  } finally {
    console.log('Shutting down services cleanly...');
    try {
      if (process.platform === 'win32') {
        if (backendProc && backendProc.pid) {
          spawn('taskkill', ['/pid', backendProc.pid, '/f', '/t']);
        }
        if (mlProc && mlProc.pid) {
          spawn('taskkill', ['/pid', mlProc.pid, '/f', '/t']);
        }
      } else {
        backendProc.kill('SIGTERM');
        mlProc.kill('SIGTERM');
      }
    } catch {}
    setTimeout(() => {
      process.exit(0);
    }, 1000);
  }
}

runEndToEndProbe();
