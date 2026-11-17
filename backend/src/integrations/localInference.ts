import path from 'path';
import fs from 'fs';
import { logger } from '../utils/logger';
import { judgmentRegistry, VerifiedJudgmentRecord } from '../utils/judgmentRegistry';
import { PrecedentRelevanceClass } from '../models/Analysis';

interface PrecedentArtifacts {
  vocabulary: Record<string, number>;
  idf: number[];
  corpus: any[];
  corpusVectors: number[][];
}

interface OutcomeClassifierArtifacts {
  classes: string[];
  coef: number[][];
  intercept: number[];
  modelVersion: string;
  evaluationMetrics: any;
}

export interface DualModelPipelineArtifact {
  name: string;
  target: string;
  classes: string[];
  vocabulary: Record<string, number>;
  idf: number[];
  coef: number[][];
  intercept: number[];
  sampleSize: number;
  macroF1: number;
  ngramRange: [number, number];
  sublinearTf: boolean;
  norm: string;
}

export interface DualModelArtifacts {
  version: string;
  modelA: DualModelPipelineArtifact;
  modelB: DualModelPipelineArtifact;
}

const LEGAL_STOPWORDS = new Set([
  'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are',
  'arent', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both',
  'but', 'by', 'cant', 'cannot', 'could', 'couldnt', 'did', 'didnt', 'do', 'does', 'doesnt',
  'doing', 'dont', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadnt',
  'has', 'hasnt', 'have', 'havent', 'having', 'he', 'hed', 'hell', 'hes', 'her', 'here',
  'heres', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 'im',
  'ive', 'if', 'in', 'into', 'is', 'isnt', 'it', 'its', 'itself', 'lets', 'me', 'more', 'most',
  'mustnt', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
  'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shant', 'she', 'shed',
  'shell', 'shes', 'should', 'shouldnt', 'so', 'some', 'such', 'than', 'that', 'thats', 'the',
  'their', 'theirs', 'them', 'themselves', 'then', 'there', 'theres', 'these', 'they', 'theyd',
  'theyll', 'theyre', 'theyve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up',
  'very', 'was', 'wasnt', 'we', 'wed', 'well', 'were', 'werent', 'what', 'whats', 'when',
  'whens', 'where', 'wheres', 'which', 'while', 'who', 'whos', 'whom', 'why', 'whys', 'with',
  'wont', 'would', 'wouldnt', 'you', 'youd', 'youll', 'youre', 'youve', 'your', 'yours',
  'yourself', 'yourselves', 'thereof', 'herein', 'wherein', 'aforesaid', 'heretofore'
]);

const LEGAL_TERMS_GAZETTEER: Record<string, string> = {
  'habeas corpus': 'Prerogative writ under Article 32/226 requiring a detained person to be produced to test legality of detention.',
  'mandamus': 'Public law writ commanding a statutory authority or public officer to perform a mandatory legal duty.',
  'certiorari': 'Supervisory writ quashing an order passed without jurisdiction, in violation of natural justice, or suffering from error apparent.',
  'quo warranto': 'Writ requiring a holder of a public office to demonstrate valid legal authority for occupying that office.',
  'res judicata': 'Doctrine barring re-litigation of an issue finally decided on merits between the same parties by a competent court.',
  'ratio decidendi': 'The binding legal rule or principle necessary for the court decision under Article 141 of the Constitution.',
  'obiter dicta': 'Judicial observations not essential to the decision of the specific issue before the court.',
  'mens rea': 'The culpable mental state (such as dishonest intention at inception in cheating) required to constitute an offence.',
  'actus reus': 'The overt physical or legal act prohibited by statute.',
  'quashing': 'Setting aside an FIR, complaint, or criminal proceeding under inherent powers (S. 482 CrPC / S. 528 BNSS) or Article 226.',
  'anticipatory bail': 'Pre-arrest bail sought by a person having reason to believe they may be arrested for a non-bailable offence (S. 438 CrPC / S. 482 BNSS).',
  'regular bail': 'Post-arrest bail application seeking release from judicial or police custody (S. 437/439 CrPC / S. 480/483 BNSS).',
  'default bail': 'Statutory right to bail when investigation is not completed within the prescribed period (S. 167(2) CrPC / S. 187(3) BNSS).',
  'grounds of arrest': 'Written factual particulars explaining why a person is arrested, required under Article 22(1) and S. 50 CrPC / S. 47 BNSS.',
  'remand': 'Magistrate authorization of police or judicial custody upon production of an arrested person within 24 hours (S. 57/167 CrPC / S. 58/187 BNSS).',
  'interim injunction': 'Temporary restraint granted under Order XXXIX Rules 1–2 CPC upon prima facie case, balance of convenience, and irreparable injury.',
  'rebuttable presumption': 'Statutory presumption under Section 139 NI Act requiring the court to presume legally enforceable debt unless rebutted on preponderance of probabilities.',
  'suo motu': 'Judicial cognizance initiated by a court on its own motion without a formal petition.',
  'cheque bounce': 'Dishonour of a cheque for insufficiency of funds or stop-payment attracting Section 138 Negotiable Instruments Act, 1881.',
  'patent illegality': 'Narrow statutory ground under Section 34(2A) Arbitration Act for setting aside domestic arbitral awards vitiated on the face of the record.'
};

interface IssueRule {
  issue: string;
  keywords: string[];
  minMatches: number;
  requiredRegex?: RegExp;
  provision: string;
  description: string;
}

