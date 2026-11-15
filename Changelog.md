# Changelog

All notable changes to **Media Directory Lister** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the versioning
is progressive (`major.minor`), with an incremental number for each substantial change.

## [Unreleased]

_Nothing pending._
## [5.63]
- Fixes the worker saving in "Edit profile" and "New profile".
  Previously, after setting profilo["worker"], _salva_profili() called _memorizza_colonne(), which re-read self.var_worker (still at the old value) and overwrote the chosen worker. Now self.var_worker is also updated after saving, so the main window combobox and the profile stay in sync.

## [5.62]
- The "Edit profile" and "New profile" windows now also show the "Analysis workers" Combobox (4, 6, 8, 12, 16, 24, 32).
  The "Save" button saves name, folder, type, and worker together. Previously the combobox was only in the main window, so it could not be saved permanently in the profile.

## [5.61]
- Each profile now has a "worker" field (number of parallel ffprobe processes). Default 8. Recommended values: 4-6 for HDD or slow USB, 8 for general use, 16-24 for SSD or fast network. Range 1-32.
- The "Media folder" tab has a "Analysis workers" Combobox with values 4, 6, 8, 12, 16, 24, 32. The value is saved in the profile.
- _lavora uses the active profile's worker for the ThreadPoolExecutor.

## [5.60]
- Audio bitrate for Audio files (FLAC, ALAC, WAV, etc.): if missing after all attempts (audio.bit_rate, fmt.bit_rate, bps tags), the real average bitrate is used: size * 8 / duration, computed in memory. No more extra ffprobe calls per file: FLAC scanning is fast again, like in v5.50.
  The value is the average over the whole file, not a 2-second sample: for VBR FLACs it is closer to the truth.
- For Video files the condition does not trigger: size * 8 / duration would include the video stream. For Video files without audio.bit_rate it falls back to _bitrate_audio_reale, as in v5.59. So nothing is lost compared to v5.59: FLACs gain, everything else stays the same.

## [5.59]
- _sorgente_cambiata no longer runs os.path.isdir synchronously for non-local folders: for local folders the check stays immediate, for remote folders they are assumed valid (the "does it exist?" check is done in avvia() with the timeout dialog from v5.56). This way `<FocusOut>` no longer freezes for 20-30 seconds when the folder is remote and offline.
- _sorgente_scelta no longer calls testo_sorgente for non-local folders: testo_sorgente goes through WNetGetConnectionW, which can block on an offline network drive. For non-local folders the raw path is used.

## [5.58]
- New "Annulla.TButton" style: red background (ERRORE), white text, darker hover.
- The "Cancel" button at the bottom of the main window uses this style.

## [5.57]
- _on_closing: if a scan is running, ask for confirmation before closing.
- avvia(): the "Generate" button is disabled during the folder check dialog, so a second scan cannot start by mistake.
- Report: the text search now includes video codecs, audio codecs, and audio tracks.
- Report: natural sort for the file name (Episode 2 before Episode 10).
- Report: the "Images only" button is hidden when the report contains no images.
- Cosmetics: removed a redundant json import, an unused loop variable, a double conn.close(), and a redundant DELETE in CacheScansioni.salva.

## [5.56]
- avvia() no longer blocks on os.path.isdir for offline network folders. For local folders the check stays immediate (os.path.isdir, fast). For network folders the check runs in a thread with a "Folder check..." dialog and a "Cancel" button. If the thread doesn't answer within 3 seconds, the folder is assumed unreachable, the dialog is closed and an error is shown. The GUI never freezes.

## [5.55]
- _chiedi_profilo_per_cartella_nuova no longer shows the dialog when there is only one option: the choice is applied directly.
- Removed a dead elif branch in _chiedi_profilo_per_cartella_nuova.
- _memorizza_colonne now has an English comment explaining why the name is historical and what the method actually does (it saves only the view options, not the columns).

## [5.54]
- _sorgente_cambiata remembers for which folder the user already answered in the profile-choice dialog (self._cartella_scelta_sessione). If it is called again for the same folder (for example `<Return>` followed by `<FocusOut>`), it exits immediately without reopening the dialog.

## [5.53]
- avvia() no longer calls _sorgente_cambiata() at the start. A folder typed by hand was already handled by the `<Return>` and `<FocusOut>` bindings of the entry box, so the call was redundant and, since v5.48, it reopened the profile-choice dialog for a folder the user had already decided to use without associating it with a profile.

## [5.52]
- New function _cartella_locale(percorso): True if the path is on a local drive, False if it is UNC, a mapped network drive, a relative path, or not determinable.
- The three places that open filedialog.askdirectory (scegli_cartella, modifica_profilo, nuovo_profilo) pass initialdir only if the folder is local. If the folder is on an offline network, askdirectory starts from the Windows default folder and does not freeze the program for 20-30 seconds.

