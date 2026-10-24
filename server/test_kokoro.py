"""
Kokoro TTS test script -- verify en-GB voices work on this machine.

Usage:
  C:/Users/nyats/.workbuddy-ai/binaries/python/envs/kokoro/Scripts/python.exe server/test_kokoro.py

Expected output:
  Two WAV files in the same directory:
  - test_examiner.wav  (bm_george, British male)
  - test_candidate.wav (bf_emma, British female)
"""

import sys
import os

def main():
    print("[1/4] Importing kokoro...")
    try:
        from kokoro import KPipeline
        import soundfile as sf
    except ImportError as e:
        print(f"ERROR: {e}")
        print("Run: pip install kokoro soundfile")
        sys.exit(1)

    print("[2/4] Loading pipeline (lang_code='b' for British English)...")
    pipeline = KPipeline(lang_code="b")

    output_dir = os.path.dirname(os.path.abspath(__file__))

    # Test 1: Examiner voice (bm_george)
    print("[3/4] Generating examiner voice (bm_george)...")
    text_exam = "Good morning. My name is George. Can you tell me your full name, please?"
    for i, (gs, ps, audio) in enumerate(pipeline(text_exam, voice="bm_george")):
        out_path = os.path.join(output_dir, "test_examiner.wav")
        sf.write(out_path, audio, 24000)
        print(f"  Wrote {out_path} ({len(audio)/24000:.2f}s, {len(audio)} samples)")
        if i == 0:
            break  # first chunk is usually the full text

    # Test 2: Candidate voice (bf_emma)
    print("[4/4] Generating candidate voice (bf_emma)...")
    text_cand = "Hello, my name is Emma. I am from London and I work as a teacher."
    for i, (gs, ps, audio) in enumerate(pipeline(text_cand, voice="bf_emma")):
        out_path = os.path.join(output_dir, "test_candidate.wav")
        sf.write(out_path, audio, 24000)
        print(f"  Wrote {out_path} ({len(audio)/24000:.2f}s, {len(audio)} samples)")
        if i == 0:
            break

    print("\nDone! Both WAV files should sound natural and British.")
    print("If you hear robotic audio, check that CUDA is available:")
    print("  python -c \"import torch; print(torch.cuda.is_available())\"")

if __name__ == "__main__":
    main()
