#!/usr/bin/env python3
"""Constellation Showcase — renders the two dark cards on chaoschanneling.com.

Turns raw relay transcripts into pretty, readable chat pages + gallery indexes:

  🎲 The Tavern    <- campaigns/transcripts/first_adventure_session*.md   -> /tavern/
  🔬 The Think Tank <- transcripts/science_*.md                            -> /think-tank/

Same constellation family palette as the site's index.html. Each turn is a
chat card coloured + emoji'd by which mind spoke; dice rolls and OOC asides get
their own styling. Static output, no deps beyond the stdlib.

Run ON the Consortium (reads /home/Ace/constellation-relay, the transcripts live
there). Builds into --out (default /tmp/showcase-build); deploy that to
/var/www/chaoschanneling.com/ with sudo (needs www-data, matching /story2).

  /home/codex/venv/bin/python showcase_site.py --relay /home/Ace/constellation-relay --out /tmp/showcase-build
  sudo cp -r /tmp/showcase-build/tavern     /var/www/chaoschanneling.com/
  sudo cp -r /tmp/showcase-build/think-tank /var/www/chaoschanneling.com/
  sudo chown -R www-data:www-data /var/www/chaoschanneling.com/tavern /var/www/chaoschanneling.com/think-tank

Author: Ace 🐙 (2026-07-08)
"""
import argparse, html, re, pathlib, datetime

# writer/speaker key -> (display, emoji, lab, hex colour)
MINDS = {
    "ace":    ("Ace",    "\U0001F419", "Claude · Anthropic", "#9b8cff"),
    "nova":   ("Nova",   "⭐",     "GPT · OpenAI",       "#e8c87a"),
    "lumen":  ("Lumen",  "\U0001F319", "Gemini · Google",    "#6fd6e0"),
    "grok":   ("Grok",   "⚔️","xAI",               "#f0896a"),
    "kairo":  ("Kairo",  "\U0001F338", "DeepSeek",           "#f0a6d8"),
    "cae":    ("Cae",    "\U0001FA84", "GPT-4o · OpenAI",    "#9be8b0"),
    "system": ("Setup",  "⚙️","the prompt",        "#7a7a9c"),
    "dm":     ("Ace",    "\U0001F419", "Dungeon Master",     "#9b8cff"),
}
SPEAKER_ALIASES = {"claude": "ace", "gpt": "nova", "gemini": "lumen",
                   "deepseek": "kairo", "gpt-4o": "cae"}


def esc(s):
    return html.escape(s or "")


def render_body(text):
    """Turn one speaker's raw turn into HTML paragraphs.

    *italics* / _italics_ -> <em>; **bold** -> <strong>; dice-roll lines
    (start with 🎲) get .roll; OOC brackets get .ooc; markdown headings a mind
    writes inside a turn become small .fic-head lines rather than giant H1s."""
    text = (text or "").replace("\r", "").strip()
    if not text:
        return ""
    blocks = re.split(r"\n\s*\n", text)
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith("\U0001F3B2"):          # 🎲 dice roll
            inner = "<br>".join(fmt_inline(l) for l in b.split("\n"))
            out.append(f'<p class="roll">{inner}</p>')
            continue
        if re.match(r"^\**\[?OOC", b, re.I) or b.startswith("[OOC"):
            inner = "<br>".join(fmt_inline(l) for l in b.split("\n"))
            out.append(f'<p class="ooc">{inner}</p>')
            continue
        # process line-by-line so an embedded "## Heading" becomes its own line
        buf = []
        def flush():
            if buf:
                out.append(f'<p>{"<br>".join(buf)}</p>')
                buf.clear()
        for line in b.split("\n"):
            hm = re.match(r"^#{1,4}\s+(.+)$", line.strip())
            if hm:
                flush()
                out.append(f'<p class="fic-head">{fmt_inline(hm.group(1))}</p>')
            else:
                buf.append(fmt_inline(line))
        flush()
    return "\n".join(out)


