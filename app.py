# The Derailed API
#
# Copyright 2022 Derailed Inc. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import contextlib
import os
import threading
from typing import TYPE_CHECKING, Any

import sentry_sdk

with contextlib.suppress(ImportError):
    import uvloop  # type: ignore

    uvloop.install()

from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from derailed import database, etc, exceptions, guilds, tracks, users
from derailed.rate_limit import rate_limiter

load_dotenv()
app = FastAPI(openapi_url=None, redoc_url=None, docs_url=None)
app.state.limiter = rate_limiter

# Preloaded Instance Info
INSTANCE_NAME = os.getenv('INSTANCE_NAME', '0x1244')
NODE_ID = hex(threading.current_thread().ident)

if os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(dsn=os.environ['SENTRY_DSN'], traces_sample_rate=1.0)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# feature modules
modules: list[str] = []
features: list[dict[str, Any]] = [
    {
        'name': 'core',
        'version': 0,
        'module': 'derailed',
        'creator': 'Derailed Inc.',
        'copyright': '2022 Derailed Inc. All rights reserved.',
        'description': 'Derailed\'s core and base product.',
    }
]

# Load plugins with this function in your own instance.
async def load_features() -> None:
    for module in modules:
        mod = __import__(module)

        await mod.load(app=app)

        if (
            not mod.FEATURE_INFO
            or ['name', 'version', 'creator'] not in mod.FEATURE_INFO
        ):
            raise exceptions.DerailedException(
                f'(Feature Module missing data exception) {repr(mod.__name__)} is missing one of name, version, or creator.'
            )

        if TYPE_CHECKING:
            mod.FEATURE_INFO: dict[str, Any] = {}

        mod.FEATURE_INFO['load_id'] = str(uuid4())

        features.append(mod.FEATURE_INFO)


@app.on_event('startup')
async def on_startup():
    await database.connect()

    # Load base routers
    app.include_router(users.personal.router)
    app.include_router(users.settings.router)
    app.include_router(users.presence.router)
    app.include_router(guilds.guild.router)
    app.include_router(guilds.role.router)
    app.include_router(etc.relationships.router)
    app.include_router(tracks.gdm)
    app.include_router(tracks.gtr)
    app.include_router(tracks.mta)
    app.include_router(tracks.msg)
    app.include_router(guilds.invs)

    # Load extra routers, plugins, or other modules.
    await load_features()


@app.get('/')
@rate_limiter.limit('1/second')
async def get_instance_information(request: Request, response: Response) -> dict:
    return {'instance_id': INSTANCE_NAME, 'node_id': NODE_ID, 'features': features}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000, log_level='debug')
