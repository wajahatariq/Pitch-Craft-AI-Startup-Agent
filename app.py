import streamlit as st
from litellm import completion

# Load CSS from external file
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Apply CSS style
local_css("style.css")

st.set_page_config(page_title="PitchCraft - AI Startup Partner", layout="centered")

st.title("PitchCraft – Your AI Startup Partner")

st.markdown(
    "Generate startup pitches, names, and taglines using **llama-instant** model via LiteLLM."
)

# Helper function to call LLM using API key from st.secrets
def run_completion(prompt: str):
    response = completion(
        model="groq/llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        api_key=st.secrets["GROQ_API_KEY"],
    )
    return response["choices"][0]["message"]["content"].strip()

# Agents

def idea_agent(idea):
    prompt = f"""
You are an expert startup strategist.
Summarize this idea in 2-3 lines, identifying the main problem and what it aims to solve.

Idea: {idea}
"""
    return run_completion(prompt)

def name_agent(summary):
    prompt = f"""
Based on this startup idea summary, generate 3 unique, short, and brandable startup names.
Avoid generic terms like "AI" or "Tech".

Idea Summary: {summary}
"""
    return run_completion(prompt)

def tagline_agent(name, tone):
    prompt = f"""
You are a creative copywriter. Generate a catchy tagline for this startup.
Tone: {tone}
Startup Name: {name}
Output only the tagline.
"""
    return run_completion(prompt)

def pitch_agent(summary, tone):
    prompt = f"""
Write a 2-paragraph elevator pitch for this startup idea.
Include a clear problem and solution.
Tone: {tone}
Idea: {summary}
"""
    return run_completion(prompt)

def audience_agent(summary):
    prompt = f"""
Define the target audience and pain points for this startup idea.
Write in bullet points.
Idea: {summary}
"""
    return run_completion(prompt)

def brand_agent(name, tone):
    prompt = f"""
Suggest a color palette and logo concept idea for this startup.
Name: {name}
Tone: {tone}
"""
    return run_completion(prompt)

def report_agent(name, tagline, pitch, audience, brand):
    problem = pitch.split(".")[0] if "." in pitch else pitch
    solution = pitch.split(".")[1] if "." in pitch else ""
    return {
        "name": name,
        "tagline": tagline,
        "pitch": pitch,
        "audience": audience,
        "problem": problem,
        "solution": solution,
        "brand": brand,
    }

# Main workflow

def run_pitchcraft_workflow(idea, tone):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    first_name = names.split("\n")[0].strip() if names else "StartupName"
    tagline = tagline_agent(first_name, tone)
    pitch_text = pitch_agent(idea_summary, tone)
    audience = audience_agent(idea_summary)
    brand = brand_agent(first_name, tone)
    return report_agent(first_name, tagline, pitch_text, audience, brand)

# Streamlit UI

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")

tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

result = None

if st.button("Generate Pitch"):
    if not idea.strip():
        st.warning("Please enter your idea first.")
    else:
        with st.spinner("Generating your startup pitch..."):
            result = run_pitchcraft_workflow(idea, tone)
            if result:
                st.success("Pitch Generated!")
                st.markdown(f"### 🏷 **Name:** {result['name']}")
                st.markdown(f"**Tagline:** {result['tagline']}")
                st.markdown(f"**Problem:** {result['problem']}")
                st.markdown(f"**Solution:** {result['solution']}")
                st.markdown(f"**Audience:** {result['audience']}")
                st.markdown(f"**Pitch:** {result['pitch']}")
                st.markdown(f"**Brand Direction:** {result['brand']}")