const ISSUE_RULES: IssueRule[] = [
  {
    issue: 'Legality of Arrest, Written Grounds of Arrest & Pre-Arrest Notice',
    keywords: [
      'arrest', 'arrested', 'custody', 'grounds of arrest', 'notice of appearance',
      'section 41a', 'section 41', 'section 35', 'section 47', 'section 50', 'article 22',
      'remand', '24 hours', 'magistrate', 'without notice', 'without warrant'
    ],
    minMatches: 2,
    requiredRegex: /\b(?:arrest|arrested|custody|remand|grounds of arrest|41a|35 bnss|47 bnss|50 crpc|article 22|24 hours)\b/i,
    provision: 'Article 22(1) & 22(2), Constitution of India; S. 35, 47, 48 & 58 BNSS / S. 41, 41A, 50 & 57 CrPC',
    description:
      'Examines whether written grounds of arrest were communicated promptly, whether pre-arrest notice safeguards applied for offences punishable up to 7 years, and whether 24-hour Magistrate production rules were complied with.'
  },
  {
    issue: 'Constitutionality of State Surveillance / Privacy Infringement',
    keywords: ['privacy', 'surveillance', 'biometric', 'aadhaar', 'data', 'fundamental right', 'article 21', 'proportionality', 'tapping'],
    minMatches: 2,
    provision: 'Article 21 & Article 19, Constitution of India',
    description: 'Evaluates whether state or executive interference satisfies legality, legitimate aim, necessity, and proportionality under the Puttaswamy framework.'
  },
  {
    issue: 'Matrimonial Cruelty / Section 498A IPC (Section 85 BNS) Pre-Arrest Safeguards',
    keywords: ['498a', 'section 85', 'dowry', 'matrimonial', 'cruelty by husband', 'stridhan', 'in-laws'],
    minMatches: 1,
    requiredRegex: /\b(?:498a|85 bns|dowry|matrimonial|stridhan|husband or relative)\b/i,
    provision: 'Section 498A IPC / Sections 85 & 86 BNS; Section 41A CrPC / Section 35 BNSS',
    description: 'Evaluates safeguards against mechanical arrest in matrimonial disputes under the Arnesh Kumar framework.'
  },
  {
    issue: 'Mandatory Obligation to Register FIR & Preliminary Inquiry Scope',
    keywords: ['fir', 'section 154', 'section 173 bnss', 'cognizable', 'police refusal', 'preliminary inquiry', 'register fir'],
    minMatches: 2,
    provision: 'Section 154 CrPC / Section 173 BNSS',
    description: 'Assesses whether police must register an FIR immediately upon disclosure of a cognizable offence or within narrow preliminary-inquiry exceptions.'
  },
  {
    issue: 'Rebuttal of Statutory Presumption in Cheque Dishonour',
    keywords: ['138', '139', 'cheque', 'dishonour', 'dishonor', 'negotiable instrument', 'enforceable debt', 'blank cheque', 'insufficient funds'],
    minMatches: 2,
    provision: 'Sections 138, 139 & 141, Negotiable Instruments Act, 1881',
    description: 'Evaluates service of statutory demand notice within limitation, signature admission, and whether the drawer rebutted the Section 139 presumption on preponderance of probabilities.'
  },
  {
    issue: 'Civil Breach of Contract vs. Criminal Cheating & Quashing Maintainability',
    keywords: ['quash', 'quashing', 'section 482', 'section 528', 'abuse of process', '420', '318 bns', 'cheating', 'civil dispute', 'bhajan lal'],
    minMatches: 2,
    provision: 'Section 482 CrPC / Section 528 BNSS; Section 420 IPC / Section 318 BNS; Article 226 Constitution of India',
    description: 'Examines whether initial dishonest intention at inception is pleaded or whether a civil/commercial dispute has been given a criminal colour justifying quashing.'
  },
  {
    issue: 'Arbitrability, Section 8/11 Reference & Award Challenge (Section 34)',
    keywords: ['arbitration', 'arbitral', 'section 8', 'section 11', 'section 34', 'award', 'patent illegality', 'arbitrable'],
    minMatches: 2,
    provision: 'Sections 8, 11 & 34, Arbitration and Conciliation Act, 1996',
    description: 'Assesses existence/validity of the arbitration clause, non-arbitrability thresholds, and narrow grounds of patent illegality or public policy.'
  },
  {
    issue: 'Grant of Regular or Pre-Arrest Bail & Liberty Safeguards',
    keywords: ['bail', 'anticipatory bail', 'regular bail', '438', '439', '480', '482 bnss', '483 bnss', 'incarceration', 'flight risk'],
    minMatches: 2,
    provision: 'Sections 480, 482 & 483 BNSS / Sections 437, 438 & 439 CrPC; Article 21 Constitution of India',
    description: 'Evaluates custody status, the triple test (flight risk, tampering with evidence, witness intimidation), and statutory conditions governing bail.'
  },
  {
    issue: 'Trademark Infringement, Passing Off & Interlocutory Injunction',
    keywords: ['trademark', 'infringement', 'passing off', 'deceptive similarity', 'interim injunction', 'dilution', 'goodwill'],
    minMatches: 2,
    provision: 'Sections 27, 29 & 135, Trade Marks Act, 1999; Order XXXIX Rules 1–2 CPC',
    description: 'Assesses likelihood of consumer confusion, deceptive similarity, prior user/registration rights, and equitable factors for interlocutory relief.'
  }
];

interface QuerySignals {
  isArrestOrCustody: boolean;
  isWrittenGroundsOr24Hrs: boolean;
  isBail: boolean;
  isCheatingOrCommercialCrime: boolean;
  isMatrimonial498A: boolean;
  isPrivacyOrArticle21: boolean;
  isCheque138: boolean;
  isQuashing: boolean;
  isFIR: boolean;
  isArbitration: boolean;
  isTrademark: boolean;
  isSpecialActPmlaUapa: boolean;
}

class LocalLegalInferenceEngine {
  private precedentArtifacts: PrecedentArtifacts | null = null;
  private classifierArtifacts: OutcomeClassifierArtifacts | null = null;
  private dualModelArtifacts: DualModelArtifacts | null = null;
  private isLoaded = false;
  private termIndexList: string[] = [];

  constructor() {
    this.loadArtifacts();
  }

