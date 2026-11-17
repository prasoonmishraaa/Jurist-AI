import {
  ICaseUnderstanding,
  IChronologyEvent,
  IEvidenceAuditItem,
  IAvailableRemedyOption,
  ILegalArgument,
  ISupportingPrecedent,
  IMatchedPrecedent,
  IJudicialTreatmentAssessment,
  IAttributedFact,
  IEvidenceTraceNode,
  ISourceDocumentPassage,
  ISupportingJudgmentPassage,
  IRetrievalSignalBreakdown,
  PrecedentRelevanceClass
} from '../models/Analysis';
import { ApplicableLawAssessment } from './legislationService';
import { judgmentRegistry, VerifiedJudgmentRecord } from '../utils/judgmentRegistry';

export class LegalArgumentService {
  private static extractPartiesStrictly(text: string): { petitioners: string[]; respondents: string[] } {
    const petitioners: string[] = [];
    const respondents: string[] = [];

    // 1. Explicit litigation caption: "A v. B" / "A vs. B"
    const vMatch = text.match(
      /([A-Z][A-Za-z0-9\s.,&'()-]{1,75}?)\s+(?:v\.|vs\.?|versus)\s+([A-Z][A-Za-z0-9\s.,&'()-]{1,75}?)(?=\s+(?:on|dated|in\s+Writ|Criminal|Civil)|[;\n.]|$)/
    );
    if (vMatch) {
      const p = vMatch[1].trim();
      const r = vMatch[2].trim();
      if (p.length > 1 && !/^(?:in|the|this|that|case)$/i.test(p)) petitioners.push(p);
      if (r.length > 1 && !/^(?:the|this|that|case)$/i.test(r)) respondents.push(r);
    }

    // 2. Explicit labeled fields like "Petitioner: Name" / "Accused: Name"
    const petLabelRx = /(?:Petitioner|Appellant|Applicant|Complainant|Plaintiff|Accused)\s*:\s*([^\n\r.;,]+)/gi;
    let m: RegExpExecArray | null;
    while ((m = petLabelRx.exec(text)) !== null) {
      const val = m[1].trim();
      if (val.length > 1 && val.length < 80 && !petitioners.includes(val)) {
        petitioners.push(val);
      }
    }

    const respLabelRx = /(?:Respondent|Defendant|Opposite Party|Prosecution|Informant)\s*:\s*([^\n\r.;,]+)/gi;
    while ((m = respLabelRx.exec(text)) !== null) {
      const val = m[1].trim();
      if (val.length > 1 && val.length < 80 && !respondents.includes(val)) {
        respondents.push(val);
      }
    }

    return {
      petitioners: petitioners.length > 0 ? petitioners : ['Not specified.'],
      respondents: respondents.length > 0 ? respondents : ['Not specified.']
    };
  }

  private static toSupportingPrecedent(
    idOrKeyword: string,
    applicationToFacts: string,
    authorityType: string,
    ratioOverride?: string
  ): ISupportingPrecedent {
    const rec: VerifiedJudgmentRecord | undefined =
      judgmentRegistry.findById(idOrKeyword) || judgmentRegistry.findByKeyword(idOrKeyword);

    if (!rec) {
      return {
        caseTitle: idOrKeyword,
        citation: 'Citation requires verification',
        court: 'Supreme Court of India',
        ratioPrinciple: ratioOverride || 'Principle requires independent verification against primary report.',
        applicationToFacts,
        officialSourceUrl: '',
        officialSourceLabel: '',
        officialSourceVerified: false,
        secondaryReferenceUrl: '',
        secondaryReferenceLabel: '',
        sourceUrl: '',
        verificationStatus: 'unverified',
        authorityType
      };
    }

    return {
      id: rec.id,
      caseTitle: rec.caseTitle,
      citation: rec.citation,
      court: rec.court,
      bench: rec.bench,
      judgmentDate: rec.judgmentDate,
      ratioPrinciple: ratioOverride || rec.summary,
      obiterNote: rec.obiterAndScopeNote,
      applicationToFacts,
      officialSourceUrl: rec.officialSourceUrl || '',
      officialSourceLabel: rec.officialSourceLabel || '',
      officialSourceVerified: Boolean(rec.officialSourceVerified),
      secondaryReferenceUrl: rec.secondaryReferenceUrl || '',
      secondaryReferenceLabel: rec.secondaryReferenceLabel || '',
      sourceUrl: rec.sourceUrl || '',
      verificationStatus: rec.verificationStatus,
      authorityType: rec.article141Status || authorityType
    };
  }

  private static detectCustodyAndPosture(text: string): ICaseUnderstanding['proceduralPosture'] {
    const t = text.toLowerCase();
    const isPastArrestConfirmed =
      /\b(?:was arrested|has been arrested|were arrested|arrested on|taken into custody|took into custody)\b/i.test(text);

    const futureOrNoArrest =
      !isPastArrestConfirmed &&
      /\b(?:apprehending arrest|apprehends arrest|fears arrest|threat of arrest|fear of arrest|seeks anticipatory bail|pre-arrest bail|not yet arrested|has not been arrested)\b/i.test(
        text
      );

    const isArrestedOrDetained =
      /\b(?:was arrested|has been arrested|were arrested|arrested|taken into custody|took into custody|in custody|police custody|judicial custody|remanded|remand order|for remand|detained|lockup|produced before magistrate|beyond 24 hours|grounds of arrest were not|not informed of grounds of arrest)\b/i.test(
        text
      ) && !futureOrNoArrest;

    const isApprehending =
      /\b(?:apprehending arrest|apprehends arrest|fears arrest|threat of arrest|anticipatory bail|section 438|section 482 bnss|pre-arrest bail)\b/i.test(
        text
      );

    const isOutOnBail = /\b(?:released on bail|granted bail|interim bail|bail bond furnished)\b/i.test(text);
    const isQuashingOnly = /\b(?:quash|quashing|482 crpc|528 bnss)\b/i.test(text) && !isArrestedOrDetained && !isApprehending;
    const isCivilSpecial = !/\b(?:arrest|fir|police|bail|remand|custody|accused|482|528|cheating)\b/i.test(t);

    if (isCivilSpecial) {
      return {
        detectedPosture: 'Civil / Constitutional / Special Statutory Proceeding (Non-Custodial)',
        custodyStatus: 'civil_or_non_custodial',
        availableRemedies: [
          {
            remedy: 'Writ Jurisdiction / Constitutional Relief or Statutory Civil Suit / Arbitration Application',
            statutoryBasis: 'Articles 226 / 32 of Constitution OR governing civil/special Act (e.g. CPC Order 39, Arbitration Act Ss. 8/34, NI Act S. 138 defence)',
            whenApplicable: 'Where infringement of fundamental rights, statutory illegality, or civil contractual dispute is raised without custodial detention.',
            cautionNote: 'Confirm limitation timelines and absence of equally efficacious alternative statutory remedy before invoking writ jurisdiction.'
          }
        ],
        remedyNote: 'No criminal custody posture detected in submitted facts.'
      };
    }

    if (isArrestedOrDetained) {
      return {
        detectedPosture: 'Post-Arrest / Custodial Challenge & Bail Posture (Person already arrested / grounds of arrest raised)',
        custodyStatus: 'in_custody_arrested',
        availableRemedies: [
          {
            remedy: 'Challenge to Arrest & Remand Legality / Application for Immediate Release',
            statutoryBasis: 'Article 22(1) Constitution of India read with Section 50 CrPC / Section 47 BNSS (Vihaan Kumar / Prabir Purkayastha principles)',
            whenApplicable: 'When arrest has ALREADY occurred and written/meaningful grounds of arrest were not communicated directly to the arrestee.',
            cautionNote: 'Anticipatory bail is NOT maintainable once an accused has already been arrested. Counsel must pursue release challenging invalid arrest/remand or regular bail.'
          },
          {
            remedy: 'Regular Bail Application',
            statutoryBasis: 'Section 437 / 439 CrPC (pre-01.07.2024) OR Section 480 / 483 BNSS (from 01.07.2024) read with Satender Kumar Antil non-compliance principles',
            whenApplicable: 'Seeking bail during police or judicial custody pending investigation or trial, particularly citing non-compliance with S. 41/41A CrPC or S. 35 BNSS.',
            cautionNote: 'Verify current custody location, remand order date, and whether chargesheet has been filed.'
          },
          {
            remedy: 'Writ Petition (Article 226 / Habeas Corpus) before High Court',
            statutoryBasis: 'Article 226 Constitution of India',
            whenApplicable: 'Where detention is argued to be illegal or void ab initio due to non-compliance with mandatory constitutional safeguards under Articles 21 and 22.',
            cautionNote: 'Ordinarily High Courts examine whether alternative remedy before Magistrate/Sessions Court was exhausted unless patent constitutional illegality is shown.'
          }
        ],
        remedyNote:
          'Because the dispute states or implies an arrest has already taken place, pre-arrest (anticipatory) bail is legally inapplicable once arrested. Available tracks center on regular bail, challenging the remand/arrest validity under Article 22(1), or seeking writ release.'
      };
    }

    if (isApprehending) {
      return {
        detectedPosture: 'Pre-Arrest Posture (Apprehension of Arrest)',
        custodyStatus: 'apprehending_arrest',
        availableRemedies: [
          {
            remedy: 'Anticipatory Bail (Pre-Arrest Protection)',
            statutoryBasis: 'Section 438 CrPC (pre-01.07.2024 FIR) OR Section 482 BNSS (from 01.07.2024)',
            whenApplicable: 'Strictly BEFORE arrest occurs, where applicant demonstrates reasonable apprehension of arrest in a non-bailable offence.',
            cautionNote: 'Anticipatory bail becomes infructuous upon arrest. Also verify statutory bars under special Acts if invoked.'
          },
          {
            remedy: 'Notice Compliance & Joining Investigation',
            statutoryBasis: 'Section 41A CrPC / Section 35(3) BNSS',
            whenApplicable: 'Where offence carries imprisonment up to 7 years and no coercive arrest necessity is recorded.',
            cautionNote: 'Verify FIR offence sections and statutory maximum sentence.'
          }
        ],
        remedyNote: 'Pre-arrest apprehension indicated; anticipatory bail and notice protection must be verified against actual FIR sections.'
      };
    }

    if (isOutOnBail) {
      return {
        detectedPosture: 'Post-Bail Investigation / Trial Stage',
        custodyStatus: 'released_on_bail',
        availableRemedies: [
          {
            remedy: 'Petition for Quashing of FIR / Proceedings',
            statutoryBasis: 'Section 482 CrPC / Section 528 BNSS read with Article 226 Constitution',
            whenApplicable: 'If allegations fail to disclose any prima facie criminal offence or convert a purely civil transaction into criminal prosecution.',
            cautionNote: 'Does not succeed where disputed factual issues require trial evidence.'
          }
        ],
        remedyNote: 'Applicant appears released on bail; custodial challenge is secondary to quashing or discharge.'
      };
    }

    if (isQuashingOnly) {
      return {
        detectedPosture: 'Threshold Quashing / Non-Custodial Criminal Challenge',
        custodyStatus: 'unclear',
        availableRemedies: [
          {
            remedy: 'Quashing Petition (Threshold Challenge)',
            statutoryBasis: 'Section 482 CrPC (legacy) / Section 528 BNSS (new) / Article 226 Constitution',
            whenApplicable: 'When seeking quashing of FIR/chargesheet on Bhajan Lal parameters.',
            cautionNote: 'Confirm whether applicant is on interim protection, facing arrest apprehension, or already in custody.'
          }
        ],
        remedyNote: 'Custody status is not stated in submitted text; confirm whether interim protection or bail is simultaneously needed.'
      };
    }

    return {
      detectedPosture: 'Custody Status Unspecified — Requires Factual Confirmation',
      custodyStatus: 'unclear',
      availableRemedies: [
        {
          remedy: 'Conditional Track A (If Not Yet Arrested): Anticipatory Bail & Notice Enforcement',
          statutoryBasis: 'Section 438 CrPC / Section 482 BNSS; Section 41A CrPC / Section 35 BNSS',
          whenApplicable: 'Applies ONLY if the person has not been taken into custody yet.',
          cautionNote: 'Do not file anticipatory bail if arrest has already been executed.'
        },
        {
          remedy: 'Conditional Track B (If Already Arrested / In Custody): Challenge Remand Legality or Regular Bail',
          statutoryBasis: 'Article 22(1) Constitution; Section 50/437/439 CrPC OR Section 47/480/483 BNSS',
          whenApplicable: 'Applies if the person has already been arrested or remanded.',
          cautionNote: 'Obtain Arrest Memo, Written Grounds of Arrest (if any), and Remand Order immediately.'
        }
      ],
      remedyNote:
        'Custody status cannot be confirmed conclusively from submitted text. Appropriate remedy differs fundamentally depending on whether arrest has already occurred.'
    };
  }

  /**
   * Discovers originating document page without guessing.
   * If a sentence matches multiple pages or cannot be matched confidently,
   * attribution is marked as unresolved rather than guessing.
   */
  public static attributeSentenceToPage(
    sentence: string,
    pages?: Array<{
      pageNumber: number;
      text: string;
      extractionMethod?: 'native' | 'ocr' | string;
      confidence?: number | null;
      warnings?: string[];
    }>
  ): {
    attributionStatus: 'verified' | 'unresolved' | 'unavailable';
    pageNumber?: number;
    extractionMethod: 'native' | 'ocr' | 'unresolved';
    pageConfidence?: number | null;
    matchedPageCount: number;
  } {
    if (!pages || !Array.isArray(pages) || pages.length === 0) {
      return {
        attributionStatus: 'unavailable',
        extractionMethod: 'unresolved',
        matchedPageCount: 0
      };
    }

    const clean = (s: string) =>
      s
        .toLowerCase()
        .replace(/\[\?[^?]+\?\]/g, (m) => m.replace(/\[\?|\?\]/g, ''))
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

    const cleanSentence = clean(sentence);
    if (cleanSentence.length < 8) {
      return {
        attributionStatus: 'unresolved',
        extractionMethod: 'unresolved',
        matchedPageCount: 0
      };
    }

    // Significant content tokens (words >= 4 chars or statutory numbers)
    const tokens = cleanSentence
      .split(' ')
      .filter(w => w.length >= 4 || /^\d+$/.test(w));

    const matchedPages: Array<{
      pageNumber: number;
      extractionMethod: 'native' | 'ocr' | 'unresolved';
      confidence: number | null;
    }> = [];

    for (const page of pages) {
      if (!page || !page.text) continue;
      const cleanPg = clean(page.text);

      let isMatch = false;

      // 1. Direct substring match
      if (cleanPg.includes(cleanSentence)) {
        isMatch = true;
      } else if (tokens.length >= 3) {
        // 2. High token density overlap (>= 75% of content tokens present on this page)
        let tokenHits = 0;
        for (const tok of tokens) {
          if (cleanPg.includes(tok)) tokenHits++;
        }
        if (tokenHits / tokens.length >= 0.75) {
          isMatch = true;
        }
      }

      if (isMatch) {
        const method = (page.extractionMethod === 'ocr' || page.extractionMethod === 'native')
          ? page.extractionMethod
          : 'native';
        matchedPages.push({
          pageNumber: page.pageNumber,
          extractionMethod: method,
          confidence: page.confidence !== undefined ? page.confidence : null
        });
      }
    }

    if (matchedPages.length === 1) {
      const match = matchedPages[0];
      return {
        attributionStatus: 'verified',
        pageNumber: match.pageNumber,
        extractionMethod: match.extractionMethod,
        pageConfidence: match.confidence,
        matchedPageCount: 1
      };
    }

    // Multiple pages matched or 0 pages matched: mark unresolved rather than guessing
    return {
      attributionStatus: 'unresolved',
      extractionMethod: 'unresolved',
      matchedPageCount: matchedPages.length
    };
  }

