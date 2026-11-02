"""Reference scores from Python difflib for the JavaScript matcher test."""

import json
import re
import sys
from difflib import SequenceMatcher


# These pairs cover clean, noisy, numeric, partial, and autojunk-sensitive text.
PAIRS = [
    ("There is a room I still think about.", "There is a room I still think about."),
    ("There is a room", "There is a room I still think about."),
    ("The window face west and in the afternoon everything went cold", "The window faced west, and in the afternoons, everything went gold."),
    ("I didnt know it wouldnt always be like this", "I didn't know it wouldn't always be like this."),
    ("The summer I turned 17 we moved", "The summer I turned seventeen, we moved."),
    ("For months after I woke at 3 in the morning", "For months after, I woke at three in the morning."),
    ("A door", "A door."),
    ("A car", "A door."),
    ("small things at first then bigger things", "Small things at first. Then bigger things."),
    ("I learned to make my own tea", "I learned to sit with the silence without fighting it."),
    ("right here", "Right here."),
    ("", "Right here."),
    ("rain at night thunder clouds a front door left open", "rain at night thunder clouds a front door left open"),
    ("abc" * 80, "abc" * 80),
    ("a" * 210 + "b", "a" * 210 + "c"),
    ("the room " * 35 + "window", "the room " * 35 + "door"),
]


# This matches the live script's text normalisation exactly.
def normalize_text(text):
    text = text.lower()
    text = text.replace("17", "seventeen")
    text = text.replace("3 in the morning", "three in the morning")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# This matches the live script's blended matcher exactly.
def text_similarity(first, second):
    first = normalize_text(first)
    second = normalize_text(second)
    if not first or not second:
        return 0.0

    sequence = SequenceMatcher(None, first, second).ratio()
    first_words = set(first.split())
    second_words = set(second.split())
    overlap = len(first_words & second_words) / max(1, min(len(first_words), len(second_words)))
    contained = 1.0 if first in second or second in first else 0.0
    return max(sequence * 0.65 + overlap * 0.35, contained * 0.85)


# This produces raw and blended scores for the JavaScript comparison test.
def results():
    return [
        {
            "first": first,
            "second": second,
            "ratio": SequenceMatcher(None, normalize_text(first), normalize_text(second)).ratio(),
            "similarity": text_similarity(first, second),
        }
        for first, second in PAIRS
    ]


# This prints readable scores by default and JSON when Node asks for machine-readable results.
def main():
    scores = results()
    if "--json" in sys.argv:
        print(json.dumps(scores))
        return

    for number, score in enumerate(scores, start=1):
        print(f"{number:02d} ratio={score['ratio']:.6f} similarity={score['similarity']:.6f}")


if __name__ == "__main__":
    main()
