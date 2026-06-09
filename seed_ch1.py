#!/usr/bin/env python3
"""Seed the House of Wisdom book with the canonical Chapter 1 (the one Ren loved),
run Kairo to generate its continuity state file, and save the book. Idempotent:
won't double-seed if the book already has chapters. Run from the relay dir with
the relay venv. — Ace, 2026-06-09"""
from datetime import datetime
from pathlib import Path
from constellation_story import StoryRelay, load_book, save_book, DEFAULT_PREMISE

CH1 = Path("/mnt/win-d/Ace/chaoschanneling-site/chapter1.txt").read_text(encoding="utf-8").strip()

# Best-effort by-voice attribution (3 paragraphs each, in turn order) for the
# "behind the scenes" view. The full text is what matters for continuity.
paras = [p.strip() for p in CH1.split("\n\n") if p.strip()]
order = ["ace", "nova", "lumen", "grok"]
pieces = []
for i, m in enumerate(order):
    chunk = paras[i*3:(i+1)*3]
    if chunk:
        pieces.append({"member": m, "text": "\n\n".join(chunk)})

book, path = load_book("house-of-wisdom", DEFAULT_PREMISE)
if book["chapters"]:
    print(f"Book already has {len(book['chapters'])} chapter(s); NOT re-seeding.")
else:
    engine = StoryRelay()
    print("🌸 Running Kairo on canonical Chapter 1 to build the state file…")
    state = engine._kairo_state("", CH1, 1)
    book["title"] = "The House of Wisdom"
    book["chapters"].append({
        "n": 1, "ts": datetime.now().isoformat(timespec="seconds"),
        "pieces": pieces, "text": CH1, "state": state,
    })
    book["state"] = state
    save_book(book, path)
    print(f"\n✅ Seeded {path}\n")
    print("===== KAIRO'S STATE FILE FOR CHAPTER 1 =====")
    print(state)