## [5.51]
- _bitrate_audio_reale now takes the audio track index and uses `-select_streams a:{index}`. _tracce_audio passes it for each track, so the computed bitrate is the one of the right track, not always the first one.
- analizza uses _bitrate_audio_reale even when calcola_audio is False, if the bitrate is missing after all attempts (bit_rate, bps tags). Before, that branch was never executed.
- versione_a_tuple extracts the leading numeric part of each component: a tag like "5.51-beta" is no longer considered lower than "5.50".
- _lossless recognises DTS:X as lossless (in addition to DTS-HD MA).
- _sorgente_cambiata does not open the choice dialog twice in a row (Return + FocusOut): a flag prevents the double opening.
- "Includi immagini" no longer sets modifiche_non_salvate: it is a session option and must not trigger the "save changes?" message on close.

## [5.50]
- Fixes profile saving. In v5.48 "Modifica profilo", "Nuovo profilo", "Elimina profilo" and the type change no longer called _salva_profili() (the call had been removed from _profilo_cambiato to avoid implicit column saves), so changes stayed in memory but were not written to config.json and were lost on restart. Now every explicit profile change calls _salva_profili().


# [5.41] — 2026-10-31

### Changed -
bugfix of interface

# [5.35] — 2026-10-31

### Changed
- The update notification has been restored to a discreet text link (instead of the intrusive
  green button) and is now correctly positioned at the bottom left of the window, right above
  the status bar.

### Fixed
- Fixed a Tkinter issue where the update label would disappear if the window was redrawn.
  The label is now created persistently inside the `costruisci()` method.

---

## [5.34] — 2026-10-31

### Fixed
- Fixed the visual placement of the update notification by using `place()` directly on the root
  window. Although functional, this approach was found to be visually intrusive and replaced
  in 5.35.

---

## [5.33] — 2026-10-31

### Fixed
- Fixed a bug in the version comparison logic that prevented the update prompt from appearing
  even when the remote version was correctly detected as newer.

---

## [5.32] — 2026-10-31

### Fixed
- Improved the robustness of the GitHub API call by increasing the timeout to 10 seconds and
  adding detailed console logging for debugging.
- Replaced the simple `float()` conversion with a tuple-based comparison (e.g., `(5, 32)` vs
  `(5, 99)`) to correctly handle multi-digit version numbers.

## [5.24] — 2026-10-31

### Fixed
- The subtitle in the main window ("v5.24 · Report with metadata") no longer wraps onto a second
  line. The window minimum width in vertical layout has been increased to 780px to accommodate
  the title, subtitle, and action buttons on a single line.

### Changed
- Restored the original subtitle text (no forced line break).

---

## [5.23] — 2026-10-31

### Changed
- Shortened the subtitle text (from "HTML report with metadata" to "Report with metadata") to
  reduce the chance of line wrapping in the window header.

---

## [5.22] — 2026-10-31

### Fixed
- Fixed a crash (`AttributeError: 'App' object has no attribute 'pie'`) introduced in the 5.21
  update check. The update notification is now correctly created inside `costruisci()` and
  persists across window redraws (language or layout changes).

---

## [5.21] — 2026-10-31

### Added
- Automatic update check: on startup, the program queries the GitHub Releases API to see if a
  newer version is available. If yes, a discreet clickable link appears at the bottom of the
  window: "⬆ Version 5.21 is available! Click here to download it." The check runs silently
  in the background and is ignored if there is no internet connection or the repository has
  no releases yet.

---

## [5.20] — 2026-10-31

### Fixed
- Added a fallback to calculate the video bitrate when ffprobe does not provide it directly.
  The value is now estimated by subtracting the total audio bitrate from the overall file
  bitrate (total - audio). This fixes empty video bitrate columns for files where the
  container does not store the video track bitrate.

### Changed
- Cache format bumped to version 2 to force a re-scan of all files and populate the new
  bitrate values.

---

## [5.19] — 2026-10-31

### Added
- **Help button** next to the search bar in the HTML report (the `?` button). Clicking it opens
  a modal window listing all advanced search operators with examples (`ext:`, `size:`, `year:`,
  `res:`, `hdr:`, `durata:`).

---

## [5.18] — 2026-10-31

### Fixed
- Advanced search in the HTML report now works correctly. Two bugs were fixed:
  - A double backslash (`\\s+` instead of `\s+`) prevented the query from being split into tokens.
  - The `input` event handler was not calling `parseAvanzato()`, so advanced operators were
    ignored.

---

## [5.17] — 2026-10-31

