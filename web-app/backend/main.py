"""
Text-to-CAD Web API (Async)
FastAPI backend that turns natural language into STEP/GLB via LLM + build123d.
Uses an in-memory task queue so long-running CAD generation never blocks HTTP.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from jose import jwt, JWTError
import bcrypt as _bcrypt

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "text-to-cad-dev-secret-key-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    # bcrypt max password length is 72 bytes
    pw = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(pw, _bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    return _bcrypt.checkpw(pw, hashed.encode("utf-8"))


def _create_token(data: dict, expires_delta_minutes: int) -> str:
    from datetime import timedelta
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


class UserInDB(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    hashed_password: str


# In-memory user store (username -> UserInDB)
_users_db: dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        email="admin@example.com",
        full_name="Administrator",
        hashed_password=_hash_password("admin123"),
    ),
}


async def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    payload = _decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(401, "Invalid token payload")
    user = _users_db.get(username)
    if not user:
        raise HTTPException(401, "User not found")
    return user

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def _find_repo_root() -> Path:
    """Walk up from this file until we find the repo root (contains skills/cad/scripts/step)."""
    start = Path(__file__).resolve().parent
    for parent in [start, *start.parents]:
        if (parent / "skills" / "cad" / "scripts" / "step").exists():
            return parent
    # Fallback: assume standard layout (backend/main.py -> text-to-cad)
    return Path(__file__).resolve().parent.parent.parent


REPO_ROOT = _find_repo_root()
GENERATED_DIR = REPO_ROOT / "web-app" / "generated_models"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

STEP_SCRIPT = REPO_ROOT / "skills" / "cad" / "scripts" / "step"

# ---------------------------------------------------------------------------
# OpenAI-compatible client
# ---------------------------------------------------------------------------
_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError:  # pragma: no cover
            return None
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            return None
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        _openai_client = AsyncOpenAI(api_key=key, base_url=base_url, timeout=360)
    return _openai_client


def _get_llm_model():
    return os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o")).strip()


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------
CAD_SYSTEM_PROMPT = """You are an expert CAD modeling assistant.
The user describes a mechanical part in natural language (Chinese or English).
Your entire response must be **ONLY** valid Python code — no explanations, no markdown, no text before or after the code.

