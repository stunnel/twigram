# -*- coding: utf-8 -*-

import re
import unittest
from unittest import mock

from lib import unshort
from lib.richtext import BOLD, ITALIC, RichText, Span, from_note_tweet, utf16_len


def bold(text, start, end):
    return RichText(text, [Span(BOLD, start, end)])


class TestFromNoteTweet(unittest.TestCase):
    def test_plain_text(self):
        self.assertEqual(from_note_tweet({'text': 'hello'}), RichText('hello'))

    def test_bold_and_italic_with_exclusive_end(self):
        result = {'text': 'abc def ghi', 'richtext': {'richtext_tags': [
            {'from_index': 0, 'to_index': 3, 'richtext_types': ['Bold']},
            {'from_index': 4, 'to_index': 7, 'richtext_types': ['Bold', 'Italic']},
        ]}}
        rich = from_note_tweet(result)
        self.assertEqual(rich.spans, (Span(BOLD, 0, 3), Span(BOLD, 4, 7), Span(ITALIC, 4, 7)))

    def test_indices_are_utf16_units(self):
        # the emoji is one code point but two UTF-16 units
        text = '🔥 burn now'
        result = {'text': text, 'richtext': {'richtext_tags': [
            {'from_index': 3, 'to_index': 7, 'richtext_types': ['Bold']}]}}
        rich = from_note_tweet(result)
        self.assertEqual(text[rich.spans[0].start:rich.spans[0].end], 'burn')

    def test_unknown_types_and_malformed_tags_are_ignored(self):
        result = {'text': 'abcdef', 'richtext': {'richtext_tags': [
            {'from_index': 0, 'to_index': 2, 'richtext_types': ['Underline']},
            {'from_index': None, 'to_index': 2, 'richtext_types': ['Bold']},
            {'from_index': 2, 'richtext_types': ['Bold']},
            {'from_index': 3, 'to_index': 5},
        ]}}
        self.assertEqual(from_note_tweet(result).spans, ())

    def test_out_of_range_indices_are_clamped(self):
        result = {'text': 'abc', 'richtext': {'richtext_tags': [
            {'from_index': 1, 'to_index': 99, 'richtext_types': ['Italic']}]}}
        self.assertEqual(from_note_tweet(result).spans, (Span(ITALIC, 1, 3),))

    def test_overlapping_spans_of_same_type_are_merged(self):
        result = {'text': 'abcdefgh', 'richtext': {'richtext_tags': [
            {'from_index': 0, 'to_index': 4, 'richtext_types': ['Bold']},
            {'from_index': 3, 'to_index': 6, 'richtext_types': ['Bold']},
            {'from_index': 6, 'to_index': 8, 'richtext_types': ['Bold']},
        ]}}
        self.assertEqual(from_note_tweet(result).spans, (Span(BOLD, 0, 8),))


class TestConcat(unittest.TestCase):
    def test_add_shifts_spans(self):
        rich = RichText('head\n') + bold('bold!', 0, 4)
        self.assertEqual(rich.text, 'head\nbold!')
        self.assertEqual(rich.spans, (Span(BOLD, 5, 9),))

    def test_add_str_on_both_sides(self):
        rich = 'x' + bold('ab', 0, 2) + 'y'
        self.assertEqual(rich.text, 'xaby')
        self.assertEqual(rich.spans, (Span(BOLD, 1, 3),))

    def test_join(self):
        rich = RichText.join(['a', bold('bc', 0, 2), '', RichText('d')], '\n')
        self.assertEqual(rich.text, 'a\nbc\n\nd')
        self.assertEqual(rich.spans, (Span(BOLD, 2, 4),))

    def test_truthiness_and_len(self):
        self.assertFalse(RichText())
        self.assertTrue(RichText('a'))
        self.assertEqual(len(RichText('abc')), 3)


class TestSub(unittest.TestCase):
    def test_longer_replacement_before_span_shifts_it(self):
        rich = bold('a SHORT b', 8, 9)
        out = rich.sub('SHORT', 'https://example.com/long')
        self.assertEqual(out.text, 'a https://example.com/long b')
        self.assertEqual(out.text[out.spans[0].start:out.spans[0].end], 'b')

    def test_replacement_inside_span_grows_it(self):
        rich = bold('see SHORT now', 0, 13)
        out = rich.sub('SHORT', 'LONGER-URL')
        self.assertEqual(out.spans, (Span(BOLD, 0, len(out.text)),))

    def test_span_fully_inside_replaced_text_covers_replacement(self):
        rich = bold('a SHORT b', 2, 7)
        out = rich.sub('SHORT', 'xyz')
        self.assertEqual(out.text, 'a xyz b')
        self.assertEqual(out.spans, (Span(BOLD, 2, 5),))

    def test_deleting_the_only_covered_text_drops_the_span(self):
        rich = bold('a SHORT b', 2, 7)
        out = rich.sub('SHORT', '')
        self.assertEqual(out.spans, ())

    def test_partial_overlap_is_clipped_to_replacement_edges(self):
        rich = bold('a SHORT b', 0, 5)
        out = rich.sub('SHORT', 'xyz')
        self.assertEqual(out.text, 'a xyz b')
        self.assertEqual(out.spans, (Span(BOLD, 0, 5),))

    def test_callable_and_multiple_matches(self):
        rich = bold('one 1 two 2 three', 12, 17)
        out = rich.sub(re.compile(r'\d'), lambda m: 'N' * 3)
        self.assertEqual(out.text, 'one NNN two NNN three')
        self.assertEqual(out.text[out.spans[0].start:out.spans[0].end], 'three')

    def test_no_match_returns_same_content(self):
        rich = bold('abc', 0, 1)
        self.assertEqual(rich.sub('zzz', 'y'), rich)


