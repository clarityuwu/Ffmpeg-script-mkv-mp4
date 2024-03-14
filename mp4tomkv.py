import os
import subprocess
import json
import glob
import re


def run_ffprobe_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return json.loads(result.stdout)


def get_streams(file, stream_type):
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-select_streams",
        stream_type,
        file,
    ]
    return run_ffprobe_command(command)["streams"]


def get_audio_tracks(mkv_file):
    audio_tracks = get_streams(mkv_file, "a")
    for track in audio_tracks:
        language = track.get("tags", {}).get("language", "Unknown")
        track["language"] = language
    return audio_tracks


def get_subtitle_tracks(mkv_file):
    subtitle_tracks = get_streams(mkv_file, "s")
    for track in subtitle_tracks:
        language = track.get("tags", {}).get("language", "Unknown")
        track["language"] = language
    return subtitle_tracks


def get_codec_and_audio_tracks(file):
    streams = get_streams(file, "v:a")
    video_codec = next(
        (stream["codec_name"] for stream in streams if stream["codec_type"] == "video"),
        None,
    )
    audio_codec = next(
        (stream["codec_name"] for stream in streams if stream["codec_type"] == "audio"),
        None,
    )
    return video_codec, audio_codec


def video_codec(file):
    return get_codec_and_audio_tracks(file)[0]


def extract_number(filename):
    numbers = re.findall(r"\d+", filename)
    return [int(number) for number in numbers]


def convert_mkv_to_mp4(
    input_dir,
    output_dir,
    audio_track,
    separate_subtitles,
    auto_encode,
    embed_subtitles,
    chosen_subtitle,
    use_gpu=True
):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mkv_files = sorted(
        [file for file in os.listdir(input_dir) if file.endswith(".mkv")],
        key=extract_number,
    )
    subtitle_files = glob.glob(
        os.path.join(input_dir, "**", "*.[as][sr][st]"), recursive=True
    )
    subtitle_files = sorted(subtitle_files, key=extract_number)

    for i, filename in enumerate(mkv_files):
        mkv_file = os.path.join(input_dir, filename)
        mp4_file = os.path.join(output_dir, os.path.splitext(filename)[0] + ".mp4")
        codec, audio_codec = get_codec_and_audio_tracks(mkv_file)

        if use_gpu:
            video_codec = "hevc_nvenc"
        else:
            video_codec = "libx264"

        ffmpeg_command = [
            "ffmpeg",
            "-i",
            mkv_file,
            "-b:a",
            "128k",
            "-crf",
            "30",
            "-map_metadata",
            "-1",
            "-map",
            "0:v:0",
            "-map",
            f"0:a:{audio_track}",
            "-c:v",
            video_codec,
        ]
        
        if separate_subtitles and not auto_encode:
            for i, subtitle_file in enumerate(subtitle_files, start=0):
                print(f"{i}. {os.path.basename(subtitle_file)}")
            subtitles_file = os.path.basename(
                subtitle_files[
                    int(input("Entrez le numéro de sous-titres pour cette vidéo: "))
                ]
            )
            if subtitles_file.endswith(".ass"):
                ffmpeg_command.extend(
                    ["-vf", f"ass='{os.path.basename(subtitles_file)}'"]
                )
            else:
                ffmpeg_command.extend(
                    ["-vf", f"subtitles='{os.path.basename(subtitles_file)}'"]
                )

        if separate_subtitles and auto_encode:
            if subtitle_files:
                subtitle_file = subtitle_files[i]
                print("Subs files", subtitle_files)
                if subtitle_file.endswith(".ass"):
                    ffmpeg_command.extend(
                        ["-vf", f"ass='{os.path.basename(subtitle_file)}'"]
                    )
                else:
                    ffmpeg_command.extend(
                        ["-vf", f"subtitles='{os.path.basename(subtitle_file)}'"]
                    )
            else:
                print("Aucun fichier de sous-titres trouvé.")

        if embed_subtitles:
            ffmpeg_command.extend(
                [
                    "-vf",
                    f"subtitles='{os.path.basename(mkv_file)}':si={chosen_subtitle}",
                ]
            )

        if audio_codec == "flac":
            ffmpeg_command.extend(["-strict", "-2"])

        ffmpeg_command.extend([mp4_file, "-y"])
        subprocess.run(ffmpeg_command, cwd=input_dir, check=True)


input_dir = input("Entrez le chemin vers le répertoire d'entrée : ")
output_dir = input("Entrez le chemin vers le répertoire de sortie : ")

mkv_files = [file for file in os.listdir(input_dir) if file.endswith(".mkv")]
first_mkv_file = os.path.join(input_dir, mkv_files[0])

audio_tracks = get_audio_tracks(first_mkv_file)
for i, track in enumerate(audio_tracks, start=0):
    track_name = track.get("tags", {}).get("title", track["codec_name"])
    language = track.get("language", "Unknown")
    print(f"{i}. {track_name} - {language}")

audio_track = input(
    "Entrez le numéro de piste audio à utiliser pour tous les fichiers : "
)
embed_subtitles = (
    input("Voulez-vous utiliser les sous-titres des fichiers mkv ? (oui/non): ").lower()
    == "oui"
)
chosen_subtitle = None
if embed_subtitles:
    subtitle_tracks = get_subtitle_tracks(first_mkv_file)
    for i, track in enumerate(subtitle_tracks):
        subtitle_track = track.get('tags', {}).get('title', track['codec_name'])
        subtitle_language = language = track.get("language", "Unknown")
        print(f"{i}. {subtitle_track} - {subtitle_language}")
    chosen_subtitle = int(input("Entrez le numéro de la piste de sous-titres à utiliser : "))

separate_subtitles = (
    input(
        "Voulez-vous encoder les sous-titres avec des fichiers séparés ? (doivent être dans le dossier d'entrée) (oui/non): "
    ).lower()
    == "oui"
)
auto_encode = (
    input(
        "Voulez-vous encoder automatiquement les fichiers avec des sous-titres séparés ? (oui/non): "
    ).lower()
    == "oui"
)

convert_mkv_to_mp4(
    input_dir,
    output_dir,
    audio_track,
    separate_subtitles,
    auto_encode,
    embed_subtitles,
    chosen_subtitle,
)
