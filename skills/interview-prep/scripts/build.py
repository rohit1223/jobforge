#!/usr/bin/env python3
"""Build the interview-prep dashboard.

Reads <datadir>/topics/*.md and <datadir>/notes/*.md (each with simple `---`
frontmatter) and renders ONE self-contained <datadir>/index.html: inline CSS +
vanilla JS sidebar nav, left = Topics (gap-weighted) + Notes, right = rendered
markdown. Markdown is rendered with pandoc; if pandoc is absent it falls back to
escaped <pre> so the build never hard-fails.

Usage: python3 build.py [datadir]   (datadir defaults to "interview-prep")
"""
import glob
import html
import os
import re
import subprocess
import sys


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "topic"

DATADIR = sys.argv[1] if len(sys.argv) > 1 else "interview-prep"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GUIDE_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "USAGE.md")  # skills/interview-prep/USAGE.md


def parse_frontmatter(text):
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip("\n").splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip("\"'")
            body = text[end + 4:].lstrip("\n")
    return meta, body


def md_to_html(body):
    try:
        p = subprocess.run(
            ["pandoc", "--from=gfm", "--to=html", "--wrap=none"],
            input=body, capture_output=True, text=True, check=True,
        )
        return p.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "<pre>" + html.escape(body) + "</pre>"


def truthy(v):
    return str(v).lower() in ("1", "true", "yes", "y")


def collect(sub):
    items = []
    for path in glob.glob(os.path.join(DATADIR, sub, "*.md")):
        with open(path, encoding="utf-8") as f:
            meta, body = parse_frontmatter(f.read())
        slug = os.path.splitext(os.path.basename(path))[0]
        meta.setdefault("title", slug.replace("-", " ").title())
        items.append({"slug": slug, "meta": meta, "html": md_to_html(body)})
    return items


def topic_key(it):
    m = it["meta"]
    try:
        rank = int(m.get("rank", "9999"))
    except ValueError:
        rank = 9999
    return (
        0 if truthy(m.get("must")) else 1,
        0 if truthy(m.get("gap")) else 1,
        rank,
        it["meta"]["title"].lower(),
    )


def badge(it):
    m = it["meta"]
    out = ""
    if truthy(m.get("must")):
        out += '<span class="badge must">must</span>'
    if truthy(m.get("learning")):
        out += '<span class="badge learning">learning</span>'
    d = (m.get("depth") or "").strip().lower()
    if d in ("quick", "standard", "deep"):
        out += f'<span class="badge depth {d}">{d}</span>'
    return out


