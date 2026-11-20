from fastapi import FastAPI

from app.api import campaigns, drafts, errors, health, lookups, push

# No /docs, /redoc or /openapi.json over HTTP; scripts/gen-api-types.sh calls app.openapi().
app = FastAPI(title="AdRobot", docs_url=None, redoc_url=None, openapi_url=None)
errors.register(app)
app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(drafts.router)
app.include_router(push.router)
app.include_router(lookups.router)
