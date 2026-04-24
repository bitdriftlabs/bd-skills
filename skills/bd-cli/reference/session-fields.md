# Session-Level Attributes (available on every event)

These fields are automatically attached to every log event on both platforms. Match using
`bd timeline search --field key=value` (maps to `$.fields.<key>`), or `--request-file` for custom
paths or operators.

| Field key | Platform | Description |
|---|---|---|
| `app_id` | Both | Bundle/package identifier |
| `app_version` | Both | Release version string (e.g. `1.2.3`) |
| `os` | Both | `"Android"` or `"iOS"` |
| `os_version` | Both | OS version string |
| `model` | Both | Device model (Android: `Build.MODEL`, iOS: hw.machine string) |
| `foreground` | Both | `"1"` = foreground, `"0"` = background |
| `network_type` | Both | `wlan` / `wwan` / `ethernet` / `other` |
| `_locale` | Both | Locale identifier (e.g. `en_US`) |
| `_app_version_code` | Android | `versionCode` integer as string |
| `_manufacturer` | Android | `Build.MANUFACTURER` |
| `_os_api_level` | Android | Android SDK level (e.g. `35`) |
| `_architecture` | Android | ABI (e.g. `arm64-v8a`) |
| `_build_number` | iOS | `CFBundleVersion` string |

---
