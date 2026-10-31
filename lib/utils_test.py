# -*- coding: utf-8 -*-

import unittest
from unittest import mock

import httpx

from lib.utils import Session

URL = 'https://pbs.twimg.com/media/a.jpg'


class FakeServer(object):
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(reply, content=b'body')


class TestRetry(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = mock.patch('lib.utils.asyncio.sleep', new_callable=mock.AsyncMock)
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    async def session(self, server):
        session = Session()
        self.addAsyncCleanup(session.aclose)
        await session._transport.aclose()
        session._transport = httpx.MockTransport(server)
        return session

    def test_default_timeout(self):
        timeout = Session().timeout
        self.assertEqual((timeout.connect, timeout.read), (10, 30))

    async def test_read_timeout_is_retried(self):
        server = FakeServer(httpx.ReadTimeout('slow'), httpx.ReadTimeout('slow'), 200)
        session = await self.session(server)

        response = await session.request_with_retry('GET', URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(server.calls, 3)
        self.assertEqual([call.args[0] for call in self.sleep.await_args_list], [1, 2])

    async def test_last_error_is_raised(self):
        server = FakeServer(*[httpx.ReadTimeout('slow') for _ in range(4)])
        session = await self.session(server)

        with self.assertRaises(httpx.ReadTimeout):
            await session.request_with_retry('GET', URL)

        self.assertEqual(server.calls, 4)
        self.assertEqual(self.sleep.await_count, 3)

    async def test_connect_error_is_left_to_transport(self):
        server = FakeServer(httpx.ConnectError('refused'))
        session = await self.session(server)

        with self.assertRaises(httpx.ConnectError):
            await session.request_with_retry('GET', URL)

        self.assertEqual(server.calls, 1)

    async def test_server_error_returns_last_response(self):
        server = FakeServer(503, 503, 503, 502)
        session = await self.session(server)

        response = await session.request_with_retry('GET', URL)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(server.calls, 4)

    async def test_not_found_is_not_retried(self):
        server = FakeServer(404)
        session = await self.session(server)

        response = await session.request_with_retry('GET', URL)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(server.calls, 1)


if __name__ == '__main__':
    unittest.main()
