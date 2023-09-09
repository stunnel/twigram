# -*- coding: utf-8 -*-

import os
import uvicorn
from quart import Quart, Response, request, jsonify

from telebot.bot import TelegramBot
from lib.logger import logger
from lib.version import version


async def webserver() -> None:
    logger.info(f'Starting bot')
    bot = TelegramBot()
    token = bot.get_token()
    port = int(os.environ.get('PORT', 8080))
    web_url = os.environ.get('WEB_URL')

    webhook_url = '{}/twigram/{}/down'.format(web_url, token)
    await bot.web(webhook_url)

    app = Quart(__name__)

    @app.get('/')
    @app.get('/twigram')
    @app.get('/twigram/')
    @app.get('/health')
    async def hello() -> Response:
        message = {'message': 'Hello World!', 'version': version}
        return jsonify(message)

    @app.post('/twigram/{}/down'.format(token))
    async def twigram() -> Response:
        result = await bot.task(request)
        logger.info(result)
        message = {'message': 'OK'}

        return jsonify(message)

    @app.get('/twigram/<path>')
    @app.post('/twigram/<path>')
    async def unknown_bot(path: str) -> Response:
        message = {'message': 'Unknown bot', 'version': version, 'path': path}
        return jsonify(message)

    server = uvicorn.Server(
        config=uvicorn.Config(
            app=app,
            port=port,
            use_colors=False,
            host='0.0.0.0',
        )
    )

    # Run application and web server together
    async with bot.application:
        await bot.application.start()
        await server.serve()
        await bot.application.stop()

    logger.info('Bot stopped, bye!')
