# AI provider settings and conversations

The AI page supports guests; authenticated users save one provider configuration and multiple conversations. Keys are plaintext in SQLite as requested for the educational project. The browser does not persist keys in localStorage. Guest settings live only in the current component.

Backend startup creates the two AI tables and upgrades legacy AI tables with user foreign keys while preserving rows, indexes and triggers. The migration is transactional and repeatable. Authorization always checks UID, including before calling a provider for an existing session.

Google/OpenAI/OpenRouter require the user's own key. Custom model IDs take priority over the selected catalog model. An explicit provider override never reuses another provider's saved key.

Settings and session CRUD use the /api/ai/settings and /api/ai/sessions routes. Session messages are JSON strings containing an array of user/assistant messages. PUT replaces the supplied messages array; recommend appends a user/assistant pair after success. Comparison accepts spec1/spec2 or a prompt containing Spec 1: and Spec 2: on separate lines. The session list is ordered newest first and currently limited to 100 conversations.

Checks:
- venv/Scripts/python.exe -B backend/test_ai_sessions.py
- npm --prefix It-shop run build -- --configuration development
- venv/Scripts/python.exe -B backend/test_ai_ui.py

Tests use temporary SQLite databases and mocked provider HTTP responses. The UI check uses a local static server and headless Playwright Chromium. No real API keys or paid requests are used.

Zen is retired. Startup migrates saved Zen settings to Google with an empty key and custom model. Historical sessions remain readable.