  /**
   * Extracts uncertain OCR tokens delimited by [?word?]
   */
  public static extractUncertainTokens(text: string): string[] {
    if (!text) return [];
    const matches = text.match(/\[\?([^?]+)\?\]/g);
    if (!matches) return [];
    return Array.from(new Set(matches.map(m => m.replace(/^\[\?|\?\]$/g, '').trim()).filter(Boolean)));
  }

  /**
   * Performs disciplined factual decomposition without inventing parties, dates, or legal conclusions.
   */
  public static analyzeCaseFacts(
    text: string,
    category: string,
    forum: string,
    lawAssessment: ApplicableLawAssessment,
    documentMetadata?: any
  ): ICaseUnderstanding {
    const textLower = text.toLowerCase();
    const parties = this.extractPartiesStrictly(text);
    const proceduralPosture = this.detectCustodyAndPosture(text);

    const rawSentences = text
      .split(/(?<=[.!?])\s+|\n+/)
      .map(s => s.trim())
      .filter(s => s.length > 10);

    const materialFacts: string[] = [];
    const chronology: IChronologyEvent[] = [];
    const attributedFacts: IAttributedFact[] = [];
    const userProvidedFacts: string[] = [];
    const partyAllegations: string[] = [];
    const reasonableInferences: string[] = [];
    const missingInformation: string[] = [...lawAssessment.missingDates];
    const factsRequiringVerification: string[] = [];
    const disputedActions: string[] = [];
    const allegedViolations: string[] = [];
    const proceduralQuestions: string[] = [];
    const evidenceAudit: IEvidenceAuditItem[] = [];

    const allegationMarkers =
      /\b(?:allege|alleged|allegedly|claim|claimed|contend|contends|failure|failed|without|illegal|unlawful|arbitrary|frivolous|malicious|false|denied|refused|violat)\b/i;

    rawSentences.forEach((sentence, idx) => {
      materialFacts.push(sentence);

      const isAllegation = allegationMarkers.test(sentence);
      let classification: 'Party allegation' | 'User-provided fact' = 'User-provided fact';
      if (isAllegation) {
        classification = 'Party allegation';
        const cleanClause = sentence.charAt(0).toLowerCase() + sentence.slice(1);
        const neutralStatement = /^it is alleged|^petitioner|^the petitioner|^applicant|^accused|^complainant/i.test(sentence)
          ? sentence
          : `User narrative alleges that ${cleanClause}`;
        partyAllegations.push(neutralStatement);
      } else {
        userProvidedFacts.push(sentence);
      }

      // Fact-to-Page Attribution
      const attr = this.attributeSentenceToPage(sentence, documentMetadata?.pages);
      const uncertainTokens = this.extractUncertainTokens(sentence);

      attributedFacts.push({
        id: `fact-${idx + 1}`,
        statement: sentence,
        classification,
        pageNumber: attr.pageNumber,
        extractionMethod: attr.extractionMethod,
        pageConfidence: attr.pageConfidence,
        uncertainTokens,
        attributionStatus: attr.attributionStatus,
        sourceSnippet: sentence
      });

      // Check if sentence contains a date
      const matchedDate = lawAssessment.detectedDates.find(d => sentence.includes(d.rawDate));
      chronology.push({
        date: matchedDate ? matchedDate.rawDate : 'Date not specified in input',
        event: sentence,
        involvedParties: parties.petitioners[0] !== 'Not specified.'
          ? `${parties.petitioners[0]} / ${parties.respondents[0]}`
          : 'Not specified in sentence',
        sourceExcerpt: sentence,
        verificationStatus: isAllegation ? 'Party allegation' : 'User-provided fact',
        pageNumber: attr.pageNumber,
        extractionMethod: attr.extractionMethod,
        pageConfidence: attr.pageConfidence,
        attributionStatus: attr.attributionStatus
      });
    });

    // Factual Inferences & Disputed Issues (Neutrally framed!)
    if (lawAssessment.isCriminalOrQuasiCriminal) {
      if (/\b(?:cheat|cheating|420|318)\b/i.test(text)) {
        disputedActions.push('Criminal complaint/arrest involving alleged offence of cheating.');
        reasonableInferences.push(
          'Standard cheating offences (IPC Section 420 / BNS Section 318(4)) carry maximum imprisonment up to 7 years; if these are the sole invoked sections, statutory pre-arrest notice rules ordinarily apply unless aggravated provisions carrying >7 years punishment are also invoked.'
        );
        factsRequiringVerification.push('Exact penal sections invoked in the FIR (to verify whether maximum prescribed sentence exceeds 7 years).');
      }

      if (/\b(?:grounds of arrest|not informed|without informing|not communicated|written grounds)\b/i.test(text)) {
        disputedActions.push('Alleged non-communication or defective communication of grounds of arrest.');
        allegedViolations.push(
          'Asserted violation of Article 22(1) of the Constitution and statutory obligation under Section 50 CrPC / Section 47 BNSS (requires verification against Arrest Memo and Remand records).'
        );
        factsRequiringVerification.push('Whether any written Grounds of Arrest were served on the arrestee and acknowledged prior to Magisterial remand.');
      }

      if (/\b(?:notice|41a|section 35|without notice|prior notice)\b/i.test(text)) {
        disputedActions.push('Alleged arrest or threat of arrest without prior service of statutory notice of appearance.');
        allegedViolations.push(
          'Asserted non-compliance with pre-arrest notice safeguards under Section 41/41A CrPC or Section 35 BNSS (depending on FIR date).'
        );
        factsRequiringVerification.push('Whether Investigating Officer recorded written reasons of necessity for arrest or issued any notice under S. 41A CrPC / S. 35(3) BNSS.');
      }

      if (/\b(?:family|relative|friend|nominee|intimat|inform)\b/i.test(text)) {
        disputedActions.push('Alleged failure to notify family members or a nominated person regarding the fact and place of arrest.');
        allegedViolations.push(
          'Asserted non-compliance with Article 21/22 custodial safeguards (D.K. Basu directions) and Section 50A CrPC / Section 48 BNSS.'
        );
        factsRequiringVerification.push('General Diary (GD) entry, Arrest Memo witness signature, and intimation log showing whether a nominated person was notified.');
      }

      if (/\b(?:article 21|personal liberty|custody|remand)\b/i.test(text)) {
        allegedViolations.push('Asserted deprivation of personal liberty contrary to procedure established by law under Article 21.');
      }

      // Specific Evidence Audit Documents (Strictly "Document to obtain / verify")
      evidenceAudit.push(
        {
          documentName: 'First Information Report (FIR) Copy',
          purpose: 'Confirm exact penal sections (IPC vs BNS), maximum sentence bracket, FIR registration date, and complainant allegations.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Determines applicable procedural statute (CrPC vs BNSS) and <=7-year threshold.'
        },
        {
          documentName: 'Arrest Memo (Punchnama / Memo of Arrest)',
          purpose: 'Verify date/time/place of arrest, attesting witness signatures, and arresting officer identification.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Central to testing compliance with D.K. Basu & S. 41B CrPC / S. 36 BNSS.'
        },
        {
          documentName: 'Written Grounds of Arrest Record / Serving Endorsement',
          purpose: 'Verify whether specific grounds of arrest were served in writing directly to the arrestee prior to remand.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Determines applicability of Prabir Purkayastha, Vihaan Kumar, and Mihir Rajesh Shah relief.'
        },
        {
          documentName: 'Notice of Appearance (Section 41A CrPC / Section 35(3) BNSS)',
          purpose: 'Ascertain whether statutory notice was issued or whether reasons dispensing with notice were recorded.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Crucial for establishing Arnesh Kumar / Satender Kumar Antil procedural non-compliance.'
        },
        {
          documentName: 'Police Case Diary / Remand Application & Judicial Remand Order',
          purpose: 'Examine whether IO placed written arrest reasons before Magistrate and whether Magistrate recorded independent satisfaction.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Demonstrates compliance or mechanical authorization under S. 167 CrPC / S. 187 BNSS.'
        },
        {
          documentName: 'Family / Friend Intimation Record & Station General Diary',
          purpose: 'Check whether nominated relative/friend was promptly notified of arrest and detention location.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Verifies Section 50A CrPC / Section 48 BNSS compliance.'
        },
        {
          documentName: 'Medico-Legal Examination Report (MLC)',
          purpose: 'Verify custodial medical examination at the time of arrest and compliance with custodial health safeguards.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Relevant to custodial integrity under D.K. Basu guidelines & S. 53 BNSS / S. 54 CrPC.'
        },
        {
          documentName: 'Prior Bail Applications & Orders (Magistrate / Sessions / High Court)',
          purpose: 'Establish prior procedural history and grounds considered/rejected by lower courts.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Essential before approaching superior courts.'
        }
      );

      if (/\b(?:cheat|420|318|commercial|business|contract)\b/i.test(text)) {
        evidenceAudit.push({
          documentName: 'Underlying Commercial Agreements, Invoices & Correspondence',
          purpose: 'Determine whether the core dispute is purely civil/contractual rather than dishonest criminal cheating at inception.',
          status: 'Document to obtain / verify',
          relevanceNote: 'Relevant both to defence on merits and threshold quashing (Bhajan Lal).'
        });
      }
    } else {
      // Non-criminal document audit
      if (/\b(?:privacy|surveillance|interception)\b/i.test(text)) {
        disputedActions.push('Asserted state surveillance or personal data/telecommunication interception.');
        allegedViolations.push('Asserted infringement of informational privacy under Article 21.');
        evidenceAudit.push(
          {
            documentName: 'Authorizing Interception / Executive Order (if any)',
            purpose: 'Verify whether valid statutory authority (e.g. Telegraph Act / IT Act S. 69) and oversight review existed.',
            status: 'Document to obtain / verify',
            relevanceNote: 'Essential for testing Legality & Proportionality under Puttaswamy.'
          }
        );
      }

      if (/\b(?:cheque|138|139|dishonour)\b/i.test(text)) {
        disputedActions.push('Presentation and dishonour of negotiable instrument; disputed underlying liability.');
        allegedViolations.push('Contest regarding statutory presumption under Section 139 NI Act.');
        evidenceAudit.push(
          {
            documentName: 'Dishonoured Cheque & Bank Return Memo',
            purpose: 'Verify exact date of dishonour and stated bank reason.',
            status: 'Document to obtain / verify',
            relevanceNote: 'Triggers 30-day statutory demand notice window under S. 138(b).'
          },
          {
            documentName: 'Section 138(b) Demand Notice & Postal Tracking Proof',
            purpose: 'Verify 30-day issuance and 15-day payment window compliance.',
            status: 'Document to obtain / verify',
            relevanceNote: 'Mandatory statutory cause-of-action condition.'
          },
          {
            documentName: 'Books of Account, Bank Statements & Loan/Contract Records',
            purpose: 'Rebut or establish existence of a legally enforceable debt on presentation date.',
            status: 'Document to obtain / verify',
            relevanceNote: 'Required under Rangappa v. Sri Mohan preponderance test.'
          }
        );
      }

      if (/\b(?:arbitrat|section 8|section 34)\b/i.test(text)) {
        evidenceAudit.push({
          documentName: 'Executed Contract Containing Arbitration Clause & Impugned Award (if any)',
          purpose: 'Verify scope of arbitration agreement and 3-month limitation period under S. 34(3).',
          status: 'Document to obtain / verify',
          relevanceNote: 'Essential for S. 8 referral or S. 34 challenge.'
        });
      }
    }

    // Standard Missing Information checks (no duplicates)
    if (parties.petitioners[0] === 'Not specified.' || parties.respondents[0] === 'Not specified.') {
      missingInformation.push('Full names and formal designations of Petitioners/Accused and Respondents/Complainant.');
    }
    if (lawAssessment.isCriminalOrQuasiCriminal && proceduralPosture.custodyStatus === 'unclear') {
      missingInformation.push('Current custody posture: whether person is already arrested/remanded or apprehending arrest.');
    }
    if (lawAssessment.isCriminalOrQuasiCriminal && !/\b(?:magistrate|sessions|remand|police station)\b/i.test(text)) {
      missingInformation.push('Jurisdictional Police Station, Remand Court details, and whether 24-hour Magistrate production occurred.');
    }

    proceduralQuestions.push(`Jurisdiction and maintainability before ${forum} given current procedural stage.`);
    if (lawAssessment.isCriminalOrQuasiCriminal) {
      proceduralQuestions.push('Whether criminal proceedings preceded or commenced on/after 1 July 2024 for CrPC vs. BNSS applicability.');
    }

    return {
      parties,
      materialFacts,
      chronology,
      attributedFacts,
      factClassification: {
        userProvidedFacts,
        partyAllegations,
        reasonableInferences,
        missingInformation,
        factsRequiringVerification
      },
      disputedActions: disputedActions.length > 0 ? disputedActions : ['Disputed legal action described in submitted statement.'],
      allegedViolations: allegedViolations.length > 0 ? allegedViolations : ['Requires mapping against identified questions of law.'],
      missingInformation,
      evidenceAudit,
      proceduralPosture,
      proceduralQuestions
    };
  }

