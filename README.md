# Media Directory Lister (v4.0h)

**Media Directory Lister** is a lightweight Python desktop application with a graphical user interface (GUI). It scans local folders or network drives to generate an **interactive, elegant, and detailed HTML report** featuring comprehensive metadata for all audio and video files found.

### 🚀 Key Features

- **Advanced Media Analysis**: Powered by `ffprobe` to extract deep metadata from video and audio files (resolution, codecs, multiple audio tracks with language, channels, bitrate, color depth, HDR, and Dolby Vision).
- **Interactive HTML Report**: The generated report includes:
  - Instant dynamic filters by file type (Audio/Video), resolution (SD, HD, 4K), HDR, or modified date.
  - Real-time text search.
  - Summary statistics (total space used, most frequent codecs, total artists/albums).
  - Subfolder grouping and pagination support.
- **CSV Export**: Export filtered data to an Excel-compatible CSV file with a single click.
- **Modern GUI with Themes**: Features adjustable layouts (vertical/horizontal) and full **Dark and Light theme** support for both the app and the HTML report.
- **Profile Management**: Create custom profiles (e.g., General, Music, Movies) to save specific column layouts and exclusion lists (to ignore `.txt`, `.log`, or artwork files).
- **SQLite Caching**: Dramatically speeds up subsequent scans by re-analyzing only new or modified files.

### 🛠️ Requirements

- **Python 3.x** (with `tkinter` support).
- **FFmpeg/FFprobe**: The `ffprobe` binary must be placed in the program folder or added to your system PATH.
