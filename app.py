from __future__ import annotations

import os
import urllib.parse

import modal
from fastapi import FastAPI
from fastapi.responses import RedirectResponse


app = modal.App("redirect-service")
webapp = FastAPI()


@webapp.get("/{page}")
async def redirect_page(page: str) -> RedirectResponse:
    campaign = urllib.parse.quote(page)
    target = f"https://apps.apple.com/app/id{os.environ['APP_ID']}?ct={campaign}"
    return RedirectResponse(url=target)


@webapp.get("/")
async def redirect_root() -> RedirectResponse:
    return RedirectResponse(url="https://example.com")


image = modal.Image.debian_slim().pip_install("fastapi")


@app.function(image=image, secrets=[modal.Secret.from_name("apple-secret")])
@modal.asgi_app()
def main() -> FastAPI:
    return webapp
