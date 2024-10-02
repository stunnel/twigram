# -*- coding: utf-8 -*-

from quart import Quart, Response, request, jsonify

from telebot.bot import TelegramBot
from lib.logger import logger
from lib.version import version

bot = TelegramBot()
token = bot.get_token()
app = Quart(__name__)


@app.before_serving
async def run_bot() -> None:
    await bot.run()
    if not bot.application.running:
        logger.info('Initializing bot')
        await bot.application.initialize()
        await bot.application.start()


@app.after_serving
async def stop():
    logger.info('Stopping bot')
    await bot.application.stop()


@app.get('/')
@app.get('/twigram')
@app.get('/twigram/')
@app.get('/health')
async def hello() -> Response:
    message = {'message': 'Bot works!', 'version': version}
    return jsonify(message)


@app.post('/twigram/{}/down'.format(token))
async def twigram() -> Response:
    await bot.task(request)
    message = {'message': 'OK'}

    return jsonify(message)


@app.get('/twigram/<path>')
@app.post('/twigram/<path>')
async def unknown_bot(path: str) -> Response:
    message = {'message': 'Unknown bot', 'version': version, 'path': path}
    return jsonify(message)
