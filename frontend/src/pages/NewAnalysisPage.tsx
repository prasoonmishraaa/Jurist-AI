import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Scale,
  Upload,
  FileText,
  AlertCircle,
  ArrowRight,
  X,
  Gavel,
  BookOpen,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  Languages
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { SpeechToTextButton } from '../components/common/SpeechToTextButton';

const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'];
const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // 15 MB

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const getFileExtension = (filename: string): string => {
  const parts = filename.split('.');
  return parts.length > 1 ? (parts.pop() || '').toLowerCase() : '';
};

const PRESET_CASES = [
  {
    label: 'Cheating Arrest Without Written Grounds (Post-July 2024 BNSS)',
    title: 'Challenge to Unlawful Arrest & Remand Without Written Grounds',
    court: 'High Court of Delhi',
    category: 'Criminal Law',
    text: 'An offence was alleged on 5 October 2024 in a commercial supply dispute. FIR was registered on 10 October 2024 alleging cheating and dishonestly inducing delivery of property. Police arrested the Accused on 14 October 2024 without serving pre-arrest notice, did not communicate written grounds of arrest under Article 22(1) / Section 47 BNSS, and produced him before the Magistrate beyond 24 hours for remand.'
  },
  {
    label: 'Informational Privacy & Surveillance (Art. 21)',
    title: 'Writ Petition: Telecom Interception & Biometric Surveillance',
    court: 'Supreme Court of India',
    category: 'Constitutional Law',
    text: 'Petitioner challenges executive interception of digital communications and retention of biometric metadata on 18 August 2024 without prior judicial authorization or statutory safeguards, alleging transgression of Article 21 privacy and proportionality standards laid down in Justice K.S. Puttaswamy (Retd.) v. Union of India.'
  },
  {
    label: 'Cheque Dishonour & S. 139 Presumption (NI Act)',
    title: 'Section 138 NI Act Appeal — Blank Signed Security Cheque Defence',
    court: 'High Court of Bombay',
    category: 'Banking & Negotiable Instruments',
    text: 'Appellant handed over a blank signed security cheque during a trade agreement dated 15 February 2024. Following stop-payment and dishonour for insufficient funds, a demand notice and complaint under Section 138 Negotiable Instruments Act, 1881 were instituted. Appellant pleads that underlying dues were settled prior to presentation, seeking rebuttal of the Section 139 presumption.'
  },
  {
    label: 'Quashing of Commercial FIR (S. 482 CrPC / S. 528 BNSS)',
    title: 'Petition for Quashing Civil-Dispute FIR Under Bhajan Lal Guidelines',
    court: 'High Court of Delhi',
    category: 'Criminal Law',
    text: 'FIR registered on 10 May 2023 under Sections 420 and 406 IPC arising out of unpaid invoices under a software services agreement. Petitioners seek quashing under Section 482 CrPC contending the dispute is purely civil/contractual without initial fraudulent intent at inception, attracting State of Haryana v. Bhajan Lal principles.'
  },
  {
    label: 'Arbitration Clause Enforcement (S. 8 Arb. Act)',
    title: 'Section 8 Reference Application in Commercial Recovery Suit',
    court: 'High Court of Bombay',
    category: 'Corporate & Commercial Law',
    text: 'Plaintiff filed a commercial suit on 20 September 2024 for recovery under a Master Services Agreement containing a valid arbitration clause. Defendant seeks reference to arbitration under Section 8 of the Arbitration and Conciliation Act, 1996 citing Vidya Drolia v. Durga Trading Corporation.'
  }
];

