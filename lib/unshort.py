# -*- coding: utf-8 -*-

import re
from unshortenit import UnshortenIt

SHORT_DOMAINS = [
    'bit.ly', 't.co', 'tinyurl.com', 'goo.gl', 'ow.ly', 'buff.ly',
    'is.gd', 'rebrand.ly', 'trib.al', 'bit.do', 'soo.gd', 'cutt.ly'
]

SHORT_URL_PATTERN = re.compile(
    rf'https?://(?:{"|".join(re.escape(d) for d in SHORT_DOMAINS)})/\S+',
    re.IGNORECASE
)

unshortener = UnshortenIt()

def expand_urls_in_text(text):
    def replacer(match):
        short_url = match.group(0)
        try:
            full_url = unshortener.unshorten(short_url)
            return full_url or short_url
        except Exception:
            return short_url

    return SHORT_URL_PATTERN.sub(replacer, text)


if __name__ == '__main__':
    sample_text = 'look at this url https://www.google.com/ and this one https://bit.ly/xyz789 and this one https://t.co/QZyY5p7PEA'
    expanded_text = expand_urls_in_text(sample_text)
    print(expanded_text)
