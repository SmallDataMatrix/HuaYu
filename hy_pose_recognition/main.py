from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from hy_pose_recognition.api import router as api_router
from hy_pose_recognition.core import settings
from hy_pose_recognition.services.storage import ensure_data_dirs


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_title, version=settings.version)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        return """
        <!doctype html>
        <html lang="zh-CN">
          <head><meta charset="utf-8"><title>华羽API</title></head>
          <body>
            <h1>华羽AI羽毛球训练分析API</h1>
            <p>请使用 <code>streamlit run streamlit_app.py</code> 启动Streamlit演示界面。</p>
          </body>
        </html>
        """

    return application


app = create_app()


def run() -> None:
    import uvicorn

    ensure_data_dirs()
    uvicorn.run("hy_pose_recognition.main:app", host="127.0.0.1", port=8000, reload=True)
