"""
Judgment Source Verification & Audit Utility
Validates structural integrity, official vs. secondary attribution, and (in --live mode)
verifies live HTTP status, PDF magic headers, non-homepage URLs, and case-name relevance.
"""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.request
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse

DEFAULT_CORPUS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app",
    "datasets",
    "indian_judgments.json"
)

OFFICIAL_DOMAINS = (
    "api.sci.gov.in",
    "sci.gov.in",
    "www.sci.gov.in",
    "digiscr.sci.gov.in",
    "cdnbbsr.s3waas.gov.in",
    "aphc.gov.in",
    "delhihighcourt.nic.in",
    "bombayhighcourt.nic.in",
    "allahabadhighcourt.in",
)

DEPRECATED_OR_BROKEN_DOMAINS = (
    "main.sci.gov.in",
    "e-services.allahabadhighcourt.in",
)


def is_generic_homepage(url: str) -> bool:
    if not url:
        return True
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    return path == "" and not parsed.query


def audit_record_structure(record: Dict[str, Any]) -> List[str]:
    issues = []
    rec_id = record.get("id", "UNKNOWN")
    official_url = record.get("officialSourceUrl", "")
    official_verified = bool(record.get("officialSourceVerified", False))
    secondary_url = record.get("secondaryReferenceUrl", "")
    source_url = record.get("sourceUrl", "")
    status = record.get("verificationStatus", "")

    for bad_domain in DEPRECATED_OR_BROKEN_DOMAINS:
        if bad_domain in official_url or bad_domain in source_url or bad_domain in secondary_url:
            issues.append(f"{rec_id}: contains deprecated/broken domain '{bad_domain}'")

    if official_verified:
        if not official_url:
            issues.append(f"{rec_id}: officialSourceVerified=True but officialSourceUrl is empty")
        else:
            host = urlparse(official_url).netloc.lower()
            if not any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS):
                issues.append(f"{rec_id}: officialSourceUrl host '{host}' is not an official court domain")
            if is_generic_homepage(official_url):
                issues.append(f"{rec_id}: officialSourceUrl points to generic court homepage")
        if status != "verified_official":
            issues.append(f"{rec_id}: officialSourceVerified=True requires verificationStatus='verified_official'")
    else:
        if official_url:
            issues.append(f"{rec_id}: officialSourceUrl must be empty when officialSourceVerified=False")
        if status == "verified_official":
            issues.append(f"{rec_id}: cannot set verificationStatus='verified_official' when officialSourceVerified=False")

    if official_url and source_url != official_url:
        issues.append(f"{rec_id}: canonical sourceUrl should equal verified officialSourceUrl")
    elif not official_url and source_url != secondary_url:
        issues.append(f"{rec_id}: canonical sourceUrl should match secondaryReferenceUrl when official source is unverified")

    return issues


def check_live_url(url: str, expected_title: str) -> Tuple[bool, str]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            final_url = resp.geturl()
            if is_generic_homepage(final_url):
                return False, f"Redirected to generic homepage: {final_url}"
            ctype = resp.headers.get("Content-Type", "").lower()
            body = resp.read(120000)
            if url.lower().endswith(".pdf") or "application/pdf" in ctype:
                if b"%PDF" not in body[:64] or len(body) < 2000:
                    return False, f"Invalid PDF payload (ctype={ctype}, bytes={len(body)})"
                return True, f"HTTP {resp.status} PDF valid ({len(body)}+ bytes)"
            html = body.decode("utf-8", "ignore")
            title_match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            page_title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
            tokens = [t.lower() for t in re.findall(r"[A-Za-z]{4,}", expected_title)
                      if t.lower() not in {"state", "union", "india", "ors.", "anr.", "versus", "private", "limited"}]
            haystack = (page_title + " " + html[:40000]).lower()
            matched = [t for t in tokens[:4] if t in haystack]
            if tokens and not matched:
                return False, f"HTML content did not match case tokens ({tokens[:3]})"
            return True, f"HTTP {resp.status} HTML valid (title='{page_title[:60]}')"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main():
    parser = argparse.ArgumentParser(description="Verify judgment source links and metadata.")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--live", action="store_true", help="Perform live HTTP verification of all URLs")
    args = parser.parse_args()

    with open(args.corpus, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    structural_errors = []
    official_verified_count = 0
    secondary_verified_count = 0
    unverified_count = 0
    live_failures = []

    for rec in corpus:
        structural_errors.extend(audit_record_structure(rec))
        if rec.get("officialSourceVerified"):
            official_verified_count += 1
        elif rec.get("secondaryReferenceUrl"):
            secondary_verified_count += 1
        else:
            unverified_count += 1

        if args.live:
            if rec.get("officialSourceUrl"):
                ok, detail = check_live_url(rec["officialSourceUrl"], rec["caseTitle"])
                print(f"[OFFICIAL] {rec['id']} -> {'PASS' if ok else 'FAIL'} | {detail}")
                if not ok:
                    live_failures.append((rec["id"], "official", detail))
            if rec.get("secondaryReferenceUrl"):
                ok, detail = check_live_url(rec["secondaryReferenceUrl"], rec["caseTitle"])
                print(f"[SECONDARY] {rec['id']} -> {'PASS' if ok else 'FAIL'} | {detail}")
                if not ok:
                    live_failures.append((rec["id"], "secondary", detail))

    print("\n--- Source Integrity Summary ---")
    print(f"Total records: {len(corpus)}")
    print(f"Official court sources verified: {official_verified_count}")
    print(f"Secondary reference verified (official marked unverified): {secondary_verified_count}")
    print(f"Unverified records: {unverified_count}")
    print(f"Structural audit errors: {len(structural_errors)}")
    for err in structural_errors:
        print("  STRUCTURAL ERROR:", err)

    if structural_errors or live_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
