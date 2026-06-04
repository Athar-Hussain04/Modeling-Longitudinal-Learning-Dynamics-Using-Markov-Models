"""Sequence-input parsing helpers for ch10 / ch12 / ch14 backends.

Frontends for sequence chapters give users a <textarea> where they type an
event trace such as `login, quiz, forum, logout` or paste a JSON array. The
backend needs a single normalized representation against a known vocabulary.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple

_SPLIT_RE = re.compile(r"[\s,;\|>\-]+")


def parse_sequence(
    raw: object,
    vocabulary: Iterable[str],
    *,
    case_sensitive: bool = False,
    max_length: int = 500,
) -> Tuple[List[str], List[str]]:
    """Normalize a sequence payload.

    Returns ``(known_events, unknown_tokens)``. The first list preserves the
    order the user supplied; the second list contains tokens that did not match
    the vocabulary (useful for surfacing typos back to the UI).
    """
    if raw is None:
        return [], []

    if isinstance(raw, str):
        tokens = [t for t in _SPLIT_RE.split(raw.strip()) if t]
    elif isinstance(raw, (list, tuple)):
        tokens = [str(t).strip() for t in raw if str(t).strip()]
    else:
        raise ValueError(f"sequence must be a string or list, got {type(raw).__name__}")

    if len(tokens) > max_length:
        raise ValueError(f"sequence has {len(tokens)} tokens; maximum is {max_length}")

    vocab_set = {v if case_sensitive else v.casefold() for v in vocabulary}
    vocab_canonical = {(v if case_sensitive else v.casefold()): v for v in vocabulary}

    known: List[str] = []
    unknown: List[str] = []
    for tok in tokens:
        probe = tok if case_sensitive else tok.casefold()
        if probe in vocab_set:
            known.append(vocab_canonical[probe])
        else:
            unknown.append(tok)
    return known, unknown
