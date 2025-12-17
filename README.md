# CD Burning Automation

Automated workflow for downloading Spotify playlists, converting them to Red Book standard WAV, and burning them to CD using ImgBurn.

## Features
- **Batch Processing**: Queue multiple playlists and customers.
- **Auto-Download**: Uses `spotdl` to fetch audio.
- **Format Conversion**: Converts audio to 44.1kHz/16-bit WAV (CD Standard).
- **CUE Sheet Generation**: Creates metadata for CD-TEXT (Artist/Title on car displays).
- **Tracklist Generation**: Creates a text file for CD case inserts.
- **ImgBurn Integration**: Automatically launches burning process.

## Requirements
- Python 3.x
- FFmpeg (Must be added to System PATH)
- ImgBurn

## Installation

1. Install Python dependencies:
   ```bash
   pip install spotdl pydub
   ```

2. Configuration:
   - Ensure `ImgBurn.exe` is at `C:\Program Files (x86)\ImgBurn\ImgBurn.exe` or update `IMGBURN_PATH` in the script.
   - Output directory is set to `C:\Users\monol\wkdir\monosound\cd`.

## Usage

1. Run the script:
   ```bash
   python mono_auto.py
   ```
2. Enter Spotify Playlist Link (script checks duration automatically).
3. Enter Customer Name.
4. Repeat for multiple orders or press Enter on an empty link to proceed.
5. The script will download and convert all orders.
6. Insert blank CDs when prompted to burn.

## Output
For each order, a folder is created in the `cd` directory containing:
- Converted WAV files
- `burn_plan.cue` (for ImgBurn)
- `tracklist.txt` (for printing)
