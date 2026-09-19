"""Thin wrapper over the Cognee Cloud REST API (/api/v1). The only file that knows Cognee's API."""

import json
import time
from pathlib import Path

import httpx

from pipeline import config


class Conflict(Exception):
    """File already exists in the dataset with different content (HTTP 409)."""


_client = httpx.Client(
    base_url=f"{config.COGNEE_API_URL}/api/v1",
    headers={"X-Api-Key": config.COGNEE_API_KEY},
    timeout=httpx.Timeout(120.0, connect=15.0),
    follow_redirects=True,
)


def _check(resp: httpx.Response) -> httpx.Response:
    if resp.status_code == 409:
        raise Conflict(resp.text)
    if resp.is_error:
        raise RuntimeError(f"{resp.request.method} {resp.request.url} -> {resp.status_code}: {resp.text[:500]}")
    return resp


def add_file(path: Path, dataset: str, metadata: dict, node_set: list[str] | None = None) -> None:
    with path.open("rb") as f:
        _check(_client.post(
            "/add",
            files={"data": (path.name, f, "text/plain")},
            data={"datasetName": dataset, "external_metadata": json.dumps([metadata]), "node_set": node_set or [""]},
        ))


def update_file(path: Path, data_id: str, dataset_id: str) -> None:
    """Replace an existing document; Cognee re-processes the changed chunks itself."""
    with path.open("rb") as f:
        _check(_client.patch(
            "/update",
            params={"data_id": data_id, "dataset_id": dataset_id},
            files={"data": (path.name, f, "text/plain")},
            timeout=900.0,
        ))


def get_dataset_id(name: str) -> str | None:
    for ds in _check(_client.get("/datasets/")).json():
        if ds["name"] == name:
            return ds["id"]
    return None


def list_data(dataset_id: str) -> list[dict]:
    return _check(_client.get(f"/datasets/{dataset_id}/data")).json()


def cognify(dataset: str, dataset_id: str, custom_prompt: str = "", poll_seconds: int = 10, timeout_seconds: int = 1800) -> None:
    """Start cognify in the background and poll until the dataset finishes processing."""
    _check(_client.post("/cognify", json={"datasets": [dataset], "run_in_background": True, "custom_prompt": custom_prompt}))
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        time.sleep(poll_seconds)
        status = str(_check(_client.get("/datasets/status", params={"dataset": dataset_id})).json().get(dataset_id, ""))
        if "COMPLETED" in status:
            return
        if "ERRORED" in status:
            raise RuntimeError(f"cognify failed for dataset {dataset}: {status}")
    raise TimeoutError(f"cognify did not finish within {timeout_seconds}s")