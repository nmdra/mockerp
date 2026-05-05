from fastapi import FastAPI
from routers import finance, hr, inventory

app = FastAPI(title="Mock ERP Service")

app.include_router(finance.router)
app.include_router(hr.router)
app.include_router(inventory.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
