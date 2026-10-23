from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


# extra="forbid": an unknown field like "publish": true is an error, not ignored.
# strict types: "dry_run": "no" is an error, it is not turned into false.
class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow: StrictStr
    sample: StrictStr
    dry_run: StrictBool = False
    approved_by: StrictStr | None = None


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: StrictStr
    decision: Literal["approve", "reject"]
    reason: StrictStr = ""


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: Literal["reset"]
    seed: StrictBool = False


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: StrictStr = Field(min_length=1, max_length=500)
    lang: Literal["en", "ar"] = "en"
    run_id: StrictStr | None = None
    source_id: StrictStr | None = None
    index: StrictInt | None = None
    # the last dry run is never saved, so the web app sends the lesson it shows. only data.
    item: dict | None = None
    workflow: StrictStr | None = None
