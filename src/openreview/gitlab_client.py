from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class GitLabClient:
    project_id: str
    token: str
    base_url: str = "https://gitlab.com/api/v4"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers={"PRIVATE-TOKEN": self.token},
            timeout=30.0,
        )

    def _project_path(self) -> str:
        return f"{self.base_url}/projects/{self.project_id}"

    def get_mr_notes(self, mr_iid: int) -> list[dict[str, Any]]:
        url = f"{self._project_path()}/merge_requests/{mr_iid}/notes"
        with self._client() as c:
            r = c.get(url)
            r.raise_for_status()
            return r.json()

    def create_mr_note(self, mr_iid: int, body: str) -> dict[str, Any]:
        url = f"{self._project_path()}/merge_requests/{mr_iid}/notes"
        with self._client() as c:
            r = c.post(url, data={"body": body})
            r.raise_for_status()
            return r.json()

    def update_mr_note(self, mr_iid: int, note_id: int, body: str) -> dict[str, Any]:
        url = f"{self._project_path()}/merge_requests/{mr_iid}/notes/{note_id}"
        with self._client() as c:
            r = c.put(url, data={"body": body})
            r.raise_for_status()
            return r.json()