  private loadArtifacts() {
    try {
      const candidateDirs = [
        path.resolve(__dirname, 'artifacts'),
        path.resolve(__dirname, '../src/integrations/artifacts'),
        path.resolve(__dirname, '../../src/integrations/artifacts'),
        path.resolve(__dirname, '../../../ml-service/app/models'),
        path.resolve(process.cwd(), 'backend/src/integrations/artifacts'),
        path.resolve(process.cwd(), 'backend/dist/integrations/artifacts'),
        path.resolve(process.cwd(), 'ml-service/app/models')
      ];

      let precPath = '';
      let clsPath = '';
      let dualPath = '';

      for (const dir of candidateDirs) {
        const p1 = path.join(dir, 'precedents_artifacts.json');
        const p2 = path.join(dir, 'outcome_model_artifacts.json');
        const p3 = path.join(dir, 'dual_model_artifacts.json');
        if (fs.existsSync(p1) && !precPath) {
          precPath = p1;
          clsPath = fs.existsSync(p2) ? p2 : '';
        }
        if (fs.existsSync(p3) && !dualPath) {
          dualPath = p3;
        }
      }

      if (precPath) {
        this.precedentArtifacts = JSON.parse(fs.readFileSync(precPath, 'utf-8'));
        if (clsPath) {
          this.classifierArtifacts = JSON.parse(fs.readFileSync(clsPath, 'utf-8'));
        }

        if (this.precedentArtifacts) {
          this.termIndexList = new Array(this.precedentArtifacts.idf.length).fill('');
          for (const [term, idx] of Object.entries(this.precedentArtifacts.vocabulary)) {
            this.termIndexList[idx] = term;
          }
        }

        this.isLoaded = true;
        logger.info(`Local Legal Inference Engine loaded (${this.precedentArtifacts?.corpus?.length || 0} precedent records).`);
      } else {
        logger.warn('Precedent artifacts file not found in backend/src/integrations/artifacts. Running with registry fallback.');
      }

      if (dualPath) {
        try {
          this.dualModelArtifacts = JSON.parse(fs.readFileSync(dualPath, 'utf-8'));
          logger.info(`Experimental Dual-Model Artifacts loaded successfully from ${dualPath}.`);
        } catch (e: any) {
          logger.warn(`Failed to parse dual_model_artifacts.json: ${e.message}`);
        }
      } else {
        logger.info('dual_model_artifacts.json not found in candidate paths; qualitative research fallback will be active if microservice is offline.');
      }
    } catch (err: any) {
      logger.error('Failed to load local inference artifacts:', err.message);
    }
  }

  public tokenize(text: string): string[] {
    const cleaned = text.toLowerCase().replace(/[\r\n\t]+/g, ' ');
    const rawTokens = cleaned.match(/\b[a-zA-Z0-9_\-]+\b/g) || [];
    return rawTokens.filter(t => !LEGAL_STOPWORDS.has(t) && t.length > 1);
  }

  public generateTfidfVector(text: string): number[] {
    if (!this.precedentArtifacts) return [];

    const vocab = this.precedentArtifacts.vocabulary;
    const idf = this.precedentArtifacts.idf;
    const vector = new Array(idf.length).fill(0);
    const tokens = this.tokenize(text);

    const termCounts: Record<string, number> = {};

    for (const t of tokens) {
      termCounts[t] = (termCounts[t] || 0) + 1;
    }

    for (let i = 0; i < tokens.length - 1; i++) {
      const bigram = `${tokens[i]} ${tokens[i + 1]}`;
      if (vocab[bigram] !== undefined) {
        termCounts[bigram] = (termCounts[bigram] || 0) + 1;
      }
    }

    for (const [term, count] of Object.entries(termCounts)) {
      const idx = vocab[term];
      if (idx !== undefined) {
        const tf = 1.0 + Math.log(count);
        vector[idx] = tf * idf[idx];
      }
    }

    let norm = 0;
    for (let i = 0; i < vector.length; i++) {
      norm += vector[i] * vector[i];
    }
    norm = Math.sqrt(norm);

    if (norm > 0) {
      for (let i = 0; i < vector.length; i++) {
        vector[i] /= norm;
      }
    }

    return vector;
  }

  public cosineSimilarity(v1: number[], v2: number[]): number {
    let dot = 0;
    const len = Math.min(v1.length, v2.length);
    for (let i = 0; i < len; i++) {
      dot += v1[i] * v2[i];
    }
    return Math.max(0, dot);
  }

  private detectQuerySignals(queryLower: string): QuerySignals {
    return {
      isArrestOrCustody: /\b(?:arrest|arrested|custody|detained|detention|remand|police station|41a|35 bnss|47 bnss|50 crpc|57 crpc|58 bnss)\b/i.test(queryLower),
      isWrittenGroundsOr24Hrs: /\b(?:grounds of arrest|written grounds|reason for arrest|not informed|without notice|notice|24 hours|24 hrs|article 22|magistrate|remand)\b/i.test(queryLower),
      isBail: /\b(?:bail|anticipatory|regular bail|default bail|437|438|439|480|482 bnss|483 bnss|custody)\b/i.test(queryLower),
      isCheatingOrCommercialCrime: /\b(?:cheat|cheating|420|318 bns|fraud|dishonest inducement|breach of trust|406)\b/i.test(queryLower),
      isMatrimonial498A: /\b(?:498a|85 bns|dowry|matrimonial|cruelty|stridhan|marriage|spouse)\b/i.test(queryLower),
      isPrivacyOrArticle21: /\b(?:privacy|surveillance|aadhaar|biometric|phone tap|personal data|decisional autonomy|intrus)/i.test(queryLower),
      isCheque138: /\b(?:138|139|cheque|dishonour|dishonor|blank cheque|stop payment|insufficient funds|negotiable instrument)\b/i.test(queryLower),
      isQuashing: /\b(?:quash|quashing|482 crpc|528 bnss|abuse of process|frivolous fir|bhajan lal)\b/i.test(queryLower),
      isFIR: /\b(?:register fir|refusal to register|section 154|173 bnss|cognizable|preliminary inquiry)\b/i.test(queryLower),
      isArbitration: /\b(?:arbitration|arbitral|arbitrator|section 8|section 11|section 34|patent illegality|arbitrable)\b/i.test(queryLower),
      isTrademark: /\b(?:trademark|passing off|infringement|deceptive similarity|mark|goodwill)\b/i.test(queryLower),
      isSpecialActPmlaUapa: /\b(?:pmla|money laundering|uapa|unlawful activities|mcoca|ndps|gujcoca)\b/i.test(queryLower)
    };
  }

