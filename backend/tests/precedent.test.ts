import request from 'supertest';
import { app } from '../src/app';

describe('Precedent API (/api/v1/precedents)', () => {
  it('should list legal precedents with pagination', async () => {
    const res = await request(app).get('/api/v1/precedents?page=1&limit=5');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.data)).toBe(true);
    expect(res.body.pagination).toBeDefined();
    expect(res.body.data.length).toBeGreaterThan(0);
  });

  it('should search precedents by keyword', async () => {
    const res = await request(app).get('/api/v1/precedents?search=privacy');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    const hasPuttaswamy = res.body.data.some((p: any) =>
      p.caseTitle.toLowerCase().includes('puttaswamy') || p.summary.toLowerCase().includes('privacy')
    );
    expect(hasPuttaswamy).toBe(true);
  });

  it('should retrieve a specific precedent by ID/identifier', async () => {
    const res = await request(app).get('/api/v1/precedents/SC-2017-001');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.citation).toContain('(2017) 10 SCC 1');
    expect(res.body.data.court).toBe('Supreme Court of India');
  });
});
