from . import registry
from .nodes.lesson_nodes import is_text

TOP_KEYS = {"id", "version", "trigger", "allowed_languages", "nodes", "edges"}
NODE_KEYS = {"id", "type"}
TRIGGER_KEYS = {"type"}
TRIGGERS = {"manual"}
# keys that try to run code. any unknown key is refused, these get a clearer message
CODE_KEYS = {"code", "script", "exec", "eval", "command", "cmd", "shell", "function",
             "python", "javascript", "js", "module", "import", "run"}

VALIDATORS = ("validate_lesson", "validate_question")
# node type -> (one of these must come before it, message)
NEEDS_BEFORE = {
    "normalize_lesson": [(("validate_lesson",), "normalize_lesson needs a validate_lesson node before it")],
    "normalize_question": [(("validate_question",),
                            "normalize_question needs a validate_question node before it")],
    "check_duplicate": [(VALIDATORS, "check_duplicate needs a validate node before it")],
    "save_draft": [
        (VALIDATORS, "save_draft needs a validate node before it (nothing unchecked is saved)"),
        (("check_duplicate",), "save_draft needs a check_duplicate node before it"),
        (("manual_approval",), "save_draft needs a manual_approval node before it "
                               "(no human approval, no save)"),
    ],
}


def lint(wf):
    if not isinstance(wf, dict):
        return ["workflow must be a JSON object"]
    errors = _key_errors(wf, TOP_KEYS, "workflow")
    if not is_text(wf.get("id")):
        errors.append("workflow: 'id' must be a non-empty string")
    if "version" in wf and not isinstance(wf["version"], str):
        errors.append("workflow: 'version' must be a string")
    errors += _trigger_errors(wf.get("trigger", {"type": "manual"}))
    langs = wf.get("allowed_languages", ["en"])
    if not (isinstance(langs, list) and langs and all(is_text(x) for x in langs)):
        errors.append('allowed_languages must be a non-empty list of language codes, like ["en"]')

    nodes = wf.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("workflow: 'nodes' must be a non-empty list")
        return errors
    node_errors, ids = _node_errors(nodes)
    errors += node_errors
    if node_errors:
        return errors
    errors += _edge_errors(wf.get("edges"), ids)
    if not errors:
        errors += _order_errors([n["type"] for n in ordered_nodes(wf)])
    return errors


def ordered_nodes(wf):
    # only call this after lint() found no errors
    by_id = {n["id"]: n for n in wf["nodes"]}
    nxt = {a: b for a, b in wf.get("edges", [])}
    targets = set(nxt.values())
    node_id = next(i for i in by_id if i not in targets)
    order = []
    while node_id is not None:
        order.append(by_id[node_id])
        node_id = nxt.get(node_id)
    return order


def _key_errors(obj, allowed, where):
    errors = []
    for key in obj:
        if key.lower() in CODE_KEYS:
            errors.append(f"{where}: key '{key}' is not allowed. "
                          "workflow.json is a description, not code")
        elif key not in allowed:
            errors.append(f"{where}: unknown key '{key}'")
    return errors


def _trigger_errors(trigger):
    if not isinstance(trigger, dict):
        return ["trigger must be an object"]
    errors = _key_errors(trigger, TRIGGER_KEYS, "trigger")
    if trigger.get("type") not in TRIGGERS:
        errors.append(f"trigger: type must be 'manual' (got {trigger.get('type')!r})")
    return errors


def _node_errors(nodes):
    errors, ids = [], []
    allowed = ", ".join(registry.NODES)
    for i, node in enumerate(nodes, 1):
        where = f"node {i}"
        if not isinstance(node, dict):
            errors.append(f"{where}: must be an object")
            continue
        if is_text(node.get("id")):
            where = f"node '{node['id']}'"
        errors += _key_errors(node, NODE_KEYS, where)
        node_id = node.get("id")
        if not is_text(node_id):
            errors.append(f"{where}: 'id' must be a non-empty string")
        elif node_id in ids:
            errors.append(f"{where}: duplicate node id")
        else:
            ids.append(node_id)
        node_type = node.get("type")
        if not isinstance(node_type, str) or node_type not in registry.NODES:
            errors.append(f"{where}: unknown node type {node_type!r}. allowed: {allowed}")
    return errors, ids


def _edge_errors(edges, ids):
    if not isinstance(edges, list):
        return ["workflow: 'edges' must be a list of [from, to] pairs"]
    errors, pairs = [], []
    for i, edge in enumerate(edges, 1):
        if not (isinstance(edge, list) and len(edge) == 2 and all(isinstance(x, str) for x in edge)):
            errors.append(f"edge {i}: must be a [from, to] pair of node ids")
            continue
        for end in edge:
            if end not in ids:
                errors.append(f"edge {i} ({edge[0]} -> {edge[1]}): points to a missing node '{end}'")
        pairs.append(edge)
    if errors:
        return errors
    return _shape_errors(pairs, ids)


def _shape_errors(pairs, ids):
    errors, nxt, prev = [], {}, {}
    for a, b in pairs:
        if a == b:
            errors.append(f"cycle found: {a} -> {a}")
            continue
        if a in nxt:
            errors.append(f"node '{a}' has more than one next node. only a straight line is supported")
        if b in prev:
            errors.append(f"node '{b}' has more than one node before it. "
                          "only a straight line is supported")
        nxt.setdefault(a, b)
        prev.setdefault(b, a)
    if errors:
        return errors
    cycle = _find_cycle(nxt)
    if cycle:
        return ["cycle found: " + " -> ".join(cycle)]
    starts = [i for i in ids if i not in prev]
    if len(starts) != 1:
        # no cycle and max one in/out each, so more starts = separate pieces
        return [f"workflow must be one straight line, but it has {len(starts)} separate parts "
                f"starting at: {', '.join(starts)}"]
    return []


def _find_cycle(nxt):
    for start in nxt:
        path = []
        node = start
        while node is not None and node not in path:
            path.append(node)
            node = nxt.get(node)
        if node is not None:
            return path[path.index(node):] + [node]
    return None


def _order_errors(types):
    errors = []
    for i, node_type in enumerate(types):
        for any_of, msg in NEEDS_BEFORE.get(node_type, []):
            if not any(t in types[:i] for t in any_of) and msg not in errors:
                errors.append(msg)
    return errors
