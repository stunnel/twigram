# -*- coding: utf-8 -*-

import httpx
from urllib.parse import urlparse

from lib.logger import logger


class Session(httpx.AsyncClient):
    def __init__(self, connections=20, retries=5):
        self.default_header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Mac OS X 10_15_7) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}
        self.twitter_set = {'twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'x.com', 'www.x.com'}
        self.x_set = {'x.com', 'www.x.com'}
        limits = httpx.Limits(max_connections=connections * 2, max_keepalive_connections=connections)
        http_transport = httpx.AsyncHTTPTransport(http2=True, retries=retries, verify=False, limits=limits)

        super().__init__(headers=self.default_header, transport=http_transport)
        self.session = self

    async def url_strict(self, url: str) -> str:
        """
        Follow redirects and return the final URL.
        Remove sensitive information from certain URLs, including Twitter tracking parameters.
        :param url:
        :return:
        """
        url = self.remove_tracker_from_url(url)  # remove tracking parameters
        url = await self.url_get_redirect(url, 0)  # follow redirects
        url = self.remove_tracker_from_url(url)  # remove tracking parameters again

        return url

    def remove_tracker_from_url(self, url: str) -> str:
        """
        Remove tracking parameters
        :param url:
        :return:
        """

        url_parse = urlparse(url)
        if url_parse.hostname in self.twitter_set:
            url_result = '{}://{}{}'.format(url_parse.scheme, url_parse.hostname, url_parse.path)
        else:
            url_result = url

        return url_result

    async def url_get_redirect(self, url: str, max_times: int) -> str:
        try:
            x = max_times or 0
            x += 1
            if x > 5:
                return url

            url_parse = urlparse(url)
            if url_parse.hostname in self.x_set:
                return url

            response = await self.session.get(url, follow_redirects=False)
            if response.status_code in (301, 302, 303, 307, 308):
                if response.headers.get('Location') and not response.headers.get('Location').startswith('http'):
                    url_parse = urlparse(url)
                    url = '{}://{}{}'.format(url_parse.scheme, url_parse.hostname, response.headers.get('Location'))
                    url = self.remove_tracker_from_url(url)
                    return await self.url_get_redirect(url, x)
                elif response.headers.get('Location'):
                    url = self.remove_tracker_from_url(response.headers.get('Location'))
                    return await self.url_get_redirect(url, x)
                else:
                    return url
            elif response.status_code == 200:
                return url
            else:
                return url
        except Exception as e:
            logger.error(e)
            return url


def split_long_string(input_string: str, max_length: int = 4096) -> list:
    if len(input_string) <= max_length:
        return [input_string]

    result_strings = []
    temp_lines = []
    temp_length = 0

    lines = input_string.splitlines()
    for line in lines:
        if temp_length + len(line) <= max_length:
            temp_lines.append(line)
            temp_length += len(line) + 1
        else:
            result_strings.append('\n'.join(temp_lines))
            temp_lines = [line]
            temp_length = len(line) + 1

    result_strings.append('\n'.join(temp_lines))

    return result_strings
