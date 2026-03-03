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
