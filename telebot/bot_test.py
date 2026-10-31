# -*- coding: utf-8 -*-

import logging
import os
import tempfile
import unittest
from unittest import mock

from telegram import Update

from telebot.bot import TelegramBot
from twitterclient.twitterclient import TwitterClient

URL = 'https://x.com/user/status/1'


class TestErrorReply(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        self.bot = TelegramBot.__new__(TelegramBot)
        self.bot.logger = logging.getLogger(__name__)
        self.bot.quote = False
        self.bot.debug = False
        self.bot.client = mock.Mock(spec=TwitterClient)
        self.bot.client.debug = False
        self.bot.client.download = mock.AsyncMock()
        self.bot.client.remove_files = lambda files: TwitterClient.remove_files(self.bot.client, files)
        self.update = mock.Mock(spec=Update)
        self.update.message.reply_text = mock.AsyncMock()

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.image = os.path.join(temp_dir.name, 'a.jpg')
        with open(self.image, 'wb') as f:
            f.write(b'image')

    def replies(self):
        return [call.args[0] for call in self.update.message.reply_text.await_args_list]

    async def test_download_error_is_replied(self):
        self.bot.client.download.side_effect = KeyError('legacy')

        await self.bot.download_twitter(self.update, URL)

        self.assertEqual(self.replies(), [f'Download failed: {URL}'])

    async def test_send_error_is_replied_and_files_removed(self):
        self.bot.client.download.return_value = ([self.image], [], 'text')
        self.bot.send_media = mock.AsyncMock(side_effect=RuntimeError('telegram'))

        with mock.patch('telebot.bot.expand_urls_in_text', side_effect=lambda text: text):
            await self.bot.download_twitter(self.update, URL)

        self.assertEqual(self.replies(), [f'Download failed: {URL}'])
        self.assertFalse(os.path.exists(self.image))

    async def test_files_removed_after_success(self):
        self.bot.client.download.return_value = ([self.image], [], 'text')
        self.bot.send_media = mock.AsyncMock()

        with mock.patch('telebot.bot.expand_urls_in_text', side_effect=lambda text: text):
            await self.bot.download_twitter(self.update, URL)

        self.assertEqual(self.replies(), [])
        self.assertFalse(os.path.exists(self.image))

    async def test_files_kept_in_debug_mode(self):
        self.bot.client.debug = True
        self.bot.client.download.return_value = ([self.image], [], 'text')
        self.bot.send_media = mock.AsyncMock()

        with mock.patch('telebot.bot.expand_urls_in_text', side_effect=lambda text: text):
            await self.bot.download_twitter(self.update, URL)

        self.assertTrue(os.path.exists(self.image))

    async def test_failed_reply_does_not_stop_next_url(self):
        self.bot.client.download.side_effect = KeyError('legacy')
        self.update.message.reply_text.side_effect = RuntimeError('telegram')

        await self.bot.download_twitter(self.update, URL)
        await self.bot.download_twitter(self.update, URL)

        self.assertEqual(self.bot.client.download.await_count, 2)

    async def test_error_handler_replies(self):
        context = mock.Mock(error=RuntimeError('boom'))

        await self.bot.error_handler(self.update, context)

        self.assertEqual(self.replies(), ['Something went wrong, please try again later.'])

    async def test_error_handler_ignores_non_update(self):
        await self.bot.error_handler(None, mock.Mock(error=RuntimeError('boom')))

        self.assertEqual(self.replies(), [])


if __name__ == '__main__':
    unittest.main()
