from fastapi import FastAPI

from app.api import campaigns, health, lookups

# No /docs, /redoc or /openapi.json over HTTP; scripts/gen-api-types.sh calls app.openapi().
app = FastAPI(title="AdRobot", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(lookups.router)
