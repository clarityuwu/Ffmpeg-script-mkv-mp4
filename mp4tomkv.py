import os
import subprocess
import json
import glob
import re

def run_ffprobe_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return json.loads(result.stdout)

def get_streams(file, stream_type):
    command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", stream_type, file]
    return run_ffprobe_command(command)['streams']

def get_audio_tracks(mkv_file):
    return [stream for stream in get_streams(mkv_file, "a") if stream['codec_type'] == 'audio']

def get_subtitle_tracks(mkv_file):
    return get_streams(mkv_file, "s")

def get_codec_and_audio_tracks(file):
    streams = get_streams(file, "v:a")
    video_codec = next((stream["codec_name"] for stream in streams if stream["codec_type"] == "video"), None)
    audio_codec = next((stream["codec_name"] for stream in streams if stream["codec_type"] == "audio"), None)
    return video_codec, audio_codec

def video_codec(file):
    return get_codec_and_audio_tracks(file)[0]

def convert_mkv_to_mp4(input_dir, output_dir, audio_track, separate_subtitles, auto_encode, embed_subtitles, chosen_subtitle):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mkv_files = [file for file in os.listdir(input_dir) if file.endswith(".mkv")]

    for filename in mkv_files:
        mkv_file = os.path.join(input_dir, filename)
        mp4_file = os.path.join(output_dir, os.path.splitext(filename)[0] + ".mp4")
        codec, audio_codec = get_codec_and_audio_tracks(mkv_file)
        ffmpeg_command = ["ffmpeg", "-i", mkv_file, "-map", "0:v:0", "-map", f"0:a:{audio_track}"]
        print('mkv_file: ', mkv_file)  

        if codec == 'h264':
            ffmpeg_command.extend(["-c:v", "h264_nvenc"])
        else:
            ffmpeg_command.extend(["-c:v", "hevc_nvenc"])

        if separate_subtitles:
            subtitle_files = glob.glob(os.path.join(input_dir, "**", "*.[as][sr][st]"), recursive=True)
            subtitle_files = sorted(subtitle_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else 0)
            
            if auto_encode:
                for subtitles_file in subtitle_files:
                    if subtitles_file.endswith(".ass"):
                        ffmpeg_command.extend(["-vf", f"ass='{os.path.basename(subtitles_file)}'"])
                    else:
                        ffmpeg_command.extend(["-vf", f"subtitles='{os.path.basename(subtitles_file)}'"])
            else:
                for i, subtitle_file in enumerate(subtitle_files, start=0):
                    print(f"{i}. {os.path.basename(subtitle_file)}")
                subtitles_file = os.path.basename(subtitle_files[int(input("Enter the number of the subtitles file for this video: "))])
                if subtitles_file.endswith(".ass"):
                    ffmpeg_command.extend(["-vf", f"ass='{os.path.basename(subtitles_file)}'"])
                else:
                    ffmpeg_command.extend(["-vf", f"subtitles='{os.path.basename(subtitles_file)}'"])
                
        if embed_subtitles:
            ffmpeg_command.extend(["-vf", f"subtitles='{os.path.basename(mkv_file)}':si={chosen_subtitle}"])

        if audio_codec == 'flac':
            ffmpeg_command.extend(["-strict", "-2"])

        ffmpeg_command.extend(["-c:a", "copy", mp4_file])
        subprocess.run(ffmpeg_command, cwd=input_dir, check=True)

input_dir = input("Entrez le chemin vers le répertoire d'entrée : ")
output_dir = input("Entrez le chemin vers le répertoire de sortie : ")

mkv_files = [file for file in os.listdir(input_dir) if file.endswith(".mkv")]
first_mkv_file = os.path.join(input_dir, mkv_files[0])

audio_tracks = get_audio_tracks(first_mkv_file)
for i, track in enumerate(audio_tracks, start=0):
    track_name = track.get('tags', {}).get('title', track['codec_name'])
    print(f"{i}. {track_name}")

audio_track = input("Entrez le numéro de piste audio à utiliser pour tous les fichiers : ")
embed_subtitles = input("Voulez-vous utilser les sous titres des fichiers mkv ? (oui/non): ").lower() == 'oui'
chosen_subtitle = None
if embed_subtitles:
    subtitle_tracks = get_subtitle_tracks(first_mkv_file)
    for i, track in enumerate(subtitle_tracks):
        print(f"{i}. {track.get('tags', {}).get('title', track['codec_name'])}")
    chosen_subtitle = int(input("Enter the number of the subtitle track to use: "))

separate_subtitles = input("Voulez-vous encoder les sous-titres avec des fichiers séparés ? (doivent être dans le dossier d'entrée) (oui/non): ").lower() == 'oui'
auto_encode = input("Voulez-vous encoder automatiquement les fichiers avec des sous-titres séparés ? (oui/non): ").lower() == 'oui'

convert_mkv_to_mp4(input_dir, output_dir, audio_track, separate_subtitles, auto_encode, embed_subtitles, chosen_subtitle)