  /**
   * Builds material questions of law tailored cleanly to factual triggers (NO arbitrary heuristic percentages!).
   */
  public static buildQuestionsOfLaw(
    facts: string,
    lawAssessment: ApplicableLawAssessment,
    understanding: ICaseUnderstanding
  ) {
    const t = facts.toLowerCase();
    const questions: Array<{
      issue: string;
      relevantFacts: string;
      statutoryProvision: string;
      supportingAuthorities: string[];
      whyIssueMatters: string;
      informationStillRequired: string;
      description: string;
    }> = [];

    if (lawAssessment.isCriminalOrQuasiCriminal) {
      const isPost = lawAssessment.regimeStatus === 'post_july_2024_new_codes';
      const noticeProv = isPost
        ? 'Section 35 BNSS, 2023'
        : lawAssessment.regimeStatus === 'pre_july_2024_legacy_codes'
          ? 'Sections 41 & 41A CrPC, 1973'
          : 'Section 35 BNSS, 2023 (from 01.07.2024) OR Sections 41 & 41A CrPC, 1973 (date-dependent)';

      if (/\b(?:arrest|grounds of arrest|not communicated|not informed|written grounds|article 22)\b/i.test(t)) {
        questions.push({
          issue: 'Whether non-communication or defective communication of written grounds of arrest violates Article 22(1) and vitiates arrest and subsequent remand',
          relevantFacts: understanding.factClassification.partyAllegations.find(a => /ground|communicat|inform/i.test(a))
            || 'Petitioner alleges that grounds of arrest were not properly communicated.',
          statutoryProvision: isPost
            ? 'Article 22(1), Constitution of India; Section 47, BNSS, 2023'
            : 'Article 22(1), Constitution of India; Section 50 CrPC / Section 47 BNSS (date-dependent)',
          supportingAuthorities: [
            'Prabir Purkayastha v. State (NCT of Delhi) [(2024) 8 SCC 254]',
            'Vihaan Kumar v. State of Haryana [(2025) 5 SCC 799 / 2025 INSC 162]',
            'Mihir Rajesh Shah v. State of Maharashtra [2025 INSC 1288]',
            'Pankaj Bansal v. Union of India [(2024) 7 SCC 576] (PMLA origin)'
          ],
          whyIssueMatters: 'Under recent Supreme Court jurisprudence, violation of Article 22(1) renders the initial arrest unconstitutional and subsequent remand illegal, entitling the detainee to release regardless of subsequent chargesheet filing.',
          informationStillRequired: 'Exact date of arrest (to determine prospective guidelines scope), copy of Arrest Memo, and whether any written grounds were furnished before remand.',
          description: 'Assesses compliance with constitutional mandate under Article 22(1) to communicate specific factual grounds of arrest meaningfully to the arrestee.'
        });
      }

      if (/\b(?:arrest|notice|41a|section 35|cheat|420|318|necessity)\b/i.test(t)) {
        questions.push({
          issue: 'Whether statutory necessity for arrest and mandatory Notice of Appearance requirements were satisfied for an offence carrying up to 7 years imprisonment',
          relevantFacts: 'Dispute involves arrest/notice questions in connection with alleged offences (verify punishment bracket in FIR, e.g., cheating IPC 420 / BNS 318 carries up to 7 years).',
          statutoryProvision: `${noticeProv}; Article 21, Constitution of India`,
          supportingAuthorities: [
            'Arnesh Kumar v. State of Bihar [(2014) 8 SCC 273]',
            'Satender Kumar Antil v. CBI [(2022) 10 SCC 51]'
          ],
          whyIssueMatters: 'Supreme Court directions prohibit mechanical arrest without recorded necessity when punishment is up to 7 years; non-compliance directly entitles the accused to bail scrutiny and departmental/contempt inquiry.',
          informationStillRequired: 'FIR sections to verify <= 7 year sentence ceiling; whether Section 41A CrPC / Section 35(3) BNSS notice was served; written IO checklist.',
          description: 'Examines whether police recorded statutory reasons justifying necessity of arrest rather than issuing notice of appearance.'
        });
      }

      if (/\b(?:family|relative|friend|nominee|intimat|inform|d\.k\. basu|dk basu)\b/i.test(t)) {
        questions.push({
          issue: 'Whether failure to promptly notify family members or a nominated friend violates statutory arrest procedures and Article 21/22 safeguards',
          relevantFacts: understanding.factClassification.partyAllegations.find(a => /family|relative|friend|inform/i.test(a))
            || 'Narrative raises failure to notify family/nominated person of arrest.',
          statutoryProvision: isPost
            ? 'Section 48 & Section 36 BNSS, 2023; Articles 21 & 22 Constitution'
            : 'Section 50A & 41B CrPC OR Section 48 & 36 BNSS; Articles 21 & 22 Constitution',
          supportingAuthorities: [
            'D.K. Basu v. State of West Bengal [(1997) 1 SCC 416]',
            'Vihaan Kumar v. State of Haryana [2025 INSC 162]'
          ],
          whyIssueMatters: 'Mandatory relative/friend intimation prevents incommunicado detention. Furthermore, under Vihaan Kumar, informing family does NOT substitute for informing the arrestee of grounds under Article 22(1).',
          informationStillRequired: 'Station General Diary entry, Arrest Memo witness signature, and mobile call/intimation log.',
          description: 'Evaluates adherence to custodial transparency and nominated person notification duties.'
        });
      }

      if (lawAssessment.regimeStatus === 'uncertain_missing_dates' || lawAssessment.regimeStatus === 'transitional_mixed') {
        questions.push({
          issue: 'Which criminal statutory regime (IPC/CrPC vs. BNS/BNSS/BSA) governs the substantive offence and arrest/bail procedures',
          relevantFacts: 'Dates of alleged offence, FIR registration, and arrest are omitted or straddle the 1 July 2024 statutory transition.',
          statutoryProvision: 'Section 531 BNSS, 2023 & Section 358 BNS, 2023 (Repeal and Savings Clauses)',
          supportingAuthorities: ['Statutory transitional provisions under BNSS S. 531 & BNS S. 358'],
          whyIssueMatters: 'Applying the wrong statutory code (e.g., citing CrPC 41A in a post-July-2024 FIR instead of BNSS 35, or invoking higher BNS punishments retroactively in violation of Art. 20(1)) risks procedural invalidity.',
          informationStillRequired: 'Exact date of offence and date of FIR registration.',
          description: 'Resolves date-dependent transitional applicability between 19th/20th-century criminal codes and the 2023 Sanhitas.'
        });
      }

      if (/\b(?:quash|482|528|civil|abuse of process)\b/i.test(t)) {
        questions.push({
          issue: 'Whether the FIR/complaint discloses prima facie criminal ingredients or impermissibly converts a civil/contractual dispute into criminal prosecution',
          relevantFacts: 'Submission asserts civil commercial dispute or absence of initial fraudulent mens rea.',
          statutoryProvision: 'Section 482 CrPC / Section 528 BNSS; Article 226 Constitution',
          supportingAuthorities: ['State of Haryana v. Bhajan Lal [1992 Supp (1) SCC 335]'],
          whyIssueMatters: 'Determines maintainability of threshold quashing before the High Court without forcing full criminal trial.',
          informationStillRequired: 'Complete text of FIR, contract documents, and stage of chargesheet.',
          description: 'Tests allegations at face value under Bhajan Lal Category 1 and 7 thresholds.'
        });
      }
    }

    if (/\b(?:privacy|surveillance|biometric|interception)\b/i.test(t)) {
      questions.push({
        issue: 'Whether non-consensual surveillance or data harvesting satisfies Article 21 three-fold legality, legitimate aim, and proportionality scrutiny',
        relevantFacts: 'Asserted state surveillance or telecommunication/biometric interception without prior judicial authorization.',
        statutoryProvision: 'Article 21 & Article 14, Constitution of India; Section 69 IT Act / Telegraph Act rules',
        supportingAuthorities: ['Justice K.S. Puttaswamy (Retd.) v. Union of India [(2017) 10 SCC 1]'],
        whyIssueMatters: 'Every State intrusion into privacy fails constitutionally unless backed by enacted law, legitimate aim, and least-intrusive proportionality.',
        informationStillRequired: 'Written interception order, Review Committee confirmation, and statutory basis claimed by State.',
        description: 'Applies the 9-judge Constitution Bench proportionality framework.'
      });
    }

    if (/\b(?:cheque|138|139|negotiable)\b/i.test(t)) {
      questions.push({
        issue: 'Whether the drawer has raised a probable defence on preponderance of probabilities sufficient to rebut Section 139 NI Act presumption',
        relevantFacts: 'Dispute regarding dishonoured/security cheque and existence of legally enforceable debt.',
        statutoryProvision: 'Sections 138, 139 & 118, Negotiable Instruments Act, 1881',
        supportingAuthorities: [
          'Rangappa v. Sri Mohan [(2010) 11 SCC 441]',
          'Bir Singh v. Mukesh Kumar [(2019) 4 SCC 197]'
        ],
        whyIssueMatters: 'Once signature is admitted, Section 139 presumes an enforceable debt unless the drawer produces probable evidence shifting the burden back.',
        informationStillRequired: 'Date of cheque presentation, bank return memo, Section 138(b) statutory demand notice dates, and ledger/account statements.',
        description: 'Assesses evidentiary threshold for rebutting statutory NI Act presumptions.'
      });
    }

    if (/\b(?:arbitrat|section 8|section 11|section 34)\b/i.test(t)) {
      questions.push({
        issue: 'Whether the dispute is subject to mandatory arbitral reference under Section 8 or narrow judicial review limits under Section 34',
        relevantFacts: 'Presence of commercial arbitration clause or challenge to arbitral award.',
        statutoryProvision: 'Sections 8, 11 & 34, Arbitration and Conciliation Act, 1996',
        supportingAuthorities: [
          'Vidya Drolia v. Durga Trading Corporation [(2021) 2 SCC 1]',
          'Associate Builders v. DDA [(2015) 3 SCC 49]'
        ],
        whyIssueMatters: 'Civil courts must refer arbitrable disputes under Section 8 and refrain from re-appreciating arbitral evidence under Section 34.',
        informationStillRequired: 'Copy of signed agreement containing arbitration clause and date of award receipt (if S. 34 challenge).',
        description: 'Assesses subject-matter arbitrability and judicial non-interference.'
      });
    }

    if (/\b(?:trademark|infringement|passing off|66a|speech|talaq)\b/i.test(t)) {
      questions.push({
        issue: 'Whether statutory protections under IT Act / Trade Marks Act / Constitutional Part III override impugned action',
        relevantFacts: 'Dispute engages statutory IP infringement or constitutional speech protections.',
        statutoryProvision: 'Trade Marks Act, 1999 S. 29 / IT Act S. 66A & 79 / Article 19(1)(a)',
        supportingAuthorities: [
          'Tata Sons Pvt. Ltd. v. Hakunamatata Tata Founders [2022 SCC OnLine Del 2968]',
          'Shreya Singhal v. Union of India [(2015) 5 SCC 1]'
        ],
        whyIssueMatters: 'Governs maintainability of injunction or unconstitutionality challenge.',
        informationStillRequired: 'Registered trademark certificates or copy of impugned statutory notice/FIR.',
        description: 'Identifies specialized statutory protections.'
      });
    }

    if (questions.length === 0) {
      questions.push({
        issue: 'Whether the impugned administrative or civil action violates procedural fairness, statutory authority, or Article 14 non-arbitrariness',
        relevantFacts: understanding.materialFacts[0] || 'Submitted dispute statement.',
        statutoryProvision: 'Articles 14 & 21, Constitution of India; governing sectoral enactment',
        supportingAuthorities: ['Maneka Gandhi v. Union of India [(1978) 1 SCC 248]'],
        whyIssueMatters: 'Public and quasi-judicial decisions without fair hearing or recorded reasons are vulnerable to judicial review.',
        informationStillRequired: 'Copies of impugned order, prior show-cause notices, and statutory appeal provisions.',
        description: 'Evaluates threshold procedural fairness and jurisdictional competence.'
      });
    }

    return questions;
  }

