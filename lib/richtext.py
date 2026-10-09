# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass

BOLD = 'bold'
ITALIC = 'italic'
_STYLES = (BOLD, ITALIC)


def utf16_len(text: str) -> int:
    """Length in UTF-16 code units, the unit Telegram uses for entities and size limits."""
    return len(text.encode('utf-16-le', 'surrogatepass')) // 2


@dataclass(frozen=True)
class Span:
    type: str
    start: int  # code point index, inclusive
    end: int    # code point index, exclusive


def _normalize(spans, length: int) -> tuple:
    """Clip spans to the text, drop empty ones and merge overlapping/adjacent spans of the same type."""
    by_type = {}
    for span in spans:
        start, end = max(span.start, 0), min(span.end, length)
        if end > start:
            by_type.setdefault(span.type, []).append([start, end])

    result = []
    for span_type, ranges in by_type.items():
        ranges.sort()
        merged = [ranges[0]]
        for start, end in ranges[1:]:
            if start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        result.extend(Span(span_type, start, end) for start, end in merged)

    return tuple(sorted(result, key=lambda s: (s.start, -s.end, s.type)))


class RichText:
    """Text with bold/italic spans. Spans are kept in code point offsets and follow every edit."""

    __slots__ = ('text', 'spans')

    def __init__(self, text: str = '', spans=()):
        self.text = text
        self.spans = _normalize(spans, len(text))

    @classmethod
    def coerce(cls, value) -> 'RichText':
        if isinstance(value, RichText):
            return value
        return cls(value or '')

    @classmethod
    def join(cls, parts, sep: str = '') -> 'RichText':
        result = cls()
        for i, part in enumerate(parts):
            if i:
                result = result + sep
            result = result + part
        return result

    def __len__(self) -> int:
        return len(self.text)

    def __bool__(self) -> bool:
        return bool(self.text)

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f'RichText({self.text!r}, {list(self.spans)!r})'

    def __eq__(self, other) -> bool:
        return isinstance(other, RichText) and self.text == other.text and self.spans == other.spans

    def __hash__(self) -> int:
        return hash((self.text, self.spans))

    def __add__(self, other) -> 'RichText':
        other = RichText.coerce(other)
        shift = len(self.text)
        shifted = [Span(s.type, s.start + shift, s.end + shift) for s in other.spans]
        return RichText(self.text + other.text, list(self.spans) + shifted)

    def __radd__(self, other) -> 'RichText':
        return RichText.coerce(other) + self

    def utf16_len(self) -> int:
        return utf16_len(self.text)

    def slice(self, start: int, end: int) -> 'RichText':
        start, end = max(start, 0), min(end, len(self.text))
        if end <= start:
            return RichText()
        spans = [Span(s.type, max(s.start, start) - start, min(s.end, end) - start) for s in self.spans]
        return RichText(self.text[start:end], spans)

    def strip(self) -> 'RichText':
        end = len(self.text.rstrip())
        start = len(self.text) - len(self.text.lstrip())
        return self.slice(start, end)

    def sub(self, pattern, repl) -> 'RichText':
        """
        Like re.sub, but spans follow the text. `repl` is a string or a callable taking a match.
        A span boundary that falls inside a replaced region moves to the matching edge of the replacement.
        """
        if isinstance(pattern, str):
            pattern = re.compile(re.escape(pattern))

        out, marks = [], []     # marks: (old_start, old_end, new_start, new_end)
        old_pos, new_len = 0, 0
        for m in pattern.finditer(self.text):
            if m.end() == m.start():
                continue
            keep = self.text[old_pos:m.start()]
            out.append(keep)
            new_len += len(keep)
            replacement = repl(m) if callable(repl) else repl
            out.append(replacement)
            marks.append((m.start(), m.end(), new_len, new_len + len(replacement)))
            new_len += len(replacement)
            old_pos = m.end()
        out.append(self.text[old_pos:])

        if not marks:
            return self

        def remap(pos: int, is_end: bool) -> int:
            delta = 0
            for old_start, old_end, new_start, new_end in marks:
                if pos <= old_start:
                    break
                if pos >= old_end:
                    delta = new_end - old_end
                    continue
                return new_end if is_end else new_start
            return pos + delta

        spans = [Span(s.type, remap(s.start, False), remap(s.end, True)) for s in self.spans]
        return RichText(''.join(out), spans)

    def split(self, limit: int) -> list['RichText']:
        """
        Split into stripped chunks of at most `limit` UTF-16 units.
        Prefers to cut at a newline, then at other whitespace, then anywhere.
        The whitespace character at the cut is dropped.
        """
        if limit < 2:
            raise ValueError('limit must be at least 2')
        if self.utf16_len() <= limit:
            return [self]

        text, size = self.text, len(self.text)
        chunks, pos = [], 0
        while pos < size:
            width, end = 0, pos
            while end < size:
                char_width = 2 if ord(text[end]) > 0xFFFF else 1
                if width + char_width > limit:
                    break
                width += char_width
                end += 1

            if end >= size:
                cut, next_pos = size, size
            else:
                cut = text.rfind('\n', pos, end + 1)
                if cut < 0:
                    cut = next((i for i in range(end, pos - 1, -1) if text[i].isspace()), -1)
                if cut < 0:
                    cut, next_pos = end, end
                else:
                    next_pos = cut + 1

            chunk = self.slice(pos, cut).strip()
            if chunk:
                chunks.append(chunk)
            pos = next_pos

        return chunks

    def to_utf16_entities(self) -> list[tuple[str, int, int]]:
        """(type, offset, length) for every span, in UTF-16 code units."""
        if not self.spans:
            return []

        offsets = [0]
        for char in self.text:
            offsets.append(offsets[-1] + (2 if ord(char) > 0xFFFF else 1))

        return [(s.type, offsets[s.start], offsets[s.end] - offsets[s.start]) for s in self.spans]


def from_note_tweet(note_result: dict) -> RichText:
    """
    Build a RichText from `note_tweet.note_tweet_results.result`.
    The tags in `richtext.richtext_tags` are [from_index, to_index) in UTF-16 units.
    """
    text = note_result.get('text') or ''
    tags = (note_result.get('richtext') or {}).get('richtext_tags') or []
    if not tags:
        return RichText(text)

    to_code_point = []
    for index, char in enumerate(text):
        to_code_point.extend([index] * (2 if ord(char) > 0xFFFF else 1))
    to_code_point.append(len(text))

    def locate(units) -> int:
        return to_code_point[max(0, min(len(to_code_point) - 1, units))]

    spans = []
    for tag in tags:
        start, end = tag.get('from_index'), tag.get('to_index')
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        types = {str(t).lower() for t in tag.get('richtext_types') or []}
        spans.extend(Span(t, locate(start), locate(end)) for t in _STYLES if t in types)

    return RichText(text, spans)