  private evaluatePrecedentFit(
    signals: QuerySignals,
    caseItem: VerifiedJudgmentRecord | any
  ): {
    domainBoost: number;
    relevanceClassification: PrecedentRelevanceClass;
    retrievalReason: string;
  } {
    const id = caseItem.id || '';
    const title = caseItem.caseTitle || '';
    const cat = (caseItem.category || '').toLowerCase();

    let boost = 0;
    let relevance: PrecedentRelevanceClass = 'Supporting authority';
    let reason = `Retrieved for overlapping statutory concepts (${(caseItem.legalProvisions || []).slice(0, 3).join(', ')}).`;

    // Arrest / Detention / Written Grounds / Pre-Arrest Notice cluster
    if (signals.isArrestOrCustody) {
      if (id === 'SC-2025-026') {
        boost += signals.isWrittenGroundsOr24Hrs ? 0.52 : 0.36;
        relevance = 'Directly relevant';
        reason =
          'Directly relevant under ordinary criminal law (Article 22(1) Constitution & S. 50 CrPC / S. 47 BNSS): non-communication of written grounds of arrest invalidates arrest and subsequent remand.';
      } else if (id === 'SC-2025-027') {
        boost += signals.isWrittenGroundsOr24Hrs ? 0.50 : 0.34;
        relevance = 'Directly relevant';
        reason =
          'Directly relevant Constitution-wide mandate applying written grounds of arrest to all offences under IPC / BNS 2023 across all courts and agencies.';
      } else if (id === 'SC-2024-025') {
        boost += signals.isWrittenGroundsOr24Hrs ? 0.44 : 0.28;
        relevance = signals.isSpecialActPmlaUapa ? 'Directly relevant' : 'Supporting authority';
        reason = signals.isSpecialActPmlaUapa
          ? 'Directly establishes mandatory supply of written "grounds of arrest" as distinguished from generic "reasons for arrest".'
          : 'Supporting authority (arose under UAPA; its distinction between written "grounds of arrest" and formal "reasons" was expressly extended to general IPC/BNS arrests).';
      } else if (id === 'SC-2023-024') {
        boost += signals.isWrittenGroundsOr24Hrs ? 0.40 : 0.24;
        relevance = signals.isSpecialActPmlaUapa ? 'Directly relevant' : 'Supporting authority';
        reason = signals.isSpecialActPmlaUapa
          ? 'Directly requires written copy of grounds of arrest to be furnished to the arrestee as a matter of course under PMLA.'
          : 'Supporting authority on written communication of grounds of arrest under Article 22(1) (note factual setting involved PMLA S. 19).';
      } else if (id === 'SC-2014-003') {
        boost += 0.44;
        relevance = signals.isMatrimonial498A ? 'Directly relevant' : 'Supporting authority';
        reason = signals.isMatrimonial498A
          ? 'Directly binding precedent under S. 498A IPC and S. 41/41A CrPC requiring mandatory checklist and notice before arrest.'
          : 'Supporting procedural authority: Supreme Court directions under S. 41/41A CrPC (now S. 35 BNSS) govern ALL offences punishable up to 7 years (underlying facts involved S. 498A IPC, which is absent here).';
      } else if (id === 'SC-2022-023') {
        boost += 0.45;
        relevance = 'Directly relevant';
        reason =
          'Directly reiterates Arnesh Kumar notice compliance under S. 41/41A CrPC (S. 35 BNSS), Magistrate oversight on remand, and bail consideration for Category A offences (<=7 years).';
      } else if (id === 'SC-1996-012') {
        boost += 0.34;
        relevance = 'Constitutional background';
        reason =
          'Foundational Article 21/22 custodial safeguard precedent governing arrest memo, relative intimation, medical inspection, and custody record transparency.';
      } else if (id === 'SC-1978-010') {
        boost += 0.22;
        relevance = 'Constitutional background';
        reason =
          'Foundational Article 21 due-process standard: liberty deprivation must follow fair, just, and reasonable statutory procedure.';
      } else if (id === 'SC-1978-014') {
        boost += signals.isBail ? 0.30 : 0.16;
        relevance = 'Constitutional background';
        reason = 'Articulates "bail, not jail" constitutional liberty principle while assessing custodial necessity.';
      }
    }

    // Civil-Criminal Cheating / Quashing cluster
    if (signals.isQuashing || signals.isCheatingOrCommercialCrime) {
      if (id === 'SC-1990-009') {
        boost += signals.isQuashing ? 0.46 : 0.28;
        relevance = signals.isQuashing ? 'Directly relevant' : 'Supporting authority';
        reason =
          'Leading Constitution/Bench threshold precedent establishing 7 exhaustive categories for quashing FIRs/proceedings under S. 482 CrPC (S. 528 BNSS) / Art. 226 where civil breach lacks criminal ingredients.';
      }
    }

    // Cheque Dishonour cluster
    if (signals.isCheque138) {
      if (id === 'SC-2019-007' || id === 'SC-2010-008') {
        boost += 0.50;
        relevance = 'Potentially adverse authority';
        reason =
          'Binding NI Act authority holding that S. 139 statutory presumption favours the holder (including in blank signed cheque pleas) unless rebutted on preponderance of probabilities; adverse to uncorroborated drawer defences.';
      } else if (id === 'SC-1990-009' && signals.isQuashing) {
        boost += 0.25;
        relevance = 'Supporting authority';
        reason = 'Relevant where maintainability/quashing of S. 138 summoning is urged for non-fulfilment of statutory notice/limitation ingredients.';
      } else if (cat.includes('family') || id === 'ALL-2020-022' || id === 'SC-2017-006') {
        boost -= 0.35;
      }
    }

    // Constitutional Privacy cluster
    if (signals.isPrivacyOrArticle21) {
      if (id === 'SC-2017-001') {
        boost += 0.52;
        relevance = 'Directly relevant';
        reason = 'Nine-Judge Bench authority affirming informational privacy under Article 21 and the three/four-pronged proportionality test.';
      } else if (id === 'SC-2015-002') {
        boost += 0.30;
        relevance = 'Supporting authority';
        reason = 'Examines overbreadth, vagueness, and proportionality restrictions on speech and digital communications.';
      } else if (id === 'SC-1978-010') {
        boost += 0.28;
        relevance = 'Constitutional background';
        reason = 'Core Article 21 fair, just, and reasonable procedure threshold.';
      }
    }

    // FIR registration cluster
    if (signals.isFIR && id === 'SC-2013-004') {
      boost += 0.48;
      relevance = 'Directly relevant';
      reason = 'Constitution Bench ruling mandating FIR registration upon cognizable disclosure under S. 154 CrPC (S. 173 BNSS), noting exceptions for commercial/matrimonial delays.';
    }

    // Arbitration / Commercial Award cluster
    if (signals.isArbitration) {
      if (id === 'SC-2020-013') {
        boost += 0.48;
        relevance = 'Directly relevant';
        reason = 'Three-Judge Bench precedent establishing four-fold non-arbitrability test and "when in doubt, refer" standard under S. 8 & 11.';
      } else if (id === 'SC-2014-020') {
        boost += 0.46;
        relevance = 'Directly relevant';
        reason = 'Landmark interpretation of "fundamental policy of Indian law", perversity, and non-reappreciation of evidence under S. 34 Arbitration Act.';
      }
    }

    // Trademark cluster
    if (signals.isTrademark && id === 'DEL-2022-016') {
      boost += 0.48;
      relevance = 'Directly relevant';
      reason = 'High Court authority on well-known mark protection, trans-border reputation, and injunction against deceptively similar misuse.';
    }

    // Suppress clearly unrelated matrimonial/family/personal-law cases when query has zero family signals
    if (!signals.isMatrimonial498A && (id === 'SC-2017-006' || id === 'ALL-2020-022')) {
      boost -= 0.30;
    }

    // Note on SC-2019-021 / SC-2022-018: avoid surfacing special-statute SC/ST or GUJCOCA cases unless query implicates them
    if (!signals.isSpecialActPmlaUapa && (id === 'SC-2019-021' || id === 'SC-2022-018')) {
      boost -= 0.18;
    }

    return { domainBoost: boost, relevanceClassification: relevance, retrievalReason: reason };
  }

