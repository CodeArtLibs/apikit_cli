import asyncio
import random

from api_web.core import Command, Context
from api_web.dataclasses import Field
from api_web.utils.log import Log


# http POST http://localhost:50000/sample/helloworld
class HelloWorld(Command):
    method = 'GET'

    async def command(self, ctx: Context) -> Command.ResponseType:
        return {'Hello': 'World!' + 'a'}


# http POST http://localhost:50000/sample/sleep seconds=2
class Sleep(Command):
    schema = dict(seconds=Field(type='int', min=0, max=10))

    async def command(self, ctx: Context) -> Command.ResponseType:
        seconds: int = int(ctx.params.seconds or random.uniform(1, 5))
        Log.info(f'Sleeping for {seconds}s')
        await asyncio.sleep(seconds)
        Log.info(f'Slept {seconds}s')
        return f'Slept for {seconds}s'
