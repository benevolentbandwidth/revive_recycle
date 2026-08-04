import base64
import json
from openai import OpenAI

GPT4O_INPUT_COST = 2.50 / 1_000_000
GPT4O_OUTPUT_COST = 10.00 / 1_000_000


def identify_brand_model(cropped_path: str, device_type: str, client: OpenAI) -> tuple[dict, float]:
    with open(cropped_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=256,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"This is a cropped image of a {device_type}. "
                            "Identify the brand and model as precisely as possible. "
                            "Reply with ONLY a JSON object in this exact format: "
                            '{"brand": "...", "model": "...", "confidence": "high|medium|low"}'
                        ),
                    },
                ],
            }
        ],
    )

    usage = response.usage
    call_cost = (usage.prompt_tokens * GPT4O_INPUT_COST) + (usage.completion_tokens * GPT4O_OUTPUT_COST)

    text = (
        response.choices[0].message.content.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"brand": "unknown", "model": "unknown", "confidence": "low", "raw": text}

    return result, call_cost
