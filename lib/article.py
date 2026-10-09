# -*- coding: utf-8 -*-

import re

from lib.richtext import (BLOCKQUOTE, BOLD, ITALIC, PRE, STRIKETHROUGH, TEXT_LINK, RichText, Span,
                          utf16_to_code_points)

ARTICLE_URL_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?(?:x|twitter)\.com/i/article/(\d+)')

# Articles can be tens of thousands of characters, keep the chat from being flooded
ARTICLE_MAX_UTF16_LEN = 12000

_INLINE_STYLES = {'bold': BOLD, 'italic': ITALIC, 'strikethrough': STRIKETHROUGH}
_HEADER_BLOCKS = {'header-one', 'header-two', 'header-three', 'header-four', 'header-five', 'header-six'}


def find_article_link(tweet_result: dict) -> tuple[str, str]:
    """
    Return (short url shown in the tweet text, article id) if the tweet links to an Article, else ('', '').
    """
    urls = ((tweet_result.get('legacy') or {}).get('entities') or {}).get('urls') or []
    for item in urls:
        match = ARTICLE_URL_PATTERN.search(item.get('expanded_url') or '')
        if match:
            return item.get('url') or '', match.group(1)

    return '', ''


def get_cover_url(article: dict) -> str:
    media_info = (article.get('cover_media') or {}).get('media_info') or {}
    url = media_info.get('original_img_url') or ''

    return f'{url}?name=4096x4096' if url else ''


def _entity_map(content: dict) -> dict:
    """DraftJS entityMap is a dict, FxTwitter returns it as a list of {key, value}."""
    entity_map = content.get('entityMap') or {}
    if isinstance(entity_map, list):
        return {str(item.get('key')): item.get('value') or {} for item in entity_map if isinstance(item, dict)}

    return {str(key): value or {} for key, value in entity_map.items()}


def _block_to_rich_text(block: dict, entities: dict) -> RichText:
    text = block.get('text') or ''
    to_code_point = utf16_to_code_points(text)
    spans = []

    for item in block.get('inlineStyleRanges') or []:
        span_type = _INLINE_STYLES.get(str(item.get('style', '')).lower())
        offset, length = item.get('offset'), item.get('length')
        if span_type and isinstance(offset, int) and isinstance(length, int):
            spans.append(Span(span_type, to_code_point(offset), to_code_point(offset + length)))

    for item in block.get('entityRanges') or []:
        entity = entities.get(str(item.get('key'))) or {}
        url = (entity.get('data') or {}).get('url')
        offset, length = item.get('offset'), item.get('length')
        if entity.get('type') == 'LINK' and url and isinstance(offset, int) and isinstance(length, int):
            spans.append(Span(TEXT_LINK, to_code_point(offset), to_code_point(offset + length), url))

    return RichText(text, spans)


def article_to_rich_text(article: dict, max_utf16_len: int = ARTICLE_MAX_UTF16_LEN) -> RichText:
    """
    Convert an Article (title + DraftJS content blocks) to RichText.
    Images, embedded tweets and other atomic blocks are skipped.
    """
    content = article.get('content') or {}
    entities = _entity_map(content)

    title = (article.get('title') or '').strip()
    result = RichText(title, [Span(BOLD, 0, len(title))]) if title else RichText()

    ordered_index = 0
    previous_type = ''
    for block in content.get('blocks') or []:
        block_type = block.get('type') or 'unstyled'
        if block_type == 'atomic':
            continue

        body = _block_to_rich_text(block, entities)
        if not body.text.strip():
            previous_type = ''
            continue

        if block_type == 'ordered-list-item':
            ordered_index = ordered_index + 1 if previous_type == block_type else 1
            body = f'{ordered_index}. ' + body
        elif block_type == 'unordered-list-item':
            body = '• ' + body
        elif block_type in _HEADER_BLOCKS:
            body = RichText(body.text, list(body.spans) + [Span(BOLD, 0, len(body.text))])
        elif block_type == 'blockquote':
            body = RichText(body.text, list(body.spans) + [Span(BLOCKQUOTE, 0, len(body.text))])
        elif block_type == 'code-block':
            body = RichText(body.text, [Span(PRE, 0, len(body.text))])

        # items of the same list stay together, everything else is a paragraph
        is_list_item = block_type.endswith('-list-item') and previous_type == block_type
        separator = '\n' if is_list_item else '\n\n'
        result = result + separator + body if result else body
        previous_type = block_type

    if result.utf16_len() > max_utf16_len:
        result = result.split(max_utf16_len - 2)[0] + '\n…'

    return result
