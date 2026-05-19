import re
import unicodedata

def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)

    # normalize weird punctuation
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return text

def extract_exp_patterns(text: str):

    patterns = [
        r"(\d+)\s*[-to]+\s*(\d+)\s*\+?\s*years",        # 0-2 years
        r"(\d+)\+?\s*years",                            # 2+ years
        r"minimum\s*(\d+)\+?\s*years",                  # minimum 8+ years
        r"at least\s*(\d+)\s*years",                    # at least 3 years
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