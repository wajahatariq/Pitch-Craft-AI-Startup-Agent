from litellm import completion
import os

def name_agent(summary):
    prompt = f"""
Based on this startup idea, generate 3 unique, short, and brandable startup names.
Avoid generic terms like "AI" or "Tech".

Idea Summary: {summary}
"""
    response = completion(
        model="groq/llama-3.1-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("GROQ_API_KEY")
    )
    return response["choices"][0]["message"]["content"].strip()
