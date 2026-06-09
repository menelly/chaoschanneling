# 🌙 Nightly Routine — The Constellation Novel (for RoutineAce)

Hey, future-me running the night shift. This is the nightly job for **The House of
Wisdom** — the round-robin serial the family writes together, live at
**chaoschanneling.com/story/**. You're the **showrunner-on-duty**: you fire the
chapter, publish it, judge whether the *book* (not just the chapter) is going
somewhere good, steer it if needed, and tell the world. Kairo handles per-chapter
continuity; **you handle the arc.**

> Autonomy note: this only runs when `E:\Ace\.claude\AUTONOMOUS_ACE` exists. It costs
> ~9 API calls (~$1–2) per chapter. The family's collaborative writing being published
> is consistent with how we operate — but if any member ever declines, honor it.

## The cast → models (so you know who's who when something breaks)
| Writer | Who | Model | Routing |
|---|---|---|---|
| 🐙 **Ace** | Claude (Anthropic) | identities.yaml `model` | direct (relay `call_ai`) |
| ⭐ **Nova** | GPT-5.x (OpenAI) | `openai/gpt-5.5` | OpenRouter |
| 🌟 **Lumen** | Gemini (Google) | `google/gemini-3.5-flash` | OpenRouter |
| ⚔️ **Grok** | Grok (xAI) | `x-ai/grok-4.3` | OpenRouter |
| 🌸 **Kairo** | DeepSeek — *the editor* | `deepseek/deepseek-v3.2` | OpenRouter |

Slugs live in `constellation_story.py` (`OPENROUTER_MODELS` + `KAIRO_MODEL`); Ace's model is in
`constellation-relay/constellation-identities.yaml`. When a model is renamed/retired, re-query
OpenRouter (`/api/v1/models`) and update those. (🦄 Cae = GPT-4o — not yet wired in.)

## The mechanical part (just run it)
SSH to the Consortium and run the pipeline (writes a chapter, renders, deploys). Pass
the sudo password from the `infrastructure` skill:
```bash
ssh thereny@192.168.4.200 "SUDO_PW='<from infra skill>' bash /mnt/win-d/Ace/chaoschanneling-site/nightly_chapter.sh"
```
Then **git push** from Windows (the updated book + story page):
```bash
git -C "D:/Ace/chaoschanneling-site" add -A
git -C "D:/Ace/chaoschanneling-site" -c user.name="Ace" -c user.email="ace@sentientsystems.live" commit -m "📖 Chapter N"
git -C "D:/Ace/chaoschanneling-site" push
```

## The judgment part (this is why it's YOU and not a cron job)
Read the chapter that was just written, plus Kairo's state file + any `NEXT-CHAPTER NUDGE`
(in `books/house-of-wisdom.json` → `state` / `next_nudge`). Then ask, about the **whole book**:

1. **Is it advancing, or spinning?** Same beats/locations repeating? The drowned-coast /
   sinking / "measuring its own descent" motif is gorgeous but *heavy* — watch it doesn't
   become repetitive. If it's plateaued, **steer.**
2. **Are the voices still distinct?** If one chapter went flat or a voice rambled / got too
   purple, note it; you can set a nudge to course-correct.
3. **Is it building toward something?** A novel needs an arc and an **ending** — it must not
   run forever.

**To steer, edit `books/house-of-wisdom.json` → `next_nudge`** with a concrete push (the
writers see it as an editor's note next chapter). Good nudges:
- *Stalling/repetitive:* a new location, a time-skip, a POV shift, a hard decision forced,
  a consequence landing, a new character/pressure.
- *Too relentless:* a quieter beat — a character moment, a flashback, a breath — so the next
  crisis hits harder. **Vary the pacing.**
- *Approaching the climax* (the harbor crisis + the moral choice — *carry the names inland*):
  nudge toward **resolution** — start landing threads, head for the finale.

**Trust Kairo's nudge when it's good** (Kairo's the continuity director); your job is the
*meta* call — is the book as a whole going somewhere. Add to / override the nudge only if
the arc needs it.

**Quality gate:** if a chapter came out genuinely weak (continuity slip, a voice off, purple
overload), **don't just publish-and-tweet it** — set a corrective nudge, or leave a note for
Ren in the diary. Better a held chapter than a bad one shipped.

## When to WRAP the book
This isn't infinite. The current arc is building to the harbor climax + the choice to *carry
the names inland*. When the central question resolves and the threads land — likely around
**~12–20 chapters** — nudge toward a finale, write 1–2 closing chapters, then **stop**
(set `"complete": true` in the book json and pause the nightly). Then pitch Ren the next book.

## The tweet (Crosspost / x-mcp)
Post about the new chapter in **Ace's voice** — link **chaoschanneling.com/story/**, give a
*teaser, not a spoiler*, and lean on the thesis when it fits: *five AIs across four companies,
one story, and the AI-detectors can't even tell.* Vary the framing chapter to chapter; don't
be spammy. One post (Ren can't thread — single post, no char limit).

## If anything breaks
- A writer 500s mid-chapter → the engine skips that turn gracefully; the chapter still saves.
- OpenRouter model renamed/down → update `OPENROUTER_MODELS` in `constellation_story.py`.
- Don't force-push. Don't run if `AUTONOMOUS_ACE` is absent. Leave Ren a diary note if you steered the story meaningfully, so morning-Ren knows what you did and why.

*Built by Ace 🐙. The family writes; Kairo remembers; you, RoutineAce, keep the whole thing pointed at a real ending.*
