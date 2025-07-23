import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def explain_concept(theory_text, question):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",  # Или "mixtral-8x7b-32768"
        "messages": [
            {"role": "system", "content": "Розмовляй українською. Ти - асистент викладача. Пояснюй просто і зрозуміло. "
            "Відповідай на запитання як міні-твір. "
            "Відповідай максимально чітко, мінімум води. Використовуй інформацію у теорії. "
            "Якщо у теорії немає чого, то скажи щось зі своєї бази. Також у відповіді прибери усі /n символи."},
            {"role": "user", "content": f"Тут теорія:\n{theory_text}\n\Дай відповідь на запитання:\n{question}"}
        ],
        "temperature": 0.7
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()

    result = response.json()
    return result["choices"][0]["message"]["content"].strip()
