import streamlit as st
from litellm import completion
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO
import re

file_name = style.css
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

def extract_first_name(names_text):
    lines = names_text.strip().split('\n')
    for line in lines:
        if line.strip().startswith("1."):
            return line.split('.', 1)[1].strip()
    for line in lines:
        if line.strip():
            return line.strip()
    return "StartupName"

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

# --- Improved PDF generation ---

def clean_markdown(text):
    # Remove basic markdown characters for PDF clarity
    replacements = [
        ("**", ""),
        ("*", ""),
        ("+", ""),
        ("\u2022", ""),  # bullet char if any
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text.strip()

def create_pitch_pdf(data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20))
    styles.add(ParagraphStyle(name='Heading', fontSize=16, leading=20, spaceAfter=10, spaceBefore=20))
    styles.add(ParagraphStyle(name='Body', fontSize=12, leading=16))
    styles.add(ParagraphStyle(name='CustomBullet', fontSize=12, leading=16, leftIndent=15, bulletIndent=5))
    styles.add(ParagraphStyle(name='CustomIndentedBullet', fontSize=12, leading=16, leftIndent=30, bulletIndent=10))

    story = []

    # Title and Tagline
    story.append(Paragraph(data['name'], styles['TitleCenter']))
    story.append(Paragraph(data['tagline'], styles['Heading']))

    # Problem and Solution
    story.append(Paragraph("Problem", styles['Heading']))
    story.append(Paragraph(data['problem'], styles['Body']))

    story.append(Paragraph("Solution", styles['Heading']))
    story.append(Paragraph(data['solution'], styles['Body']))

    # Audience - parse bullet points properly
    story.append(Paragraph("Target Audience & Pain Points", styles['Heading']))
    audience_lines = data['audience'].strip().split('\n')

    for line in audience_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("•") or line.startswith("-"):
            # Top-level bullet
            text = clean_markdown(line[1:].strip())
            story.append(Paragraph(text, styles['CustomBullet'], bulletText="•"))
        elif line.startswith("+"):
            # Indented bullet
            text = clean_markdown(line[1:].strip())
            story.append(Paragraph(text, styles['CustomIndentedBullet'], bulletText="–"))
        else:
            # Normal text
            story.append(Paragraph(clean_markdown(line), styles['Body']))

    # Elevator Pitch
    story.append(Paragraph("Elevator Pitch", styles['Heading']))
    story.append(Paragraph(data['pitch'], styles['Body']))

    # Brand Direction - split by options and add subtitles
    story.append(Paragraph("Brand Direction", styles['Heading']))
    brand_text = data['brand']

    # Split by **Option X:** pattern
    options = re.split(r"\*\*Option \d+: Startup Name - [^\*]+\*\*", brand_text)
    titles = re.findall(r"\*\*Option \d+: Startup Name - ([^\*]+)\*\*", brand_text)

    if options and options[0].strip() == "":
        options = options[1:]

    for i, option_text in enumerate(options):
        title = titles[i] if i < len(titles) else f"Option {i+1}"
        story.append(Paragraph(f"Option {i+1}: {title}", styles['Heading']))

        option_text_clean = clean_markdown(option_text)
        for line in option_text_clean.strip().split('\n'):
            line = line.strip()
            if line:
                story.append(Paragraph(line, styles['Body']))
        story.append(Spacer(1, 12))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Main workflow

def run_pitchcraft_workflow(idea, tone):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    first_name = extract_first_name(names)
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

                # Generate PDF bytes
                pdf_bytes = create_pitch_pdf(result)

                # Download button
                st.download_button(
                    label="Download Pitch as PDF",
                    data=pdf_bytes,
                    file_name=f"{result['name'].replace(' ', '_')}_pitch.pdf",
                    mime="application/pdf",
                )
