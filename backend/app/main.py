"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import wallets, cex, tax, reports

# Import tax rules to register them
import app.tax_rules.germany  # noqa: F401

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Crypto tax tracking and calculation API"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(wallets.router, prefix=f"{settings.api_prefix}/wallets", tags=["wallets"])
app.include_router(cex.router, prefix=f"{settings.api_prefix}/cex", tags=["cex"])
app.include_router(tax.router, prefix=f"{settings.api_prefix}/tax", tags=["tax"])
app.include_router(reports.router, prefix=f"{settings.api_prefix}/reports", tags=["reports"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Crypto Tax Tracker API",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
