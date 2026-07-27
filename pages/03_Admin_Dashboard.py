import hmac
import os
import pandas as pd
import streamlit as st
from pandas.errors import EmptyDataError

st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🔒",
    layout="wide",
)

REPORTS_FILE = "data/all_student_reports.csv"

# ---------- Session state defaults ----------
if "admin_status" not in st.session_state:
    st.session_state.admin_status = "unverified"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "role" not in st.session_state:
    st.session_state.role = None

if "user_name" not in st.session_state:
    st.session_state.user_name = "Admin"


# ---------- Auth helpers ----------
def logout_admin():
    st.session_state.admin_status = "unverified"
    st.session_state.is_admin = False
    st.session_state.role = None


def check_admin_password(entered_password: str):
    expected = st.secrets.get("ADMIN_PASSWORD", "")

    if expected and hmac.compare_digest(entered_password, expected):
        st.session_state.admin_status = "verified"
        st.session_state.is_admin = True
        st.session_state.role = "admin"
    else:
        st.session_state.admin_status = "incorrect"
        st.session_state.is_admin = False
        st.session_state.role = None


def admin_login_prompt():
    st.title("🔒 Admin Login")
    st.caption("Enter the admin password to access all student speaking reports.")

    with st.form("admin_login_form", clear_on_submit=True):
        entered_password = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        check_admin_password(entered_password)
        st.rerun()

    if st.session_state.admin_status == "incorrect":
        st.error("Incorrect admin password.")


def load_reports_dataframe(file_path: str):
    if not os.path.exists(file_path):
        return None, "missing"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()

        if not raw.strip():
            return None, "blank"

        df = pd.read_csv(file_path)

        if df.empty:
            return df, "headers_only"

        return df, "ok"

    except EmptyDataError:
        return None, "emptydata"
    except Exception as e:
        return None, f"error:{e}"


# ---------- Guard ----------
if not (
    st.session_state.get("admin_status") == "verified"
    and st.session_state.get("is_admin", False)
):
    admin_login_prompt()
    st.stop()


# ---------- Admin dashboard ----------
st.title("Admin Dashboard")
st.caption("View all saved student interview reports.")

top1, top2 = st.columns([4, 1])

with top2:
    if st.button("Logout", use_container_width=True):
        logout_admin()
        st.rerun()

with top1:
    st.success("Admin access granted.")

st.divider()

# ---------- Load all reports safely ----------
df, status = load_reports_dataframe(REPORTS_FILE)

if status == "missing":
    st.warning("No saved student reports file was found yet.")
    st.caption(f"Expected file path: {REPORTS_FILE}")

elif status in ["blank", "emptydata"]:
    st.warning("The reports file exists, but it has no readable report data yet.")
    st.caption("This usually means the file is empty, whitespace-only, or not yet initialized as a proper CSV.")

elif status == "headers_only":
    st.info("The reports file has column headers, but no student report rows yet.")

elif isinstance(status, str) and status.startswith("error:"):
    st.error(f"Could not load reports file: {status[6:]}")

elif df is not None:
    st.subheader("All Student Reports")

    filter_cols = st.columns(3)

    with filter_cols[0]:
        applicant_filter = st.text_input("Filter by applicant name")

    with filter_cols[1]:
        university_options = ["All"] + sorted(
            [u for u in df["University"].dropna().astype(str).unique()]
        ) if "University" in df.columns else ["All"]
        selected_university = st.selectbox("Filter by university", university_options)

    with filter_cols[2]:
        category_options = ["All"] + sorted(
            [c for c in df["Category"].dropna().astype(str).unique()]
        ) if "Category" in df.columns else ["All"]
        selected_category = st.selectbox("Filter by category", category_options)

    filtered_df = df.copy()

    if applicant_filter and "Applicant" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Applicant"].astype(str).str.contains(
                applicant_filter, case=False, na=False
            )
        ]

    if selected_university != "All" and "University" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["University"].astype(str) == selected_university
        ]

    if selected_category != "All" and "Category" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Category"].astype(str) == selected_category
        ]

    summary_cols = st.columns(4)

    with summary_cols[0]:
        st.metric("Total Report Rows", len(filtered_df))

    with summary_cols[1]:
        if "Applicant" in filtered_df.columns and not filtered_df.empty:
            st.metric("Unique Students", filtered_df["Applicant"].nunique())
        else:
            st.metric("Unique Students", "N/A")

    with summary_cols[2]:
        if "Score" in filtered_df.columns and not filtered_df.empty:
            numeric_scores = pd.to_numeric(filtered_df["Score"], errors="coerce")
            mean_score = numeric_scores.mean()
            st.metric("Average Score", f"{mean_score:.1f}" if pd.notna(mean_score) else "N/A")
        else:
            st.metric("Average Score", "N/A")

    with summary_cols[3]:
        if "Readiness" in filtered_df.columns and not filtered_df.empty:
            high_risk_count = (
                filtered_df["Readiness"]
                .astype(str)
                .str.contains("risk", case=False, na=False)
                .sum()
            )
            st.metric("Risk-labelled Rows", int(high_risk_count))
        else:
            st.metric("Risk-labelled Rows", "N/A")

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download visible reports (CSV)",
        data=csv_data,
        file_name="student_speaking_reports_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )

    with st.expander("Column visibility check"):
        st.write(list(filtered_df.columns))

st.divider()

st.subheader("Reports File Debug")
debug_info = {
    "admin_status": st.session_state.get("admin_status"),
    "is_admin": st.session_state.get("is_admin"),
    "role": st.session_state.get("role"),
    "user_name": st.session_state.get("user_name"),
    "reports_file": REPORTS_FILE,
    "reports_file_exists": os.path.exists(REPORTS_FILE),
    "reports_file_size_bytes": os.path.getsize(REPORTS_FILE) if os.path.exists(REPORTS_FILE) else None,
    "load_status": status,
}

if os.path.exists(REPORTS_FILE):
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            debug_info["first_300_chars"] = f.read(300)
    except Exception as e:
        debug_info["first_300_chars"] = f"Could not preview file: {e}"

st.json(debug_info)
