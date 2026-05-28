import json

from openai import OpenAI

from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def request_json(system_prompt: str, payload: dict) -> dict:
    response = client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        max_tokens=settings.max_tokens,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps({"input": payload}, ensure_ascii=False),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
