from llm_reply import build_prompt, SYSTEM_PROMPT


def test_build_prompt_includes_system_and_user_messages():
    messages = build_prompt("今天天氣很好，我剛吃完早餐。")

    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["role"] == "user"


def test_build_prompt_preserves_transcript_verbatim():
    transcript = "喔，還好啦，就一個人在家看電視。"

    messages = build_prompt(transcript)

    assert messages[1]["content"] == transcript
