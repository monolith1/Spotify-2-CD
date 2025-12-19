import os
import subprocess
import datetime
import time
import json
import re
from pathlib import Path
from pydub import AudioSegment
import platform
import unicodedata

# --- CONFIGURATION ---
# Path to ImgBurn executable
IMGBURN_PATH = r"C:\Program Files (x86)\ImgBurn\ImgBurn.exe"

# Base directory for CD output folders
BASE_CD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cd")

# Burning Speed: 'MAX', '1x', '2x', '4x', etc. 
# Lower (4x or 8x) is recommended for high-fidelity Audio CDs to reduce jitter.
BURN_SPEED = "8x" 

# Target Drive (Optional). If None, ImgBurn picks the first available writer.
# Example: DRIVE_LETTER = "D:"
DRIVE_LETTER = None 

def check_playlist_duration(link):
    """
    Uses spotdl to fetch metadata and calculate total duration without downloading audio.
    Returns total seconds or None if failed.
    """
    print("  [...] Verifying playlist duration...")
    temp_file = "temp_duration_check.spotdl"
    
    # spotdl save <link> --save-file <file>
    cmd = ["spotdl", "save", link, "--save-file", temp_file]
    
    try:
        # Run quietly to avoid cluttering console
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if not os.path.exists(temp_file):
            return None

        with open(temp_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        os.remove(temp_file)
        
        # data is a list of track objects
        total_seconds = sum(track.get('duration', 0) for track in data)
        return total_seconds
        
    except Exception:
        return None

def get_jobs():
    jobs = []
    print("--- CD Auto-Burn Workflow ---")
    print("Enter playlist details. Leave 'Link' empty to finish.")
    
    while True:
        print(f"\n[Job #{len(jobs) + 1}]")
        link = input("Spotify Playlist Link: ").strip()
        if not link:
            break
            
        # Check duration immediately
        total_seconds = check_playlist_duration(link)
        if total_seconds:
            minutes = total_seconds / 60
            print(f"  -> Total Duration: {minutes:.1f} minutes")
            if minutes > 80:
                print("  [!] WARNING: Playlist exceeds 80 minutes (Standard CD capacity).")
                confirm = input("      Continue anyway? (y/n): ").strip().lower()
                if confirm == 'n':
                    continue

        cd_name = input("CD Name: ").strip()
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        folder_name = f"cd_{date_str}_{cd_name}"
        full_path = os.path.join(BASE_CD_DIR, folder_name)
        jobs.append((link, full_path, cd_name))
    return jobs

def download_playlist(link, output_folder):
    print(f"\n[1/5] Downloading Playlist...")
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # 1. Get Expected Track Count
    print("  [...] Fetching playlist metadata...")
    expected_count = 0
    metadata_tracks = []
    temp_file = f"temp_{int(time.time())}.spotdl"
    
    try:
        subprocess.run(["spotdl", "save", link, "--save-file", temp_file], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_file):
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                expected_count = len(data)
                metadata_tracks = data
            os.remove(temp_file)
    except Exception:
        pass # Proceed without validation if metadata fetch fails

    if expected_count > 0:
        print(f"  [...] Expecting {expected_count} tracks.")

    cmd = [
        "spotdl", link, 
        "--output", f"{output_folder}/{{list-position}} {{artist}} - {{title}}.{{output-ext}}"
    ]
    
    max_retries = 3
    supported_ext = {'.mp3', '.m4a', '.ogg', '.opus', '.flac', '.wav'}

    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"  [...] Retry attempt {attempt}/{max_retries}...")
            subprocess.run(cmd, check=True)
            
            # Validation
            if expected_count > 0:
                files = [f for f in Path(output_folder).iterdir() if f.suffix.lower() in supported_ext]
                actual_count = len(files)
                
                if actual_count >= expected_count:
                    # Verify Durations
                    print("  [...] Verifying audio integrity...")
                    for f in files:
                        try:
                            actual = AudioSegment.from_file(str(f)).duration_seconds
                            
                            # Fuzzy match filename against metadata to find the correct track info
                            match_found = False
                            candidate_duration = 0
                            f_clean = re.sub(r'[^a-z0-9]', '', f.stem.lower())
                            
                            for track in metadata_tracks:
                                t_artist = re.sub(r'[^a-z0-9]', '', str(track.get('artist', '')).lower())
                                t_name = re.sub(r'[^a-z0-9]', '', str(track.get('name', '')).lower())
                                
                                # Check if artist and title are present in filename
                                if t_artist in f_clean and t_name in f_clean:
                                    expected = track.get('duration', 0)
                                    if abs(actual - expected) < 10: # 10s tolerance
                                        match_found = True
                                        break
                                    candidate_duration = expected
                            
                            if not match_found and candidate_duration > 0:
                                print(f"  [!] WARNING: Duration mismatch for '{f.name}'")
                                print(f"      Expected: {int(candidate_duration)}s, Actual: {int(actual)}s")
                        except Exception:
                            pass
                    return True
                else:
                    print(f"  [!] Warning: Found {actual_count}/{expected_count} files.")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
            else:
                return True

        except subprocess.CalledProcessError:
            print(f"  [!] spotdl process failed on attempt {attempt}.")
            if attempt < max_retries:
                time.sleep(2)
                continue
        except Exception as e:
            print(f"Download Error: {e}")
            return False
            
    print("  [X] Download incomplete after retries.")
    return False

