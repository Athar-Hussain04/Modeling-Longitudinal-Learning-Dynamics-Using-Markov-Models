"""FastAPI scaffolding shared by all FYP chapter backends.

Each chapter's `backend/api.py` is expected to call `create_app(...)` once at
import time. The factory returns a fully wired FastAPI instance exposing:

    GET  /health   -> {"ok": True, "title": <title>}
    GET  /schema   -> the schema_dict the caller supplied (manual_demo block)
    POST /predict  -> predict_fn(payload_dict) wrapped in error handling

The frontend served from a sibling port hits `/predict` from the browser, so
CORS is permissive for localhost / 127.0.0.1 on any port.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Callable, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


LOG = logging.getLogger("fyp_shared.api")


def create_app(
    title: str,
    predict_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    schema_dict: Dict[str, Any],
) -> FastAPI:
    app = FastAPI(title=title)

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"ok": True, "title": title}

    @app.get("/schema")
    def schema() -> Dict[str, Any]:
        return schema_dict

    @app.post("/predict")
    async def predict(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_json", "detail": str(exc)},
            )

        if not isinstance(payload, dict):
            return JSONResponse(
                status_code=400,
                content={"error": "payload_must_be_object"},
            )

        try:
            result = predict_fn(payload)
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": "invalid_input", "detail": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001
            LOG.exception("predict_fn raised")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "prediction_failed",
                    "detail": str(exc),
                    "trace": traceback.format_exc(limit=4),
                },
            )

        if not isinstance(result, dict):
            return JSONResponse(
                status_code=500,
                content={"error": "predict_fn_must_return_dict"},
            )
        return JSONResponse(status_code=200, content=result)

    return app
