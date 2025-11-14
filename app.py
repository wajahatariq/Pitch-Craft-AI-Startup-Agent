import streamlit as st
from litellm import completion
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO
from pathlib import Path
import re
import zipfile

# Load CSS from external file in the same directory as app.py
css_path = Path(__file__).parent / "style.css"

def local_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css(css_path)

st.set_page_config(page_title="PitchCraft - AI Startup Partner", layout="centered")

st.title("PitchCraft – Your AI Startup Partner")

st.markdown(
    """
Generate **startup content dynamically**.  
Enter your startup idea, select tone, and toggle which assets to generate.
"""
)

# --- LLM interaction helper ---

def run_completion(prompt: str):
    response = completion(
        model="groq/llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        api_key=st.secrets["GROQ_API_KEY"],
    )
    return response["choices"][0]["message"]["content"].strip()

# --- Agents ---

def idea_agent(idea):
    prompt = f"""
You are a seasoned startup strategist. Analyze this startup idea carefully.

Provide a concise summary (2-3 sentences) that clearly identifies:
- The main problem the startup addresses
- The core solution it offers

Make the summary compelling and insightful.

Startup Idea:
{idea}
"""
    return run_completion(prompt)

def name_agent(summary):
    prompt = f"""
Generate exactly 3 unique startup names as a numbered list ONLY.  
Do NOT include any explanations, descriptions, or pronunciation guides.
Avoid generic words like "AI", "Tech".
Names only.
"""
    return run_completion(prompt)

def tagline_agent(name, tone):
    prompt = f"""
You are an expert copywriter.

Create a catchy and memorable tagline for this startup name.

Requirements:
- Reflect the startup's core value and vision
- Use the tone: {tone} (e.g., Formal, Casual, Fun, Investor)
- Keep it short (under 10 words)
- Output only the tagline text (no explanations)

Startup Name:
{name}
"""
    return run_completion(prompt)

def pitch_agent(summary, tone):
    prompt = f"""
You are a skilled marketer.

Write a compelling **two-paragraph elevator pitch** for this startup.

Include:
- A clear statement of the problem and its impact
- A description of the solution and unique value proposition
- Use the tone: {tone}

Startup Summary:
{summary}
"""
    return run_completion(prompt)

def audience_agent(summary):
    prompt = f"""
You are a market analyst.

Define the target audience and their pain points for this startup.

Format your answer as bullet points grouped under:
- Primary Target Audience
- Secondary Target Audience
- Pain Points

Use clear and concise language.

Startup Summary:
{summary}
"""
    return run_completion(prompt)

def brand_agent(name, tone):
    prompt = f"""
You are a branding expert.

Suggest a professional color palette (with hex codes) and a simple but effective logo concept idea for this startup.

Consider the startup name: {name} and the tone: {tone}.

Describe:
- Primary and secondary colors
- Logo style and symbolism

Output your response in clear paragraphs.
"""
    return run_completion(prompt)

def website_agent(name, tone):
    prompt = f"""
You are a web developer.

Generate a simple, clean, and responsive **single-page website** for the startup named "{name}" using HTML, CSS, and JavaScript.

The website should include:
- A homepage header with the startup name and tagline
- A section about the problem
- A section about the solution
- A contact form (no backend needed)
- Styling that matches a {tone} tone

Output your response as three separate code blocks, labeled clearly:
1) HTML code
2) CSS code
3) JavaScript code
"""
    return run_completion(prompt)

def social_media_agent(name, tone):
    prompt = f"""
You are a social media strategist.

Create a list of 5 creative social media post ideas for the startup "{name}" using a {tone} tone.

Each idea should be short, engaging, and suitable for platforms like Twitter or Instagram.

Output as a numbered list without explanations.
"""
    return run_completion(prompt)

def competitor_analysis_agent(summary):
    prompt = f"""
You are a business analyst.

Provide a brief competitor analysis for the startup idea summarized below.

Include:
- Key competitors
- What differentiates this startup from competitors
- Potential market challenges

Write in clear, concise paragraphs.

Startup Summary:
{summary}
"""
    return run_completion(prompt)

