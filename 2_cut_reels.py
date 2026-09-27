"""
2_cut_reels.py

Gemini'ye elle gönderdiğin promptun cevabını (JSON) bir dosyaya kaydet,
bu script o dosyayı okuyup raw videodan FFmpeg ile klipleri keser.

Kullanım:
    python 2_cut_reels.py raw_video.mov gemini_response.json
"""

import argparse
import json
import os
import subprocess
import sys


def cut_clips(video_path: str, segments: list, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    manifest = []

    for i, seg in enumerate(segments, start=1):
        start = seg["start"]
        end = seg["end"]
        duration = round(end - start, 2)
        title = seg.get("title", f"clip_{i}")
        safe_title = "".join(c if c.isalnum() or c in " _-" else "" for c in title).strip().replace(" ", "_")
        out_name = f"{i:02d}_{safe_title or 'clip'}.mp4"
        out_path = os.path.join(output_dir, out_name)

        cmd = [
            "ffmpeg" , "-y" ,
            "-i" , video_path ,
            "-ss" , str ( start ) ,
            "-to" , str ( end ) ,
            "-c:v" , "libx264" , "-c:a" , "aac" ,
            "-avoid_negative_ts" , "make_zero" ,
            "-movflags" , "+faststart" ,
            out_path ,
        ]
        print(f"[{i}/{len(segments)}] Kesiliyor: {title} ({start}s - {end}s, {duration}s)")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        if result.returncode != 0:
            print(f"  Hata oluştu: {result.stderr.decode()[-500:]}")
            continue

        manifest.append({
            "file": out_path,
            "start": start,
            "end": end,
            "duration": duration,
            "title": title,
            "hook": seg.get("hook"),
            "category": seg.get("category"),
            "reason": seg.get("reason"),
        })

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest_path


def main():
    parser = argparse.ArgumentParser(description="Gemini'nin JSON cevabına göre videodan klipler keser.")
    parser.add_argument("video", help="Raw video dosyası")
    parser.add_argument("gemini_response", help="Gemini'den kopyaladığın JSON cevabının kaydedildiği dosya")
    parser.add_argument("--output_dir", default="reels_output", help="Çıktı klasörü")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Hata: video bulunamadı -> {args.video}")
        sys.exit(1)
    if not os.path.exists(args.gemini_response):
        print(f"Hata: gemini cevap dosyası bulunamadı -> {args.gemini_response}")
        sys.exit(1)

    with open(args.gemini_response, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        segments = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Hata: dosya geçerli JSON değil ({e}).")
        sys.exit(1)

    print(f"{len(segments)} klip bulundu, kesim başlıyor...\n")
    manifest_path = cut_clips(args.video, segments, args.output_dir)

    print(f"\nTamamlandı. Klipler '{args.output_dir}' klasöründe.")
    print(f"Detaylar: {manifest_path}")


if __name__ == "__main__":
    main()