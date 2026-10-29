# Private messaging — Phase 1

## Scope

The React workspace offers private text conversations between a farmer and an active CropPulse reviewer. Farmers can contact reviewers whose administrator-assigned districts overlap a district of a farm they currently own. The UI calls these accounts **CropPulse reviewers**; the role does not certify agricultural training or qualifications. One reusable conversation is stored for each farmer/reviewer pair. Farmers and reviewers can read paginated history, send text, and see persisted unread counts. Loading the conversation list does not change read state; opening a conversation explicitly records incoming messages shown in the loaded page as read.

The administrator setting is at **System health → Private farmer-to-reviewer messaging**. It starts disabled and can only be changed by an administrator; each change requires a reason and is written to the existing administrative audit log. The API enforces the setting on discovery, listing, reading, sending, and read-state updates.

## Setup and migration

Install the repository Python requirements, configure the API/database as described in [React app setup](react-app-setup.md), then apply the additive Alembic migration from the project root:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Restart the FastAPI API and Vite frontend after schema changes. The migration `0006_private_messaging` adds a singleton messaging setting, private conversations, and private messages. Its initial setting is disabled. Apply to a disposable/test database first, and take a verified backup before production migrations. Downgrade removes the messaging tables and their content; it does not restore deleted messages. The migration is reversible structurally, not as a data-preserving rollback.

## Access and privacy

Every messaging API request rechecks active account status, current roles, current farm ownership/districts, current reviewer assignments, and the global setting. Thus suspension, role changes, farm district/ownership changes, or reviewer-scope changes immediately deny access when the eligibility condition no longer holds. Administrators control the feature switch and audit actions but have no endpoint to read message contents. Only the two conversation participants can list or access messages. Account deletion cascades to that account's conversations and their messages.

Messages are private application records, but the project does not yet provide retention limits, user reporting, moderation workflows, encryption beyond the configured transport/database controls, or message export/deletion controls. Operators must protect database backups and production transport, define retention and incident procedures, and communicate those terms before serving real users. There is no end-to-end encryption.

## API

- `GET /v1/messaging/reviewers` — farmer's currently eligible reviewers and overlapping districts.
- `POST /v1/messaging/conversations` — create or return the unique pair conversation (`reviewer_id`).
- `GET /v1/messaging/conversations` — participant's eligible conversations and unread counts.
- `GET /v1/messaging/conversations/{id}/messages?offset=0&limit=50` — stable newest-page history, returned chronologically; limit 1–100.
- `POST /v1/messaging/conversations/{id}/messages` — send nonblank text, up to 4,000 characters.
- `POST /v1/messaging/conversations/{id}/read` — mark only supplied incoming message IDs from the displayed page read (`{"message_ids": [...]}`). Older messages outside the loaded page remain unread.
- `GET/PUT /v1/admin/messaging-setting` — admin-only feature setting; updates require a reason.

The frontend checks for new messages while a conversation is open using a 15-second HTTP refresh. No WebSocket, push, email, SMS, attachment, group, or farmer-to-farmer functionality is included.

## Limitations and rollout

The feature requires a current authenticated FastAPI service, database migrations through `0006_private_messaging`, active reviewer accounts with administrator-assigned district scopes, and an administrator to enable the setting. If an eligibility scope is removed, the conversation becomes inaccessible; its history remains in the database unless the account is deleted. Offset pagination may shift while new messages arrive. Automated tests do not establish browser usability, operational monitoring, privacy compliance, backup recoverability, or production readiness.
