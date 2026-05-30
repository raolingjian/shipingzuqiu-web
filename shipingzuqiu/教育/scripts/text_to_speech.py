import asyncio, edge_tts, os, random, struct, wave

def _make_silent_wav(path, duration=1.0, sample_rate=16000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_samples = int(sample_rate * duration)
        for _ in range(num_samples):
            wf.writeframes(struct.pack("<h", 0))

async def generate_tts(text_lines, voice="zh-CN-YunxiNeural", rate="+0%", volume="+0%",
                       enable_ssml=True, pitch_variation=True):
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "temp_audio")
    os.makedirs(output_dir, exist_ok=True)
    audio_files = []

    for i, line in enumerate(text_lines):
        fpath = os.path.join(output_dir, f"scene_{i:03d}.wav")
        r = f"{random.randint(5, 20):+d}%" if rate == "random" else rate
        p = f"{random.choice([0, 5, 10, 15, 20, 25, 30]):+d}Hz" if pitch_variation else "+0Hz"
        last_err = None
        for retry in range(3):
            try:
                communicate = edge_tts.Communicate(line, voice, rate=r, volume=volume, pitch=p)
                await communicate.save(fpath)
                last_err = None
                break
            except Exception as e:
                last_err = e
                print(f"  [WARN] TTS重试 {retry+1}/3 场景{i}: {e}")
                await asyncio.sleep(2)
        if last_err:
            print(f"  [WARN] TTS失败，生成静音替代: {fpath}")
            _make_silent_wav(fpath, duration=1.5)
        audio_files.append(fpath)

    full_path = os.path.join(output_dir, "full.wav")
    fr = "+15%" if rate == "random" else rate
    last_err = None
    for retry in range(3):
        try:
            communicate = edge_tts.Communicate(" ".join(text_lines), voice, rate=fr, volume=volume)
            await communicate.save(full_path)
            last_err = None
            break
        except Exception as e:
            last_err = e
            print(f"  [WARN] TTS完整音频重试 {retry+1}/3: {e}")
            await asyncio.sleep(2)
    if last_err:
        _make_silent_wav(full_path, duration=3.0)
        print(f"  [WARN] TTS完整音频失败，生成静音替代: {full_path}")

    return audio_files, full_path

def run_tts(text_lines, voice="zh-CN-YunxiNeural", rate="+0%", volume="+0%",
            enable_ssml=True, pitch_variation=True):
    return asyncio.run(generate_tts(text_lines, voice, rate, volume, enable_ssml, pitch_variation))

if __name__ == "__main__":
    lines = ["消防证含金量有多高？", "考过就是铁饭碗！", "想考消防证的朋友，加我咨询详情！"]
    files, full = run_tts(lines)
    print("Generated:", files)
    print("Full:", full)
