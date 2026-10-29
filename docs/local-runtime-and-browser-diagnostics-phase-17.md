# CropPulse Rwanda — Local Runtime and Browser Diagnostics, Phase 17

**Date:** 2026-10-28  
**Scope:** read-only inspection of local listeners and prior browser launch evidence, plus fresh-profile blank-page launch diagnostics. No application service was started and no application port was contacted.  
**Product status:** **DEVELOPMENT ONLY.**

## Summary

Ports 5173 and 8001 had loopback listeners in both snapshots, but the 5173 PID changed during this diagnostic: initial PID 8980 was absent from the final snapshot, where PID 21300 owned that port. PID 21300's start time fell during the diagnostic window, but no evidence establishes why the PID changed or whether this was related to the browser attempt. Port 8001 remained PID 27120. The executable images are visible as `node.exe` and `python.exe`, but this shell cannot read their command lines, parent process IDs, or owners. Port convention and executable type do not prove either is CropPulse. Current owners are classified **UNKNOWN**, left running, and were not contacted.

The Phase 16 requests can be accounted for only at the socket level: its report says unauthenticated `GET /` was sent to `127.0.0.1:5173` and `GET /health` to `127.0.0.1:8001` before the listeners were identified. The current listener table maps those addresses/ports to PIDs 8980 and 27120. The responses and timing do not identify the applications, explain their behavior, or establish ownership. No further requests were sent.

Chrome and Edge both fail to render even `about:blank` when launched headlessly with new, writable, unique profiles. Chrome reports Crashpad and Mojo `Access is denied`; Edge reports the same plus sandbox ACL grant failures for its own profile cache/network directories. This reproduces independently of any CropPulse listener. Basic profile-directory writability is therefore not sufficient to explain the failure. The evidence does not distinguish Windows job/container restrictions, enterprise policy, endpoint controls, or another OS security boundary. No security controls were disabled.

## Environment and commands

- Shell: Windows PowerShell `powershell.exe`; user `DESKTOP-RLJSIBU\Student`; temporary root `C:\Users\Student\AppData\Local\Temp`; local app-data root `C:\Users\Student\AppData\Local`.
- Diagnostic commands: `whoami.exe`; `$PSVersionTable`; `Get-Command ...`; `netstat -ano -p tcp`; `Get-NetTCPConnection -State Listen`; `tasklist /fo csv`; `Get-CimInstance Win32_Process -Filter ...`; `Get-Process`; `icacls.exe`; `Get-ChildItem`; `Test-Path`; `Get-Item`/`Get-Acl`; `git --version`.
- `git --version`: unavailable because Git is not on PATH. A complete repository status/diff could not be captured. This phase changed only this report and the README link; no application or data files were edited.
- `tasklist /fo csv`: returned `ERROR: Access denied`. `Get-CimInstance Win32_Process` for the two listener PIDs returned `Access denied`; `Get-Process -IncludeUserName` requires elevation. No elevation was requested.
- `Get-NetTCPConnection -State Listen` returned no rows, while `netstat` consistently showed the two listeners below. `netstat` results are reported as the effective socket evidence.
- Setup references inspected: `docs/react-app-setup.md`, `docs/react-deployment-checklist.md`, `frontend/package.json`, and `backend/db.py`. The setup guide's normal development ports are API 8001, React 5173, and Streamlit 8501. No app was started; no database selector was read from or applied to a process.

No credentials, cookies, tokens, full environment dump, or secret values were read or recorded.

## Relevant listeners

Read-only command: `netstat -ano -p tcp`, filtered to `LISTENING` entries for ports 8000, 8001, 5173, 8501, 49182, and 49183. Follow-up `Get-Process -Id` provided image/path and start time. Parent and command line requests were denied.

