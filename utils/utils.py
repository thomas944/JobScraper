import re
import unicodedata

def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)

    # normalize weird punctuation
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return text
        # 1. Matches "two (2) years" AND "two (2) years of experience"
        # 2. Matches "2 years of experience" OR "two years of experience"
        # 3. Existing Range patterns (e.g., 0-2 years or 0 to 2 years)
        # 4. Existing Simple counts (e.g., 2+ years)
        # 5. Existing "Minimum" patterns (e.g. minimum 2+ years, minimum 2 years, at least 2 years, at least 2+ years, etc)

def extract_exp_patterns(text: str):

    patterns = [
        # 1. Matches "two (2) years" AND "two (2) years of experience"
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*\((\d+)\)\s*years?(?:\s+of\s+experience)?",

        # 2. Matches "2 years of experience" OR "two years of experience"
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+years(?:\s+of\s+experience)?",

        # 3. Existing Range patterns (e.g., 0-2 years)
        r"(\d+)\s*[-to]+\s*(\d+)\s*\+?\s*years",

        # 4. Existing Simple counts (e.g., 2+ years)
        r"(\d+)\+?\s*years",

        # 5. Existing "Minimum" patterns
        r"minimum\s*(\d+)\+?\s*years",
        r"at least\s*(\d+)\s*years",
    ]

    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.groups()

    return None


WORD_TO_NUM = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

def replace_words(text: str) -> str:
    for word, num in WORD_TO_NUM.items():
        text = re.sub(rf"\b{word}\b", str(num), text)
    return text