  /**
   * Generates comprehensive, fact-specific legal arguments with all 13 required sections and non-fabricated counterarguments.
   */
  public static generateLegalArguments(
    facts: string,
    category: string,
    forum: string,
    precedents: IMatchedPrecedent[],
    understanding: ICaseUnderstanding,
    lawAssessment: ApplicableLawAssessment
  ): ILegalArgument[] {
    const textLower = facts.toLowerCase();
    const argumentsList: ILegalArgument[] = [];
    const draftDisclaimer = 'Draft legal research submissions — subject to verification and review by qualified counsel.';
    const isPost = lawAssessment.regimeStatus === 'post_july_2024_new_codes';
    const isPre = lawAssessment.regimeStatus === 'pre_july_2024_legacy_codes';
    const custodyStatus = understanding.proceduralPosture.custodyStatus;

    // 1. CRIMINAL GROUND: Non-Communication of Written Grounds of Arrest (Article 22(1))
    if (
      lawAssessment.isCriminalOrQuasiCriminal &&
      /\b(?:grounds of arrest|not communicated|not informed|communicat|written grounds|article 22)\b/i.test(textLower)
    ) {
      const prabir = this.toSupportingPrecedent(
        'SC-2024-025',
        'Supports the proposition that failure to furnish specific, factual grounds of arrest in writing vitiates both the initial arrest and any subsequent judicial remand.',
        'Supreme Court of India — Division Bench (Article 141 authority on Art. 22(1) distinction between reasons and grounds)'
      );
      const vihaan = this.toSupportingPrecedent(
        'SC-2025-026',
        'Directly on point for ordinary criminal/cheating arrests: held that notifying relatives or recording notes in case diaries cannot substitute for direct, meaningful communication of grounds to the arrestee.',
        'Supreme Court of India — Division Bench (Ordinary IPC/BNS offences Article 22(1) binding mandate)'
      );
      const mihir = this.toSupportingPrecedent(
        'SC-2025-027',
        'Reinforces that under Section 47 BNSS / Section 50 CrPC read with Article 22(1), written grounds of arrest must be furnished (prospectively at least 2 hours before remand production).',
        'Supreme Court of India — Chief Justice Bench (2025 INSC 1288)'
      );

      const statutoryList = isPost
        ? ['Article 22(1), Constitution of India', 'Article 21, Constitution of India', 'Section 47, BNSS, 2023']
        : isPre
          ? ['Article 22(1), Constitution of India', 'Article 21, Constitution of India', 'Section 50, CrPC, 1973']
          : [
              'Article 22(1), Constitution of India',
              'Article 21, Constitution of India',
              'Section 47 BNSS, 2023 (from 01.07.2024) OR Section 50 CrPC, 1973 (date verification required)'
            ];

      const relevantAllegation =
        understanding.factClassification.partyAllegations.find(a => /ground|communicat|inform/i.test(a)) ||
        'It is alleged that the grounds of arrest were not properly communicated to the arrested person.';

      argumentsList.push({
        id: 'arg-art22-grounds',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Asserted Violation of Article 22(1) Due to Failure to Communicate Specific Grounds of Arrest',
        legalQuestion: 'Whether failure to communicate specific factual grounds of arrest directly and meaningfully to the arrestee renders the arrest and subsequent Magisterial remand unlawful under Article 22(1).',
        legalProposition:
          'Under Article 22(1) of the Constitution read with Section 50 CrPC / Section 47 BNSS, an arrested person must be meaningfully informed of the specific grounds necessitating their arrest—not merely generic statutory boilerplate—so they can consult counsel and oppose remand.',
        relevantFacts: relevantAllegation,
        applicableProvisions: statutoryList,
        supportingPrecedents: [vihaan, prabir, mihir],
        ratioDecidendi:
          'Supreme Court precedent draws a sharp distinction between generalized "reasons to arrest" and case-specific "grounds of arrest" (Prabir Purkayastha). Direct communication to the arrestee is non-negotiable across ordinary offences, and informing a relative does not cure non-communication to the arrestee (Vihaan Kumar).',
        judicialReasoning:
          'Article 22(1) safeguards personal liberty by enabling an arrestee to understand the exact factual accusation immediately upon detention and mount an informed opposition to police/judicial custody remand before the Magistrate.',
        applicationToFacts:
          `If documentary verification confirms that the arresting agency omitted written/meaningful communication of factual grounds of arrest prior to remand production (and merely relied on an oral intimation or general FIR summary), the foundational arrest and subsequent remand order stand vulnerable to being declared illegal, entitling the detainee to release.`,
        factualDistinctions:
          'Pankaj Bansal (2023) originated under Section 19(1) PMLA; Prabir Purkayastha (May 2024) involved UAPA; however, Vihaan Kumar (Feb 2025) settled its application to ordinary cheating/IPC offences. Note that Mihir Rajesh Shah (Nov 2025) clarified the strict 2-hour pre-remand written timeline operates prospectively; thus verification of arrest date is essential.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Subject to verification of Arrest Memo & Remand Order dates):

1. THAT the Petitioner/Applicant respectfully challenges the validity of the arrest and consequential remand on the constitutional ground of non-compliance with Article 22(1) of the Constitution of India read with ${isPost ? 'Section 47 of the Bharatiya Nagarik Suraksha Sanhita, 2023' : isPre ? 'Section 50 of the Code of Criminal Procedure, 1973' : 'Section 50 CrPC / Section 47 BNSS (applicable statute subject to FIR/arrest date verification)'}.
2. THAT as alleged, the specific factual grounds necessitating arrest were not communicated to the arrestee in a meaningful, intelligible manner prior to Magisterial production. As authoritatively held by the Hon'ble Supreme Court in Prabir Purkayastha v. State (NCT of Delhi) [(2024) 8 SCC 254] and reinforced in ordinary criminal prosecutions in Vihaan Kumar v. State of Haryana [(2025) 5 SCC 799], there is a fundamental constitutional distinction between generic formal reasons to arrest and case-specific grounds of arrest.
3. THAT even assuming any intimation was conveyed to a family member or entered in internal police diaries, the Hon'ble Supreme Court in Vihaan Kumar squarely held that informing relatives under S. 50A CrPC / S. 48 BNSS cannot substitute for direct communication of grounds to the arrestee under Article 22(1).
4. THAT non-compliance with Article 22(1) vitiates the arrest ab initio and renders consequential remand orders unsustainable in law, warranting release subject to appropriate terms.`,
        draftDisclaimer,
        evidenceRequired: [
          'Certified copy of Arrest Memo showing whether grounds column was served/acknowledged by the arrestee.',
          'Remand Application and first Judicial Remand Order verifying whether Magistrate examined compliance with Article 22(1).',
          'Exact date and timestamp of arrest and Magistrate production (required to assess prospective rule timing).'
        ],
        weaknesses:
          'If the prosecution produces a contemporaneous Arrest Memo or Remand Application bearing the arrestee’s signed acknowledgment of written grounds (or demonstrates oral explanation in a pre-prospective arrest window where substantial compliance is proved), this ground may weaken or fail.',
        limitations:
          'Requires factual verification: mere allegation cannot establish non-communication without inspecting the Arrest Memo and Remand record.',
        counterarguments: [
          {
            opposingGround: 'Claim of Substantial Oral Intimation / Mention in FIR & Arrest Memo',
            opposingLegalBasis: 'State may contend that FIR contents were explained orally at arrest and standard Arrest Memo reasons sufficed, especially prior to strict written timelines.',
            factualBasis: 'Dependent on whether Arrest Memo contains accused’s endorsement or signature; document not yet verified.',
            vulnerabilityAssessment: 'Moderate to High — Courts examine whether arrestee actually received notice of concrete factual allegations.',
            rebuttalStrategy:
              'Rely on Prabir Purkayastha and Vihaan Kumar holding that routine printed reasons on an arrest memo ("to prevent tampering / for investigation") do not equate to case-specific factual grounds under Article 22(1), and mere oral assertions absent contemporaneous record do not discharge constitutional burden.',
            requiredEvidence: 'Original/certified copy of Arrest Memo, Case Diary abstract produced at remand, and remand counsel objections.'
          },
          {
            opposingGround: 'Objection Based on Subsequent Filing of Remand Order / Chargesheet',
            opposingLegalBasis: 'Contention that judicial remand orders or filing of chargesheet cure prior procedural defects at arrest.',
            factualBasis: 'Applicable if judicial remand or chargesheet has subsequently followed arrest.',
            vulnerabilityAssessment: 'Low against settled SC precedent — Expressly rejected by Supreme Court in Prabir Purkayastha and Vihaan Kumar.',
            rebuttalStrategy:
              'Cite paragraph ratio in Prabir Purkayastha and Vihaan Kumar settling that once initial arrest violates Article 22(1), subsequent remand orders and chargesheet filing cannot validate an unconstitutional detention.',
            requiredEvidence: 'First remand order showing absence of Article 22(1) compliance satisfaction recorded by the Magistrate.'
          }
        ]
      });
    }

    // 2. CRIMINAL GROUND: Necessity of Arrest & Statutory Notice (S. 41/41A CrPC vs S. 35 BNSS)
    if (
      lawAssessment.isCriminalOrQuasiCriminal &&
      /\b(?:arrest|notice|41a|section 35|cheat|420|318|necessity)\b/i.test(textLower)
    ) {
      const arnesh = this.toSupportingPrecedent(
        'SC-2014-003',
        'Establishes that automatic arrest without recording statutory necessity or serving prior notice in offences punishable up to 7 years violates statutory limits on police power.',
        'Supreme Court of India — Division Bench (Directions expressly governing ALL offences punishable up to 7 years)'
      );
      const antil = this.toSupportingPrecedent(
        'SC-2022-023',
        'Mandates courts to verify Section 41/41A CrPC (and Section 35 BNSS) compliance while considering bail; non-compliance constitutes an independent ground for bail.',
        'Supreme Court of India — Division Bench ((2022) 10 SCC 51)'
      );

      const has498a = /\b(?:498a|498-a|85 bns|dowry)\b/i.test(textLower);
      const offenceDesc = /\b(?:cheat|420|318)\b/i.test(textLower)
        ? 'alleged offence of cheating (verify whether solely S. 420 IPC / S. 318 BNS carrying <= 7 years punishment)'
        : has498a
          ? 'alleged offence under Section 498A IPC / Section 85 BNS (<= 3 years imprisonment)'
          : 'alleged cognizable offence (sentence bracket <= 7 years requires FIR verification)';

      const procProvisions = isPost
        ? ['Section 35(1)(b) & 35(3), BNSS, 2023', 'Article 21, Constitution of India']
        : isPre
          ? ['Section 41(1)(b) & 41A, CrPC, 1973', 'Article 21, Constitution of India']
          : ['Section 35 BNSS, 2023 (from 01.07.2024) OR Sections 41 & 41A CrPC, 1973 (date-dependent)', 'Article 21, Constitution of India'];

      const remedyClause =
        custodyStatus === 'in_custody_arrested'
          ? 'grant of Regular Bail / setting aside mechanical remand in accordance with Satender Kumar Antil v. CBI [(2022) 10 SCC 51]'
          : custodyStatus === 'apprehending_arrest'
            ? 'pre-arrest protection / Anticipatory Bail subject to judicial discretion'
            : 'grant of Regular Bail if currently detained (or Anticipatory Bail ONLY if arrest has not yet taken place)';

      argumentsList.push({
        id: 'arg-notice-necessity',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Alleged Non-Compliance with Pre-Arrest Necessity Criteria and Statutory Notice of Appearance Requirements',
        legalQuestion: `Whether arrest in respect of an ${offenceDesc} without prior notice of appearance or recorded statutory necessity breaches ${isPost ? 'Section 35 BNSS' : 'Section 41/41A CrPC'} and Satender Kumar Antil guidelines.`,
        legalProposition:
          'Power to arrest is distinct from justification to arrest. For offences punishable with imprisonment up to 7 years, arresting officers cannot effect automatic arrest without recording concrete satisfaction that arrest is necessary for one or more alternative statutory necessity purposes under Section 35(1)(b)(ii) BNSS / Section 41(1)(b)(ii) CrPC (preventing further offences, proper investigation, preventing evidence tampering, preventing witness intimidation/dissuasion, or securing court presence) and ordinarily issuing Notice of Appearance first.',
        relevantFacts: `Submitted dispute concerns ${offenceDesc} alongside questions regarding pre-arrest notice requirements.`,
        applicableProvisions: procProvisions,
        supportingPrecedents: [antil, arnesh],
        ratioDecidendi:
          'Even though Arnesh Kumar involved a matrimonial complaint, paragraph 11.7 explicitly applies its checklist to all offences punishable with imprisonment up to 7 years (including cheating under IPC 420 / BNS 318). Satender Kumar Antil further requires remand/bail courts to scrutinize compliance and treat non-compliance as a ground favouring bail.',
        judicialReasoning:
          'Depriving personal liberty prior to conviction is an extraordinary power restricted by legislative safeguards so criminal process does not become pre-trial punishment.',
        applicationToFacts:
          `If the FIR penal provisions carry a maximum sentence not exceeding 7 years and no valid written checklist justifying immediate custody was placed before the Magistrate, petitioner has strong statutory grounds seeking ${remedyClause}.`,
        factualDistinctions:
          'CRITICAL CHECK: If the FIR also invokes an offence carrying more than 7 years imprisonment (e.g., S. 467 IPC / S. 338 BNS forgery of valuable security — life/10 years), mandatory Arnesh Kumar notice protection is displaced by higher sentence ceiling. Additionally, applicable code (CrPC S. 41A vs. BNSS S. 35(3)) depends strictly on FIR/commencement dates.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Verify FIR offences & registration date before finalizing):

1. THAT without prejudice to the merits of the investigation, assuming the allegations in the FIR relate to offences punishable with imprisonment up to seven years, the investigating agency was statutorily bound by ${isPost ? 'Section 35(1)(b) and Section 35(3) of the BNSS, 2023' : isPre ? 'Section 41(1)(b)(ii) and Section 41A of the CrPC, 1973' : 'Section 41/41A CrPC OR Section 35 BNSS (subject to verification of FIR date)'} before curtailing the personal liberty of the Accused.
2. THAT as laid down by the Hon'ble Supreme Court in Arnesh Kumar v. State of Bihar [(2014) 8 SCC 273] (explicitly made applicable to ALL offences punishable up to seven years) and reiterated in Satender Kumar Antil v. CBI [(2022) 10 SCC 51], an investigating officer cannot effect routine or mechanical arrest without serving a Notice of Appearance and recording objective reasons demonstrating necessity under one or more of the alternative statutory sub-clauses.
3. THAT in the absence of recorded non-cooperation or evasive conduct following statutory notice, coercive custody violates Article 21 and directly supports ${remedyClause}.`,
        draftDisclaimer,
        evidenceRequired: [
          'FIR copy confirming exact penal sections and confirming sentence ceiling <= 7 years.',
          'Police notice log / Arrest Checklist furnished to Magistrate under CrPC S. 41(1)(b) or BNSS S. 35(1)(b).',
          'Proof of permanent residence, cooperation/availability, and documentary character of disputed transaction.'
        ],
        weaknesses:
          'Protection fails or diminishes substantially if the FIR includes non-Arnesh offences punishable above 7 years (such as S. 467 IPC / S. 338 BNS, or S. 409 IPC / S. 316(5) BNS criminal breach of trust by public servant/banker) or if IO records verified evasion/tampering risk.',
        limitations:
          'Sentence limit of the actual FIR sections and proof of whether notice was evaded remain unverified.',
        counterarguments: [
          {
            opposingGround: 'Applicability of Higher Punishment Offences (>7 Years) or Recorded Risk of Evidence Tampering',
            opposingLegalBasis: 'Prosecution may assert aggravated sections punishable above 7 years or cite necessity to prevent witness intimidation / digital evidence destruction.',
            factualBasis: 'Dependent on actual FIR sections and police case diary; not verifiable from brief prompt alone.',
            vulnerabilityAssessment: 'High if FIR contains >7-year sections; Moderate otherwise — Must inspect FIR text immediately.',
            rebuttalStrategy:
              'Check whether any >7-year section (e.g. forgery) is unsupported by the primary ingredients of the complaint, and demonstrate that all banking/documentary evidence in a commercial cheating case is already on electronic/bank record without risk of tampering.',
            requiredEvidence: 'Certified FIR copy, list of seized documents/devices, and bank account transaction trails.'
          }
        ]
      });
    }

    // 3. CRIMINAL GROUND: Family / Nominated Person Notification & Custodial Safeguards (D.K. Basu / Art. 21 & 22)
    if (
      lawAssessment.isCriminalOrQuasiCriminal &&
      /\b(?:family|relative|friend|nominee|intimat|inform|d\.k\. basu|dk basu)\b/i.test(textLower)
    ) {
      const dkbasu = this.toSupportingPrecedent(
        'SC-1996-012',
        'Mandates attested Arrest Memo, visible officer identification, medical examination, and prompt intimation of arrest and place of detention to a nominated relative or friend.',
        'Supreme Court of India — Division Bench (Authoritative guidelines under Articles 21 & 22)'
      );
      const vihaanRef = this.toSupportingPrecedent(
        'SC-2025-026',
        'Clarifies statutory separation between relative intimation (S. 50A CrPC / S. 48 BNSS) and direct grounds of arrest communication (S. 50 CrPC / S. 47 BNSS).',
        'Supreme Court of India — Division Bench (2025 INSC 162)'
      );

      argumentsList.push({
        id: 'arg-family-safeguards',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Asserted Breach of Mandatory Custodial Notification and Arrest Documentation Safeguards (Article 21 & 22)',
        legalQuestion: 'Whether failure to notify a nominated family member or friend forthwith of the fact and location of arrest violates statutory duties and D.K. Basu constitutional safeguards.',
        legalProposition:
          'Upon every arrest without warrant, police authorities owe a mandatory statutory and constitutional duty to give immediate information regarding the arrest and place of detention to any friend, relative, or person nominated by the arrestee and record that compliance in the Station Diary.',
        relevantFacts:
          understanding.factClassification.partyAllegations.find(a => /family|relative|friend|inform/i.test(a)) ||
          'It is alleged that family members were not promptly informed of the arrest.',
        applicableProvisions: isPost
          ? ['Section 48 & Section 36, BNSS, 2023', 'Article 21 & Article 22, Constitution of India']
          : isPre
            ? ['Section 50A & Section 41B, CrPC, 1973', 'Article 21 & Article 22, Constitution of India']
            : [
                'Section 48 BNSS, 2023 (from 01.07.2024) OR Section 50A CrPC, 1973',
                'Section 36 BNSS OR Section 41B CrPC',
                'Articles 21 & 22, Constitution of India'
              ],
        supportingPrecedents: [dkbasu, vihaanRef],
        ratioDecidendi:
          'In D.K. Basu v. State of West Bengal [(1997) 1 SCC 416], the Supreme Court framed 11 enforceable custodial directions to eliminate unacknowledged detentions and custodial abuse, subjecting non-compliant officers to departmental action and contempt.',
        judicialReasoning:
          'Prompt intimation to family or nominated friends guarantees external accountability and enables immediate legal representation as contemplated under Article 22(1).',
        applicationToFacts:
          'Failure to notify a relative/friend reinforces the pattern of procedural non-compliance at arrest, supporting relief when read together with non-communication of grounds under Article 22(1) or departmental accountability directions before the High Court/Magistrate.',
        factualDistinctions:
          'IMPORTANT PROCEDURAL NUANCE: While violation of Article 22(1) grounds of arrest can invalidate arrest/remand directly (Prabir Purkayastha / Vihaan Kumar), standalone delay in relative notification (absent Article 22(1) lapse or unlawful detention) primarily attracts bail consideration, Magisterial adverse remarks, or contempt/disciplinary proceedings under D.K. Basu rather than automatic quashing of FIR.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Subject to verification of Arrest Memo & Station Diary):

1. THAT in addition to non-communication of grounds of arrest, the arresting authorities are alleged to have breached the mandatory procedural duties codified under ${isPost ? 'Sections 36 and 48 of the BNSS, 2023' : isPre ? 'Sections 41B and 50A of the CrPC, 1973' : 'Sections 41B/50A CrPC or Sections 36/48 BNSS (verify FIR/arrest date)'} and the binding directions settled in D.K. Basu v. State of West Bengal [(1997) 1 SCC 416].
2. THAT under Direction (3) and (4) of D.K. Basu, an arrestee is entitled to have a friend, relative, or nominated person informed forthwith of the arrest and the exact place of detention, with an explicit entry recorded in the police station register.
3. THAT cumulative disregard of transparent arrest safeguards strengthens judicial scrutiny against continued detention and warrants appropriate protective and accountability directions.`,
        draftDisclaimer,
        evidenceRequired: [
          'Police Station General Diary (GD) / Arrest Register entries for the arrest date.',
          'Arrest Memo verifying whether relative/witness column contains genuine signature and contact timing.',
          'Police station CCTV footage preservation request (Paramvir Singh Saini principles).'
        ],
        weaknesses:
          'Standalone breach of relative notification (if grounds were properly served and Magistrate production occurred within 24 hours) generally aids bail or disciplinary remedies rather than terminating criminal investigation itself.',
        limitations:
          'Station GD entries and mobile call records have not been produced or examined yet.',
        counterarguments: [
          {
            opposingGround: 'Claim of Telephonic Intimation or Arrestee Refusal to Nominate',
            opposingLegalBasis: 'Police may assert arrestee declined to nominate anyone or was informed over phone, claiming substantial compliance.',
            factualBasis: 'Requires examination of Arrest Memo & GD entries.',
            vulnerabilityAssessment: 'Moderate — Courts verify objective written diary entries or CDR records rather than bare police affidavits.',
            rebuttalStrategy:
              'Demand production of station diary timestamp, call detail logs, and independent witness attestation on the Arrest Memo as required by S. 41B CrPC / S. 36 BNSS.',
            requiredEvidence: 'Police Station Arrest Register, GD copy, and CCTV preservation record.'
          }
        ]
      });
    }

    // 4. PRIVACY & PROPORTIONALITY GROUND
    if (/\b(?:privacy|surveillance|biometric|interception|telemetry|aadhaar)\b/i.test(textLower)) {
      const puttaswamy = this.toSupportingPrecedent(
        'SC-2017-001',
        'Establishes that any state measure affecting informational privacy or personal autonomy must pass legality, legitimate state aim, and proportionality.',
        'Supreme Court of India — 9-Judge Constitution Bench ((2017) 10 SCC 1)'
      );
      const maneka = this.toSupportingPrecedent(
        'SC-1978-010',
        'Requires state procedure impacting Article 21 personal liberty to be fair, just, and non-arbitrary.',
        'Supreme Court of India — 7-Judge Constitution Bench ((1978) 1 SCC 248)'
      );

      argumentsList.push({
        id: 'arg-privacy-proportionality',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Challenge to State Surveillance / Data Interception Under Article 21 Proportionality Test',
        legalQuestion: 'Whether impugned surveillance, interception, or biometric harvesting satisfies the three-fold constitutional requirements of legality, legitimate state aim, and strict proportionality under Article 21.',
        legalProposition:
          'Informational privacy is a fundamental right under Article 21. Any State curtailment is unconstitutional unless authorized by valid enacted law, pursuing a legitimate state interest, and satisfying strict proportionality (minimal intrusiveness and procedural safeguards).',
        relevantFacts:
          understanding.factClassification.partyAllegations.find(a => /privacy|surveillance|biometric|interception/i.test(a)) ||
          'Submitted facts allege unauthorized surveillance or biometric data interception.',
        applicableProvisions: ['Article 21, Constitution of India', 'Article 14, Constitution of India', 'Article 19(1)(a), Constitution of India', 'Section 69, IT Act, 2000 (verify if invoked)'],
        supportingPrecedents: [puttaswamy, maneka],
        ratioDecidendi:
          'A unanimous 9-judge bench held in Justice K.S. Puttaswamy (Retd.) v. Union of India [(2017) 10 SCC 1] that privacy encompasses informational self-determination and restrains State surveillance absent strict proportionality.',
        judicialReasoning:
          'Unchecked electronic or biometric surveillance chills free expression (Art. 19(1)(a)) and erodes human dignity unless bounded by statutory necessity and independent review safeguards.',
        applicationToFacts:
          'Absent a specific, reasoned written order complying with statutory interception rules (such as S. 5(2) Telegraph Act / S. 69 IT Act & Review Committee oversight), impugned telemetry harvesting fails legality and proportionality thresholds.',
        factualDistinctions:
          'Note that in K.S. Puttaswamy (Aadhaar-5J, 2018), targeted welfare legislation passed proportionality while private/blanket linkage provisions were struck down; thus whether a clear statutory backing exists is decisive.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Subject to verification of statutory authorization & executive orders):

1. THAT the impugned interception and personal data collection directly implicate the Petitioner's fundamental right to informational privacy guaranteed under Article 21 of the Constitution of India.
2. THAT as settled by the 9-Judge Constitution Bench in Justice K.S. Puttaswamy (Retd.) v. Union of India [(2017) 10 SCC 1], any State measure restricting privacy must cumulatively satisfy: (i) legality, backed by an enacted statute; (ii) legitimate State aim; and (iii) proportionality between the objective pursued and the intrusiveness of means adopted.
3. THAT lacking prior reasoned statutory authorization and independent oversight scrutiny, the impugned action cannot pass constitutional muster under Articles 14, 19(1)(a), and 21.`,
        draftDisclaimer,
        evidenceRequired: [
          'Impugned executive order or interception notice (or RTI / statutory disclosure response).',
          'Proof of specific statutory authority cited by the Respondent agency.',
          'Review Committee approval records (if interception claims S. 69 IT Act).'
        ],
        weaknesses:
          'Where the State establishes statutory interception orders approved by the designated Review Committee on national security or public order grounds, courts extend heightened deference.',
        limitations: 'Official interception orders are frequently confidential until produced before court in sealed cover or redacted disclosure.',
        counterarguments: [
          {
            opposingGround: 'Statutory Authorization under National Security / Public Order Exceptions',
            opposingLegalBasis: 'Article 19(2), Section 69 Information Technology Act, 2000 / Telecommunication Act rules.',
            factualBasis: 'Applies if the State relies on duly passed Competent Authority interception orders.',
            vulnerabilityAssessment: 'Moderate to High — Courts require specific statutory compliance, not blanket security assertions.',
            rebuttalStrategy:
              'Argue that even where national security is invoked, strict procedural compliance (written recorded reasons, time limits, and Review Committee scrutiny) remains mandatory under PUCL & Puttaswamy.',
            requiredEvidence: 'Affidavit from Respondent confirming existence and review compliance of authorization order (if any).'
          }
        ]
      });
    }

    // 5. QUASHING GROUND (Section 482 CrPC / Section 528 BNSS)
    if (/\b(?:quash|482|528|frivolous|civil breach|civil dispute|abuse of process|bhajan lal)\b/i.test(textLower)) {
      const bhajan = this.toSupportingPrecedent(
        'SC-1990-009',
        'Enumerates Categories (1) and (7) allowing quashing where face-value FIR allegations fail to disclose any offence or manifest civil dispute coercion.',
        'Supreme Court of India — Division Bench (1992 Supp (1) SCC 335)'
      );

      argumentsList.push({
        id: 'arg-quashing-threshold',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Maintainability of Quashing Due to Lack of Prima Facie Mens Rea in Contractual / Civil Dispute',
        legalQuestion: 'Whether an FIR arising out of a commercial or contractual default discloses a prima facie criminal offence at inception or warrants quashing as an abuse of process.',
        legalProposition:
          'Mere breach of contract does not constitute criminal cheating unless dishonest intention existed at the very inception of the transaction. Courts may quash proceedings under S. 482 CrPC / S. 528 BNSS where face-value allegations establish only a civil wrong.',
        relevantFacts: 'Narrative asserts commercial contractual dispute without dishonest intention at contract inception.',
        applicableProvisions: isPost
          ? ['Section 528, BNSS, 2023', 'Article 226, Constitution of India', 'Section 318, BNS, 2023']
          : ['Section 482 CrPC / Section 528 BNSS (verify FIR date)', 'Article 226, Constitution of India'],
        supportingPrecedents: [bhajan],
        ratioDecidendi:
          'Under Categories 1 and 7 of Bhajan Lal, inherent power serves to prevent abuse of criminal process where allegations fail to disclose essential ingredients of the charged offence.',
        judicialReasoning:
          'Criminal law cannot be used as an instrument of recovery or civil settlement pressure absent prima facie statutory ingredients.',
        applicationToFacts:
          'Examine exact FIR averments to verify whether part-performance or subsequent business failure is mischaracterized as initial fraudulent inducement.',
        factualDistinctions:
          'In Neeharika Infrastructure (2021), SC cautioned High Courts against staying investigations prematurely unless exceptional Bhajan Lal grounds plainly appear on face of FIR.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Examine complete FIR allegations prior to filing):

1. THAT taking the allegations in the impugned FIR at face value and in their entirety, the essential ingredients of dishonest intention at the inception of the transaction are absent.
2. THAT relying on Category (1) and Category (7) of State of Haryana v. Bhajan Lal [1992 Supp (1) SCC 335], criminal prosecution cannot be permitted to coerce civil contractual recovery.
3. THAT invoking inherent jurisdiction under ${isPost ? 'Section 528 BNSS' : 'Section 482 CrPC / Section 528 BNSS'}, the impugned proceedings merit threshold scrutiny to prevent abuse of process.`,
        draftDisclaimer,
        evidenceRequired: ['Certified copy of FIR', 'Original commercial agreement and invoices showing part performance', 'Civil notice / ledger correspondence'],
        weaknesses:
          'If FIR contains specific factual averments alleging forged representations or pre-inception deception, courts generally decline threshold quashing and leave it to investigation/trial.',
        limitations: 'Full FIR text must be audited line-by-line.',
        counterarguments: [
          {
            opposingGround: 'Investigation Should Not Be Scuttled at Threshold / Disputed Questions of Fact',
            opposingLegalBasis: 'Neeharika Infrastructure principles restricting Section 482/528 intervention during nascent investigation.',
            factualBasis: 'Raised routinely where chargesheet is yet to be filed.',
            vulnerabilityAssessment: 'High during early investigation — Quashing is discretionary and exceptional.',
            rebuttalStrategy: 'Demonstrate from undisputed written contracts attached to FIR itself that every essential element of cheating at inception is absent.',
            requiredEvidence: 'Undisputed signed contract terms & bank transfer evidence showing initial bona fide performance.'
          }
        ]
      });
    }

    // 6. NI ACT SECTION 138/139 PRESUMPTION GROUND
    if (/\b(?:cheque|138|139|dishonour|negotiable)\b/i.test(textLower)) {
      const rangappa = this.toSupportingPrecedent(
        'SC-2010-008',
        'Holds accused may rebut Section 139 presumption on preponderance of probabilities using complainant records or defence evidence.',
        'Supreme Court of India — 3-Judge Bench ((2010) 11 SCC 441)'
      );
      const bir = this.toSupportingPrecedent(
        'SC-2019-007',
        'Clarifies signed blank cheques attract Section 139 presumption unless absence of enforceable debt or misuse is established by cogent defence.',
        'Supreme Court of India — Division Bench ((2019) 4 SCC 197)'
      );

      argumentsList.push({
        id: 'arg-ni-138',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Rebuttal of Section 139 NI Act Statutory Presumption on Preponderance of Probabilities',
        legalQuestion: 'Whether the drawer has raised a probable defence showing absence of legally enforceable debt or time-barred liability at the date of cheque presentation.',
        legalProposition:
          'While Section 139 raises a rebuttable presumption covering existence of legally enforceable debt, the accused need only raise a probable defence on preponderance of probabilities rather than proof beyond reasonable doubt.',
        relevantFacts: 'Submitted facts assert blank/security cheque or absence/time-bar of enforceable debt.',
        applicableProvisions: ['Section 138, Negotiable Instruments Act, 1881', 'Section 139, NI Act, 1881', 'Section 118, NI Act, 1881'],
        supportingPrecedents: [rangappa, bir],
        ratioDecidendi:
          'Under Rangappa v. Sri Mohan [(2010) 11 SCC 441], once credible doubt is cast upon enforceable debt (including financial capacity or time-barred claim under S. 18 Limitation Act), statutory presumption stands rebutted.',
        judicialReasoning:
          'Standard of proof for defence in quasi-criminal cheque dishonour trials aligns with civil preponderance of probabilities.',
        applicationToFacts:
          'Note that under Bir Singh v. Mukesh Kumar [(2019) 4 SCC 197], merely asserting that cheque particulars were filled by payee does not automatically defeat S. 138; the defence must prove actual absence of debt/consideration or post-settlement misuse.',
        factualDistinctions:
          'Time-barred debt claims require computing exact acknowledgment dates under Limitation Act, 1963.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Verify cheque presentation, dishonour & demand notice timelines):

1. THAT under Rangappa v. Sri Mohan [(2010) 11 SCC 441], the presumption mandated by Section 139 NI Act is rebuttable on a preponderance of probabilities, and the accused is entitled to rely on omissions in the complainant's own financial records.
2. THAT acknowledging Bir Singh v. Mukesh Kumar [(2019) 4 SCC 197], the defence rests not merely on the cheque having been handed over in blank, but on substantive absence of any subsisting legally enforceable debt on the date of presentation.`,
        draftDisclaimer,
        evidenceRequired: ['Original cheque & bank return memo', 'Section 138(b) statutory demand notice & reply', 'Books of account / payment receipts / time-bar calculation'],
        weaknesses:
          'If drawer failed to reply to statutory S. 138(b) notice or admits transaction without documentary repayment proof, Section 139 presumption prevails.',
        limitations: 'Requires proof of debt timeline and reply notice.',
        counterarguments: [
          {
            opposingGround: 'Statutory Presumption Once Signature Admitted (Section 139 & Bir Singh)',
            opposingLegalBasis: 'Sections 20, 118 & 139 Negotiable Instruments Act, 1881.',
            factualBasis: 'Signature admission places initial evidentiary burden on drawer.',
            vulnerabilityAssessment: 'High — Presumption operates automatically unless concrete probable defence is demonstrated.',
            rebuttalStrategy: 'Cross-examine complainant on financial capacity/ITR records and confront with prior repayment receipts or limitation expiration.',
            requiredEvidence: 'Bank account statements, written payment receipts, and notice reply.'
          }
        ]
      });
    }

    // 7. ARBITRATION GROUND
    if (/\b(?:arbitrat|section 8|section 11|section 34)\b/i.test(textLower)) {
      const vidya = this.toSupportingPrecedent(
        'SC-2020-013',
        'Establishes four-fold non-arbitrability test and mandates Section 8/11 referral unless agreement is ex facie non-existent or non-arbitrable.',
        'Supreme Court of India — 3-Judge Bench ((2021) 2 SCC 1)'
      );
      const assoc = this.toSupportingPrecedent(
        'SC-2014-020',
        'Restricts judicial interference under Section 34 arbitration challenge strictly to narrow public policy/perversity grounds.',
        'Supreme Court of India — Division Bench ((2015) 3 SCC 49)'
      );

      argumentsList.push({
        id: 'arg-arbitration',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Mandatory Arbitration Referral (S. 8) & Scope of Judicial Non-Interference',
        legalQuestion: 'Whether civil court jurisdiction is excluded by a valid arbitration clause under S. 8, or whether award challenge falls within narrow S. 34 grounds.',
        legalProposition: 'Judicial authorities must refer parties to arbitration under Section 8 once a valid arbitration clause is shown, and under Section 34 cannot sit as appellate courts over arbitral reasoning.',
        relevantFacts: 'Submitted facts invoke arbitration clause or challenge under the 1996 Act.',
        applicableProvisions: ['Section 8, Arbitration and Conciliation Act, 1996', 'Section 11 & 34, Arbitration and Conciliation Act, 1996'],
        supportingPrecedents: [vidya, assoc],
        ratioDecidendi: 'Civil commercial disputes involving rights in personam are arbitrable under the four-fold test in Vidya Drolia.',
        judicialReasoning: 'Preserves contractual party autonomy and minimal judicial interference (Section 5).',
        applicationToFacts: 'Check whether application under Section 8 was filed not later than the date of submitting first statement on substance of dispute.',
        factualDistinctions: 'Verify whether subject matter involves non-arbitrable rent control statutory forums or public actions in rem.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION:

1. THAT under Section 8(1) of the Arbitration and Conciliation Act, 1996, reference to arbitration is peremptory once an arbitration agreement covering the dispute is placed on record.
2. THAT applying Vidya Drolia v. Durga Trading Corporation [(2021) 2 SCC 1], the commercial dispute operates strictly in personam and satisfies arbitrability.`,
        draftDisclaimer,
        evidenceRequired: ['Signed contract containing arbitration clause', 'Timeline verifying first statement on substance not yet filed'],
        weaknesses: 'Forfeited if defendant already submitted first statement on merits without seeking S. 8 referral.',
        limitations: 'Agreement text and special rent/consumer exclusivity must be checked.',
        counterarguments: [
          {
            opposingGround: 'Allegation of Fraud / Waiver by Submitting Written Statement',
            opposingLegalBasis: 'S. 8(1) statutory deadline and serious fraud exception.',
            factualBasis: 'Turns on filing dates in civil suit.',
            vulnerabilityAssessment: 'Moderate — Fraud affecting substantive contract remains arbitrable unless it invalidates arbitration clause itself.',
            rebuttalStrategy: 'Invoke Vidya Drolia clarification narrowing the fraud exception and confirm timely filing prior to written statement.',
            requiredEvidence: 'Court order-sheet confirming date of written statement vs S. 8 application.'
          }
        ]
      });
    }

    // 8. TRADEMARK / DEFAMATION / SPEECH GROUNDS (only when genuinely triggered)
    if (/\b(?:trademark|passing off|66a|speech|defamation)\b/i.test(textLower)) {
      const shreya = this.toSupportingPrecedent(
        'SC-2015-002',
        'Invalidated Section 66A IT Act for vagueness and clarified discussion/advocacy vs incitement.',
        'Supreme Court of India ((2015) 5 SCC 1)'
      );
      const tata = this.toSupportingPrecedent(
        'DEL-2022-016',
        'Clarified trademark infringement and purposeful availment jurisdiction for online commercial platforms.',
        'High Court of Delhi — Division Bench (2022 SCC OnLine Del 2968)'
      );

      argumentsList.push({
        id: 'arg-ip-speech',
        groundNumber: `Ground ${argumentsList.length + 1}`,
        heading: 'Statutory Trademark Protection / Constitutional Free Speech Parameters',
        legalQuestion: 'Whether impugned conduct infringes statutory trademark rights (S. 29 Trade Marks Act) or enjoys Article 19(1)(a) protection.',
        legalProposition: 'Well-known trademarks receive protection against deceptive similarity and commercial dilution, whereas state restrictions on online speech must strictly conform to Article 19(2) exceptions.',
        relevantFacts: 'Submitted text raises trademark infringement or online expression.',
        applicableProvisions: ['Section 29, Trade Marks Act, 1999 / Article 19(1)(a) Constitution'],
        supportingPrecedents: [tata, shreya],
        ratioDecidendi: 'Marks targeting Indian markets satisfy purposeful availment; speech restrictions require clear Article 19(2) nexus.',
        judicialReasoning: 'Balances commercial goodwill against constitutional freedom of expression.',
        applicationToFacts: 'Assess documentary evidence of deceptive similarity or statutory basis of restriction.',
        factualDistinctions: 'Delhi HC decisions are persuasive outside Delhi; verify registration certificate and balance of convenience.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION: Rely on statutory registration/goodwill (Tata Sons) or Article 19(1)(a) overbreadth standards (Shreya Singhal) depending on party posture.`,
        draftDisclaimer,
        evidenceRequired: ['Trademark registration record / impugned post / screenshot evidence with S. 63 BSA / 65B certificate'],
        weaknesses: 'Interim injunction requires strong prima facie case, balance of convenience, and irreparable harm.',
        limitations: 'Fact-dependent.',
        counterarguments: [
          {
            opposingGround: 'Fair Comment / Territorial Jurisdiction Objection',
            opposingLegalBasis: 'Article 19(1)(a) fair comment defence or Section 20 CPC.',
            factualBasis: 'Depends on online interactivity or truth justification.',
            vulnerabilityAssessment: 'Moderate.',
            rebuttalStrategy: 'Produce proof of commercial targeting in jurisdiction and consumer confusion.',
            requiredEvidence: 'Verified screenshots and commercial traffic records.'
          }
        ]
      });
    }

    // Fallback when no specialized domain ground matched
    if (argumentsList.length === 0) {
      const maneka = this.toSupportingPrecedent(
        'SC-1978-010',
        'Establishes that any procedure or administrative order affecting rights or liberty must be just, fair, and reasonable under Articles 14 and 21.',
        'Supreme Court of India — 7-Judge Constitution Bench ((1978) 1 SCC 248)'
      );

      argumentsList.push({
        id: 'arg-natural-justice',
        groundNumber: 'Ground 1',
        heading: 'Procedural Fairness, Reasoned Decision-Making & Natural Justice (Articles 14 & 21)',
        legalQuestion: 'Whether the impugned action conforms to statutory jurisdiction, fair hearing (audi alteram partem), and reasoned adjudication.',
        legalProposition: 'Administrative and quasi-judicial decisions adversely affecting civil rights or liberty must be non-arbitrary, backed by reasons, and preceded by an opportunity of fair hearing.',
        relevantFacts: understanding.materialFacts[0] || 'Submitted narrative requires closer statutory detail.',
        applicableProvisions: ['Article 14, Constitution of India', 'Article 21, Constitution of India'],
        supportingPrecedents: [maneka],
        ratioDecidendi: 'Procedure established by law must be just, fair, and reasonable rather than fanciful or oppressive (Maneka Gandhi).',
        judicialReasoning: 'Reasoned orders prevent arbitrary executive action and permit meaningful appellate/judicial review.',
        applicationToFacts: 'Requires examination of the impugned order and underlying statutory enactment.',
        factualDistinctions: 'Verify whether alternative statutory appellate remedy exists before invoking writ jurisdiction.',
        suggestedSubmission: `DRAFT RESEARCH SUBMISSION (Populate exact statutory provision & impugned order date):

1. THAT the impugned action suffers from procedural unfairness and lack of reasoned consideration contrary to Article 14 of the Constitution of India and Maneka Gandhi v. Union of India [(1978) 1 SCC 248].`,
        draftDisclaimer,
        evidenceRequired: ['Impugned order / notice copy', 'Representation or reply submitted prior to adverse action'],
        weaknesses: 'Insufficient statutory specifics in the factual input limit targeted argument drafting.',
        limitations: 'Submit specific statute, court/authority name, and chronological dates for stronger grounds.',
        counterarguments: [
          {
            opposingGround: 'Availability of Alternate Statutory Remedy / Substantial Hearing',
            opposingLegalBasis: 'Doctrine of exhaustion of alternative statutory remedies.',
            factualBasis: 'Applicable if governing statute provides an appellate tribunal.',
            vulnerabilityAssessment: 'Moderate.',
            rebuttalStrategy: 'Demonstrate patent lack of jurisdiction or breach of natural justice exception.',
            requiredEvidence: 'Show-cause notice and order copy.'
          }
        ]
      });
    }

    return argumentsList;
  }

