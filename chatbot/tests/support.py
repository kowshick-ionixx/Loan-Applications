"""Shared helpers for asserting on facts, not wording."""

import re

from accounts import MANAGER, UserContext

MANAGER_USER = UserContext("test-manager", MANAGER)

# How each app rule message starts -> the oracle's rule key.
RULE_PREFIXES = {
    "Amount": "amount",
    "Tenure": "tenure",
    "Age": "age",
    "Monthly income": "income",
    "Credit score": "credit",
    "EMI burden": "burden",
}


def rule_keys(failed_rules: list[str]) -> set[str]:
    keys = set()
    for rule in failed_rules:
        key = next((k for p, k in RULE_PREFIXES.items() if rule.startswith(p)), None)
        assert key is not None, f"unrecognised rule message: {rule!r}"
        keys.add(key)
    return keys


def numbers_in(text: str) -> list[float]:
    """Every number in a text, with ₹, Rs and digit grouping removed."""
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", text)
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", cleaned)]


def mentions_amount(text: str, value: float, tolerance: float = 1.0) -> bool:
    return any(abs(n - value) <= tolerance for n in numbers_in(text))


def sections(policy_text: str) -> dict[str, str]:
    """{'1.1': 'Applicants must be ...', ...} from the policy text."""
    found, current = {}, None
    for line in policy_text.splitlines():
        match = re.match(r"^(\d+\.\d+)\s+(.*)", line.strip())
        if match:
            current = match.group(1)
            found[current] = match.group(2)
        elif current and line.strip() and not line.startswith("Section"):
            found[current] += " " + line.strip()
        else:
            current = None
    return found


def find_section(policy_text: str, *keywords: str) -> tuple[str, str]:
    """The first section whose text contains every keyword (case-insensitive)."""
    for sid, text in sections(policy_text).items():
        if all(k.lower() in text.lower() for k in keywords):
            return sid, text
    raise AssertionError(f"no policy section contains {keywords}")


def percentages(text: str) -> list[float]:
    """Numbers written as percentages: '11%', '11 %', '11 percent'."""
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", text)
    return [
        float(n)
        for n in re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", cleaned, re.IGNORECASE)
    ]


def failure_label(expected_section: str, retrieved: list[str]) -> str:
    """RETRIEVAL if the right section was not fetched, else MODEL."""
    hit = any(expected_section in chunk for chunk in retrieved)
    return "MODEL" if hit else "RETRIEVAL"
