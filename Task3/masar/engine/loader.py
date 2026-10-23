import json
from dataclasses import dataclass
from pathlib import Path

from .errors import WorkflowError
from .lint import lint, ordered_nodes


@dataclass
class Workflow:
    id: str
    version: str
    allowed_languages: list[str]
    nodes: list[dict]  # in run order, from the edges
    raw: dict


def parse_workflow(raw):
    errors = lint(raw)
    if errors:
        raise WorkflowError(errors)
    langs = [x.strip().lower() for x in raw.get("allowed_languages", ["en"])]
    return Workflow(id=raw["id"], version=raw.get("version", ""), allowed_languages=langs,
                    nodes=ordered_nodes(raw), raw=raw)


def read_json(path):
    # utf-8-sig: powershell often saves files with a BOM
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_workflow(path):
    try:
        raw = read_json(path)
    except FileNotFoundError:
        raise WorkflowError([f"workflow file not found: {path}"]) from None
    except json.JSONDecodeError as ex:
        raise WorkflowError([f"workflow file is not valid JSON: {ex}"]) from None
    return parse_workflow(raw)


def to_mermaid(wf):
    # short ids so odd characters in node ids cannot break the diagram
    lines = ["flowchart LR", '  trigger(["manual trigger"])']
    prev = "trigger"
    for i, node in enumerate(wf.nodes, 1):
        label = f"{node['id']}<br/>{node['type']}".replace('"', "#quot;")
        lines.append(f'  n{i}["{label}"]')
        lines.append(f"  {prev} --> n{i}")
        prev = f"n{i}"
    return "\n".join(lines)
