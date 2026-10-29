# CropPulse Rwanda — Gate 1M Disposable Test Environment Results

**Date:** 2026-10-26  
**Scope:** Mandatory preflight for the authorized limited health/OpenAPI setup. Execution stopped before environment creation or process launch.

## Initial setup attempt

The initial setup attempt was blocked because the plan contained only a workspace placeholder. This follow-up resolved the proposed path and inspected its existing parent metadata/ACL. The workspace itself remains uncreated; see the addendum below for the current disposition.

## Preflight results

| Required prerequisite | Result | Evidence / reason |
|---|---|---|
| Exact candidate path | **Verified by read-only environment/path resolution** | `[Environment]::GetFolderPath('UserProfile')` returned `C:\Users\Student`; `LocalApplicationData` returned `C:\Users\Student\AppData\Local`. Candidate resolves to `C:\Users\Student\AppData\Local\CropPulse-Rwanda\isolated-test-2026-10-26`. It does not currently exist. |
| Outside repository and known DB locations | **Verified by path comparison** | Candidate is outside `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda` and its known `data`, `.test-runtime`, and `.backups` directories. The app-specific `AppData\Local\CropPulse-Rwanda` parent does not exist, so this would be a new workspace rather than an existing application data store. |
| Existing parent ACL | **Inspected; suitable for a restricted child** | Existing `AppData` and `AppData\Local` ACLs list only `Student`, `SYSTEM`, and `Administrators` with full control; no `Users` or `Authenticated Users` entries were present. Rules are inherited from the protected user-profile ACL. The workspace and its parent do not yet exist, so their effective ACL cannot be directly observed. |
| Explicit DB URL and source selection | **Verified statically** | The plan and source identify `CROP_PULSE_DATABASE_URL`; `backend.db.database_url()` uses it, otherwise falling back to `sqlite:///./data/croppulse_phase1.sqlite3`. Relative paths resolve from process CWD. The missing workspace prevents forming the required explicit URL. |
| Startup/migration behavior | **Verified statically from the plan/source** | FastAPI lifespan runs `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`; no Alembic migration or background job is called by startup. The authorized configuration requires `0`. Route-level writes still exist, so the proposed test DB must use SQLite `mode=ro` and only the reviewed endpoints. |
| Project venv and entry point | **Documented; not runtime-preflighted** | Plan specifies `<project-root>\.venv\Scripts\python.exe` and `backend.api:app`. No Python command/import check was run because setup was stopped at the unresolved workspace prerequisite. |
| Port 18001 availability | **UNVERIFIED** | No port check was needed after the mandatory path/ACL preflight failed. No listener was contacted or changed. Recheck immediately before any future separately approved launch. |
| Existing listeners 8001/8501/5173 | **Preservation requirement retained; current mapping not rechecked** | No process or service command was executed. The plan requires capturing their PIDs before any later launch and verifying they remain unchanged afterward. |
| Empty DB safety | **Supported statically for health/OpenAPI only** | Source review in the governing plan says `/health` performs `SELECT 1`, `/openapi.json` is generated from route metadata, and neither requires application tables. This does not prove runtime behavior or schema compatibility. No DB was created/opened. |

## Actions taken and not taken

The plan was inspected. At the initial attempt, the unresolved placeholder caused setup to stop before filesystem/process setup. In this read-only follow-up, the profile path, candidate path, existing ancestor metadata/ACLs, and repository data-directory locations were inspected. The absent workspace's own ACL was not changed or directly observed.

No disposable directory or SQLite file was created. No existing database was opened, queried, copied, or modified. No API or other service was started, stopped, restarted, or contacted. No listener was inspected or changed. Existing ancestor ACLs were inspected read-only; no ACL was changed. No tests, migrations, application startup commands, dependency checks, or route requests were run. The only file created for this work is this requested results report.

## Exact next prerequisite

The owner must explicitly approve creating the workspace at the resolved candidate path and using a child-only protected ACL. The existing `AppData\Local` ACL provides a suitable inherited baseline without changing any existing directory permissions. At creation time, create the workspace with inheritance protected and explicit full-control grants only for the operator (`DESKTOP-RLJSIBU\Student`), `SYSTEM`, and `Administrators`; verify the resulting child ACL before creating the empty DB. This affects only the new child. Run the API with the explicit absolute `CROP_PULSE_DATABASE_URL` in SQLite `mode=ro`, auto-create set to `0`, and the reviewed project venv/entry point. Because the current API's database remains unidentified, preserve the plan's additional fail-closed requirement: use an OS isolation boundary that cannot write to any existing protected DB; if that cannot be established, do not launch. Recheck port 18001 and all existing listener mappings immediately before any separately authorized setup/launch.