export const NewAnalysisPage: React.FC = () => {
  const [title, setTitle] = useState('');
  const [court, setCourt] = useState('Supreme Court of India');
  const [category, setCategory] = useState('Criminal Law');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [documentLanguage, setDocumentLanguage] = useState<'auto' | 'en' | 'hi'>('auto');
  const [analysisLanguage] = useState<'en'>('en');
  const [translateForAnalysis, setTranslateForAnalysis] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const dragCounterRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const navigate = useNavigate();

  const handleApplyPreset = (preset: (typeof PRESET_CASES)[0]) => {
    setTitle(preset.title);
    setCourt(preset.court);
    setCategory(preset.category);
    setDescription(preset.text);
    setError(null);
  };

  const validateAndSetFile = (selected: File): boolean => {
    const ext = getFileExtension(selected.name);
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      setError(
        `Unsupported file format '.${ext || 'unknown'}'. Accepted formats: PDF (.pdf), Word (.docx), plain text (.txt), and image files (.png, .jpg, .jpeg).`
      );
      return false;
    }
    if (selected.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (selected.size / (1024 * 1024)).toFixed(1);
      setError(
        `Document exceeds the 15 MB limit (selected file is ${sizeMB} MB). Please upload a smaller file or split large annexures.`
      );
      return false;
    }
    setFile(selected);
    setError(null);
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'copy';
    if (!isDragging) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      dragCounterRef.current = 0;
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = 0;
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDropzoneKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!description.trim() && !file) {
      setError('Please enter case facts or upload a readable PDF, DOCX, TXT, or image document.');
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append('title', title.trim() || 'Legal Research Memorandum');
      formData.append('caseTitle', title.trim() || 'Legal Research Memorandum');
      formData.append('court', court);
      formData.append('category', category);
      formData.append('documentLanguage', documentLanguage);
      formData.append('analysisLanguage', analysisLanguage);
      formData.append('translateForAnalysis', String(translateForAnalysis));
      if (description.trim()) {
        formData.append('description', description.trim());
      }
      if (file) {
        formData.append('document', file);
      }

      const result = await api.createAnalysis(formData);
      navigate(`/dashboard/analysis/${result.id || result._id}`);
    } catch (err: any) {
      setError(
        err.response?.data?.error ||
          err.message ||
          'Unable to complete case analysis. Please verify input length or document readability.'
      );
      setIsSubmitting(false);
    }
  };

  if (isSubmitting) {
    return (
      <div className="bg-white rounded border border-gold-500/30 p-12 text-center shadow-judicial">
        <LoadingSpinner message="Evaluating document structure, executing OCR / native extraction, classifying facts, matching verified judgments, and preparing draft submissions..." />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 bg-ivory-100">
      <div className="space-y-1.5">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-serif font-semibold uppercase tracking-widest text-burgundy-900">
          <Gavel className="w-3.5 h-3.5 text-gold-600" />
          <span>New Matter Intake</span>
        </div>
        <h1 className="text-2xl font-serif font-bold text-navy-900">
          Prepare Legal Research &amp; Case Submissions
        </h1>
        <p className="text-xs text-charcoal-600">
          Provide factual particulars including exact dates (alleged offence, FIR registration, arrest/action) or attach a searchable pleading/FIR file to receive structured legislation analysis, authorities, and editable court grounds.
        </p>
      </div>

      {/* Reference Scenarios */}
      <div className="bg-white rounded border border-gold-500/35 p-4 parchment-card space-y-2.5">
        <span className="text-xs font-serif font-semibold text-navy-900 flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-gold-600" />
          <span>Sample Matter Templates (Click to Populate):</span>
        </span>
        <div className="flex flex-wrap gap-2">
          {PRESET_CASES.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyPreset(preset)}
              className="text-xs font-sans font-medium px-3 py-1.5 rounded bg-ivory-100 hover:bg-navy-900 hover:text-gold-300 border border-gold-500/30 transition-colors text-charcoal-700 text-left"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-burgundy-50 border border-burgundy-900/30 rounded text-xs text-burgundy-900 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-burgundy-800" />
          <span>{error}</span>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded border border-gold-500/35 p-6 sm:p-8 shadow-judicial parchment-card space-y-6"
      >
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-serif font-semibold text-charcoal-700">
              Matter Title / Reference <span className="text-burgundy-900">*</span>
            </label>
            <SpeechToTextButton
              onTranscript={(transcript) => {
                setTitle((prev) => (prev ? `${prev} ${transcript}` : transcript));
              }}
              size="sm"
              title="Dictate matter title"
            />
          </div>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Writ Petition — Challenge to Arrest Without Written Grounds"
            className="w-full px-3.5 py-2.5 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-navy-900 focus:ring-1 focus:ring-navy-900 transition-colors font-sans"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-serif font-semibold text-charcoal-700 mb-1">
              Target Forum
            </label>
            <select
              value={court}
              onChange={(e) => setCourt(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-navy-900 focus:ring-1 focus:ring-navy-900 transition-colors font-sans"
            >
              <option value="Supreme Court of India">Supreme Court of India</option>
              <option value="High Court of Delhi">High Court of Delhi</option>
              <option value="High Court of Bombay">High Court of Bombay</option>
              <option value="High Court of Judicature at Allahabad">High Court of Judicature at Allahabad</option>
              <option value="High Court of Judicature at Madras">High Court of Judicature at Madras</option>
              <option value="High Court of Calcutta">High Court of Calcutta</option>
              <option value="Sessions Court / Magistrate Court">Sessions / Magistrate Court</option>
              <option value="National Company Law Tribunal">National Company Law Tribunal (NCLT)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-serif font-semibold text-charcoal-700 mb-1">
              Primary Legal Domain
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-navy-900 focus:ring-1 focus:ring-navy-900 transition-colors font-sans"
            >
              <option value="Criminal Law">Criminal Law</option>
              <option value="Constitutional Law">Constitutional Law</option>
              <option value="Corporate & Commercial Law">Corporate &amp; Commercial Law</option>
              <option value="Banking & Negotiable Instruments">Banking &amp; Negotiable Instruments</option>
              <option value="Intellectual Property Law">Intellectual Property Law</option>
              <option value="Cyber & Information Technology Law">Cyber &amp; Information Technology Law</option>
              <option value="Family Law">Family Law</option>
              <option value="Labour & Service Law">Labour &amp; Service Law</option>
              <option value="Civil Law">Civil Law</option>
            </select>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-serif font-semibold text-charcoal-700">
              Factual Statement &amp; Procedural Posture {!file && <span className="text-burgundy-900">*</span>}
            </label>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-charcoal-500 hidden sm:inline">Voice Dictation:</span>
              <SpeechToTextButton
                onTranscript={(transcript) => {
                  setDescription((prev) => (prev ? `${prev.trim()}\n${transcript}` : transcript));
                }}
                size="sm"
                title="Dictate factual statement using microphone"
              />
            </div>
          </div>
          <textarea
            rows={6}
            required={!file}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="State known facts chronologically (include offence date, FIR registration date, arrest/remand status, or contractual timeline). Clearly distinguish disputed allegations from admitted facts..."
            className="w-full px-3.5 py-2.5 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-navy-900 focus:ring-1 focus:ring-navy-900 transition-colors leading-relaxed font-sans"
          />
          <span className="text-[11px] text-charcoal-500 block mt-1">
            Including exact dates allows accurate determination between IPC/CrPC/IEA (pre-1 July 2024) and BNS/BNSS/BSA (from 1 July 2024). Voice dictation will insert recognized text without auto-submitting.
          </span>
        </div>

        {/* Enhanced Document Upload & OCR Intelligence Section */}
        <div className="rounded-lg border border-gold-500/40 bg-gradient-to-b from-ivory-50/70 to-white p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-300 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-burgundy-900" />
                <h3 className="text-xs font-serif font-bold uppercase tracking-wider text-navy-900">
                  Document Intelligence &amp; Multi-Page OCR Pipeline
                </h3>
              </div>
              <p className="text-[11px] text-charcoal-600 mt-0.5">
                Upload pleadings, FIRs, order sheets, or handwritten annexures. Native digital text is prioritized; scanned and image pages automatically invoke the Tesseract OCR engine with script analysis.
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 self-start px-2 py-0.5 rounded bg-gold-100 text-gold-900 text-[10px] font-semibold border border-gold-400">
              <Sparkles className="w-3 h-3 text-gold-700" />
              <span>Up to 15 MB</span>
            </div>
          </div>

          {/* Supported Format Badges */}
          <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
            <span className="text-charcoal-500 font-sans font-medium text-[11px] mr-1">Accepted Formats:</span>
            <span className="px-2 py-0.5 rounded bg-white border border-ivory-300 text-navy-950 font-semibold">PDF (Digital &amp; Scanned)</span>
            <span className="px-2 py-0.5 rounded bg-white border border-ivory-300 text-navy-950 font-semibold">Word (.docx)</span>
            <span className="px-2 py-0.5 rounded bg-white border border-ivory-300 text-navy-950 font-semibold">Plain Text (.txt)</span>
            <span className="px-2 py-0.5 rounded bg-white border border-ivory-300 text-navy-950 font-semibold">Images (.png, .jpg, .jpeg)</span>
          </div>

          {/* Dropzone Container */}
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className="relative"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className="hidden"
              tabIndex={-1}
              aria-hidden="true"
            />

            {file ? (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-ivory-50/90 rounded-lg border border-gold-500/60 shadow-sm gap-3">
                <div className="flex items-start sm:items-center space-x-3.5 min-w-0">
                  <div className="w-11 h-11 rounded-md bg-navy-900 text-gold-300 flex items-center justify-center shrink-0 shadow-sm">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div className="text-left min-w-0 space-y-0.5">
                    <p className="text-xs font-serif font-bold text-navy-900 truncate" title={file.name}>
                      {file.name}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-charcoal-600 font-sans">
                      <span>{formatFileSize(file.size)}</span>
                      <span>&bull;</span>
                      <span className="uppercase font-mono px-1.5 py-0.5 rounded bg-white border border-ivory-300 text-navy-950 font-semibold text-[10px]">
                        {getFileExtension(file.name) || 'FILE'}
                      </span>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[10px] text-green-700 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
                      <span>Ready for multi-page OCR extraction &amp; script classification upon dossier assembly</span>
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-2.5 py-1.5 text-xs font-serif font-medium text-navy-900 bg-white hover:bg-ivory-100 border border-ivory-300 rounded shadow-sm transition-colors flex items-center gap-1 focus:outline-none focus:ring-1 focus:ring-navy-900"
                    title="Choose a different document"
                  >
                    <span>Replace</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    aria-label="Remove uploaded document"
                    className="p-1.5 rounded-md hover:bg-burgundy-50 text-charcoal-500 hover:text-burgundy-800 transition-colors focus:outline-none focus:ring-1 focus:ring-burgundy-800"
                    title="Remove document"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={handleDropzoneKeyDown}
                aria-label="Upload legal document. Drag and drop file or press Enter to browse"
                className={`border-2 border-dashed rounded-lg p-6 sm:p-8 text-center transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-navy-900 focus:border-navy-900 ${
                  isDragging
                    ? 'border-gold-600 bg-gold-50/80 shadow-lg ring-4 ring-gold-400/25 scale-[1.008]'
                    : 'border-gold-500/50 bg-white/70 hover:bg-white hover:border-gold-600/80 hover:shadow-sm'
                }`}
              >
                <div className="space-y-2.5 pointer-events-none">
                  <div
                    className={`w-12 h-12 rounded-full mx-auto flex items-center justify-center transition-all duration-200 ${
                      isDragging
                        ? 'bg-gold-200 text-gold-900 scale-110 shadow-sm'
                        : 'bg-ivory-100 text-gold-700'
                    }`}
                  >
                    <Upload className="w-6 h-6" />
                  </div>

                  <div>
                    <span className="text-sm font-serif font-bold text-navy-900 block">
                      {isDragging ? 'Release to Attach Legal Document' : 'Click to Browse or Drag & Drop Legal Document'}
                    </span>
                    <span className="text-xs text-charcoal-600 block font-sans max-w-md mx-auto mt-1 leading-relaxed">
                      {isDragging
                        ? 'Drop your PDF, DOCX, TXT, or scanned image filing here to stage for analysis.'
                        : 'Multi-page PDFs, scanned filings, or handwritten police extracts up to 15 MB will be indexed with page-level confidence diagnostics.'}
                    </span>
                  </div>

                  <div className="pt-1">
                    <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-serif font-semibold bg-ivory-100 text-navy-900 border border-gold-500/40 rounded shadow-sm">
                      <Upload className="w-3.5 h-3.5 text-gold-700" />
                      <span>Browse Document</span>
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Pre-Analysis Multilingual Settings */}
          <div className="rounded border border-gold-500/35 bg-ivory-50/80 p-3.5 space-y-2.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-300 pb-2">
              <div className="flex items-center gap-1.5">
                <Languages className="w-3.5 h-3.5 text-gold-700" />
                <span className="text-xs font-serif font-bold text-navy-900 uppercase tracking-wide">
                  Multilingual Processing &amp; Translation
                </span>
              </div>
              <span className="text-[10.5px] font-mono text-charcoal-500">
                English &bull; हिन्दी (Devanagari)
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-[11px] font-serif font-semibold text-charcoal-700 mb-1">
                  Document Language
                </label>
                <select
                  value={documentLanguage}
                  onChange={(e) => setDocumentLanguage(e.target.value as 'auto' | 'en' | 'hi')}
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-ivory-300 rounded text-navy-900 focus:outline-none focus:border-navy-900 focus:ring-1 focus:ring-navy-900 font-sans"
                >
                  <option value="auto">Auto-detect (Recommended)</option>
                  <option value="en">English</option>
                  <option value="hi">Hindi (हिन्दी Devanagari)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-serif font-semibold text-charcoal-700 mb-1">
                  Analysis Language
                </label>
                <div className="flex items-center justify-between px-2.5 py-1.5 text-xs bg-ivory-100/80 border border-ivory-300 rounded text-charcoal-700 font-sans cursor-not-allowed">
                  <span className="font-medium text-navy-900">English (Appellate Standard)</span>
                  <span className="text-[10px] uppercase font-mono px-1 py-0.2 bg-white rounded border border-ivory-300 text-charcoal-500">Fixed</span>
                </div>
              </div>
            </div>

            <div className="pt-0.5 space-y-1">
              <label className="inline-flex items-center gap-2 cursor-pointer select-none text-xs text-navy-950 font-medium">
                <input
                  type="checkbox"
                  checked={translateForAnalysis}
                  onChange={(e) => setTranslateForAnalysis(e.target.checked)}
                  className="rounded border-ivory-300 text-navy-900 focus:ring-navy-900 w-3.5 h-3.5"
                />
                <span>Translate non-English extracted text into English for legal analysis</span>
              </label>
              <p className="text-[10.5px] text-charcoal-500 leading-relaxed pl-5 font-sans">
                The verified legal research corpus and dual-model judicial outcome estimators operate primarily on Supreme Court and High Court English jurisprudence. Enabling this automatically bridges vernacular FIRs and Hindi pleadings while preserving citations and statutory section numbers.
              </p>
            </div>
          </div>

          {/* Legal AI Safety & Evidentiary Caution Box */}
          <div className="bg-ivory-100/70 border border-ivory-300 rounded p-3 text-[11px] text-charcoal-700 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-gold-700 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-semibold text-navy-950 font-serif">Evidentiary Safety Guarantee:</span>
              <p className="leading-relaxed">
                Handwritten pages are classified separately from machine-printed text and marked with evidentiary caveats. Ambiguous words will be flagged as <code className="px-1 py-0.2 bg-white rounded border border-ivory-300 text-burgundy-900 font-mono text-[10px]">[?token?]</code> and never silently presented as verified court evidence.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-2">
          <button
            type="submit"
            className="w-full py-3 px-6 bg-navy-900 hover:bg-navy-800 text-gold-300 font-serif font-bold rounded border border-gold-500/40 transition-colors shadow-judicial text-sm flex items-center justify-center gap-2"
          >
            <Scale className="w-4 h-4 text-gold-400" />
            <span>Assemble Legal Research Dossier</span>
            <ArrowRight className="w-4 h-4 text-gold-400" />
          </button>
        </div>
      </form>
    </div>
  );
};
