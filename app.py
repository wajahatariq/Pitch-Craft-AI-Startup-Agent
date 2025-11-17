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
import requests

domainsduck_key = st.secrets["DOMAINDUCK_API_KEY"]

# Load CSS from external file
css_path = Path(__file__).parent / "style.css"
def local_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass  # ignore if no CSS file

local_css(css_path)

st.set_page_config(page_title="PitchCraft - AI Startup Partner", layout="centered")

st.title("PitchCraft – Your AI Startup Partner")
st.markdown(
    """
Generate **startup content dynamically**.  
Enter your startup idea, select tone, and toggle which assets to generate.
"""
)

# --- Pollinations image generation for logo preview ---
def generate_pollinations_image(prompt: str) -> str:
    from urllib.parse import quote_plus
    base_url = "https://image.pollinations.ai/prompt/"
    url = base_url + quote_plus(prompt)
    return url

# --- Domain availability check ---
def check_domain_availability(domain: str) -> str:
    url = "https://us.domainsduck.com/api/get/"
    params = {
        "domain": domain,
        "apikey": domainsduck_key,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("availability", "unknown")
    except Exception as e:
        return f"error: {str(e)}"

def map_domain_status(status):
    status = status.upper()
    if status == "TRUE":
        return "Domain is available"
    elif status == "FALSE":
        return "Domain is taken"
    else:
        return "Unable to check status"

# --- Helpers ---
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

def name_agent(idea):
    prompt = f"""
Generate exactly 3 unique startup names as a numbered list ONLY.  
Do NOT include any explanations, descriptions, or pronunciation guides.  
Avoid generic words like "AI", "Tech" and complex or hard-to-pronounce names. 
Names only.

Startup idea:
{idea}
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
You are a professional web developer.

Generate a modern, fully responsive, visually appealing **single-page website** for the startup named "{name}".

Requirements:
- Use semantic, well-structured HTML5.
- Include the following sections:
  1. Hero section with startup name, tagline, and a call-to-action button.
  2. About section describing the problem the startup solves.
  3. Features or solution section with cards or icons.
  4. Testimonials or social proof section (3 example testimonials).
  5. Contact section with a fully functional contact form (name, email, message) including input validation.
- Use a clean, consistent color scheme that fits the tone: {tone}.
- Include smooth scrolling navigation with a fixed header menu.
- Use responsive CSS that works well on mobile and desktop.
- Add subtle animations and transitions (e.g., fade-in on scroll, button hover effects).
- Provide a sticky navigation bar with links to sections.
- Ensure accessibility best practices (aria labels, alt text, proper heading hierarchy).
- Include SEO-friendly meta tags and page title.
- Use plain CSS or a lightweight framework (like Flexbox and Grid) for layout.
- Add JavaScript only for form validation and smooth scrolling navigation.
- Structure your output clearly in three labeled code blocks: HTML, CSS, and JavaScript.

Output your response in three separate clearly labeled code blocks:

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

# --- Workflow split into parts ---
def run_name_generation(idea):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    return idea_summary, names

def run_full_generation(idea_summary, selected_name, tone, generate_flags):
    results = {}
    if generate_flags.get("tagline", False):
        results['tagline'] = tagline_agent(selected_name, tone)
    if generate_flags.get("pitch", False):
        results['pitch'] = pitch_agent(idea_summary, tone)
    if generate_flags.get("audience", False):
        results['audience'] = audience_agent(idea_summary)
    if generate_flags.get("brand", False):
        results['brand'] = brand_agent(selected_name, tone)
    if generate_flags.get("website", False):
        results['website'] = website_agent(selected_name, tone)
    if generate_flags.get("social_media", False):
        results['social_media'] = social_media_agent(selected_name, tone)
    if generate_flags.get("competitor", False):
        results['competitor'] = competitor_analysis_agent(idea_summary)
    if generate_flags.get("financials", False):
        results['financials'] = financials_agent(selected_name)
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

if 'names_generated' not in st.session_state:
    st.session_state['names_generated'] = []
if 'finalized_name' not in st.session_state:
    st.session_state['finalized_name'] = None
if 'idea_summary' not in st.session_state:
    st.session_state['idea_summary'] = None
if 'last_idea' not in st.session_state:
    st.session_state['last_idea'] = ""
if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")
tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

# Reset session states if idea changed
if st.session_state['last_idea'] != idea:
    st.session_state['last_idea'] = idea
    st.session_state['submitted'] = False
    st.session_state['names_generated'] = []
    st.session_state['finalized_name'] = None
    st.session_state['idea_summary'] = None

submitted = st.button("Submit")

if submitted:
    if not idea.strip():
        st.warning("Please enter your startup idea before submitting.")
    else:
        st.session_state['submitted'] = True
        with st.spinner("Generating startup names..."):
            idea_summary, names_text = run_name_generation(idea)
            name_options = []
            for line in names_text.split('\n'):
                line = line.strip()
                if line and len(line) > 2 and line[0].isdigit() and line[1] == '.':
                    name = line.split('.', 1)[1].strip()
                    name_options.append(name)

            st.session_state['names_generated'] = name_options
            st.session_state['idea_summary'] = idea_summary
        st.rerun()

if st.session_state['submitted']:
    idea_summary = st.session_state['idea_summary']
    name_options = st.session_state['names_generated']

    if st.session_state['finalized_name'] is None:
        if name_options:
            selected_name = st.radio("Select a startup name", name_options)
        else:
            st.warning("No AI-generated names available. Please enter your own startup name below.")
            selected_name = None
        
        custom_name = st.text_input("Or enter your own startup name (optional)")


        final_name = custom_name.strip() if custom_name.strip() else selected_name
        
        if final_name and len(final_name) > 0:
            domain_to_check = final_name.replace(" ", "") + ".com"
            raw_availability = check_domain_availability(domain_to_check)
            availability = map_domain_status(raw_availability)
            st.markdown(f"**Domain check for `{domain_to_check}`:** **{availability}**")
        else:
            st.warning("Please select or enter a valid startup name.")
            domain_to_check = None
            availability = None


        if st.button("Finalize Name"):
            st.session_state['finalized_name'] = final_name
            st.rerun()
    else:
        st.markdown(f"**Finalized Startup Name:** {st.session_state['finalized_name']}")

        logo_prompt = (
    f"Create a creative, iconic logo concept for the startup named '{st.session_state['finalized_name']}'. "
    f"The logo should be bold, memorable, and visually represent the core values of the startup. "
    f"Use the brand's suggested color palette with primary and secondary colors. "
    f"Include symbolic elements related to the startup's mission, avoiding minimal or sleek styles. "
    f"The design should stand out and be suitable for various media, including digital and print."
)

        logo_url = generate_pollinations_image(logo_prompt)
        st.image(logo_url, caption="Logo Preview (AI-generated)", use_column_width=True)

        # Asset toggles
        generate_tagline = st.checkbox("Generate Tagline", value=True)
        generate_pitch = st.checkbox("Generate Elevator Pitch", value=True)
        generate_audience = st.checkbox("Generate Target Audience & Pain Points", value=True)
        generate_brand = st.checkbox("Generate Brand Direction", value=True)
        generate_website = st.checkbox("Generate Website (HTML/CSS/JS)", value=True)
        generate_social_media = st.checkbox("Generate Social Media Post Ideas", value=False)
        generate_competitor = st.checkbox("Generate Competitor Analysis", value=False)
        generate_financials = st.checkbox("Generate Financial Projections", value=False)

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
                result = run_full_generation(idea_summary, st.session_state['finalized_name'], tone, generate_flags)

            st.success("Generation Complete!")

            tabs = st.tabs(["Tagline", "Pitch", "Audience", "Brand", "Competitor", "Financials", "Social Media", "Website Preview", "Website Code"])

            if generate_tagline:
                with tabs[0]:
                    st.markdown(f"### Tagline\n{result.get('tagline','')}")

            if generate_pitch:
                with tabs[1]:
                    st.markdown(f"### Elevator Pitch\n{result.get('pitch','')}")

            if generate_audience:
                with tabs[2]:
                    st.markdown(f"### Target Audience & Pain Points\n{result.get('audience','')}")

            if generate_brand:
                with tabs[3]:
                    st.markdown(f"### Brand Direction\n{result.get('brand','')}")

            if generate_competitor:
                with tabs[4]:
                    st.markdown(f"### Competitor Analysis\n{result.get('competitor','')}")

            if generate_financials:
                with tabs[5]:
                    st.markdown(f"### Financial Projections\n{result.get('financials','')}")

            if generate_social_media:
                with tabs[6]:
                    st.markdown(f"### Social Media Post Ideas\n{result.get('social_media','')}")

            # Website preview tab with iframe
            if generate_website:
                html_code = css_code = js_code = ""
                website_code = result.get('website','')

                html_match = re.search(r"(?:```html|<html>)(.*?)(?:```|</html>)", website_code, re.DOTALL | re.IGNORECASE)
                css_match = re.search(r"(?:```css)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)
                js_match = re.search(r"(?:```js|```javascript)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)

                if html_match:
                    html_code = html_match.group(1).strip()
                if css_match:
                    css_code = css_match.group(1).strip()
                if js_match:
                    js_code = js_match.group(1).strip()
                    smooth_scroll_js = """
                    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                      anchor.addEventListener('click', function(e) {
                        e.preventDefault();
                        const targetID = this.getAttribute('href').substring(1);
                        const targetElement = document.getElementById(targetID);
                        if (targetElement) {
                          targetElement.scrollIntoView({ behavior: 'smooth' });
                        }
                      });
                    });
                    """
                    
                    js_code += smooth_scroll_js

                if not (html_code and css_code and js_code):
                    parts = re.split(r"\d\)\s*[Hh][Tt][Mm][Ll]|CSS|JavaScript|JS", website_code)
                    if len(parts) >= 4:
                        html_code = parts[1].strip()
                        css_code = parts[2].strip()
                        js_code = parts[3].strip()

                full_html = f"""
                <html>
                <head>
                <style>{css_code}</style>
                </head>
                <body>
                {html_code}
                <script>{js_code}</script>
                </body>
                </html>
                """

                with tabs[7]:
                    st.markdown("### Live Website Preview")
                    st.components.v1.html(full_html, height=600, scrolling=True)

                with tabs[8]:
                    st.markdown("### Website Code")
                    st.subheader("HTML")
                    st.code(html_code, language="html")
                    st.subheader("CSS")
                    st.code(css_code, language="css")
                    st.subheader("JavaScript")
                    st.code(js_code, language="javascript")

                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        zip_file.writestr("index.html", html_code)
                        zip_file.writestr("styles.css", css_code)
                        zip_file.writestr("scripts.js", js_code)
                    zip_buffer.seek(0)

                    st.download_button(
                        label="Download Website Files (ZIP)",
                        data=zip_buffer,
                        file_name=f"{st.session_state['finalized_name'].replace(' ','_')}_website.zip",
                        mime="application/zip"
                    )

else:
    st.info("Enter your startup idea and tone, then press Submit to generate startup names.")







