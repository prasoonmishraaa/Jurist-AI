import request from 'supertest';
import { app } from '../src/app';

describe('Full Analysis, Editable Dossier, Documents & Security Pipeline (/api/v1/analysis)', () => {
  let userAToken = '';
  let userBToken = '';
  let createdAnalysisId = '';

  beforeAll(async () => {
    const resA = await request(app)
      .post('/api/v1/auth/register')
      .send({
        name: 'Advocate Priya Nair',
        email: `priya_${Date.now()}@supremecourtbar.in`,
        password: 'LawyerPassword456!'
      });
    userAToken = resA.body.data.token;

    const resB = await request(app)
      .post('/api/v1/auth/register')
      .send({
        name: 'Advocate Vikram Malhotra',
        email: `vikram_${Date.now()}@delhihighcourtbar.in`,
        password: 'LawyerPassword789!'
      });
    userBToken = resB.body.data.token;
  });

  it('Test B: Constitutional privacy analysis retrieves Puttaswamy with verified PDF source and qualitative assessment', async () => {
    const casePayload = {
      caseTitle: 'Writ Petition: Telecom Interception & Biometric Surveillance',
      court: 'Supreme Court of India',
      category: 'Constitutional Law',
      description:
        'Petitioner challenges state interception of digital telecommunications and biometric metadata without prior judicial warrant, arguing violation of the fundamental right to privacy under Article 21 and freedom of speech under Article 19(1)(a).'
    };

    const res = await request(app)
      .post('/api/v1/analysis')
      .set('Authorization', `Bearer ${userAToken}`)
      .send(casePayload);

    expect(res.status).toBe(201);
    expect(res.body.success).toBe(true);

    const data = res.body.data;
    createdAnalysisId = data._id || data.id;
    expect(data.caseTitle).toBe(casePayload.caseTitle);
    expect(data.applicableLaw).toBeDefined();
    expect(data.caseUnderstanding.factClassification).toBeDefined();
    expect(data.judicialTreatment).toBeDefined();
    expect(data.evidenceTraceGraph).toBeDefined();
    expect(Array.isArray(data.evidenceTraceGraph)).toBe(true);

    // Verify Puttaswamy retrieved cleanly with official SCI PDF and no deprecated main.sci.gov.in URL
    expect(Array.isArray(data.similarCases)).toBe(true);
    expect(data.similarCases.length).toBeGreaterThan(0);
    const puttaswamy = data.similarCases.find((p: any) => p.caseTitle.includes('Puttaswamy'));
    expect(puttaswamy).toBeDefined();
    expect(puttaswamy.officialSourceVerified).toBe(true);
    expect(puttaswamy.officialSourceUrl).toContain('api.sci.gov.in');
    expect(puttaswamy.sourceUrl).not.toContain('main.sci.gov.in');

    // Dual-model outcome evaluation replaces misleading binary win/loss probabilities
    expect(['validated_estimate', 'qualitative_research_mode']).toContain(data.prediction.status);
    expect(data.prediction.winProbability).toBeUndefined();
    expect(data.prediction.probabilities?.win).toBeUndefined();
    expect(data.prediction.probabilities?.loss).toBeUndefined();
    if (data.prediction.status === 'validated_estimate') {
      expect(data.prediction.predictedDisposition).toBeDefined();
      expect(data.prediction.predictedSuccessfulParty).toBeDefined();
      expect(typeof data.prediction.probabilities?.petition_allowed).toBe('number');
    }
  });

  it('Test C: Cheque dishonour (Section 138 NI Act) identifies statutory presumption & Bir Singh / Rangappa', async () => {
    const res = await request(app)
      .post('/api/v1/analysis')
      .set('Authorization', `Bearer ${userAToken}`)
      .send({
        caseTitle: 'NI Act Complaint Defence — Signed Security Cheque',
        court: 'High Court',
        category: 'Banking & Negotiable Instruments',
        description:
          'Accused handed over a blank signed cheque as security during a commercial supply arrangement dated 15 February 2024. Cheque returned dishonoured for insufficient funds, followed by statutory demand notice under Section 138 Negotiable Instruments Act.'
      });

    expect(res.status).toBe(201);
    const titles = res.body.data.similarCases.map((p: any) => p.caseTitle);
    expect(titles.some((t: string) => t.includes('Bir Singh') || t.includes('Rangappa'))).toBe(true);
    const dump = JSON.stringify(res.body.data.legalArguments);
    expect(dump).toContain('139');
  });

  it('Test D: TXT document upload succeeds while empty file and unsupported .doc are rejected cleanly', async () => {
    const sampleTxt = Buffer.from(
      'An incident occurred on 2 August 2024 and FIR was registered on 5 August 2024. On 10 August 2024, the police arrested the Applicant without serving any written grounds of arrest under Article 22(1) or Section 47 BNSS and produced him after 30 hours.',
      'utf-8'
    );

    const okUpload = await request(app)
      .post('/api/v1/analysis')
      .set('Authorization', `Bearer ${userAToken}`)
      .field('caseTitle', 'Uploaded TXT Arrest Challenge')
      .field('category', 'Criminal Law')
      .attach('document', sampleTxt, { filename: 'facts.txt', contentType: 'text/plain' });

    expect(okUpload.status).toBe(201);
    expect(okUpload.body.data.applicableLaw.regimeStatus).toBe('post_july_2024_new_codes');

    const badDocUpload = await request(app)
      .post('/api/v1/analysis')
      .set('Authorization', `Bearer ${userAToken}`)
      .field('caseTitle', 'Legacy DOC Reject')
      .attach('document', Buffer.from('legacy content here 1234567890'), {
        filename: 'brief.doc',
        contentType: 'application/msword'
      });

    expect(badDocUpload.status).toBe(400);
    expect(badDocUpload.body.success).toBe(false);

    const emptyTxtUpload = await request(app)
      .post('/api/v1/analysis')
      .set('Authorization', `Bearer ${userAToken}`)
      .field('caseTitle', 'Blank Upload')
      .attach('document', Buffer.from('   '), { filename: 'empty.txt', contentType: 'text/plain' });

    expect(emptyTxtUpload.status).toBe(400);
  });

  it('should persist editable drafts and research notes via PATCH and enforce strict user isolation', async () => {
    const patchRes = await request(app)
      .patch(`/api/v1/analysis/${createdAnalysisId}`)
      .set('Authorization', `Bearer ${userAToken}`)
      .send({
        researchNotes: 'Obtain certified copy of interception authorization order under Telegraph Rules 419A.',
        editedDrafts: {
          'ground-1': 'Edited Ground I: Impugned warrantless surveillance violates K.S. Puttaswamy proportionality test.'
        }
      });

    expect(patchRes.status).toBe(200);
    expect(patchRes.body.data.researchNotes).toContain('419A');
    expect(patchRes.body.data.editedDrafts['ground-1']).toContain('Edited Ground I');

    // Cross-user isolation checks
    const otherRead = await request(app)
      .get(`/api/v1/analysis/${createdAnalysisId}`)
      .set('Authorization', `Bearer ${userBToken}`);
    expect(otherRead.status).toBe(404);

    const otherPatch = await request(app)
      .patch(`/api/v1/analysis/${createdAnalysisId}`)
      .set('Authorization', `Bearer ${userBToken}`)
      .send({ researchNotes: 'Unauthorized tamper attempt' });
    expect(otherPatch.status).toBe(404);
  });

  it('should save and update bookmarks for custom precedent IDs like SC-2017-001 without ObjectId crash', async () => {
    const saveRes = await request(app)
      .post('/api/v1/saved-cases')
      .set('Authorization', `Bearer ${userAToken}`)
      .send({
        precedentId: 'SC-2017-001',
        caseTitle: 'Justice K.S. Puttaswamy (Retd.) and Anr. v. Union of India and Ors.',
        notes: 'Key para on four-pronged proportionality'
      });

    expect(saveRes.status).toBe(201);
    expect(saveRes.body.data.precedentCode).toBe('SC-2017-001');
    expect(saveRes.body.data.officialSourceVerified).toBe(true);

    const bookmarkId = saveRes.body.data._id || saveRes.body.data.id;
    const patchBookmark = await request(app)
      .patch(`/api/v1/saved-cases/${bookmarkId}`)
      .set('Authorization', `Bearer ${userAToken}`)
      .send({ notes: 'Updated proportionality citation note' });

    expect(patchBookmark.status).toBe(200);
    expect(patchBookmark.body.data.notes).toBe('Updated proportionality citation note');
  });
});