Requirements:
1. Define exactly one function: `def gen_step():`
2. The function must return a build123d `Shape`, `Solid`, or `Compound`.
3. Use named variables for every dimension (e.g. `width = 100.0`).
4. Default units are **millimetres (mm)**.
5. Coordinate convention: XY is the base plane, +Z is up / extrusion direction.
6. The part bottom should sit at Z = 0 and be centred on the XY origin unless the user says otherwise.
7. Import only `from build123d import *` at the top.
8. Do NOT write file I/O, print statements, or `if __name__ == "__main__"`.
9. Do NOT wrap the code in markdown fences (```python).
10. Do NOT include any Chinese or English explanation text.
11. Use `Rotation` (singular), NOT `Rotations`.
12. `Rotation` takes Euler angles as positional args: `Rotation(x_angle, y_angle, z_angle)` — e.g. `Rotation(0, -90, 0)` for a -90° rotation about Y. Do NOT use keyword args like `Rotation(about_y=...)`, `Rotation(axis=...)`, or `Rotation(angle=...)`.

Example output for "100 x 60 x 20 mm block with four 8 mm holes":

from build123d import *

def gen_step():
    length = 100.0
    width = 60.0
    height = 20.0
    hole_dia = 8.0
    hole_offset_x = 35.0
    hole_offset_y = 20.0

    with BuildPart() as part:
        with Locations((0, 0, height / 2)):
            Box(length, width, height)
        with Locations(
            ( hole_offset_x,  hole_offset_y, 0),
            (-hole_offset_x,  hole_offset_y, 0),
            ( hole_offset_x, -hole_offset_y, 0),
            (-hole_offset_x, -hole_offset_y, 0),
        ):
            Cylinder(radius=hole_dia / 2, height=height + 1, mode=Mode.SUBTRACT)
    return part.part
"""


# ---------------------------------------------------------------------------
# Async task queue
# ---------------------------------------------------------------------------
class TaskStatus(str, Enum):
    PENDING = "pending"
    LLM_RUNNING = "llm_running"
    CAD_RUNNING = "cad_running"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class Task:
    task_id: str
    model_id: str
    prompt: str
    status: TaskStatus
    created_at: str
    updated_at: str = ""
    message: str = ""
    result: dict[str, Any] = field(default_factory=dict)


_tasks: dict[str, Task] = {}
_task_lock = asyncio.Lock()


async def _update_task(task_id: str, status: TaskStatus, message: str = "", result: dict | None = None):
    async with _task_lock:
        task = _tasks.get(task_id)
        if task:
            task.status = status
            task.message = message
            task.updated_at = datetime.utcnow().isoformat() + "Z"
            if result:
                task.result.update(result)


# ---------------------------------------------------------------------------
# Core generation pipeline (runs in background)
# ---------------------------------------------------------------------------
async def _run_generation(task_id: str, prompt: str, model_id: str):
    work_dir = GENERATED_DIR / model_id
    work_dir.mkdir(parents=True, exist_ok=True)

    py_file = work_dir / f"{model_id}.py"
    step_file = work_dir / f"{model_id}.step"
    glb_file = work_dir / f".{model_id}.step.glb"

    # cache hit
    if step_file.exists() and glb_file.exists():
        await _update_task(
            task_id,
            TaskStatus.CACHED,
            "Model already exists.",
            {"model_id": model_id},
        )
        return

    # ---- 1. LLM call ----
    await _update_task(task_id, TaskStatus.LLM_RUNNING, "Generating Python code via LLM...")
    client = _get_openai_client()
    if client is None:
        await _update_task(task_id, TaskStatus.FAILED, "LLM API key not configured.")
        return

    try:
        payload = {
            "model": _get_llm_model(),
            "messages": [
                {"role": "system", "content": CAD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        if "kimi" not in _get_llm_model().lower():
            payload["temperature"] = 0.2
            payload["max_tokens"] = 2048
        else:
            payload["max_tokens"] = 8192

        async with asyncio.timeout(300):
            chat = await client.chat.completions.create(**payload)
        raw_code = chat.choices[0].message.content or ""
    except asyncio.TimeoutError:
        await _update_task(task_id, TaskStatus.FAILED, "LLM request timed out after 300s.")
        return
    except Exception as exc:
        await _update_task(task_id, TaskStatus.FAILED, f"LLM request failed: {exc}")
        return

    # ---- 2. Extract code ----
    raw_code = raw_code.strip()
    debug_file = work_dir / f"{model_id}_llm_raw.txt"
    debug_file.write_text(raw_code, encoding="utf-8")

    fence_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", raw_code, re.DOTALL)
    code = fence_match.group(1).strip() if fence_match else raw_code

    start_idx = code.find("from build123d import")
    if start_idx == -1:
        start_idx = code.find("import build123d")
    if start_idx == -1:
        start_idx = code.find("def gen_step()")
    if start_idx != -1:
        code = code[start_idx:].strip()

    # trim trailing text after gen_step
    lines = code.splitlines()
    cleaned_lines = []
    inside_gen_step = False
    gen_step_indent = None
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("def gen_step("):
            inside_gen_step = True
            gen_step_indent = len(line) - len(stripped)
            cleaned_lines.append(line)
            continue
        if inside_gen_step:
            if stripped == "" or (len(line) - len(stripped)) > gen_step_indent or stripped.startswith("return"):
                cleaned_lines.append(line)
                if stripped.startswith("return"):
                    continue
            else:
                inside_gen_step = False
                break
        else:
            cleaned_lines.append(line)
    code = "\n".join(cleaned_lines).strip()

    if "def gen_step()" not in code:
        await _update_task(
            task_id,
            TaskStatus.FAILED,
            f"LLM did not return a valid gen_step function. Raw output: {debug_file}",
        )
        return

    # Fix common LLM hallucinations
    code = code.replace("Rotations(", "Rotation(")

    # Fix Rotation(about_y=-90) -> Rotation(0, -90, 0)
    def _fix_rotation(match: re.Match) -> str:
        x = match.group("x") or "0"
        y = match.group("y") or "0"
        z = match.group("z") or "0"
        return f"Rotation({x}, {y}, {z})"

    code = re.sub(
        r"Rotation\(\s*about_x\s*=\s*([^,\)]+)\s*\)",
        lambda m: f"Rotation({m.group(1).strip()}, 0, 0)",
        code,
    )
    code = re.sub(
        r"Rotation\(\s*about_y\s*=\s*([^,\)]+)\s*\)",
        lambda m: f"Rotation(0, {m.group(1).strip()}, 0)",
        code,
    )
    code = re.sub(
        r"Rotation\(\s*about_z\s*=\s*([^,\)]+)\s*\)",
        lambda m: f"Rotation(0, 0, {m.group(1).strip()})",
        code,
    )

    py_file.write_text(code, encoding="utf-8")

    # ---- 3. Run scripts/step ----
    await _update_task(task_id, TaskStatus.CAD_RUNNING, "Running build123d to generate STEP/GLB...")
    loop = asyncio.get_event_loop()
    try:
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [sys.executable, str(STEP_SCRIPT), str(py_file)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            ),
        )
    except subprocess.TimeoutExpired:
        await _update_task(task_id, TaskStatus.FAILED, "CAD generation timed out (300s).")
        return

    if proc.returncode != 0:
        error_log = work_dir / f"{model_id}_step_error.log"
        error_log.write_text(f"STDERR:\n{proc.stderr}\n\nSTDOUT:\n{proc.stdout}", encoding="utf-8")
        short_err = (proc.stderr or proc.stdout or "").strip()[:800]
        await _update_task(
            task_id,
            TaskStatus.FAILED,
            f"STEP generation failed. Log: {error_log}\n{short_err}",
        )
        return

    if not step_file.exists():
        await _update_task(task_id, TaskStatus.FAILED, "STEP file was not produced.")
        return

    await _update_task(
        task_id,
        TaskStatus.COMPLETED,
        "CAD model generated successfully.",
        {"model_id": model_id},
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Text-to-CAD API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    task_id: str
    model_id: str
    status: str
    message: str = ""


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
    model_id: str
    created_at: str
    updated_at: str


@app.get("/api/health")
async def health():
    client = _get_openai_client()
    return {
        "ok": True,
        "llm_configured": client is not None,
        "llm_model": _get_llm_model(),
        "llm_base_url": os.getenv("OPENAI_BASE_URL", "").strip() or "default (openai.com)",
        "repo_root": str(REPO_ROOT),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_cad(req: GenerateRequest):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(400, "prompt is empty")

    model_id = hashlib.sha256(prompt.encode()).hexdigest()[:12]
    task_id = hashlib.sha256(f"{prompt}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]

    task = Task(
        task_id=task_id,
        model_id=model_id,
        prompt=prompt,
        status=TaskStatus.PENDING,
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    async with _task_lock:
        _tasks[task_id] = task

    # kick off background work
    asyncio.create_task(_run_generation(task_id, prompt, model_id))

    return GenerateResponse(
        task_id=task_id,
        model_id=model_id,
        status="pending",
        message="Task accepted. Poll /api/tasks/{task_id} for progress.",
    )


@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    async with _task_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found.")
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        message=task.message,
        model_id=task.model_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@app.get("/api/models/{model_id}/glb")
async def get_glb(model_id: str):
    glb_file = GENERATED_DIR / model_id / f".{model_id}.step.glb"
    if not glb_file.exists():
        raise HTTPException(404, "GLB not found.")
    return FileResponse(glb_file, media_type="model/gltf-binary", filename=f"{model_id}.glb")


@app.get("/api/models/{model_id}/step")
async def get_step(model_id: str):
    step_file = GENERATED_DIR / model_id / f"{model_id}.step"
    if not step_file.exists():
        raise HTTPException(404, "STEP not found.")
    return FileResponse(step_file, media_type="application/step", filename=f"{model_id}.step")


@app.get("/api/models/{model_id}/code")
async def get_code(model_id: str):
    py_file = GENERATED_DIR / model_id / f"{model_id}.py"
    if not py_file.exists():
        raise HTTPException(404, "Source code not found.")
    return FileResponse(py_file, media_type="text/x-python", filename=f"{model_id}.py")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    email: str
    full_name: str | None = None


@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    if len(req.username) < 3 or len(req.username) > 50:
        raise HTTPException(400, "Username must be 3-50 characters.")
    if not re.match(r"^[a-zA-Z0-9_-]+$", req.username):
        raise HTTPException(400, "Username must be alphanumeric, hyphens, or underscores.")
    if req.username in _users_db:
        raise HTTPException(409, "Username already exists.")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")

    user = UserInDB(
        username=req.username,
        email=req.email,
        full_name=req.full_name,
        hashed_password=_hash_password(req.password),
    )
    _users_db[req.username] = user

    access_token = _create_token({"sub": user.username, "type": "access"}, ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token = _create_token({"sub": user.username, "type": "refresh"}, REFRESH_TOKEN_EXPIRE_MINUTES)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.post("/api/v1/auth/login/json", response_model=TokenResponse)
async def login_json(req: LoginRequest):
    user = _users_db.get(req.username)
    if not user or not _verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid username or password.")
    access_token = _create_token({"sub": user.username, "type": "access"}, ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token = _create_token({"sub": user.username, "type": "refresh"}, REFRESH_TOKEN_EXPIRE_MINUTES)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(user: UserInDB = Depends(_get_current_user)):
    return UserResponse(username=user.username, email=user.email, full_name=user.full_name)


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    payload = _decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token.")
    username = payload.get("sub")
    user = _users_db.get(username) if username else None
    if not user:
        raise HTTPException(401, "User not found.")
    access_token = _create_token({"sub": user.username, "type": "access"}, ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token = _create_token({"sub": user.username, "type": "refresh"}, REFRESH_TOKEN_EXPIRE_MINUTES)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------
DIST_DIR = Path(__file__).resolve().parent / ".." / "frontend" / "dist"
if DIST_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