  /**
   * Builds honest Historical Judicial Treatment & Research Assessment (NO invented numeric probabilities!).
   */
  public static buildJudicialTreatmentAssessment(
    facts: string,
    precedents: IMatchedPrecedent[],
    understanding: ICaseUnderstanding,
    lawAssessment: ApplicableLawAssessment
  ): IJudicialTreatmentAssessment {
    const principles: string[] = [];
    const supporting: IJudicialTreatmentAssessment['supportingAuthorities'] = [];
    const distinguishing: IJudicialTreatmentAssessment['distinguishingOrAdverseAuthorities'] = [];
    const determinants: string[] = [];

    if (lawAssessment.isCriminalOrQuasiCriminal) {
      principles.push(
        'Indian Supreme Court jurisprudence treats personal liberty (Art. 21) and written/meaningful grounds of arrest (Art. 22(1)) as foundational constitutional requirements; proven violation can invalidate arrest and subsequent remand.'
      );
      principles.push(
        'For offences punishable up to 7 years, judicial relief ordinarily turns on whether arresting officers recorded objective necessity and served statutory Notice of Appearance (S. 41A CrPC / S. 35(3) BNSS).'
      );
      determinants.push(
        'Exact penal sections invoked in the FIR (specifically whether maximum sentence is <= 7 years or > 7 years)',
        'FIR registration and arrest dates (governing CrPC vs. BNSS applicability and prospective timeline of Mihir Rajesh Shah)',
        'Documentary contents of Arrest Memo, Case Diary reasons, and first Judicial Remand Order'
      );
    } else {
      principles.push(
        'Courts examine strict statutory compliance (such as 30-day NI Act demand notice, three-fold Article 21 proportionality, or Section 8 arbitral mandate) based on contemporaneous documentary proof.'
      );
      determinants.push(
        'Limitation dates and statutory notice acknowledgments',
        'Executed contractual terms and documentary proof supporting/rebutting claims'
      );
    }

    precedents.forEach(p => {
      if (p.relevanceClassification === 'Directly relevant' || p.relevanceClassification === 'Supporting authority') {
        supporting.push({
          caseTitle: p.caseTitle,
          citation: p.citation,
          proposition: p.summary
        });
      } else {
        distinguishing.push({
          caseTitle: p.caseTitle,
          citation: p.citation,
          distinctionNote: p.obiterAndScopeNote || p.retrievalReason
        });
      }
    });

    if (distinguishing.length === 0) {
      distinguishing.push({
        caseTitle: 'General Statutory & Evidentiary Qualification',
        citation: 'Procedural Verification Standard',
        distinctionNote:
          'Favourable precedents depend strictly upon proving underlying factual allegations (e.g. non-service of notice or absence of written grounds) from certified court and police records.'
      });
    }

    return {
      assessmentTitle: 'Historical Judicial Treatment & Research Assessment',
      researchScopeNote:
        'Statistical judicial outcome forecasting and numeric probability percentages are intentionally omitted. Court outcomes depend on verified evidence, exact statutory provisions in the FIR/plaint, and independent judicial discretion.',
      historicalLegalPrinciples: principles,
      supportingAuthorities: supporting.slice(0, 5),
      distinguishingOrAdverseAuthorities: distinguishing.slice(0, 4),
      keyFactualDeterminants: determinants,
      researchLimitations: [
        'This assessment relies exclusively on user-supplied facts and cannot inspect unproduced police diaries, FIRs, remand orders, or opposite-party records.',
        'Curated judgment summaries highlight core legal principles and do not replace reading the full judgment text alongside subsequent High Court/Supreme Court rulings.',
        `Applicable procedural statute requires verification whenever offence/FIR dates are missing (${lawAssessment.regimeStatus}).`
      ]
    };
  }

