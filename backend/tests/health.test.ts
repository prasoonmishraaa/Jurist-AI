import request from 'supertest';
import { app } from '../src/app';

describe('GET /api/v1/health', () => {
  it('should return 200, healthy status, and live persistence metadata', async () => {
    const res = await request(app).get('/api/v1/health');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.status).toBe('healthy');
    expect(res.body.data.service).toBe('Jurist AI Research API');
    expect(['mongodb', 'in_memory_fallback']).toContain(res.body.data.persistenceMode);
    expect(res.body.data.verifiedPrecedentCount).toBeGreaterThanOrEqual(25);
  });

  it('should respond to root /health check', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
  });
});
