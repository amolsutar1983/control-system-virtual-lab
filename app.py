
import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import requests

st.set_page_config(
    page_title="Control Systems Virtual Laboratory",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Configuration / persistence
# -----------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))
FACULTY_PASSWORD = st.secrets.get("FACULTY_PASSWORD", os.getenv("FACULTY_PASSWORD", ""))

TABLE = "lab_submissions"

def db_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def db_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def save_submission(row):
    if not db_enabled():
        st.error("Online database is not configured. Add SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets.")
        return False
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{TABLE}"
        r = requests.post(url, headers=db_headers(), json=row, timeout=15)
        if r.status_code >= 300:
            st.error(f"Database error: {r.status_code} — {r.text[:300]}")
            return False
        return True
    except Exception as e:
        st.error(f"Could not save submission: {e}")
        return False

def load_submissions():
    if not db_enabled():
        return pd.DataFrame()
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{TABLE}"
        params = {"select": "*", "order": "submitted_at.desc", "limit": "2000"}
        r = requests.get(url, headers=db_headers(), params=params, timeout=15)
        if r.status_code >= 300:
            return pd.DataFrame()
        return pd.DataFrame(r.json())
    except Exception:
        return pd.DataFrame()

# -----------------------------
# Mathematics
# -----------------------------
def normalize_coeffs(text):
    vals = [float(x.strip()) for x in text.split(",") if x.strip()]
    if len(vals) < 2:
        raise ValueError("Enter at least two coefficients.")
    if abs(vals[0]) < 1e-12:
        raise ValueError("Leading coefficient cannot be zero.")
    return vals

def equation_string(c):
    n = len(c) - 1
    pieces = []
    for i, a in enumerate(c):
        p = n - i
        if abs(a) < 1e-12:
            continue
        sign = "+" if a >= 0 else "-"
        mag = abs(a)
        if p == 0:
            term = f"{mag:g}"
        elif p == 1:
            term = ("" if abs(mag-1) < 1e-12 else f"{mag:g}") + "s"
        else:
            term = ("" if abs(mag-1) < 1e-12 else f"{mag:g}") + f"s^{p}"
        if not pieces:
            pieces.append(("" if a >= 0 else "-") + term)
        else:
            pieces.append(f" {sign} {term}")
    return "".join(pieces) + " = 0"

def classify_roots(roots, tol=1e-7):
    re = np.real(roots)
    if np.all(re < -tol):
        return "STABLE", "All poles are in the left-half s-plane."
    if np.any(re > tol):
        return "UNSTABLE", "At least one pole lies in the right-half s-plane."
    return "MARGINAL / BOUNDARY", "A pole lies on or extremely close to the imaginary axis."

def routh_table(coeffs, eps=1e-9):
    """General Routh array for real-coefficient polynomial."""
    c = np.array(coeffs, dtype=float)
    order = len(c) - 1
    cols = int(np.ceil((order + 1) / 2))
    R = np.zeros((order + 1, cols), dtype=float)
    R[0, :len(c[0::2])] = c[0::2]
    R[1, :len(c[1::2])] = c[1::2]
    special = []
    for i in range(2, order + 1):
        if np.all(np.abs(R[i-1, :]) < eps):
            # Auxiliary polynomial from row above.
            special.append(i)
            power = order - (i - 2)
            for j in range(cols):
                p = power - 2*j
                R[i-1, j] = p * R[i-2, j] if p > 0 else 0.0
        if abs(R[i-1, 0]) < eps:
            R[i-1, 0] = eps
        for j in range(cols - 1):
            R[i, j] = (R[i-1, 0] * R[i-2, j+1] - R[i-2, 0] * R[i-1, j+1]) / R[i-1, 0]
    return R, special

def sign_changes(first_col, eps=1e-7):
    x = [v for v in first_col if abs(v) > eps]
    if len(x) < 2:
        return 0
    s = np.sign(x)
    return int(np.sum(s[1:] != s[:-1]))

def pole_figure(roots):
    fig = go.Figure()
    fig.add_shape(type="line", x0=0, x1=0, y0=0, y1=1, xref="x", yref="paper",
                  line=dict(color="gray", dash="dash"))
    fig.add_shape(type="line", x0=0, x1=1, y0=0, y1=0, xref="paper", yref="y",
                  line=dict(color="gray", dash="dash"))
    re = np.real(roots)
    im = np.imag(roots)
    labels = [f"p{i+1}" for i in range(len(roots))]
    hover = [f"{labels[i]} = {roots[i].real:.4f} {'+' if roots[i].imag >= 0 else '-'} {abs(roots[i].imag):.4f}j"
             for i in range(len(roots))]
    fig.add_trace(go.Scatter(
        x=re, y=im, mode="markers+text", text=labels, textposition="top center",
        hovertext=hover, hoverinfo="text",
        marker=dict(size=13, symbol="x", line=dict(width=2))
    ))
    span = max(1.0, float(np.max(np.abs(re))) if len(re) else 1.0, float(np.max(np.abs(im))) if len(im) else 1.0)
    fig.update_layout(
        height=430, margin=dict(l=20,r=20,t=35,b=20),
        title="Pole Map — updates when K changes",
        xaxis_title="Real axis σ", yaxis_title="Imaginary axis jω",
        xaxis=dict(range=[-1.25*span, 1.25*span]),
        yaxis=dict(range=[-1.25*span, 1.25*span], scaleanchor="x", scaleratio=1),
        showlegend=False,
    )
    return fig

# -----------------------------
# Mobile-friendly styling
# -----------------------------
st.markdown("""
<style>
.block-container {max-width: 1250px; padding-top: 1rem; padding-bottom: 2rem;}
h1 {font-size: clamp(1.7rem, 5vw, 2.6rem) !important;}
h2 {font-size: clamp(1.35rem, 4vw, 2rem) !important;}
.stButton > button, .stDownloadButton > button {width: 100%; min-height: 44px;}
div[data-testid="stMetricValue"] {font-size: 1.25rem;}
.small-note {color:#666; font-size:0.9rem;}
.lab-card {padding:1rem; border:1px solid #ddd; border-radius:14px; margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.title("🎛️ Control Systems Virtual Laboratory")
st.caption("Online • Mobile friendly • Multi-student • Interactive stability laboratory")

if not db_enabled():
    st.warning("Demo mode: the online database is not connected yet. Configure Supabase Secrets before publishing for real class-wide submissions.")

# -----------------------------
# Navigation
# -----------------------------
page = st.radio(
    "Go to",
    ["🧪 Student Lab", "📘 Workbook", "👨‍🏫 Faculty Dashboard", "ℹ️ About"],
    horizontal=True,
    label_visibility="collapsed",
)

# -----------------------------
# Student lab
# -----------------------------
if page == "🧪 Student Lab":
    st.subheader("Experiment 1 — Conditional Stability by Routh-Hurwitz")

    with st.container(border=True):
        st.markdown("**Learning objective:** Determine stability from the characteristic equation, predict the effect of parameter K, and verify the prediction from pole locations.")
        preset = st.selectbox(
            "Choose a laboratory system",
            [
                "s³ + 4s² + 5s + K = 0",
                "s² + 5s + K = 0",
                "s⁴ + 5s³ + 6s² + 4s + K = 0",
                "Custom characteristic equation",
            ],
        )
        defaults = {
            "s³ + 4s² + 5s + K = 0": "1,4,5,1",
            "s² + 5s + K = 0": "1,5,1",
            "s⁴ + 5s³ + 6s² + 4s + K = 0": "1,5,6,4,1",
        }
        coeff_text = st.text_input(
            "Polynomial coefficients, highest power first",
            value=defaults.get(preset, "1,4,5,1"),
            help="Example: 1,4,5,K is entered as 1,4,5,1 and K below replaces the final coefficient.",
        )

        try:
            base = normalize_coeffs(coeff_text)
        except Exception as e:
            st.error(str(e))
            st.stop()

        use_k = st.checkbox("Use adjustable K for the constant term", value=True)
        if use_k:
            K = st.slider("Gain / parameter K", -50.0, 50.0, float(base[-1]), 0.1)
            coeffs = base[:-1] + [K]
        else:
            K = None
            coeffs = base

        st.latex(equation_string(coeffs).replace("s^", "s^"))
        roots = np.roots(coeffs)
        status, explanation = classify_roots(roots)

    m1, m2, m3 = st.columns(3)
    m1.metric("System order", len(coeffs)-1)
    m2.metric("Current K", "—" if K is None else f"{K:g}")
    m3.metric("Stability", status)

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.plotly_chart(pole_figure(roots), use_container_width=True)
    with right:
        st.markdown("### Pole locations")
        pole_df = pd.DataFrame({
            "Pole": [f"p{i+1}" for i in range(len(roots))],
            "Real": [round(z.real, 6) for z in roots],
            "Imaginary": [round(z.imag, 6) for z in roots],
            "Magnitude": [round(abs(z), 6) for z in roots],
        })
        st.dataframe(pole_df, use_container_width=True, hide_index=True)
        st.info(explanation)

    st.markdown("### Routh-Hurwitz analysis")
    R, special = routh_table(coeffs)
    routh_df = pd.DataFrame(
        np.round(R, 5),
        index=[f"s^{len(coeffs)-1-i}" for i in range(len(coeffs))],
        columns=[f"col {j+1}" for j in range(R.shape[1])]
    )
    st.dataframe(routh_df, use_container_width=True)
    first_col = R[:,0]
    changes = sign_changes(first_col)
    st.write(f"**Routh first-column sign changes:** {changes} → predicted right-half-plane poles.")
    if special:
        st.caption("A special Routh case (zero row/near-zero pivot) was encountered and handled numerically.")

    st.markdown("### Student investigation")
    with st.form("student_workbook", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            student_name = st.text_input("Student name *")
        with c2:
            roll_no = st.text_input("Roll number / ID *")

        prediction = st.text_area("1. Before changing K, what stability trend do you predict?")
        boundary = st.text_input("2. Approximate K at which the system reaches the stability boundary.")
        observations = st.text_area("3. What happens to the poles as K changes?")
        explanation_student = st.text_area("4. Explain the Routh-Hurwitz result in your own words.")
        reflection = st.text_area("5. One engineering insight you learned from this experiment.")

        submitted = st.form_submit_button("Submit experiment", type="primary")
        if submitted:
            if not student_name.strip() or not roll_no.strip():
                st.error("Please enter your name and roll number.")
            else:
                row = {
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "student_name": student_name.strip(),
                    "roll_no": roll_no.strip(),
                    "experiment": "Conditional Stability / Routh-Hurwitz",
                    "equation": equation_string(coeffs),
                    "coefficients": ",".join(f"{x:g}" for x in coeffs),
                    "K": None if K is None else float(K),
                    "system_order": len(coeffs)-1,
                    "status": status,
                    "routh_sign_changes": changes,
                    "poles": "; ".join(f"{z.real:.6f}{z.imag:+.6f}j" for z in roots),
                    "prediction": prediction.strip(),
                    "boundary": boundary.strip(),
                    "observations": observations.strip(),
                    "explanation": explanation_student.strip(),
                    "reflection": reflection.strip(),
                }
                if save_submission(row):
                    st.success("Submitted successfully. Your workbook has been cleared for the next attempt.")

# -----------------------------
# Workbook
# -----------------------------
elif page == "📘 Workbook":
    st.subheader("📘 My / Class Workbook")
    st.write("Students submit directly from the laboratory. Faculty can view the class record from the dashboard.")
    if not db_enabled():
        st.info("Connect the online database to see class submissions here.")
    else:
        df = load_submissions()
        if df.empty:
            st.info("No submissions yet.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

# -----------------------------
# Faculty dashboard
# -----------------------------
elif page == "👨‍🏫 Faculty Dashboard":
    st.subheader("👨‍🏫 Faculty Dashboard")
    if FACULTY_PASSWORD:
        pw = st.text_input("Faculty password", type="password")
        if pw != FACULTY_PASSWORD:
            st.info("Enter the faculty password to continue.")
            st.stop()
    else:
        st.warning("No faculty password is configured. Set FACULTY_PASSWORD in Streamlit Secrets before public deployment.")

    if db_enabled():
        df = load_submissions()
        if df.empty:
            st.info("No submissions found.")
        else:
            a,b,c = st.columns(3)
            a.metric("Submissions", len(df))
            b.metric("Students", df["roll_no"].nunique())
            c.metric("Experiments", df["experiment"].nunique())

            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download class CSV", csv, "control_systems_lab_submissions.csv", "text/csv")
    else:
        st.info("Connect Supabase to enable the live faculty dashboard.")

# -----------------------------
# About / deployment
# -----------------------------
else:
    st.subheader("About this laboratory")
    st.markdown("""
    This is designed as a **real online virtual laboratory**, not a Python program that students install.

    **Student side**
    - Opens in Android Chrome, iPhone Safari, tablet, laptop, or desktop.
    - Interactive K slider and live pole map.
    - General characteristic-polynomial input.
    - Automatic pole calculation and stability classification.
    - General Routh array.
    - Digital experiment workbook and submission.

    **Faculty side**
    - Central class submission database.
    - Student-wise records.
    - Downloadable CSV.
    - Live dashboard.

    **Recommended deployment architecture**

    `Student Android/PC → HTTPS Streamlit application → Supabase cloud database`

    The project is ready to deploy on Streamlit Community Cloud or another Python hosting service.
    """)
    st.info("Important: do not put database secrets directly in app.py or GitHub. Use Streamlit Secrets / environment variables.")
