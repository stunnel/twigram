# -*- coding: utf-8 -*-

import asyncio
import httpx
import re
from urllib.parse import urlparse

from lib.logger import logger

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class Session(httpx.AsyncClient):
    def __init__(self, connections=20, retries=5):
        self.default_header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Mac OS X 10_15_7) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}
        self.twitter_set = {'twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'x.com', 'www.x.com'}
        self.replace_domain_set = {'fixupx.com',    't.fixupx.com',    'g.fixupx.com',    'd.fixupx.com',
                                   'fxtwitter.com', 't.fxtwitter.com', 'g.fxtwitter.com', 'd.fxtwitter.com',
                                   'vxtwitter.com', 't.vxtwitter.com', 'g.vxtwitter.com', 'd.vxtwitter.com',
                                   'fixvx.com',     't.fixvx.com',     'g.fixvx.com',     'd.fixvx.com'}
        self.tweet_pattern = r'^/([^/]+)/status/(\d+)'
        self.x_set = {'x.com', 'www.x.com'}
        limits = httpx.Limits(max_connections=connections * 2, max_keepalive_connections=connections)
        http_transport = httpx.AsyncHTTPTransport(http2=True, retries=retries, verify=False, limits=limits)

        timeout = httpx.Timeout(30, connect=10)

        super().__init__(headers=self.default_header, transport=http_transport, timeout=timeout)
        self.session = self

    @staticmethod
    def should_retry(error: Exception) -> bool:
        # connection failures are already retried by the transport
        if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
            return False
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in RETRY_STATUS_CODES
        return isinstance(error, httpx.TransportError)

    async def retry(self, func, url: str, max_attempts: int = 4):
        """
        Call func until it succeeds, waiting 1s, 2s, 4s between attempts.
        Only network errors and RETRY_STATUS_CODES are retried, the last error is raised.
        :param func: async function without arguments
        :param url: for logging
        :param max_attempts:
        :return: result of func
        """
        attempt = 1
        while True:
            try:
                return await func()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                if attempt >= max_attempts or not self.should_retry(e):
                    raise
                logger.info(f'Request {url} failed: {e!r}, retrying... ({attempt}/{max_attempts})')

            await asyncio.sleep(2 ** (attempt - 1))
            attempt += 1

    async def request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Send a request with retries.
        :return: the last response, its status code may still be an error
        """
        async def send():
            response = await self.request(method, url, **kwargs)
            if response.status_code in RETRY_STATUS_CODES:
                response.raise_for_status()
            return response

        try:
            return await self.retry(send, url)
        except httpx.HTTPStatusError as e:
            return e.response

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
        url_result = url
        if url_parse.hostname in self.twitter_set:
            url_result = '{}://{}{}'.format('https', url_parse.hostname, url_parse.path)
        elif url_parse.hostname in self.replace_domain_set:
            match = re.match(self.tweet_pattern, url_parse.path)
            if match:
                path_result = '/{}/status/{}'.format(match.group(1), match.group(2))
                url_result = '{}://{}{}'.format('https', 'x.com', path_result)

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
