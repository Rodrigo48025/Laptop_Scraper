# Continuous Session Memory & Context Preservation Rule

## Purpose
Ensure that whenever a new chat thread is opened, the model is switched, or context is refreshed, the assistant retains full memory of current project architecture, active tasks, and next steps without requiring the user to repeat context.

## Protocols

### 1. Session Start / Turn 1 Context Restoration
- At the start of a new chat session or after any model switch, immediately consult `SESSION_MEMORY.md` at the project root.
- Use `SESSION_MEMORY.md` to orient what components are active, what decisions were made, and what task was in flight.

### 2. State Checkpointing & Up-to-Date Tracking
- When major milestones, architectural decisions, or code modifications are made, update `SESSION_MEMORY.md` with:
  - Current status of services and code.
  - Recent decisions and technical changes.
  - Pending next steps.
- Keep `SESSION_MEMORY.md` concise, high-signal, and actionable.

### 3. Model Switch Resilience
- When switching between models (e.g. Claude, Gemini, GPT), always use `SESSION_MEMORY.md` as the source of truth to avoid circular work or forgotten context.