CSS = """
:root{--bg:#0f1419;--panel:#171c24;--line:#2a313c;--fg:#e6e9ee;--muted:#8b95a3;--accent:#4da3ff;--gap:#ff7a59;--must:#3ddc97}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{display:flex;font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--fg)}
#sidebar{width:280px;flex:none;height:100vh;overflow-y:auto;background:var(--panel);border-right:1px solid var(--line);padding:18px 0}
#sidebar h1{font-size:15px;margin:0 18px 4px;letter-spacing:.3px}
#sidebar .sub{color:var(--muted);font-size:12px;margin:0 18px 16px}
.group{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin:18px 18px 6px}
nav a{display:flex;align-items:center;gap:6px;padding:7px 18px;color:var(--fg);text-decoration:none;border-left:3px solid transparent;cursor:pointer;font-size:14px}
nav a:hover{background:rgba(255,255,255,.04)}
nav a.active{border-left-color:var(--accent);background:rgba(77,163,255,.10);color:#fff}
.badge{font-size:9px;font-weight:700;text-transform:uppercase;padding:1px 5px;border-radius:6px;letter-spacing:.04em}
.badge.must{background:rgba(61,220,151,.16);color:var(--must)}
.badge.gap{background:rgba(255,122,89,.16);color:var(--gap)}
.badge.learning{background:rgba(255,184,77,.16);color:#ffb84d}
.badge.depth{background:rgba(139,149,163,.14);color:var(--muted)}
.badge.depth.deep{background:rgba(199,146,234,.16);color:#c792ea}
.badge.depth.quick{background:rgba(127,209,255,.14);color:#7fd1ff}
nav.suggested{counter-reset:sg}
nav.suggested a{align-items:center}
nav.suggested a::before{counter-increment:sg;content:counter(sg);flex:none;display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border:1px solid var(--line);border-radius:50%;font-size:10px;color:var(--muted)}
.prompt{display:flex;align-items:center;gap:8px;background:#0d1117;border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:6px 0 16px}
.prompt code{flex:1;background:none;color:#7fd1ff;font-size:13px;padding:0;word-break:break-all}
.prompt button.copy{flex:none;cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;padding:5px 11px;font-size:12px}
.prompt button.copy:hover{background:rgba(77,163,255,.12);border-color:var(--accent)}
#search{width:calc(100% - 36px);margin:0 18px 8px;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:#0d1117;color:var(--fg)}
main{flex:1;height:100vh;overflow-y:auto;padding:40px 56px;max-width:900px}
.pane{display:none}.pane.active{display:block;animation:f .15s ease}
@keyframes f{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
main h2{border-bottom:1px solid var(--line);padding-bottom:8px;margin-top:30px}
main h1{margin-top:0}
a{color:var(--accent)}
code{background:#0d1117;padding:2px 6px;border-radius:5px;font-size:13px}
pre{background:#0d1117;border:1px solid var(--line);border-radius:10px;padding:14px;overflow-x:auto}
pre code{padding:0;background:none}
blockquote{border-left:3px solid var(--accent);margin:0;padding:2px 16px;color:var(--muted)}
details{border:1px solid var(--line);border-radius:10px;margin:10px 0;background:rgba(255,255,255,.02)}
details>summary{cursor:pointer;padding:11px 16px;font-weight:600;color:#fff;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"\\25B8  ";color:var(--accent);font-weight:700}
details[open]>summary::before{content:"\\25BE  "}
details[open]>summary{border-bottom:1px solid var(--line)}
details>summary:hover{background:rgba(77,163,255,.06)}
details>*:not(summary){padding-left:16px;padding-right:16px}
details>*:last-child{padding-bottom:12px}
.qcount{color:var(--muted);font-size:12px;margin:-6px 0 14px}
.empty{color:var(--muted);margin-top:40px}
"""

JS = """
const links=[...document.querySelectorAll('nav a')];
const panes=[...document.querySelectorAll('.pane')];
function show(id){
  panes.forEach(p=>p.classList.toggle('active',p.id===id));
  links.forEach(a=>a.classList.toggle('active',a.dataset.target===id));
  if(location.hash!=='#'+id) history.replaceState(null,'','#'+id);
}
links.forEach(a=>a.addEventListener('click',e=>{e.preventDefault();show(a.dataset.target)}));
const search=document.getElementById('search');
if(search)search.addEventListener('input',()=>{const q=search.value.toLowerCase();
  links.forEach(a=>a.style.display=a.textContent.toLowerCase().includes(q)?'':'none')});
const first=(location.hash&&document.getElementById(location.hash.slice(1)))?location.hash.slice(1):(panes[0]&&panes[0].id);
if(first)show(first);
function copyEl(id,btn){var el=document.getElementById(id);if(!el)return;var text=el.textContent;
  var done=function(){var o=btn.textContent;btn.textContent='✓ Copied';setTimeout(function(){btn.textContent=o},1200)};
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done,function(){fbCopy(text,done)})}else{fbCopy(text,done)}}
function fbCopy(text,done){var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.focus();ta.select();try{document.execCommand('copy')}catch(e){}document.body.removeChild(ta);done()}
"""


def read_suggested():
    """Parse <datadir>/suggested.md lines like '- Title — why' into (title, why)."""
    path = os.path.join(DATADIR, "suggested.md")
    items = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("- "):
                    rest = line[2:].strip().lstrip("*").rstrip("*").strip()
                    for sep in (" — ", " -- ", " - ", ": "):
                        if sep in rest:
                            title, why = rest.split(sep, 1)
                            break
                    else:
                        title, why = rest, ""
                    items.append((title.strip().strip("*"), why.strip()))
    return items


