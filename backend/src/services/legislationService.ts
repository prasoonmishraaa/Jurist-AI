export interface DetectedDateEntry {
  rawDate: string;
  parsedIso?: string;
  role: 'offence' | 'fir' | 'arrest' | 'remand' | 'filing' | 'unspecified';
  contextSnippet: string;
}

export interface ApplicableLawAssessment {
  isCriminalOrQuasiCriminal: boolean;
  regimeStatus: 'post_july_2024_new_codes' | 'pre_july_2024_legacy_codes' | 'transitional_mixed' | 'uncertain_missing_dates' | 'civil_special_statute';
  regimeSummary: string;
  detectedDates: DetectedDateEntry[];
  missingDates: string[];
  substantiveLaw: Array<{
    provision: string;
    statute: string;
    applicabilityNote: string;
  }>;
  proceduralLaw: Array<{
    provision: string;
    statute: string;
    applicabilityNote: string;
  }>;
  evidenceLaw?: {
    statute: string;
    applicabilityNote: string;
  };
  transitionalNotes: string[];
  verificationRequired: string[];
}

const COMMENCEMENT_DATE = new Date('2024-07-01T00:00:00Z');

const MONTH_MAP: Record<string, string> = {
  jan: '01', january: '01',
  feb: '02', february: '02',
  mar: '03', march: '03',
  apr: '04', april: '04',
  may: '05',
  jun: '06', june: '06',
  jul: '07', july: '07',
  aug: '08', august: '08',
  sep: '09', sept: '09', september: '09',
  oct: '10', october: '10',
  nov: '11', november: '11',
  dec: '12', december: '12'
};

export class LegislationService {
  private static tryParseIsoDate(raw: string): string | undefined {
    // Format: DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    const dmy = raw.match(/^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{4})$/);
    if (dmy) {
      const dd = dmy[1].padStart(2, '0');
      const mm = dmy[2].padStart(2, '0');
      const yyyy = dmy[3];
      if (parseInt(mm, 10) >= 1 && parseInt(mm, 10) <= 12 && parseInt(dd, 10) >= 1 && parseInt(dd, 10) <= 31) {
        return `${yyyy}-${mm}-${dd}`;
      }
    }

    // Format: YYYY-MM-DD
    const ymd = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (ymd) return raw;

    // Format: 12 July 2024 or 12th July, 2024
    const textDate = raw.match(/(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})/);
    if (textDate) {
      const dd = textDate[1].padStart(2, '0');
      const mKey = textDate[2].toLowerCase();
      const mm = MONTH_MAP[mKey];
      const yyyy = textDate[3];
      if (mm) return `${yyyy}-${mm}-${dd}`;
    }

    // Format: July 12, 2024
    const mdyText = raw.match(/([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})/);
    if (mdyText) {
      const mKey = mdyText[1].toLowerCase();
      const mm = MONTH_MAP[mKey];
      const dd = mdyText[2].padStart(2, '0');
      const yyyy = mdyText[3];
      if (mm) return `${yyyy}-${mm}-${dd}`;
    }

