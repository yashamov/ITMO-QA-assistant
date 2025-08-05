import openai
from config import OPENAI_API_KEY, OPENAI_MODEL
openai.api_key = OPENAI_API_KEY

def ask_openai(question, program_data, model=OPENAI_MODEL):
    # Если это dict — сериализуем для полноты данных.
    if isinstance(program_data, dict):
        import json
        program_data_str = json.dumps(program_data, ensure_ascii=False, indent=2)
    else:
        program_data_str = str(program_data)
    
    # Инструкцию и саму структуру программы кладём в system/user.
    system_prompt = (
        "Ты — умный ассистент, который помогает абитуриентам разобраться в магистерских программах ИТМО. "
        "Дай подробный, но лаконичный и точный ответ строго по теме вопроса и предоставленным данным."
    )
    user_prompt = (
        f"Вот информация о магистерских программах:\n{program_data_str}\n\n"
        f"Вопрос пользователя: {question}\n"
    )
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=700,
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка при обращении к OpenAI: {e}"
