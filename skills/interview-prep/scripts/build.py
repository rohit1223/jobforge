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
        0 if truthy(m.get("learning")) else 1,
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
.badge.learning{background:rgba(255,184,77,.16);color:#ffb84d}
.badge.depth{background:rgba(139,149,163,.14);color:var(--muted)}
.badge.depth.deep{background:rgba(199,146,234,.16);color:#c792ea}
.badge.depth.quick{background:rgba(127,209,255,.14);color:#7fd1ff}
details.navgroup{border:none;background:none;border-radius:0;margin:0}
details.navgroup>summary{padding:14px 18px 6px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:600;border-bottom:none}
details.navgroup>summary:hover{background:rgba(255,255,255,.03)}
details.navgroup>summary::before{content:"\\25B8  ";color:var(--muted);font-weight:700}
details.navgroup[open]>summary::before{content:"\\25BE  "}
details.navgroup>*:not(summary){padding-left:0;padding-right:0;padding-bottom:0}
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
table{border-collapse:collapse;margin:14px 0;width:100%;font-size:14px}
th,td{border:1px solid var(--line);padding:7px 12px;text-align:left;vertical-align:top}
th{background:rgba(255,255,255,.05);color:#fff;font-weight:600}
tbody tr:nth-child(even) td{background:rgba(255,255,255,.02)}
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
.gradebar{display:flex;gap:8px;align-items:center;border-top:1px dashed var(--line);margin-top:10px;padding:10px 16px 12px;color:var(--muted);font-size:12px}
.gradebar button{cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;padding:4px 10px;font-size:12px}
.gradebar button:hover{border-color:var(--accent)}
.gradebar button.on[data-g=good]{background:rgba(61,220,151,.18);border-color:var(--must);color:var(--must)}
.gradebar button.on[data-g=shaky]{background:rgba(255,184,77,.18);border-color:#ffb84d;color:#ffb84d}
.gradebar button.on[data-g=missed]{background:rgba(255,122,89,.18);border-color:var(--gap);color:var(--gap)}
details.g-good>summary{box-shadow:inset 3px 0 0 var(--must)}
details.g-shaky>summary{box-shadow:inset 3px 0 0 #ffb84d}
details.g-missed>summary{box-shadow:inset 3px 0 0 var(--gap)}
nav a .prog{margin-left:auto;font-size:10px;color:var(--muted)}
nav a .prog.done{color:var(--must)}
.quizrow{display:flex;gap:8px;margin:0 18px 8px}
.quizrow button{flex:1;cursor:pointer;border:1px solid var(--line);background:#0d1117;color:var(--fg);border-radius:8px;padding:7px 0;font-size:12px}
.quizrow button:hover{border-color:var(--accent)}
.quizq{font-size:17px;font-weight:600;margin:18px 0;color:#fff;line-height:1.5}
.quizctl{display:flex;gap:10px;margin-top:22px;flex-wrap:wrap}
.quizctl button{cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:8px;padding:8px 16px;font-size:13px}
.quizctl button:hover{border-color:var(--accent)}
.panectl{display:flex;gap:8px;align-items:center;margin:0 0 14px}
.panectl button{cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--muted);border-radius:6px;padding:4px 10px;font-size:12px}
.panectl button:hover{border-color:var(--accent);color:var(--fg)}
.panectl .kbd{color:var(--muted);font-size:11px;margin-left:auto}
#menu{display:none}
@media(max-width:768px){
  #menu{display:block;position:fixed;top:10px;left:10px;z-index:30;cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:8px;padding:6px 12px;font-size:16px}
  #sidebar{position:fixed;left:0;top:0;z-index:20;transform:translateX(-100%);transition:transform .2s ease;box-shadow:4px 0 24px rgba(0,0,0,.5)}
  body.nav-open #sidebar{transform:none}
  main{padding:60px 20px 40px;max-width:none}
  .panectl .kbd{display:none}
}
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
const paneText={};panes.forEach(p=>paneText[p.id]=p.textContent.toLowerCase());
if(search)search.addEventListener('input',()=>{
  const q=search.value.trim().toLowerCase();
  links.forEach(a=>{
    const hit=!q||a.textContent.toLowerCase().includes(q)||(paneText[a.dataset.target]||'').includes(q);
    a.style.display=hit?'':'none';
  });
  if(q)document.querySelectorAll('details.navgroup').forEach(d=>{d.open=true});
});
const first=(location.hash&&document.getElementById(location.hash.slice(1)))?location.hash.slice(1):(panes[0]&&panes[0].id);
if(first)show(first);
function copyEl(id,btn){var el=document.getElementById(id);if(!el)return;var text=el.textContent;
  var done=function(){var o=btn.textContent;btn.textContent='✓ Copied';setTimeout(function(){btn.textContent=o},1200)};
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done,function(){fbCopy(text,done)})}else{fbCopy(text,done)}}
function fbCopy(text,done){var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.focus();ta.select();try{document.execCommand('copy')}catch(e){}document.body.removeChild(ta);done()}

/* --- self-quiz progress (persisted in localStorage) --- */
const PKEY='iprep.progress.v1';
let prog={};try{prog=JSON.parse(localStorage.getItem(PKEY)||'{}')}catch(e){}
function saveProg(){try{localStorage.setItem(PKEY,JSON.stringify(prog))}catch(e){}}
const GRADES={good:'\\u2713 Knew it',shaky:'~ Shaky',missed:'\\u2717 Missed'};
const quizIndex={};
function isQ(d){var s=d.querySelector(':scope > summary');return s&&/^Q\\b/.test(s.textContent.trim())}
panes.forEach(p=>{
  const qs=[...p.querySelectorAll('details')].filter(isQ);
  if(!qs.length)return;
  quizIndex[p.id]=qs.map((d,i)=>{
    const key=p.id+'#'+i;
    const bar=document.createElement('div');bar.className='gradebar';
    bar.innerHTML='<span>Self-grade:</span>'+Object.keys(GRADES).map(g=>'<button data-g="'+g+'">'+GRADES[g]+'</button>').join('');
    d.appendChild(bar);
    bar.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;setGrade(key,d,b.dataset.g)});
    applyGrade(key,d);
    return {el:d,key};
  });
});
function applyGrade(key,d){
  const g=prog[key];
  d.classList.remove('g-good','g-shaky','g-missed');
  if(g)d.classList.add('g-'+g);
  d.querySelectorAll('.gradebar button').forEach(b=>b.classList.toggle('on',b.dataset.g===g));
}
function setGrade(key,d,g){
  if(prog[key]===g){delete prog[key]}else{prog[key]=g}
  saveProg();applyGrade(key,d);updateProg();
}
function updateProg(){
  Object.keys(quizIndex).forEach(pid=>{
    const list=quizIndex[pid];
    const good=list.filter(q=>prog[q.key]==='good').length;
    const a=links.find(l=>l.dataset.target===pid);if(!a)return;
    let sp=a.querySelector('.prog');
    if(!sp){sp=document.createElement('span');sp.className='prog';a.appendChild(sp)}
    sp.textContent=good+'/'+list.length;
    sp.classList.toggle('done',good===list.length&&list.length>0);
  });
}
updateProg();

/* --- quiz mode: shuffled flashcard runs --- */
const qpane=document.getElementById('quizpane');
let deck=[],qpos=0,tally={};
function titleOf(pid){const a=links.find(l=>l.dataset.target===pid);return a?a.childNodes[0].textContent.trim():pid}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function startQuiz(weak){
  deck=[];Object.keys(quizIndex).forEach(pid=>quizIndex[pid].forEach(q=>deck.push({pid,key:q.key,el:q.el})));
  if(weak)deck=deck.filter(c=>prog[c.key]==='shaky'||prog[c.key]==='missed');
  if(!deck.length){alert(weak?'Nothing graded shaky/missed yet \\u2014 grade some questions first.':'No questions found.');return}
  shuffle(deck);if(!weak&&deck.length>20)deck=deck.slice(0,20);
  qpos=0;tally={good:0,shaky:0,missed:0};quizCard();show('quizpane');
}
function quizCard(){
  if(qpos>=deck.length)return quizDone();
  const c=deck[qpos],d=c.el;
  const sum=d.querySelector(':scope > summary');
  const ans=[...d.children].filter(x=>x.tagName!=='SUMMARY'&&!x.classList.contains('gradebar')).map(x=>x.outerHTML).join('');
  qpane.innerHTML='<p class="sub">Question '+(qpos+1)+' / '+deck.length+' \\u00b7 '+titleOf(c.pid)+'</p>'
    +'<div class="quizq">'+sum.innerHTML+'</div>'
    +'<div id="quizans" style="display:none">'+ans+'</div>'
    +'<div class="quizctl"><button id="qreveal">Reveal answer</button>'
    +Object.keys(GRADES).map(g=>'<button class="qgrade" data-g="'+g+'" style="display:none">'+GRADES[g]+'</button>').join('')
    +'<button id="qskip">Skip</button><button id="qend">End quiz</button></div>';
  document.getElementById('qreveal').onclick=()=>{
    document.getElementById('quizans').style.display='';
    document.getElementById('qreveal').style.display='none';
    qpane.querySelectorAll('.qgrade').forEach(b=>b.style.display='');
  };
  qpane.querySelectorAll('.qgrade').forEach(b=>b.onclick=()=>{
    prog[c.key]=b.dataset.g;saveProg();applyGrade(c.key,d);updateProg();
    tally[b.dataset.g]++;qpos++;quizCard();
  });
  document.getElementById('qskip').onclick=()=>{qpos++;quizCard()};
  document.getElementById('qend').onclick=quizDone;
}
function quizDone(){
  qpane.innerHTML='<h1>Quiz finished</h1><p>'+tally.good+' knew \\u00b7 '+tally.shaky+' shaky \\u00b7 '+tally.missed+' missed (deck of '+deck.length+')</p>'
    +'<div class="quizctl"><button id="qagain">New quiz</button><button id="qweak2">Weak only</button></div>';
  document.getElementById('qagain').onclick=()=>startQuiz(false);
  document.getElementById('qweak2').onclick=()=>startQuiz(true);
}
const qa=document.getElementById('quiz-all'),qw=document.getElementById('quiz-weak');
if(qa)qa.onclick=()=>startQuiz(false);
if(qw)qw.onclick=()=>startQuiz(true);

/* --- expand/collapse all per pane --- */
panes.forEach(p=>{
  if(p.id==='quizpane')return;
  const ds=[...p.querySelectorAll('details')];
  if(!ds.length)return;
  const row=document.createElement('div');row.className='panectl';
  row.innerHTML='<button data-x="1">Expand all</button><button data-x="0">Collapse all</button><span class="kbd">j/k topics \\u00b7 / search</span>';
  const h1=p.querySelector('h1');
  p.insertBefore(row,h1?h1.nextSibling:p.firstChild);
  row.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;ds.forEach(d=>d.open=b.dataset.x==='1')});
});

/* --- mobile drawer --- */
const menu=document.getElementById('menu');
if(menu)menu.addEventListener('click',()=>document.body.classList.toggle('nav-open'));
links.forEach(a=>a.addEventListener('click',()=>document.body.classList.remove('nav-open')));

/* --- keyboard navigation --- */
document.addEventListener('keydown',e=>{
  if(e.target.matches('input,textarea')){if(e.key==='Escape')e.target.blur();return}
  if(e.metaKey||e.ctrlKey||e.altKey)return;
  if(e.key==='/'){e.preventDefault();if(search){search.focus();search.select()}return}
  if(e.key==='j'||e.key==='k'){
    const vis=links.filter(a=>a.style.display!=='none'&&a.offsetParent!==null);
    if(!vis.length)return;
    const cur=vis.findIndex(a=>a.classList.contains('active'));
    let nxt=e.key==='j'?cur+1:cur-1;
    if(nxt<0)nxt=vis.length-1;if(nxt>=vis.length)nxt=0;
    show(vis[nxt].dataset.target);vis[nxt].scrollIntoView({block:'nearest'});
  }
});
"""


def read_suggested():
    """Parse <datadir>/suggested.md into (origin, title, why) tuples.

    `## Section` headers set the origin group (preserving file order, so résumé
    sections listed first stay first); `- Title — why` lines are the items.
    """
    path = os.path.join(DATADIR, "suggested.md")
    items = []
    origin = "Suggested"
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s.startswith("## "):
                    origin = s[3:].strip()
                    continue
                if s.startswith("- "):
                    rest = s[2:].strip().strip("*").strip()
                    for sep in (" — ", " -- ", " - ", ": "):
                        if sep in rest:
                            title, why = rest.split(sep, 1)
                            break
                    else:
                        title, why = rest, ""
                    items.append((origin, title.strip().strip("*"), why.strip()))
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
            cite = ""
            if src:
                urls = [u.strip() for u in src.split(",") if u.strip()]
                links_html = " · ".join(
                    f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(u)}</a>'
                    for u in urls
                )
                label = "sources" if len(urls) > 1 else "source"
                cite = f'<p class="sub">{label}: {links_html}</p>'
            nq = it["html"].count("<details>")
            qline = (f'<p class="qcount">{nq} self-quiz question{"s" if nq != 1 else ""}</p>'
                     if nq else "")
            panes.append(
                f'<section class="pane" id="{html.escape(pid)}">'
                f'<h1>{html.escape(it["meta"]["title"])}</h1>{cite}{qline}{it["html"]}</section>'
            )
        nav.append("</nav>")

    emit("Topics", topics)
    emit("Notes", notes)

    # Suggested-but-not-generated: collapsible groups by origin (résumé first,
    # then JD — file order preserved). Each item opens a pane with copy-able
    # prompts (standard / +detailed / deep+detailed). Auto-dropped once generated.
    existing = {it["slug"] for it in topics} | {slugify(it["meta"]["title"]) for it in topics}
    pending = [(o, t, w) for (o, t, w) in suggested if slugify(t) not in existing]

    def prompt_row(eid, cmd):
        return (f'<div class="prompt"><code id="{eid}">{html.escape(cmd)}</code>'
                f'<button class="copy" onclick="copyEl(\'{eid}\',this)">Copy</button></div>')

    if pending:
        nav.append('<div class="group">Suggested · not generated</div>')
        order, by_origin = [], {}
        for origin, title, why in pending:
            if origin not in by_origin:
                by_origin[origin] = []
                order.append(origin)
            by_origin[origin].append((title, why))
        for gi, origin in enumerate(order):
            items_ = by_origin[origin]
            open_attr = " open" if gi == 0 else ""
            nav.append(
                f'<details class="navgroup"{open_attr}>'
                f'<summary>{html.escape(origin)} ({len(items_)})</summary>'
                f'<nav class="suggested">'
            )
            for title, why in items_:
                slug = slugify(title)
                pid = f"suggest-{slug}"
                nav.append(f'<a data-target="{pid}">{html.escape(title)}</a>')
                why_html = f'<p class="sub">{html.escape(origin)} · {html.escape(why)}</p>' if why else ""
                panes.append(
                    f'<section class="pane" id="{pid}">'
                    f'<h1>{html.escape(title)} <span class="badge depth">suggested</span></h1>'
                    f'{why_html}'
                    f'<p>Not generated yet. Copy a prompt to add it:</p>'
                    f'<p class="sub">Standard depth</p>{prompt_row(f"c1-{slug}", f"""add-topic \"{title}\"""")}'
                    f'<p class="sub">More concepts (good for an unfamiliar topic)</p>{prompt_row(f"c2-{slug}", f"""add-topic \"{title}\" --detailed""")}'
                    f'<p class="sub">Deep + detailed</p>{prompt_row(f"c3-{slug}", f"""add-topic \"{title}\" --depth=deep --detailed""")}'
                    f'</section>'
                )
            nav.append("</nav></details>")

    body_panes = "".join(panes) or '<p class="empty">No content yet. Run the interview-prep skill to populate topics, or add a note.</p>'
    total = len(topics) + len(notes)
    total_q = sum(it["html"].count("<details>") for it in topics + notes)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interview Prep Dashboard</title>
<style>{CSS}</style></head>
<body>
<button id="menu" aria-label="Toggle navigation">☰</button>
<aside id="sidebar">
<h1>Interview Prep</h1>
<p class="sub">{total} section{"s" if total != 1 else ""} · {total_q} questions</p>
<input id="search" placeholder="Filter…" autocomplete="off">
<div class="quizrow"><button id="quiz-all">▶ Quiz me</button><button id="quiz-weak">Weak only</button></div>
{"".join(nav)}
</aside>
<main>{body_panes}<section class="pane" id="quizpane"></section></main>
<script>{JS}</script>
</body></html>"""

    out = os.path.join(DATADIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"✓ built {out}  ({len(topics)} topics, {len(notes)} notes)")


if __name__ == "__main__":
    build()
