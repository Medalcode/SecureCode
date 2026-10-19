import asyncio
import os
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="Mock GitHub API (Performance Test)")

@app.get("/repos/{owner}/{repo}")
async def get_repo(owner: str, repo: str):
    # Simula latencia de red de GitHub (100ms)
    await asyncio.sleep(0.1)
    return {"name": repo, "owner": {"login": owner}, "default_branch": "main"}

@app.get("/repos/{owner}/{repo}/branches/{branch}")
async def get_branch(owner: str, repo: str, branch: str):
    await asyncio.sleep(0.1)
    return {
        "name": branch,
        "protected": True,
        "commit": {
            "sha": "a" * 40
        }
    }

@app.get("/repos/{owner}/{repo}/branches/{branch}/protection")
async def get_branch_protection(owner: str, repo: str, branch: str):
    await asyncio.sleep(0.15)

    scenario = os.environ.get("MOCK_GH002_SCENARIO", "PASS").upper()

    if scenario == "FAIL":
        # La rama existe, pero no tiene protección configurada.
        raise HTTPException(
            status_code=404,
            detail="Branch not protected"
        )

    if scenario == "UNKNOWN":
        # GitHub no permite determinar la configuración.
        raise HTTPException(
            status_code=403,
            detail="Resource not accessible"
        )

    if scenario != "PASS":
        raise HTTPException(
            status_code=500,
            detail="Invalid mock scenario"
        )

    return {
        "required_pull_request_reviews": {
            "required_approving_review_count": 2,
            "dismiss_stale_reviews": True
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
