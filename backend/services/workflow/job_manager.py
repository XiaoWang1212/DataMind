from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .workflow_service import WorkflowService

_JOB_TTL_SECONDS = 60 * 60  # 已結束的 job 保留 1 小時後清掉，避免字典無限長大


class WorkflowJob:
    def __init__(self, job_id: str, total_models: int, user_id: int) -> None:
        self.job_id = job_id
        self.user_id = user_id
        self.status = "running"  # running | done | error
        self.total_models = total_models
        self.completed: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.finished_at: Optional[float] = None


_jobs: Dict[str, WorkflowJob] = {}
_lock = threading.Lock()


def _purge_old_jobs() -> None:
    now = time.time()
    stale_ids = [
        job_id
        for job_id, job in _jobs.items()
        if job.finished_at is not None and now - job.finished_at > _JOB_TTL_SECONDS
    ]
    for job_id in stale_ids:
        del _jobs[job_id]


def start_job(data_path: str, user_id: int, **kwargs: Any) -> str:
    model_names = kwargs.get("model_names") or []
    preprocess_pipelines = kwargs.get("preprocess_pipelines") or [[]]
    total_models = max(1, len(model_names)) * max(1, len(preprocess_pipelines))

    job_id = uuid.uuid4().hex
    job = WorkflowJob(job_id, total_models, user_id)

    with _lock:
        _purge_old_jobs()
        _jobs[job_id] = job

    thread = threading.Thread(target=_run_job, args=(job_id, data_path), kwargs=kwargs, daemon=True)
    thread.start()
    return job_id


def _run_job(job_id: str, data_path: str, **kwargs: Any) -> None:
    job = _jobs[job_id]
    try:
        for event in WorkflowService.execute_workflow_stream(data_path=data_path, **kwargs):
            if event.get("type") == "model_done":
                with _lock:
                    job.completed.append({
                        "model_name": event.get("model_name"),
                        "results": event.get("results"),
                    })
            elif event.get("type") == "done":
                with _lock:
                    job.result = event
                    job.status = "done"
                    job.finished_at = time.time()
    except Exception as exc:
        with _lock:
            job.status = "error"
            job.error = str(exc)
            job.finished_at = time.time()


def get_job(job_id: str) -> Optional[WorkflowJob]:
    with _lock:
        return _jobs.get(job_id)
