import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_recommendations(passed_tests_titles: list[str]) -> list[str]:
    prompt = f"""
    Користувач пройшов такі тести: {', '.join(passed_tests_titles)}.
    Які 6 курсів (за назвою) ви б порекомендували, щоб поглибити їхні знання?
    Поверніть лише назви курсів, кожну на новому рядку, без нумерації. Поверни лише 6 курсів.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",  # или "mixtral-8x7b-32768"
        "messages": [
            {"role": "system", "content": "You are an educational recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()

    result = response.json()
    recommendations_text = result["choices"][0]["message"]["content"].strip()

    recommendations = [line.strip() for line in recommendations_text.split('\n') if line.strip()]
    return recommendations
