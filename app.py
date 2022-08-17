# The Itch API
#
# Copyright 2022 Itch. All rights reserved.
#
# Sharing of any piece of code to any unauthorized third-party is not allowed.
import os

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from scratch import database, guilds, rate_limit, users

load_dotenv()
app = FastAPI(openapi_url=None, redoc_url=None, docs_url=None)
rate_limiter = rate_limit.get_limiter()
app.state.limiter = rate_limiter

if os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(dsn=os.environ['SENTRY_DSN'], traces_sample_rate=1.0)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event('startup')
async def on_startup():
    await database.connect()
    app.include_router(guilds.information.router)
    app.include_router(users.personal.router)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000, log_level='debug')
