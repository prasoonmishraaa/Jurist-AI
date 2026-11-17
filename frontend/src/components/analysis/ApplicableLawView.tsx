import React from 'react';
import { ApplicableLawAssessment } from '../../types';
import { BookOpen, Calendar, AlertTriangle, Scale, CheckCircle2 } from 'lucide-react';

export const ApplicableLawView: React.FC<{ law?: ApplicableLawAssessment }> = ({ law }) => {
  if (!law) return null;

  const regimeBadgeMap: Record<ApplicableLawAssessment['regimeStatus'], { label: string; style: string }> = {
    post_july_2024_new_codes: {
      label: 'Post-1 July 2024 Regime (BNS / BNSS / BSA)',
      style: 'bg-navy-50 text-navy-900 border-navy-300'
    },
    pre_july_2024_legacy_codes: {
      label: 'Pre-1 July 2024 Legacy Codes (IPC / CrPC / IEA — S. 531 BNSS)',
      style: 'bg-ivory-200 text-charcoal-900 border-gold-500'
    },
    transitional_mixed: {
      label: 'Transitional Straddling Matter (Verify Offence vs FIR Dates)',
      style: 'bg-burgundy-50 text-burgundy-900 border-burgundy-300'
    },
    uncertain_missing_dates: {
      label: 'Dates Missing — Parallel IPC/BNS & CrPC/BNSS Review Required',
      style: 'bg-gold-100 text-gold-900 border-gold-500'
    },
    civil_special_statute: {
      label: 'Constitutional / Civil / Special Statute Governance',
      style: 'bg-navy-50 text-navy-900 border-navy-200'
    }
  };

  const badge = regimeBadgeMap[law.regimeStatus] || regimeBadgeMap.uncertain_missing_dates;

  return (
    <div className="space-y-6">
      {/* Regime Determination Banner */}
      <div className="parchment-card rounded p-5 space-y-3 border-l-4 border-l-burgundy-900">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-2">
            <Scale className="w-4 h-4 text-gold-600" />
            <span>Date-Aware Statutory Regime Determination</span>
          </h3>
          <span className={`text-[11px] font-semibold px-3 py-1 rounded border ${badge.style}`}>
            {badge.label}
          </span>
        </div>

        <p className="text-xs text-charcoal-700 leading-relaxed bg-ivory-50 p-3.5 rounded border border-ivory-200">
          {law.regimeSummary}
        </p>

        {/* Extracted vs Missing Transition Dates */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
          <div className="bg-white border border-ivory-300 rounded p-3.5 space-y-2">
            <h4 className="font-serif font-bold text-navy-900 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-gold-600" />
              <span>Detected Dates in Record</span>
            </h4>
            {law.detectedDates && law.detectedDates.length > 0 ? (
              <ul className="space-y-1.5">
                {law.detectedDates.map((d, i) => (
                  <li key={i} className="bg-ivory-50 p-2 rounded border border-ivory-200">
                    <span className="font-mono font-bold text-navy-900">{d.rawDate}</span>{' '}
                    <span className="uppercase text-[10px] font-semibold text-burgundy-900 px-1.5 py-0.5 bg-burgundy-50 rounded border border-burgundy-200">
                      {d.role}
                    </span>
                    <p className="text-[11px] text-charcoal-600 mt-1">{d.contextSnippet}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-charcoal-500 italic">No explicit calendar dates found in supplied facts.</p>
            )}
          </div>

          <div className="bg-gold-50/50 border border-gold-400 rounded p-3.5 space-y-2">
            <h4 className="font-serif font-bold text-burgundy-900 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-burgundy-800" />
              <span>Missing Dates Affecting Governing Code</span>
            </h4>
            {law.missingDates && law.missingDates.length > 0 ? (
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-800">
                {law.missingDates.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            ) : (
              <p className="text-navy-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-navy-700" />
                <span>Key transition dates were provided for statutory classification.</span>
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Substantive vs Procedural vs Evidentiary Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="parchment-card rounded p-5 space-y-3">
          <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-burgundy-900 border-b border-ivory-200 pb-2 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-gold-600" />
            <span>Substantive Provisions</span>
          </h4>
          {law.substantiveLaw && law.substantiveLaw.length > 0 ? (
            <div className="space-y-3 text-xs">
              {law.substantiveLaw.map((item, i) => (
                <div key={i} className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
                  <p className="font-serif font-bold text-navy-900">{item.provision}</p>
                  <p className="text-[11px] font-semibold text-burgundy-900">{item.statute}</p>
                  <p className="text-charcoal-700 leading-relaxed">{item.applicabilityNote}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-charcoal-500 italic">No specific substantive offence section verified from brief.</p>
          )}
        </div>

        <div className="parchment-card rounded p-5 space-y-3">
          <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-burgundy-900 border-b border-ivory-200 pb-2 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-gold-600" />
            <span>Procedural &amp; Constitutional Safeguards</span>
          </h4>
          {law.proceduralLaw && law.proceduralLaw.length > 0 ? (
            <div className="space-y-3 text-xs">
              {law.proceduralLaw.map((item, i) => (
                <div key={i} className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
                  <p className="font-serif font-bold text-navy-900">{item.provision}</p>
                  <p className="text-[11px] font-semibold text-burgundy-900">{item.statute}</p>
                  <p className="text-charcoal-700 leading-relaxed">{item.applicabilityNote}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-charcoal-500 italic">No separate procedural track flagged.</p>
          )}

          {law.evidenceLaw && (
            <div className="bg-white p-3 rounded border border-gold-400 text-xs space-y-1 mt-2">
              <p className="font-serif font-bold text-navy-900">{law.evidenceLaw.statute}</p>
              <p className="text-charcoal-700 leading-relaxed">{law.evidenceLaw.applicabilityNote}</p>
            </div>
          )}
        </div>
      </div>

      {/* Transitional & Verification Checklists */}
      {(law.transitionalNotes?.length > 0 || law.verificationRequired?.length > 0) && (
        <div className="parchment-card rounded p-5 space-y-3 text-xs">
          <h4 className="font-serif font-bold text-navy-900 uppercase tracking-wide border-b border-ivory-200 pb-2">
            Section 531 BNSS Transitional &amp; Counsel Verification Notes
          </h4>
          <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
            {(law.transitionalNotes || []).map((t, i) => (
              <li key={`t-${i}`}>{t}</li>
            ))}
            {(law.verificationRequired || []).map((v, i) => (
              <li key={`v-${i}`} className="text-burgundy-900">
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