def financials_agent(name):
    prompt = f"""
You are a financial advisor.

Create a simple 3-year financial projection outline for the startup "{name}".

Include expected:
- Revenue streams
- Key costs
- Profit estimates

Write in bullet points, clear and concise.
"""
    return run_completion(prompt)

# --- Report generator ---

def report_agent(name, tagline, pitch, audience, brand, idea_summary):
    if "." in pitch:
        problem = pitch.split(".", 1)[0] + "."
        solution = pitch.split(".", 1)[1].strip()
    else:
        problem = pitch
        solution = ""
    return {
        "name": name,
        "tagline": tagline,
        "pitch": pitch,
        "audience": audience,
        "problem": problem,
        "solution": solution,
        "brand": brand,
        "idea_summary": idea_summary,
    }

# --- PDF generation ---

def clean_markdown(text):
    replacements = [
        ("**", ""),
        ("*", ""),
        ("+", ""),
        ("\u2022", ""),
        ("\n\n", "\n"),
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
    styles.add(ParagraphStyle(name='TitleCenter', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20, spaceBefore=10))
    styles.add(ParagraphStyle(name='Heading', fontSize=16, leading=20, spaceAfter=10, spaceBefore=15))
    styles.add(ParagraphStyle(name='Body', fontSize=12, leading=16))
    styles.add(ParagraphStyle(name='CustomBullet', fontSize=12, leading=16, leftIndent=15, bulletIndent=5))
    styles.add(ParagraphStyle(name='CustomIndentedBullet', fontSize=12, leading=16, leftIndent=30, bulletIndent=10))

    story = []

    story.append(Paragraph(data['name'], styles['TitleCenter']))
    story.append(Paragraph(data['tagline'], styles['Heading']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Problem", styles['Heading']))
    story.append(Paragraph(data['problem'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Solution", styles['Heading']))
    story.append(Paragraph(data['solution'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Target Audience & Pain Points", styles['Heading']))
    audience_lines = data['audience'].strip().split('\n')
    for line in audience_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("•") or line.startswith("-"):
            text = clean_markdown(line[1:].strip())
            story.append(Paragraph(text, styles['CustomBullet'], bulletText="•"))
        elif line.startswith("+"):
            text = clean_markdown(line[1:].strip())
            story.append(Paragraph(text, styles['CustomIndentedBullet'], bulletText="–"))
        else:
            story.append(Paragraph(clean_markdown(line), styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Elevator Pitch", styles['Heading']))
    story.append(Paragraph(data['pitch'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Brand Direction", styles['Heading']))
    brand_text = data['brand']

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

# --- Workflow split into parts ---

def run_name_generation(idea):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    return idea_summary, names

def run_full_generation(idea_summary, selected_name, tone, generate_flags):
    results = {}
    if generate_flags["tagline"]:
        results['tagline'] = tagline_agent(selected_name, tone)
    if generate_flags["pitch"]:
        results['pitch'] = pitch_agent(idea_summary, tone)
    if generate_flags["audience"]:
        results['audience'] = audience_agent(idea_summary)
    if generate_flags["brand"]:
        results['brand'] = brand_agent(selected_name, tone)
    if generate_flags["website"]:
        results['website'] = website_agent(selected_name, tone)
    if generate_flags["social_media"]:
        results['social_media'] = social_media_agent(selected_name, tone)
    if generate_flags["competitor"]:
        results['competitor'] = competitor_analysis_agent(idea_summary)
    if generate_flags["financials"]:
        results['financials'] = financials_agent(selected_name)
    # Required base fields for report
    results.update(report_agent(
        selected_name,
        results.get('tagline', ''),
        results.get('pitch', ''),
        results.get('audience', ''),
        results.get('brand', ''),
        idea_summary,
    ))
    return results

# --- Streamlit UI ---

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")
tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

generate_tagline = st.checkbox("Generate Tagline", value=True)
generate_pitch = st.checkbox("Generate Elevator Pitch", value=True)
generate_audience = st.checkbox("Generate Target Audience & Pain Points", value=True)
generate_brand = st.checkbox("Generate Brand Direction", value=True)
generate_website = st.checkbox("Generate Website (HTML/CSS/JS)", value=False)
generate_social_media = st.checkbox("Generate Social Media Post Ideas", value=False)
generate_competitor = st.checkbox("Generate Competitor Analysis", value=False)
generate_financials = st.checkbox("Generate Financial Projections", value=False)

if idea.strip():
    with st.spinner("Generating startup names..."):
        idea_summary, names = run_name_generation(idea)

    name_options = []
    for line in names.split('\n'):
        line = line.strip()
        if line and len(line) > 2 and line[0].isdigit() and line[1] == '.':
            name = line.split('.', 1)[1].strip()
            name_options.append(name)

    selected_name = st.selectbox("Select a startup name", name_options)

    if st.button("Generate Selected Assets"):
        generate_flags = {
            "tagline": generate_tagline,
            "pitch": generate_pitch,
            "audience": generate_audience,
            "brand": generate_brand,
            "website": generate_website,
            "social_media": generate_social_media,
            "competitor": generate_competitor,
            "financials": generate_financials,
        }
        with st.spinner("Generating your startup assets..."):
            result = run_full_generation(idea_summary, selected_name, tone, generate_flags)

        st.success("Generation Complete!")

        if generate_tagline:
            st.markdown(f"### Tagline\n{result.get('tagline','')}")
        if generate_pitch:
            st.markdown(f"### Elevator Pitch\n{result.get('pitch','')}")
        if generate_audience:
            st.markdown(f"### Target Audience & Pain Points\n{result.get('audience','')}")
        if generate_brand:
            st.markdown(f"### Brand Direction\n{result.get('brand','')}")
        if generate_competitor:
            st.markdown(f"### Competitor Analysis\n{result.get('competitor','')}")
        if generate_financials:
            st.markdown(f"### Financial Projections\n{result.get('financials','')}")
        if generate_social_media:
            st.markdown(f"### Social Media Post Ideas\n{result.get('social_media','')}")
        if generate_website:
            st.markdown("### Website Code")
            # Parse website agent output into HTML, CSS, JS parts
            website_code = result.get('website','')
            # Attempt to split code blocks by labels
            # Expected format: labeled code blocks with comments or code fences
            
            # Try simple extraction using regex for code blocks (assuming triple backticks and labels)
            html_code = css_code = js_code = ""
            html_match = re.search(r"(?:```html|<html>)(.*?)(?:```|</html>)", website_code, re.DOTALL | re.IGNORECASE)
            css_match = re.search(r"(?:```css)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)
            js_match = re.search(r"(?:```js|```javascript)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)

            if html_match:
                html_code = html_match.group(1).strip()
            if css_match:
                css_code = css_match.group(1).strip()
            if js_match:
                js_code = js_match.group(1).strip()

            # Fallback parsing by labels (for output not fenced)
            if not (html_code and css_code and js_code):
                # Try split by lines like "1) HTML code", etc
                parts = re.split(r"\d\)\s*[Hh][Tt][Mm][Ll]|CSS|JavaScript|JS", website_code)
                if len(parts) >= 4:
                    html_code = parts[1].strip()
                    css_code = parts[2].strip()
                    js_code = parts[3].strip()

            # Show code in expanders
            with st.expander("HTML"):
                st.code(html_code, language="html")
            with st.expander("CSS"):
                st.code(css_code, language="css")
            with st.expander("JavaScript"):
                st.code(js_code, language="javascript")

            # Allow download as zip
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                zip_file.writestr("index.html", html_code)
                zip_file.writestr("styles.css", css_code)
                zip_file.writestr("scripts.js", js_code)
            zip_buffer.seek(0)

            st.download_button(
                label="Download Website Files (ZIP)",
                data=zip_buffer,
                file_name=f"{selected_name.replace(' ','_')}_website.zip",
                mime="application/zip"
            )

        # PDF generation if pitch + brand + tagline present (minimum)
        if generate_pitch and generate_brand and generate_tagline:
            pdf_bytes = create_pitch_pdf(result)
            st.download_button(
                label="Download Pitch as PDF",
                data=pdf_bytes,
                file_name=f"{selected_name.replace(' ', '_')}_pitch.pdf",
                mime="application/pdf",
            )

else:
    st.info("Please enter your startup idea to generate names.")