def convert_to_wav(folder_path):
    """
    Converts to 44.1kHz/16-bit WAV. 
    WAV is preferred over FLAC for the actual burning step because 
    it requires no external codecs in ImgBurn.
    """
    print("\n[2/5] Converting to Red Book WAV (44.1kHz / 16-bit)...")
    folder = Path(folder_path)
    supported_ext = {'.mp3', '.m4a', '.ogg', '.opus', '.flac'}
    wav_files = []

    for file_path in sorted(folder.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in supported_ext:
            if file_path.suffix.lower() == '.wav':
                # Already WAV? Ensure filename is safe.
                original_stem = file_path.stem
                safe_stem = unicodedata.normalize('NFKD', original_stem).encode('ascii', 'ignore').decode('ascii')
                safe_stem = re.sub(r'["]', '', safe_stem).strip()
                
                if original_stem != safe_stem:
                    new_path = file_path.with_name(safe_stem).with_suffix('.wav')
                    os.rename(file_path, new_path)
                    wav_files.append(new_path)
                    print(f"  Renamed: {file_path.name} -> {new_path.name}")
                else:
                    wav_files.append(file_path)
                continue
                
            try:
                audio = AudioSegment.from_file(str(file_path))
                
                # Enforce CD Quality
                audio = audio.set_frame_rate(44100)
                audio = audio.set_sample_width(2) # 16-bit
                audio = audio.set_channels(2)
                
                # Sanitize filename for ImgBurn compatibility (ASCII only)
                original_stem = file_path.stem
                safe_stem = unicodedata.normalize('NFKD', original_stem).encode('ascii', 'ignore').decode('ascii')
                safe_stem = re.sub(r'["]', '', safe_stem).strip()
                
                target_filename = file_path.with_name(safe_stem).with_suffix('.wav')
                audio.export(str(target_filename), format="wav")
                
                # Delete original
                os.remove(file_path)
                wav_files.append(target_filename)
                print(f"  Converted: {file_path.name} -> {target_filename.name}")
                
            except Exception as e:
                print(f"  Failed: {file_path.name} ({e})")
    
    return wav_files

def generate_cue_sheet(folder_path, cd_name):
    """
    Creates a .cue file which maps the WAV files to CD tracks.
    This enables CD-TEXT (Song titles on car displays).
    """
    print("\n[3/5] Generating CUE Sheet...")
    folder = Path(folder_path)
    
    # Robust sort by track number (assumes "01 - Artist..." format)
    def get_track_number(file_path):
        try:
            return int(file_path.name.split(' - ')[0])
        except (ValueError, IndexError):
            return float('inf')
    
    wav_files = sorted(list(folder.glob("*.wav")), key=get_track_number)
    cue_path = folder / "burn_plan.cue"
    
    with open(cue_path, "w", encoding="utf-8") as cue:
        # Album Metadata
        cue.write(f'TITLE "{cd_name}"\n')
        cue.write(f'PERFORMER ""\n')
        
        for i, wav in enumerate(wav_files):
            track_num = i + 1
            # Try to parse Artist/Title from filename "01 - Artist - Title.wav"
            # Fallback to filename if parsing fails
            clean_name = wav.stem
            parts = clean_name.split(' - ')
            
            artist = "Unknown"
            title = clean_name
            if len(parts) >= 3:
                artist = parts[1]
                title = " - ".join(parts[2:])
            
            # Write Track Entry
            cue.write(f'FILE "{wav.name}" WAVE\n')
            cue.write(f'  TRACK {track_num:02d} AUDIO\n')
            cue.write(f'    TITLE "{title}"\n')
            cue.write(f'    PERFORMER "{artist}"\n')
            cue.write(f'    INDEX 01 00:00:00\n')

    return cue_path

def generate_tracklist(folder_path, cd_name):
    """
    Generates a text file listing the tracks for the CD case.
    """
    folder = Path(folder_path)
    
    # Reuse sort logic
    def get_track_number(file_path):
        try:
            return int(file_path.name.split(' - ')[0])
        except (ValueError, IndexError):
            return float('inf')
    
    wav_files = sorted(list(folder.glob("*.wav")), key=get_track_number)
    txt_path = folder / "tracklist.txt"
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Mix for {cd_name}\n")
        f.write("-" * 40 + "\n")
        
        for wav in wav_files:
            clean_name = wav.stem
            parts = clean_name.split(' - ')
            
            if len(parts) >= 3:
                # parts[0] is track num, parts[1] is artist, rest is title
                track_num = parts[0]
                artist = parts[1]
                title = " - ".join(parts[2:])
                line = f"{track_num}. {artist} - {title}"
            else:
                line = clean_name
            
            f.write(f"{line}\n")
    
    print(f"  [+] Tracklist saved to: {txt_path.name}")

def burn_disc(cue_file_path):
    print(f"\n[4/5] Launching ImgBurn...")
    
    if platform.system() == "Darwin":
        # macOS Logic using cdrdao
        try:
            # Check if cdrdao is installed
            subprocess.run(["cdrdao", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("[-] 'cdrdao' not found. Please install it via Homebrew:")
            print("    brew install cdrdao")
            return

        cue_path = Path(cue_file_path)
        cwd = cue_path.parent
        
        # Parse speed (e.g., "8x" -> "8")
        speed = BURN_SPEED.lower().replace("x", "")
        speed_args = [] if speed == "max" else ["--speed", speed]

        # cdrdao command for macOS
        # --driver generic-mmc: Standard for most modern USB/SATA drives
        # --device IOCompactDiscServices: Auto-detects the first optical drive on macOS
        cmd = ["cdrdao", "write", "--eject", "--driver", "generic-mmc", "--device", "IOCompactDiscServices"] + speed_args + [cue_path.name]
        
        print(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
            print("\n[5/5] Burning Complete! Disc ejected.")
        except subprocess.CalledProcessError:
            print("\nBurning Failed. Ensure a blank CD is inserted.")
        return

    if not os.path.exists(IMGBURN_PATH):
        print(f"ERROR: ImgBurn not found at {IMGBURN_PATH}")
        print("Please install it or fix the path in the script.")
        return

    cue_abs_path = Path(cue_file_path).resolve()
    
    # ImgBurn CLI Flags
    # /MODE WRITE  -> Write mode
    # /SRC "..."   -> Source CUE file
    # /START       -> Start immediately
    # /EJECT       -> Eject when done
    # /CLOSE       -> Close program when done
    # /NOIMAGEDETAILS -> Don't ask for confirmation of details
    # /SPEED       -> Write speed
    
    cmd = [
        IMGBURN_PATH,
        "/MODE", "WRITE",
        "/SRC", str(cue_abs_path),
        "/SPEED", BURN_SPEED,
        "/START",
        "/EJECT",
        "/CLOSE",
        "/NOIMAGEDETAILS",
        "/WAITFORMEDIA" # Waits for you to insert a blank disc if none is present
    ]
    
    if DRIVE_LETTER:
        cmd.extend(["/DEST", DRIVE_LETTER])

    print("Waiting for ImgBurn to finish...")
    print("If you haven't inserted a CD, ImgBurn will wait for one.")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n[5/5] Burning Complete! Disc ejected.")
    except subprocess.CalledProcessError:
        print("\nBurning Failed. Check ImgBurn log.")

def main():
    jobs = get_jobs()
    if not jobs:
        return
    
    # Phase 1: Batch Download & Convert
    ready_to_burn = []
    
    for link, folder, cd_name in jobs:
        print(f"\n=== Processing: {folder} ===")
        # 1. Download
        if not download_playlist(link, folder):
            continue
            
        # 2. Convert to WAV (Standard for burning)
        convert_to_wav(folder)
        
        # 3. Create CUE Sheet
        cue_file = generate_cue_sheet(folder, cd_name)
        generate_tracklist(folder, cd_name)
        ready_to_burn.append((folder, cue_file))
    
    # Phase 2: Interactive Burn
    print(f"\n=== Batch Processing Complete. {len(ready_to_burn)} jobs ready. ===")
    
    for folder, cue_file in ready_to_burn:
        print(f"\n>>> Burning Job: {folder}")
        user_ready = input("Insert blank CD and press Enter (or 's' to skip, 'q' to quit): ")
        if user_ready.lower() == 'q':
            break
        if user_ready.lower() == 's':
            print("Skipped.")
            continue
        
        burn_disc(cue_file)

if __name__ == "__main__":
    main()