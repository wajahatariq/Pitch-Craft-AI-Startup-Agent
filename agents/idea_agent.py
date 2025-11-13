from litellm import completion
import os

def idea_agent(idea):
    prompt = f"""
You are an expert startup strategist.
Summarize this idea in 2-3 lines, identifying the main problem and what it aims to solve.

Idea: {idea}
"""
    response = completion(
        model="groq/llama-3.1-70b",
        messages=[{"role": "user", "content": prompt}],
        api_key=os.getenv("GROQ_API_KEY")
    )
    return response["choices"][0]["message"]["content"].strip()
