# -*- coding: utf-8 -*-
"""
Created on Tue Sep 29 10:05:20 2026

@author: sr49099
"""
"""
PUZZ-ONLY Batch Local Video Transcriber — Spanish + English

This script ONLY processes videos containing "_PUZZ_" in the filename.

Example files:
    BRCH-307-25-244_PUZZ_C1.MP4
    BRCH-307-25-244_PUZZ_C1.LRV

For each PUZZ video, the script will:
1. Find PUZZ video files in the selected folder
2. Transcribe each video with Whisper
3. Save a separate *_transcript.txt file
4. Extract ID, task, and camera from the filename
5. Save metadata/status information to video_metadata_log.txt
6. Save PUZZ videos detected as neither English nor Spanish
   to non_english_or_spanish_files.txt
7. Automatically convert LRV files to a temporary MP4 for Whisper

First-time setup:
    pip install -U openai-whisper
    winget install Gyan.FFmpeg
"""

import os
import subprocess
import tempfile
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime


# ============================================================
# SETTINGS
# ============================================================

MODEL_NAME = "medium"

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
    ".wmv",
    ".lrv",
}

# Only process files containing "_PUZZ_" in the filename
TARGET_TASK = "PUZZ"

# Whisper language codes/names accepted as English or Spanish
ALLOWED_LANGUAGES = {
    "en",
    "es",
    "english",
    "spanish",
}


# ============================================================
# CHECK WHISPER + FFMPEG
# ============================================================

def install_check():
    missing = []

    try:
        import whisper
    except ImportError:
        missing.append("openai-whisper")

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        missing.append("FFmpeg")

    if missing:
        msg = (
            "Missing required software:\n\n"
            + "\n".join(f"• {x}" for x in missing)
            + "\n\n"
            "Install them first:\n"
            "1. Open Command Prompt\n"
            "2. Run: pip install -U openai-whisper\n"
            "3. Run: winget install Gyan.FFmpeg\n"
            "4. Restart your computer if necessary."
        )

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror("Setup needed", msg)
        root.destroy()
        return None

    return whisper


# ============================================================
# CHOOSE FOLDER
# ============================================================

def choose_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(
        title="Select the folder containing the PUZZ videos"
    )

    root.destroy()
    return folder


# ============================================================
# GET PUZZ VIDEOS
# ============================================================

def get_puzz_videos(folder):
    videos = []

    for filename in os.listdir(folder):
        full_path = os.path.join(folder, filename)

        # Ignore folders
        if not os.path.isfile(full_path):
            continue

        extension = os.path.splitext(filename)[1].lower()

        # Only supported video files
        if extension not in VIDEO_EXTENSIONS:
            continue

        # Only filenames containing _PUZZ_
        filename_upper = filename.upper()

        if "_PUZZ_" not in filename_upper:
            continue

        videos.append(full_path)

    videos.sort(key=lambda x: os.path.basename(x).lower())

    return videos


# ============================================================
# PARSE PUZZ FILENAME
# ============================================================

def parse_filename(video_path):
    filename = os.path.basename(video_path)
    name = os.path.splitext(filename)[0]

    parts = name.split("_")

    # Expected:
    # BRCH-307-25-244_PUZZ_C1
    #
    # parts[0] = BRCH-307-25-244
    # parts[1] = PUZZ
    # parts[2] = C1

    if len(parts) >= 3:
        video_id = parts[0]
        task = parts[1]
        camera = parts[2]
    else:
        video_id = "UNKNOWN"
        task = "PUZZ"
        camera = "UNKNOWN"

    return video_id, task, camera


# ============================================================
# PREPARE LRV FOR WHISPER
# ============================================================

