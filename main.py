from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from database import Database
from dependencies import CredentialResolver
from routers import finance, hr, integration, inventory, organization
from seed import seed_platform
from settings import load_settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    database = Database(settings.database_path)
    database.initialize()
    seed_platform(database)
    application.state.settings = settings
    application.state.database = database
    application.state.credential_resolver = CredentialResolver(settings)
    try:
        yield
    finally:
        database.close()
        for attribute in ("settings", "database", "credential_resolver"):
            application.state.__dict__.pop(attribute, None)


app = FastAPI(title="Mock ERP Service", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def erpnext_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    if isinstance(exc.detail, dict) and "exc_type" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"message": str(exc.detail)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(finance.router)
app.include_router(organization.router)
app.include_router(hr.router)
app.include_router(inventory.router)
app.include_router(integration.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