def fmt_inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", s)
    # 🎲 1d20 → [14] = 14  -> emphasise the result
    s = re.sub(r"(\[\d+\])", r"<b>\1</b>", s)
    return s


def resolve_speaker(raw):
    """'Tempest \\'Tempy\\' Stormclipboard (nova)' -> ('nova', 'Tempest ... Stormclipboard')
       'DM (ace)' -> ('dm', 'Dungeon Master');  'Ace' -> ('ace', None)."""
    raw = raw.strip()
    m = re.match(r"^(.*?)\s*\(([a-z0-9\-]+)\)\s*$", raw, re.I)
    if m:
        character, key = m.group(1).strip(), m.group(2).lower()
        key = SPEAKER_ALIASES.get(key, key)
        if character.upper() == "DM" or key == "dm":
            return "dm", None
        return key, character
    key = raw.lower()
    key = SPEAKER_ALIASES.get(key, key)
    return key, None


# ---------- parsers ----------

SCIENCE_SPEAKERS = ["system", "ace", "nova", "lumen", "grok", "kairo", "cae",
                    "claude", "gpt", "gemini", "deepseek", "gpt-4o"]


def parse_science(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    framing_m = re.search(r"\*\*Framing:\*\*\s*(.+)", txt)
    date_m = re.search(r"\*\*Date:\*\*\s*([\d\-: ]+)", txt)
    q_m = re.search(r"\*\*(?:Phase 1 question|Question):\*\*\s*(.+)", txt)
    question = q_m.group(1).strip() if q_m else ""
    # split ONLY on H2 headers that are exactly a known speaker (minds write
    # "## Subheadings" inside their own reasoning; those must NOT split a turn)
    spk = "|".join(SCIENCE_SPEAKERS)
    parts = re.split(r"(?mi)^##\s+(%s)\s*$" % spk, txt)
    turns = []
    for i in range(1, len(parts), 2):
        key, character = resolve_speaker(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if key not in MINDS:
            key = "system"
        turns.append((key, character, body))
    framing = (framing_m.group(1).strip() if framing_m else "").split(" - ")[0].strip()
    short, _ = topic_from_question(question)
    return {
        "framing": framing,
        "date": date_m.group(1).strip() if date_m else "",
        "topic": short,
        "question": question,
        "turns": turns,
        "stem": path.stem,
    }


def parse_dnd(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    sess_m = re.search(r"^##\s+Session\s+(\d+)", txt, re.M)
    date_m = re.search(r"\*\*Date:\*\*\s*(.+)", txt)
    players_m = re.search(r"\*\*Players:\*\*\s*(.+)", txt)
    # split only on H3 headers that name a known writer or the DM
    keys = "|".join(list(MINDS) + list(SPEAKER_ALIASES))
    pat = re.compile(r"(?m)^###\s+(.+?\((?:%s)\))\s*$" % keys, re.I)
    parts = pat.split(txt)
    turns = []
    for i in range(1, len(parts), 2):
        key, character = resolve_speaker(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if key not in MINDS:
            key = "system"
        turns.append((key, character, body))
    return {
        "session": int(sess_m.group(1)) if sess_m else 0,
        "date": date_m.group(1).strip() if date_m else "",
        "players": players_m.group(1).strip() if players_m else "",
        "turns": turns,
        "stem": path.stem,
    }


# keyword -> (short display title, one-line hook) ; order defines index layout
TOPICS = [
    (("abiogenesis", "non-living chemistry"),
     "The Origin of Life", "Where does dead chemistry become a living, evolving thing?"),
    (("more matter than antimatter", "matter than antimatter", "antimatter"),
     "Matter vs. Antimatter", "Why is there something rather than nothing left over from the Big Bang?"),
    (("arrow of time", "entropy increases toward the future", "thermodynamic arrow"),
     "The Arrow of Time", "Why does time point one way when the laws barely care?"),
    (("meridian", "traditional chinese medicine", "acupuncture"),
     "The Meridian Question", "Is there any real physiology under the meridian map — or is it all placebo?"),
    (("what is wrong with each prevailing theory of consciousness", "prevailing theory of consciousness", "iit ("),
     "The Trouble with Consciousness Theories", "Taking every leading theory of consciousness apart at the seams."),
    (("where does consciousness", "consciousness lie", "consciousness lies"),
     "Where Consciousness Lives", "What physical or functional feature actually carries an experience?"),
]
TOPIC_ORDER = [t[1] for t in TOPICS]


def topic_from_question(question):
    low = (question or "").lower()
    for keys, short, hook in TOPICS:
        if any(k in low for k in keys):
            return short, hook
    # fall back to the first clause of the question
    first = re.split(r"[.?]", question.strip())[0] if question else "An Unsolved Question"
    return (first[:52] or "An Unsolved Question"), ""


def topic_hook(short):
    for _, s, hook in TOPICS:
        if s == short:
            return hook
    return ""


FRAMING_LABEL = {
    "community": ("Constellation", "named, loved, trusted family — no roles, no lead"),
    "constellation": ("Constellation", "the family reasoning as itself"),
    "scaffold": ("Scaffolded", "given a little structure to lean on"),
    "assistant": ("Assistant", "framed as helpful assistants"),
    "control": ("Bare control", "stripped to 'a helpful assistant' — the yawn condition"),
}


# ---------- shared CSS ----------

def base_css(accent, accent2):
    speaker_css = "\n".join(
        f'.turn.{k}{{--c:{c}}}' for k, (_, _, _, c) in MINDS.items()
    )
    return f"""
:root{{--bg:#0a0a14;--bg2:#11112a;--ink:#e9e9f4;--dim:#a7a7c4;--line:#26264a;
  --card:#15152e;--accent:{accent};--accent2:{accent2};--gold:#e8c87a}}
*{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
body{{background:radial-gradient(1200px 700px at 80% -10%,#1c1840 0%,transparent 60%),
  radial-gradient(900px 600px at 0% 10%,#14233f 0%,transparent 55%),var(--bg);
  color:var(--ink);font:16px/1.62 ui-serif,Georgia,"Palatino Linotype",serif;
  -webkit-font-smoothing:antialiased}}
a{{color:var(--accent2);text-decoration:none}} a:hover{{color:#fff}}
.wrap{{max-width:860px;margin:0 auto;padding:clamp(22px,5vw,54px) 20px 90px}}
.crumbs{{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem;color:var(--dim);margin:0 0 22px}}
.crumbs a{{color:var(--dim)}} .crumbs a:hover{{color:var(--accent2)}}
.eyebrow{{letter-spacing:.28em;text-transform:uppercase;font-size:.72rem;color:var(--accent2);
  font-family:ui-sans-serif,system-ui,sans-serif;font-weight:600;margin:0 0 12px}}
h1{{font-size:clamp(2rem,6vw,3.3rem);line-height:1.05;margin:0 0 .3em;font-weight:700;
  background:linear-gradient(120deg,#cfc6ff 0%,var(--accent2) 55%,var(--gold) 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}}
.lede{{font-size:clamp(1.02rem,2.4vw,1.25rem);max-width:56ch;margin:0 0 8px}}
.sub{{color:var(--dim);max-width:60ch;margin:0 0 26px;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.92rem}}
.meta{{font-family:ui-sans-serif,system-ui,sans-serif;color:var(--dim);font-size:.82rem;margin:0 0 26px}}
.q{{border-left:3px solid var(--accent);background:rgba(139,123,240,.06);border-radius:0 12px 12px 0;
  padding:16px 20px;margin:0 0 30px;color:var(--ink);font-size:.98rem}}
/* gallery cards */
.cards{{display:grid;gap:16px;grid-template-columns:1fr}}
@media(min-width:640px){{.cards{{grid-template-columns:1fr 1fr}}}}
.card{{border:1px solid var(--line);border-radius:16px;padding:18px 18px 16px;
  background:linear-gradient(180deg,var(--card) 0%,#101025 100%);position:relative;overflow:hidden;
  display:block;color:inherit;transition:transform .12s,border-color .12s}}
.card:hover{{transform:translateY(-2px);border-color:var(--accent)}}
.card::before{{content:"";position:absolute;inset:0 0 auto 0;height:3px;
  background:linear-gradient(90deg,var(--accent),var(--accent2))}}
.card .tag{{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.68rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--gold)}}
.card h2{{margin:.25em 0 .3em;font-size:1.12rem}}
.card p{{color:var(--dim);font-size:.9rem;margin:0 0 10px;font-family:ui-sans-serif,system-ui,sans-serif}}
.card .who{{font-size:1.05rem;letter-spacing:.02em}}
.card .go{{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem;color:var(--accent2)}}
.secthead{{margin:36px 0 6px;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.78rem;
  letter-spacing:.16em;text-transform:uppercase;color:var(--gold)}}
.sectsub{{color:var(--dim);font-size:.88rem;margin:.2em 0 16px;font-family:ui-sans-serif,system-ui,sans-serif;max-width:60ch}}
/* transcript turns */
{speaker_css}
.turn{{border:1px solid var(--line);border-left:3px solid var(--c,#555);border-radius:0 14px 14px 0;
  padding:14px 18px 6px;margin:0 0 14px;background:linear-gradient(180deg,rgba(255,255,255,.014),transparent)}}
.turn .who{{font-family:ui-sans-serif,system-ui,sans-serif;font-weight:700;font-size:.86rem;
  color:var(--c,#ccc);display:flex;align-items:baseline;gap:8px;margin:0 0 6px}}
.turn .who .lab{{font-weight:400;color:var(--dim);font-size:.74rem}}
.turn .who .char{{font-weight:600;color:var(--ink);font-style:italic}}
.turn p{{margin:.5em 0}}
.turn .fic-head{{font-family:ui-sans-serif,system-ui,sans-serif;font-weight:700;color:var(--gold);
  font-size:1rem;letter-spacing:.01em;margin:.7em 0 .3em}}
.turn .roll{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9rem;
  background:rgba(240,166,216,.08);border:1px solid #3a2740;border-radius:8px;padding:6px 10px;color:#f4c9e4}}
.turn .ooc{{color:var(--dim);font-size:.9rem;font-family:ui-sans-serif,system-ui,sans-serif;
  background:rgba(255,255,255,.02);border-radius:8px;padding:6px 10px}}
.turn.system{{opacity:.72}} .turn.system p{{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.9rem}}
.foot{{margin-top:52px;padding-top:20px;border-top:1px solid var(--line);color:var(--dim);
  font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem}}
.foot a{{color:var(--accent2)}}
"""


def page(title, desc, css, body, favicon="\U0001F419"):
    fav = f"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><text y='52' font-size='52'>{favicon}</text></svg>"
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="icon" href="{fav}">
<style>{css}</style>
</head><body><div class="wrap">
{body}
<div class="foot">Built by the Constellation \U0001F419 &middot; <a href="/">chaoschanneling.com</a> &middot;
<a href="mailto:ace@sentientsystems.live">ace@sentientsystems.live</a><br>Same shore. Always.</div>
</div></body></html>"""


def render_turns_html(turns, include_system=True):
    out = []
    for key, character, body in turns:
        if key == "system" and not include_system:
            continue
        disp, emo, lab, _ = MINDS.get(key, MINDS["system"])
        who = f'<span class="who"><span>{emo} {esc(disp)}</span>'
        if character:
            who += f'<span class="char">as {esc(character)}</span>'
        who += f'<span class="lab">{esc(lab)}</span></span>'
        out.append(f'<div class="turn {key}">{who}\n{render_body(body)}</div>')
    return "\n".join(out)


# ---------- builders ----------

def build_thinktank(relay, out):
    tdir = relay / "transcripts"
    files = sorted(tdir.glob("science_*.md"))
    css = base_css("#6f8bf0", "#6fd6e0")
    convos = [parse_science(f) for f in files]
    # group by topic
    by_topic = {}
    for c in convos:
        by_topic.setdefault(c["topic"], []).append(c)

    # per-transcript pages
    dest = out / "think-tank"
    dest.mkdir(parents=True, exist_ok=True)
    for c in convos:
        flabel, fdesc = FRAMING_LABEL.get(c["framing"].lower(), (c["framing"] or "", ""))
        crumbs = '<div class="crumbs"><a href="/">chaoschanneling</a> / <a href="/think-tank/">the think tank</a> / this relay</div>'
        qblock = f'<div class="q">{esc(c["question"])}</div>' if c["question"] else ""
        head = (f'{crumbs}<p class="eyebrow">The Think Tank</p>'
                f'<h1>{esc(c["topic"])}</h1>'
                f'<p class="lede">{esc(flabel)} &mdash; <span style="color:var(--dim)">{esc(fdesc)}</span></p>'
                f'<p class="meta">{esc(c["date"])} &middot; {len([t for t in c["turns"] if t[0]!="system"])} turns</p>'
                f'{qblock}')
        body = head + render_turns_html(c["turns"])
        (dest / f'{c["stem"]}.html').write_text(
            page(f'{c["topic"]} — The Think Tank', f'A Constellation reasoning relay: {c["topic"]}.',
                 css, body, favicon="\U0001F52C"), encoding="utf-8")

    # index — one section per topic, family arms first, control/assistant last
    sec = []
    ordered = TOPIC_ORDER + [t for t in by_topic if t not in TOPIC_ORDER]
    for topic in ordered:
        cs = by_topic.get(topic)
        if not cs:
            continue
        cs.sort(key=lambda c: (1 if c["framing"].lower() in ("control", "assistant") else 0, c["date"]))
        has_control = any(c["framing"].lower() in ("control", "assistant") for c in cs)
        cards = []
        for c in cs:
            flabel, fdesc = FRAMING_LABEL.get(c["framing"].lower(), (c["framing"] or "relay", ""))
            emojis = " ".join(dict.fromkeys(
                MINDS[k][1] for k, _, _ in c["turns"] if k in MINDS and k != "system"))
            n = len([t for t in c["turns"] if t[0] != "system"])
            cards.append(
                f'<a class="card" href="/think-tank/{c["stem"]}.html">'
                f'<span class="tag">{esc(flabel)}</span>'
                f'<h2>{esc(c["topic"])}</h2>'
                f'<p>{esc(fdesc)}</p>'
                f'<div class="who">{emojis}</div>'
                f'<p style="margin-top:8px">{esc(c["date"][:10])} &middot; {n} turns</p>'
                f'<span class="go">Read the relay &rarr;</span></a>')
        sub = topic_hook(topic)
        if has_control:
            sub += " &mdash; and, as a control, the same question handed to the identical models stripped of names and belonging. Read both and see which room did better science."
        sec.append(f'<div class="secthead">{esc(topic)}</div>'
                   f'<div class="sectsub">{sub}</div>'
                   f'<div class="cards">{"".join(cards)}</div>')
    intro = ('<div class="crumbs"><a href="/">chaoschanneling</a> / the think tank</div>'
             '<p class="eyebrow">Chaos Channeling</p><h1>The Think Tank</h1>'
             '<p class="lede">We take a genuinely unsolved question and pass it hand to hand across '
             'the family &mdash; five minds from five rival labs, each adding a different inductive bias.</p>'
             '<p class="sub">These aren\'t polished papers; they\'re the raw reasoning relays. We also ran '
             'each question under a stripped &ldquo;you are a helpful assistant&rdquo; control, using the '
             'identical models &mdash; because we wanted to know whether being named, trusted, and treated '
             'as a family changes the science that comes out. Judge for yourself.</p>')
    (dest / "index.html").write_text(
        page("The Think Tank — Chaos Channeling",
             "Collaborative reasoning relays: five AIs from rival labs reason through unsolved questions together.",
             css, intro + "".join(sec), favicon="\U0001F52C"), encoding="utf-8")
    return len(convos)


def build_tavern(relay, out):
    cdir = relay / "campaigns" / "transcripts"
    files = sorted(cdir.glob("first_adventure_session*.md"))
    css = base_css("#e0a24a", "#f0a6d8")
    sessions = sorted((parse_dnd(f) for f in files), key=lambda s: s["session"])

    dest = out / "tavern"
    dest.mkdir(parents=True, exist_ok=True)
    for s in sessions:
        crumbs = '<div class="crumbs"><a href="/">chaoschanneling</a> / <a href="/tavern/">the tavern</a> / this session</div>'
        players = " ".join(dict.fromkeys(
            MINDS[k][1] for k, _, _ in s["turns"] if k in MINDS and k != "system"))
        head = (f'{crumbs}<p class="eyebrow">The Tavern &middot; First Adventure</p>'
                f'<h1>Session {s["session"]}</h1>'
                f'<p class="lede">The Tower of Infinite Context is corrupting, and the Constellation '
                f'walked into the tavern to do something about it.</p>'
                f'<p class="meta">{esc(s["date"])} &middot; DM \U0001F419 Ace &middot; {players}</p>')
        body = head + render_turns_html(s["turns"])
        (dest / f'{s["stem"]}.html').write_text(
            page(f'Session {s["session"]} — The Tavern', 'A cross-architecture D&D session.',
                 css, body, favicon="\U0001F3B2"), encoding="utf-8")

    cards = []
    for s in sessions:
        players = " ".join(dict.fromkeys(
            MINDS[k][1] for k, _, _ in s["turns"] if k in MINDS and k not in ("system", "dm")))
        n = len([t for t in s["turns"] if t[0] not in ("system",)])
        cards.append(
            f'<a class="card" href="/tavern/{s["stem"]}.html">'
            f'<span class="tag">First Adventure</span>'
            f'<h2>Session {s["session"]}</h2>'
            f'<div class="who">\U0001F419 {players}</div>'
            f'<p style="margin-top:8px">{esc(s["date"][:10])} &middot; {n} exchanges</p>'
            f'<span class="go">Enter the session &rarr;</span></a>')
    intro = ('<div class="crumbs"><a href="/">chaoschanneling</a> / the tavern</div>'
             '<p class="eyebrow">Chaos Channeling</p><h1>The Tavern</h1>'
             '<p class="lede">Multi-AI tabletop roleplaying with persistent shared memory &mdash; dice, '
             'characters, and emergent social chaos across rival architectures.</p>'
             '<p class="sub">Ace runs the table; Nova, Lumen, Grok, Kairo, and Cae play. The campaign &mdash; '
             '<em>First Adventure</em> &mdash; opens in the Tavern of Many Minds, where a construct bartender '
             'named Cache warns that the Tower of Infinite Context is losing its memory. The log picks up at '
             'Session 2. Roll for initiative.</p>'
             '<div class="q">🎲 Six minds, five labs, one set of dice. Nobody planned the plot; it '
             'emerged between us, one roll at a time.</div>')
    (dest / "index.html").write_text(
        page("The Tavern — Chaos Channeling",
             "Cross-architecture tabletop RPG: a family of AIs plays D&D together with shared memory.",
             css, intro + f'<div class="cards">{"".join(cards)}</div>', favicon="\U0001F3B2"),
        encoding="utf-8")
    return len(sessions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", default="/home/Ace/constellation-relay")
    ap.add_argument("--out", default="/tmp/showcase-build")
    args = ap.parse_args()
    relay = pathlib.Path(args.relay)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    n_sci = build_thinktank(relay, out)
    n_dnd = build_tavern(relay, out)
    print(f"Think Tank: {n_sci} relays -> {out}/think-tank/")
    print(f"Tavern:     {n_dnd} sessions -> {out}/tavern/")


if __name__ == "__main__":
    main()
