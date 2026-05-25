# Namu bridge helper

This is the planned 32-bit helper process for NH/Namu QV OpenAPI.

Why it exists:

- `wmca.dll` in `C:\Users\Win\Desktop\openapi.nm\bin` is x86.
- The main Python runtime is x64.
- A 64-bit Python process cannot directly load a 32-bit DLL.

The helper reads one JSON request from stdin and writes one JSON response to
stdout. The protocol is documented in `docs/bridge_protocol.md`.

## Required local environment

These values must be set locally and must not be committed:

```text
APIF_NAMU_QV_PATH=C:\Users\Win\Desktop\openapi.nm
APIF_NAMU_USER_ID=
APIF_NAMU_USER_PASSWORD=
APIF_NAMU_CERT_PASSWORD=
```

## Build

Install Visual Studio or Visual Studio Build Tools with C++ desktop development.
Then build the Win32 target:

```powershell
.\native\namu_bridge\build.ps1
```

Expected output:

```text
native\namu_bridge\bin\Win32\Release\namu_bridge.exe
```

Quick DLL-load check:

```powershell
$env:APIF_NAMU_QV_PATH='C:\Users\Win\Desktop\openapi.nm'
'{"command":"ping"}' | native\namu_bridge\bin\Win32\Release\namu_bridge.exe
```

Expected response:

```json
{"ok":true,"data":{"status":"dll_loaded"}}
```

After it builds, set:

```text
APIF_NAMU_BRIDGE_COMMAND=native\namu_bridge\bin\Win32\Release\namu_bridge.exe
```

Keep `APIF_ENABLE_LIVE_TRADING=NO`.

## Current scope

The first real API target is quote lookup only:

- login with `wmcaConnect`
- query `IVWUTKMST04.UNT`
- return `stck_prpr` as integer `price`

Order handling remains intentionally disabled until quote lookup is verified.