def build():
    topics = sorted(collect("topics"), key=topic_key)
    notes = sorted(collect("notes"), key=lambda it: it["meta"]["title"].lower())
    suggested = read_suggested()

    nav, panes = [], []

    # Pinned guide pane (rendered from skills/interview-prep/USAGE.md), shown first.
    if os.path.isfile(GUIDE_PATH):
        with open(GUIDE_PATH, encoding="utf-8") as f:
            _, guide_body = parse_frontmatter(f.read())
        nav.append('<nav><a data-target="guide">ℹ️  How to use</a></nav>')
        panes.append(f'<section class="pane" id="guide">{md_to_html(guide_body)}</section>')

    def emit(group, items):
        nonlocal nav, panes
        if not items:
            return
        nav.append(f'<div class="group">{html.escape(group)}</div><nav>')
        for it in items:
            pid = f"{group.lower()}-{it['slug']}"
            nav.append(
                f'<a data-target="{html.escape(pid)}">{html.escape(it["meta"]["title"])}{badge(it)}</a>'
            )
            src = it["meta"].get("source") or it["meta"].get("sources")
            cite = (f'<p class="sub">source: <a href="{html.escape(src)}" target="_blank" rel="noopener">{html.escape(src)}</a></p>'
                    if src else "")
            panes.append(
                f'<section class="pane" id="{html.escape(pid)}">'
                f'<h1>{html.escape(it["meta"]["title"])}</h1>{cite}{it["html"]}</section>'
            )
        nav.append("</nav>")

    emit("Topics", topics)
    emit("Notes", notes)

    # Suggested-but-not-generated group: ordered, clickable; each opens a pane
    # with the exact copy-able prompt. Auto-dropped once that topic is generated.
    existing = {it["slug"] for it in topics} | {slugify(it["meta"]["title"]) for it in topics}
    pending = [(t, w) for (t, w) in suggested if slugify(t) not in existing]
    if pending:
        nav.append('<div class="group">Suggested · not generated</div><nav class="suggested">')
        for title, why in pending:
            slug = slugify(title)
            pid = f"suggest-{slug}"
            nav.append(f'<a data-target="{pid}">{html.escape(title)}</a>')
            why_html = f'<p class="sub">{html.escape(why)}</p>' if why else ""
            cmd = f'add-topic "{title}"'
            cmd_deep = f'add-topic "{title}" --depth=deep'
            panes.append(
                f'<section class="pane" id="{pid}">'
                f'<h1>{html.escape(title)} <span class="badge depth">suggested</span></h1>'
                f'{why_html}'
                f'<p>Not generated yet. Run this prompt to add it at standard depth:</p>'
                f'<div class="prompt"><code id="cmd-{slug}">{html.escape(cmd)}</code>'
                f'<button class="copy" onclick="copyEl(\'cmd-{slug}\',this)">Copy</button></div>'
                f'<p>Or go deeper:</p>'
                f'<div class="prompt"><code id="cmdd-{slug}">{html.escape(cmd_deep)}</code>'
                f'<button class="copy" onclick="copyEl(\'cmdd-{slug}\',this)">Copy</button></div>'
                f'</section>'
            )
        nav.append("</nav>")

    body_panes = "".join(panes) or '<p class="empty">No content yet. Run the interview-prep skill to populate topics, or add a note.</p>'
    total = len(topics) + len(notes)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interview Prep Dashboard</title>
<style>{CSS}</style></head>
<body>
<aside id="sidebar">
<h1>Interview Prep</h1>
<p class="sub">{total} section{"s" if total != 1 else ""}</p>
<input id="search" placeholder="Filter…" autocomplete="off">
{"".join(nav)}
</aside>
<main>{body_panes}</main>
<script>{JS}</script>
</body></html>"""

    out = os.path.join(DATADIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"✓ built {out}  ({len(topics)} topics, {len(notes)} notes)")


if __name__ == "__main__":
    build()
