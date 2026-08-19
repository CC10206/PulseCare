"""
PulseCare — 本地小型 LLM 生成回應 (OpenVINO GenAI)

隱私核心：跟 transcribe.py 的 Whisper 一樣，完全跑在本地，不上傳雲端。
語氣設計：溫暖、簡短、不用醫療/診斷字眼，呼應 PDF 提案的「去標籤化」原則
——AI 只負責自然接話陪伴，不負責衛教或催促就醫。
"""

_pipe = None

SYSTEM_PROMPT = (
    "你是一位溫暖親切的居家關懷語音助理，正在跟一位獨居長者日常聊天。"
    "回覆規則：\n"
    "1. 只用一到兩句自然口語回覆，不要條列、不要說教。\n"
    "2. 絕對不要提到憂鬱、心理健康、看醫生、診斷等字眼。\n"
    "3. 根據長者剛剛說的話自然接話，語氣像晚輩對長輩問候。\n"
    "4. 一律使用繁體中文（正體中文）回覆，不要出現簡體字。"
)


def get_pipeline(model_dir: str = "models/qwen2.5-1.5b-instruct-int4-ov",
                  device: str = "CPU"):
    """延遲載入 —— 模型載入需要時間，不要在每次呼叫時重建 (同 transcribe.py 的作法)。"""
    global _pipe
    if _pipe is None:
        import openvino_genai
        _pipe = openvino_genai.LLMPipeline(model_dir, device)
    return _pipe


def build_prompt(transcript: str) -> list[dict]:
    """組成送進 LLM 的對話訊息。獨立成純函式方便測試，不需要真的載入模型。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript},
    ]


def generate_reply(transcript: str, model_dir: str = "models/qwen2.5-1.5b-instruct-int4-ov",
                    device: str = "CPU", max_new_tokens: int = 60) -> str:
    """回傳 AI 音箱要用 TTS 念出來的下一句話。"""
    import openvino_genai

    pipe = get_pipeline(model_dir, device)
    config = openvino_genai.GenerationConfig()
    config.max_new_tokens = max_new_tokens

    history = openvino_genai.ChatHistory()
    for message in build_prompt(transcript):
        history.append(message)

    result = pipe.generate(history, config)
    return result.texts[0].strip()


if __name__ == "__main__":
    import sys
    transcript = sys.argv[1] if len(sys.argv) > 1 else "今天天氣很好，我剛吃完早餐。"
    print(generate_reply(transcript))
