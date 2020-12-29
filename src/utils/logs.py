import logging

import sentry_sdk

from functools import wraps
from typing import Union


logging.basicConfig(
    level=logging.DEBUG,
)
log = logging.getLogger(__name__)


def async_log_exception(f):

    @wraps(f)
    async def inner(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception as e:
            sentry_sdk.capture_exception(error=e)
            log.error(f'Exception in {f.__name__}: {e}')

    return inner


def pretty_time_delta(seconds: Union[int, float]) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return f'{days} days {hours} hours {minutes} min {seconds} sec'
    elif hours > 0:
        return f'{hours} hours {minutes} min {seconds} sec'
    elif minutes > 0:
        return f'{minutes} min {seconds} sec'
    else:
        return f'{seconds} sec'
