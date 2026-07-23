# pre_ukvi_app.py
import streamlit as st
from advisors_theme import apply_advisors_theme

st.set_page_config(
    page_title="Pre UKVI Compliance Interview",
    page_icon="🎓",
    layout="wide",
)

apply_advisors_theme()

st.title("Pre UKVI Compliance Interview")
st.markdown(
    """
Use the pages on the left:

- **Advisor (typed)**: counsellors run mock interviews and type student answers.
- **Student (speaking)**: students practise speaking answers with live feedback.
"""
)
