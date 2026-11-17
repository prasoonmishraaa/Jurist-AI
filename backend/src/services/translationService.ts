import axios from 'axios';
import { logger } from '../utils/logger';

export interface LanguageDetectionResult {
  detectedLanguage: 'en' | 'hi' | 'mixed';
  primaryLanguage: 'en' | 'hi';
  devanagariCount: number;
  latinCount: number;
  devanagariRatio: number;
  latinRatio: number;
  isMixed: boolean;
  confidence: number;
}

export interface TranslationOptions {
  sourceLanguage?: 'en' | 'hi' | 'auto';
  targetLanguage: 'en' | 'hi';
  consentExternalService?: boolean;
  preserveCitations?: boolean;
}

export interface TranslationResult {
  originalText: string;
  translatedText: string;
  sourceLanguage: 'en' | 'hi';
  targetLanguage: 'en' | 'hi';
  detectedLanguage: 'en' | 'hi' | 'mixed';
  languageMetrics: {
    devanagariRatio: number;
    latinRatio: number;
    isMixed: boolean;
  };
  providerUsed: 'local_legal' | 'google_cloud';
  isMachineGenerated: true;
  disclaimer: string;
  preservedCitationsCount: number;
  paragraphCount: number;
  characterCount: number;
}

// Curated bidirectional Indian legal phrase dictionary
const EN_TO_HI_PHRASES: [RegExp, string][] = [
  // Court & Jurisdiction Headings
  [/\bIN THE SUPREME COURT OF INDIA\b/gi, 'भारत के सर्वोच्च न्यायालय में'],
  [/\bIN THE HIGH COURT OF DELHI\b/gi, 'दिल्ली उच्च न्यायालय में'],
  [/\bIN THE HIGH COURT OF BOMBAY\b/gi, 'बॉम्बे उच्च न्यायालय में'],
  [/\bIN THE HIGH COURT OF JUDICATURE AT ALLAHABAD\b/gi, 'इलाहाबाद उच्च न्यायालय में'],
  [/\bIN THE HIGH COURT OF JUDICATURE AT MADRAS\b/gi, 'मद्रास उच्च न्यायालय में'],
  [/\bIN THE HIGH COURT OF CALCUTTA\b/gi, 'कलकत्ता उच्च न्यायालय में'],
  [/\bCRIMINAL APPELLATE JURISDICTION\b/gi, 'आपराधिक अपीलीय क्षेत्राधिकार'],
  [/\bCIVIL APPELLATE JURISDICTION\b/gi, 'दीवानी अपीलीय क्षेत्राधिकार'],
  [/\bSPECIAL LEAVE PETITION\s*\((?:CRL|CIVIL)\)?/gi, 'विशेष अनुमति याचिका (एसएलपी)'],
  [/\bSPECIAL LEAVE PETITION\b/gi, 'विशेष अनुमति याचिका'],
  [/\bWRIT PETITION\s*\((?:CRL|CIVIL)\)?/gi, 'रिट याचिका'],
  [/\bWRIT PETITION\b/gi, 'रिट याचिका'],
  [/\bHABEAS CORPUS\b/gi, 'बंदी प्रत्यक्षीकरण (Habeas Corpus)'],
  [/\bMANDAMUS\b/gi, 'परमादेश (Mandamus)'],
  [/\bCERTIORARI\b/gi, 'उत्प्रेषण (Certiorari)'],
  [/\bQUO WARRANTO\b/gi, 'अधिकार पृच्छा (Quo Warranto)'],
  [/\bRECORD OF PROCEEDINGS\b/gi, 'कार्यवाही का अभिलेख'],

  // Parties & Institutions
  [/\bSUPREME COURT OF INDIA\b/gi, 'भारत का सर्वोच्च न्यायालय'],
  [/\bHIGH COURT\b/gi, 'उच्च न्यायालय'],
  [/\bSESSIONS COURT\b/gi, 'सत्र न्यायालय'],
  [/\bMAGISTRATE COURT\b/gi, 'मजिस्ट्रेट न्यायालय'],
  [/\bJUDICIAL MAGISTRATE FIRST CLASS\b/gi, 'प्रथम श्रेणी न्यायिक मजिस्ट्रेट'],
  [/\bCHIEF METROPOLITAN MAGISTRATE\b/gi, 'मुख्य मेट्रोपॉलिटन मजिस्ट्रेट'],
  [/\bNATIONAL COMPANY LAW TRIBUNAL\b/gi, 'राष्ट्रीय कंपनी विधि अधिकरण (NCLT)'],
  [/\bUNION OF INDIA\b/gi, 'भारत संघ'],
  [/\bSTATE OF HARYANA\b/gi, 'हरियाणा राज्य'],
  [/\bSTATE OF MAHARASHTRA\b/gi, 'महाराष्ट्र राज्य'],
  [/\bSTATE OF UTTAR PRADESH\b/gi, 'उत्तर प्रदेश राज्य'],
  [/\bSTATE OF WEST BENGAL\b/gi, 'पश्चिम बंगाल राज्य'],
  [/\bSTATE OF TAMIL NADU\b/gi, 'तमिलनाडु राज्य'],
  [/\bNCT OF DELHI\b/gi, 'राष्ट्रीय राजधानी क्षेत्र दिल्ली'],
  [/\bSTATE PROSECUTION\b/gi, 'राज्य अभियोजन'],
  [/\bPETITIONER\b/gi, 'याचिकाकर्ता'],
  [/\bRESPONDENT\b/gi, 'प्रत्यर्थी'],
  [/\bAPPELLANT\b/gi, 'अपीलकर्ता'],
  [/\bACCUSED\b/gi, 'अभियुक्त / आरोपी'],
  [/\bCOMPLAINANT\b/gi, 'शिकायतकर्ता'],
  [/\bINFORMANT\b/gi, 'सूचनादाता / मुखबिर'],
  [/\bINVESTIGATING OFFICER\b/gi, 'जांच अधिकारी (आईओ)'],
  [/\bLEARNED SENIOR COUNSEL\b/gi, 'विद्वान वरिष्ठ अधिवक्ता'],
  [/\bLEARNED COUNSEL\b/gi, 'विद्वान अधिवक्ता'],
  [/\bLEARNED ADVOCATE\b/gi, 'विद्वान अधिवक्ता'],
  [/\bHON'BLE MR\. JUSTICE\b/gi, 'माननीय न्यायमूर्ति'],
  [/\bHON'BLE MRS\. JUSTICE\b/gi, 'माननीय न्यायमूर्ति'],
  [/\bHON'BLE MS\. JUSTICE\b/gi, 'माननीय न्यायमूर्ति'],
  [/\bHON'BLE JUSTICE\b/gi, 'माननीय न्यायमूर्ति'],
  [/\bHON'BLE COURT\b/gi, 'माननीय न्यायालय'],

  // Procedural Terminology & Dispositions
  [/\bAPPEAL ALLOWED\b/gi, 'अपील स्वीकार की गई'],
  [/\bAPPEAL DISMISSED\b/gi, 'अपील खारिज की गई'],
  [/\bPETITION ALLOWED\b/gi, 'याचिका स्वीकार की गई'],
  [/\bPETITION DISMISSED\b/gi, 'याचिका खारिज की गई'],
  [/\bLEAVE GRANTED\b/gi, 'विशेष अनुमति प्रदान की गई'],
  [/\bORDERED ACCORDINGLY\b/gi, 'तदनुसार आदेशित किया जाता है'],
  [/\bHEARD LEARNED COUNSEL FOR THE PARTIES\b/gi, 'पक्षकारों के विद्वान अधिवक्ताओं को सुना गया'],
  [/\bHEARD LEARNED COUNSEL\b/gi, 'विद्वान अधिवक्ता को सुना गया'],
  [/\bPERUSED THE RECORD\b/gi, 'अभिलेख का ध्यानपूर्वक अवलोकन किया'],
  [/\bQUASHED AND SET ASIDE\b/gi, 'निरस्त एवं अपास्त किया गया'],
  [/\bSET ASIDE\b/gi, 'अपास्त किया गया'],
  [/\bDISPOSED OF\b/gi, 'निस्तारित किया गया'],
  [/\bPENDING ADJUDICATION\b/gi, 'न्यायनिर्णयन हेतु लंबित'],
  [/\bPRIMA FACIE\b/gi, 'प्रथम दृष्टया (Prima Facie)'],
  [/\bRATIO DECIDENDI\b/gi, 'निर्णयाधार (Ratio Decidendi)'],
  [/\bOBITER DICTUM\b/gi, 'प्रासंगिक कथन (Obiter Dictum)'],
  [/\bOBITER DICTA\b/gi, 'प्रासंगिक कथन (Obiter Dicta)'],
  [/\bSTATUS QUO\b/gi, 'यथास्थिति (Status Quo)'],
  [/\bIN LIMINE\b/gi, 'प्रारंभिक स्तर पर (In Limine)'],
  [/\bINTER ALIA\b/gi, 'अन्य बातों के साथ-साथ (Inter Alia)'],

  // Statutory Acts & Codes
  [/\bINDIAN PENAL CODE(?:,\s*1860)?\b/gi, 'भारतीय दंड संहिता (आईपीसी)'],
  [/\bCODE OF CRIMINAL PROCEDURE(?:,\s*1973)?\b/gi, 'दंड प्रक्रिया संहिता (सीआरपीसी)'],
  [/\bINDIAN EVIDENCE ACT(?:,\s*1872)?\b/gi, 'भारतीय साक्ष्य अधिनियम (आईईए)'],
  [/\bBHARATIYA NYAYA SANHITA(?:,\s*2023)?\b/gi, 'भारतीय न्याय संहिता (बीएनएस)'],
  [/\bBHARATIYA NAGARIK SURAKSHA SANHITA(?:,\s*2023)?\b/gi, 'भारतीय नागरिक सुरक्षा संहिता (बीएनएसएस)'],
  [/\bBHARATIYA SAKSHYA ADHINIYAM(?:,\s*2023)?\b/gi, 'भारतीय साक्ष्य अधिनियम (बीएसए)'],
  [/\bNEGOTIABLE INSTRUMENTS ACT(?:,\s*1881)?\b/gi, 'परक्राम्य लिखत अधिनियम (एनआई एक्ट)'],
  [/\bARBITRATION AND CONCILIATION ACT(?:,\s*1996)?\b/gi, 'मध्यस्थता और सुलह अधिनियम, 1996'],
  [/\bCONSTITUTION OF INDIA\b/gi, 'भारत का संविधान'],

  // Criminal Process & Civil Rights
  [/\bFIRST INFORMATION REPORT\b/gi, 'प्रथम सूचना रिपोर्ट (प्राथमिकी)'],
  [/\bGROUNDS OF ARREST\b/gi, 'गिरफ्तारी के आधार'],
  [/\bWRITTEN GROUNDS OF ARREST\b/gi, 'गिरफ्तारी के लिखित आधार'],
  [/\bARREST MEMO\b/gi, 'गिरफ्तारी मेमो'],
  [/\bPRE-ARREST NOTICE\b/gi, 'गिरफ्तारी पूर्व नोटिस'],
  [/\bANTICIPATORY BAIL\b/gi, 'अग्रिम जमानत'],
  [/\bREGULAR BAIL\b/gi, 'नियमित जमानत'],
  [/\bINTERIM BAIL\b/gi, 'अंतरिम जमानत'],
  [/\bSTATUTORY BAIL\b/gi, 'डिफ़ॉल्ट / वैधानिक जमानत'],
  [/\bJUDICIAL CUSTODY\b/gi, 'न्यायिक हिरासत'],
  [/\bPOLICE CUSTODY\b/gi, 'पुलिस हिरासत'],
  [/\bPOLICE REMAND\b/gi, 'पुलिस रिमांड'],
  [/\bUNLAWFUL ARREST\b/gi, 'गैरकानूनी गिरफ्तारी'],
  [/\bPERSONAL LIBERTY\b/gi, 'व्यक्तिगत स्वतंत्रता'],
  [/\bFUNDAMENTAL RIGHTS\b/gi, 'मौलिक अधिकार'],
  [/\bCHARGE SHEET\b/gi, 'आरोप पत्र (चार्जशीट)'],
  [/\bCOGNIZANCE\b/gi, 'संज्ञान'],
  [/\bIMPUGNED JUDGMENT\b/gi, 'आक्षेपित निर्णय'],
  [/\bIMPUGNED ORDER\b/gi, 'आक्षेपित आदेश'],

  // Common Legal Connectives & Phrases
  [/\bIN ACCORDANCE WITH LAW\b/gi, 'विधि के अनुसार'],
  [/\bPURSUANT TO\b/gi, 'के अनुसरण में'],
  [/\bWITHOUT PREJUDICE\b/gi, 'बिना किसी पूर्वाग्रह के'],
  [/\bIN THE FACTS AND CIRCUMSTANCES OF THE CASE\b/gi, 'मामले के तथ्यों एवं परिस्थितियों में'],
  [/\bHAVING REGARD TO\b/gi, 'को ध्यान में रखते हुए'],
  [/\bIN VIEW OF THE ABOVE\b/gi, 'उपरोक्त के आलोक में'],
  [/\bIN VIEW OF THE FOREGOING\b/gi, 'पूर्वोक्त के आलोक में'],
  [/\bSUBMITTED THAT\b/gi, 'निवेदन किया कि'],
  [/\bCONTENDED THAT\b/gi, 'तर्क दिया कि'],
  [/\bIT IS SETTLED LAW THAT\b/gi, 'यह सुस्थापित विधि है कि'],
  [/\bTHERE IS NO MERIT IN\b/gi, 'इसमें कोई सार नहीं है'],
  [/\bNO MERIT\b/gi, 'कोई सार नहीं'],
  [/\bNOTICE ISSUED\b/gi, 'नोटिस जारी किया गया'],
  [/\bINTERIM RELIEF\b/gi, 'अंतरिम राहत'],
  [/\bSTAY OF PROCEEDINGS\b/gi, 'कार्यवाही पर रोक (स्टे)'],
  [/\bINTERIM PROTECTION\b/gi, 'अंतरिम संरक्षण']
];

const HI_TO_EN_PHRASES: [RegExp, string][] = [
  // Court & Jurisdiction
  [/भारत के सर्वोच्च न्यायालय में/g, 'IN THE SUPREME COURT OF INDIA'],
  [/भारत का सर्वोच्च न्यायालय/g, 'Supreme Court of India'],
  [/उच्च न्यायालय/g, 'High Court'],
  [/सत्र न्यायालय/g, 'Sessions Court'],
  [/मजिस्ट्रेट न्यायालय/g, 'Magistrate Court'],
  [/न्यायिक मजिस्ट्रेट/g, 'Judicial Magistrate'],
  [/राष्ट्रीय कंपनी विधि अधिकरण/g, 'National Company Law Tribunal (NCLT)'],
  [/आपराधिक अपीलीय क्षेत्राधिकार/g, 'CRIMINAL APPELLATE JURISDICTION'],
  [/दीवानी अपीलीय क्षेत्राधिकार/g, 'CIVIL APPELLATE JURISDICTION'],
  [/विशेष अनुमति याचिका/g, 'Special Leave Petition (SLP)'],
  [/रिट याचिका/g, 'Writ Petition'],
  [/बंदी प्रत्यक्षीकरण/g, 'Habeas Corpus'],
  [/परमादेश/g, 'Mandamus'],
  [/उत्प्रेषण/g, 'Certiorari'],

  // Parties & Institutions
  [/भारत संघ/g, 'Union of India'],
  [/हरियाणा राज्य/g, 'State of Haryana'],
  [/महाराष्ट्र राज्य/g, 'State of Maharashtra'],
  [/उत्तर प्रदेश राज्य/g, 'State of Uttar Pradesh'],
  [/याचिकाकर्ता/g, 'Petitioner'],
  [/प्रत्यर्थी/g, 'Respondent'],
  [/अपीलकर्ता/g, 'Appellant'],
  [/अभियुक्त(?:\s*\/\s*आरोपी)?/g, 'Accused'],
  [/शिकायतकर्ता/g, 'Complainant'],
  [/जांच अधिकारी/g, 'Investigating Officer'],
  [/विद्वान वरिष्ठ अधिवक्ता/g, 'Learned Senior Counsel'],
  [/विद्वान अधिवक्ता/g, 'Learned Counsel'],
  [/माननीय न्यायमूर्ति/g, "Hon'ble Justice"],
  [/माननीय न्यायालय/g, "Hon'ble Court"],

  // Procedural Terminology & Dispositions
  [/अपील स्वीकार की गई/g, 'Appeal allowed'],
  [/अपील खारिज की गई/g, 'Appeal dismissed'],
  [/याचिका स्वीकार की गई/g, 'Petition allowed'],
  [/याचिका खारिज की गई/g, 'Petition dismissed'],
  [/विशेष अनुमति प्रदान की गई/g, 'Leave granted'],
  [/तदनुसार आदेशित किया जाता है/g, 'Ordered accordingly'],
  [/पक्षकारों के विद्वान अधिवक्ताओं को सुना गया/g, 'Heard learned counsel for the parties'],
  [/विद्वान अधिवक्ता को सुना गया/g, 'Heard learned counsel'],
  [/अभिलेख का ध्यानपूर्वक अवलोकन किया/g, 'Perused the record'],
  [/निरस्त एवं अपास्त किया गया/g, 'Quashed and set aside'],
  [/अपास्त किया गया/g, 'Set aside'],
  [/निस्तारित किया गया/g, 'Disposed of'],
  [/प्रथम दृष्टया/g, 'Prima facie'],
  [/निर्णयाधार/g, 'Ratio decidendi'],
  [/प्रासंगिक कथन/g, 'Obiter dictum'],
  [/यथास्थिति/g, 'Status quo'],

  // Statutory Acts & Codes
  [/भारतीय दंड संहिता/g, 'Indian Penal Code (IPC)'],
  [/दंड प्रक्रिया संहिता/g, 'Code of Criminal Procedure (CrPC)'],
  [/भारतीय साक्ष्य अधिनियम/g, 'Indian Evidence Act (IEA)'],
  [/भारतीय न्याय संहिता/g, 'Bharatiya Nyaya Sanhita (BNS)'],
  [/भारतीय नागरिक सुरक्षा संहिता/g, 'Bharatiya Nagarik Suraksha Sanhita (BNSS)'],
  [/परक्राम्य लिखत अधिनियम/g, 'Negotiable Instruments Act'],
  [/मध्यस्थता और सुलह अधिनियम/g, 'Arbitration and Conciliation Act'],
  [/भारत का संविधान/g, 'Constitution of India'],
  [/प्रथम सूचना रिपोर्ट(?:\s*\(प्राथमिकी\))?/g, 'First Information Report (FIR)'],
  [/प्राथमिकी/g, 'FIR'],

  // Criminal Process & Civil Rights
  [/गिरफ्तारी के आधार/g, 'Grounds of arrest'],
  [/गिरफ्तारी के लिखित आधार/g, 'Written grounds of arrest'],
  [/गिरफ्तारी पूर्व नोटिस/g, 'Pre-arrest notice'],
  [/अग्रिम जमानत/g, 'Anticipatory bail'],
  [/नियमित जमानत/g, 'Regular bail'],
  [/अंतरिम जमानत/g, 'Interim bail'],
  [/न्यायिक हिरासत/g, 'Judicial custody'],
  [/पुलिस हिरासत/g, 'Police custody'],
  [/पुलिस रिमांड/g, 'Police remand'],
  [/गैरकानूनी गिरफ्तारी/g, 'Unlawful arrest'],
  [/व्यक्तिगत स्वतंत्रता/g, 'Personal liberty'],
  [/मौलिक अधिकार/g, 'Fundamental rights'],
  [/आरोप पत्र(?:\s*\(चार्जशीट\))?/g, 'Chargesheet'],
  [/चार्जशीट/g, 'Chargesheet'],
  [/आक्षेपित निर्णय/g, 'Impugned judgment'],
  [/आक्षेपित आदेश/g, 'Impugned order'],

  // Common Legal Connectives
  [/विधि के अनुसार/g, 'in accordance with law'],
  [/के अनुसरण में/g, 'pursuant to'],
  [/बिना किसी पूर्वाग्रह के/g, 'without prejudice'],
  [/मामले के तथ्यों एवं परिस्थितियों में/g, 'in the facts and circumstances of the case'],
  [/उपरोक्त के आलोक में/g, 'in view of the above'],
  [/पूर्वोक्त के आलोक में/g, 'in view of the foregoing'],
  [/निवेदन किया कि/g, 'submitted that'],
  [/तर्क दिया कि/g, 'contended that'],
  [/कोई सार नहीं है/g, 'has no merit'],
  [/नोटिस जारी किया गया/g, 'Notice issued'],
  [/अंतरिम संरक्षण/g, 'Interim protection']
];

// Single legal vocabulary tokens for post-phrase replacement
const EN_TO_HI_WORDS: Record<string, string> = {
  section: 'धारा',
  sections: 'धाराएं',
  article: 'अनुच्छेद',
  articles: 'अनुच्छेद',
  clause: 'खंड',
  order: 'आदेश',
  rule: 'नियम',
  act: 'अधिनियम',
  court: 'न्यायालय',
  judge: 'न्यायाधीश',
  judgment: 'निर्णय',
  decree: 'डिक्री',
  bail: 'जमानत',
  arrest: 'गिरफ्तारी',
  remand: 'रिमांड',
  custody: 'हिरासत',
  plea: 'याचिका',
  grounds: 'आधार',
  notice: 'सूचना/नोटिस',
  evidence: 'साक्ष्य',
  witness: 'गवाह',
  affidavit: 'शपथ पत्र',
  allegations: 'आरोप',
  dispute: 'विवाद',
  commercial: 'वाणिज्यिक',
  contract: 'अनुबंध',
  agreement: 'समझौता',
  quash: 'निरस्त',
  quashing: 'निरस्तीकरण',
  challenge: 'चुनौती',
  interception: 'अवरोधन',
  surveillance: 'निगरानी',
  privacy: 'निजता',
  cheque: 'चेक',
  dishonour: 'अनादर',
  presumption: 'उपधारणा',
  arbitration: 'मध्यस्थता',
  reference: 'संदर्भ',
  recovery: 'वसूली',
  suit: 'वाद',
  plaintiff: 'वादी',
  defendant: 'प्रतिवादी',
  delay: 'विलंब',
  limitation: 'परिसीमा',
  offence: 'अपराध',
  cognizable: 'संज्ञेय',
  investigation: 'जांच'
};

const HI_TO_EN_WORDS: Record<string, string> = {
  'धारा': 'Section',
  'धाराएं': 'Sections',
  'अनुच्छेद': 'Article',
  'खंड': 'Clause',
  'आदेश': 'Order',
  'नियम': 'Rule',
  'अधिनियम': 'Act',
  'न्यायालय': 'Court',
  'न्यायाधीश': 'Judge',
  'निर्णय': 'Judgment',
  'जमानत': 'Bail',
  'गिरफ्तारी': 'Arrest',
  'हिरासत': 'Custody',
  'साक्ष्य': 'Evidence',
  'गवाह': 'Witness',
  'शपथ पत्र': 'Affidavit',
  'आरोप': 'Allegation',
  'विवाद': 'Dispute',
  'अनुबंध': 'Contract',
  'समझौता': 'Agreement',
  'निरस्त': 'Quashed',
  'चुनौती': 'Challenge',
  'निजता': 'Privacy',
  'मध्यस्थता': 'Arbitration',
  'वादी': 'Plaintiff',
  'प्रतिवादी': 'Defendant',
  'अपराध': 'Offence',
  'जांच': 'Investigation'
};

// Pre-sorted phrases by pattern length descending to guarantee multi-word phrases match before sub-phrases
const SORTED_EN_TO_HI_PHRASES = [...EN_TO_HI_PHRASES].sort(
  (a, b) => b[0].source.length - a[0].source.length
);
const SORTED_HI_TO_EN_PHRASES = [...HI_TO_EN_PHRASES].sort(
  (a, b) => b[0].source.length - a[0].source.length
);

export class TranslationService {
  /**
   * Evaluates text to detect script and primary language (en, hi, or mixed).
   */
  public static detectLanguage(text: string): LanguageDetectionResult {
    if (!text || !text.trim()) {
      return {
        detectedLanguage: 'en',
        primaryLanguage: 'en',
        devanagariCount: 0,
        latinCount: 0,
        devanagariRatio: 0,
        latinRatio: 0,
        isMixed: false,
        confidence: 1.0
      };
    }

    const devanagariMatches = text.match(/[\u0900-\u097F]/g) || [];
    const latinMatches = text.match(/[a-zA-Z]/g) || [];

    const devanagariCount = devanagariMatches.length;
    const latinCount = latinMatches.length;
    const totalScript = devanagariCount + latinCount;

    if (totalScript === 0) {
      return {
        detectedLanguage: 'en',
        primaryLanguage: 'en',
        devanagariCount: 0,
        latinCount: 0,
        devanagariRatio: 0,
        latinRatio: 0,
        isMixed: false,
        confidence: 0.5
      };
    }

    const devanagariRatio = devanagariCount / totalScript;
    const latinRatio = latinCount / totalScript;

    const isMixed = devanagariRatio >= 0.15 && latinRatio >= 0.15;
    let detectedLanguage: 'en' | 'hi' | 'mixed' = 'en';

    if (isMixed) {
      detectedLanguage = 'mixed';
    } else if (devanagariRatio >= 0.65) {
      detectedLanguage = 'hi';
    } else {
      detectedLanguage = 'en';
    }

    const primaryLanguage: 'en' | 'hi' = devanagariCount > latinCount ? 'hi' : 'en';
    const confidence = Math.max(devanagariRatio, latinRatio);

    return {
      detectedLanguage,
      primaryLanguage,
      devanagariCount,
      latinCount,
      devanagariRatio: Math.round(devanagariRatio * 100) / 100,
      latinRatio: Math.round(latinRatio * 100) / 100,
      isMixed,
      confidence: Math.round(confidence * 100) / 100
    };
  }

  /**
   * Protects legal citations, section references, FIR numbers, and case titles.
   */
  private static maskLegalEntities(text: string): { maskedText: string; tokens: Map<string, string> } {
    const tokens = new Map<string, string>();
    let counter = 0;

    const createPlaceholder = (original: string): string => {
      const key = `__LEGAL_CITE_${counter++}__`;
      tokens.set(key, original);
      return key;
    };

    let masked = text;

    // 0. Uncertain OCR tokens: [?word?], [?token?]
    const UNCERTAIN_OCR_REGEX = /\[\?[^?\]]+\?\]/g;
    masked = masked.replace(UNCERTAIN_OCR_REGEX, (match) => createPlaceholder(match));

    // 1. Supreme Court / High Court standard legal citations
    // e.g. (2023) 5 SCC 120, 2024 INSC 78, AIR 1994 SC 123
    const CITATION_REGEX = /(?:\(\d{4}\)\s+\d+\s+(?:SCC|SCR|SCALE|ILR|CriLJ)\s+\d+(?:,\s+at\s+para(?:graph)?\s+\d+)?|\b\d{4}\s+INSC\s+\d+\b|\bAIR\s+\d{4}\s+(?:SC|Del|Bom|All|Mad|Cal)\s+\d+\b)/gi;
    masked = masked.replace(CITATION_REGEX, (match) => createPlaceholder(match));

    // 2. Specific Statute & Section references
    // e.g. Section 482 CrPC, Article 21, Section 138 NI Act, Section 47 BNSS
    const SECTION_ACT_REGEX = /\b(?:Section|Sec\.|Article|Art\.|Clause|Order|Rule)\s+\d+[A-Z]*(?:\([a-zA-Z0-9]+\))*(?:\s+(?:of\s+the\s+)?(?:CrPC|IPC|BNSS|BNS|BSA|IEA|NI\s+Act|Arbitration\s+Act))?/gi;
    masked = masked.replace(SECTION_ACT_REGEX, (match) => createPlaceholder(match));

    // 3. FIR numbers
    // e.g. FIR No. 123/2024, FIR 45/2023
    const FIR_REGEX = /\bFIR\s+(?:No\.\s*)?\d+[/]\d{2,4}\b/gi;
    masked = masked.replace(FIR_REGEX, (match) => createPlaceholder(match));

    // 4. Exact dates: 14 October 2024, 5 Oct 2024
    const DATE_REGEX = /\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b/gi;
    masked = masked.replace(DATE_REGEX, (match) => createPlaceholder(match));

    return { maskedText: masked, tokens };
  }

  /**
   * Restores masked citations and legal tokens into the translated output.
   */
  private static unmaskLegalEntities(text: string, tokens: Map<string, string>): string {
    let unmasked = text;
    for (const [placeholder, original] of tokens.entries()) {
      unmasked = unmasked.split(placeholder).join(original);
    }
    return unmasked;
  }

  /**
   * High-accuracy, offline, privacy-first Indian legal translation engine.
   */
  public static translateLegalLocal(text: string, sourceLang: 'en' | 'hi', targetLang: 'en' | 'hi'): string {
    if (!text || !text.trim() || sourceLang === targetLang) {
      return text;
    }

    const { maskedText, tokens } = this.maskLegalEntities(text);

    // Split text into paragraphs to preserve layout and paragraph boundaries
    const paragraphs = maskedText.split(/\n\s*\n/);
    const translatedParagraphs = paragraphs.map((para) => {
      if (!para.trim()) return '';

      let current = para;

      if (sourceLang === 'en' && targetLang === 'hi') {
        // Apply English -> Hindi legal phrases (sorted longest first)
        for (const [regex, hiPhrase] of SORTED_EN_TO_HI_PHRASES) {
          current = current.replace(regex, hiPhrase);
        }

        // Apply remaining single-word replacements on word boundaries
        for (const [enWord, hiWord] of Object.entries(EN_TO_HI_WORDS)) {
          const wordRegex = new RegExp(`\\b${enWord}\\b`, 'gi');
          current = current.replace(wordRegex, hiWord);
        }
      } else if (sourceLang === 'hi' && targetLang === 'en') {
        // Apply Hindi -> English legal phrases (sorted longest first)
        for (const [regex, enPhrase] of SORTED_HI_TO_EN_PHRASES) {
          current = current.replace(regex, enPhrase);
        }

        // Apply single-word replacements
        for (const [hiWord, enWord] of Object.entries(HI_TO_EN_WORDS)) {
          const wordRegex = new RegExp(hiWord, 'g');
          current = current.replace(wordRegex, enWord);
        }
      }

      return current;
    });

    const assembled = translatedParagraphs.join('\n\n');
    return this.unmaskLegalEntities(assembled, tokens);
  }

  /**
   * External Cloud Google Translation option with explicit user consent gate.
   */
  private static async translateWithGoogleCloud(
    text: string,
    sourceLang: 'en' | 'hi',
    targetLang: 'en' | 'hi'
  ): Promise<string | null> {
    const apiKey = process.env.GOOGLE_TRANSLATION_API_KEY;
    if (!apiKey) {
      return null;
    }

    try {
      const url = `https://translation.googleapis.com/language/translate/v2?key=${apiKey}`;
      const response = await axios.post(
        url,
        {
          q: text,
          source: sourceLang,
          target: targetLang,
          format: 'text'
        },
        { timeout: 10000 }
      );

      const translated = response.data?.data?.translations?.[0]?.translatedText;
      return translated || null;
    } catch (err: any) {
      logger.warn(`Google Cloud Translation API call failed or timed out: ${err.message}. Falling back to local engine.`);
      return null;
    }
  }

  /**
   * Main translation orchestrator method.
   */
  public static async translateDocumentText(
    text: string,
    options: TranslationOptions
  ): Promise<TranslationResult> {
    if (!text || typeof text !== 'string' || !text.trim()) {
      throw new Error('Document text is required for translation.');
    }

    const trimmed = text.trim();
    const langInfo = this.detectLanguage(trimmed);

    let effectiveSource: 'en' | 'hi';
    if (options.sourceLanguage && options.sourceLanguage !== 'auto') {
      effectiveSource = options.sourceLanguage;
    } else {
      effectiveSource = langInfo.primaryLanguage;
    }

    const effectiveTarget: 'en' | 'hi' = options.targetLanguage;

    if (effectiveSource === effectiveTarget) {
      // If source and target are identical, adjust target to the other supported language
      const adjustedTarget: 'en' | 'hi' = effectiveSource === 'en' ? 'hi' : 'en';
      return this.translateDocumentText(text, { ...options, targetLanguage: adjustedTarget });
    }

    let translated = '';
    let providerUsed: 'local_legal' | 'google_cloud' = 'local_legal';

    // Check if cloud translation is enabled and user explicitly consented
    if (options.consentExternalService && process.env.GOOGLE_TRANSLATION_API_KEY) {
      const cloudResult = await this.translateWithGoogleCloud(trimmed, effectiveSource, effectiveTarget);
      if (cloudResult) {
        translated = cloudResult;
        providerUsed = 'google_cloud';
      }
    }

    // Default & privacy-preserving on-premise legal engine
    if (!translated) {
      translated = this.translateLegalLocal(trimmed, effectiveSource, effectiveTarget);
      providerUsed = 'local_legal';
    }

    const { tokens } = this.maskLegalEntities(trimmed);
    const paragraphs = trimmed.split(/\n\s*\n/).filter(Boolean);

    const disclaimer =
      providerUsed === 'google_cloud'
        ? 'Machine-translated via Google Cloud API (with user consent). For reference only; certified legal translation required for court submission.'
        : 'Machine-translated via JURIST AI On-Premise Legal Engine (100% Private, Zero Cloud Egress). For reference only; certified translation required for court submission.';

    return {
      originalText: trimmed,
      translatedText: translated,
      sourceLanguage: effectiveSource,
      targetLanguage: effectiveTarget,
      detectedLanguage: langInfo.detectedLanguage,
      languageMetrics: {
        devanagariRatio: langInfo.devanagariRatio,
        latinRatio: langInfo.latinRatio,
        isMixed: langInfo.isMixed
      },
      providerUsed,
      isMachineGenerated: true,
      disclaimer,
      preservedCitationsCount: tokens.size,
      paragraphCount: paragraphs.length,
      characterCount: trimmed.length
    };
  }
}
