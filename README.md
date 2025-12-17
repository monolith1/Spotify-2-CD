# CD Burning Automation

Automated workflow for downloading Spotify playlists, converting them to Red Book standard WAV, and burning them to CD using ImgBurn.

## Features
- **Batch Processing**: Queue multiple playlists.
- **Auto-Download**: Uses `spotdl` to fetch audio.
- **Smart Retry**: Automatically retries failed downloads.
- **Integrity Check**: Verifies audio duration against metadata to ensure correct tracks.
- **Format Conversion**: Converts audio to 44.1kHz/16-bit WAV (CD Standard).
- **CUE Sheet Generation**: Creates metadata for CD-TEXT (Artist/Title on car displays).
- **Tracklist Generation**: Creates a text file for CD case inserts.
- **ImgBurn Integration**: Automatically launches burning process.

## Requirements
- Python 3.x
- FFmpeg (Must be added to System PATH)
- ImgBurn
- **macOS Users**: `cdrdao` (via Homebrew)

## Installation

1. Install Python dependencies:
   ```bash
   pip install spotdl pydub
   ```

   **Windows**:
   - Install FFmpeg: `winget install Gyan.FFmpeg`
   - Ensure ImgBurn is installed.

   **macOS**: Install system tools: `brew install ffmpeg cdrdao`

2. Configuration:
   - Ensure `ImgBurn.exe` is at `C:\Program Files (x86)\ImgBurn\ImgBurn.exe` or update `IMGBURN_PATH` in the script.
   - Output directory is the `cd` folder in the script's location.

## Usage

1. Run the script:
   ```bash
   python spotify2cd.py
   ```
2. Enter Spotify Playlist Link (script checks duration automatically).
3. Enter CD Name.
4. Repeat for multiple playlists or press Enter on an empty link to proceed.
5. The script will download and convert all playlists.
6. Insert blank CDs when prompted to burn.

## Output
For each playlist, a folder is created in the `cd` directory containing:
- Converted WAV files
- `burn_plan.cue` (for ImgBurn)
- `tracklist.txt` (for printing)
