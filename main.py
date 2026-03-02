import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import os
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# ============================
# הגדרת הדף
# ============================
st.set_page_config(
    page_title="שיעבודא פון",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================
# CSS גלובלי
# ============================
def inject_css():
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        direction: rtl;
        font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    }
    .stApp { direction: rtl; background-color: #f0f2f6; }
    #MainMenu, footer, .stDeployButton { visibility: hidden; }
    .block-container { padding-top: 0.5rem !important; }

    /* ===== HEADER ===== */
    .top-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 14px 32px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 3px 12px rgba(0,0,0,0.3);
        margin-bottom: 0;
    }
    .header-logo {
        color: #e8b84b;
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: 1px;
    }
    .header-nav { display: flex; gap: 8px; align-items: center; }
    .header-nav button {
        background: transparent;
        border: 1px solid rgba(255,255,255,0.25);
        color: #ccd6f6;
        padding: 6px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
        font-family: inherit;
    }
    .header-nav button:hover { background: #e8b84b; color: #1a1a2e; border-color: #e8b84b; }
    .header-nav button.active { background: #e8b84b; color: #1a1a2e; border-color: #e8b84b; font-weight: 700; }

    /* ===== LOGIN PAGE ===== */
    .login-wrapper {
        min-height: 90vh;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding: 40px;
        background: linear-gradient(135deg, rgba(15,52,96,0.85) 0%, rgba(26,26,46,0.7) 100%),
                    url('https://images.unsplash.com/photo-1601597111158-2fceff292cdc?w=1600') center/cover;
    }
    .login-box {
        background: rgba(255,255,255,0.97);
        border-radius: 20px;
        padding: 44px 40px;
        box-shadow: 0 16px 48px rgba(0,0,0,0.3);
        width: 100%;
        max-width: 420px;
        backdrop-filter: blur(10px);
    }
    .login-title {
        text-align: center;
        font-size: 1.7rem;
        font-weight: 800;
        color: #1a1a2e;
        margin-bottom: 6px;
    }
    .login-subtitle {
        text-align: center;
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 28px;
    }

    /* ===== METRIC CARDS ===== */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 22px 26px;
        box-shadow: 0 3px 14px rgba(0,0,0,0.07);
        text-align: center;
        height: 100%;
    }
    .metric-card .mc-label { color: #888; font-size: 0.82rem; margin-bottom: 6px; }
    .metric-card .mc-value { font-size: 2rem; font-weight: 800; color: #1a1a2e; }
    .metric-card .mc-sub { font-size: 0.72rem; color: #aaa; margin-top: 4px; }

    /* ===== SMART CARDS ===== */
    .smart-card {
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        direction: rtl;
        transition: transform 0.15s;
    }
    .smart-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,0.1); }
    .smart-card.debit  { background: #fff5f5; border-right: 5px solid #e53935; }
    .smart-card.credit { background: #f0fff4; border-right: 5px solid #43a047; }
    .smart-card.failed { background: #fff8e1; border-right: 5px solid #f9a825; }
    .smart-card.admin  { background: #e8f4ff; border-right: 5px solid #1e88e5; }

    .card-circle {
        min-width: 58px; height: 58px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.8rem; flex-shrink: 0; text-align: center;
    }
    .debit  .card-circle { background: #ffcdd2; color: #b71c1c; }
    .credit .card-circle { background: #c8e6c9; color: #1b5e20; }
    .failed .card-circle { background: #fff3e0; color: #e65100; }
    .admin  .card-circle { background: #bbdefb; color: #0d47a1; }

    .card-main { flex: 1; min-width: 0; }
    .card-main .c-title { font-weight: 600; font-size: 0.88rem; color: #1a1a2e; margin-bottom: 3px; }
    .card-main .c-sub   { font-size: 0.78rem; color: #666; }

    .card-side { text-align: left; min-width: 110px; flex-shrink: 0; }
    .badge {
        display: inline-block; padding: 2px 9px; border-radius: 12px;
        font-size: 0.7rem; font-weight: 700; margin-bottom: 4px;
    }
    .badge-ok     { background: #e8f5e9; color: #2e7d32; }
    .badge-failed { background: #fff3e0; color: #e65100; }
    .badge-admin  { background: #e3f2fd; color: #1565c0; }
    .c-date  { font-size: 0.72rem; color: #999; margin: 3px 0; }
    .c-phone { font-size: 0.68rem; color: #bbb; }

    /* ===== INFO PAGES ===== */
    .info-page {
        max-width: 820px; margin: 30px auto;
        background: white; border-radius: 16px;
        padding: 44px 48px;
        box-shadow: 0 2px 14px rgba(0,0,0,0.07);
        line-height: 1.9;
    }
    .info-page h2 { color: #0f3460; border-bottom: 2px solid #e8b84b; padding-bottom: 8px; }

    /* ===== FLOATING CHATBOT ===== */
    .chat-fab {
        position: fixed; bottom: 28px; left: 28px;
        width: 58px; height: 58px; border-radius: 50%;
        background: linear-gradient(135deg, #0f3460, #e8b84b);
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 18px rgba(0,0,0,0.28);
        z-index: 9999; font-size: 1.5rem; color: white;
        animation: pulse 2.5s infinite;
    }
    @keyframes pulse {
        0%   { box-shadow: 0 0 0 0 rgba(232,184,75,0.5); }
        70%  { box-shadow: 0 0 0 12px rgba(232,184,75,0); }
        100% { box-shadow: 0 0 0 0 rgba(232,184,75,0); }
    }
    .chat-panel {
        position: fixed; bottom: 95px; left: 28px;
        width: 360px; max-height: 480px;
        background: white; border-radius: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.18);
        z-index: 9998; overflow: hidden;
        display: flex; flex-direction: column;
    }
    .chat-panel-header {
        background: linear-gradient(135deg, #1a1a2e, #0f3460);
        color: white; padding: 14px 18px;
        font-weight: 700; font-size: 1rem;
        display: flex; justify-content: space-between; align-items: center;
    }
    .chat-panel-body { flex: 1; overflow-y: auto; padding: 14px; }

    /* ===== SECTION TITLES ===== */
    .section-title {
        font-size: 1.05rem; font-weight: 700; color: #0f3460;
        margin: 18px 0 10px; border-right: 4px solid #e8b84b; padding-right: 10px;
    }

    /* ===== PERSONAL DETAILS ===== */
    .detail-block {
        background: white; border-radius: 14px;
        padding: 26px 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        margin-bottom: 18px;
    }
    .detail-row { display: flex; gap: 16px; margin-bottom: 12px; align-items: baseline; }
    .detail-label { color: #888; font-size: 0.82rem; min-width: 110px; }
    .detail-value { font-weight: 600; color: #1a1a2e; font-size: 0.95rem; }

    .phone-tag {
        display: inline-block; background: #e8f4ff;
        color: #1565c0; border-radius: 20px;
        padding: 4px 14px; font-size: 0.85rem;
        margin: 4px; font-weight: 600;
    }
    .readonly-note {
        background: #fff8e1; border: 1px solid #ffe082;
        border-radius: 10px; padding: 12px 16px;
        font-size: 0.82rem; color: #795548; margin-top: 16px;
    }

    /* ===== PAGINATION ===== */
    .page-btn button {
        background: #0f3460 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# ============================
# משתנים גלובליים
# ============================
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'

SYSTEM_MANUAL = """
אתה הנציג הדיגיטלי של שיעבודא פון. תפקידך לשמש כמנתח נתונים של המשתמש.
מותר לך לסכם לו את הפעולות, לחשב הוצאות/הכנסות, ולענות על שאלות בצורה אדיבה ומקצועית.
אל תחשוף מידע על משתמשים אחרים. ענה תמיד בעברית.
"""

# ============================
# Backend – חיבורים
# ============================
@st.cache_resource
def get_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    secret_dir = "/etc/secrets"
    required_keys = [
        "type", "project_id", "private_key_id", "private_key",
        "client_email", "client_id", "auth_uri", "token_uri",
        "auth_provider_x509_cert_url", "client_x509_cert_url",
    ]
    creds_dict = {}
    for key in required_keys:
        path = os.path.join(secret_dir, key)
        if os.path.exists(path):
            with open(path, "r") as f:
                creds_dict[key] = f.read().strip()
                if key == "private_key":
                    creds_dict[key] = creds_dict[key].replace("\\n", "\n").replace('"', '')
    if "private_key" in creds_dict:
        return gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=scopes))
    json_path = os.path.join(secret_dir, "service_account.json")
    if os.path.exists(json_path):
        return gspread.authorize(Credentials.from_service_account_file(json_path, scopes=scopes))
    st.error("תקלה בחיבור לשיטס")
    st.stop()


@st.cache_resource
def get_api_keys():
    keys = []
    try:
        if "gemini_api_key" in st.secrets:
            val = st.secrets["gemini_api_key"]
            if isinstance(val, dict):
                raw_keys = val.get("api_keys", val.get("api_key", ""))
                keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            else:
                keys = [k.strip() for k in str(val).split(",") if k.strip()]
    except Exception:
        pass
    if not keys:
        for path in ["/etc/secrets/api_key", "/etc/secrets/gemini_api_key"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read().strip().replace('"', '').replace("'", "")
                    keys = [k.strip() for k in content.split(",") if k.strip()]
                break
    return keys


@st.cache_data(ttl=600)   # עדכון כל 10 דקות
def get_all_data():
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    df_users = pd.DataFrame(sh.worksheet("משתמשים").get_all_records())
    df_actions = pd.DataFrame(sh.worksheet("פעולות").get_all_records())
    try:
        admin_ids = pd.DataFrame(sh.worksheet("מנהלים").get_all_records()).iloc[:, 0].astype(str).tolist()
    except Exception:
        admin_ids = []
    return df_users, df_actions, admin_ids


@st.cache_data(ttl=600)
def get_cms_content():
    """שולף תוכן דינמי (קצת עלינו / צור קשר / תקנון) מגיליון 'תוכן'."""
    defaults = {
        "קצת עלינו": "**שיעבודא פון** – מערכת ניהול חשבונות מתקדמת.\n\nאנחנו מספקים שירות מהיר, בטוח ושקוף.",
        "צור קשר": "לפניות ותמיכה:\n📞 054-0000000\n📧 support@shiabudefon.com",
        "תקנון": "השימוש במערכת כפוף לתנאי השימוש. כל הפעולות מבוצעות בצורה מאובטחת.",
    }
    try:
        client = get_client()
        sh = client.open_by_key(SPREADSHEET_ID)
        df = pd.DataFrame(sh.worksheet("תוכן").get_all_records())
        for _, row in df.iterrows():
            key = str(row.get("כותרת", "")).strip()
            val = str(row.get("תוכן", "")).strip()
            if key and val:
                defaults[key] = val
    except Exception:
        pass
    return defaults


# ============================
# עיבוד נתונים
# ============================
def process_user_actions(df_actions: pd.DataFrame, user_id: str) -> pd.DataFrame:
    if df_actions.empty:
        return pd.DataFrame()
    df = df_actions.copy()
    df["מספר משתמש מקור"] = df["מספר משתמש מקור"].astype(str)
    df["מספר משתמש יעד"]  = df["מספר משתמש יעד"].astype(str)
    uid = str(user_id)
    mask = (df["מספר משתמש מקור"] == uid) | (df["מספר משתמש יעד"] == uid)
    my = df[mask].copy()
    if my.empty:
        return pd.DataFrame()

    def enrich(row):
        is_sender = str(row["מספר משתמש מקור"]) == uid
        try:
            amount = float(row.get("סכום", 0))
        except Exception:
            amount = 0
        direction = "חובה" if is_sender else "זכות"
        net = -amount if is_sender else amount
        desc = f"העברה אל {row.get('שם יעד','')} ({row.get('מספר משתמש יעד','')})" if is_sender \
               else f"התקבל מ-{row.get('שם מקור','')} ({row.get('מספר משתמש מקור','')})"
        return pd.Series({"כיוון": direction, "סכום נטו": net, "תיאור": desc})

    enriched = my.apply(enrich, axis=1)
    my = pd.concat([my.reset_index(drop=True), enriched.reset_index(drop=True)], axis=1)
    return my


def get_user_balance(df_users: pd.DataFrame, user_id: str) -> float:
    df_users["מספר משתמש"] = df_users["מספר משתמש"].astype(str).str.strip()
    row = df_users[df_users["מספר משתמש"] == str(user_id)]
    if row.empty:
        return 0.0
    try:
        return float(row.iloc[0]["יתרה"])
    except Exception:
        return 0.0


# ============================
# רינדור כרטיסייה חכמה
# ============================
def render_smart_card(row: pd.Series):
    status = str(row.get("סטטוס", "מוצלחת")).strip()
    direction = str(row.get("כיוון", "חובה")).strip()
    is_admin_op = "מנהל" in status.lower()

    if is_admin_op:
        cls, badge_cls, badge_txt = "admin", "badge-admin", "פעולת מנהל"
    elif "כושלת" in status or "נכשל" in status:
        cls, badge_cls, badge_txt = "failed", "badge-failed", "כושלת"
    elif direction == "זכות":
        cls, badge_cls, badge_txt = "credit", "badge-ok", "מוצלחת"
    else:
        cls, badge_cls, badge_txt = "debit", "badge-ok", "מוצלחת"

    try:
        amount = abs(float(row.get("סכום", 0)))
        amount_str = f"₪{amount:,.0f}"
    except Exception:
        amount_str = "₪-"

    desc   = row.get("תיאור", "")
    after  = row.get("יתרה לאחר פעולה", row.get("יתרה", ""))
    date   = row.get("תאריך", "")
    time   = row.get("שעה", "")
    phone  = row.get("טלפון", row.get("מבצע", ""))

    after_str = f"₪{float(after):,.2f}" if after not in ("", None) else ""

    st.markdown(f"""
    <div class="smart-card {cls}">
        <div class="card-circle">{amount_str}</div>
        <div class="card-main">
            <div class="c-title">{desc}</div>
            {'<div class="c-sub">יתרה לאחר פעולה: ' + after_str + '</div>' if after_str else ''}
        </div>
        <div class="card-side">
            <span class="badge {badge_cls}">{badge_txt}</span>
            <div class="c-date">{date} {time}</div>
            {'<div class="c-phone">📱 ' + str(phone) + '</div>' if phone else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================
# Header גלובלי
# ============================
def render_header(current_page: str):
    pages = {"app": "🏠 ראשי", "about": "קצת עלינו", "contact": "צור קשר", "terms": "תקנון"}
    if st.session_state.get("authenticated"):
        pages["app"] = "🏠 אזור אישי"

    cols = st.columns([3, 5, 2])
    with cols[0]:
        st.markdown('<div class="header-logo">💰 שיעבודא פון</div>', unsafe_allow_html=True)
    with cols[1]:
        btns = st.columns(len(pages))
        for i, (page_key, label) in enumerate(pages.items()):
            with btns[i]:
                active = "primary" if current_page == page_key else "secondary"
                if st.button(label, key=f"nav_{page_key}", type=active, use_container_width=True):
                    st.session_state.page = page_key
                    st.rerun()
    with cols[2]:
        if st.session_state.get("authenticated"):
            if st.button("🚪 יציאה", type="secondary", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.page = "login"
                st.rerun()
        else:
            if st.button("🔑 כניסה", type="primary", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()

    st.divider()


# ============================
# Floating Chatbot
# ============================
def render_floating_chatbot():
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    col_fab, _ = st.columns([1, 9])
    with col_fab:
        icon = "✕" if st.session_state.show_chat else "💬"
        if st.button(icon, key="chat_fab_btn", help="בוט שירות"):
            st.session_state.show_chat = not st.session_state.show_chat
            st.rerun()

    if st.session_state.show_chat:
        with st.expander("🤖 בוט שיעבודא פון – שירות 24/7", expanded=True):
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            if prompt := st.chat_input("שאל אותי..."):
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("חושב..."):
                        api_keys_pool = get_api_keys()
                        u = st.session_state.get("user", {})
                        uid = str(u.get("מספר משתמש", ""))
                        if uid:
                            df_users, df_actions, _ = get_all_data()
                            my_act = process_user_actions(df_actions, uid)
                            curr_row = df_users[df_users["מספר משתמש"].astype(str) == uid]
                            context = f"פרטים:\n{curr_row.to_csv()}\nפעולות:\n{my_act.to_csv()}"
                        else:
                            context = "המשתמש לא מחובר."

                        reply = "מצטער, לא הצלחתי לקבל תשובה."
                        for key in api_keys_pool:
                            try:
                                genai.configure(api_key=key)
                                valid_model = "gemini-pro"
                                for m in genai.list_models():
                                    if "generateContent" in m.supported_generation_methods:
                                        valid_model = m.name
                                        if "flash" in m.name.lower():
                                            break
                                model = genai.GenerativeModel(valid_model)
                                res = model.generate_content(
                                    f"{SYSTEM_MANUAL}\n{context}\nשאלה: {prompt}",
                                    generation_config=genai.types.GenerationConfig(max_output_tokens=400),
                                )
                                reply = res.text
                                break
                            except Exception:
                                continue
                        st.write(reply)
                        st.session_state.chat_messages.append({"role": "assistant", "content": reply})


# ============================
# דף כניסה
# ============================
def render_login_page():
    st.markdown("""
    <div class="login-wrapper">
        <div class="login-box">
            <div class="login-title">🔐 כניסה למערכת</div>
            <div class="login-subtitle">שיעבודא פון | ניהול חשבון אישי</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        with st.container():
            st.markdown("##### 🔐 כניסה למערכת")
            with st.form("login_form", clear_on_submit=False):
                uid = st.text_input("👤 מספר משתמש", placeholder="הזן מספר משתמש")
                pwd = st.text_input("🔒 סיסמה", type="password", placeholder="הזן סיסמה",
                                    help="לחץ על 👁 להצגת הסיסמה")
                submitted = st.form_submit_button("🔓 התחבר", use_container_width=True, type="primary")
                if submitted:
                    try:
                        df_users, _, admin_ids = get_all_data()
                        df_users["מספר משתמש"] = df_users["מספר משתמש"].astype(str).str.strip()
                        df_users["סיסמה"] = df_users["סיסמה"].astype(str).str.strip()
                        uid_c, pwd_c = uid.strip(), pwd.strip()
                        user = df_users[(df_users["מספר משתמש"] == uid_c) & (df_users["סיסמה"] == pwd_c)]
                        if not user.empty:
                            st.session_state.authenticated = True
                            st.session_state.user = user.iloc[0].to_dict()
                            st.session_state.is_admin = uid_c in [str(x).strip() for x in admin_ids]
                            st.session_state.page = "app"
                            st.rerun()
                        else:
                            st.error("⚠️ מספר משתמש או סיסמה שגויים")
                    except Exception as e:
                        st.error(f"שגיאה: {e}")
            st.caption("אין אפשרות הרשמה עצמאית או שחזור סיסמה. לפרטים חייג למערכת הטלפונית.")


# ============================
# Tab 1 – דשבורד
# ============================
def render_dashboard(u, is_admin, df_users, df_actions):
    uid = str(u.get("מספר משתמש", ""))
    balance = get_user_balance(df_users, uid)
    sync_time = datetime.now().strftime("%H:%M")

    # --- ברכה ---
    st.markdown(f"### שלום, {u.get('שם משתמש', '')} | מספר משתמש: {uid}")

    # --- קוביות נתונים ---
    total_volume = 0
    try:
        total_volume = pd.to_numeric(df_actions.get("סכום", pd.Series()), errors="coerce").sum()
    except Exception:
        pass

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="mc-label">💰 יתרה נוכחית</div>
            <div class="mc-value" style="color:#0f3460">₪{balance:,.2f}</div>
            <div class="mc-sub">⏱ עודכן בשעה {sync_time} (כל 10 דקות)</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="mc-label">🔄 מחזור כללי במערכת</div>
            <div class="mc-value" style="color:#388e3c">₪{total_volume:,.0f}</div>
            <div class="mc-sub">סך כל הפעולות</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        my_act = process_user_actions(df_actions, uid)
        cnt = len(my_act)
        st.markdown(f"""
        <div class="metric-card">
            <div class="mc-label">📋 פעולות בחשבוני</div>
            <div class="mc-value" style="color:#6a1b9a">{cnt}</div>
            <div class="mc-sub">סך הכל פעולות</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    col_chart, col_feed = st.columns([1, 1.4])

    # --- גרף עמודות ---
    with col_chart:
        st.markdown('<div class="section-title">📊 גרף פעילות</div>', unsafe_allow_html=True)
        if not my_act.empty:
            view = st.radio("תקופה", ["החודש הנוכחי", "כל הפעולות"], horizontal=True, key="dash_view")
            df_chart = my_act.copy()
            if view == "החודש הנוכחי":
                cur_month = datetime.now().strftime("%Y-%m")
                if "תאריך" in df_chart.columns:
                    df_chart = df_chart[df_chart["תאריך"].astype(str).str.startswith(cur_month)]

            if not df_chart.empty:
                try:
                    df_chart["סכום נטו"] = pd.to_numeric(df_chart["סכום נטו"], errors="coerce").fillna(0)
                    df_chart["צבע"] = df_chart["סכום נטו"].apply(lambda x: "הכנסה" if x >= 0 else "הוצאה")
                    fig = px.bar(
                        df_chart.tail(20), y="סכום נטו", color="צבע",
                        color_discrete_map={"הכנסה": "#43a047", "הוצאה": "#e53935"},
                        title="", height=280,
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0),
                        showlegend=True, legend_title="",
                        xaxis_title="", yaxis_title="₪",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.info("אין מספיק נתונים לגרף")
            else:
                st.info("אין פעולות בתקופה זו")
        else:
            st.info("עדיין אין פעולות בחשבון")

    # --- 5 פעולות אחרונות ---
    with col_feed:
        st.markdown('<div class="section-title">⚡ 5 פעולות אחרונות</div>', unsafe_allow_html=True)
        if is_admin:
            feed_df = df_actions.tail(5)
            for _, row in feed_df.iterrows():
                render_smart_card(row)
        else:
            if not my_act.empty:
                for _, row in my_act.tail(5).iloc[::-1].iterrows():
                    render_smart_card(row)
            else:
                st.info("אין פעולות להצגה")


# ============================
# Tab 2 – עובר ושב
# ============================
def render_history(u, is_admin, df_users, df_actions):
    uid = str(u.get("מספר משתמש", ""))

    if is_admin:
        my_act = df_actions.copy()
        try:
            my_act["כיוון"] = "חובה"
            my_act["תיאור"] = my_act.apply(
                lambda r: f"העברה מ-{r.get('שם מקור','')} אל {r.get('שם יעד','')}", axis=1)
            my_act["סכום נטו"] = pd.to_numeric(my_act.get("סכום", 0), errors="coerce").fillna(0)
        except Exception:
            pass
    else:
        my_act = process_user_actions(df_actions, uid)

    if my_act.empty:
        st.info("אין פעולות להצגה")
        return

    # --- סנכרון עמודות ---
    for col in ["תאריך", "שעה", "סכום", "סטטוס", "כיוון", "תיאור", "שם מקור", "שם יעד"]:
        if col not in my_act.columns:
            my_act[col] = ""

    my_act["סכום_num"] = pd.to_numeric(my_act["סכום"], errors="coerce").fillna(0)

    # ===== גרפים חכמים =====
    st.markdown('<div class="section-title">📈 אנליטיקס</div>', unsafe_allow_html=True)
    tab_pie, tab_line = st.tabs(["🥧 לאן הכסף עבר?", "📉 מגמת יתרה"])

    with tab_pie:
        try:
            debits = my_act[my_act["כיוון"] == "חובה"].copy()
            if not debits.empty and "שם יעד" in debits.columns:
                pie_df = debits.groupby("שם יעד")["סכום_num"].sum().reset_index()
                pie_df.columns = ["שם", "סכום"]
                fig_pie = px.pie(pie_df, names="שם", values="סכום",
                                 title="פילוח הוצאות לפי יעד", hole=0.35)
                fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("אין נתוני הוצאות")
        except Exception as e:
            st.warning(f"שגיאה בגרף: {e}")

    with tab_line:
        try:
            if "תאריך" in my_act.columns and "סכום נטו" in my_act.columns:
                line_df = my_act[["תאריך", "סכום נטו"]].copy()
                line_df["סכום נטו"] = pd.to_numeric(line_df["סכום נטו"], errors="coerce").fillna(0)
                line_df = line_df.sort_values("תאריך")
                line_df["יתרה_מצטברת"] = line_df["סכום נטו"].cumsum()
                fig_line = px.line(line_df, x="תאריך", y="יתרה_מצטברת",
                                   title="מגמת יתרה לאורך זמן",
                                   markers=True, color_discrete_sequence=["#0f3460"])
                fig_line.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("אין מספיק נתונים לגרף קווי")
        except Exception as e:
            st.warning(f"שגיאה בגרף: {e}")

    st.divider()

    # ===== סרגל סינון =====
    st.markdown('<div class="section-title">🔍 סינון וחיפוש</div>', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 2, 2])

    with fc1:
        search_text = st.text_input("🔎 חיפוש חופשי (שם / מספר / מזהה)", "")

    with fc2:
        date_filter = st.selectbox("📅 תקופה", ["הכל", "החודש הנוכחי", "חודש קודם", "טווח מותאם"])
        if date_filter == "טווח מותאם":
            d1, d2 = st.columns(2)
            with d1:
                date_from = st.date_input("מ-", key="df")
            with d2:
                date_to = st.date_input("עד", key="dt")
        else:
            date_from = date_to = None

    with fc3:
        status_filter = st.multiselect(
            "סטטוס",
            ["הכל", "זכות", "חובה", "כושלות", "פעולות מנהל"],
            default=["הכל"],
        )

    fc4, fc5 = st.columns([2, 2])
    with fc4:
        min_amt = st.number_input("סכום מינימלי ₪", value=0.0, step=10.0)
    with fc5:
        max_amt = st.number_input("סכום מקסימלי ₪", value=999999.0, step=100.0)

    # --- החלת סינונים ---
    filtered = my_act.copy()

    if search_text:
        mask = filtered.apply(lambda r: search_text.lower() in " ".join(r.astype(str).values).lower(), axis=1)
        filtered = filtered[mask]

    if date_filter == "החודש הנוכחי":
        cur = datetime.now().strftime("%Y-%m")
        filtered = filtered[filtered["תאריך"].astype(str).str.startswith(cur)]
    elif date_filter == "חודש קודם":
        lm = (datetime.now().replace(day=1) - pd.Timedelta(days=1)).strftime("%Y-%m")
        filtered = filtered[filtered["תאריך"].astype(str).str.startswith(lm)]
    elif date_filter == "טווח מותאם" and date_from and date_to:
        filtered = filtered[
            (filtered["תאריך"].astype(str) >= str(date_from)) &
            (filtered["תאריך"].astype(str) <= str(date_to))
        ]

    if "הכל" not in status_filter and status_filter:
        conds = []
        if "זכות" in status_filter:
            conds.append(filtered["כיוון"] == "זכות")
        if "חובה" in status_filter:
            conds.append(filtered["כיוון"] == "חובה")
        if "כושלות" in status_filter:
            conds.append(filtered["סטטוס"].astype(str).str.contains("כושל|נכשל"))
        if "פעולות מנהל" in status_filter:
            conds.append(filtered["סטטוס"].astype(str).str.contains("מנהל"))
        if conds:
            import functools
            combined = functools.reduce(lambda a, b: a | b, conds)
            filtered = filtered[combined]

    filtered = filtered[
        (filtered["סכום_num"].abs() >= min_amt) &
        (filtered["סכום_num"].abs() <= max_amt)
    ]

    st.caption(f"נמצאו **{len(filtered)}** פעולות")

    # ===== ייצוא =====
    ex1, ex2, _ = st.columns([1, 1, 4])
    with ex1:
        try:
            buf = BytesIO()
            export_df = filtered.drop(columns=["סכום_num"], errors="ignore")
            export_df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button(
                "📥 ייצוא Excel",
                data=buf.getvalue(),
                file_name="shiabudefon_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            st.warning("התקן openpyxl לייצוא Excel")
    with ex2:
        try:
            html_table = filtered.drop(columns=["סכום_num"], errors="ignore").to_html(
                index=False, border=1, classes="export-table"
            )
            html_content = f"""
            <html><head><meta charset="UTF-8">
            <style>
            body{{direction:rtl; font-family:Arial; padding:20px}}
            h2{{color:#0f3460}} table{{border-collapse:collapse; width:100%}}
            th{{background:#0f3460;color:white;padding:8px}} td{{padding:6px;border:1px solid #ddd}}
            </style></head><body>
            <h2>שיעבודא פון – ייצוא נתונים</h2>
            <p>תאריך הפקה: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            {html_table}
            </body></html>"""
            st.download_button(
                "📄 ייצוא PDF (HTML להדפסה)",
                data=html_content.encode("utf-8"),
                file_name="shiabudefon_export.html",
                mime="text/html",
            )
        except Exception:
            pass

    # ===== דפדוף + כרטיסיות =====
    st.divider()
    PAGE_SIZE = 15
    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
    if "hist_page" not in st.session_state:
        st.session_state.hist_page = 0
    st.session_state.hist_page = min(st.session_state.hist_page, total_pages - 1)

    pg_col1, pg_col2, pg_col3 = st.columns([1, 2, 1])
    with pg_col1:
        if st.session_state.hist_page > 0:
            if st.button("◀ הקודם"):
                st.session_state.hist_page -= 1
                st.rerun()
    with pg_col2:
        st.markdown(f"<div style='text-align:center;color:#888'>עמוד {st.session_state.hist_page+1} מתוך {total_pages}</div>",
                    unsafe_allow_html=True)
    with pg_col3:
        if st.session_state.hist_page < total_pages - 1:
            if st.button("הבא ▶"):
                st.session_state.hist_page += 1
                st.rerun()

    start = st.session_state.hist_page * PAGE_SIZE
    page_df = filtered.iloc[::-1].reset_index(drop=True).iloc[start: start + PAGE_SIZE]

    for _, row in page_df.iterrows():
        render_smart_card(row)


# ============================
# Tab 3 – פרטים אישיים
# ============================
def render_personal(u, df_users):
    uid = str(u.get("מספר משתמש", ""))

    st.markdown('<div class="section-title">👤 החשבון שלי – פרטים מזהים</div>', unsafe_allow_html=True)

    user_row = df_users[df_users["מספר משתמש"].astype(str) == uid]
    user_data = user_row.iloc[0].to_dict() if not user_row.empty else u

    fields = [
        ("שם משתמש", "שם משתמש"),
        ("מספר משתמש", "מספר משתמש"),
        ("תעודת זהות", "תעודת זהות"),
        ("כתובת", "כתובת"),
        ("סיסמה נוכחית", "סיסמה"),
    ]
    rows_html = ""
    for label, key in fields:
        val = user_data.get(key, "—")
        rows_html += f'<div class="detail-row"><span class="detail-label">{label}:</span><span class="detail-value">{val}</span></div>'

    st.markdown(f"""
    <div class="detail-block">
        {rows_html}
        <div class="readonly-note">⚠️ המידע מוצג לקריאה בלבד. לעדכון פרטים אישיים או שינוי סיסמה, אנא חייג למערכת הטלפונית.</div>
    </div>""", unsafe_allow_html=True)

    # --- רשימת צינתוקים ---
    st.markdown('<div class="section-title">📱 ניהול רשימת צינתוקים</div>', unsafe_allow_html=True)

    phones_raw = user_data.get("צינתוקים", user_data.get("טלפונים", ""))
    phones = [p.strip() for p in str(phones_raw).split(",") if p.strip() and phones_raw]

    if phones:
        tags_html = "".join(f'<span class="phone-tag">📞 {p}</span>' for p in phones)
        count_txt = f"ברשימת הצינתוקים שלך רשומים כרגע <b>{len(phones)}</b> מספרים."
    else:
        tags_html = '<span style="color:#aaa">לא רשומים מספרים</span>'
        count_txt = "לא רשומים מספרים בצינתוקים."

    st.markdown(f"""
    <div class="detail-block">
        <div style="margin-bottom:12px;color:#555">{count_txt}</div>
        <div>{tags_html}</div>
        <div class="readonly-note">➕ להוספה, עריכה או הסרה של מספרים מרשימת הצינתוקים, אנא חייג למערכת הטלפונית.</div>
    </div>""", unsafe_allow_html=True)


# ============================
# אזור מנהל (Admin)
# ============================
def render_admin(df_users, df_actions):
    st.markdown("## 🛠️ לוח בקרה – מנהל מערכת")

    total_users = len(df_users)
    total_actions = len(df_actions)
    try:
        total_vol = pd.to_numeric(df_actions.get("סכום", pd.Series()), errors="coerce").sum()
    except Exception:
        total_vol = 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("👥 משתמשים רשומים", total_users)
    with c2:
        st.metric("📋 סך פעולות", total_actions)
    with c3:
        st.metric("💸 מחזור כולל", f"₪{total_vol:,.0f}")

    st.divider()
    atab1, atab2 = st.tabs(["📋 כל הפעולות", "👥 משתמשים"])
    with atab1:
        st.dataframe(df_actions.tail(50)[::-1], hide_index=True, use_container_width=True)
    with atab2:
        st.dataframe(df_users, hide_index=True, use_container_width=True)


# ============================
# דפי מידע (CMS)
# ============================
def render_info_page(title: str, content: str):
    st.markdown(f"""
    <div class="info-page">
        <h2>{title}</h2>
        <div>{content.replace(chr(10), '<br>')}</div>
    </div>""", unsafe_allow_html=True)


# ============================
# MAIN – ניהול ניווט
# ============================
def main():
    # Session state
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    page = st.session_state.page

    # אם מחובר וניסה לגשת לlogin – שלח לapp
    if st.session_state.authenticated and page == "login":
        st.session_state.page = "app"
        page = "app"

    render_header(page)

    # ===== דפי מידע (ציבוריים) =====
    if page in ("about", "contact", "terms"):
        cms = get_cms_content()
        titles = {"about": "קצת עלינו", "contact": "צור קשר", "terms": "תקנון"}
        key = titles[page]
        render_info_page(key, cms.get(key, ""))
        return

    # ===== דף כניסה =====
    if page == "login" or not st.session_state.authenticated:
        render_login_page()
        return

    # ===== אזור אישי =====
    u = st.session_state.user
    is_admin = st.session_state.get("is_admin", False)

    with st.spinner("טוען נתונים..."):
        df_users, df_actions, _ = get_all_data()

    # Floating chatbot
    render_floating_chatbot()

    if is_admin:
        main_tab, hist_tab, personal_tab, admin_tab = st.tabs([
            "🏠 דשבורד", "📊 עובר ושב", "👤 פרטים אישיים", "🛠️ ניהול מנהל"
        ])
    else:
        main_tab, hist_tab, personal_tab = st.tabs([
            "🏠 דשבורד", "📊 עובר ושב", "👤 פרטים אישיים"
        ])

    with main_tab:
        render_dashboard(u, is_admin, df_users, df_actions)

    with hist_tab:
        render_history(u, is_admin, df_users, df_actions)

    with personal_tab:
        render_personal(u, df_users)

    if is_admin:
        with admin_tab:
            render_admin(df_users, df_actions)


main()
