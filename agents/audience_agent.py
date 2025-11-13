from litellm import completion
import os

def audience_agent(summary):
    prompt = f"""
Define the target audience and pain points for this startup idea.
Write in bullet points.
Idea: {summary}
"""
    response = completion(
        model="groq/llama-3.1-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("GROQ_API_KEY")
    )
    return response["choices"][0]["message"]["content"].strip()
