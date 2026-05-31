"""CAD 生成路由（前台 + 异步任务队列）"""

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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_superuser
from app.db.database import get_db, SessionLocal
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.generation import GenerationRecord
from app.schemas.generation import (
    GenerationRecordCreate,
    GenerationRecordUpdate,
    GenerationRecordInDB,
    GenerationRecordListResponse,
    GenerationRecordWithUser,
    GenerationRecordWithUserListResponse,
)
from app.crud.generation import (
    create_record,
    update_record,
    get_records_by_user,
    get_all_records,
    get_record,
)

settings = get_settings()

router = APIRouter()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = settings.REPO_ROOT
GENERATED_DIR = settings.GENERATED_DIR
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
        key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            return None
        base_url = settings.OPENAI_BASE_URL or os.getenv("OPENAI_BASE_URL", "").strip() or None
        _openai_client = AsyncOpenAI(
            api_key=key,
            base_url=base_url,
            timeout=360,  # client-level timeout (must be > LLM expected time)
            max_retries=1,
        )
    return _openai_client


def _get_llm_model():
    return (settings.LLM_MODEL or os.getenv("LLM_MODEL", "gpt-4o")).strip()


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------
CAD_SYSTEM_PROMPT = """You are an expert CAD modeling assistant.
The user describes a mechanical part in natural language (Chinese or English).
Your entire response must be **ONLY** valid Python code — no explanations, no markdown, no text before or after the code.

CRITICAL — You MUST use **build123d** and NOTHING else:
- Use `from build123d import *` at the top.
- Do NOT use `import Part`, `import cadquery`, `import FreeCAD`, or any other CAD library.
- Do NOT use `Part.makeBox`, `Part.makeCylinder`, `cq.Workplane`, or any non-build123d API.

Coordinate convention (ALWAYS follow this):
- XY plane is the base plane.
- +Z is the UP / extrusion direction.
- The part bottom sits at Z = 0 and is centred on the XY origin unless the user says otherwise.
- "长度方向" = Z direction (extrusion direction).
- "宽度方向" = X direction.
- "高度/厚度方向" = Y direction.
- "径向" = from the centre outward in XY plane.

Key build123d patterns you MUST know:

1. Solid block:
   with BuildPart() as part:
       with Locations((0, 0, height/2)):
           Box(length, width, height)
   return part.part

2. Hollow tube / rectangular pipe (ALWAYS hollow when user says "管" / "pipe" / "tube"):
   The user may write dimensions like "140x60x5mm" for a rectangular pipe — this means outer_width=140, outer_height=60, wall_thickness=5.
   You MUST compute inner dimensions and create a HOLLOW shape.
   Use Plane.XY for the subtract sketch (Do NOT use part.faces().sort_by(Axis.Z).first — BuildSketch does NOT accept Face objects):
   with BuildPart() as part:
       with BuildSketch():
           Rectangle(outer_width, outer_height)
       extrude(amount=length)
       with BuildSketch(Plane.XY):
           Rectangle(outer_width - 2*wall_thickness, outer_height - 2*wall_thickness)
       extrude(amount=length, mode=Mode.SUBTRACT)
   return part.part

3. Cylinder (hollow or solid):
   with BuildPart() as part:
       with Locations((0, 0, height/2)):
           Cylinder(radius=outer_r, height=height)
       with BuildSketch(Plane.XY):
           Circle(radius=inner_r)
       extrude(amount=height, mode=Mode.SUBTRACT)
   return part.part

4. Hole / slot along length (Z direction):
   with BuildPart() as part:
       # ... create base part ...
       with Locations((0, 0, length/2)):
           Box(slot_width, slot_height, length+1, mode=Mode.SUBTRACT)
   return part.part

5. Circular holes through the part:
   with BuildPart() as part:
       # ... create base part ...
       with Locations((hole_x, hole_y, height/2)):
           Cylinder(radius=hole_r, height=height+1, mode=Mode.SUBTRACT)
   return part.part

IMPORTANT dimension shorthand rules:
- "AxBxCmm 矩形管" means outer_width=A, outer_height=B, wall_thickness=C.
- "直径Dmm 圆管" or "外径Dmm 圆管" means outer_diameter=D.
- "管壁厚度Tmm" or "壁厚Tmm" means wall_thickness=T (overrides any earlier thickness if different).

Requirements:
1. Define exactly one function: `def gen_step():`
2. The function must return a build123d `Shape`, `Solid`, or `Compound`.
3. Use named variables for every dimension (e.g. `width = 100.0`).
4. Default units are **millimetres (mm)**.
5. Do NOT write file I/O, print statements, or `if __name__ == "__main__"`.
6. Do NOT wrap the code in markdown fences (```python).
7. Do NOT include any Chinese or English explanation text.
8. Use `Rotation` (singular), NOT `Rotations`.
9. `Rotation` takes Euler angles as positional args: `Rotation(x_angle, y_angle, z_angle)` — e.g. `Rotation(0, -90, 0)` for a -90° rotation about Y. Do NOT use keyword args like `Rotation(about_y=...)`, `Rotation(axis=...)`, or `Rotation(angle=...)`.
10. When the user says "均匀分布" / "evenly spaced", use a loop or list comprehension with Locations.

Example 1 — "100 x 60 x 20 mm block with four 8 mm holes":

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

Example 2 — "140x80x5mm rectangular pipe, length 500mm, with a 100x30mm rectangular slot through the center along the length":

from build123d import *

def gen_step():
    outer_width = 140.0
    outer_height = 80.0
    wall_thickness = 5.0
    length = 500.0
    slot_width = 100.0
    slot_height = 30.0

    inner_width = outer_width - 2 * wall_thickness
    inner_height = outer_height - 2 * wall_thickness

    with BuildPart() as part:
        with BuildSketch():
            Rectangle(outer_width, outer_height)
        extrude(amount=length)
        with BuildSketch(Plane.XY):
            Rectangle(inner_width, inner_height)
        extrude(amount=length, mode=Mode.SUBTRACT)
        with Locations((0, 0, length / 2)):
            Box(slot_width, slot_height, length + 1, mode=Mode.SUBTRACT)
    return part.part

Example 3 — "outer diameter 70mm, inner diameter 60mm, length 500mm hollow cylinder with 5 evenly spaced 10mm diameter radial through-holes":

from build123d import *

def gen_step():
    import math
    outer_dia = 70.0
    inner_dia = 60.0
    length = 500.0
    hole_dia = 10.0
    num_holes = 5

    with BuildPart() as part:
        with Locations((0, 0, length / 2)):
            Cylinder(radius=outer_dia / 2, height=length)
        with BuildSketch(Plane.XY):
            Circle(radius=inner_dia / 2)
        extrude(amount=length, mode=Mode.SUBTRACT)

        for i in range(num_holes):
            angle = 2 * math.pi * i / num_holes
            x = (outer_dia / 2) * math.cos(angle)
            y = (outer_dia / 2) * math.sin(angle)
            with Locations((x, y, length / 2)):
                with Rotation(0, math.degrees(angle) + 90, 0):
                    Cylinder(radius=hole_dia / 2, height=outer_dia + 1, mode=Mode.SUBTRACT)
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


def _sync_update_db_record(record_id: int, status: str, message: str, paths: dict | None = None):
    """在线程中同步更新数据库记录"""
    db = SessionLocal()
    try:
        record = db.query(GenerationRecord).filter(GenerationRecord.id == record_id).first()
        if record:
            record.status = status
            record.message = message
            if paths:
                record.py_path = paths.get("py")
                record.step_path = paths.get("step")
                record.glb_path = paths.get("glb")
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Core generation pipeline (runs in background)
# ---------------------------------------------------------------------------
async def _run_generation(task_id: str, prompt: str, model_id: str, db_record_id: int):
    work_dir = GENERATED_DIR / model_id
    work_dir.mkdir(parents=True, exist_ok=True)

    py_file = work_dir / f"{model_id}.py"
    step_file = work_dir / f"{model_id}.step"
    glb_file = work_dir / f".{model_id}.step.glb"

    async def _safe_db_update(status: str, message: str, paths: dict | None = None):
        try:
            await asyncio.to_thread(_sync_update_db_record, db_record_id, status, message, paths)
        except Exception:
            pass

    try:
        # cache hit
        if step_file.exists() and glb_file.exists():
            await _update_task(
                task_id,
                TaskStatus.CACHED,
                "Model already exists.",
                {"model_id": model_id},
            )
            await _safe_db_update(
                "cached",
                "Model already exists.",
                {
                    "py": str(py_file) if py_file.exists() else None,
                    "step": str(step_file),
                    "glb": str(glb_file),
                },
            )
            return

        # ---- 1. LLM call ----
        await _update_task(task_id, TaskStatus.LLM_RUNNING, "Generating Python code via LLM...")
        await _safe_db_update("llm_running", "Generating Python code via LLM...")

        client = _get_openai_client()
        if client is None:
            await _update_task(task_id, TaskStatus.FAILED, "LLM API key not configured.")
            await _safe_db_update("failed", "LLM API key not configured.")
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
            msg = "LLM request timed out after 300s."
            await _update_task(task_id, TaskStatus.FAILED, msg)
            await _safe_db_update("failed", msg)
            return
        except Exception as exc:
            await _update_task(task_id, TaskStatus.FAILED, f"LLM request failed: {exc}")
            await _safe_db_update("failed", f"LLM request failed: {exc}")
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
            msg = f"LLM did not return a valid gen_step function. Raw output: {debug_file}"
            await _update_task(task_id, TaskStatus.FAILED, msg)
            await _safe_db_update("failed", msg)
            return

        if "import Part" in code or "Part.make" in code:
            msg = f"LLM returned FreeCAD/Part code instead of build123d. Raw output: {debug_file}"
            await _update_task(task_id, TaskStatus.FAILED, msg)
            await _safe_db_update("failed", msg)
            return

        # Fix common LLM hallucinations
        code = code.replace("Rotations(", "Rotation(")
        # BuildSketch does NOT accept Face objects — replace with Plane.XY
        code = re.sub(
            r"BuildSketch\([^)]*\.faces\(\)[^)]*\)",
            "BuildSketch(Plane.XY)",
            code,
        )
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
        await _safe_db_update("cad_running", "Running build123d to generate STEP/GLB...")

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
            msg = "CAD generation timed out (300s)."
            await _update_task(task_id, TaskStatus.FAILED, msg)
            await _safe_db_update("failed", msg)
            return

        if proc.returncode != 0:
            error_log = work_dir / f"{model_id}_step_error.log"
            error_log.write_text(f"STDERR:\n{proc.stderr}\n\nSTDOUT:\n{proc.stdout}", encoding="utf-8")
            short_err = (proc.stderr or proc.stdout or "").strip()[:800]
            msg = f"STEP generation failed. Log: {error_log}\n{short_err}"
            await _update_task(task_id, TaskStatus.FAILED, msg)
            await _safe_db_update("failed", msg)
            return

        if not step_file.exists():
            msg = "STEP file was not produced."
            await _update_task(task_id, TaskStatus.FAILED, msg)
            await _safe_db_update("failed", msg)
            return

        await _update_task(
            task_id,
            TaskStatus.COMPLETED,
            "CAD model generated successfully.",
            {"model_id": model_id},
        )
        await _safe_db_update(
            "completed",
            "CAD model generated successfully.",
            {
                "py": str(py_file),
                "step": str(step_file),
                "glb": str(glb_file) if glb_file.exists() else None,
            },
        )
    except Exception as exc:
        import traceback
        msg = f"Unexpected generation error: {exc}"
        await _update_task(task_id, TaskStatus.FAILED, msg)
        await _safe_db_update("failed", msg)
        raise


# ---------------------------------------------------------------------------
# Schemas for API
# ---------------------------------------------------------------------------
from pydantic import BaseModel


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=GenerateResponse)
async def generate_cad(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(400, "prompt is empty")

    model_id = hashlib.sha256(prompt.encode()).hexdigest()[:12]
    task_id = hashlib.sha256(f"{prompt}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]

    # Create DB record
    db_record = create_record(
        db,
        GenerationRecordCreate(
            user_id=current_user.id,
            model_id=model_id,
            prompt=prompt,
            status="pending",
        ),
    )

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
    asyncio.create_task(_run_generation(task_id, prompt, model_id, db_record.id))

    return GenerateResponse(
        task_id=task_id,
        model_id=model_id,
        status="pending",
        message="Task accepted. Poll /api/v1/cad/tasks/{task_id} for progress.",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
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


@router.get("/records", response_model=GenerationRecordListResponse)
async def list_my_records(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records, total = get_records_by_user(db, current_user.id, skip=skip, limit=limit, status=status)
    return GenerationRecordListResponse(
        items=[GenerationRecordInDB.model_validate(r) for r in records],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/records/{record_id}", response_model=GenerationRecordInDB)
async def get_my_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_record(db, record_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Record not found.")
    return record


@router.get("/models/{model_id}/glb")
async def get_glb(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    glb_file = GENERATED_DIR / model_id / f".{model_id}.step.glb"
    if not glb_file.exists():
        raise HTTPException(404, "GLB not found.")
    return FileResponse(glb_file, media_type="model/gltf-binary", filename=f"{model_id}.glb")


@router.get("/models/{model_id}/step")
async def get_step(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    step_file = GENERATED_DIR / model_id / f"{model_id}.step"
    if not step_file.exists():
        raise HTTPException(404, "STEP not found.")
    return FileResponse(step_file, media_type="application/step", filename=f"{model_id}.step")


@router.get("/models/{model_id}/code")
async def get_code(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    py_file = GENERATED_DIR / model_id / f"{model_id}.py"
    if not py_file.exists():
        raise HTTPException(404, "Source code not found.")
    return FileResponse(py_file, media_type="text/x-python", filename=f"{model_id}.py")


# ---------------------------------------------------------------------------
# Admin routes for generation records
# ---------------------------------------------------------------------------
@router.get("/admin/records", response_model=GenerationRecordWithUserListResponse)
async def admin_list_records(
    skip: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    _: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    records, total = get_all_records(db, skip=skip, limit=limit, user_id=user_id, status=status, search=search)
    items = []
    for r in records:
        data = GenerationRecordInDB.model_validate(r).model_dump()
        data["username"] = r.user.username if r.user else None
        data["email"] = r.user.email if r.user else None
        items.append(GenerationRecordWithUser(**data))
    return GenerationRecordWithUserListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/admin/records/{record_id}", response_model=GenerationRecordWithUser)
async def admin_get_record(
    record_id: int,
    _: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    record = get_record(db, record_id)
    if not record:
        raise HTTPException(404, "Record not found.")
    data = GenerationRecordInDB.model_validate(record).model_dump()
    data["username"] = record.user.username if record.user else None
    data["email"] = record.user.email if record.user else None
    return GenerationRecordWithUser(**data)


@router.get("/admin/stats")
async def admin_stats(
    _: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func
    total_users = db.query(func.count(User.id)).scalar()
    total_records = db.query(func.count(GenerationRecord.id)).scalar()
    completed_records = db.query(func.count(GenerationRecord.id)).filter(GenerationRecord.status == "completed").scalar()
    failed_records = db.query(func.count(GenerationRecord.id)).filter(GenerationRecord.status == "failed").scalar()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_records = db.query(func.count(GenerationRecord.id)).filter(GenerationRecord.created_at >= today).scalar()
    return {
        "total_users": total_users,
        "total_records": total_records,
        "completed_records": completed_records,
        "failed_records": failed_records,
        "today_records": today_records,
    }
