import request from 'supertest';
import { app } from '../src/app';

describe('Authentication API (/api/v1/auth)', () => {
  const testUser = {
    name: 'Advocate Ramesh Sharma',
    email: `ramesh_${Date.now()}@legalchamber.in`,
    password: 'SecurePassword123!'
  };

  let token = '';

  it('should register a new user successfully', async () => {
    const res = await request(app)
      .post('/api/v1/auth/register')
      .send(testUser);

    expect(res.status).toBe(201);
    expect(res.body.success).toBe(true);
    expect(res.body.data.user.email).toBe(testUser.email.toLowerCase());
    expect(res.body.data.token).toBeDefined();
    token = res.body.data.token;
  });

  it('should reject registration with duplicate email', async () => {
    const res = await request(app)
      .post('/api/v1/auth/register')
      .send(testUser);

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
  });

  it('should log in with valid credentials', async () => {
    const res = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: testUser.email,
        password: testUser.password
      });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.token).toBeDefined();
  });

  it('should reject login with wrong password', async () => {
    const res = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: testUser.email,
        password: 'IncorrectPassword'
      });

    expect(res.status).toBe(401);
    expect(res.body.success).toBe(false);
  });

  it('should retrieve authenticated user profile via /me', async () => {
    const res = await request(app)
      .get('/api/v1/auth/me')
      .set('Authorization', `Bearer ${token}`);

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.name).toBe(testUser.name);
  });

  it('should reject unauthenticated profile requests', async () => {
    const res = await request(app).get('/api/v1/auth/me');
    expect(res.status).toBe(401);
    expect(res.body.success).toBe(false);
  });

  it('should ignore privileged role escalation during public registration', async () => {
    const res = await request(app)
      .post('/api/v1/auth/register')
      .send({
        name: 'Privilege Escalation Check',
        email: `nonadmin_${Date.now()}@legalchamber.in`,
        password: 'SecurePassword123!',
        role: 'admin'
      });

    expect(res.status).toBe(201);
    expect(res.body.data.user.role).toBe('user');
  });
});
