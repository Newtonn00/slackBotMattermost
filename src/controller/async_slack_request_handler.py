import logging
from aiohttp import web

from slack_bolt.adapter.aiohttp import to_aiohttp_response, to_bolt_request


class AsyncSlackRequestHandler:

    def __init__(self, app):
        self.app = app
        self._logger_bot = logging.getLogger("")

    async def handle(self, request: web.Request):
        self._logger_bot.info(f"Handling request: {request}")
        bolt_request = await to_bolt_request(request)
        bolt_response = await self.app.async_dispatch(bolt_request)
        self._logger_bot.info("Request handled successfully")
        return await to_aiohttp_response(bolt_response)


__all__ = [
    "AsyncSlackRequestHandler",
]
