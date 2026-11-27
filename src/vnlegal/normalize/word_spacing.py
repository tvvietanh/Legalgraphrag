"""Conservative, reversible word-boundary candidates; never a spelling model."""
from collections import Counter
import hashlib
import re

WORDS = re.compile(r"(?<![\w\u0300-\u036f])[^\W\d_]+(?![\w\u0300-\u036f])", re.UNICODE)
HORIZONTAL_SPACE = re.compile(r"[ \t\u00a0\u202f]+\Z")


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replay(text, edits):
    """Apply source-coordinate, nonoverlapping edits and check every character."""
    end = 0
    pieces = []
    for edit in sorted(edits, key=lambda e: e["start"]):
        a, b = edit["start"], edit["end"]
        if a < end or not (0 <= a <= b <= len(text)):
            raise ValueError("Overlapping or invalid edit")
        if text[a:b] != edit["before"]:
            raise ValueError("Stale source edit")
        if "".join(edit["before"].split()) != "".join(edit["after"].split()):
            raise ValueError("Edit changes a non-whitespace character")
        pieces.extend((text[end:a], edit["after"]))
        end = b
    pieces.append(text[end:])
    output = "".join(pieces)
    if "".join(output.split()) != "".join(text.split()):
        raise ValueError("Non-whitespace invariant failed")
    return output


def apply_patches(text, patches, expected_source_sha256):
    """Reconstruct a candidate view only from the exact source markdown version."""
    if text_sha(text) != expected_source_sha256:
        raise ValueError("Source markdown hash mismatch")
    return replay(text, patches)


class SpacingCandidates:
    def __init__(self, vocabulary):
        self.vocabulary = frozenset(vocabulary)
        self.prefixes = frozenset(w[:i] for w in vocabulary for i in range(1, len(w)))
        self.max_length = max(map(len, vocabulary), default=0)

    def propose(self, text, exact=()):
        digest = text_sha(text)
        edits = []
        for proposal in exact:
            if proposal["source_text_sha256"] != digest:
                raise ValueError("Exact PDF proposal source hash mismatch")
            edits.append(dict(start=proposal["start"], end=proposal["end"],
                              before=proposal["before"], after=proposal["after"],
                              method="same_document_pdf_supported", rule="pdf_anchor_glyph_v004",
                              provenance=proposal, target_pdf_verified=True))
        tokens = list(WORDS.finditer(text))
        counts = Counter(m[0] for m in tokens)
        supported = {w for w in self.vocabulary if counts[w] >= 2}
        candidates = []
        for i, first in enumerate(tokens):
            if first[0] not in self.prefixes or not first[0].islower():
                continue
            parts = [first[0]]
            merged = first[0]
            for j in range(i + 1, min(i + 4, len(tokens))):
                other = tokens[j]
                gap = text[tokens[j - 1].end():other.start()]
                if not HORIZONTAL_SPACE.fullmatch(gap) or not other[0].islower():
                    break
                parts.append(other[0])
                merged += other[0]
                if len(merged) > self.max_length:
                    break
                if merged in supported and any(len(p) == 1 or p not in self.vocabulary for p in parts):
                    # Adjacent point labels ("điểm a b") remain evidence-sensitive.
                    previous = tokens[i - 1][0].lower() if i else ""
                    if previous == "điểm" and len(first[0]) == 1:
                        continue
                    candidates.append(dict(start=first.start(), end=other.end(),
                        before=text[first.start():other.end()], after=merged,
                        method="native_law_lexicon_same_document_support", rule="lowercase_2_to_4_fragments_v2",
                        target_pdf_verified=False, intact_word_count=counts[merged], fragments=parts.copy(),
                        vocabulary_word=merged, status="needs_review"))
                if merged not in self.prefixes:
                    break
        # PDF coordinates take priority. Longest overlapping generic candidate wins;
        # every decision is deterministic and source offsets stay unchanged.
        occupied = [(e["start"], e["end"]) for e in edits]
        for candidate in sorted(candidates, key=lambda e: (e["start"], -(e["end"] - e["start"]))):
            a, b = candidate["start"], candidate["end"]
            if any(a < y and x < b for x, y in occupied):
                continue
            edits.append(candidate)
            occupied.append((a, b))
        edits.sort(key=lambda e: e["start"])
        return replay(text, edits), edits
