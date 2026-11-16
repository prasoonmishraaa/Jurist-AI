import { AnalysisController } from '../src/controllers/analysisController';
import { TranslationService } from '../src/services/translationService';

describe('Multilingual Legal Document Intelligence (Hindi–English)', () => {
  // 1. English to Hindi Legal Translation
  test('1. translates English legal text to Hindi accurately', async () => {
    const englishText =
      'IN THE SUPREME COURT OF INDIA\n' +
      'CRIMINAL APPELLATE JURISDICTION\n' +
      'SPECIAL LEAVE PETITION (CRL)\n' +
      'Petitioner challenges unlawful arrest without written grounds of arrest under Article 22(1).\n' +
      'Heard learned counsel for the parties. Perused the record. Appeal allowed. Impugned order quashed and set aside.';

    const result = await TranslationService.translateDocumentText(englishText, {
      sourceLanguage: 'en',
      targetLanguage: 'hi'
    });

    expect(result.sourceLanguage).toBe('en');
    expect(result.targetLanguage).toBe('hi');
    expect(result.translatedText).toContain('भारत के सर्वोच्च न्यायालय में');
    expect(result.translatedText).toContain('आपराधिक अपीलीय क्षेत्राधिकार');
    expect(result.translatedText).toContain('विशेष अनुमति याचिका');
    expect(result.translatedText).toContain('याचिकाकर्ता');
    expect(result.translatedText).toContain('अपील स्वीकार की गई');
    expect(result.translatedText).toContain('निरस्त एवं अपास्त किया गया');
    expect(result.isMachineGenerated).toBe(true);
    expect(result.providerUsed).toBe('local_legal');
  });

  // 2. Hindi to English Legal Translation
  test('2. translates Hindi legal text to English accurately', async () => {
    const hindiText =
      'भारत के सर्वोच्च न्यायालय में\n' +
      'याचिकाकर्ता ने उच्च न्यायालय के आक्षेपित आदेश को चुनौती दी।\n' +
      'अभियुक्त को अग्रिम जमानत प्रदान की जाती है।\n' +
      'अपील स्वीकार की गई। तदनुसार आदेशित किया जाता है।';

    const result = await TranslationService.translateDocumentText(hindiText, {
      sourceLanguage: 'hi',
      targetLanguage: 'en'
    });

    expect(result.sourceLanguage).toBe('hi');
    expect(result.targetLanguage).toBe('en');
    expect(result.translatedText).toContain('IN THE SUPREME COURT OF INDIA');
    expect(result.translatedText).toContain('Petitioner');
    expect(result.translatedText).toContain('High Court');
    expect(result.translatedText).toContain('Impugned order');
    expect(result.translatedText).toContain('Anticipatory bail');
    expect(result.translatedText).toContain('Appeal allowed');
    expect(result.translatedText).toContain('Ordered accordingly');
  });

  // 3. OCR Output Translation (Simulating OCR text with uncertain tokens)
  test('3. processes OCR-extracted text with uncertainty tokens without dropping them', async () => {
    const ocrText =
      'The police arrested the accused under Section 41A without serving pre-arrest notice. ' +
      'The [?custody?] was extended by the Magistrate without recording [?satisfaction?]. ' +
      'Petitioner prays for regular bail in FIR No. 120/2024.';

    const result = await TranslationService.translateDocumentText(ocrText, {
      targetLanguage: 'hi'
    });

    expect(result.translatedText).toContain('[?custody?]');
    expect(result.translatedText).toContain('[?satisfaction?]');
    expect(result.translatedText).toContain('FIR No. 120/2024');
    expect(result.translatedText).toContain('जमानत');
  });

  // 4. Mixed Hindi-English Legal Text
  test('4. accurately detects and translates mixed bilingual Hindi-English text', async () => {
    const mixedText =
      'FIR No. 45/2023 was registered at Police Station Connaught Place. ' +
      'याचिकाकर्ता ने अग्रिम जमानत हेतु उच्च न्यायालय में आवेदन किया। ' +
      'The matter is pending adjudication.';

    const detection = TranslationService.detectLanguage(mixedText);
    expect(detection.isMixed).toBe(true);
    expect(detection.detectedLanguage).toBe('mixed');
    expect(detection.devanagariCount).toBeGreaterThan(0);
    expect(detection.latinCount).toBeGreaterThan(0);

    // Translate to Hindi
    const toHindi = await TranslationService.translateDocumentText(mixedText, {
      targetLanguage: 'hi'
    });
    expect(toHindi.translatedText).toContain('याचिकाकर्ता');
    expect(toHindi.translatedText).toContain('FIR No. 45/2023');

    // Translate to English
    const toEnglish = await TranslationService.translateDocumentText(mixedText, {
      sourceLanguage: 'hi',
      targetLanguage: 'en'
    });
    expect(toEnglish.translatedText).toContain('Petitioner');
    expect(toEnglish.translatedText).toContain('Anticipatory bail');
    expect(toEnglish.translatedText).toContain('High Court');
  });

  // 5. Preservation of Legal Citations and Statutory Section Numbers
  test('5. strictly preserves Supreme Court citations and statutory sections without corruption', async () => {
    const citationText =
      'The landmark ruling in (2023) 5 SCC 120, at paragraph 14 establishes compliance with Article 21. ' +
      'The petition under Section 482 of the CrPC is allowed following principles in 2024 INSC 78. ' +
      'Pre-arrest notice under Section 41A of the CrPC was mandatory on 14 October 2024.';

    const result = await TranslationService.translateDocumentText(citationText, {
      sourceLanguage: 'en',
      targetLanguage: 'hi'
    });

    // Check verbatim preservation of citations and sections
    expect(result.translatedText).toContain('(2023) 5 SCC 120, at paragraph 14');
    expect(result.translatedText).toContain('Article 21');
    expect(result.translatedText).toContain('Section 482 of the CrPC');
    expect(result.translatedText).toContain('2024 INSC 78');
    expect(result.translatedText).toContain('Section 41A of the CrPC');
    expect(result.translatedText).toContain('14 October 2024');
    expect(result.preservedCitationsCount).toBeGreaterThanOrEqual(4);
  });

  // 6. Long Document Chunking & Paragraph Boundary Preservation
  test('6. preserves paragraph structure and double-line breaks across multi-paragraph documents', async () => {
    const multiParaText =
      'Paragraph 1: In the Supreme Court of India. Criminal appellate jurisdiction.\n\n' +
      'Paragraph 2: The petitioner challenges the impugned order of the High Court.\n\n' +
      'Paragraph 3: Heard learned counsel for the parties. Perused the record.\n\n' +
      'Paragraph 4: Appeal allowed. Ordered accordingly.';

    const result = await TranslationService.translateDocumentText(multiParaText, {
      sourceLanguage: 'en',
      targetLanguage: 'hi'
    });

    const outputParas = result.translatedText.split(/\n\s*\n/);
    expect(outputParas.length).toBe(4);
    expect(outputParas[0]).toContain('भारत के सर्वोच्च न्यायालय में');
    expect(outputParas[1]).toContain('याचिकाकर्ता');
    expect(outputParas[2]).toContain('पक्षकारों के विद्वान अधिवक्ताओं को सुना गया');
    expect(outputParas[3]).toContain('अपील स्वीकार की गई');
  });

  // 7. Empty, Whitespace, or Invalid Input Handling
  test('7. rejects empty or blank text with understandable error', async () => {
    await expect(
      TranslationService.translateDocumentText('', { targetLanguage: 'hi' })
    ).rejects.toThrow('Document text is required');

    await expect(
      TranslationService.translateDocumentText('   \n  \t  ', { targetLanguage: 'hi' })
    ).rejects.toThrow('Document text is required');
  });

  // 8. Translation Fallback Behavior & Privacy Guarantees
  test('8. defaults to on-premise private engine without sending data externally when cloud consent is absent', async () => {
    const text = 'Writ Petition under Article 32 of the Constitution of India.';

    const result = await TranslationService.translateDocumentText(text, {
      targetLanguage: 'hi',
      consentExternalService: false
    });

    expect(result.providerUsed).toBe('local_legal');
    expect(result.disclaimer).toContain('On-Premise Legal Engine');
    expect(result.disclaimer).toContain('100% Private, Zero Cloud Egress');
    expect(result.translatedText).toContain('रिट याचिका');
  });

  // 9. Unicode & Devanagari Integrity
  test('9. renders full Devanagari Unicode character set without corruption', async () => {
    const hindiDevanagari = 'भारत का संविधान, मौलिक अधिकार, व्यक्तिगत स्वतंत्रता और न्यायिक समीक्षा।';
    const detection = TranslationService.detectLanguage(hindiDevanagari);

    expect(detection.detectedLanguage).toBe('hi');
    expect(detection.primaryLanguage).toBe('hi');
    expect(detection.devanagariRatio).toBe(1.0);
    expect(detection.latinCount).toBe(0);

    const translated = await TranslationService.translateDocumentText(hindiDevanagari, {
      sourceLanguage: 'hi',
      targetLanguage: 'en'
    });

    expect(translated.translatedText).toContain('Constitution of India');
    expect(translated.translatedText).toContain('Fundamental rights');
    expect(translated.translatedText).toContain('Personal liberty');
  });

  // 10. Language Metrics & Safeguards
  test('10. provides transparent metrics and marks translation as machine-generated', async () => {
    const text = 'The High Court dismissed the application under Section 482 CrPC.';
    const result = await TranslationService.translateDocumentText(text, {
      targetLanguage: 'hi'
    });

    expect(result.isMachineGenerated).toBe(true);
    expect(result.languageMetrics).toBeDefined();
    expect(result.languageMetrics.latinRatio).toBeGreaterThan(0.5);
    expect(result.characterCount).toBe(text.length);
    expect(result.paragraphCount).toBe(1);
    expect(result.disclaimer).toBeDefined();
  });

  // Helper to construct mock Express response
  function createMockRes() {
    const res: any = {
      statusCode: 200,
      body: null,
      status(code: number) {
        this.statusCode = code;
        return this;
      },
      json(payload: any) {
        this.body = payload;
        return this;
      }
    };
    return res;
  }

  // 11. Pre-Analysis Workflow: Hindi narrative with translateForAnalysis: true
  test('11. pre-analysis intake: translates Hindi narrative into English and attaches preAnalysisTranslation', async () => {
    const hindiNarrative =
      'भारत के सर्वोच्च न्यायालय में याचिकाकर्ता ने धारा 482 सीआरपीसी के तहत प्राथमिकी संख्या 123/2024 को रद्द करने की प्रार्थना की। अभियुक्त को अग्रिम जमानत प्रदान की जाए।';

    const req: any = {
      user: { id: 'usr_test_11', email: 'rajesh@bar.in', name: 'Advocate Rajesh' },
      body: {
        title: 'Hindi Criminal Petition Analysis',
        court: 'Supreme Court of India',
        category: 'Criminal Law',
        text: hindiNarrative,
        documentLanguage: 'hi',
        analysisLanguage: 'en',
        translateForAnalysis: 'true'
      }
    };
    const res = createMockRes();

    await AnalysisController.createAnalysis(req, res);

    expect(res.statusCode).toBe(201);
    expect(res.body.success).toBe(true);
    const data = res.body.data;
    expect(data.documentMetadata).toBeDefined();
    expect(data.documentMetadata.translationForAnalysis).toBe(true);
    expect(data.documentMetadata.preAnalysisTranslation).toBeDefined();
    expect(data.documentMetadata.preAnalysisTranslation.sourceLanguage).toBe('hi');
    expect(data.documentMetadata.preAnalysisTranslation.targetLanguage).toBe('en');
    expect(data.documentMetadata.originalExtractedText).toBe(hindiNarrative);
    expect(data.documentMetadata.preAnalysisTranslation.translatedText).toContain('123/2024');
  });

  // 12. Pre-Analysis Workflow: Hindi narrative with translateForAnalysis: false is rejected
  test('12. pre-analysis intake: rejects Hindi text when translateForAnalysis is false and no English description is provided', async () => {
    const hindiNarrative =
      'भारत के सर्वोच्च न्यायालय में याचिकाकर्ता ने धारा 482 सीआरपीसी के तहत प्राथमिकी संख्या 123/2024 को रद्द करने की प्रार्थना की।';

    const req: any = {
      user: { id: 'usr_test_12', email: 'sunita@bar.in', name: 'Advocate Sunita' },
      body: {
        title: 'Hindi Criminal Petition Analysis Without Translation',
        court: 'Supreme Court of India',
        category: 'Criminal Law',
        text: hindiNarrative,
        documentLanguage: 'hi',
        analysisLanguage: 'en',
        translateForAnalysis: 'false'
      }
    };
    const res = createMockRes();

    await AnalysisController.createAnalysis(req, res);

    expect(res.statusCode).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toContain('Translate for analysis');
  });

  // 13. Pre-Analysis Workflow: English document does not invoke pre-analysis translation
  test('13. pre-analysis intake: processes English document without unnecessary translation overhead', async () => {
    const englishNarrative =
      'Petitioner challenges unlawful arrest without written grounds under Article 22(1) and Section 47 BNSS on 14 October 2024. Offence was alleged on 5 October 2024 in a commercial supply contract dispute.';

    const req: any = {
      user: { id: 'usr_test_13', email: 'arjun@bar.in', name: 'Advocate Arjun' },
      body: {
        title: 'English Arrest Challenge',
        court: 'Supreme Court of India',
        category: 'Criminal Law',
        text: englishNarrative,
        documentLanguage: 'auto',
        analysisLanguage: 'en',
        translateForAnalysis: 'true'
      }
    };
    const res = createMockRes();

    await AnalysisController.createAnalysis(req, res);

    expect(res.statusCode).toBe(201);
    expect(res.body.success).toBe(true);
    const data = res.body.data;
    if (data.documentMetadata) {
      expect(data.documentMetadata.translationForAnalysis).toBe(false);
      expect(data.documentMetadata.preAnalysisTranslation).toBeUndefined();
    }
  });

  // 14. Pre-Analysis Workflow: Uploaded Hindi file with translateForAnalysis: true
  test('14. pre-analysis intake: translates uploaded Hindi text file and passes English translation to analysis', async () => {
    const hindiContent =
      'भारत का सर्वोच्च न्यायालय\n' +
      'विशेष अनुमति याचिका (आपराधिक)\n' +
      'याचिकाकर्ता ने उच्च न्यायालय के आक्षेपित आदेश को चुनौती दी। प्राथमिकी संख्या 98/2024 धारा 420 भारतीय दंड संहिता के तहत दर्ज की गई।';

    const req: any = {
      user: { id: 'usr_test_14', email: 'meera@bar.in', name: 'Advocate Meera' },
      body: {
        title: 'Hindi Pleading File Upload',
        court: 'Supreme Court of India',
        category: 'Criminal Law',
        documentLanguage: 'hi',
        analysisLanguage: 'en',
        translateForAnalysis: 'true'
      },
      file: {
        buffer: Buffer.from(hindiContent, 'utf-8'),
        originalname: 'pleading_hindi.txt',
        mimetype: 'text/plain'
      }
    };
    const res = createMockRes();

    await AnalysisController.createAnalysis(req, res);

    expect(res.statusCode).toBe(201);
    expect(res.body.success).toBe(true);
    const data = res.body.data;
    expect(data.documentMetadata).toBeDefined();
    expect(data.documentMetadata.translationForAnalysis).toBe(true);
    expect(data.documentMetadata.preAnalysisTranslation).toBeDefined();
    expect(data.documentMetadata.originalExtractedText).toContain('प्राथमिकी संख्या 98/2024');
    expect(data.documentMetadata.preAnalysisTranslation.translatedText).toContain('98/2024');
  });

  // 15. Pre-Analysis Workflow: Uploaded Hindi file with translateForAnalysis: false fails if no English text
  test('15. pre-analysis intake: rejects uploaded Hindi file when translateForAnalysis is false and no English text is provided', async () => {
    const hindiContent =
      'भारत का सर्वोच्च न्यायालय\n' +
      'विशेष अनुमति याचिका (आपराधिक)\n' +
      'याचिकाकर्ता ने उच्च न्यायालय के आक्षेपित आदेश को चुनौती दी।';

    const req: any = {
      user: { id: 'usr_test_15', email: 'devansh@bar.in', name: 'Advocate Devansh' },
      body: {
        title: 'Hindi Pleading File Upload Without Translation',
        court: 'Supreme Court of India',
        category: 'Criminal Law',
        documentLanguage: 'hi',
        analysisLanguage: 'en',
        translateForAnalysis: 'false'
      },
      file: {
        buffer: Buffer.from(hindiContent, 'utf-8'),
        originalname: 'pleading_hindi.txt',
        mimetype: 'text/plain'
      }
    };
    const res = createMockRes();

    await AnalysisController.createAnalysis(req, res);

    expect(res.statusCode).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toContain('Translate for analysis');
  });
});