  /**
   * Verified pinpoint judgment passages verified against primary signed Supreme Court judgments.
   * Paragraph numbers and direct verbatim quotes are strictly limited to character-verified authorities.
   */
  public static readonly VERIFIED_JUDGMENT_PASSAGES: Record<string, {
    caseTitle: string;
    neutralCitation?: string;
    reportedCitation: string;
    paragraphNumber?: number;
    verbatimQuote?: string;
    editorialParaphrase: string;
    isDirectQuote: boolean;
    pinpointCitation?: string;
    officialSourceUrl?: string;
    verificationStatus: 'character_verified' | 'editorial_paraphrase' | 'unverified';
  }> = {
    // 1. Vihaan Kumar v. State of Haryana [2025 INSC 162 / (2025) 5 SCC 799]
    'SC-2025-026': {
      caseTitle: 'Vihaan Kumar v. State of Haryana and Anr.',
      neutralCitation: '2025 INSC 162',
      reportedCitation: '(2025) 5 SCC 799',
      paragraphNumber: 14,
      verbatimQuote: 'Thus, the requirement of informing the person arrested of the grounds of arrest is not a formality but a mandatory constitutional requirement. Article 22 is included in Part III of the Constitution under the heading of Fundamental Rights. Thus, it is the fundamental right of every person arrested and detained in custody to be informed of the grounds of arrest as soon as possible.',
      editorialParaphrase: 'Supreme Court held that informing relatives under S. 50A CrPC / S. 48 BNSS or recording entries in police diaries cannot substitute for direct, written communication of grounds to the arrestee under Article 22(1), and non-compliance vitiates the arrest ab initio.',
      isDirectQuote: true,
      pinpointCitation: 'Para 14, 2025 INSC 162; (2025) 5 SCC 799',
      officialSourceUrl: 'https://main.sci.gov.in/supremecourt/2024/49156/49156_2024_1_1501_56133_Judgement_07-Feb-2025.pdf',
      verificationStatus: 'character_verified'
    },
    // 2. Prabir Purkayastha v. State (NCT of Delhi) [2024 INSC 414 / (2024) 8 SCC 254]
    'SC-2024-025': {
      caseTitle: 'Prabir Purkayastha v. State (NCT of Delhi)',
      neutralCitation: '2024 INSC 414',
      reportedCitation: '(2024) 8 SCC 254',
      paragraphNumber: 21,
      verbatimQuote: 'The right to be informed about the grounds of arrest flows from Article 22(1) of the Constitution of India and any infringement of this fundamental right would vitiate the process of arrest and remand. Mere fact that a charge-sheet has been filed in the matter, would not validate the illegality and the unconstitutionality committed at the time of arresting the accused and the grant of initial police custody remand to the accused.',
      editorialParaphrase: 'Supreme Court distinguished between formal reasons to arrest and case-specific grounds of arrest, holding that written communication of grounds to the arrestee is a mandatory constitutional requirement under Article 22(1), the breach of which vitiates arrest and remand.',
      isDirectQuote: true,
      pinpointCitation: 'Para 21, 2024 INSC 414; (2024) 8 SCC 254',
      officialSourceUrl: 'https://main.sci.gov.in/supremecourt/2023/45233/45233_2023_1_1501_52702_Judgement_15-May-2024.pdf',
      verificationStatus: 'character_verified'
    },
    // 3. Arnesh Kumar v. State of Bihar [(2014) 8 SCC 273; [2014] 8 S.C.R. 128]
    'SC-2014-003': {
      caseTitle: 'Arnesh Kumar v. State of Bihar and Anr.',
      neutralCitation: '2014 INSC 474',
      reportedCitation: '(2014) 8 SCC 273; [2014] 8 S.C.R. 128',
      paragraphNumber: 11,
      verbatimQuote: 'Our endeavour in this judgment is to ensure that police officers do not arrest accused unnecessarily and Magistrate do not authorise detention casually and mechanically.',
      editorialParaphrase: 'Supreme Court directed all State Governments to instruct police officers that they will not automatically arrest when a case under Section 498-A IPC or offences punishable with up to 7 years imprisonment is registered, but must satisfy themselves regarding the necessity of arrest under Section 41 CrPC checklist and serve notice of appearance under Section 41A.',
      isDirectQuote: true,
      pinpointCitation: 'Para 11, (2014) 8 SCC 273; [2014] 8 S.C.R. 128',
      officialSourceUrl: 'https://api.sci.gov.in/jonew/judis/41736.pdf',
      verificationStatus: 'character_verified'
    },
    // 4. D.K. Basu v. State of West Bengal [(1997) 1 SCC 416; 1996 INSC 1599]
    'SC-1996-012': {
      caseTitle: 'D.K. Basu v. State of West Bengal',
      neutralCitation: '1996 INSC 1599',
      reportedCitation: '(1997) 1 SCC 416; AIR 1997 SC 610; [1996] Supp. 10 S.C.R. 284',
      paragraphNumber: 35,
      verbatimQuote: 'The person arrested may be permitted to meet his lawyer during interrogation, though not throughout the interrogation.',
      editorialParaphrase: 'Formulated 11 mandatory procedural guidelines governing arrest and detention to prevent custodial violence, including visible police identification badges, contemporaneous arrest memo, family notification within 8-12 hours, and periodic medical checkups every 48 hours.',
      isDirectQuote: true,
      pinpointCitation: 'Para 35(10), (1997) 1 SCC 416; 1996 INSC 1599',
      officialSourceUrl: 'https://api.sci.gov.in/jonew/judis/14580.pdf',
      verificationStatus: 'character_verified'
    },
    // Legacy alias for D.K. Basu
    'SC-1997-008': {
      caseTitle: 'D.K. Basu v. State of West Bengal',
      neutralCitation: '1996 INSC 1599',
      reportedCitation: '(1997) 1 SCC 416; AIR 1997 SC 610; [1996] Supp. 10 S.C.R. 284',
      paragraphNumber: 35,
      verbatimQuote: 'The person arrested may be permitted to meet his lawyer during interrogation, though not throughout the interrogation.',
      editorialParaphrase: 'Formulated 11 mandatory procedural guidelines governing arrest and detention to prevent custodial violence, including visible police identification badges, contemporaneous arrest memo, family notification within 8-12 hours, and periodic medical checkups every 48 hours.',
      isDirectQuote: true,
      pinpointCitation: 'Para 35(10), (1997) 1 SCC 416; 1996 INSC 1599',
      officialSourceUrl: 'https://api.sci.gov.in/jonew/judis/14580.pdf',
      verificationStatus: 'character_verified'
    },
    // 5. Lalita Kumari v. Govt. of U.P. [(2014) 2 SCC 1; 2013 INSC 1184]
    'SC-2013-004': {
      caseTitle: 'Lalita Kumari v. Govt. of U.P. and Ors.',
      neutralCitation: '2013 INSC 1184',
      reportedCitation: '(2014) 2 SCC 1; [2013] 14 S.C.R. 713',
      paragraphNumber: 120,
      verbatimQuote: 'The registration of FIR is mandatory under Section 154 of the Code, if the information discloses commission of a cognizable offence and no preliminary inquiry is permissible in such a situation.',
      editorialParaphrase: 'Held registration of FIR mandatory under Section 154 CrPC upon disclosure of a cognizable offence, with preliminary inquiry permissible only in narrow specified categories (e.g. matrimonial disputes, commercial offences, medical negligence, corruption cases, or abnormal delay) to ascertain whether a cognizable offence is disclosed.',
      isDirectQuote: true,
      pinpointCitation: 'Para 120.1, (2014) 2 SCC 1; 2013 INSC 1184',
      officialSourceUrl: 'https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/documents/aor_notice_circular/31.pdf',
      verificationStatus: 'character_verified'
    },
    // 6. Navtej Singh Johar v. Union of India [(2018) 10 SCC 1; 2018 INSC 790]
    'SC-2018-005': {
      caseTitle: 'Navtej Singh Johar and Ors. v. Union of India thr. Secretary Ministry of Law and Justice',
      neutralCitation: '2018 INSC 790',
      reportedCitation: '(2018) 10 SCC 1; [2018] 13 S.C.R. 379; AIR 2018 SC 4321',
      paragraphNumber: 267,
      verbatimQuote: 'Thus analysed, Section 377 IPC, so far as it penalizes any consensual sexual activity between two adults, be it homosexuals (man and a man), heterosexuals (man and a woman) and lesbians (woman and a woman), cannot be regarded as constitutional.',
      editorialParaphrase: 'Supreme Court unanimously read down Section 377 IPC to decriminalize consensual sexual conduct between adults in private, holding that criminalization violates fundamental rights under Articles 14, 15, 19(1)(a), and 21 of the Constitution.',
      isDirectQuote: true,
      pinpointCitation: 'Para 267, (2018) 10 SCC 1; 2018 INSC 790',
      officialSourceUrl: 'https://api.sci.gov.in/supremecourt/2016/14961/14961_2016_Judgement_06-Sep-2018.pdf',
      verificationStatus: 'character_verified'
    },
    // 7. Shayara Bano v. Union of India [(2017) 9 SCC 1; 2017 INSC 615]
    'SC-2017-006': {
      caseTitle: 'Shayara Bano v. Union of India and Ors.',
      neutralCitation: '2017 INSC 615',
      reportedCitation: '(2017) 9 SCC 1; [2017] 9 S.C.R. 797; AIR 2017 SC 4609',
      paragraphNumber: 101,
      verbatimQuote: 'Manifest arbitrariness, therefore, must be something done by the legislature capriciously, irrationally and/or without adequate determining principle. Also, when something is done which is excessive and disproportionate, such legislation would be manifestly arbitrary. We are, therefore, of the view that arbitrariness in the sense of manifest arbitrariness as pointed out by us above would apply to negate legislation as well under Article 14.',
      editorialParaphrase: 'Constitution Bench majority established the doctrine of manifest arbitrariness as an independent ground to invalidate primary legislation under Article 14, setting aside the practice of instantaneous triple talaq (talaq-e-biddat) as unconstitutional.',
      isDirectQuote: true,
      pinpointCitation: 'Para 101, (2017) 9 SCC 1; 2017 INSC 615',
      officialSourceUrl: 'https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/documents/aor_notice_circular/42.pdf',
      verificationStatus: 'character_verified'
    },
    // 8. State of Haryana v. Bhajan Lal [1992 Supp (1) SCC 335; 1990 INSC 363]
    'SC-1990-009': {
      caseTitle: 'State of Haryana and Ors. v. Ch. Bhajan Lal and Ors.',
      neutralCitation: '1990 INSC 363',
      reportedCitation: '1992 Supp (1) SCC 335; AIR 1992 SC 604; [1990] Supp. 3 S.C.R. 259',
      paragraphNumber: 102,
      verbatimQuote: 'Where the allegations made in the first information report or the complaint, even if they are taken at their face value and accepted in their entirety do not prima facie constitute any offence or make out a case against the accused.',
      editorialParaphrase: 'Laid down seven illustrative categories where the High Court may exercise extraordinary power under Article 226 or inherent powers under Section 482 CrPC to quash criminal proceedings to prevent abuse of the judicial process or secure the ends of justice.',
      isDirectQuote: true,
      pinpointCitation: 'Para 102(1), 1992 Supp (1) SCC 335; 1990 INSC 363',
      officialSourceUrl: 'https://api.sci.gov.in/jonew/judis/1033637.pdf',
      verificationStatus: 'character_verified'
    },
    // Legacy alias for Bhajan Lal
    'SC-1992-001': {
      caseTitle: 'State of Haryana and Ors. v. Ch. Bhajan Lal and Ors.',
      neutralCitation: '1990 INSC 363',
      reportedCitation: '1992 Supp (1) SCC 335; AIR 1992 SC 604; [1990] Supp. 3 S.C.R. 259',
      paragraphNumber: 102,
      verbatimQuote: 'Where the allegations made in the first information report or the complaint, even if they are taken at their face value and accepted in their entirety do not prima facie constitute any offence or make out a case against the accused.',
      editorialParaphrase: 'Laid down seven illustrative categories where the High Court may exercise extraordinary power under Article 226 or inherent powers under Section 482 CrPC to quash criminal proceedings to prevent abuse of the judicial process or secure the ends of justice.',
      isDirectQuote: true,
      pinpointCitation: 'Para 102(1), 1992 Supp (1) SCC 335; 1990 INSC 363',
      officialSourceUrl: 'https://api.sci.gov.in/jonew/judis/1033637.pdf',
      verificationStatus: 'character_verified'
    }
  };

