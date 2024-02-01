from concurrent.futures import ThreadPoolExecutor
from aiohttp import web


class ThreadedWebApplication(web.Application):
    def __init__(self, app_manager, executor=None):
        super().__init__()
        self.app_manager = app_manager
        self.executor = executor

        self.router.add_post("/slack/events", self.handle_slack_events)
        self.router.add_get("/auth/redirect", self.handle_auth_redirect)

    async def handle_slack_events(self, request):
        return await self.handle_request(request)

    async def handle_auth_redirect(self, request):
        return await self.handle_request(request)

    async def handle_request(self, request):
        return await self.app_manager.handle(request)

    def run(self, port=3005):
        executor = self.executor or ThreadPoolExecutor()
        runner = web.AppRunner(self, executor=executor)
        web.run_app(self, port=port)
