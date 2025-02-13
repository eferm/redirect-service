from __future__ import annotations

import datetime
import os
import pathlib
import re
import sqlite3
from typing import TYPE_CHECKING

import modal
from fastapi import FastAPI
from fastapi.responses import RedirectResponse


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response


VOL_DIR = pathlib.PurePosixPath("/data")
DB_FILE = "logs.db"

webapp = FastAPI()


@webapp.get("/{page}")
async def redirect_page(page: str) -> RedirectResponse:
    app_id = os.environ["APPLE_ID"]
    params = [
        f"pt={os.environ['PROVIDER_ID']}",  # Provider token
        f"ct={to_campaign_name(page)}",  # Campaign token
        "mt=8",  # Media type (8: iOS)
    ]
    return RedirectResponse(f"https://apps.apple.com/app/id{app_id}?{'&'.join(params)}")


@webapp.get("/")
async def redirect_root() -> RedirectResponse:
    return RedirectResponse("https://example.com")


@webapp.middleware("http")
async def log_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    with sqlite3.connect(VOL_DIR / DB_FILE) as conn:
        conn.execute(
            "INSERT INTO requests VALUES (?, ?, ?, ?)",
            (
                datetime.datetime.now(datetime.UTC).isoformat(),
                request.url.path,
                request.headers.get("user-agent"),
                request.client.host if request.client else None,
            ),
        )
    return response


app = modal.App("redirect-service")
image = modal.Image.debian_slim().pip_install("fastapi")
volume = modal.Volume.from_name("redirect-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={VOL_DIR: volume},
    secrets=[modal.Secret.from_name("apple-secret")],
)
@modal.asgi_app()
def main() -> FastAPI:
    init_db()
    return webapp


@app.function(volumes={VOL_DIR: volume})
def inspect_db() -> None:
    init_db()

    with sqlite3.connect(VOL_DIR / DB_FILE) as conn:
        cursor = conn.execute(
            """
            SELECT timestamp, path, user_agent, ip
            FROM requests
            ORDER BY timestamp
            LIMIT 10
            """,
        )

        for row in cursor.fetchall():
            timestamp, path, user_agent, ip = row
            print(f"{timestamp} {path:30} {user_agent} {ip}")  # noqa: T201


@app.function(volumes={VOL_DIR: volume})
def reset_db() -> None:
    init_db()

    with sqlite3.connect(VOL_DIR / DB_FILE) as conn:
        conn.execute("DELETE FROM requests")


def init_db() -> None:
    with sqlite3.connect(VOL_DIR / DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                timestamp TEXT,
                path TEXT,
                user_agent TEXT,
                ip TEXT
            )
            """,
        )


def to_campaign_name(text: str) -> str:
    """Return a valid campaign name.

    Reference:
    https://developer.apple.com/help/app-store-connect/view-app-analytics/manage-campaigns/
    """
    pattern = r'[^a-zA-Z0-9 \[\]\/\\\-~+=<>:;,\._\'"*&$%#@?!|{}()]'
    return re.sub(pattern, "", text.strip())[:30]
