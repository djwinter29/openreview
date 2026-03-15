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
        url = f"{self.base_url}/issues/{pr_number}/comments"
        with self._client() as client:
            res = client.get(url)
            res.raise_for_status()
            return res.json()

    def create_issue_comment(self, pr_number: int, body: str) -> dict[str, Any]:
        url = f"{self.base_url}/issues/{pr_number}/comments"
        with self._client() as client:
            res = client.post(url, json={"body": body})
            res.raise_for_status()
            return res.json()

    def update_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}"
        with self._client() as client:
            res = client.patch(url, json={"body": body})
            res.raise_for_status()
            return res.json()

    def get_pull_request(self, pr_number: int) -> dict[str, Any]:
        url = f"{self.base_url}/pulls/{pr_number}"
        with self._client() as client:
            res = client.get(url)
            res.raise_for_status()
            return res.json()

    def get_review_comments(self, pr_number: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/pulls/{pr_number}/comments"
        with self._client() as client:
            res = client.get(url)
            res.raise_for_status()
            return res.json()

    def create_review_comment(
        self,
        *,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int,
        side: str = "RIGHT",
    ) -> dict[str, Any]:
        url = f"{self.base_url}/pulls/{pr_number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "line": line,
            "side": side,
        }
        with self._client() as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            return res.json()

    def update_review_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        url = f"{self.base_url}/pulls/comments/{comment_id}"
        with self._client() as client:
            res = client.patch(url, json={"body": body})
            res.raise_for_status()
            return res.json()
