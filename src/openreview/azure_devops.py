from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class AzureDevOpsClient:
    organization: str
    project: str
    repository_id: str
    pat: str

    @property
    def base_url(self) -> str:
        return f"https://dev.azure.com/{self.organization}/{self.project}/_apis/git/repositories/{self.repository_id}"

    def _client(self) -> httpx.Client:
        return httpx.Client(auth=("", self.pat), timeout=30.0)

    def get_pull_request_threads(self, pr_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/pullRequests/{pr_id}/threads?api-version=7.1-preview.1"
        with self._client() as client:
            res = client.get(url)
            res.raise_for_status()
            payload = res.json()
        return payload.get("value", [])

    def get_pull_request_iterations(self, pr_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/pullRequests/{pr_id}/iterations?api-version=7.1-preview.1"
        with self._client() as client:
            res = client.get(url)
            res.raise_for_status()
            payload = res.json()
        return payload.get("value", [])

    def get_iteration_changes(self, pr_id: int, iteration_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/pullRequests/{pr_id}/iterations/{iteration_id}/changes?api-version=7.1-preview.1"
        with self._client() as client:
            res = client.get(url)
            res.raise_for_status()
            payload = res.json()
        return payload.get("changeEntries", [])

    def get_changed_files_latest_iteration(self, pr_id: int) -> list[str]:
        iterations = self.get_pull_request_iterations(pr_id)
        if not iterations:
            return []
        latest = max(iterations, key=lambda x: int(x.get("id", 0)))
        changes = self.get_iteration_changes(pr_id, int(latest["id"]))

        paths: list[str] = []
        for c in changes:
            item = c.get("item") or {}
            path = item.get("path")
            if isinstance(path, str) and path:
                if path not in paths:
                    paths.append(path)
        return paths

    def create_thread(self, pr_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/pullRequests/{pr_id}/threads?api-version=7.1-preview.1"
        with self._client() as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            return res.json()

    def update_thread(self, pr_id: int, thread_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/pullRequests/{pr_id}/threads/{thread_id}?api-version=7.1-preview.1"
        with self._client() as client:
            res = client.patch(url, json=payload)
            res.raise_for_status()
            return res.json()

    def create_comment(self, pr_id: int, thread_id: int, content: str) -> dict[str, Any]:
        url = f"{self.base_url}/pullRequests/{pr_id}/threads/{thread_id}/comments?api-version=7.1-preview.1"
        payload = {"content": content, "commentType": 1, "parentCommentId": 0}
        with self._client() as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            return res.json()
