"""
salary_parser.py
~~~~~~~~~~~~~~~~
Salary / compensation extractor for job posting text.

Strategy:
  1. Find every "$N" occurrence in the text (handles commas, decimals, K/M suffix).
  2. Detect pay type (annual vs hourly) from surrounding context.
  3. Normalise all values to a common unit (annual dollars or $/hr).
  4. Return (min, max) across all found values.

Usage:
    from salary_parser import SalaryParser

    parser = SalaryParser()
    result = parser.parse(raw_text)

    print(result)               # "[annual] $80,000 – $142,484"
    print(result.min_salary)    # 80000.0
    print(result.max_salary)    # 142484.02
    print(result.pay_type)      # "annual"
    print(result.all_values)    # [90466.05, 142484.02, 80000.0]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Patterns
# ══════════════════════════════════════════════════════════════════════════════

# Matches a dollar sign followed by a number.
# Captures:
#   group 1 – the numeric part (may include commas and a decimal)
#   group 2 – optional K / M suffix  (e.g. "$80K", "$1.2M")
_SALARY_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*([KkMm]?)\b",
)

# Hourly indicators that can appear near a salary figure.
# We scan a window around each match to classify it.
_HOURLY_RE = re.compile(
    r"/\s*h(?:ou?)?r?\b"        # /hr  /hour  /h
    r"|per\s+hour"
    r"|\bhourly\b"
    r"|\bhr\.?\b",
    re.IGNORECASE,
)

# Annual indicators (helps disambiguate when both hourly and annual text exist)
_ANNUAL_RE = re.compile(
    r"\bper\s+(?:year|annum)\b"
    r"|\bannual(?:ly)?\b"
    r"|\bsalary\b"
    r"|\bbase\s+pay\b"
    r"|\bcompensation\b"
    r"|\bOTE\b"                 # on-target earnings
    r"|\bpay\s+range\b"
    r"|\bcommission\b"
    r"|\bbonus\b"
    r"|\bbase\s+salary\b"
    r"|\btotal\s+(?:target\s+)?compensation\b"
    r"|\bctc\b",                # cost to company (common in international postings)
    re.IGNORECASE,
)

# How many characters around a match to look for pay-type context
_CONTEXT_WINDOW = 80

# ── Sanity filters ────────────────────────────────────────────────────────────
# Annual salaries outside this range are almost certainly noise
# (e.g. "$500 signing bonus", "$10 gift card").
_ANNUAL_MIN =  15_000.0
_ANNUAL_MAX = 5_000_000.0

# Hourly rates outside this range are similarly skipped
_HOURLY_MIN =  7.0
_HOURLY_MAX =  500.0


# ══════════════════════════════════════════════════════════════════════════════
# Normalisation helpers
# ══════════════════════════════════════════════════════════════════════════════

def _parse_value(digits: str, suffix: str) -> float:
    """
    Turn a raw captured number string + optional suffix into a float.

    Examples:
        "90,466", ""   → 90466.0
        "80",     "K"  → 80000.0
        "1.2",    "M"  → 1200000.0
    """
    value = float(digits.replace(",", ""))
    suffix = suffix.upper()
    if suffix == "K":
        value *= 1_000
    elif suffix == "M":
        value *= 1_000_000
    return value


def _fmt(value: float) -> str:
    """Human-readable dollar amount (e.g. 90466.05 → '$90,466')."""
    if value >= 1_000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


# ══════════════════════════════════════════════════════════════════════════════
# Data model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SalaryResult:
    """
    Parsed salary / compensation result from a job description.

    Attributes:
        min_salary:  Lowest salary value found (normalised to pay_type unit).
        max_salary:  Highest salary value found.
        pay_type:    "annual" | "hourly" | "unknown"
        all_values:  Every individual salary figure found, sorted ascending.
        source:      "found" | "not_found"
    """
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    pay_type: str = "unknown"
    all_values: list[float] = field(default_factory=list)
    source: str = "not_found"

    @property
    def is_range(self) -> bool:
        return (
            self.min_salary is not None
            and self.max_salary is not None
            and self.min_salary != self.max_salary
        )

    def __str__(self) -> str:
        if self.min_salary is None:
            return "[not_found] Not found"
        if self.is_range:
            body = f"{_fmt(self.min_salary)} – {_fmt(self.max_salary)}"
        else:
            body = _fmt(self.min_salary)
        suffix = "/hr" if self.pay_type == "hourly" else ""
        return f"[{self.pay_type}] {body}{suffix}"


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════════

def _classify_pay_type(text: str, match_positions: list[int]) -> str:
    """
    Scan a context window around each matched position and vote on pay type.

    Returns "hourly", "annual", or "unknown".
    """
    hourly_votes = 0
    annual_votes = 0

    for pos in match_positions:
        lo = max(0, pos - _CONTEXT_WINDOW)
        hi = min(len(text), pos + _CONTEXT_WINDOW)
        window = text[lo:hi]

        if _HOURLY_RE.search(window):
            hourly_votes += 1
        if _ANNUAL_RE.search(window):
            annual_votes += 1

    if hourly_votes == 0 and annual_votes == 0:
        return "unknown"
    if hourly_votes > annual_votes:
        return "hourly"
    return "annual"


def _valid_value(value: float, pay_type: str) -> bool:
    """Return True if *value* is plausible for the given *pay_type*."""
    if pay_type == "hourly":
        return _HOURLY_MIN <= value <= _HOURLY_MAX
    # annual or unknown → use the broader annual filter
    return _ANNUAL_MIN <= value <= _ANNUAL_MAX


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

class SalaryParser:
    """
    Stateless salary extractor.

    Instantiate once and call :meth:`parse` for each job description.
    """

    def parse(self, text: str) -> SalaryResult:
        """
        Extract salary information from *text*.

        Steps:
          1. Find every "$N" token (commas, decimals, K/M suffix handled).
          2. Classify pay type (hourly vs annual) from surrounding context.
          3. Filter values outside a plausible range for the detected pay type.
          4. Return (min, max) across all remaining values.

        Args:
            text: Plain text content of the job description div.

        Returns:
            A :class:`SalaryResult` with the best available information.
        """
        raw_matches: list[tuple[float, int]] = []   # (value, char_position)

        for m in _SALARY_RE.finditer(text):
            value = _parse_value(m.group(1), m.group(2))
            raw_matches.append((value, m.start()))

        if not raw_matches:
            return SalaryResult(source="not_found")

        # Classify pay type using all match positions
        pay_type = _classify_pay_type(text, [pos for _, pos in raw_matches])

        # Filter implausible values (bonuses, fees, etc.)
        valid_values = sorted(
            v for v, _ in raw_matches if _valid_value(v, pay_type)
        )

        if not valid_values:
            return SalaryResult(source="not_found")

        return SalaryResult(
            min_salary=valid_values[0],
            max_salary=valid_values[-1],
            pay_type=pay_type,
            all_values=valid_values,
            source="found",
        )