  public retrieveSimilarPrecedents(queryText: string, topK = 5, minScore = 0.04) {
    const corpus: any[] = this.precedentArtifacts?.corpus?.length
      ? this.precedentArtifacts.corpus
      : judgmentRegistry.getAll();

    if (!corpus || corpus.length === 0) {
      return [];
    }

    const queryLower = queryText.toLowerCase();
    const signals = this.detectQuerySignals(queryLower);
    const queryVec = this.precedentArtifacts ? this.generateTfidfVector(queryText) : [];
    const queryTokens = new Set(this.tokenize(queryText));

    const scored = corpus.map((caseItem: any, idx: number) => {
      const reg = judgmentRegistry.findById(caseItem.id) || caseItem;
      const tfidfSim =
        queryVec.length > 0 && this.precedentArtifacts?.corpusVectors?.[idx]
          ? this.cosineSimilarity(queryVec, this.precedentArtifacts.corpusVectors[idx])
          : 0;

      const { domainBoost, relevanceClassification, retrievalReason } = this.evaluatePrecedentFit(signals, reg);

      // Extract matched query tokens from title, provisions, summary, and text
      const docText = `${reg.caseTitle} ${(reg.legalProvisions || []).join(' ')} ${reg.summary} ${reg.judgmentText}`.toLowerCase();
      const docTokens = new Set(this.tokenize(docText));
      const matchedTerms: string[] = [];
      for (const t of queryTokens) {
        if (docTokens.has(t) && !matchedTerms.includes(t)) {
          matchedTerms.push(t);
        }
      }
      const tokenOverlapBonus = Math.min(0.18, matchedTerms.length * 0.02);

      const rawCombined = tfidfSim * 0.65 + domainBoost + tokenOverlapBonus;
      const clampedScore = Math.max(0, Math.min(0.99, rawCombined));

      return {
        id: reg.id,
        caseTitle: reg.caseTitle,
        court: reg.court,
        judgmentDate: reg.judgmentDate,
        caseIdentifier: reg.caseIdentifier,
        citation: reg.citation,
        bench: reg.bench,
        category: reg.category,
        legalProvisions: reg.legalProvisions || [],
        summary: reg.summary,
        judgmentText: reg.judgmentText,
        officialSourceUrl: reg.officialSourceUrl || '',
        officialSourceLabel: reg.officialSourceLabel || '',
        officialSourceVerified: Boolean(reg.officialSourceVerified),
        secondaryReferenceUrl: reg.secondaryReferenceUrl || '',
        secondaryReferenceLabel: reg.secondaryReferenceLabel || '',
        sourceUrl: reg.sourceUrl || reg.officialSourceUrl || reg.secondaryReferenceUrl || '',
        verificationStatus: reg.verificationStatus || 'unverified',
        verificationNote: reg.verificationNote || '',
        article141Status: reg.article141Status || '',
        obiterAndScopeNote: reg.obiterAndScopeNote || '',
        subsequentTreatment: reg.subsequentTreatment || '',
        similarityScore: Math.round(clampedScore * 10000) / 10000,
        matchedTerms: matchedTerms.slice(0, 8),
        relevanceClassification,
        retrievalReason,
        historicalOutcome: reg.outcome || caseItem.outcome,
        outcomeRationale: reg.outcomeRationale || caseItem.outcomeRationale
      };
    });

    scored.sort((a, b) => b.similarityScore - a.similarityScore);
    return scored.filter(c => c.similarityScore >= minScore).slice(0, topK);
  }

