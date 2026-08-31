#!/usr/bin/env bash
# Reusable dev tmux session for collections-workflow.
# Kills any existing "collections" session, then creates a fresh one with:
#   0 compose  - docker compose watch (live container output)
#   1 backend  - shell in backend/, uv venv active, idle for pytest/scripts
#   2 frontend - idle shell in frontend/, ready for `bun dev`
#   3 git      - idle shell at repo root
set -euo pipefail

SESSION="collections"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

tmux kill-session -t "$SESSION" 2>/dev/null || true

tmux new-session -d -s "$SESSION" -n compose -c "$REPO_ROOT"
tmux send-keys -t "$SESSION:compose" 'docker compose watch' C-m

tmux new-window -t "$SESSION" -n backend -c "$REPO_ROOT/backend"
tmux send-keys -t "$SESSION:backend" 'source .venv/bin/activate 2>/dev/null; echo "backend shell ready (uv venv active) — try: uv run pytest app/collections/tests -v"' C-m

tmux new-window -t "$SESSION" -n frontend -c "$REPO_ROOT/frontend"
tmux send-keys -t "$SESSION:frontend" 'echo "frontend shell ready — try: bun dev  (hot reload on :5173)"' C-m

tmux new-window -t "$SESSION" -n git -c "$REPO_ROOT"
tmux send-keys -t "$SESSION:git" 'git status' C-m

tmux new-window -t "$SESSION" -n ngrok -c "$REPO_ROOT"
tmux send-keys -t "$SESSION:ngrok" 'ngrok http 8000' C-m

tmux select-window -t "$SESSION:compose"

echo "Session '$SESSION' ready. Attach with: tmux attach -t $SESSION"
