from fastapi import FastAPI

from meloxo_common.errors import register_error_handlers

from gateway_auth.routes import health_router, router

PORT = 8004


def create_app() -> FastAPI:
    app = FastAPI(title="MELOXO gateway-auth", docs_url=None, openapi_url=None)
    register_error_handlers(app)
    app.include_router(router)
    app.include_router(health_router)
    return app


app = create_app()
