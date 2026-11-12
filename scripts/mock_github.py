"""Local, deterministic GitHub REST simulator for performance testing only."""

import asyncio
import os

import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock GitHub API (Performance Test)")
app.state.repository_requests = 0


def _scenario() -> str:
    return os.environ.get("MOCK_GITHUB_SCENARIO", "PASS").strip().upper()


async def _apply_upstream_scenario() -> None:
    """Produce reproducible upstream failures before an endpoint returns data."""
    scenario = _scenario()
    status_by_scenario = {
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "RATE_LIMITED": 429,
        "SERVER_ERROR": 500,
    }
    if scenario in status_by_scenario:
        raise HTTPException(status_code=status_by_scenario[scenario], detail=scenario)
    if scenario not in {"PASS", "UNPROTECTED", "SIGNATURES_DISABLED"}:
        raise HTTPException(status_code=500, detail="Invalid mock scenario")
    await asyncio.sleep(float(os.environ.get("MOCK_GITHUB_LATENCY_SECONDS", "0.05")))


@app.middleware("http")
async def count_repository_requests(request, call_next):
    if request.url.path.startswith("/repos/"):
        app.state.repository_requests += 1
    return await call_next(request)


@app.get("/__metrics")
async def get_metrics():
    """Expose only the local simulator request count for measurement scripts."""
    return {"repository_requests": app.state.repository_requests}


@app.get("/repos/{owner}/{repo}")
async def get_repo(owner: str, repo: str):
    await _apply_upstream_scenario()
    return {"name": repo, "owner": {"login": owner}, "default_branch": "main"}


@app.get("/repos/{owner}/{repo}/branches/{branch}")
async def get_branch(owner: str, repo: str, branch: str):
    await _apply_upstream_scenario()
    return {"name": branch, "protected": True, "commit": {"sha": "a" * 40}}


@app.get("/repos/{owner}/{repo}/branches/{branch}/protection")
async def get_branch_protection(owner: str, repo: str, branch: str):
    await _apply_upstream_scenario()
    if _scenario() == "UNPROTECTED":
        raise HTTPException(status_code=404, detail="Branch not protected")
    return {
        "required_pull_request_reviews": {
            "required_approving_review_count": 2,
            "dismiss_stale_reviews": True,
        }
    }


@app.get("/repos/{owner}/{repo}/branches/{branch}/protection/required_signatures")
async def get_required_signatures(owner: str, repo: str, branch: str):
    await _apply_upstream_scenario()
    if _scenario() in {"UNPROTECTED", "SIGNATURES_DISABLED"}:
        raise HTTPException(status_code=404, detail="Required signatures are not enabled")
    return {"url": f"/repos/{owner}/{repo}/branches/{branch}/protection/required_signatures"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