This operation does not establish schema compatibility, persistence correctness, authentication behavior, or production readiness.

## Follow-up: proposed workspace path and ACL review (2026-10-26)

### Resolved path and evidence

The user-profile path was obtained from Windows using `[Environment]::GetFolderPath('UserProfile')`; it returned `C:\Users\Student`. The Local Application Data path was obtained with `[Environment]::GetFolderPath('LocalApplicationData')`; it returned `C:\Users\Student\AppData\Local`. No username was inferred. The proposed candidate is therefore:

```text
C:\Users\Student\AppData\Local\CropPulse-Rwanda\isolated-test-2026-10-26
```

The candidate and its `CropPulse-Rwanda` parent do not exist. Existing ancestors inspected were `C:\Users\Student`, `AppData`, and `AppData\Local`. Their relevant ACL facts:

- Profile root is ACL-protected and grants full control to the profile owner, `SYSTEM`, and `Administrators`.
- `AppData` and `AppData\Local` inherit rules and list full control for the same three principals. No broad `Users` or `Authenticated Users` write grant appeared in the displayed effective rules.
- The profile owner can create the child. A new workspace can be restricted at the child only, using a protected DACL and explicit owner, `SYSTEM`, and `Administrators` grants. This does not require changing permissions on any existing parent/file. The new directory ACL must still be inspected and confirmed after separately authorized creation; it cannot be truthfully reported as already verified.
- The project root is `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`; its documented database/data locations include `data`, `.test-runtime`, and `.backups`. The candidate is outside the entire repository tree and those known DB locations. The candidate is under the Windows Local Application Data namespace, but the app-specific directory is absent; it is not an existing CropPulse data location.

The workspace is not private merely because it is under AppData. Suitability is supported here by inspected ancestor ACLs, not by an ACL on the absent child. Do not create it until the owner separately authorizes this exact path and child-only ACL. A test process running as the profile owner will have full control under that ACL; therefore SQLite `mode=ro` remains necessary to reject API route writes. To prevent other authenticated local users from accessing the workspace, keep the child DACL protected and verify that no broad principals are present.

### Minimum future access rights

- **Operator during setup:** traverse existing ancestors and create the new child under `AppData\Local`; full control on the new workspace only, sufficient to create and verify the empty DB and then start/stop the foreground test process.
- **Test process:** read/execute access to project source and the venv; read/traverse access to the test DB and its containing workspace. Configure SQLite URI `mode=ro` and `uri=true`. Avoid route calls that write. If same-user ACL grants the process full control, the SQLite read-only connection is the database write barrier; the ACL protects against other users, not the owner process itself.
- **SYSTEM/Administrators:** retain full control on the new child for Windows administration/recovery.
- Do not add `Users`, `Authenticated Users`, or other interactive users to the child ACL. Do not change existing parent ACLs.

### Remaining isolation limit and owner decision

The workspace path and its ancestor-based access boundary are verified as a suitable candidate, but the candidate directory's ACL is not yet in existence to verify. Also, the active database of the existing API on port 8001 remains unknown. Static source shows the intended API uses one configured SQLAlchemy URL, and the process can be asserted to use only the new absolute test DB URL, but this does not identify the existing API's database. Before launch, either establish an OS sandbox/VM that has no write access to host databases and existing services, or otherwise prove the test process cannot access protected DB paths. If this cannot be established, do not start the test process.

**Next owner decision:** explicitly approve or decline creating only `C:\Users\Student\AppData\Local\CropPulse-Rwanda\isolated-test-2026-10-26` with a protected child ACL. Approval to create the workspace is not approval to start the API; launch remains a separately gated action after the child ACL, empty DB target, dependency/venv, and port/listener checks pass.

No filesystem or runtime changes were made in this follow-up. No database was opened or modified, and no service was contacted or started.

**Verdict: WORKSPACE PATH AND ISOLATION BOUNDARY VERIFIED — OWNER APPROVAL REQUIRED**