| Local endpoint | PID / image | Executable path and start time | Command line / parent / owner | Association and confidence |
|---|---|---|---|---|
| `127.0.0.1:5173` initial snapshot | 8980 / `node.exe` | `C:\Users\Student\AppData\Local\nodejs\node.exe`; 2026-10-28 08:43:39 local time | Not readable: CIM denied; owner query requires elevation | **UNKNOWN.** Port and image are compatible with many Node apps; no project path or parent evidence is available. It was present at the first snapshot and absent later; this phase did not terminate it. |
| `127.0.0.1:5173` final snapshot | 21300 / `node.exe` | `C:\Users\Student\AppData\Local\nodejs\node.exe`; 2026-10-28 14:08:14 local time | Not readable: CIM denied; owner query requires elevation | **UNKNOWN.** The PID change happened during this phase, but cause and relationship to the diagnostic are unestablished. Left running and not contacted. |
| `127.0.0.1:8001` both snapshots | 27120 / `python.exe` | `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; 2026-10-28 08:45:45 local time | Not readable: CIM denied; owner query requires elevation | **UNKNOWN.** Port and interpreter are compatible with many Python apps; no module/working-directory evidence is available. Left running and not contacted. |
| `127.0.0.1:8501` | No listener observed | — | — | No Streamlit listener observed at diagnostic time. |
| `127.0.0.1:49182`, `127.0.0.1:49183` | No listener observed | — | — | Phase 16 test service ports were free after its cleanup. |

No process was stopped, restarted, signaled, reconfigured, or probed over HTTP. The PID change at 5173 was observed from successive `netstat`/`Get-Process` snapshots; no process tree or event log evidence was accessible to explain it.

## Browser executable and profile evidence

Browser paths and versions recorded in Phases 11/16:

| Browser | Executable | Recorded version |
|---|---|---|
| Google Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` | 156.0.8078.48 |
| Microsoft Edge | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` | 156.0.4314.42 |

The files exist. This shell's direct `--version` calls produced no version text; the version strings above are carried forward from Phase 11/16 records, not independently confirmed by that command in this phase.

### Phase 16 attempt review

- Chrome profile path recorded by Phase 16: `C:\Users\Student\AppData\Local\Temp\croppulse-phase16-run\chrome-profile`. It was created for that attempt, and its ACL grants `DESKTOP-RLJSIBU\Student` full control; a direct write probe to that older directory was not recorded. Its error log contains Crashpad `CreateFile: Access is denied`, a fatal Mojo platform-channel access-denied error, and Crashpad self-termination. The report's HTML capture was empty. The ACL evidence alone does not establish that Chrome's sandbox/child processes could operate there.
- The Phase 16 folder has no `edge-profile`, Edge stdout, or Edge stderr artifact. The Phase 16 report says an Edge fallback was attempted, but does not preserve the exact profile path or command. Exact profile use and whether the Edge executable actually launched in that attempt are therefore **UNKNOWN**. No stale lock or profile-owner conclusion can be made for that attempt.
- Existing Chrome/Edge processes and default profile state files were visible during this phase. Their profile contents and command lines were not inspected. They are not evidence that the unique Phase 16/17 profile paths were already owned.

### Fresh blank-page diagnostics in this phase

No application service or listener was accessed. The following exact new profile directories were confirmed absent before creation, created under the current user's `%TEMP%`, ACL-inspected with `icacls`, and passed a write/delete probe as the current user:

- Chrome: `C:\Users\Student\AppData\Local\Temp\croppulse-phase17-browser-blank\chrome-profile`
- Edge: `C:\Users\Student\AppData\Local\Temp\croppulse-phase17-browser-blank\edge-profile`

The PowerShell launch pattern used the following arguments (with `$browser`, `$profileDir`, `$stdout`, and `$stderr` set to the exact values in the table above):

```powershell
$args = @('--headless=new', "--user-data-dir=`"$profileDir`"", '--dump-dom', 'about:blank')
$proc = Start-Process -FilePath $browser -ArgumentList $args -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait
```

For Chrome, `$browser` was `C:\Program Files\Google\Chrome\Application\chrome.exe`, `$profileDir` was `C:\Users\Student\AppData\Local\Temp\croppulse-phase17-browser-blank\chrome-profile`, and outputs were `stdout.txt`/`stderr.txt` in the diagnostic directory. For Edge, `$browser` was `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, `$profileDir` was `C:\Users\Student\AppData\Local\Temp\croppulse-phase17-browser-blank\edge-profile`, and outputs were `edge-stdout.txt`/`edge-stderr.txt` there. The PowerShell setup also used this write probe before each launch:

```powershell
[IO.File]::WriteAllText((Join-Path $profileDir 'write-check.tmp'), 'temporary diagnostic write check')
Remove-Item -LiteralPath (Join-Path $profileDir 'write-check.tmp') -Force
```

| Browser | Exit | Result |
|---|---:|---|
| Chrome | `-36863` | No DOM output. `stderr`: Crashpad `CreateFile: Access is denied (0x5)`; fatal Mojo platform-channel check `Access is denied (0x5)`; crash server failed and browser self-terminated. |
| Edge | `-2147483645` | No DOM output. `stderr`: Crashpad access denied; fatal Mojo platform-channel access denied; EdgeUpdate registry stats write denied; sandbox could not grant access to profile Cache/Network directories. |

The profile directories passed an ordinary user write test and have explicit user full-control ACL entries. Both attempts used unique new profile paths; no `SingletonLock` or pre-existing profile directory was reused. No request was made to an app URL, and no browser automation package or capture extension was involved. Because the failure occurred during browser process startup and access checks, the evidence does not point to a CropPulse route, Vite/API listener, Playwright package, or HTML capture tool as the cause. It also does not identify which OS or enterprise control denied the operations.

## Actions deliberately not taken

- Did not request/attempt administrator elevation or read protected process metadata.
- Did not send requests to ports 5173, 8001, or any other unidentified listener.
- Did not stop or modify any listener, browser process, user profile, lock file, policy, or browser security setting.
- Did not start CropPulse, Streamlit, FastAPI, Vite, or any other application service.
- Did not access any application database, backup, farmer record, credential, or external provider.
- Did not install packages, change npm offline policy, launch Playwright, or alter source/configuration/build outputs/agronomic data.
- Retained the new blank-page diagnostic profiles and logs under `%TEMP%`; no personal profile data was used. No unrelated files were cleaned up.

## Safest next verification path

1. Ask the workstation/IT owner to identify the owners and command lines for PIDs 8980 and 27120, and confirm whether those services are authorized CropPulse test instances. The current shell lacks the rights to establish this. Until then, keep both **UNKNOWN** and do not contact them.
2. Ask the workstation/IT owner to run or authorize a browser launch in an approved interactive desktop context using a fresh temporary profile, while preserving Chrome/Edge sandboxing. The same blank-page failure reproduced for both browsers with writable profiles, so repeating with another directory in this shell is unlikely to add useful evidence. Do not use `--no-sandbox` or weaken policy.
3. Separately resolve Phase 11–13's `@playwright/test` package-source approval. Manual blank-page launchability and package-source approval are distinct prerequisites; neither establishes automated E2E coverage.
4. After browser launch and listener ownership are established, prepare a positively identified test service with an explicit synthetic database, then perform only the bounded manual checks planned in Phase 16. Record screenshots/observations and keep automated E2E status separate.

CropPulse remains **DEVELOPMENT ONLY**. This diagnostic phase provides no deployment, rule activation, pilot, or release authorization.
