import os
import subprocess
import json
import glob
import re
def get_codec_and_audio_tracks(file):
    command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = json.loads(result.stdout)

    video_codec = None
    audio_codec = None

    for stream in output["streams"]:
        if stream["codec_type"] == "video":
            video_codec = stream["codec_name"]
        elif stream["codec_type"] == "audio":
            audio_codec = stream["codec_name"]

    return video_codec, audio_codec
def video_codec(file):
    command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = json.loads(result.stdout)

    video_codec = None

    for stream in output["streams"]:
        if stream["codec_type"] == "video":
            video_codec = stream["codec_name"]

    return video_codec
def convert_mkv_to_mp4(input_dir, output_dir, audio_track, separate_subtitles):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mkv_files = [file for file in os.listdir(input_dir) if file.endswith(".mkv")]
    if not separate_subtitles:
        for filename in mkv_files:
            mkv_file = os.path.join(input_dir, filename)
            codec = video_codec(mkv_file)
            mp4_file = os.path.join(output_dir, os.path.splitext(filename)[0] + ".mp4")
            ffmpeg_command = ["ffmpeg", "-i", mkv_file, "-map", "0:v:0", "-map", f"0:a:{audio_track}"]
            if codec == 'h264':
                ffmpeg_command.extend(["-c:v", "h264_nvenc", mp4_file])
            else:
                    ffmpeg_command.extend(["-c:v", "hevc_nvenc", mp4_file])
            subprocess.run(ffmpeg_command, cwd=input_dir, check=True)

    if separate_subtitles:
        for filename in mkv_files:
            mkv_file = os.path.join(input_dir, filename)
            mp4_file = os.path.join(output_dir, os.path.splitext(filename)[0] + ".mp4")
            subtitle_files = glob.glob(os.path.join(input_dir, "*.[as][sr][st]"))
            subtitle_files = sorted(subtitle_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0)
            print(f"Processing file: {filename}") 
            print("Available subtitle files:")
            for i, subtitle_file in enumerate(subtitle_files, start=1):
                print(f"{i}. {os.path.basename(subtitle_file)}")
            file_number = int(input("Enter the number of the subtitles file for this video: "))
            subtitles_file = os.path.basename(subtitle_files[file_number - 1])
            codec, audio_codec = get_codec_and_audio_tracks(mkv_file)
            print(f"Detected audio codec: {audio_codec}")  # Debugging line
            ffmpeg_command = ["ffmpeg", "-i", mkv_file]
            if subtitles_file.endswith(".ass"):
                ffmpeg_command.extend(["-vf", f"ass='{subtitles_file}'"])
            else:
                ffmpeg_command.extend(["-vf", f"subtitles='{subtitles_file}'"])
            if audio_codec == 'flac':
                ffmpeg_command.extend(["-strict", "-2"])
            if codec == 'h264':
                ffmpeg_command.extend(["-c:v", "h264_nvenc", "-c:a", "copy", mp4_file])
            else:
                ffmpeg_command.extend(["-c:v", "hevc_nvenc", "-c:a", "copy", mp4_file])
            subprocess.run(ffmpeg_command, cwd=input_dir)
    
input_dir = input("Enter the path to the input directory: ")
output_dir = input("Enter the path to the output directory: ")
audio_track = input("Enter the audio track number to use for all files: ")
separate_subtitles = False
separate_subtitles = input("Do you want to encode subtitles with seperate files (need to be in the input folder) ? (yes/no): ").lower() == 'yes'

# Usage
convert_mkv_to_mp4(input_dir, output_dir, audio_track, separate_subtitles)