  private sanitizePreDecisionText(text: string): string {
    if (!text) return '';
    // Strip concluding operative order headers and decrees if present
    const operativeRegex = /(?:^|\n)\s*(?:O\s*R\s*D\s*E\s*R|OPERATIVE\s+ORDER|FINAL\s+ORDER|CONCLUSION|DISPOSITION|IN\s+THE\s+RESULT)\s*(?::|-|\n)[\s\S]*$/i;
    let sanitized = text.replace(operativeRegex, '');

    // Strip explicit concluding decretal lines
    sanitized = sanitized.replace(/(?:^|\n)\s*(?:Accordingly|Consequently|In\s+the\s+result|Resultantly)[,\s]+(?:the\s+)?(?:appeal|petition)\s+(?:is|stands|deserves\s+to\s+be)\s+(?:allowed|dismissed)[\s\S]*$/i, '');
    return sanitized.trim() || text;
  }

  private evaluateDualModel(text: string, model: DualModelPipelineArtifact): {
    prediction: string;
    probabilities: Record<string, number>;
    rawScores: Record<string, number>;
    maxProb: number;
  } {
    const sanitized = this.sanitizePreDecisionText(text);
    const lower = sanitized.toLowerCase();
    const tokens = lower.match(/\b\w\w+\b/g) || [];
    const ngrams: string[] = [...tokens];
    for (let i = 0; i < tokens.length - 1; i++) {
      ngrams.push(`${tokens[i]} ${tokens[i + 1]}`);
    }

    const termCounts: Record<string, number> = {};
    for (const ng of ngrams) {
      termCounts[ng] = (termCounts[ng] || 0) + 1;
    }

    const numFeatures = model.idf.length;
    const vec = new Float64Array(numFeatures);

    for (const [term, count] of Object.entries(termCounts)) {
      const idx = model.vocabulary[term];
      if (idx !== undefined && idx < numFeatures) {
        // sublinear_tf: 1.0 + ln(count)
        const tf = 1.0 + Math.log(count);
        vec[idx] = tf * model.idf[idx];
      }
    }

    // L2 norm
    let sumSq = 0;
    for (let i = 0; i < numFeatures; i++) {
      sumSq += vec[i] * vec[i];
    }
    const norm = Math.sqrt(sumSq);
    if (norm > 0) {
      for (let i = 0; i < numFeatures; i++) {
        vec[i] /= norm;
      }
    }

    // Decision function: scores = coef * vec + intercept
    const numClasses = model.classes.length;
    const scores = new Float64Array(numClasses);
    let maxScore = -Infinity;

    for (let c = 0; c < numClasses; c++) {
      let dot = 0;
      const coefRow = model.coef[c];
      for (let i = 0; i < numFeatures; i++) {
        if (vec[i] !== 0) {
          dot += coefRow[i] * vec[i];
        }
      }
      scores[c] = dot + model.intercept[c];
      if (scores[c] > maxScore) {
        maxScore = scores[c];
      }
    }

    // Softmax
    let sumExp = 0;
    const expScores = new Float64Array(numClasses);
    for (let c = 0; c < numClasses; c++) {
      expScores[c] = Math.exp(scores[c] - maxScore);
      sumExp += expScores[c];
    }

    let maxProb = 0;
    let bestClassIdx = 0;
    const probabilities: Record<string, number> = {};
    const rawScores: Record<string, number> = {};

    for (let c = 0; c < numClasses; c++) {
      const prob = sumExp > 0 ? expScores[c] / sumExp : 0;
      rawScores[model.classes[c]] = prob;
      const roundedProb = Math.round(prob * 10000) / 10000;
      probabilities[model.classes[c]] = roundedProb;
      if (prob > maxProb) {
        maxProb = prob;
        bestClassIdx = c;
      }
    }

    return {
      prediction: model.classes[bestClassIdx],
      probabilities,
      rawScores,
      maxProb: Math.round(maxProb * 1000) / 1000
    };
  }

  public detectCaseDomain(text: string, category?: string): string {
    const cat = (category || '').toLowerCase().trim();
    if (cat.includes('criminal')) return 'criminal';
    if (
      cat.includes('commercial') ||
      cat.includes('corporate') ||
      cat.includes('arbitrat') ||
      cat.includes('banking') ||
      cat.includes('tax')
    ) {
      return 'commercial_civil';
    }
    if (
      cat.includes('constitutional') ||
      cat.includes('writ') ||
      cat.includes('civil') ||
      cat.includes('administrative')
    ) {
      return 'civil_writ';
    }

    const textLower = text.toLowerCase();
    const hasCriminal = /\b(?:chargesheet|police custody|judicial custody|remand order|bail application|regular bail|anticipatory bail|438 crpc|439 crpc|480 bnss|482 bnss|483 bnss|section 302|section 420|section 498a|section 318)\b/i.test(textLower);
    const hasCommercial = /\b(?:arbitrat|arbitral|section 8|section 11|section 34|commercial suit|recovery suit|promissory note|trademark|patent|insolvency|nclt)\b/i.test(textLower);
    const hasWrit = /\b(?:writ petition|article 32|article 226|mandamus|certiorari|fundamental right)\b/i.test(textLower);

    if (hasCommercial && !hasCriminal) return 'commercial_civil';
    if (hasWrit && !hasCriminal) return 'civil_writ';
    if (hasCriminal) return 'criminal';
    return 'general';
  }

