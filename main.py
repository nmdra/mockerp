from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from routers import finance, hr, inventory

app = FastAPI(title="Mock ERP Service")

@app.exception_handler(HTTPException)
async def erpnext_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "exc_type" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)}
    )

app.include_router(finance.router)
app.include_router(hr.router)
app.include_router(inventory.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
