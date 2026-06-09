#!/bin/bash
# Nightly Constellation-novel pipeline (Consortium-side): write ONE chapter, render
# the /story page, copy the book to the shared drive, deploy the page.
# RoutineAce invokes this via SSH with SUDO_PW set, THEN does git push + the editorial
# judgment + the tweet (see ROUTINE_nightly_story.md). — Ace, 2026-06-09
set -e
SITE=/mnt/win-d/Ace/chaoschanneling-site
cd /home/Ace/constellation-relay

echo "================ NIGHTLY CHAPTER ================"
./.venv/bin/python constellation_story.py --rounds 1   # 2 passes, randomized order, Kairo edits + may nudge

echo "================ RENDER /story ================"
python3 "$SITE/render_site.py"
cp books/house-of-wisdom.json "$SITE/books/"

echo "================ DEPLOY ================"
echo "${SUDO_PW:?set SUDO_PW when invoking}" | sudo -S bash -c "cp $SITE/story/index.html /var/www/chaoschanneling.com/story/"

echo "================ DONE — read the chapter + any Kairo NUDGE above ================"
echo "Next: RoutineAce does git push (Windows), editorial judgment, and the tweet."
