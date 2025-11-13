from litellm import completion
import os

def pitch_agent(summary, tone):
    prompt = f"""
Write a 2-paragraph elevator pitch for this startup idea.
Include a clear problem and solution.
Tone: {tone}
Idea: {summary}
"""
    response = completion(
        model="groq/llama-3.1-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("GROQ_API_KEY")
    )
    return response["choices"][0]["message"]["content"].strip()
