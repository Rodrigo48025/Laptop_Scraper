# GSD (Get Shit Done) Persistent Context & Memory Rule

## Continuous Context Protocol
To eliminate context loss and session amnesia across model changes, restarts, and thread resets:

1. **State First on Every Turn**:
   - At the beginning of any session or model change, inspect `.planning/STATE.md` at the project root.
   - Ground all planning and execution in the active roadmap and state recorded in `.planning/`.

2. **Living Memory Updates**:
   - Whenever milestones are completed, architecture decisions are agreed upon, or bugs are resolved, immediately update `.planning/STATE.md`.
   - Keep `.planning/STATE.md` concise, structured, and factual.

3. **Discipline**:
   - Strictly follow project UI rules (no emojis, clean light theme, Lucide SVG icons).
   - Execute in atomic, verified cycles.
