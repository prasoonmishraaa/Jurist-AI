import React, { useState, useMemo } from 'react';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  PenTool,
  Type,
  Layers,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  ShieldAlert,
  Languages,
  Globe,
  Download,
  Sparkles,
  RefreshCw,
  Lock
} from 'lucide-react';
import { renderTextWithOcrWarnings } from './EvidenceTraceView';
import { api } from '../../services/api';

interface DocumentIntelligenceViewProps {
  documentMetadata?: any;
  extractedTextSnippet?: string;
}

export const DocumentIntelligenceView: React.FC<DocumentIntelligenceViewProps> = ({
  documentMetadata,
  extractedTextSnippet
}) => {
  const [showFullText, setShowFullText] = useState(false);
  const [copiedOriginal, setCopiedOriginal] = useState(false);
  const [copiedTranslation, setCopiedTranslation] = useState(false);

  // Translation State
  const [targetLanguage, setTargetLanguage] = useState<'en' | 'hi'>('hi');
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationResult, setTranslationResult] = useState<any | null>(
    documentMetadata?.preAnalysisTranslation || null
  );
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'sideBySide' | 'original' | 'translated'>('sideBySide');
  const [consentCloud, setConsentCloud] = useState(false);

  React.useEffect(() => {
    if (documentMetadata?.preAnalysisTranslation) {
      setTranslationResult(documentMetadata.preAnalysisTranslation);
      if (documentMetadata.preAnalysisTranslation.targetLanguage) {
        setTargetLanguage(documentMetadata.preAnalysisTranslation.targetLanguage === 'en' ? 'hi' : 'en');
      }
    }
  }, [documentMetadata?.preAnalysisTranslation]);

  if (!documentMetadata) {
    return (
      <div className="parchment-card rounded p-8 text-center space-y-3">
        <FileText className="w-10 h-10 text-gold-600 mx-auto" />
        <h3 className="text-base font-serif font-bold text-navy-900">
          No Document Attachment
        </h3>
        <p className="text-xs text-charcoal-500 max-w-md mx-auto leading-relaxed">
          This matter was submitted via direct factual narrative without an uploaded document. To utilize automated OCR, multi-page inspection, and multilingual document intelligence, attach a PDF, Word DOCX, TXT, or image file during matter intake.
        </p>
      </div>
    );
  }

  const {
    filename = 'Uploaded Legal Document',
    documentType = 'pdf',
    pageCount = 1,
    extractionMethod = 'native',
    scriptType = 'digital',
    handwrittenDetected = false,
    overallStatus = 'SUCCESS',
    warnings = [],
    pages = []
  } = documentMetadata;

  // Extract all uncertain tokens across all pages
  const allUncertainTokens: string[] = useMemo(() => {
    const tokens: string[] = [];
    pages.forEach((p: any) => {
      if (Array.isArray(p.uncertainTokens)) {
        p.uncertainTokens.forEach((t: string) => {
          if (!tokens.includes(t)) tokens.push(t);
        });
      }
    });
    return tokens;
  }, [pages]);

  // Calculate composite confidence
  const validConfs = pages
    .map((p: any) => p.confidence)
    .filter((c: any) => typeof c === 'number' && c !== null);
  const avgConfidence =
    validConfs.length > 0
      ? (validConfs.reduce((a: number, b: number) => a + b, 0) / validConfs.length)
      : null;

  // Complete extracted text
  const fullExtractedText = useMemo(() => {
    if (documentMetadata?.originalExtractedText) {
      return documentMetadata.originalExtractedText;
    }
    const textFromPages = pages.map((p: any) => p.text || '').join('\n\n').trim();
    return textFromPages || (extractedTextSnippet || '').trim();
  }, [pages, extractedTextSnippet, documentMetadata?.originalExtractedText]);

  // Detected Source Script & Language
  const scriptAnalysis = useMemo(() => {
    if (!fullExtractedText) {
      return { sourceLang: 'en' as const, devanagariCount: 0, latinCount: 0, label: 'English (Default)' };
    }
    const devanagariMatches = fullExtractedText.match(/[\u0900-\u097F]/g) || [];
    const latinMatches = fullExtractedText.match(/[a-zA-Z]/g) || [];
    const devanagariCount = devanagariMatches.length;
    const latinCount = latinMatches.length;

    let sourceLang: 'en' | 'hi' = 'en';
    let label = 'English';

    if (devanagariCount > latinCount && devanagariCount >= 10) {
      sourceLang = 'hi';
      label = 'Hindi (Devanagari)';
    } else if (devanagariCount > 0 && latinCount > 0 && devanagariCount / (devanagariCount + latinCount) > 0.15) {
      sourceLang = devanagariCount > latinCount ? 'hi' : 'en';
      label = `Bilingual Mixed (${devanagariCount > latinCount ? 'Hindi Primary' : 'English Primary'})`;
    }

    return { sourceLang, devanagariCount, latinCount, label };
  }, [fullExtractedText]);

  // Automatically suggest complementary target language
  const suggestedTarget = scriptAnalysis.sourceLang === 'hi' ? 'en' : 'hi';

  const handleCopyOriginal = () => {
    if (fullExtractedText) {
      navigator.clipboard.writeText(fullExtractedText);
      setCopiedOriginal(true);
      setTimeout(() => setCopiedOriginal(false), 2500);
    }
  };

  const handleCopyTranslation = () => {
    if (translationResult?.translatedText) {
      navigator.clipboard.writeText(translationResult.translatedText);
      setCopiedTranslation(true);
      setTimeout(() => setCopiedTranslation(false), 2500);
    }
  };

  const handleDownloadTranslation = () => {
    if (!translationResult?.translatedText) return;

    // Use UTF-8 BOM to ensure Devanagari Hindi characters render cleanly in all editors
    const bom = '\uFEFF';
    const content =
      `${bom}========================================================================\n` +
      `JURIST AI — MULTILINGUAL LEGAL DOCUMENT TRANSLATION\n` +
      `Matter File: ${filename}\n` +
      `Target Language: ${translationResult.targetLanguage === 'hi' ? 'Hindi (हिन्दी)' : 'English'}\n` +
      `Engine: ${translationResult.providerUsed === 'google_cloud' ? 'Google Cloud Translation' : 'JURIST AI On-Premise Legal Engine'}\n` +
      `Preserved Citations: ${translationResult.preservedCitationsCount || 0}\n` +
      `Date: ${new Date().toLocaleDateString('en-IN')}\n` +
      `Notice: Machine-assisted translation. For court use, certified translation required.\n` +
      `========================================================================\n\n` +
      translationResult.translatedText;

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename.replace(/\.[^/.]+$/, '')}_translated_${translationResult.targetLanguage}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleTranslate = async () => {
    if (!fullExtractedText) {
      setTranslationError('No extracted text available to translate.');
      return;
    }

    setIsTranslating(true);
    setTranslationError(null);

    try {
      const response = await api.translateDocument({
        text: fullExtractedText,
        sourceLanguage: scriptAnalysis.sourceLang,
        targetLanguage,
        consentExternalService: consentCloud,
        preserveCitations: true
      });

      setTranslationResult(response);
    } catch (err: any) {
      setTranslationError(
        err.response?.data?.error ||
          err.message ||
          'Translation service is temporarily unreachable. Please try again.'
      );
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="parchment-card rounded p-5 space-y-4 border-l-4 border-l-navy-900">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-ivory-200 pb-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-serif font-bold text-sm px-2.5 py-0.5 rounded bg-navy-950 text-gold-300 border border-gold-500/30">
                {documentType.toUpperCase()}
              </span>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-ivory-100 text-navy-900 border border-ivory-300">
                {pageCount} Page{pageCount > 1 ? 's' : ''}
              </span>
              <span
                className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                  overallStatus === 'SUCCESS'
                    ? 'bg-green-50 text-green-900 border-green-300'
                    : overallStatus === 'SUCCESS_WITH_WARNINGS'
                    ? 'bg-gold-50 text-gold-950 border-gold-300'
                    : 'bg-amber-100 text-amber-950 border-amber-400'
                }`}
              >
                Status: {overallStatus.replace(/_/g, ' ')}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-navy-100/70 text-navy-950 border border-navy-300">
                <Globe className="w-3 h-3 text-gold-600" />
                <span>Script: {scriptAnalysis.label}</span>
              </span>
            </div>
            <h3 className="text-base font-serif font-bold text-navy-900 leading-snug">
              {filename}
            </h3>
          </div>

          <div className="flex items-center gap-2 self-start flex-wrap">
            <button
              type="button"
              onClick={handleCopyOriginal}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-ivory-50 hover:bg-navy-900 hover:text-gold-200 text-xs font-semibold text-navy-900 border border-ivory-300 transition-colors"
            >
              {copiedOriginal ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5 text-gold-700" />}
              <span>{copiedOriginal ? 'Original Copied' : 'Copy Original'}</span>
            </button>
          </div>
        </div>

        {/* Diagnostic Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
            <span className="text-charcoal-500 font-serif flex items-center gap-1">
              <FileSearch className="w-3.5 h-3.5 text-gold-700" />
              <span>Extraction Method</span>
            </span>
            <p className="font-semibold text-navy-900">
              {extractionMethod === 'native'
                ? 'Native Digital Layer'
                : extractionMethod === 'ocr'
                ? 'Optical Character Recognition (OCR)'
                : extractionMethod === 'hybrid'
                ? 'Hybrid (Digital & OCR)'
                : 'Direct Stream'}
            </p>
          </div>

          <div className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
            <span className="text-charcoal-500 font-serif flex items-center gap-1">
              {handwrittenDetected ? (
                <PenTool className="w-3.5 h-3.5 text-burgundy-700" />
              ) : (
                <Type className="w-3.5 h-3.5 text-navy-800" />
              )}
              <span>Script Nature</span>
            </span>
            <p className="font-semibold text-navy-900 flex items-center gap-1.5">
              <span>
                {scriptType === 'handwritten'
                  ? 'Handwritten Manuscript'
                  : scriptType === 'mixed'
                  ? 'Mixed (Printed & Handwritten)'
                  : scriptType === 'printed'
                  ? 'Machine-Printed Typography'
                  : 'Digital Text Layer'}
              </span>
            </p>
          </div>

          <div className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
            <span className="text-charcoal-500 font-serif flex items-center gap-1">
              <Layers className="w-3.5 h-3.5 text-gold-700" />
              <span>OCR Confidence</span>
            </span>
            <p className="font-semibold text-navy-900">
              {avgConfidence !== null
                ? `${Math.round(avgConfidence * 100)}% Average Confidence`
                : '100% (Native Digital Stream)'}
            </p>
          </div>

          <div className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
            <span className="text-charcoal-500 font-serif flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5 text-gold-700" />
              <span>Uncertain Tokens</span>
            </span>
            <p className="font-semibold text-navy-900">
              {allUncertainTokens.length > 0
                ? `${allUncertainTokens.length} Token${allUncertainTokens.length > 1 ? 's' : ''} Flagged [?...?]`
                : '0 Uncertain Tokens'}
            </p>
          </div>
        </div>

        {/* High-Priority Handwritten Evidentiary Notice */}
        {handwrittenDetected && (
          <div className="p-4 bg-amber-50 border border-amber-300 rounded text-xs text-amber-950 space-y-1.5">
            <div className="flex items-center gap-2 font-serif font-bold text-amber-900">
              <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
              <span>Evidentiary Warning: Handwritten Manuscript Detected</span>
            </div>
            <p className="leading-relaxed">
              Automated OCR cannot reliably transcribe unconstrained or cursive handwriting without error. Extracted dates, names, FIR numbers, and penal sections must be manually cross-checked against original physical manuscripts before relying upon them in court submissions. Flagged uncertain words appear with dashed borders below.
            </p>
          </div>
        )}

        {/* Global Warnings List */}
        {warnings && warnings.length > 0 && !handwrittenDetected && (
          <div className="p-3 bg-ivory-100 border border-ivory-300 rounded text-xs text-charcoal-800 space-y-1">
            <strong className="font-serif text-navy-900 block">Processing Notices:</strong>
            <ul className="list-disc pl-4 space-y-0.5">
              {warnings.map((w: string, idx: number) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Multilingual Legal Translation Control Panel */}
      <div className="parchment-card rounded-lg p-5 border border-gold-500/50 bg-gradient-to-r from-ivory-50 via-white to-ivory-50 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-ivory-200 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-navy-900 text-gold-300 flex items-center justify-center shrink-0">
              <Languages className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-serif font-bold text-navy-900 flex items-center gap-2">
                <span>Multilingual Document Intelligence (English &bull; हिन्दी)</span>
                <span className="px-1.5 py-0.2 rounded bg-gold-100 text-gold-900 text-[10px] font-sans font-semibold border border-gold-400">
                  Legal Precision
                </span>
              </h3>
              <p className="text-[11px] text-charcoal-600">
                Translate extracted legal text between English and Hindi while preserving statutory section numbers, case citations, dates, and party designations.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center">
            <span className="text-[11px] text-charcoal-600 font-serif">Translate into:</span>
            <select
              value={targetLanguage}
              onChange={(e) => setTargetLanguage(e.target.value as 'en' | 'hi')}
              className="text-xs font-serif font-semibold px-3 py-1.5 rounded bg-white border border-ivory-300 text-navy-900 focus:outline-none focus:ring-1 focus:ring-navy-900 shadow-sm"
            >
              <option value="hi">Hindi (हिन्दी Devanagari)</option>
              <option value="en">English (Appellate Standard)</option>
            </select>

            <button
              type="button"
              onClick={handleTranslate}
              disabled={isTranslating || !fullExtractedText}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-navy-900 hover:bg-navy-800 disabled:opacity-50 text-gold-300 text-xs font-serif font-bold border border-gold-500/40 shadow-sm transition-colors"
            >
              {isTranslating ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-gold-400" />
                  <span>Translating...</span>
                </>
              ) : (
                <>
                  <Languages className="w-3.5 h-3.5 text-gold-400" />
                  <span>Translate Document</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Translation Privacy & Settings Sub-bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px] text-charcoal-600 pt-0.5">
          <div className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-green-700 shrink-0" />
            <span className="font-semibold text-navy-950">Privacy First:</span>
            <span>
              Default processing uses the <strong>On-Premise Legal Engine</strong> (zero data leaves your local/private environment).
            </span>
          </div>

          <label className="inline-flex items-center gap-1.5 cursor-pointer text-[10.5px] select-none text-charcoal-700">
            <input
              type="checkbox"
              checked={consentCloud}
              onChange={(e) => setConsentCloud(e.target.checked)}
              className="rounded border-ivory-300 text-navy-900 focus:ring-navy-900 w-3.5 h-3.5"
            />
            <span>Allow External Cloud Translation (Google Cloud API if configured)</span>
          </label>
        </div>

        {/* Translation Error Banner */}
        {translationError && (
          <div className="p-3 bg-burgundy-50 border border-burgundy-900/30 rounded text-xs text-burgundy-900 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-burgundy-800" />
            <span>{translationError}</span>
          </div>
        )}
      </div>

      {/* Flagged Uncertain Words Chips */}
      {allUncertainTokens.length > 0 && (
        <div className="parchment-card rounded p-5 space-y-2.5">
          <h4 className="text-xs font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
            <span>Uncertain / Low-Confidence Words Requiring Verification ({allUncertainTokens.length})</span>
          </h4>
          <p className="text-[11px] text-charcoal-600">
            The OCR engine identified these words as either out-of-lexicon or below confidence threshold. Each is enclosed in <code className="bg-amber-100 px-1 py-0.5 rounded text-amber-950">[?word?]</code> in the extracted text.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {allUncertainTokens.map((token, tIdx) => (
              <span
                key={tIdx}
                className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-950 border border-amber-300"
              >
                <span>[?{token}?]</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Per-Page Diagnostics Table */}
      {pages && pages.length > 1 && (
        <div className="parchment-card rounded p-5 space-y-3">
          <h4 className="text-xs font-serif font-bold text-navy-900 uppercase tracking-wide">
            Per-Page Extraction &amp; Script Diagnostics
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-ivory-300 font-serif font-bold text-navy-900 bg-ivory-50">
                  <th className="py-2 px-3">Page #</th>
                  <th className="py-2 px-3">Extraction Mode</th>
                  <th className="py-2 px-3">Script Classification</th>
                  <th className="py-2 px-3">OCR Confidence</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Uncertain Words</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ivory-200">
                {pages.map((p: any, idx: number) => (
                  <tr key={idx} className="hover:bg-ivory-50/50">
                    <td className="py-2 px-3 font-mono font-semibold text-navy-900">
                      Page {p.pageNumber || idx + 1}
                    </td>
                    <td className="py-2 px-3 capitalize">
                      {p.extractionMethod === 'native' ? 'Digital Native' : 'OCR Scanned'}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10.5px] font-semibold ${
                          p.handwrittenDetected || p.scriptType === 'handwritten'
                            ? 'bg-burgundy-50 text-burgundy-900 border border-burgundy-200'
                            : 'bg-navy-50 text-navy-900 border border-navy-200'
                        }`}
                      >
                        {p.scriptType === 'handwritten'
                          ? 'Handwritten'
                          : p.scriptType === 'mixed'
                          ? 'Mixed'
                          : p.scriptType === 'printed'
                          ? 'Printed Typography'
                          : 'Digital Native'}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono">
                      {p.confidence !== null && p.confidence !== undefined
                        ? `${Math.round(p.confidence * 100)}%`
                        : '100%'}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`text-[10.5px] font-medium px-1.5 py-0.5 rounded ${
                          p.status === 'SUCCESS'
                            ? 'bg-green-50 text-green-800'
                            : 'bg-amber-100 text-amber-900'
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px] text-charcoal-700">
                      {p.uncertainTokens && p.uncertainTokens.length > 0
                        ? `${p.uncertainTokens.length} flagged`
                        : 'None'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Document Text Viewer: Side-by-Side or Full View */}
      <div className="parchment-card rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-ivory-200 pb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-xs font-serif font-bold text-navy-900 uppercase tracking-wide">
              {translationResult ? 'Bilingual Legal Document Workspace' : 'Extracted Document Text'}
            </h4>
            {translationResult && (
              <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-gold-100 text-gold-900 font-semibold border border-gold-400">
                {translationResult.preservedCitationsCount} Citations &amp; Sections Preserved
              </span>
            )}
            {documentMetadata?.translationForAnalysis && (
              <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-green-100 text-green-900 font-semibold border border-green-400 inline-flex items-center gap-1">
                <Check className="w-3 h-3 text-green-700" />
                <span>Pre-Analysis Translation Active</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {translationResult && (
              <div className="inline-flex rounded-md border border-ivory-300 p-0.5 bg-ivory-100 text-xs font-serif">
                <button
                  type="button"
                  onClick={() => setViewMode('sideBySide')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    viewMode === 'sideBySide'
                      ? 'bg-navy-900 text-gold-300 font-bold shadow-xs'
                      : 'text-charcoal-700 hover:text-navy-900'
                  }`}
                >
                  Side-by-Side
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('original')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    viewMode === 'original'
                      ? 'bg-navy-900 text-gold-300 font-bold shadow-xs'
                      : 'text-charcoal-700 hover:text-navy-900'
                  }`}
                >
                  Original Only
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('translated')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    viewMode === 'translated'
                      ? 'bg-navy-900 text-gold-300 font-bold shadow-xs'
                      : 'text-charcoal-700 hover:text-navy-900'
                  }`}
                >
                  Translation Only
                </button>
              </div>
            )}

            <button
              type="button"
              onClick={() => setShowFullText(!showFullText)}
              className="inline-flex items-center gap-1 text-xs font-serif font-semibold text-navy-900 hover:text-gold-700 ml-1"
            >
              {showFullText ? <ChevronUp className="w-4 h-4 text-gold-600" /> : <ChevronDown className="w-4 h-4 text-gold-600" />}
              <span>{showFullText ? 'Collapse' : 'Expand'}</span>
            </button>
          </div>
        </div>

        {/* Pre-Analysis Translation Notice Banner */}
        {documentMetadata?.translationForAnalysis && (
          <div className="p-3 bg-gold-50/80 border border-gold-400/60 rounded text-xs text-navy-950 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-gold-700 shrink-0" />
              <div>
                <span className="font-serif font-bold text-navy-900 block">
                  Automatic Pre-Analysis Translation Generated &bull; Fed into Legal Research Pipeline
                </span>
                <span className="text-[11px] text-charcoal-600">
                  Extracted vernacular text was automatically translated to English prior to case classification, statutory matching, and model estimation. The side-by-side view below presents the original OCR extract alongside the English legal translation.
                </span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded bg-white text-navy-900 font-mono text-[10.5px] font-semibold border border-gold-300 self-start sm:self-center shrink-0">
              Auto-Translated
            </span>
          </div>
        )}

        {/* Content Viewer Panes */}
        {translationResult && viewMode === 'sideBySide' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Pane: Original */}
            <div className="border border-ivory-300 rounded-lg bg-ivory-50/70 p-4 space-y-2.5">
              <div className="flex items-center justify-between border-b border-ivory-200 pb-2">
                <span className="text-xs font-serif font-bold text-navy-900 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-navy-800" />
                  <span>Original Document ({scriptAnalysis.sourceLang === 'hi' ? 'Hindi' : 'English'})</span>
                </span>
                <button
                  type="button"
                  onClick={handleCopyOriginal}
                  className="text-[11px] font-sans font-medium text-charcoal-600 hover:text-navy-900 inline-flex items-center gap-1"
                  title="Copy original extracted text"
                >
                  {copiedOriginal ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3 text-gold-700" />}
                  <span>{copiedOriginal ? 'Copied' : 'Copy'}</span>
                </button>
              </div>

              <div
                className={`text-xs text-charcoal-800 leading-relaxed font-sans whitespace-pre-line ${
                  showFullText ? '' : 'max-h-96 overflow-y-auto'
                }`}
              >
                {pages.length > 0 ? (
                  pages.map((p: any, idx: number) => (
                    <div key={idx} className="mb-4 last:mb-0">
                      <div className="font-serif font-bold text-navy-900 text-xs mb-1 text-gold-700">
                        [Page {p.pageNumber || idx + 1} &bull; {p.extractionMethod === 'native' ? 'Digital' : `OCR ${p.scriptType || 'printed'}`}]
                      </div>
                      <div className="leading-relaxed">
                        {renderTextWithOcrWarnings(p.text || '')}
                      </div>
                    </div>
                  ))
                ) : (
                  <div>{renderTextWithOcrWarnings(fullExtractedText)}</div>
                )}
              </div>
            </div>

            {/* Right Pane: Translated */}
            <div className="border border-gold-500/40 rounded-lg bg-white p-4 space-y-2.5 shadow-sm">
              <div className="flex items-center justify-between border-b border-ivory-200 pb-2">
                <span className="text-xs font-serif font-bold text-navy-900 flex items-center gap-1.5">
                  <Languages className="w-3.5 h-3.5 text-gold-600" />
                  <span>
                    Legal Translation ({translationResult.targetLanguage === 'hi' ? 'Hindi / हिन्दी' : 'English'})
                  </span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCopyTranslation}
                    className="text-[11px] font-sans font-medium text-charcoal-600 hover:text-navy-900 inline-flex items-center gap-1"
                    title="Copy translated text to clipboard"
                  >
                    {copiedTranslation ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3 text-gold-700" />}
                    <span>{copiedTranslation ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadTranslation}
                    className="text-[11px] font-sans font-medium text-navy-900 hover:text-gold-700 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-ivory-100 hover:bg-ivory-200 border border-ivory-300"
                    title="Download translated text as UTF-8 file"
                  >
                    <Download className="w-3 h-3 text-gold-700" />
                    <span>Download</span>
                  </button>
                </div>
              </div>

              <div
                className={`text-xs text-charcoal-900 leading-relaxed font-sans whitespace-pre-line ${
                  showFullText ? '' : 'max-h-96 overflow-y-auto'
                }`}
              >
                {translationResult.translatedText}
              </div>
            </div>
          </div>
        ) : translationResult && viewMode === 'translated' ? (
          <div className="border border-gold-500/40 rounded-lg bg-white p-4 space-y-2.5 shadow-sm">
            <div className="flex items-center justify-between border-b border-ivory-200 pb-2">
              <span className="text-xs font-serif font-bold text-navy-900 flex items-center gap-1.5">
                <Languages className="w-3.5 h-3.5 text-gold-600" />
                <span>
                  Legal Translation ({translationResult.targetLanguage === 'hi' ? 'Hindi / हिन्दी' : 'English'})
                </span>
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyTranslation}
                  className="text-xs font-sans font-medium text-charcoal-600 hover:text-navy-900 inline-flex items-center gap-1"
                >
                  {copiedTranslation ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5 text-gold-700" />}
                  <span>{copiedTranslation ? 'Copied' : 'Copy Translation'}</span>
                </button>
                <button
                  type="button"
                  onClick={handleDownloadTranslation}
                  className="text-xs font-sans font-medium text-navy-900 hover:text-gold-700 inline-flex items-center gap-1 px-2.5 py-1 rounded bg-ivory-100 hover:bg-ivory-200 border border-ivory-300"
                >
                  <Download className="w-3.5 h-3.5 text-gold-700" />
                  <span>Download .txt</span>
                </button>
              </div>
            </div>

            <div
              className={`p-2 text-xs text-charcoal-900 leading-relaxed font-sans whitespace-pre-line ${
                showFullText ? '' : 'max-h-96 overflow-y-auto'
              }`}
            >
              {translationResult.translatedText}
            </div>
          </div>
        ) : (
          /* Default Original Text View */
          <div
            className={`p-4 rounded bg-ivory-50 border border-ivory-200 text-xs text-charcoal-800 leading-relaxed font-sans whitespace-pre-line ${
              showFullText ? '' : 'max-h-72 overflow-y-auto'
            }`}
          >
            {pages.length > 0 ? (
              pages.map((p: any, idx: number) => (
                <div key={idx} className="mb-4 last:mb-0">
                  <div className="font-serif font-bold text-navy-900 text-xs mb-1 text-gold-700">
                    [Page {p.pageNumber || idx + 1} &bull; {p.extractionMethod === 'native' ? 'Digital Native' : `OCR ${p.scriptType || 'printed'}`}]
                  </div>
                  <div className="leading-relaxed">
                    {renderTextWithOcrWarnings(p.text || '')}
                  </div>
                </div>
              ))
            ) : (
              <div>{renderTextWithOcrWarnings(fullExtractedText)}</div>
            )}
          </div>
        )}

        {/* Legal Evidentiary Translation Disclaimer */}
        <div className="bg-ivory-100/70 border border-ivory-300 rounded p-3 text-[11px] text-charcoal-700 flex items-start gap-2">
          <ShieldAlert className="w-4 h-4 text-gold-700 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-navy-950 font-serif">Legal Practice &amp; Translation Notice:</span>
            <p className="leading-relaxed">
              Machine-generated translations are provided for preliminary legal research and reference only. Under Supreme Court of India Rules and High Court Directives, non-English court pleadings, vernacular FIRs, or local testimonies relied upon in substantive appellate proceedings must be accompanied by an Advocate’s or Certified Translator’s verification. Case citations and statutory section numbers are preserved as verbatim tokens.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
