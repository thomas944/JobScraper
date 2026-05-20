"""
yoe_parser.py
~~~~~~~~~~~~~
Years-of-Experience (YOE) extractor for job posting text.

Extraction cascade (tried in order):
  1. Section-scoped  – locate a known requirements section, run regex inside it.
  2. Full-text regex – run the same patterns over the entire description.
  3. Probabilistic   – aggregate every bare "N years" mention → min / max range.
  4. Degree fallback – return any detected education requirements.

Usage:
    from yoe_parser import YOEParser

    parser = YOEParser()
    result = parser.parse(raw_text)

    print(result)            # "[section] 3–5 yrs; Degrees: Bachelor's"
    print(result.min_years)  # 3.0
    print(result.max_years)  # 5.0
    print(result.degrees)    # ["Bachelor's"]
    print(result.source)     # "section"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Word-number helpers
# ══════════════════════════════════════════════════════════════════════════════

WORD_TO_NUM: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15,
}

# Regex alternation of all word-numbers (e.g. "zero|one|two|...")
_WN = "|".join(WORD_TO_NUM)


def _to_num(value: str) -> Optional[float]:
    """Convert a digit string *or* a word-number to float, or return None."""
    v = value.strip().lower()
    if v in WORD_TO_NUM:
        return float(WORD_TO_NUM[v])
    try:
        return float(v)
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Section-header patterns
# These identify blocks that typically introduce experience/qualification reqs.
# ══════════════════════════════════════════════════════════════════════════════

_RAW_SECTION_HEADERS: list[str] = [
    r"preferred\s+qualifications?",
    r"required\s+qualifications?",
    r"basic\s+qualifications?",
    r"minimum\s+qualifications?",
    r"requirements?",
    r"relevant\s+work\s+experience",
    r"what\s+we(?:'re|re|\s+are)\s+looking\s+for",
    r"what\s+you(?:'ll|ll|\s+will)\s+(?:need|bring|have)",
    r"your\s+skills?\s+(?:&|and)\s+abilities",
    r"what\s+we\s+need\s+to\s+see",
    r"who\s+you\s+are",
    r"you(?:'ll|ll|\s+will)\s+(?:need\s+to\s+have|have|bring)",
    r"skills?\s+(?:required|needed)",
    r"experience\s+required",
    r"job\s+requirements?",
    r"qualifications?",
    r"education\s+(?:and\s+)?experience",
    r"minimum\s+requirements?",
    r"must\s+have",
    r"about\s+you",
    r"the\s+ideal\s+candidate",
    r"you(?:'re|re|\s+are)\s+a\s+(?:great\s+)?fit",
]

# Matches a header on its own line, optionally followed by a colon.
# Handles LF, CRLF, and start-of-string anchors.
_SECTION_RE = re.compile(
    r"(?:^|[\r\n])\s*(?:" + "|".join(_RAW_SECTION_HEADERS) + r")\s*:?\s*(?:\r?\n|$)",
    re.IGNORECASE,
)


# ══════════════════════════════════════════════════════════════════════════════
# YOE regex patterns  (ordered: most specific → least specific)
#
# Label          Example match
# -----------    -------------------------------------------------------
# word_paren     "two (2) years of experience"
# range_hyphen   "3-5 years" / "3–5 years of experience"
# range_to       "3 to 5 years of relevant experience"
# minimum        "minimum 3 years" / "at least 3+ years"
# simple_plus    "3+ years" / "five+ years of experience"
# simple_of_exp  "3 years of experience" / "three years of experience"
# ══════════════════════════════════════════════════════════════════════════════

_OPTIONAL_EXP = r"(?:\s+of\s+(?:\w+\s+)?experience)?"  # " of [relevant] experience"

_RAW_YOE_PATTERNS: list[tuple[str, str]] = [
    # 1. "two (2) years [of experience]"  – digit inside parens is unambiguous
    (
        "word_paren",
        rf"(?:{_WN})\s*\(\s*(\d+)\s*\)\s*years?{_OPTIONAL_EXP}",
    ),
    # 2. Hyphen/dash range: "3-5 years" or "3–5 years [of experience]"
    (
        "range_hyphen",
        rf"(\d+)\s*[-–]\s*(\d+)\s*\+?\s*years?{_OPTIONAL_EXP}",
    ),
    # 3. Word range: "3 to 5 years [of experience]"
    (
        "range_to",
        rf"(\d+)\s+to\s+(\d+)\s*\+?\s*years?{_OPTIONAL_EXP}",
    ),
    # 4. Minimum/floor prefix: "minimum 3 years" / "at least 5+ years" etc.
    (
        "minimum",
        rf"(?:minimum|at\s+least|min\.?|no\s+less\s+than|over|more\s+than)\s+"
        rf"(\d+|{_WN})\s*\+?\s*years?{_OPTIONAL_EXP}",
    ),
    # 5. "N+ years [of experience]"
    (
        "simple_plus",
        rf"(\d+|{_WN})\s*\+\s*years?{_OPTIONAL_EXP}",
    ),
    # 6. "N years of [relevant] experience"
    (
        "simple_of_exp",
        rf"(\d+|{_WN})\s+years?\s+of\s+(?:\w+\s+)?experience",
    ),
]

_COMPILED_YOE: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(raw, re.IGNORECASE))
    for label, raw in _RAW_YOE_PATTERNS
]

# Least-specific "bare" pattern used ONLY in probabilistic mode.
# \b after years? ensures whole-word matching so that "year" cannot partially
# consume "years" in "5 years ago" before the lookahead kicks in.
_BARE_YOE_RE = re.compile(
    rf"(\d+|{_WN})\s*\+?\s*years?\b"
    r"(?!\s+(?:ago|old|later|earlier|prior|before))",
    re.IGNORECASE,
)

# Valid YOE range for sanity filtering (catches "500 years" etc.)
_MIN_VALID_YOE = 0.5
_MAX_VALID_YOE = 30.0


# ══════════════════════════════════════════════════════════════════════════════
# Degree patterns
# ══════════════════════════════════════════════════════════════════════════════

_RAW_DEGREE_PATTERNS: dict[str, str] = {
    "PhD": (
        r"\b(?:ph\.?\s*d\.?|doctorate|doctoral\s+degree)\b"
    ),
    "Master's": (
        r"\b(?:master'?s?(?:\s+degree)?|m\.?\s*s\.?|m\.?\s*eng\.?|"
        r"m\.?\s*b\.?\s*a\.?|m\.?\s*a\.?|graduate\s+degree)\b"
    ),
    "Bachelor's": (
        r"\b(?:bachelor'?s?(?:\s+degree)?|b\.?\s*s\.?|b\.?\s*eng\.?|"
        r"b\.?\s*a\.?|undergraduate\s+degree|college\s+degree|"
        r"4-year\s+degree|four[\s-]+year\s+degree)\b"
    ),
}

_COMPILED_DEGREES: dict[str, re.Pattern[str]] = {
    name: re.compile(raw, re.IGNORECASE)
    for name, raw in _RAW_DEGREE_PATTERNS.items()
}

# Return order: highest degree first
_DEGREE_ORDER = ["PhD", "Master's", "Bachelor's"]


# ══════════════════════════════════════════════════════════════════════════════
# Data model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class YOEResult:
    """
    Parsed years-of-experience result from a job description.

    Attributes:
        min_years:  Lower bound (or exact value) of required experience.
                    Equals max_years when only a single value was found.
        max_years:  Upper bound; equals min_years for non-range results.
        degrees:    Detected degree requirements, highest first.
                    e.g. ["PhD", "Master's"] or ["Bachelor's"]
        source:     Which extraction level produced the result.
                    One of: "section" | "regex" | "probabilistic" |
                            "degree_only" | "not_found"
    """

    min_years: Optional[float] = None
    max_years: Optional[float] = None
    degrees: list[str] = field(default_factory=list)
    source: str = "not_found"

    @property
    def is_range(self) -> bool:
        """True when min and max differ (a genuine range was found)."""
        return (
            self.min_years is not None
            and self.max_years is not None
            and self.min_years != self.max_years
        )

    def __str__(self) -> str:
        parts: list[str] = []
        if self.min_years is not None:
            if self.is_range:
                parts.append(f"{self.min_years:g}–{self.max_years:g} yrs")
            else:
                parts.append(f"{self.min_years:g}+ yrs")
        if self.degrees:
            parts.append("Degrees: " + ", ".join(self.degrees))
        body = "; ".join(parts) if parts else "Not found"
        return f"[{self.source}] {body}"


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════════

def _is_valid(n: float) -> bool:
    return _MIN_VALID_YOE <= n <= _MAX_VALID_YOE


def _find_section_texts(text: str) -> list[str]:
    """
    Return text bodies of every detected requirements/qualifications section,
    in the order they appear.  Each body is trimmed to the next section header
    (or end of text).
    """
    bodies: list[str] = []
    matches = list(_SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            bodies.append(body)
    return bodies


def _extract_definitive(text: str) -> Optional[tuple[float, float]]:
    """
    Run all YOE patterns (1-6) against *text* and collect every valid match.

    Returns (min_of_all_matches, max_of_all_matches), or None if nothing found.

    Collecting all matches (rather than stopping at the first) handles two
    important cases:
      - Explicit ranges: "3–5 years" → (3, 5)
      - Scattered requirements: "6+ years Kafka, 7+ years C++" → (6, 7)
        These are common in senior/staff postings that never state a single
        overall floor but imply seniority through per-technology requirements.
    """
    collected: list[float] = []

    for label, pat in _COMPILED_YOE:
        for m in pat.finditer(text):
            groups = [g for g in m.groups() if g is not None]
            if not groups:
                continue

            if label in ("range_hyphen", "range_to"):
                lo = _to_num(groups[0])
                hi = _to_num(groups[1]) if len(groups) > 1 else None
                if lo is not None and hi is not None and _is_valid(lo) and _is_valid(hi):
                    collected.extend([lo, hi])
            else:
                # word_paren, minimum, simple_plus, simple_of_exp
                n = _to_num(groups[0])
                if n is not None and _is_valid(n):
                    collected.append(n)

    if not collected:
        return None
    return (min(collected), max(collected))


def _extract_probabilistic(text: str) -> Optional[tuple[float, float]]:
    """
    Collect *all* bare "N years" mentions and return (min, max).

    This catches roles like Senior Engineer that list tool-specific experience
    ("6+ years with Kafka, 7+ years with C++") without a stated overall floor.
    The caller can then combine min/max with the job title to infer seniority.
    """
    collected: list[float] = []
    for m in _BARE_YOE_RE.finditer(text):
        n = _to_num(m.group(1))
        if n is not None and _is_valid(n):
            collected.append(n)

    if not collected:
        return None
    return (min(collected), max(collected))


def _find_degrees(text: str) -> list[str]:
    """Return degree names (highest first) that appear anywhere in *text*."""
    found = {name for name, pat in _COMPILED_DEGREES.items() if pat.search(text)}
    return [d for d in _DEGREE_ORDER if d in found]


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

class YOEParser:
    """
    Stateless years-of-experience extractor.

    Instantiate once and call :meth:`parse` for each job description.
    """

    def parse(self, text: str) -> YOEResult:
        """
        Extract years-of-experience from *text* using a four-level cascade.

        Level 1 – Section-scoped regex
            Locate every recognised requirements / qualifications section and
            run definitive regex patterns inside it.  Multiple sections are
            tried in document order; the first match wins.  This scope
            dramatically reduces false positives.

        Level 2 – Full-text regex
            If no section was found (or none contained a YOE match), run the
            same definitive patterns over the entire description.

        Level 3 – Probabilistic aggregation
            Collect every "N years" occurrence in the full text and return
            (min, max).  Useful for roles that scatter experience requirements
            across per-technology bullet points.

        Level 4 – Degree fallback
            If no numeric YOE was found, return any detected degree
            requirements (PhD / Master's / Bachelor's).

        Args:
            text: Plain text content of the job description div.

        Returns:
            A :class:`YOEResult` with the best available information.
        """
        degrees = _find_degrees(text)  # compute once; reused in all returns

        # ── Level 1: search inside each requirements section ────────────────
        for section_body in _find_section_texts(text):
            span = _extract_definitive(section_body)
            if span:
                # Degrees may live outside the section, so scan the full text
                return YOEResult(
                    min_years=span[0],
                    max_years=span[1],
                    degrees=degrees,
                    source="section",
                )

        # ── Level 2: full-text definitive regex ─────────────────────────────
        span = _extract_definitive(text)
        if span:
            return YOEResult(
                min_years=span[0],
                max_years=span[1],
                degrees=degrees,
                source="regex",
            )

        # ── Level 3: probabilistic aggregation ──────────────────────────────
        span = _extract_probabilistic(text)
        if span:
            return YOEResult(
                min_years=span[0],
                max_years=span[1],
                degrees=degrees,
                source="probabilistic",
            )

        # ── Level 4: degree-only fallback ───────────────────────────────────
        if degrees:
            return YOEResult(degrees=degrees, source="degree_only")

        return YOEResult(source="not_found")