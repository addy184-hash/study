"""智能学习伴侣 - FastAPI后端"""
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

from agents import process_chat_message, generate_ics

app = FastAPI(title="智能学习伴侣")

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ========== 请求模型 ==========
class ChatRequest(BaseModel):
    conv: Dict[str, Any]
    message: str


class IcsRequest(BaseModel):
    plan: Dict[str, Any]
    goal: str
    start_date: Optional[str] = None


# ========== API接口 ==========
@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>智能学习伴侣</h1><p>前端文件未找到</p>"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """处理对话消息，返回更新后的对话状态和AI回复"""
    conv = req.conv
    message = req.message

    # 调用agents.py的核心逻辑
    reply = process_chat_message(conv, message)

    return {
        "conv": conv,
        "reply": reply
    }


@app.post("/api/ics")
async def export_ics(req: IcsRequest):
    """生成ICS日历文件"""
    ics_content = generate_ics(req.plan, req.goal, req.start_date)
    safe_goal = "".join(c if c.isalnum() else "_" for c in req.goal)[:30]
    filename = f"{safe_goal}_study_plan.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
