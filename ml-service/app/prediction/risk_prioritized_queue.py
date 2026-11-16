"""
Risk-Based Outcome Annotation Queue Prioritization Engine
JURIST AI — Feature 4.7: Accelerated Risk-Based Human Outcome Annotation

Stratifies judicial outcome candidate records into 4 risk tiers to maximize annotation velocity
while safeguarding legal rigor:
- Tier 1 (Low Risk / Definitive Merits): Non-truncated text, high confidence (>=0.85), unambiguous merits rulings.
- Tier 2 (Moderate Risk / Bail & Substantive Directives): Requires distinguishing provisional liberty vs merits.
- Tier 3 (High Risk / Procedural & Non-Merits Nuance): Remands, partial allowances, withdrawals, infructuous disposals.
- Tier 4 (Critical / Deferred & Truncated): Text >= 39,900 chars, interlocutory references, or conflicting rulings.
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import Counter

logger = logging.getLogger("RiskPrioritizedQueue")


class RiskTier:
    TIER_1_DEFINITIVE_MERITS = "tier_1"
    TIER_2_MODERATE_RISK_BAIL_DIRECTIVES = "tier_2"
    TIER_3_HIGH_RISK_PROCEDURAL = "tier_3"
    TIER_4_CRITICAL_DEFERRED = "tier_4"

    LABELS = {
        "tier_1": "Tier 1: Definitive Merits (Low Risk)",
        "tier_2": "Tier 2: Bail & Substantive Directives (Moderate Risk)",
        "tier_3": "Tier 3: Procedural Nuance & Non-Merits (High Risk)",
        "tier_4": "Tier 4: Truncated & Ambiguous (Critical Risk / Defer)",
    }


class RiskPrioritizer:
    """
    Evaluates candidate judicial decisions for risk factors (truncation, procedural complexity,
    disposition ambiguity) and prioritizes annotation queues.
    """

    TRUNCATION_CHAR_LIMIT = 39900  # Threshold near 40,000 char ingestion cap

    TIER_1_DISPOSITIONS = {
        "appeal_allowed",
        "appeal_dismissed",
        "petition_allowed",
        "petition_dismissed",
    }

    TIER_2_DISPOSITIONS = {
        "bail_granted",
        "bail_rejected",
        "disposed_with_substantive_directions",
    }

    TIER_3_DISPOSITIONS = {
        "remanded",
        "partly_allowed",
        "withdrawn",
        "dismissed_as_infructuous",
        "disposed_procedural",
    }

    TIER_4_DISPOSITIONS = {
        "unknown_truncated_text",
        "unknown",
        "interlocutory_reference",
        "ambiguous",
    }

    def assess_case_risk(self, record: Dict[str, Any], judgment_text: str = "") -> Dict[str, Any]:
        """
        Assesses the risk profile of an individual candidate case.
        Returns risk tier, human-readable label, specific cautionary flags, and recommended mode.
        """
        disp = (record.get("normalized_disposition") or record.get("original_disposition") or "").strip().lower()
        conf = float(record.get("parser_confidence", 0.0))
        text_len = len(judgment_text)
        flags: List[str] = []

        # 1. Critical Risk Checks (Tier 4)
        if text_len >= self.TRUNCATION_CHAR_LIMIT or disp == "unknown_truncated_text":
            tier = RiskTier.TIER_4_CRITICAL_DEFERRED
            flags.append("TRUNCATION_WARNING: Text length >= 39,900 chars; concluding order may be clipped.")
        elif disp in ["interlocutory_reference", "ambiguous", "unknown"]:
            tier = RiskTier.TIER_4_CRITICAL_DEFERRED
            if disp == "ambiguous":
                flags.append("AMBIGUITY_WARNING: Multiple contradictory disposition signals detected.")
            elif disp == "interlocutory_reference":
                flags.append("INTERLOCUTORY_WARNING: Reference order to Larger Bench or interim stay.")
            else:
                flags.append("INCOMPLETE_HOLDING_WARNING: Concluding operative order not identified.")

        # 2. High Risk Checks (Tier 3: Procedural & Nuanced Non-Merits)
        elif disp in self.TIER_3_DISPOSITIONS:
            tier = RiskTier.TIER_3_HIGH_RISK_PROCEDURAL
            if disp == "remanded":
                flags.append("REMAND_CHECK: Matter sent back for fresh disposal; do NOT record as merits win/loss.")
            elif disp == "partly_allowed":
                flags.append("PARTIAL_RELIEF_CHECK: Relief granted in part (e.g. sentence reduction); preserve distinct class.")
            elif disp == "withdrawn":
                flags.append("WITHDRAWAL_CHECK: Voluntary withdrawal; successful_party must be none_procedural.")
            elif disp == "dismissed_as_infructuous":
                flags.append("MOOTNESS_CHECK: Cause of action lapsed; non-merits procedural disposal.")
            elif disp == "disposed_procedural":
                flags.append("PROCEDURAL_DISPOSAL_CHECK: Generic closure without substantive findings.")

        # 3. Moderate Risk Checks (Tier 2: Bail & Substantive Directives)
        elif disp in self.TIER_2_DISPOSITIONS:
            tier = RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES
            if "bail" in disp:
                flags.append("BAIL_LIBERTY_CHECK: Provisional liberty only; do NOT equate to acquittal or conviction.")
            elif disp == "disposed_with_substantive_directions":
                flags.append("DIRECTIVE_CHECK: Verify affirmative duty ordered against respondent authority.")

        # 4. Tier 1: Definitive Merits Rulings (Low Risk)
        elif disp in self.TIER_1_DISPOSITIONS and conf >= 0.85:
            tier = RiskTier.TIER_1_DEFINITIVE_MERITS
            if "appeal" in disp:
                flags.append("APPELLANT_ROLE_CHECK: Verify whether State or Accused appealed to assign party correctly.")
            else:
                flags.append("DEFINITIVE_HOLDING: Clean concluding order detected.")

        else:
            tier = RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES
            flags.append("CONFIDENCE_NOTICE: Parser confidence < 0.85; verify concluding excerpt carefully.")

        recommended_mode = {
            "tier_1": "accelerated_batch",
            "tier_2": "scrutiny_batch",
            "tier_3": "procedural_isolation",
            "tier_4": "deferred_pending_full_text",
        }.get(tier, "scrutiny_batch")

        return {
            "tier": tier,
            "label": RiskTier.LABELS[tier],
            "flags": flags,
            "confidence": conf,
            "text_length": text_len,
            "is_truncated": text_len >= self.TRUNCATION_CHAR_LIMIT,
            "recommended_review_mode": recommended_mode,
        }

    def stratify_queue(
        self,
        records: List[Dict[str, Any]],
        source_cases: Dict[str, Dict[str, Any]],
        only_pending: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Partitions candidate records into four risk tiers.
        """
        stratified: Dict[str, List[Dict[str, Any]]] = {
            RiskTier.TIER_1_DEFINITIVE_MERITS: [],
            RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES: [],
            RiskTier.TIER_3_HIGH_RISK_PROCEDURAL: [],
            RiskTier.TIER_4_CRITICAL_DEFERRED: [],
        }

        for r in records:
            if only_pending and (r.get("review_status") or "pending_review").strip().lower() != "pending_review":
                continue

            cid = r.get("case_id", "")
            source = source_cases.get(cid, {})
            text = source.get("judgmentText", "")

            risk = self.assess_case_risk(r, text)
            enriched_record = dict(r)
            enriched_record["risk_assessment"] = risk

            tier = risk["tier"]
            stratified[tier].append(enriched_record)

        return stratified

    def get_prioritized_pending_queue(
        self,
        records: List[Dict[str, Any]],
        source_cases: Dict[str, Dict[str, Any]],
        tier_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns pending cases ordered by priority tier: Tier 1 -> Tier 2 -> Tier 3 -> Tier 4.
        If tier_filter is specified, returns only records belonging to that tier.
        """
        stratified = self.stratify_queue(records, source_cases, only_pending=True)

        if tier_filter:
            tier_key = tier_filter.strip().lower()
            return stratified.get(tier_key, [])

        # Default: Concatenate in priority order (Tier 1 first)
        ordered: List[Dict[str, Any]] = []
        for t in [
            RiskTier.TIER_1_DEFINITIVE_MERITS,
            RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES,
            RiskTier.TIER_3_HIGH_RISK_PROCEDURAL,
            RiskTier.TIER_4_CRITICAL_DEFERRED,
        ]:
            ordered.extend(stratified[t])

        return ordered
