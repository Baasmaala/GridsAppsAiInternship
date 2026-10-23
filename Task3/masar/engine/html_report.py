from html import escape

LABELS = {
    "draft_saved": ("Saved", "#5E7D3A"),
    "review_pending": ("Waiting", "#D9A23B"),
    "skipped_duplicate": ("Skipped", "#8A8F98"),
    "dry_run_preview": ("Preview", "#C4572A"),
    "failed_validation": ("Failed", "#A23B32"),
    "failed_error": ("Error", "#A23B32"),
}

CSS = """
body { background: #F5F2EA; color: #1E2328; margin: 0; padding: 24px 16px;
  font: 15px/1.5 "IBM Plex Sans", "IBM Plex Sans Arabic", system-ui, sans-serif; }
main { max-width: 960px; margin: 0 auto; }
h1 { font: 600 24px/1.2 "Bricolage Grotesque", system-ui, sans-serif; margin: 0 0 4px; }
.muted { color: #6B6A64; }
.mono { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 13px; }
.card { background: #FFFFFF; border: 1px solid #E4DED2; border-radius: 6px;
  padding: 16px; margin-top: 16px; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: start; padding: 8px; border-bottom: 1px solid #E4DED2; vertical-align: top; }
th { font-weight: 600; color: #6B6A64; font-size: 13px; }
.status { font-weight: 600; white-space: nowrap; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-inline-end: 6px; }
"""


def _status(status):
    label, color = LABELS.get(status, (status, "#6B6A64"))
    return (f'<span class="status"><span class="dot" style="background:{color}"></span>'
            f"{escape(label)}</span> <span class=\"muted mono\">{escape(status)}</span>")


def render_html(report):
    summary = "".join(f"<li>{_status(s)}: {n}</li>" for s, n in report["summary"].items())
    rows = []
    for item in report["items"]:
        rows.append(
            "<tr>"
            f'<td class="mono">{escape(str(item["source_id"]))}</td>'
            f"<td>{_status(item['status'])}</td>"
            f"<td>{item.get('word_count', '')}</td>"
            f'<td class="mono">{escape(" > ".join(item["steps"]))}</td>'
            f"<td dir=\"auto\">{escape(item.get('error', ''))}</td>"
            "</tr>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Masar run report</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Masar run report</h1>
<p class="muted">Drafts only. Nothing here is published.</p>
<div class="card">
<p class="mono">workflow {escape(report["workflow_id"])} {escape(report.get("workflow_version", ""))}<br>
run {escape(report["run_id"])}<br>
time {escape(report["generated_at"])}<br>
mode {escape(report["mode"])}</p>
<ul>{summary}</ul>
</div>
<div class="card">
<table>
<thead><tr><th>Lesson</th><th>Status</th><th>Words</th><th>Steps</th><th>Error</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
</div>
</main>
</body>
</html>
"""