    return undefined;
  }

  public static extractDatesWithContext(text: string): DetectedDateEntry[] {
    const entries: DetectedDateEntry[] = [];
    const seen = new Set<string>();

    const dateRegex =
      /\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b/gi;

    let match: RegExpExecArray | null;
    while ((match = dateRegex.exec(text)) !== null) {
      const rawDate = match[0].trim();
      const start = Math.max(0, match.index - 65);
      const end = Math.min(text.length, match.index + rawDate.length + 65);
      const contextSnippet = text.slice(start, end).replace(/\s+/g, ' ').trim();

      // Prioritize tight local clause before the date so adjacent clauses do not shadow role detection
      const immediateBefore = text.slice(Math.max(0, match.index - 45), match.index).toLowerCase();
      const immediateAfter = text.slice(match.index + rawDate.length, Math.min(text.length, match.index + rawDate.length + 25)).toLowerCase();
      const localClause = `${immediateBefore} ${immediateAfter}`;

      let role: DetectedDateEntry['role'] = 'unspecified';
      if (/\b(?:arrest|arrested|apprehend|detained|custody)\b/.test(localClause)) role = 'arrest';
      else if (/\b(?:fir|first information report|registered|lodged)\b/.test(localClause)) role = 'fir';
      else if (/\b(?:offence|incident|allegedly|cheated|committed|transaction)\b/.test(localClause)) role = 'offence';
      else if (/\b(?:remand|magistrate|produced)\b/.test(localClause)) role = 'remand';
      else if (/\b(?:filed|petition|suit|complaint|application)\b/.test(localClause)) role = 'filing';

      const key = `${rawDate}|${role}`;
      if (!seen.has(key)) {
        seen.add(key);
        entries.push({
          rawDate,
          parsedIso: this.tryParseIsoDate(rawDate),
          role,
          contextSnippet
        });
      }
    }

    return entries;
  }

  public static assessApplicableLegislation(text: string, category: string): ApplicableLawAssessment {
    const textLower = text.toLowerCase();
    const detectedDates = this.extractDatesWithContext(text);

    const hasCriminalSignals =
      category === 'Criminal Law' ||
      /\b(?:arrest|fir|police|remand|bail|custody|cheat|cheating|420|318|498a|482|528|crpc|bnss|ipc|bns|accused|magistrate|detention|quash)\b/i.test(text);

    const hasCheatingSignals = /\b(?:cheat|cheating|420|318|fraud|dishonest inducement)\b/i.test(text);
    const has498aSignals = /\b(?:498a|498-a|85 bns|dowry|cruelty by husband|matrimonial cruelty)\b/i.test(text);
    const hasArrestSignals = /\b(?:arrest|arrested|custody|detained|apprehended|remand|grounds of arrest)\b/i.test(text);
    const hasChequeSignals = /\b(?:cheque|138|139|negotiable instrument|dishonour)\b/i.test(text);
    const hasArbitrationSignals = /\b(?:arbitrat|arbitral|section 8|section 11|section 34)\b/i.test(text);
    const hasPrivacySignals = /\b(?:privacy|surveillance|biometric|interception|telemetry|aadhaar)\b/i.test(text);

    const missingDates: string[] = [];
    const transitionalNotes: string[] = [];
    const verificationRequired: string[] = [];
    const substantiveLaw: ApplicableLawAssessment['substantiveLaw'] = [];
    const proceduralLaw: ApplicableLawAssessment['proceduralLaw'] = [];

    if (!hasCriminalSignals) {
      if (hasChequeSignals) {
        substantiveLaw.push({
          provision: 'Section 138 & 139, Negotiable Instruments Act, 1881',
          statute: 'Negotiable Instruments Act, 1881',
          applicabilityNote: 'Governs dishonour of cheques for insufficiency of funds and the rebuttable presumption of legally enforceable debt.'
        });
        proceduralLaw.push({
          provision: 'Section 142 & 143A, Negotiable Instruments Act, 1881 (read with CrPC / BNSS summary trial)',
          statute: 'NI Act, 1881 / CrPC or BNSS',
          applicabilityNote: 'Statutory limitation (notice within 30 days, complaint after 15 days) must be verified against dishonour memo and demand notice dates.'
        });
      }
      if (hasArbitrationSignals) {
        substantiveLaw.push({
          provision: 'Sections 7, 8, 11 & 34, Arbitration and Conciliation Act, 1996',
          statute: 'Arbitration and Conciliation Act, 1996',
          applicabilityNote: 'Governs reference to arbitration, appointment of arbitrators, and narrow challenge thresholds.'
        });
      }
      if (hasPrivacySignals || /\b(?:article 14|article 19|article 21|fundamental right|writ|226|32)\b/i.test(text)) {
        substantiveLaw.push({
          provision: 'Articles 14, 19 & 21, Constitution of India',
          statute: 'Constitution of India',
          applicabilityNote: 'Governs fundamental rights scrutiny, non-arbitrariness, proportionality, and constitutional writ remedies.'
        });
      }

      if (detectedDates.length === 0) {
        missingDates.push('Dates of key contractual events, cause of action, and filing (needed for limitation analysis).');
      }

      return {
        isCriminalOrQuasiCriminal: false,
        regimeStatus: 'civil_special_statute',
        regimeSummary: 'Governed by substantive Constitutional, Civil, or Special Enactments (subject to cause-of-action limitation dates).',
        detectedDates,
        missingDates,
        substantiveLaw,
        proceduralLaw,
        transitionalNotes,
        verificationRequired
      };
    }

    // Criminal date-aware logic (1 July 2024 cutoff)
    const hasOffenceDate = detectedDates.some(d => d.role === 'offence');
    const hasFirDate = detectedDates.some(d => d.role === 'fir');
    const hasArrestDate = detectedDates.some(d => d.role === 'arrest' || d.role === 'remand');

    if (!hasOffenceDate) missingDates.push('Date of alleged offence (determines IPC 1860 vs. BNS 2023 applicability).');
    if (!hasFirDate) missingDates.push('Date of FIR / complaint registration (determines CrPC 1973 vs. BNSS 2023 & Section 531 BNSS savings scope).');
    if (hasArrestSignals && !hasArrestDate) {
      missingDates.push('Date and time of arrest and Magisterial remand production (determines procedural law & Article 22(2) compliance).');
    }

    const parsedTimestamps = detectedDates
      .map(d => (d.parsedIso ? { role: d.role, date: new Date(`${d.parsedIso}T00:00:00Z`) } : null))
      .filter((x): x is { role: DetectedDateEntry['role']; date: Date } => x !== null && !isNaN(x.date.getTime()));

    const allPostCommencement = parsedTimestamps.length > 0 && parsedTimestamps.every(x => x.date >= COMMENCEMENT_DATE);
    const allPreCommencement = parsedTimestamps.length > 0 && parsedTimestamps.every(x => x.date < COMMENCEMENT_DATE);
    const mixedDates = parsedTimestamps.length > 1 && !allPostCommencement && !allPreCommencement;

    const userMentionsBNSS = /\b(?:bnss|bharatiya nagarik|bns|bharatiya nyaya|bsa|bharatiya sakshya)\b/i.test(text);
    const userMentionsCrPC = /\b(?:crpc|cr\.p\.c|ipc|i\.p\.c|41a|420|498a|482)\b/i.test(text);

    let regimeStatus: ApplicableLawAssessment['regimeStatus'] = 'uncertain_missing_dates';
    let regimeSummary = '';

    if (allPostCommencement && hasOffenceDate && hasFirDate) {
      regimeStatus = 'post_july_2024_new_codes';
      regimeSummary = 'All extracted offence, FIR, and procedural dates fall on or after 1 July 2024: BNS 2023, BNSS 2023, and BSA 2023 govern substantive, procedural, and evidentiary questions.';
    } else if (allPostCommencement && hasFirDate) {
      regimeStatus = 'post_july_2024_new_codes';
      regimeSummary = 'FIR and arrest dates fall on or after 1 July 2024: BNSS 2023 governs arrest, remand, and trial procedure (verify exact offence date regarding IPC vs. BNS substantive applicability under Art. 20(1)).';
    } else if (allPreCommencement && (hasFirDate || hasOffenceDate)) {
      regimeStatus = 'pre_july_2024_legacy_codes';
      regimeSummary = 'Extracted offence/FIR dates precede 1 July 2024: IPC 1860 governs substantive liability and CrPC 1973 continues to apply to pre-commencement investigations/proceedings under Section 531 BNSS.';
    } else if (mixedDates) {
      regimeStatus = 'transitional_mixed';
      regimeSummary = 'Facts straddle the 1 July 2024 commencement date. Substantive offence law (date of offence) and procedural safeguards (FIR/inquiry/arrest timing under Section 531 BNSS) require separate analysis.';
    } else if (allPostCommencement) {
      regimeStatus = 'uncertain_missing_dates';
      regimeSummary = 'A post-1 July 2024 date was detected, indicating BNSS 2023 likely governs arrest/procedure if the FIR was registered on/after 1 July 2024, but missing offence/FIR dates prevent confirming whether S. 531 BNSS savings preserve CrPC/IPC.';
    } else if (userMentionsBNSS && !userMentionsCrPC) {
      regimeStatus = 'uncertain_missing_dates';
      regimeSummary = 'Post-1 July 2024 codes referenced, but exact dates of offence, FIR registration, and arrest are missing; both statutory frameworks must be verified.';
    } else {
      regimeStatus = 'uncertain_missing_dates';
      regimeSummary = 'Critical dates (offence, FIR, and arrest/action dates) are missing. On 1 July 2024, BNS 2023, BNSS 2023, and BSA 2023 commenced; governing code cannot be assumed without verifying dates.';
    }

    // Populate Substantive Law accurately (NO 498A unless 498A/dowry/cruelty mentioned!)
    if (hasCheatingSignals) {
      if (regimeStatus === 'post_july_2024_new_codes') {
        substantiveLaw.push({
          provision: 'Section 318, Bharatiya Nyaya Sanhita, 2023 (Cheating)',
          statute: 'Bharatiya Nyaya Sanhita, 2023',
          applicabilityNote: 'Replaces Section 415/420 IPC for offences committed on or after 1 July 2024. Note maximum punishment thresholds (e.g., S. 318(2) up to 3 years; S. 318(4) cheating & dishonestly inducing delivery of property up to 7 years).'
        });
      } else if (regimeStatus === 'pre_july_2024_legacy_codes') {
        substantiveLaw.push({
          provision: 'Section 415 & 420, Indian Penal Code, 1860',
          statute: 'Indian Penal Code, 1860',
          applicabilityNote: 'Applies to offences committed before 1 July 2024. Punishable with imprisonment up to 7 years and fine.'
        });
      } else {
        substantiveLaw.push({
          provision: 'Section 415/420 IPC (pre-01.07.2024) OR Section 318 BNS, 2023 (on/after 01.07.2024)',
          statute: 'IPC, 1860 / BNS, 2023 (Date-Dependent)',
          applicabilityNote: 'Exact offence date must be verified to identify whether IPC S. 420 or BNS S. 318 governs. Both carry maximum imprisonment up to 7 years for inducing delivery of property, attracting pre-arrest notice rules.'
        });
      }
    }

    if (has498aSignals) {
      substantiveLaw.push({
        provision: regimeStatus === 'post_july_2024_new_codes'
          ? 'Section 85 & 86, Bharatiya Nyaya Sanhita, 2023'
          : 'Section 498A IPC (pre-01.07.2024) / Section 85 BNS (from 01.07.2024)',
        statute: regimeStatus === 'post_july_2024_new_codes' ? 'BNS, 2023' : 'IPC / BNS (Date-Dependent)',
        applicabilityNote: 'Specifically raised only because cruelty by husband/relatives is indicated in the input.'
      });
    }

    // Constitutional & Procedural Safeguards (Strictly separated pre vs post 1 July 2024!)
    substantiveLaw.push({
      provision: 'Articles 21 & 22(1)–(2), Constitution of India',
      statute: 'Constitution of India',
      applicabilityNote: 'Irrespective of IPC/BNS or CrPC/BNSS, Article 21 (personal liberty) and Article 22 (mandatory grounds of arrest communication, counsel consultation, and 24-hour Magistrate production) apply without exception.'
    });

    if (hasArrestSignals || /\b(?:41a|notice|35 bnss|bail|remand)\b/i.test(text)) {
      if (regimeStatus === 'post_july_2024_new_codes') {
        proceduralLaw.push({
          provision: 'Section 35, Bharatiya Nagarik Suraksha Sanhita, 2023',
          statute: 'BNSS, 2023',
          applicabilityNote: 'Consolidates CrPC Ss. 41 & 41A for post-01.07.2024 proceedings: S. 35(1)(b) restricts warrantless arrest for offences punishable up to 7 years (whether less than 7 years or extending to 7 years) to cases where the officer is satisfied that arrest is necessary for one or more of the five alternative statutory purposes under S. 35(1)(b)(ii)(a)-(e) (preventing further offences, proper investigation, preventing evidence tampering, preventing witness inducement/threat, or ensuring court presence) with reasons recorded in writing; S. 35(3) mandates notice of appearance where arrest is not required under sub-section (1); S. 35(7) requires prior DSP permission for offences punishable with imprisonment of less than 3 years or where the person is infirm or above 60 years of age.'
        });
        proceduralLaw.push({
          provision: 'Sections 47 & 48, BNSS, 2023',
          statute: 'BNSS, 2023',
          applicabilityNote: 'S. 47 requires communicating full particulars and grounds of arrest; S. 48 mandates informing nominated friend, relative, or designated police officer.'
        });
        proceduralLaw.push({
          provision: 'Sections 58 & 187, BNSS, 2023',
          statute: 'BNSS, 2023',
          applicabilityNote: 'Requires production before Magistrate within 24 hours (S. 58) and reasoned Magisterial scrutiny of remand necessity (S. 187).'
        });
      } else if (regimeStatus === 'pre_july_2024_legacy_codes') {
        proceduralLaw.push({
          provision: 'Sections 41 & 41A, Code of Criminal Procedure, 1973',
          statute: 'CrPC, 1973',
          applicabilityNote: 'Pre-01.07.2024 arrest safeguards preventing automatic arrest and mandating notice of appearance in offences punishable up to 7 years.'
        });
        proceduralLaw.push({
          provision: 'Sections 41B, 50 & 50A, CrPC, 1973',
          statute: 'CrPC, 1973',
          applicabilityNote: 'Mandates attested arrest memo (S. 41B), communication of grounds of arrest (S. 50), and relative/friend intimation (S. 50A).'
        });
        proceduralLaw.push({
          provision: 'Sections 57 & 167, CrPC, 1973',
          statute: 'CrPC, 1973',
          applicabilityNote: 'Requires 24-hour production before Magistrate (S. 57) and judicial scrutiny before remand detention (S. 167).'
        });
      } else {
        proceduralLaw.push({
          provision: 'Section 35 BNSS, 2023 (from 01.07.2024) OR Sections 41 & 41A CrPC, 1973 (prior FIR/savings)',
          statute: 'BNSS, 2023 / CrPC, 1973 (Date Verification Required)',
          applicabilityNote: 'Do not assume CrPC S. 41/41A automatically: verify FIR and arrest dates. Post-commencement proceedings are governed by Section 35 BNSS (which restricts arrest for offences punishable up to 7 years under S. 35(1)(b) to one or more alternative statutory necessity grounds, mandates notice of appearance under S. 35(3) when arrest is unnecessary, and adds S. 35(7) DSP sanction for offences under 3 years).'
        });
        proceduralLaw.push({
          provision: 'Sections 47 & 48 BNSS, 2023 OR Sections 50 & 50A CrPC, 1973 (with Art. 22(1) Constitution)',
          statute: 'BNSS, 2023 / CrPC, 1973',
          applicabilityNote: 'Mandatory communication of grounds of arrest directly to the arrestee (S. 47 BNSS / S. 50 CrPC) is constitutionally distinct from informing a nominated relative/friend (S. 48 BNSS / S. 50A CrPC).'
        });
      }
    }

    if (/\b(?:quash|482|528|abuse of process)\b/i.test(text)) {
      proceduralLaw.push({
        provision: regimeStatus === 'post_july_2024_new_codes'
          ? 'Section 528 BNSS, 2023 / Article 226 Constitution'
          : 'Section 482 CrPC (pre-01.07.2024) or Section 528 BNSS (from 01.07.2024) / Article 226',
        statute: 'BNSS / CrPC / Constitution',
        applicabilityNote: 'Inherent jurisdiction of the High Court to prevent abuse of process; High Court transitional rules apply based on filing/FIR date under S. 531 BNSS.'
      });
    }

    const evidenceLaw = {
      statute: regimeStatus === 'post_july_2024_new_codes'
        ? 'Bharatiya Sakshya Adhiniyam, 2023 (BSA) (verify Section 63 for electronic records)'
        : regimeStatus === 'pre_july_2024_legacy_codes'
          ? 'Indian Evidence Act, 1872 (verify Section 65B for electronic records)'
          : 'Indian Evidence Act, 1872 OR Bharatiya Sakshya Adhiniyam, 2023 (Date-Dependent)',
      applicabilityNote: 'Electronic proof (CCTV footage, call records, arrest intimation logs) requires certification under S. 63 BSA / S. 65B Evidence Act depending on trial/proceeding regime.'
    };

    transitionalNotes.push(
      'Section 531 BNSS, 2023 (Repeal & Savings) preserves CrPC application to trials, appeals, applications, and inquiries pending immediately before 1 July 2024; judicial interpretation across High Courts has varied where FIR preceded 01.07.2024 but subsequent steps occurred after 01.07.2024.'
    );
    transitionalNotes.push(
      'Section 358 BNS, 2023 (Repeal & Savings) maintains prior substantive criminal liabilities for offences committed before 1 July 2024 under the IPC, 1860 (read with Article 20(1) protection against ex post facto harsher penalties).'
    );

    if (regimeStatus !== 'pre_july_2024_legacy_codes' && userMentionsCrPC && !userMentionsBNSS) {
      verificationRequired.push(
        'Input references IPC/CrPC terminology while offence/FIR/arrest dates are missing or recent: verify exact FIR registration date to avoid misapplying CrPC/IPC if BNS/BNSS commenced before the FIR.'
      );
    }

    if (missingDates.length > 0) {
      verificationRequired.push(
        'Obtain exact FIR registration date, date of alleged offence, and arrest memo timestamp before finalizing statutory citations in pleadings.'
      );
    }

    return {
      isCriminalOrQuasiCriminal: true,
      regimeStatus,
      regimeSummary,
      detectedDates,
      missingDates,
      substantiveLaw,
      proceduralLaw,
      evidenceLaw,
      transitionalNotes,
      verificationRequired
    };
  }
}
