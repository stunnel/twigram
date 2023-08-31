# -*- coding: utf-8 -*-

import os
import logging


def get_logger():
    # Enable logging
    _logger = logging.getLogger()
    debug = os.environ.get('DEBUG') in {'True', 'true', 'TRUE', '1'}
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    return _logger


logger = get_logger()
