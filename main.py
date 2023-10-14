#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Bot to get the media and text from Twitter and forward them to Telegram.

Press Ctrl-C on the command line or send a signal to the process to stop the bot.
"""

from web.router import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=58081, debug=True)
