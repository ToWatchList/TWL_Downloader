#!/usr/bin/env python3
"""
Direct test of SponsorBlock functionality with yt-dlp using different configurations
"""

import yt_dlp
import tempfile
import os

def test_sponsorblock_chapters():
    video_url = "https://www.youtube.com/watch?v=Nq-Faw_ENEQ"

    with tempfile.TemporaryDirectory() as temp_dir:
        output_template = os.path.join(temp_dir, "test-%(id)s.%(ext)s")

        # Try configuration that should create chapters from SponsorBlock
        ydl_opts = {
            "format": "best[height<=720]",  # Lower quality for faster download
            "outtmpl": output_template,
            "embed_chapters": True,
            #"writeautomaticsub": True,
            "postprocessors": [
                {
                    "key": "SponsorBlock",
                    "categories": ["sponsor"],
                    "when": "pre_process",
                },
                {
                    "key": "ModifyChapters",
                    # This should create chapters from the SponsorBlock data
                    # but NOT remove the segments
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                    "add_chapters": True,
                },
            ],
        }

        print("Testing SponsorBlock chapter creation...")
        print(f"Video URL: {video_url}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Check chapters
            files = [f for f in os.listdir(temp_dir) if f.endswith(('.mkv', '.mp4', '.webm'))]

            for file in files:
                video_path = os.path.join(temp_dir, file)
                print(f"\nChecking chapters in: {video_path}")

                import subprocess
                import json

                result = subprocess.run([
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_chapters", video_path
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    chapters_info = json.loads(result.stdout)
                    chapters = chapters_info.get("chapters", [])
                    print(f"Found {len(chapters)} chapters")

                    for i, chapter in enumerate(chapters):
                        start = float(chapter.get("start_time", 0))
                        end = float(chapter.get("end_time", 0))
                        title = chapter.get("title", f"Chapter {i+1}")
                        print(f"  Chapter {i+1}: {start:.3f}s to {end:.3f}s - '{title}'")

                        # Check if this matches the expected sponsor segment
                        if 275 <= start <= 285:  # Around 4:39
                            print(f"    -> This looks like the sponsor segment!")
                else:
                    print(f"ffprobe failed: {result.stderr}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_sponsorblock_chapters()
