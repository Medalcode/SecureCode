"""Run the API for local performance tests without monkeypatching networking."""

import os

import uvicorn

os.environ["SECURECODE_GITHUB_TEST_MODE"] = "1"
os.environ["SECURECODE_GITHUB_TEST_BASE_URL"] = "http://127.0.0.1:8001"


if __name__ == "__main__":
    uvicorn.run("securecode.api.app:app", host="127.0.0.1", port=8000)
