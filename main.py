"""
1_transcript_extract.py

Raw videodan (veya ses dosyasından) kelime bazlı timestamp'li transcript çıkarır.
Çıktı: transcript.json  -> Gemini'ye gönderilmeye hazır format.

Kurulum:
    pip install faster-whisper

Kullanım:
    python 1_transcript_extract.py raw_video.mp4
    python 1_transcript_extract.py raw_video.mp4 --model medium --lang tr
"""

import argparse
import json
import subprocess
import sys
import tempfile
import os


def extract_audio(video_path: str) -> str:
    """Videodan ses çıkarır (Whisper wav ister)."""
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-ac", "1", "-ar", "16000",
        "-vn", tmp_wav,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp_wav


def transcribe(audio_path: str, model_size: str, language: str):
    from faster_whisper import WhisperModel

    # cpu icin compute_type="int8", gpu varsa "float16" kullan
    model = WhisperModel(model_size, device="auto", compute_type="int8")

    segments, info = model.transcribe(
        audio_path,
        language=language if language != "auto" else None,
        word_timestamps=True,
        vad_filter=True,  # sessizlikleri otomatik ayıklar
    )

    words = []
    full_segments = []

    for seg in segments:
        full_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                })

    return words, full_segments, info


def main():
    parser = argparse.ArgumentParser(description="Video/ses dosyasından timestamp'li transcript çıkarır.")
    parser.add_argument("input", help="Raw video veya ses dosyası yolu")
    parser.add_argument("--model", default="small", help="Whisper model boyutu: tiny/base/small/medium/large-v3 (default: small)")
    parser.add_argument("--lang", default="tr", help="Dil kodu, örn: tr, en. 'auto' verilirse otomatik tespit eder.")
    parser.add_argument("--output", default="transcript.json", help="Çıktı json dosyası adı")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Hata: dosya bulunamadı -> {args.input}")
        sys.exit(1)

    print("Ses çıkarılıyor...")
    audio_path = extract_audio(args.input)

    print(f"Transkript oluşturuluyor (model={args.model}, lang={args.lang})... Bu biraz sürebilir.")
    words, segments, info = transcribe(audio_path, args.model, args.lang)

    output = {
        "source_video": os.path.abspath(args.input),
        "language": info.language,
        "duration": round(info.duration, 2),
        "segments": segments,   # cümle bazlı (okunması kolay, Gemini context'i için)
        "words": words,         # kelime bazlı (kesin timestamp için)
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    os.remove(audio_path)

    print(f"\nTamamlandı. {len(words)} kelime, {len(segments)} segment bulundu.")
    print(f"Çıktı dosyası: {args.output}")
    print("\nBu dosyayı Gemini API'ya gönderirken 'segments' + 'words' alanlarını prompt içine koy.")


if __name__ == "__main__":
    main()