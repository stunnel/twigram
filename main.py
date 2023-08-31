#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Bot to get the media and text from Twitter and forward them to Telegram.

Press Ctrl-C on the command line or send a signal to the process to stop the bot.
"""

import os
import asyncio

from telebot.bot import TelegramBot
from web.web import webserver


if __name__ == '__main__':
    if os.environ.get('WEB_URL'):
        asyncio.run(webserver())
    else:
        bot = TelegramBot()
        asyncio.run(bot.run())
