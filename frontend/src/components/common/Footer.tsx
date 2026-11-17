import React from 'react';
import { Scale, ShieldCheck, AlertCircle } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-navy-950 border-t border-gold-500/20 text-charcoal-400 text-xs py-10 no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-8 border-b border-navy-800">
          <div className="space-y-3 md:col-span-2">
            <div className="flex items-center space-x-2 text-white font-serif font-bold text-base">
              <Scale className="w-5 h-5 text-gold-400" />
              <span>JURIST AI</span>
              <span className="text-gold-300 font-sans font-normal text-xs px-2 py-0.5 rounded bg-navy-900 border border-gold-500/30">
                Legal Research &amp; Case Analysis
              </span>
            </div>
            <p className="text-charcoal-400 max-w-lg leading-relaxed text-xs">
              A structured Indian legal research and litigation-support workspace designed for Advocates, judicial researchers, and law students—combining chronology organization, date-aware statutory mapping across IPC/CrPC/IEA and BNS/BNSS/BSA, verified precedent retrieval, and draft court submissions.
            </p>
            <div className="text-[11px] text-charcoal-500 flex items-start gap-1.5 pt-1">
              <AlertCircle className="w-3.5 h-3.5 text-gold-400/80 shrink-0 mt-0.5" />
              <span>
                Independent legal research platform. Not a law firm, not an official registry of any court, and not a substitute for independent advice from qualified counsel.
              </span>
            </div>
          </div>

          <div>
            <h5 className="font-serif font-semibold text-gold-300 mb-3 uppercase tracking-wider text-[11px]">
              Practice Domains
            </h5>
            <ul className="space-y-1.5 text-charcoal-400">
              <li>Constitutional Writs (Art. 226 &amp; Art. 32)</li>
              <li>Arrest, Remand &amp; Bail Safeguards (CrPC / BNSS)</li>
              <li>FIR Quashing &amp; Cheating Disputes</li>
              <li>Arbitration &amp; Commercial Suits (1996 Act)</li>
              <li>Cheque Dishonour (S. 138 / 139 NI Act)</li>
            </ul>
          </div>

          <div>
            <h5 className="font-serif font-semibold text-gold-300 mb-3 uppercase tracking-wider text-[11px]">
              Source Verification
            </h5>
            <ul className="space-y-1.5 text-charcoal-400">
              <li>Supreme Court of India Official Judgments</li>
              <li>Supreme Court Reports (e-SCR) Citations</li>
              <li>Verified High Court Public Orders</li>
              <li>Indian Kanoon Reference Index</li>
            </ul>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between text-charcoal-400 gap-4 text-[11px]">
          <p>© {new Date().getFullYear()} JURIST AI. Indian Legal Research &amp; Litigation Support.</p>
          <div className="flex items-center space-x-2 text-charcoal-300">
            <ShieldCheck className="w-4 h-4 text-gold-400" />
            <span>Source-Verified Citations • Confidential Dossier Workflow</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
