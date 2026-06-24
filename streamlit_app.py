import time
import requests
import streamlit as st
from datetime import datetime

API = "http://localhost:8000"

st.set_page_config(page_title="Welcome Sequence", page_icon="📬", layout="centered")

# ── session state defaults ───────────────────────────────────────────────────
for k, v in {
    "page":         "signup",
    "user":         None,
    "signup_time":  None,
    "shown_email":  False,
    "shown_sms":    False,
    "shown_tips":   False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def go(page: str):
    st.session_state.page = page


def elapsed() -> float:
    if not st.session_state.signup_time:
        return 0.0
    return (datetime.utcnow() - st.session_state.signup_time).total_seconds()


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 ── SIGNUP
# ════════════════════════════════════════════════════════════════════════════
def page_signup():
    st.markdown("<h2 style='text-align:center'>📬 Dynamic Welcome Sequence</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray'>Sign up and watch your welcome messages arrive live</p>", unsafe_allow_html=True)
    st.divider()

    with st.form("signup"):
        name  = st.text_input("Full Name",  placeholder="Ahmad Furrokh")
        email = st.text_input("Email",      placeholder="ahmad@gmail.com")
        phone = st.text_input("Phone",      placeholder="03001234567")
        submitted = st.form_submit_button("Sign Up →", use_container_width=True, type="primary")

    if submitted:
        if not name or not email or not phone:
            st.error("Please fill in all fields.")
            return
        try:
            resp = requests.post(f"{API}/signup", json={"name": name, "email": email, "phone": phone}, timeout=5)
        except requests.ConnectionError:
            st.error("❌ Backend not running. Start it first:\n```\nuvicorn src.main:app\n```")
            return

        if resp.status_code == 201:
            st.session_state.user        = resp.json()
            st.session_state.signup_time = datetime.utcnow()
            st.session_state.shown_email = False
            st.session_state.shown_sms   = False
            st.session_state.shown_tips  = False
            go("live")
            st.rerun()
        elif resp.status_code == 409:
            st.error("⚠️ Email already registered — try a different one.")
        else:
            st.error(f"Server error: {resp.status_code}")

    st.divider()
    st.button("📋 View all users & schedules", on_click=go, args=("schedules",), use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 ── LIVE FEED
# ════════════════════════════════════════════════════════════════════════════
def page_live():
    user = st.session_state.user
    secs = elapsed()

    st.markdown(f"<h2 style='text-align:center'>👋 Welcome, {user['name']}!</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:gray'>{user['email']}</p>", unsafe_allow_html=True)
    st.divider()

    # ── toast popups (fire once each) ───────────────────────────────────────
    if not st.session_state.shown_email:
        st.toast("📧 Welcome email sent!", icon="✅")
        st.session_state.shown_email = True

    if secs >= 60 and not st.session_state.shown_sms:
        st.toast("📱 SMS sent!", icon="✅")
        st.session_state.shown_sms = True

    if secs >= 180 and not st.session_state.shown_tips:
        st.toast("💡 Final tips sent!", icon="✅")
        st.session_state.shown_tips = True

    # ── message cards ────────────────────────────────────────────────────────
    # EMAIL — always sent instantly
    st.success(
        "**📧 Welcome Email** — *Sent instantly*\n\n"
        f"Hi **{user['name']}**! Welcome aboard. We're so excited to have you with us. "
        "Get started by exploring your dashboard."
    )

    # SMS — after 60s
    if secs >= 60:
        st.success(
            "**📱 SMS Follow-up** — *Sent after 60s*\n\n"
            f"Hey {user['name']}! This is your SMS reminder. "
            "Reply HELP if you need any assistance. 😊"
        )
    else:
        remaining = int(60 - secs)
        st.info(f"⏳ **SMS Follow-up** — sending in **{remaining}s**…")

    # TIPS — after 180s (60+120)
    if secs >= 180:
        st.success(
            "**💡 Final Tips** — *Sent after 120s*\n\n"
            f"Hi {user['name']}! Here are your top 3 tips:\n"
            "1. Explore your dashboard\n"
            "2. Complete your profile\n"
            "3. Invite your team"
        )
    else:
        remaining = int(180 - secs)
        st.info(f"⏳ **Final Tips** — sending in **{remaining}s**…")

    st.divider()
    col1, col2 = st.columns(2)
    col1.button("🔄 New Signup",          on_click=go, args=("signup",),    use_container_width=True)
    col2.button("📋 View all schedules",  on_click=go, args=("schedules",), use_container_width=True)

    # auto-refresh every second until all done
    if secs < 180:
        time.sleep(1)
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 ── ALL USERS & SCHEDULES
# ════════════════════════════════════════════════════════════════════════════
def page_schedules():
    st.markdown("## 📋 Users & Schedules")
    st.divider()

    try:
        users     = requests.get(f"{API}/users",     timeout=5).json()
        schedules = requests.get(f"{API}/schedules", timeout=5).json()
    except requests.ConnectionError:
        st.error("❌ Backend not reachable.")
        return

    # ── Users table ──────────────────────────────────────────────────────────
    st.markdown(f"### 👥 Registered Users &nbsp; `{len(users)}`", unsafe_allow_html=True)
    if users:
        st.dataframe(users, use_container_width=True)
    else:
        st.info("No users registered yet.")

    # ── Schedules ────────────────────────────────────────────────────────────
    st.markdown(f"### 📨 Message Schedules &nbsp; `{len(schedules)}`", unsafe_allow_html=True)
    if schedules:
        for s in schedules:
            si = "✅" if s["status"] == "sent" else "⏳"
            ci = "📧" if s["channel"] == "email" else "📱"
            label = f"{si} {ci} **{s['message_type']}** — User #{s['user_id']} — `{s['status'].upper()}`"
            with st.expander(label):
                if s["status"] == "sent" and s.get("sent_at"):
                    due  = datetime.fromisoformat(s["send_at"])
                    sent = datetime.fromisoformat(s["sent_at"])
                    drift_s = (sent - due).total_seconds()
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Channel",   s["channel"])
                    col2.metric("Status",    s["status"])
                    col3.metric("Scheduled", s["send_at"][:16].replace("T", " "))
                    col4.metric("Drift", f"{drift_s:.1f}s", delta=f"{drift_s:.1f}s late", delta_color="inverse")
                else:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Channel",   s["channel"])
                    col2.metric("Status",    s["status"])
                    col3.metric("Scheduled", s["send_at"][:16].replace("T", " "))
    else:
        st.info("No schedules yet.")

    st.divider()
    col1, col2 = st.columns(2)
    col1.button("← Back to Sign Up",   on_click=go, args=("signup",), use_container_width=True)
    col2.button("🔄 Refresh",          on_click=go, args=("schedules",), use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════════════════════════════════════
{
    "signup":    page_signup,
    "live":      page_live,
    "schedules": page_schedules,
}.get(st.session_state.page, page_signup)()
