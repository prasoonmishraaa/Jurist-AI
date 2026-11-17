import React from 'react';
import { Link } from 'react-router-dom';
import {
  Scale,
  BookOpen,
  ArrowRight,
  CheckCircle,
  AlertTriangle,
  Gavel,
  ScrollText,
  ShieldAlert
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-20 pb-20 bg-ivory-100 text-charcoal-800">
      {/* Judiciary Hero */}
      <section className="relative bg-navy-950 text-white pt-16 sm:pt-24 pb-20 sm:pb-24 px-4 sm:px-6 lg:px-8 border-b-2 border-gold-500/40">
        <div className="max-w-5xl mx-auto text-center space-y-7">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded bg-navy-900 border border-gold-500/40 text-gold-300 text-xs font-semibold tracking-wider uppercase">
            <Scale className="w-4 h-4 text-gold-400" />
            <span>Indian Legal Research &amp; Litigation Support</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-serif font-bold tracking-tight text-white leading-tight">
            Structured Legal Analysis, <br className="hidden sm:inline" />
            <span className="text-gold-400 font-serif italic">
              Verified Indian Judgments &amp; Submissions
            </span>
          </h1>

          <p className="text-sm sm:text-lg text-charcoal-200 max-w-3xl mx-auto font-sans font-light leading-relaxed">
            Built for advocates, judicial researchers, and law students preparing matters before Indian courts. Organize material facts from allegations, determine pre- and post-1 July 2024 statutory codes, examine Supreme Court ratios under Article 141, and draft editable grounds with anticipated rebuttals.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-3">
            <Link
              to="/register"
              className="w-full sm:w-auto px-7 py-3.5 rounded bg-gold-500 hover:bg-gold-600 text-navy-950 font-serif font-bold text-sm tracking-wide transition-colors shadow-judicial flex items-center justify-center gap-2"
            >
              <span>Open Research Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/precedents"
              className="w-full sm:w-auto px-7 py-3.5 rounded bg-navy-900 text-charcoal-100 hover:bg-navy-800 hover:text-white border border-gold-500/35 text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <BookOpen className="w-4 h-4 text-gold-400" />
              <span>Browse Judgment Library</span>
            </Link>
          </div>

          {/* Grounded Platform Pillars */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-10 border-t border-navy-800 text-left">
            <div className="bg-navy-900 p-4 rounded border border-gold-500/25">
              <span className="block text-xl font-serif font-bold text-gold-400">IPC/CrPC &amp; BNS/BNSS</span>
              <span className="text-xs text-charcoal-300">Date-Aware 1 July 2024 Regime Check</span>
            </div>
            <div className="bg-navy-900 p-4 rounded border border-gold-500/25">
              <span className="block text-xl font-serif font-bold text-white">Source Verified</span>
              <span className="text-xs text-charcoal-300">Official Court PDFs &amp; Explicit Labels</span>
            </div>
            <div className="bg-navy-900 p-4 rounded border border-gold-500/25">
              <span className="block text-xl font-serif font-bold text-gold-300">Adversarial Audit</span>
              <span className="text-xs text-charcoal-300">Opposing Submissions &amp; Rebuttals</span>
            </div>
            <div className="bg-navy-900 p-4 rounded border border-gold-500/25">
              <span className="block text-xl font-serif font-bold text-white">Editable Dossier</span>
              <span className="text-xs text-charcoal-300">Exportable Grounds &amp; Notes</span>
            </div>
          </div>
        </div>
      </section>

      {/* Core Capabilities */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-burgundy-900">
            <Gavel className="w-3.5 h-3.5 text-gold-600" />
            <span>Litigation Workflow</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-navy-900">
            From Raw Facts to Structured Research Memoranda
          </h2>
          <p className="text-charcoal-600 text-sm leading-relaxed">
            Designed to keep every legal conclusion traceable to supplied facts, explicit statutory text, and primary court decisions—never unverified claims.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded border border-gold-500/35 p-6 parchment-card space-y-4">
            <div className="w-11 h-11 rounded bg-navy-900 border border-gold-500/40 flex items-center justify-center text-gold-400">
              <Scale className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-serif font-bold text-navy-900">Fact vs. Allegation Discipline</h3>
            <p className="text-sm text-charcoal-600 leading-relaxed">
              Separates dated user-provided facts, contested party allegations, custody posture, and missing evidence rather than assuming unproved points or inventing litigants.
            </p>
            <ul className="text-xs text-charcoal-600 space-y-1.5 pt-3 border-t border-ivory-200">
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-gold-700 shrink-0" />
                <span>Chronology with source verification status</span>
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-gold-700 shrink-0" />
                <span>Actionable missing-document checklist</span>
              </li>
            </ul>
          </div>

          <div className="bg-white rounded border border-gold-500/35 p-6 parchment-card space-y-4">
            <div className="w-11 h-11 rounded bg-navy-900 border border-gold-500/40 flex items-center justify-center text-gold-400">
              <ScrollText className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-serif font-bold text-navy-900">Grounds &amp; Article 141 Ratios</h3>
            <p className="text-sm text-charcoal-600 leading-relaxed">
              Drafts structured legal grounds paired with Supreme Court and High Court ratios, expressly distinguishing factual settings and special enactments.
            </p>
            <ul className="text-xs text-charcoal-600 space-y-1.5 pt-3 border-t border-ivory-200">
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-gold-700 shrink-0" />
                <span>Editable draft paragraphs saved to your brief</span>
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-gold-700 shrink-0" />
                <span>Ratio decidendi vs. obiter distinctions</span>
              </li>
            </ul>
          </div>

          <div className="bg-white rounded border border-gold-500/35 p-6 parchment-card space-y-4">
            <div className="w-11 h-11 rounded bg-navy-900 border border-gold-500/40 flex items-center justify-center text-burgundy-200">
              <ShieldAlert className="w-5 h-5 text-gold-400" />
            </div>
            <h3 className="text-lg font-serif font-bold text-navy-900">Counterarguments &amp; Rebuttals</h3>
            <p className="text-sm text-charcoal-600 leading-relaxed">
              Identifies statutory exceptions and likely objections from the opposing side, alongside evidence required and tailored rebuttal strategies.
            </p>
            <ul className="text-xs text-charcoal-600 space-y-1.5 pt-3 border-t border-ivory-200">
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-gold-700 shrink-0" />
                <span>No speculative percentage win predictions</span>
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-gold-700 shrink-0" />
                <span>Exportable to Markdown, Text &amp; Print</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Analytical Pipeline */}
      <section id="methodology" className="bg-white py-14 px-4 sm:px-6 lg:px-8 border-y border-ivory-300">
        <div className="max-w-7xl mx-auto space-y-10">
          <div className="text-center space-y-2">
            <span className="text-xs font-serif font-semibold uppercase tracking-widest text-burgundy-900">
              Research Methodology
            </span>
            <h2 className="text-2xl sm:text-3xl font-serif font-bold text-navy-900">
              Six-Stage Case Structuring Process
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                num: '1',
                title: 'Document & Fact Ingestion',
                desc: 'Accepts manual narratives and text-searchable PDF, DOCX, and TXT files, isolating key dates and rejecting unreadable scans.'
              },
              {
                num: '2',
                title: 'Statutory Regime & Date Check',
                desc: 'Evaluates offence, FIR, and arrest dates against the 1 July 2024 commencement threshold separating IPC/CrPC/IEA from BNS/BNSS/BSA.'
              },
              {
                num: '3',
                title: 'Custody Posture & Remedies',
                desc: 'Determines whether a party is already in custody, apprehending arrest, or seeking civil relief before suggesting appropriate remedies.'
              },
              {
                num: '4',
                title: 'Precedent Ranking & Verification',
                desc: 'Matches statutory provisions and factual patterns across verified Indian judgments, visibly flagging official PDF vs. secondary index status.'
              },
              {
                num: '5',
                title: 'Submissions & Rebuttal Drafting',
                desc: 'Builds editable draft submissions under Article 141 ratios alongside opposing arguments, factual vulnerabilities, and evidentiary gaps.'
              },
              {
                num: '6',
                title: 'Qualitative Doctrinal Assessment',
                desc: 'Summarizes supporting and adverse authorities without misleading numeric court prediction scores.'
              }
            ].map((step) => (
              <div key={step.num} className="bg-ivory-100 p-5 rounded border border-gold-500/25 space-y-2">
                <div className="text-xs font-serif font-bold text-burgundy-900 flex items-center gap-2">
                  <span className="w-6 h-6 rounded bg-navy-900 text-gold-400 flex items-center justify-center text-xs">
                    {step.num}
                  </span>
                  <span>{step.title}</span>
                </div>
                <p className="text-xs text-charcoal-600 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Precedent Standards */}
      <section id="compliance" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-xs font-serif font-semibold uppercase tracking-widest text-burgundy-900">
              Curated Authority Corpus
            </span>
            <h2 className="text-2xl sm:text-3xl font-serif font-bold text-navy-900">
              Verified Supreme Court &amp; High Court Decisions
            </h2>
            <p className="text-sm text-charcoal-600 mt-1">
              Includes landmark constitutional, criminal procedure (arrest, grounds of arrest, bail, FIR, quashing), cheque dishonour, and commercial authorities.
            </p>
          </div>
          <Link
            to="/precedents"
            className="text-xs font-semibold uppercase tracking-wider text-burgundy-900 hover:text-navy-900 inline-flex items-center gap-1.5"
          >
            <span>Explore Full Precedent Corpus</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="p-5 rounded bg-white border border-gold-500/35 parchment-card space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-navy-900 bg-ivory-200 px-2.5 py-1 rounded border border-gold-500/20">
                Supreme Court (9-Judge Constitution Bench)
              </span>
              <span className="font-mono text-burgundy-900 font-bold">(2017) 10 SCC 1; [2017] 10 S.C.R. 569</span>
            </div>
            <h4 className="font-serif font-bold text-navy-900 text-base">
              Justice K.S. Puttaswamy (Retd.) and Anr. v. Union of India and Ors.
            </h4>
            <p className="text-xs text-charcoal-600 leading-relaxed">
              Affirmed privacy as an intrinsic facet of Article 21 life and personal liberty and articulated legality, legitimate aim, necessity, and proportionality standards.
            </p>
            <div className="text-[11px] text-charcoal-500 flex items-center justify-between pt-2 border-t border-ivory-200">
              <span>Provisions: Articles 14, 19 &amp; 21</span>
              <span className="text-navy-900 font-semibold">Official SCI PDF Verified</span>
            </div>
          </div>

          <div className="p-5 rounded bg-white border border-gold-500/35 parchment-card space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-navy-900 bg-ivory-200 px-2.5 py-1 rounded border border-gold-500/20">
                Supreme Court of India
              </span>
              <span className="font-mono text-burgundy-900 font-bold">(2025) 5 SCC 799; [2025] 2 S.C.R. 224</span>
            </div>
            <h4 className="font-serif font-bold text-navy-900 text-base">
              Vihaan Kumar v. State of Haryana and Anr.
            </h4>
            <p className="text-xs text-charcoal-600 leading-relaxed">
              Held that informing an arrestee of written grounds of arrest under Article 22(1) and S. 50 CrPC / S. 47 BNSS is mandatory across ordinary criminal law, and its breach vitiates arrest and remand.
            </p>
            <div className="text-[11px] text-charcoal-500 flex items-center justify-between pt-2 border-t border-ivory-200">
              <span>Provisions: Art. 22(1), S. 50 CrPC / S. 47 BNSS</span>
              <span className="text-navy-900 font-semibold">Official SCI e-SCR PDF Verified</span>
            </div>
          </div>
        </div>
      </section>

      {/* Legal Notice */}
      <section id="disclaimer" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white border border-gold-500/40 rounded p-6 md:p-8 space-y-3 parchment-card">
          <div className="flex items-center gap-2.5 text-navy-950 font-serif font-bold text-sm sm:text-base">
            <AlertTriangle className="w-5 h-5 text-burgundy-900 shrink-0" />
            <span>MANDATORY LEGAL RESEARCH NOTICE</span>
          </div>
          <p className="text-xs sm:text-sm text-charcoal-600 leading-relaxed font-sans">
            <strong>JURIST AI</strong> is a legal research and drafting-support tool. It does <strong>not</strong> constitute a law firm, does not establish an advocate–client relationship, and does not provide formal legal advice or court outcome guarantees. Users must independently verify cited statutory amendments, local High Court Rules, and certified copies of judicial orders prior to court filing.
          </p>
        </div>
      </section>
    </div>
  );
};