  /**
   * Evaluates experimental outcome prediction using verified Model A & Model B artifacts.
   * If model artifacts are missing or text is insufficient, gracefully falls back to qualitative research mode.
   */
  public predictOutcome(text: string, category?: string, _maxSimilarity = 0.5) {
    if (!text || text.trim().length < 15) {
      return {
        status: 'insufficient_input',
        estimatedOutcome: 'Insufficient Case Input',
        rationale: 'Provide at least a concise factual chronology and statutory grievance for structured legal research.',
        modelVersion: 'jurist-legal-research-v2.0',
        disclaimer: 'This platform prepares structured legal research and draft submissions rather than automated judicial outcome predictions.'
      };
    }

    if (this.dualModelArtifacts?.modelA && this.dualModelArtifacts?.modelB) {
      const evalA = this.evaluateDualModel(text, this.dualModelArtifacts.modelA);
      const evalB = this.evaluateDualModel(text, this.dualModelArtifacts.modelB);

      // Domain validation for Model B substantive party
      const domain = this.detectCaseDomain(text, category);
      const isNonCriminal = domain === 'civil_writ' || domain === 'commercial_civil';
      let modelBAbstained = false;
      let modelBDomainLimitation: string | undefined = undefined;
      let finalPredParty = evalB.prediction;

      if (isNonCriminal) {
        modelBDomainLimitation =
          "Domain Limitation: Party identities 'accused' and 'state_prosecution' are specific to criminal proceedings and are legally inapplicable to civil and constitutional writ litigation. Model B taxonomy contains criminal classes which do not apply to this proceeding.";
        if (evalB.prediction === 'accused' || evalB.prediction === 'state_prosecution') {
          modelBAbstained = true;
          finalPredParty = 'domain_abstained';
        }
      }

      const confidence = evalA.maxProb >= 0.50 ? 'Moderate' : 'Low';
      const estimatedOutcomeStr = modelBAbstained
        ? `${evalA.prediction} (Prevailing: Abstained — Civil Domain)`
        : `${evalA.prediction} (Prevailing: ${finalPredParty})`;

      const rationaleStr = modelBAbstained
        ? `Experimental precedent analysis: Model A estimates disposition '${evalA.prediction}' (${Math.round(evalA.maxProb * 100)}% uncalibrated score). Model B abstains from party estimation because criminal party labels ('accused' / 'state_prosecution') are outside the substantive scope of civil/constitutional litigation.`
        : `Experimental precedent analysis: Model A estimates disposition '${evalA.prediction}' (${Math.round(evalA.maxProb * 100)}% uncalibrated score); Model B estimates prevailing party '${finalPredParty}' (${Math.round(evalB.maxProb * 100)}% uncalibrated score) based on pre-decision text features.`;

      return {
        status: 'validated_estimate',
        predictionMode: 'statistical_verified',
        isExperimental: true,
        predictedDisposition: evalA.prediction,
        predictedSuccessfulParty: finalPredParty,
        disposition: evalA.prediction,
        successfulParty: finalPredParty,
        estimatedOutcome: estimatedOutcomeStr,
        domainDetected: domain,
        modelA: {
          target: 'judicial_disposition',
          prediction: evalA.prediction,
          uncalibratedScores: evalA.probabilities,
          rawScores: evalA.rawScores,
          confidenceScore: evalA.maxProb,
          confidenceLevel: evalA.maxProb >= 0.50 ? 'Moderate' : 'Low',
          sampleSize: this.dualModelArtifacts.modelA.sampleSize || 43,
          macroF1: this.dualModelArtifacts.modelA.macroF1 || 0.2559,
          classes: this.dualModelArtifacts.modelA.classes,
          domainStatus: 'supported'
        },
        modelB: {
          target: 'successful_party',
          prediction: finalPredParty,
          rawPrediction: evalB.prediction,
          uncalibratedScores: evalB.probabilities,
          rawScores: evalB.rawScores,
          confidenceScore: modelBAbstained ? 0.0 : evalB.maxProb,
          confidenceLevel: modelBAbstained ? 'Abstained (Domain Limitation)' : (evalB.maxProb >= 0.50 ? 'Moderate' : 'Low'),
          sampleSize: this.dualModelArtifacts.modelB.sampleSize || 37,
          macroF1: this.dualModelArtifacts.modelB.macroF1 || 0.3664,
          classes: this.dualModelArtifacts.modelB.classes,
          domainStatus: isNonCriminal ? 'domain_limited' : 'supported',
          domainLimitation: modelBDomainLimitation,
          abstained: modelBAbstained
        },
        probabilities: evalA.probabilities,
        confidenceScore: evalA.maxProb,
        confidenceLevel: confidence,
        rationale: rationaleStr,
        modelVersion: 'v4.26-dual-experimental',
        disclaimer:
          'Experimental research prototype for presentation demonstration. Trained on 43 (Model A) and 37 (Model B) verified judicial precedents. Class scores are uncalibrated historical vocabulary correlations and do not constitute legal advice.'
      };
    }

    return {
      status: 'qualitative_research_mode',
      estimatedOutcome: 'Structured Doctrinal & Authority Assessment',
      rationale:
        'Relief depends on verified evidentiary records, statutory limitation, procedural compliance under applicable law, and judicial discretion on opposing submissions rather than statistical extrapolation from historical appellate counts.',
      modelVersion: 'jurist-legal-research-v2.0',
      disclaimer:
        'Legal research output only. Judicial discretion turns on proved facts, case diaries/documents on record, and oral advocacy in court.'
    };
  }

