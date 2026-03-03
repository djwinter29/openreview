from pydantic import BaseModel, Field


class OpenReviewConfig(BaseModel):
    azure_org: str = Field(default="")
    azure_project: str = Field(default="")
    azure_repo_id: str = Field(default="")
    azure_pat: str = Field(default="")
    model_provider: str = Field(default="openai")
    model_name: str = Field(default="gpt-5.3-codex")
