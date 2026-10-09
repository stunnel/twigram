# -*- coding: utf-8 -*-

import unittest

from lib.article import article_to_rich_text, find_article_link, get_cover_url
from lib.richtext import BLOCKQUOTE, BOLD, ITALIC, PRE, STRIKETHROUGH, TEXT_LINK, utf16_len


def block(text, block_type='unstyled', styles=(), links=()):
    return {'text': text, 'type': block_type,
            'inlineStyleRanges': [{'style': s, 'offset': o, 'length': n} for s, o, n in styles],
            'entityRanges': [{'key': k, 'offset': o, 'length': n} for k, o, n in links]}


def article(blocks, entity_map=None, title='Title'):
    return {'title': title, 'content': {'blocks': blocks, 'entityMap': entity_map or []}}


def covered(rich, span):
    return rich.text[span.start:span.end]


class TestFindArticleLink(unittest.TestCase):
    def test_found(self):
        tweet = {'legacy': {'entities': {'urls': [
            {'url': 'https://t.co/abc', 'expanded_url': 'http://x.com/i/article/1765821414056120320'}]}}}
        self.assertEqual(find_article_link(tweet), ('https://t.co/abc', '1765821414056120320'))

    def test_normal_tweet(self):
        tweet = {'legacy': {'entities': {'urls': [{'url': 'https://t.co/abc', 'expanded_url': 'https://example.com'}]}}}
        self.assertEqual(find_article_link(tweet), ('', ''))
        self.assertEqual(find_article_link({}), ('', ''))


class TestCover(unittest.TestCase):
    def test_cover_url(self):
        data = {'cover_media': {'media_info': {'original_img_url': 'https://pbs.twimg.com/media/a.jpg'}}}
        self.assertEqual(get_cover_url(data), 'https://pbs.twimg.com/media/a.jpg?name=4096x4096')
        self.assertEqual(get_cover_url({}), '')


class TestArticleToRichText(unittest.TestCase):
    def test_title_is_bold_and_paragraphs_are_separated(self):
        rich = article_to_rich_text(article([block('first'), block('second')]))
        self.assertEqual(rich.text, 'Title\n\nfirst\n\nsecond')
        self.assertEqual([covered(rich, s) for s in rich.spans if s.type == BOLD], ['Title'])

    def test_inline_styles(self):
        rich = article_to_rich_text(article([block('abc def ghi', styles=[('Bold', 0, 3), ('Italic', 4, 3),
                                                                           ('Strikethrough', 8, 3), ('Underline', 0, 3)])]))
        by_type = {s.type: covered(rich, s) for s in rich.spans if s.type != BOLD or s.start > 0}
        self.assertEqual(by_type, {BOLD: 'abc', ITALIC: 'def', STRIKETHROUGH: 'ghi'})

    def test_inline_offsets_are_utf16_units(self):
        text = '🔥 burn it'
        rich = article_to_rich_text(article([block(text, styles=[('Bold', 3, 4)])], title=''))
        self.assertEqual([covered(rich, s) for s in rich.spans], ['burn'])

    def test_links_from_entity_map_list_and_dict(self):
        entity = {'type': 'LINK', 'data': {'url': 'https://example.com'}}
        for entity_map in ([{'key': '0', 'value': entity}], {'0': entity}):
            rich = article_to_rich_text(article([block('see here now', links=[(0, 4, 4)])], entity_map, title=''))
            spans = [s for s in rich.spans if s.type == TEXT_LINK]
            self.assertEqual([(covered(rich, s), s.url) for s in spans], [('here', 'https://example.com')])

    def test_unknown_entity_is_ignored(self):
        rich = article_to_rich_text(article([block('abc', links=[(7, 0, 3)])], title=''))
        self.assertEqual(rich.spans, ())

    def test_headers_lists_quote_and_code(self):
        blocks = [block('Head', 'header-two'), block('one', 'unordered-list-item'), block('two', 'unordered-list-item'),
                  block('a', 'ordered-list-item'), block('b', 'ordered-list-item'), block('q', 'blockquote'),
                  block('x = 1', 'code-block')]
        rich = article_to_rich_text(article(blocks, title=''))
        self.assertEqual(rich.text, 'Head\n\n• one\n• two\n\n1. a\n2. b\n\nq\n\nx = 1')
        by_type = {s.type: covered(rich, s) for s in rich.spans}
        self.assertEqual(by_type, {BOLD: 'Head', BLOCKQUOTE: 'q', PRE: 'x = 1'})

    def test_ordered_list_restarts_after_other_blocks(self):
        blocks = [block('a', 'ordered-list-item'), block('text'), block('b', 'ordered-list-item')]
        self.assertEqual(article_to_rich_text(article(blocks, title='')).text, '1. a\n\ntext\n\n1. b')

    def test_atomic_and_empty_blocks_are_skipped(self):
        blocks = [block('x', 'atomic'), block('  '), block('real')]
        self.assertEqual(article_to_rich_text(article(blocks, title='')).text, 'real')

    def test_empty_article(self):
        self.assertFalse(article_to_rich_text({}))

    def test_long_article_is_truncated(self):
        blocks = [block('word ' * 100) for _ in range(50)]
        rich = article_to_rich_text(article(blocks), max_utf16_len=1000)
        self.assertLessEqual(utf16_len(rich.text), 1000)
        self.assertTrue(rich.text.endswith('…'))
        self.assertTrue(rich.text.startswith('Title'))


if __name__ == '__main__':
    unittest.main()
