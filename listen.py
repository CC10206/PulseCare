"""
PulseCare — 麥克風錄音 + VAD 自動斷句 (Phase 2)

隱私核心：全部在本地端執行，錄到的原始音訊只在記憶體/暫存檔存在到
特徵抽取完成為止 (呼叫端負責銷毀，同 analyze.py 的作法)。

silero-vad 的 VADIterator 要求固定的 chunk 大小 (16kHz 時為 512 samples)，
每個 chunk 餵進去後回傳 {"start": t} / {"end": t} / None 三種事件。
EndOfTurnDetector 只處理「何時該停止錄音」的純邏輯，不碰麥克風或 VAD 模型，
方便在沒有硬體的環境下測試；record_with_vad() 負責把它接上真正的硬體。
"""


class EndOfTurnDetector:
    """純邏輯：根據 VADIterator 逐塊丟出的事件，決定何時該停止錄音。"""

    def __init__(self, chunk_s: float, max_total_s: float = 20.0):
        self.chunk_s = chunk_s
        self.max_total_s = max_total_s
        self._elapsed_s = 0.0
        self._started = False

    def push(self, vad_event: dict | None) -> bool:
        """餵一個 chunk 的 VADIterator 回傳值。回傳 True 代表該停止錄音了。"""
        self._elapsed_s += self.chunk_s

        if vad_event:
            if "start" in vad_event:
                self._started = True
            if "end" in vad_event and self._started:
                return True

        return self._elapsed_s >= self.max_total_s

    @property
    def started(self) -> bool:
        """是否曾經偵測到語音開始——False 代表整段錄音很可能是靜音/沒收到聲音。"""
        return self._started


def pick_input_device(devices: list, default_index: int) -> int:
    """純邏輯：系統預設輸入裝置無效 (超出範圍/沒有輸入聲道) 時，
    改選第一個有輸入聲道的裝置。找不到就直接報錯，不要默默錄到啞巴音檔。"""
    if 0 <= default_index < len(devices) and devices[default_index].get("max_input_channels", 0) > 0:
        return default_index
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            return i
    raise RuntimeError("找不到任何可用的麥克風輸入裝置")


def record_with_vad(sample_rate: int = 16000, max_total_s: float = 20.0, device: int | None = None):
    """開麥克風錄音，用 silero-vad 自動偵測語句起訖。回傳 (numpy float32 array, sample_rate)。

    用 callback 模式而非 blocking read——部分裝置後端 (如 Windows WDM-KS)
    不支援 blocking read API，callback 模式相容性較好。

    WDM-KS 裝置通常只接受自己的原生取樣率 (常見 44100/48000)，不像
    MME/WASAPI 共享模式會自動幫忙轉 16kHz。所以錄音一律用裝置原生取樣率，
    每個 chunk 進來後即時降採樣到 silero-vad 需要的 16kHz 再餵進去，
    輸出的音訊也一併轉成 16kHz（跟 features.py/transcribe.py 的假設一致）。
    """
    import queue
    import numpy as np
    import sounddevice as sd
    import torch
    from scipy.signal import resample_poly
    from silero_vad import load_silero_vad, VADIterator

    if device is None:
        devices = sd.query_devices()
        device = pick_input_device(list(devices), sd.default.device[0])
    device_info = sd.query_devices(device)
    native_rate = int(device_info["default_samplerate"])
    print(f"使用麥克風裝置 #{device}: {device_info['name']}（原生取樣率 {native_rate}Hz）")

    chunk_size = 512  # silero-vad 在 16kHz 下固定要求的 chunk 大小
    chunk_s = chunk_size / sample_rate
    chunk_size_native = round(chunk_size * native_rate / sample_rate)

    model = load_silero_vad(onnx=True)
    vad_iterator = VADIterator(model, sampling_rate=sample_rate)
    detector = EndOfTurnDetector(chunk_s=chunk_s, max_total_s=max_total_s)

    q: "queue.Queue" = queue.Queue()

    def callback(indata, frame_count, time_info, status):
        # PortAudio 不會把這裡丟出的例外傳到主執行緒——會被默默吞掉，
        # 主執行緒的 q.get() 就會永遠卡住。所以自己接住例外丟進 queue。
        try:
            q.put(indata[:, 0].copy())
        except Exception as e:  # noqa: BLE001
            q.put(e)

    def to_target_rate(chunk_native: "np.ndarray") -> "np.ndarray":
        resampled = resample_poly(chunk_native, sample_rate, native_rate).astype("float32")
        if len(resampled) > chunk_size:
            return resampled[:chunk_size]
        if len(resampled) < chunk_size:
            return np.pad(resampled, (0, chunk_size - len(resampled)))
        return resampled

    frames = []
    print("🎤 請開始講話…")
    with sd.InputStream(samplerate=native_rate, channels=1, dtype="float32",
                         blocksize=chunk_size_native, device=device, callback=callback):
        while True:
            try:
                item = q.get(timeout=5.0)
            except queue.Empty:
                raise RuntimeError("5 秒內沒有收到任何錄音資料——麥克風 callback 沒有被觸發，"
                                    "請檢查裝置是否被其他程式獨占，或換一個裝置") from None
            if isinstance(item, Exception):
                raise RuntimeError(f"錄音 callback 內發生錯誤: {item}") from item
            chunk = to_target_rate(item)
            frames.append(chunk)
            event = vad_iterator(torch.from_numpy(chunk), return_seconds=True)
            if detector.push(event):
                break

    vad_iterator.reset_states()
    if detector.started:
        print("🔇 偵測到語句結束，停止錄音")
    else:
        print(f"⚠️ 錄了 {max_total_s:.0f} 秒都沒偵測到語音，已達安全上限自動停止"
              "（請確認麥克風輸入裝置/音量是否正確）")
    return np.concatenate(frames), sample_rate


def save_wav(audio, path: str, sample_rate: int = 16000) -> None:
    import soundfile as sf
    sf.write(path, audio, sample_rate)


if __name__ == "__main__":
    import sys
    out_path = sys.argv[1] if len(sys.argv) > 1 else "recorded.wav"
    audio, sr = record_with_vad()
    save_wav(audio, out_path, sr)
    print(f"已錄製 {len(audio) / sr:.1f}s → {out_path}")