  /**
   * Resolves verifiable judgment passage or editorial paraphrase without manufacturing citations.
   */
  public static getSupportingJudgmentPassage(
    precedentIdOrKeyword: string,
    fallbackSummary?: string
  ): ISupportingJudgmentPassage {
    const rec = judgmentRegistry.findById(precedentIdOrKeyword) || judgmentRegistry.findByKeyword(precedentIdOrKeyword);
    const id = rec ? rec.id : precedentIdOrKeyword;

    const verified = this.VERIFIED_JUDGMENT_PASSAGES[id];
    if (verified) {
      return {
        paragraphNumber: verified.paragraphNumber,
        verbatimQuote: verified.isDirectQuote ? verified.verbatimQuote : undefined,
        editorialParaphrase: verified.editorialParaphrase,
        isDirectQuote: verified.isDirectQuote,
        pinpointCitation: verified.pinpointCitation,
        verificationSource: rec?.officialSourceUrl || verified.officialSourceUrl || rec?.sourceUrl,
        verificationStatus: verified.verificationStatus || (verified.isDirectQuote ? 'character_verified' : 'editorial_paraphrase')
      };
    }

    // Editorial paraphrase / unverified fallback: isDirectQuote strictly false, paragraphNumber undefined
    const isUnverified = !rec || rec.verificationStatus === 'unverified';
    const para = fallbackSummary || rec?.summary || 'Authoritative ratio principle requires independent verification against primary report.';
    return {
      editorialParaphrase: para,
      isDirectQuote: false,
      verificationSource: rec?.officialSourceUrl || rec?.sourceUrl,
      verificationStatus: isUnverified ? 'unverified' : 'editorial_paraphrase'
    };
  }