  public extractEntities(text: string) {
    const courts: string[] = [];
    const courtMatches = [
      /Supreme Court of India/gi,
      /High Court of [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?/gi,
      /(?:Delhi|Bombay|Allahabad|Calcutta|Madras|Karnataka|Gujarat|Punjab and Haryana)\s+High Court/gi,
      /National Company Law (?:Appellate )?Tribunal/gi,
      /Judicial Magistrate First Class|Chief Judicial Magistrate|Additional Chief Judicial Magistrate|Sessions Court|Magistrate/gi
    ];
    for (const rx of courtMatches) {
      const match = text.match(rx);
      if (match) {
        match.forEach(m => {
          const clean = m.trim();
          if (!courts.some(existing => existing.toLowerCase() === clean.toLowerCase())) {
            courts.push(clean);
          }
        });
      }
    }

    const statutes: string[] = [];
    const knownStatutePatterns: Array<{ pattern: RegExp; canonical: string }> = [
      { pattern: /\b(?:Constitution of India|Article\s+\d+)\b/i, canonical: 'Constitution of India' },
      { pattern: /\b(?:Bharatiya Nyaya Sanhita|BNS)\b/i, canonical: 'Bharatiya Nyaya Sanhita, 2023 (BNS)' },
      { pattern: /\b(?:Bharatiya Nagarik Suraksha Sanhita|BNSS)\b/i, canonical: 'Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)' },
      { pattern: /\b(?:Bharatiya Sakshya Adhiniyam|BSA)\b/i, canonical: 'Bharatiya Sakshya Adhiniyam, 2023 (BSA)' },
      { pattern: /\b(?:Indian Penal Code|IPC)\b/i, canonical: 'Indian Penal Code, 1860 (IPC)' },
      { pattern: /\b(?:Code of Criminal Procedure|CrPC|Cr\.P\.C\.)\b/i, canonical: 'Code of Criminal Procedure, 1973 (CrPC)' },
      { pattern: /\b(?:Indian Evidence Act|Evidence Act)\b/i, canonical: 'Indian Evidence Act, 1872' },
      { pattern: /\b(?:Code of Civil Procedure|CPC)\b/i, canonical: 'Code of Civil Procedure, 1908 (CPC)' },
      { pattern: /\b(?:Negotiable Instruments Act|NI Act)\b/i, canonical: 'Negotiable Instruments Act, 1881' },
      { pattern: /\b(?:Information Technology Act|IT Act)\b/i, canonical: 'Information Technology Act, 2000' },
      { pattern: /\b(?:Arbitration and Conciliation Act|Arbitration Act)\b/i, canonical: 'Arbitration and Conciliation Act, 1996' },
      { pattern: /\b(?:Trade Marks Act|Trademark Act)\b/i, canonical: 'Trade Marks Act, 1999' },
      { pattern: /\b(?:Specific Relief Act)\b/i, canonical: 'Specific Relief Act, 1963' },
      { pattern: /\b(?:Indian Contract Act|Contract Act)\b/i, canonical: 'Indian Contract Act, 1872' },
      { pattern: /\b(?:Limitation Act)\b/i, canonical: 'Limitation Act, 1963' }
    ];
    for (const s of knownStatutePatterns) {
      if (s.pattern.test(text) && !statutes.includes(s.canonical)) {
        statutes.push(s.canonical);
      }
    }

    const sections: string[] = [];
    const secRx =
      /\b(?:Section|Sections|Sec\.|S\.|u\/s|Article|Articles|Art\.)\s+(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]+\))?(?:\s*(?:,|&|and|to)\s*\d+[A-Z]?(?:\(\d+\))?)*)(?:\s+(?:of(?:\s+the)?\s+)?([A-Za-z][A-Za-z\s,]{1,40}?(?:\b(?:IPC|BNS|BNSS|CrPC|CPC|BSA|NI Act|IT Act|Constitution|Act|1973|1860|1881|1996|1999|2023)\b)))?/gi;
    let match: RegExpExecArray | null;
    while ((match = secRx.exec(text)) !== null) {
      const sec = match[1].trim();
      const act = match[2] ? match[2].trim().replace(/\s+/g, ' ') : '';
      const entry = act ? `Section/Article ${sec} (${act})` : `Section/Article ${sec}`;
      if (!sections.includes(entry)) sections.push(entry);
    }

    const citations: string[] = [];
    const citRx = /\b(?:\(\d{4}\)|\d{4})\s+(?:\d+\s+)?(?:INSC|SCC|AIR|SCR|SCALE|SCC OnLine(?:\s+[A-Z][a-z]+)?)\s+\d+\b/gi;
    const citMatches = text.match(citRx);
    if (citMatches) {
      citMatches.forEach(c => {
        if (!citations.includes(c)) citations.push(c);
      });
    }

    const legalTerms: Array<{ term: string; definition: string }> = [];
    const textLower = text.toLowerCase();
    for (const [term, def] of Object.entries(LEGAL_TERMS_GAZETTEER)) {
      if (new RegExp(`\\b${term}\\b`, 'i').test(textLower)) {
        legalTerms.push({
          term: term.charAt(0).toUpperCase() + term.slice(1),
          definition: def
        });
      }
    }

    // Strict party extraction only — never fabricate placeholder names
    const petitioners: string[] = [];
    const respondents: string[] = [];
    const vMatch = text.match(
      /([A-Z][A-Za-z0-9\s.,&'()-]{1,75}?)\s+(?:v\.|vs\.?|versus)\s+([A-Z][A-Za-z0-9\s.,&'()-]{1,75}?)(?=\s+(?:on|dated|in\s+Writ|Criminal|Civil)|[;\n.]|$)/
    );
    if (vMatch) {
      const p = vMatch[1].trim();
      const r = vMatch[2].trim();
      if (p.length > 1 && p.length < 100) petitioners.push(p);
      if (r.length > 1 && r.length < 100) respondents.push(r);
    }

    return {
      parties: { petitioners, respondents },
      courts,
      statutes,
      sections,
      citations,
      legalTerms,
      disclaimer: 'Extracted from user-supplied text via statutory pattern matching; verify against the original record.'
    };
  }

  public identifyIssues(text: string) {
    const textLower = text.toLowerCase();
    const identified: any[] = [];

    for (const rule of ISSUE_RULES) {
      if (rule.requiredRegex && !rule.requiredRegex.test(text)) {
        continue;
      }
      const matched = rule.keywords.filter(kw => textLower.includes(kw));
      if (matched.length >= rule.minMatches) {
        identified.push({
          issue: rule.issue,
          statutoryProvision: rule.provision,
          description: rule.description,
          matchedKeywords: matched
        });
      }
    }

    return identified;
  }
}

export const localInferenceEngine = new LocalLegalInferenceEngine();
