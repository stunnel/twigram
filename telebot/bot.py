# -*- coding: utf-8 -*-

import os
import sys

import validators
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from lib.logger import logger
from lib.utils import Session
from twitterclient.twitter import TwitterClient

version = '0.2'
message = ('*Tweet forward Bot*',
           f'Version: {version}\n',
           '*Usage:*',
           '`/down <url>`: Grab tweet and send to telegram.',
           '`/start`: Show this message.',
           '`/help`: Show this message.',)


class TelegramBot(object):
    def __init__(self, ):
        self.logger = logger
        self.application = Application.builder().token(self.get_token()).build()
        self.debug = os.environ.get('DEBUG', False) in {'True', 'true', 'TRUE', '1'}
        self.client = TwitterClient(debug=self.debug)
        self.session = Session()
        self.set_bot_handler()

    def run(self):
        _interval = os.environ.get('INTERVAL', 30.0)
        try:
            interval = float(_interval)
        except ValueError:
            self.logger.warning('INTERVAL is not a number, use default value 30')
            interval = 30.0

        self.application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=interval)

    async def web(self, url):
        self.logger.info('Setting webhook: %s', url)
        result = await self.application.bot.set_webhook(url=url, allowed_updates=Update.ALL_TYPES)

        if result:
            self.logger.info('Webhook setup OK, URL: %s', url)
        else:
            self.logger.info('Webhook setup FAILED, URL: %s', url)
            raise Exception('Webhook setup failed.')

    async def task(self, request):
        msg = await request.get_json()
        self.logger.info('Message received: %s', msg)

        update_result = await self.application.update_queue.put(Update.de_json(msg, self.application.bot))
        self.logger.info('Queue added.')

        return update_result

    def stop(self):
        self.application.stop()

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
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.download))

    @staticmethod
    async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Send a message when the command /help is issued.
        """
        text = '\n'.join(message)
        (text.replace('_', '\\_')
         .replace('*', '\\*')
         .replace('[', '\\[')
         .replace('`', '\\`'))

        await update.message.reply_markdown(text, quote=False)

    async def download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        urls = await self.get_urls(update.message.text)
        if not urls:
            await update.message.reply_text('Can\'t find any Twitter url in your message.', quote=True)
        for url in urls:
            await self.download_twitter(update, url)

    async def download_twitter(self, update: Update, url: str):
        images_path, videos_path, text = await self.client.download(url)
        if len(images_path) + len(videos_path) > 0:
            await self.send_media(update=update, images_path=images_path, videos_path=videos_path, text=text)
        elif text:
            await update.message.reply_text(text, quote=True, disable_web_page_preview=True)
        else:
            await update.message.reply_text('Download failed.', quote=True)

    async def send_media(self, update: Update, images_path: [str], videos_path: [str], text: str = ''):
        medias = []

        for image_path in images_path:
            medias.append(InputMediaPhoto(media=open(image_path, 'rb')))

        for video_path in videos_path:
            medias.append(InputMediaVideo(media=open(video_path, 'rb')))

        if len(text) > 1024:
            await update.message.reply_media_group(media=medias, quote=True)
            await update.message.reply_text(text, quote=True, disable_web_page_preview=True)
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

    async def get_urls(self, chat_msg: str) -> list:
        urls = []

        chat_list = chat_msg.split()
        for msg in chat_list:
            if validators.url(msg):
                msg = await self.session.url_strict(msg)  # follow URL redirect, remove tracking code
                if (msg.startswith('https://twitter.com/')
                        or msg.startswith('https://x.com/')
                        or msg.startswith('https://mobile.twitter.com/')
                        or msg.startswith('https://www.twitter.com/')
                        or msg.startswith('https://m.twitter.com/')):
                    urls.append(msg)

        if not urls:
            self.logger.error('URL not found.')
        else:
            self.logger.info('Get URL: %s', urls)

        return urls
