from litellm import completion
import os

def tagline_agent(name, tone):
    prompt = f"""
You are a creative copywriter. Generate a catchy tagline for this startup.
Tone: {tone}
Startup Name: {name}
Output only the tagline.
"""
    response = completion(
        model="groq/llama-3.1-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("GROQ_API_KEY")
    )
    return response["choices"][0]["message"]["content"].strip()
