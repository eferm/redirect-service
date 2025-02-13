from __future__ import annotations

import modal
from fastapi import FastAPI
from fastapi.responses import RedirectResponse


app = modal.App("redirect-service")
webapp = FastAPI()


@webapp.get("/{page}")
async def redirect_page(page: str) -> RedirectResponse:
    target_domain = "https://example.com"
    return RedirectResponse(url=f"{target_domain}?page={page}")


@webapp.get("/")
async def redirect_root() -> RedirectResponse:
    return RedirectResponse(url="https://example.com")


image = modal.Image.debian_slim().pip_install("fastapi")


@app.function(image=image)
@modal.asgi_app()
def main() -> modal.App:
    return webapp


# To deploy:
# 1. Save this as app.py
# 2. Run: modal deploy app.py
# To run locally for development:
# modal serve app.py