def prepare_media_for_whisper(video_path):
    extension = os.path.splitext(video_path)[1].lower()

    # Normal video files can be used directly
    if extension != ".lrv":
        return video_path, None

    temp_dir = tempfile.mkdtemp(prefix="whisper_lrv_")
    converted_path = os.path.join(temp_dir, "converted.mp4")

    print()
    print("LRV detected.")
    print("Converting LRV to temporary MP4...")
    print()

    # First attempt: copy video and convert audio to AAC
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-map",
        "0:v:0?",
        "-map",
        "0:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        converted_path,
    ]

    try:
        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            print("Fast LRV conversion failed.")
            print("Retrying with H.264...")

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-map",
                "0:v:0?",
                "-map",
                "0:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                converted_path,
            ]

            subprocess.run(cmd, check=True)

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return converted_path, temp_dir


# ============================================================
# CLEAN UP TEMPORARY FILE
# ============================================================

def cleanup_temp_media(temp_dir):
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# LANGUAGE HELPERS
# ============================================================

def is_allowed_language(language):
    if not language:
        return False

    return language.strip().lower() in ALLOWED_LANGUAGES


# ============================================================
# MAIN
# ============================================================

def main():

    whisper = install_check()

    if whisper is None:
        return

    folder = choose_folder()

    if not folder:
        return

    print("=" * 70)
    print("PUZZ-ONLY BATCH VIDEO TRANSCRIPTION")
    print("=" * 70)
    print(f"Folder: {folder}")
    print()

    # --------------------------------------------------------
    # Find ONLY PUZZ videos
    # --------------------------------------------------------

    videos = get_puzz_videos(folder)

    print(f"Found {len(videos)} PUZZ video(s).")
    print()

    # --------------------------------------------------------
    # Create report paths
    # --------------------------------------------------------

    log_path = os.path.join(
        folder,
        "PUZZ_video_metadata_log.txt"
    )

    other_language_log_path = os.path.join(
        folder,
        "PUZZ_non_english_or_spanish_files.txt"
    )

    # --------------------------------------------------------
    # Create language report
    # --------------------------------------------------------

    with open(
        other_language_log_path,
        "w",
        encoding="utf-8"
    ) as report:

        report.write(
            "PUZZ VIDEOS DETECTED AS NON-ENGLISH OR NON-SPANISH\n"
        )
        report.write(
            "==================================================\n\n"
        )
        report.write(f"Folder: {folder}\n")
        report.write(f"Checked: {datetime.now()}\n\n")

        report.write(
            "Only English (en) and Spanish (es) are considered "
            "allowed languages.\n\n"
        )

        if not videos:
            report.write(
                "No PUZZ video files were found.\n"
            )

    # --------------------------------------------------------
    # No videos
    # --------------------------------------------------------

    if not videos:

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        messagebox.showwarning(
            "No PUZZ videos found",
            "No PUZZ video files were found in this folder."
        )

        root.destroy()

        return

    # --------------------------------------------------------
    # Load Whisper model ONCE
    # --------------------------------------------------------

    print("Loading Whisper model...")
    print(f"Model: {MODEL_NAME}")
    print()

    model = whisper.load_model(MODEL_NAME)

    print("Whisper model loaded.")
    print()

    # --------------------------------------------------------
    # Open logs
    # --------------------------------------------------------

    with open(
        log_path,
        "w",
        encoding="utf-8"
    ) as log, open(
        other_language_log_path,
        "a",
        encoding="utf-8"
    ) as language_report:

        log.write("PUZZ VIDEO METADATA LOG\n")
        log.write("=======================\n\n")
        log.write(f"Folder: {folder}\n")
        log.write(f"Started: {datetime.now()}\n\n")

        other_language_count = 0

        # ----------------------------------------------------
        # Process every PUZZ video
        # ----------------------------------------------------

        for index, video_path in enumerate(
            videos,
            start=1
        ):

            filename = os.path.basename(video_path)

            print()
            print("=" * 70)
            print(
                f"PUZZ VIDEO {index} OF {len(videos)}"
            )
            print("=" * 70)

            print(f"Filename: {filename}")

            # -----------------------------------------------
            # Extract metadata
            # -----------------------------------------------

            video_id, task, camera = parse_filename(
                video_path
            )

            print(f"ID:     {video_id}")
            print(f"Task:   {task}")
            print(f"Camera: {camera}")

            # -----------------------------------------------
            # Determine transcript path
            # -----------------------------------------------

            transcript_path = (
                os.path.splitext(video_path)[0]
                + "_transcript.txt"
            )

            # -----------------------------------------------
            # Skip existing transcript
            # -----------------------------------------------

            if os.path.exists(transcript_path):

                print()
                print("Transcript already exists.")
                print("Skipping transcription.")

                status = (
                    "SKIPPED — transcript already exists"
                )

            else:

                temp_dir = None

                try:

                    # ---------------------------------------
                    # Prepare media
                    # ---------------------------------------

                    media_path, temp_dir = (
                        prepare_media_for_whisper(
                            video_path
                        )
                    )

                    # ---------------------------------------
                    # Transcribe
                    # ---------------------------------------

                    print()
                    print("Transcribing...")

                    result = model.transcribe(
                        media_path,
                        task="transcribe",
                        fp16=False,
                        verbose=True,
                    )

                    detected_language = result.get(
                        "language",
                        "unknown"
                    )

                    text = result["text"].strip()

                    print(
                        f"Detected language: "
                        f"{detected_language}"
                    )

                    # ---------------------------------------
                    # Check language
                    # ---------------------------------------

                    if not is_allowed_language(
                        detected_language
                    ):

                        other_language_count += 1

                        language_report.write(
                            f"Filename: {filename}\n"
                            f"Detected language: "
                            f"{detected_language}\n"
                            f"Transcript: "
                            f"{os.path.basename(transcript_path)}"
                            "\n\n"
                        )

                        language_report.flush()

                    # ---------------------------------------
                    # Save transcript
                    # ---------------------------------------

                    with open(
                        transcript_path,
                        "w",
                        encoding="utf-8"
                    ) as transcript_file:

                        transcript_file.write(text)

                    status = "COMPLETED"

                    print()
                    print("Transcription complete.")
                    print(
                        f"Saved to: {transcript_path}"
                    )

                except Exception as e:

                    status = (
                        "ERROR — " + str(e)
                    )

                    print()
                    print("ERROR:")
                    print(str(e))

                finally:

                    cleanup_temp_media(temp_dir)

            # -----------------------------------------------
            # Write metadata log
            # -----------------------------------------------

            log.write(
                f"ID: {video_id}\n"
            )

            log.write(
                f"Task: {task}\n"
            )

            log.write(
                f"Camera: {camera}\n"
            )

            log.write(
                f"Filename: {filename}\n"
            )

            log.write(
                f"Status: {status}\n"
            )

            log.write(
                f"Transcript: "
                f"{os.path.basename(transcript_path)}\n"
            )

            log.write("\n")

            log.flush()

        # ----------------------------------------------------
        # Finish language report
        # ----------------------------------------------------

        language_report.write(
            "----------------------------------\n"
        )

        language_report.write(
            "Total PUZZ videos detected as other languages: "
            f"{other_language_count}\n"
        )

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("ALL PUZZ VIDEOS PROCESSED")
    print("=" * 70)
    print()

    print("Metadata log saved to:")
    print(log_path)

    print()

    print("Other-language report saved to:")
    print(other_language_log_path)

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    open_folder = messagebox.askyesno(
        "PUZZ transcription complete",

        f"Finished processing {len(videos)} PUZZ video(s).\n\n"

        f"Metadata log:\n{log_path}\n\n"

        f"Other languages:\n"
        f"{other_language_log_path}\n\n"

        "Would you like to open the folder?"
    )

    root.destroy()

    if open_folder:

        subprocess.Popen(
            [
                "explorer",
                "/select,",
                os.path.normpath(log_path),
            ]
        )


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    main()