### Fixed
- Made the `checkAdv` function much more robust for size filters. It now accepts spaces
  (`10 GB`), case variations (`10gb`), and both decimal separators (`10,5` or `10.5`).

---

## [5.16] — 2026-10-31

### Fixed
- Fixed the empty table issue on report open (introduced in 5.15). The search parsing now handles
  an empty query correctly and does not hide all files.
- Added a safety check in `checkAdv` to return `true` if the advanced filter object is empty.

---

## [5.15] — 2026-10-31

### Added
- **Advanced search** in the HTML report: the search bar now supports operators to filter
  results precisely:
  - `ext:` (e.g. `ext:mkv`, `ext:flac,mp3`) — filter by file extension
  - `size:` (e.g. `size:>10GB`, `size:<500MB`) — filter by file size
  - `year:` (e.g. `year:2020`, `year:>2015`) — filter by tag year
  - `res:` (e.g. `res:4k`, `res:1080`) — filter by video resolution
  - `hdr:` (e.g. `hdr:sì`, `hdr:no`) — filter by HDR presence
  - `durata:` (e.g. `durata:>60`) — filter by duration in minutes
  Operators can be combined with plain text (e.g. `Dragon res:4k`).

---

## [5.14] — 2026-10-31

### Changed
- The "Copy path" option in the report HTML now copies the full absolute file path (e.g.
  `C:\Users\Name\Desktop\Folder\CD1\file.flac`), making it much easier to paste directly
  into File Explorer or a terminal. The base folder path is embedded once into the HTML with
  zero impact on performance or report size.

---

## [5.13] — 2026-10-31

### Fixed
- Fixed an issue where "Copy path" in the report HTML would copy only the file name if the
  "Group by subfolder" option was disabled. The relative path is now always calculated and
  included in the report data.

---

## [5.12] — 2026-10-31

### Added
- **Context menu** in the HTML report: right-click on a file name to copy the file name or
  the full path directly to the clipboard. The context menu also shows a small confirmation
  ("Copied!") for a few seconds.

---

## [5.11] — 2026-10-31

### Fixed
- The program no longer prompts "unsaved changes" on close if the user has not actually
  modified anything. The `modifiche_non_salvate` flag is now set only by real user actions
  (column changes, "All"/"None" buttons, etc.) and not by automatic interface redraws.

---

## [5.10] — 2026-10-31

### Fixed
- Fixed a crash (`KeyError: 'sistema'`) when the "System theme" was selected. The logo
  loading in `costruisci()` now correctly uses `self.tema_effettivo` instead of `self.tema`.

---

## [5.9] — 2026-10-31

### Added
- **System theme**: a new "System theme" option in the Settings menu that follows the Windows
  light/dark mode setting.
- **Default columns button**: in the "Report columns" section, a new "Default" button restores
  the default columns for the active profile type (General, Music or Movie).

## [5.8] — 2026-10-31

### Fixed
- Fixed a crash (`KeyError: 'profilo_generale_nome'`) that occurred when opening the profile menu
  after the 5.7 update. The missing translation keys have been correctly added for both Italian
  and English.

---

## [5.7] — 2026-10-31

### Added
- The default "Generale" profile is now displayed as "General" when the interface language is
  set to English. The underlying profile name in `config.json` remains unchanged for compatibility.

---

## [5.6] — 2026-10-31

### Fixed
- Saving a profile from the "Edit profile" or "Exclusions" dialogs now also commits any pending
  column selections, so the "unsaved changes" prompt no longer appears unnecessarily when
  closing the program afterwards.

---

## [5.5] — 2026-10-31

### Changed
- The program now prompts for confirmation before closing if there are unsaved changes
  (including column selections). "Yes" saves, "No" discards, "Cancel" keeps the program open.
- Background silent saves have been removed: modifications are only written to `config.json`
  when the user confirms on exit, or when generating a report (which inherently uses the
  current settings).
- Column selections and the "All"/"None" buttons mark the profile as modified, so the
  confirmation dialog appears when needed.

---

## [5.4] — 2026-10-31

### Fixed
- Profile column selections and options are now saved automatically when closing the program,
  even if no other action (like generating a report or switching profile) was performed.
- Added a one-time informational dialog for users upgrading from older versions, explaining
  that "Include images" is now a session-only option and no longer saved in the profile.

### Changed
- Removed the unused `includi_immagini` field from new profiles.
- Removed the unused `profilo_etichetta` ("Profile:") translation key.

---

## [5.3] — 2026-10-31

### Changed
- The active profile name in the profile combobox is now displayed in **bold**.
- The source folder combobox now uses the same larger font (Segoe UI 12) both when closed and
  when open, improving readability.

---

## [5.2] — 2026-10-31