class TestStripAndSlice(unittest.TestCase):
    def test_strip_moves_spans(self):
        out = bold('  \nab cd\n ', 3, 5).strip()
        self.assertEqual(out.text, 'ab cd')
        self.assertEqual(out.spans, (Span(BOLD, 0, 2),))

    def test_strip_all_whitespace(self):
        self.assertEqual(RichText(' \n ').strip(), RichText())

    def test_slice_clips_spans(self):
        out = bold('0123456789', 2, 8).slice(5, 10)
        self.assertEqual(out.text, '56789')
        self.assertEqual(out.spans, (Span(BOLD, 0, 3),))


class TestSplit(unittest.TestCase):
    def test_short_text_is_not_split(self):
        rich = bold('abc', 0, 3)
        self.assertEqual(rich.split(10), [rich])

    def test_split_at_newline_and_span_is_cut_in_two(self):
        text = 'aaaa\nbbbb\ncccc'
        chunks = bold(text, 2, 12).split(10)
        self.assertEqual([c.text for c in chunks], ['aaaa\nbbbb', 'cccc'])
        self.assertEqual(chunks[0].spans, (Span(BOLD, 2, 9),))
        self.assertEqual(chunks[1].spans, (Span(BOLD, 0, 2),))

    def test_chunks_never_exceed_limit(self):
        text = '\n'.join(['word ' * 30] * 50) + '🔥' * 500
        for chunk in RichText(text).split(100):
            self.assertLessEqual(chunk.utf16_len(), 100)

    def test_single_long_line_is_hard_split_without_losing_text(self):
        text = 'x' * 250
        chunks = RichText(text).split(100)
        self.assertEqual([len(c) for c in chunks], [100, 100, 50])
        self.assertEqual(''.join(c.text for c in chunks), text)

    def test_prefers_whitespace_over_hard_cut(self):
        chunks = RichText('hello world foo').split(8)
        self.assertEqual([c.text for c in chunks], ['hello', 'world', 'foo'])

    def test_surrogate_pairs_are_not_broken(self):
        chunks = RichText('🔥' * 10).split(5)
        self.assertEqual([c.text for c in chunks], ['🔥🔥', '🔥🔥', '🔥🔥', '🔥🔥', '🔥🔥'])

    def test_no_text_is_lost_across_chunks(self):
        text = 'line one\nline two\n\nline three is a bit longer\nfour'
        chunks = RichText(text).split(15)
        self.assertEqual(' '.join(c.text.replace('\n', ' ') for c in chunks).split(), text.split())


class TestUtf16Entities(unittest.TestCase):
    def test_offsets_count_emoji_as_two(self):
        rich = bold('🔥 burn', 2, 6)
        self.assertEqual(rich.to_utf16_entities(), [(BOLD, 3, 4, '')])

    def test_no_spans(self):
        self.assertEqual(RichText('abc').to_utf16_entities(), [])

    def test_utf16_len(self):
        self.assertEqual(utf16_len('a🔥b'), 4)
        self.assertEqual(utf16_len('中文'), 2)


class TestPipeline(unittest.TestCase):
    """Header prefix, short link expansion, tweet url suffix and split, as the bot applies them."""

    def test_end_to_end_offsets_stay_on_the_same_words(self):
        text = '🔥 Intro https://t.co/abc tail BOLD here and more'
        start = utf16_len(text[:text.index('BOLD')])
        note = {'text': text,
                'richtext': {'richtext_tags': [{'from_index': start, 'to_index': start + 4,
                                                'richtext_types': ['Bold']}]}}
        rich = from_note_tweet(note)
        self.assertEqual(rich.text[rich.spans[0].start:rich.spans[0].end], 'BOLD')

        rich = RichText('Name (handle)\n\n') + rich
        rich = rich + '\n\nhttps://x.com/handle/status/1'
        with mock.patch.object(unshort.unshortener, 'unshorten', return_value='https://example.com/a/very/long/path'):
            rich = unshort.expand_urls_in_text(rich)

        self.assertIn('https://example.com/a/very/long/path', rich.text)
        for chunk in rich.split(40):
            for entity_type, offset, length, _ in chunk.to_utf16_entities():
                units = chunk.text.encode('utf-16-le')[offset * 2:(offset + length) * 2].decode('utf-16-le')
                self.assertEqual(entity_type, BOLD)
                self.assertEqual(units, 'BOLD')

    def test_expand_urls_in_plain_str_still_works(self):
        with mock.patch.object(unshort.unshortener, 'unshorten', return_value='https://example.com/full'):
            self.assertEqual(unshort.expand_urls_in_text('go https://t.co/abc now'), 'go https://example.com/full now')


if __name__ == '__main__':
    unittest.main()
