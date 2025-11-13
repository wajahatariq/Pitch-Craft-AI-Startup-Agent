import streamlit as st
from graph.workflow import run_pitchcraft_workflow
from utils.export_pdf import export_to_pdf
from utils.storage import save_pitch
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="PitchCraft - AI Startup Partner", layout="centered")

st.title("PitchCraft – Your AI Startup Partner")

st.markdown("Generate startup pitches, names, and taglines using Groq + LangGraph + LiteLLM.")

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")

tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

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

                save_pitch(result)

                if st.button("Export as PDF"):
                    export_to_pdf(result)
                    st.success("PDF saved as 'pitch_output.pdf'")
