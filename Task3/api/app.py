import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from masar.cli import OUTPUT_DIR
from masar.engine.errors import ResumeError, StoreError, WorkflowError

from .schemas import ChatRequest, DecisionRequest, ResetRequest, RunRequest
from .service import UPLOAD_MAX_BYTES, BadInput, NotFound, Service

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
WEB_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # the vite dev server


def create_app(output_dir=None):
    svc = Service(Path(output_dir or os.environ.get("MASAR_OUTPUT") or OUTPUT_DIR))
    app = FastAPI(title="Masar API", version="1.0.0",
                  description="Local sandbox only. Nothing is published, every saved record is a draft.")
    app.state.service = svc
    # a page on another site cannot reach this server through a fake host name
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    app.add_middleware(CORSMiddleware, allow_origins=WEB_ORIGINS, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    def error(status, detail, **extra):
        return JSONResponse(status_code=status, content={"detail": detail, **extra})

    app.add_exception_handler(NotFound, lambda r, ex: error(404, str(ex)))
    app.add_exception_handler(BadInput, lambda r, ex: error(422, str(ex)))
    app.add_exception_handler(WorkflowError, lambda r, ex: error(422, "workflow rejected", errors=ex.errors))
    app.add_exception_handler(ResumeError, lambda r, ex: error(409, str(ex)))
    app.add_exception_handler(StoreError, lambda r, ex: error(409, str(ex)))

    @app.get("/api")
    def info():
        return {"name": "Masar", "version": "1.0.0", "note": "local sandbox only, drafts only"}

    @app.get("/api/workflows")
    def workflows():
        return svc.list_workflows()

    @app.get("/api/workflows/{key}")
    def workflow(key: str):
        return svc.get_workflow(key)

    @app.get("/api/samples")
    def samples():
        return svc.list_samples()

    @app.post("/api/samples/upload", status_code=201)
    async def upload(request: Request, name: str):
        # read the body in pieces and stop early when it gets too big
        body = bytearray()
        async for chunk in request.stream():
            body += chunk
            if len(body) > UPLOAD_MAX_BYTES:
                return error(413, f"file is too big (max {UPLOAD_MAX_BYTES} bytes)")
        return svc.save_upload(name, bytes(body))

    @app.post("/api/runs")
    def start_run(req: RunRequest):
        return svc.start_run(req.workflow, req.sample, req.dry_run, req.approved_by)

    @app.get("/api/runs")
    def runs():
        return svc.list_runs()

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        return svc.get_run(run_id)

    @app.get("/api/reviews")
    def reviews():
        return svc.reviews()

    @app.post("/api/reviews/{run_id}/{source_id}")
    def decide(run_id: str, source_id: str, req: DecisionRequest):
        return svc.decide(run_id, source_id, req.reviewer, req.decision, req.reason)

    @app.get("/api/drafts")
    def drafts():
        return svc.drafts()

    @app.get("/api/audit")
    def audit():
        return svc.audit()

    @app.get("/api/audit/verify")
    def verify():
        return svc.verify()

    @app.post("/api/challenges/run")
    def challenges():
        results = svc.challenges()
        return {"passed": sum(r["passed"] for r in results), "total": len(results), "results": results}

    @app.post("/api/ask")
    def chat(req: ChatRequest):
        return svc.chat(req.question, req.lang, req.run_id, req.source_id, req.index, req.item, req.workflow)

    @app.post("/api/demo/reset")
    def reset(req: ResetRequest):
        return svc.reset(req.seed)

    return app


app = create_app()
