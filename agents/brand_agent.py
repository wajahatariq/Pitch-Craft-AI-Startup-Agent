from litellm import completion
import os

def brand_agent(name, tone):
    prompt = f"""
Suggest a color palette and logo concept idea for this startup.
Name: {name}
Tone: {tone}
"""
    response = completion(
        model="groq/llama-3.1-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("GROQ_API_KEY")
    )
    return response["choices"][0]["message"]["content"].strip()