### Changed
- The profile combo box no longer repeats the word "Profile:" — it shows only the profile name,
  since the section header already says "PROFILE".

---
## [5.0z13] — 2026-10-31   →   ## [5.1] — 2026-10-31
## [5.0z13] — 2026-10-31

### Changed
- One-time `config.json` cleanup: on first launch of this version, obsolete or unused fields are
  removed (`includi_immagini` from profiles, `migrazione_3_9g`, `migrazione_3_9t`,
  `cartella_scansione`, `colonne`). The configuration file stays cleaner and consistent with
  the current behavior.

---

## [5.0z12] — 2026-10-31

### Fixed
- Removed the duplicated "folder" block in the **New profile** dialog (two "Use current folder"
  checkboxes, two folder fields, two "Browse..." buttons).
- Removed the duplicated `nuovo_usa_corrente` key in Italian and English text files.
- Removed dead code in `_cambia_lingua_menu`.
- Fixed the `VERSIONE` constant (it was still `5.0z4` despite the file name).

### Changed
- `includi_immagini` is no longer written to `config.json` by `avvia()`.
- `_versione_cache()` now includes `ESTENSIONI_IMMAGINE`: if image behavior changes, the scan cache
  is invalidated automatically.

---

## [5.0z11] — 2026-10-31

### Added
- Bitrate formatting in the HTML report for video and audio:
  - below **10,000 kbps** → `kbps` with thousand separator (e.g. `9,122 kbps` in English,
    `9.122 kbps` in Italian);
  - above **10,000 kbps** → `Mb/s` with two decimals (e.g. `16.50 Mb/s`).
- `SOGLIA_MBPS` constant to easily change the threshold.

---

## [5.0z10] — 2026-10-31

### Changed
- **"Include images"** is now a **session option**: it applies to the current scan only and is no
  longer remembered in the profile. On next launch it starts unchecked.
- The flag no longer modifies the profile's `estensioni_escluse`: image inclusion is handled at
  scan time via `_esclusioni_attive`, without touching the saved configuration.

---

## [5.0z9] — 2026-10-31

### Changed
- Checkbox label renamed from **"Includi le immagini nel report"** to **"Includi immagini"**
  (Italian) and from **"Include images in the report"** to **"Include images"** (English).

---

## [5.0z8] — 2026-10-31

### Changed
- **Profile** menu order: **New profile...** first, then **Edit profile...**, then **Delete profile**.

---

## [5.0z7] — 2026-10-31

### Added
- In the **New profile** dialog you can now choose the new profile's folder:
  - **"Use current folder"** checkbox (checked by default if a folder is already selected);
  - folder field + **"Browse..."** button to pick a different one.
- The main folder field is no longer cleared when creating a profile: it shows the folder chosen
  for the new profile.

---

## [5.0z6] — 2026-10-31

### Added
- **"Open configuration folder"** entry in the **Settings** menu: opens File Explorer (or the file
  manager) on `%APPDATA%\MediaDirLister\` where `config.json`, cache and logs live.

### Fixed
- `VERSIONE` constant aligned with the file name (`5.0z6`), which was lagging behind.

---

## [5.0z5] — 2026-10-31

### Fixed
- All image extensions are now excluded by default: added `gif`, `bmp`, `tif`, `tiff`, `webp`,
  `svg`, `heic`, `ico`, `raw`, `cr2`, `nef`, `arw`, `psd` to `ESTENSIONI_ESCLUSE`.
  Previously only `jpg`, `jpeg`, `png`, `avif` were excluded, while the others still appeared in
  the report.
- Updated `includi_immagini_nota` (Italian and English) to reflect the new behavior: without the
  option all images are excluded, with the option all are included.

---

## [5.0z4] and earlier

Earlier versions are documented in the project's historical repository. Main features from
previous versions include: profiles with separate exclusions and columns, SQLite scan cache,
light/dark/color themes, vertical and horizontal layouts, HTML report with filters and summary,
Italian/English languages.

---

## Legend

- **Added** — new features.
- **Changed** — changes in existing functionality.
- **Deprecated** — features that will be removed in future.
- **Removed** — removed features.
- **Fixed** — bug fixes.
- **Security** — vulnerability fixes.

---

## Updating

1. Download the new `media_directory_lister_v5.0zN.py`.
2. Replace the previous file (you can keep a copy of the old one).
3. **Do not delete** `config.json`: it is read and updated automatically. The first launch of a new
   version creates a backup `config.json.bak_<previous version>`.
4. If you use FFmpeg, keep `ffprobe` in the program folder or in `PATH`.

---

## Reporting issues

- Email: roby77dopa@gmail.com
- GitHub: https://github.com/Roby77ita/Media-Directory-Lister