  /**
   * Validates legal authority citations and quotations against strict judicial integrity rules.
   * - Rejects invalid neutral citations (must match official INSC / High Court patterns).
   * - Rejects paragraph numbers not supported by primary signed records.
   * - Prevents editorial paraphrases from being presented as direct quotations.
   * - Ensures unverified authorities are visibly marked.
   */
  public static validateAuthorityPassage(authority: {
    caseTitle?: string;
    neutralCitation?: string;
    reportedCitation?: string;
    paragraphNumber?: number;
    verbatimQuote?: string;
    editorialParaphrase?: string;
    isDirectQuote?: boolean;
    verificationStatus?: 'character_verified' | 'editorial_paraphrase' | 'unverified';
  }): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    // 1. Strict neutral citation format check (e.g. "2025 INSC 162" or "2023:BHC-OS:4316")
    if (authority.neutralCitation) {
      const validCitationPattern = /^(\d{4}\s+INSC\s+\d+|\d{4}:[A-Z]{2,4}(?:-[A-Z]+)?:\d+)$/;
      if (!validCitationPattern.test(authority.neutralCitation.trim())) {
        errors.push(`Invalid neutral citation format: "${authority.neutralCitation}". Expected official format like "YYYY INSC NNN".`);
      }
    }

    // 2. Cross-check against known verified authorities if caseTitle matches
    if (authority.caseTitle) {
      const lowerTitle = authority.caseTitle.toLowerCase();
      let matchedEntry = Object.values(this.VERIFIED_JUDGMENT_PASSAGES).find(
        e => e.caseTitle.toLowerCase().includes(lowerTitle) || lowerTitle.includes(e.caseTitle.toLowerCase())
      );

      if (matchedEntry) {
        // Neutral citation mismatch
        if (
          authority.neutralCitation &&
          matchedEntry.neutralCitation &&
          authority.neutralCitation.trim() !== matchedEntry.neutralCitation
        ) {
          errors.push(
            `Neutral citation mismatch for "${authority.caseTitle}": got "${authority.neutralCitation}", expected verified "${matchedEntry.neutralCitation}".`
          );
        }

        // Paragraph number mismatch
        if (
          authority.paragraphNumber !== undefined &&
          matchedEntry.paragraphNumber !== undefined &&
          authority.paragraphNumber !== matchedEntry.paragraphNumber
        ) {
          errors.push(
            `Paragraph number not supported by source for "${authority.caseTitle}": claimed Para ${authority.paragraphNumber}, but primary record verifies Para ${matchedEntry.paragraphNumber}.`
          );
        }
      }
    }

    // 3. Strict quotation integrity: Editorial paraphrases must NEVER claim to be direct quotes
    if (authority.isDirectQuote) {
      if (authority.verificationStatus === 'editorial_paraphrase') {
        errors.push('Integrity violation: Editorial paraphrase cannot be claimed as a direct quotation (isDirectQuote must be false).');
      }
      if (authority.verificationStatus === 'unverified') {
        errors.push('Integrity violation: Unverified authority cannot be claimed as a direct quotation.');
      }
      if (!authority.verbatimQuote || authority.verbatimQuote.trim().length === 0) {
        errors.push('Integrity violation: isDirectQuote is true but verbatimQuote is empty or missing.');
      }
    }

    // 4. If isDirectQuote is false, verbatimQuote must not be present
    if (!authority.isDirectQuote && authority.verbatimQuote) {
      errors.push('Integrity violation: When isDirectQuote is false, verbatimQuote must be omitted to prevent misleading quotes.');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Assembles an end-to-end evidence traceability chain:
   * Uploaded Document Passage -> Extracted Fact -> Legal Issue -> Statute -> Precedent -> Judgment Passage -> Draft Argument
   * Connects actual generated analysis data using stable IDs, detects OCR uncertainty,
   * attaches caveats where necessary, and leaves arguments unrelated to OCR text unencumbered.
   */
  public static buildEvidenceTraceGraph(
    understanding: ICaseUnderstanding,
    legalIssues: Array<{
      issue: string;
      relevantFacts?: string;
      statutoryProvision: string;
      supportingAuthorities?: string[];
      whyIssueMatters?: string;
      informationStillRequired?: string;
      description: string;
      matchedKeywords?: string[];
      id?: string;
    }>,
    legalArguments: ILegalArgument[],
    precedents: IMatchedPrecedent[],
    applicableLaw: ApplicableLawAssessment,
    documentMetadata?: any
  ): IEvidenceTraceNode[] {
    const traceNodes: IEvidenceTraceNode[] = [];
    const attributedFacts = understanding.attributedFacts || [];

    legalArguments.forEach((arg, argIdx) => {
      const traceId = `trace-${arg.id || 'ground-' + (argIdx + 1)}`;
      const unresolvedRelationships: string[] = [];

      // 1. Match Factual Assertion
      let matchedFact: IAttributedFact | undefined;
      if (arg.relevantFacts) {
        matchedFact = attributedFacts.find(f =>
          f.statement.includes(arg.relevantFacts) || arg.relevantFacts.includes(f.statement)
        );
      }
      if (!matchedFact && attributedFacts.length > 0) {
        matchedFact = attributedFacts[argIdx % attributedFacts.length];
      }

      const factStatement = matchedFact?.statement || arg.relevantFacts || 'Material fact statement submitted for analysis';
      const factClassification = matchedFact?.classification ||
        (/\b(?:allege|alleged|allegedly|claim|contend|without|illegal|unlawful)\b/i.test(factStatement)
          ? 'Party allegation'
          : 'User-provided fact');
      const factId = matchedFact?.id || `fact-${argIdx + 1}`;
      const isContested = factClassification === 'Party allegation';

      // 2. Source Document Passage
      let sourcePassage: ISourceDocumentPassage;
      const combinedUncTokens = Array.from(new Set([
        ...(matchedFact?.uncertainTokens || []),
        ...this.extractUncertainTokens(factStatement),
        ...this.extractUncertainTokens(arg.relevantFacts || '')
      ]));

      if (matchedFact && matchedFact.attributionStatus === 'verified') {
        const pageConf = matchedFact.pageConfidence !== undefined ? matchedFact.pageConfidence : null;
        sourcePassage = {
          documentName: documentMetadata?.filename || 'Uploaded Legal Document',
          pageNumber: matchedFact.pageNumber,
          totalDocumentPages: documentMetadata?.pageCount || documentMetadata?.pages?.length,
          textSnippet: matchedFact.statement,
          extractionMethod: matchedFact.extractionMethod || 'native',
          pageConfidence: pageConf,
          uncertainTokens: combinedUncTokens,
          hasLowConfidenceTokens: combinedUncTokens.length > 0,
          attributionStatus: 'verified'
        };
      } else if (documentMetadata?.pages && documentMetadata.pages.length > 0) {
        const directAttr = this.attributeSentenceToPage(factStatement, documentMetadata.pages);
        if (directAttr.attributionStatus === 'verified') {
          sourcePassage = {
            documentName: documentMetadata?.filename || 'Uploaded Legal Document',
            pageNumber: directAttr.pageNumber,
            totalDocumentPages: documentMetadata?.pageCount || documentMetadata?.pages?.length,
            textSnippet: factStatement,
            extractionMethod: directAttr.extractionMethod,
            pageConfidence: directAttr.pageConfidence,
            uncertainTokens: combinedUncTokens,
            hasLowConfidenceTokens: combinedUncTokens.length > 0,
            attributionStatus: 'verified'
          };
        } else {
          unresolvedRelationships.push('source_page_attribution');
          sourcePassage = {
            documentName: documentMetadata?.filename || 'Uploaded Legal Document',
            pageNumber: undefined,
            totalDocumentPages: documentMetadata?.pageCount || documentMetadata?.pages?.length,
            textSnippet: factStatement,
            extractionMethod: directAttr.extractionMethod,
            pageConfidence: directAttr.pageConfidence,
            uncertainTokens: combinedUncTokens,
            hasLowConfidenceTokens: combinedUncTokens.length > 0,
            attributionStatus: 'unresolved'
          };
        }
      } else {
        unresolvedRelationships.push('source_page_attribution');
        sourcePassage = {
          documentName: documentMetadata?.filename || 'Uploaded Legal Document',
          pageNumber: undefined,
          totalDocumentPages: undefined,
          textSnippet: factStatement,
          extractionMethod: 'unresolved',
          pageConfidence: null,
          uncertainTokens: combinedUncTokens,
          hasLowConfidenceTokens: combinedUncTokens.length > 0,
          attributionStatus: 'unavailable'
        };
      }

      // 3. Match Legal Issue & Statute
      let matchedIssue = legalIssues.find(iss =>
        arg.heading.toLowerCase().includes((iss.issue || '').slice(0, 30).toLowerCase()) ||
        arg.applicableProvisions.some(p => (iss.statutoryProvision || '').includes(p)) ||
        (iss.supportingAuthorities || []).some(auth =>
          arg.supportingPrecedents.some(sp => auth.toLowerCase().includes(sp.caseTitle.toLowerCase().slice(0, 15)))
        )
      );
      if (!matchedIssue && legalIssues.length > 0) {
        matchedIssue = legalIssues[argIdx % legalIssues.length];
      }

      let legalIssueId: string | undefined;
      let legalIssueTitle: string | undefined;
      if (matchedIssue) {
        const issueIdx = legalIssues.indexOf(matchedIssue);
        legalIssueId = matchedIssue.id || `issue-${issueIdx + 1}`;
        legalIssueTitle = matchedIssue.issue;
      } else {
        unresolvedRelationships.push('legal_issue');
      }

      const statutoryProvision = arg.applicableProvisions.length > 0
        ? arg.applicableProvisions.join('; ')
        : (matchedIssue?.statutoryProvision || 'Statutory basis requires verification');
      const statutoryRegime = applicableLaw?.regimeStatus || 'unresolved';

      // 4. Precedent Authority & Issue-Specific Mapping
      let precedentNode: IEvidenceTraceNode['precedent'] | undefined;
      let supportingPassage: ISupportingJudgmentPassage | undefined;

      const primarySupporting = arg.supportingPrecedents && arg.supportingPrecedents.length > 0
        ? arg.supportingPrecedents[0]
        : undefined;

      if (primarySupporting) {
        const matchedPrec = precedents.find(p =>
          (primarySupporting.id && p.id === primarySupporting.id) ||
          p.caseTitle.toLowerCase().includes(primarySupporting.caseTitle.toLowerCase()) ||
          primarySupporting.caseTitle.toLowerCase().includes(p.caseTitle.toLowerCase()) ||
          (p.citation && primarySupporting.citation && p.citation === primarySupporting.citation)
        );

        const signals: IRetrievalSignalBreakdown = matchedPrec?.retrievalSignals || {
          tfidfRank: matchedPrec?.similarityScore ? 1 : undefined,
          rrfScore: matchedPrec?.similarityScore ? Number(matchedPrec.similarityScore.toFixed(4)) : 0.03,
          activeModalities: ['tfidf', 'bm25'],
          matchedKeywords: matchedPrec?.matchedTerms || []
        };

        precedentNode = {
          id: matchedPrec?.id || primarySupporting.id || 'SC-PRECEDENT',
          caseTitle: primarySupporting.caseTitle,
          citation: primarySupporting.citation,
          court: primarySupporting.court,
          relevanceClassification: matchedPrec?.relevanceClassification || 'Directly relevant',
          signals,
          officialSourceVerified: Boolean(primarySupporting.officialSourceVerified || matchedPrec?.officialSourceVerified),
          officialSourceUrl: primarySupporting.officialSourceUrl || matchedPrec?.officialSourceUrl
        };

        supportingPassage = this.getSupportingJudgmentPassage(
          primarySupporting.id || primarySupporting.caseTitle,
          primarySupporting.ratioPrinciple
        );
      } else {
        unresolvedRelationships.push('precedent_authority');
        unresolvedRelationships.push('judgment_passage');
      }

      // 5. OCR Uncertainty Gate & Epistemic Confidence
      // Warning threshold: page confidence < 75% (0.75)
      // Explicit uncertain tokens: [?word?]
      const isLowConfidencePage = sourcePassage.pageConfidence !== null &&
        sourcePassage.pageConfidence !== undefined &&
        sourcePassage.pageConfidence < 0.75;
      const hasUncertainTokens = sourcePassage.uncertainTokens && sourcePassage.uncertainTokens.length > 0;
      const isOcrUncertain = hasUncertainTokens || isLowConfidencePage;

      let overallTraceReliability: 'high_confidence' | 'moderate_confidence' | 'requires_verification';
      let ocrReliabilityCaveat: string | undefined;

      if (isOcrUncertain) {
        overallTraceReliability = 'requires_verification';
        if (hasUncertainTokens && isLowConfidencePage) {
          ocrReliabilityCaveat = `Factual premise relies on OCR text with ${Math.round((sourcePassage.pageConfidence || 0) * 100)}% page confidence (< 75% threshold) and contains ${sourcePassage.uncertainTokens.length} uncertain token(s): ${sourcePassage.uncertainTokens.map(t => `'${t}'`).join(', ')}. Verify against the original document.`;
        } else if (hasUncertainTokens) {
          ocrReliabilityCaveat = `Factual premise contains ${sourcePassage.uncertainTokens.length} uncertain OCR token(s): ${sourcePassage.uncertainTokens.map(t => `'${t}'`).join(', ')}. Verify against the original document.`;
        } else {
          ocrReliabilityCaveat = `Source page extracted via OCR with ${Math.round((sourcePassage.pageConfidence || 0) * 100)}% confidence (< 75% threshold). Verify factual premise against original document.`;
        }
        arg.ocrConfidenceWarning = ocrReliabilityCaveat;
      } else {
        arg.ocrConfidenceWarning = undefined;
        if (sourcePassage.attributionStatus === 'verified' && unresolvedRelationships.length === 0) {
          overallTraceReliability = 'high_confidence';
        } else {
          overallTraceReliability = 'moderate_confidence';
        }
      }

      arg.sourceTraceId = traceId;

      const node: IEvidenceTraceNode = {
        traceId,
        argumentId: arg.id,
        groundNumber: arg.groundNumber,
        sourcePassage,
        factAssertion: {
          statement: factStatement,
          classification: factClassification as any,
          factId,
          isContested
        },
        legalIssueId,
        legalIssueTitle,
        statutoryProvision,
        statutoryRegime,
        precedent: precedentNode,
        judgmentPassage: supportingPassage,
        draftSubmissionSnippet: arg.suggestedSubmission
          ? arg.suggestedSubmission.split('\n').filter(l => l.trim().length > 0).slice(0, 3).join(' ')
          : undefined,
        confidenceAssessment: {
          overallTraceReliability,
          ocrReliabilityCaveat,
          isOcrUncertain
        },
        unresolvedRelationships: unresolvedRelationships.length > 0 ? unresolvedRelationships : undefined
      };

      traceNodes.push(node);
    });

    return traceNodes;
  }
}
