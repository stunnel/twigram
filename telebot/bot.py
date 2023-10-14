# -*- coding: utf-8 -*-

import os
import re
import sys
import validators

from telegram import Update, Message, InputMediaVideo, InputMediaDocument
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from lib.logger import logger
from lib.utils import Session, split_long_string
from lib import version
from twitterclient.twitter import TwitterClient

_url_prefixes = (r'https://(?:www\.|mobile\.|m\.)?twitter\.com/', r'https://x\.com/')


class TelegramBot(object):
    def __init__(self, ):
        self.logger = logger
        self.application = Application.builder().token(self.get_token()).build()
        self.debug = os.environ.get('DEBUG', False) in {'True', 'true', 'TRUE', '1'}
        self.client = TwitterClient(debug=self.debug)
        self.url_pattern = re.compile('|'.join(_url_prefixes))
        self.session = Session()
        self.set_bot_handler()

    def poll(self):
        interval_default = 30.0
        _interval = os.environ.get('INTERVAL', interval_default)
        try:
            interval = float(_interval)
        except ValueError:
            interval = interval_default
            self.logger.warning('INTERVAL is not a number, use default value %s', interval)

        self.application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=interval)

    async def web(self, url):
        self.logger.info('Setting webhook: %s', url)
        result = await self.application.bot.set_webhook(url=url, allowed_updates=Update.ALL_TYPES)

        if result:
            self.logger.info('Webhook setup OK, URL: %s', url)
        else:
            self.logger.info('Webhook setup FAILED, URL: %s', url)
            raise Exception('Webhook setup failed.')

    async def run(self):
        self.logger.info(f'Starting bot')
        if os.environ.get('WEB_URL_ENABLE') in {'True', 'true', 'TRUE', '1'}:
            web_url = os.environ.get('WEB_URL')
            webhook_url = '{}/twigram/{}/down'.format(web_url, self.get_token())
            self.logger.info(f'Starting bot in webhook mode with url: {web_url}/twigram/TOKEN/down')
            await self.web(webhook_url)
        else:
            self.logger.info('Starting bot in polling mode')
            self.poll()

    async def task(self, request):
        msg = await request.get_json()
        self.logger.info('Message received: %s', msg)

        await self.application.update_queue.put(Update.de_json(msg, self.application.bot))
        self.logger.info('Queue added.')

    def get_token(self) -> str:
        token = os.environ.get('TOKEN', None)
        if not token:
            self.logger.fatal('Can\'t find bot token in environment variable "%s"\n'
                              'TOKEN is not setting.', token)
            sys.exit(1)

        return token

    def set_bot_handler(self):
        self.application.add_handler(CommandHandler('start', self.help))
        self.application.add_handler(CommandHandler('help', self.help))
        self.application.add_handler(CommandHandler('down', self.download))
        self.application.add_handler(CommandHandler('download', self.download))
        self.application.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, self.download))

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Send a message when the command /help is issued.
        """
        text = '\n'.join(version.message)
        escaped_text = re.sub(r'[_*`[]', r'\\\g<0>', text)
        self.logger.info(escaped_text)

        await update.message.reply_markdown(escaped_text, quote=False)

    async def download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        urls = await self.get_urls(update.message)
        if not urls:
            await self.reply_text(update, "Can't find any Twitter url in your message.")
        for url in urls[:10]:   # limit to 10 urls
            await self.download_twitter(update, url)

    async def download_twitter(self, update: Update, url: str):
        images_path, videos_path, text = await self.client.download(url)
        if len(images_path) + len(videos_path) > 0:
            await self.send_media(update=update, images_path=images_path, videos_path=videos_path, text=text)
        elif text:
            await self.reply_text(update, text)
        else:
            await self.reply_text(update, 'Download failed.')

    @staticmethod
    async def reply_text(update: Update, text: str):
        quote = True
        if len(text) <= 4096:
            await update.message.reply_text(text, quote=quote, disable_web_page_preview=True)
        else:
            text_split = split_long_string(text)
            for text_part in text_split:
                await update.message.reply_text(text_part, quote=quote, disable_web_page_preview=True)
                quote = False

    async def send_media(self, update: Update, images_path: [str], videos_path: [str], text: str = ''):
        medias = []

        for image_path in images_path:
            medias.append(InputMediaDocument(media=open(image_path, 'rb')))

        for video_path in videos_path:
            medias.append(InputMediaVideo(media=open(video_path, 'rb'), supports_streaming=True))

        if len(text) > 1024:
            await update.message.reply_media_group(media=medias, quote=True)
            await self.reply_text(update, text)
        else:
            await update.message.reply_media_group(media=medias, caption=text, quote=True)

        if not self.debug:
            await self.delete_files(images_path, videos_path)

    @staticmethod
    async def delete_files(images_path: [str], videos_path: [str]):
        for image_path in images_path:
            os.remove(image_path)

        for video_path in videos_path:
            os.remove(video_path)

    async def get_urls(self, message: Message) -> list:
        urls = []
        self.logger.debug(message)

        if message.text:
            urls = await self.extract_url(message.text)
        if not urls and message.caption:
            urls = await self.extract_url(message.caption)

        if not urls:
            self.logger.error('URL not found.')
        else:
            self.logger.info('Get URL: %s', urls)

        return urls

    async def extract_url(self, text: str) -> list:
        urls = []
        test_split = text.split()
        for msg in test_split:
            if validators.url(msg):
                msg = await self.session.url_strict(msg)  # follow URL redirect, remove tracking code
                if self.url_pattern.match(msg):
                    urls.append(msg)

        return urls
