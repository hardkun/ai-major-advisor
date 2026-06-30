from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def generate_answer(messages: list[dict]) -> str:
    """调用 OpenAI-compatible Chat Completions API。"""
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY 未配置")

    try:
        client_options = {"api_key": LLM_API_KEY}
        if LLM_BASE_URL:
            client_options["base_url"] = LLM_BASE_URL

        client = OpenAI(**client_options)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise RuntimeError("AI 服务调用失败") from exc

