import os
import subprocess
import json
import glob
import re

def get_audio_tracks(mkv_file):
    command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "a", mkv_file]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    streams = json.loads(result.stdout)['streams']
    audio_tracks = [stream for stream in streams if stream['codec_type'] == 'audio']
    return audio_tracks

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
def convert_mkv_to_mp4(input_dir, output_dir, audio_track, separate_subtitles, auto_encode):
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

    if separate_subtitles and not auto_encode:
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
            print(f"Detected audio codec: {audio_codec}")
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

    if auto_encode and separate_subtitles:
        mkv_files = sorted(mkv_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0)
        subtitle_files = glob.glob(os.path.join(input_dir, "*.[as][sr][st]"))
        subtitle_files = sorted(subtitle_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0)
        for i, file in enumerate(mkv_files):
            mkv_file = os.path.join(input_dir, file)
            subtitles_file = os.path.basename(subtitle_files[i])
            codec, audio_codec = get_codec_and_audio_tracks(mkv_file)
            ffmpeg_command = ["ffmpeg", "-i", mkv_file]
            if subtitles_file.endswith(".ass"):
                ffmpeg_command.extend(["-vf", f"ass='{subtitles_file}'"])
            else:
                ffmpeg_command.extend(["-vf", f"subtitles='{subtitles_file}'"])
            if audio_codec == 'flac':
                ffmpeg_command.extend(["-strict", "-2"])
            if codec == 'h264':
                ffmpeg_command.extend(["-c:v", "h264_nvenc", "-c:a", "copy", os.path.join(output_dir, f'{i+1}.mp4')])
            else:
                ffmpeg_command.extend(["-c:v", "hevc_nvenc", "-c:a", "copy", os.path.join(output_dir, f'{i+1}.mp4')])
            subprocess.run(ffmpeg_command, cwd=input_dir)
    
input_dir = input("Entrez le chemin vers le répertoire d'entrée : ")
output_dir = input("Entrez le chemin vers le répertoire de sortie : ")

mkv_files = [file for file in os.listdir(input_dir) if file.endswith(".mkv")]
first_mkv_file = os.path.join(input_dir, mkv_files[0])

audio_tracks = get_audio_tracks(first_mkv_file)
for i, track in enumerate(audio_tracks, start=0):
    track_name = track.get('tags', {}).get('title', track['codec_name'])
    print(f"{i}. {track_name}")

audio_track = input("Entrez le numéro de piste audio à utiliser pour tous les fichiers : ")
separate_subtitles = False
separate_subtitles = input("Voulez-vous encoder les sous-titres avec des fichiers séparés ? (doivent être dans le dossier d'entrée) (oui/non): ").lower() == 'oui'
auto_encode = input("Voulez-vous encoder automatiquement les fichiers avec des sous-titres séparés ? (oui/non): ").lower() == 'oui'

convert_mkv_to_mp4(input_dir, output_dir, audio_track, separate_subtitles, auto_encode)