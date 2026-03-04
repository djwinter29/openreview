from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class GitHubClient:
    owner: str
    repo: str
    token: str

    @property
    def base_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def get_issue_comments(self, pr_number: int) -> list[dict[str, Any]]:
        # PR comments are issue comments + review comments; MVP starts with issue comments
        url = f"{self.base_url}/issues/{pr_number}/comments"
        with self._client() as c:
            r = c.get(url)
            r.raise_for_status()
            return r.json()

    def create_issue_comment(self, pr_number: int, body: str) -> dict[str, Any]:
        url = f"{self.base_url}/issues/{pr_number}/comments"
        with self._client() as c:
            r = c.post(url, json={"body": body})
            r.raise_for_status()
            return r.json()

    def update_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}"
        with self._client() as c:
            r = c.patch(url, json={"body": body})
            r.raise_for_status()
            return r.json()
