import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import os

# --- הגדרת הדף ---
st.set_page_config(page_title="שיעבודא פון", layout="wide")
st.markdown("""
<style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, p, div, input, .stTextInput > label, .stSelectbox > label { text-align: right; }
    .stChatMessage { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- משתנים ---
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'
SYSTEM_MANUAL = """
אתה הנציג הדיגיטלי של שיעבודא פון.
תשובות קצרות ולעניין.
"""

# --- חיבור לגוגל שיטס (עובד!) ---
@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    secret_dir = "/etc/secrets"
    
    # רשימת המפתחות שאנחנו צריכים
    required_keys = [
        "type", "project_id", "private_key_id", "private_key", 
        "client_email", "client_id", "auth_uri", "token_uri", 
        "auth_provider_x509_cert_url", "client_x509_cert_url"
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
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    else:
        # Fallback לקובץ JSON
        json_path = os.path.join(secret_dir, "service_account.json")
        if os.path.exists(json_path):
            creds = Credentials.from_service_account_file(json_path, scopes=scopes)
            return gspread.authorize(creds)
    
    st.error("תקלה בחיבור לשיטס")
    st.stop()

# --- חיבור ל-AI (התיקון) ---
@st.cache_resource
def configure_genai():
    api_key = None
    
    # ניסיון 1: קריאה מ-st.secrets (הדרך הרגילה)
    try:
        if "gemini_api_key" in st.secrets:
            if isinstance(st.secrets["gemini_api_key"], dict):
                api_key = st.secrets["gemini_api_key"].get("api_key")
            else:
                api_key = st.secrets["gemini_api_key"]
    except:
        pass
        
    # ניסיון 2: קריאה מהקבצים בשרת (אם Render פירק אותם)
    if not api_key:
        possible_paths = ["/etc/secrets/api_key", "/etc/secrets/gemini_api_key"]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read().strip()
                    # ניקוי מרכאות אם יש
                    api_key = content.replace('"', '').replace("'", "")
                    break

    # הגדרה סופית
    if api_key:
        genai.configure(api_key=api_key)
        return True
    else:
        return False

@st.cache_data(ttl=60)
def get_all_data():
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws_users = sh.worksheet("משתמשים")
    df_users = pd.DataFrame(ws_users.get_all_records())
    ws_actions = sh.worksheet("פעולות")
    df_actions = pd.DataFrame(ws_actions.get_all_records())
    try:
        ws_admins = sh.worksheet("מנהלים")
        df_admins = pd.DataFrame(ws_admins.get_all_records())
        admin_ids = df_admins[df_admins.columns[0]].astype(str).tolist()
    except:
        admin_ids = []
    return df_users, df_actions, admin_ids

def process_data_for_display(df_actions, user_id):
    df_actions['מספר משתמש מקור'] = df_actions['מספר משתמש מקור'].astype(str)
    df_actions['מספר משתמש יעד'] = df_actions['מספר משתמש יעד'].astype(str)
    user_id = str(user_id)
    mask = (df_actions['מספר משתמש מקור'] == user_id) | (df_actions['מספר משתמש יעד'] == user_id)
    my_actions = df_actions[mask].copy()
    if my_actions.empty: return pd.DataFrame()

    def clean_row(row):
        is_sender = str(row['מספר משתמש מקור']) == user_id
        try: amount = float(row['סכום'])
        except: amount = 0
        if is_sender: return f"העברה ל-{row['שם יעד']}", -amount
        else: return f"התקבל מ-{row['שם מקור']}", amount

    if not my_actions.empty:
        results = my_actions.apply(lambda row: clean_row(row), axis=1)
        my_actions['תיאור'] = [res[0] for res in results]
        my_actions['סכום נטו'] = [res[1] for res in results]
    return my_actions

# --- האפליקציה ---
ai_configured = configure_genai()

if "messages" not in st.session_state: st.session_state.messages = []
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🤖 כניסה")
        with st.form("login"):
            uid = st.text_input("מספר משתמש")
            pwd = st.text_input("סיסמה", type="password")
            if st.form_submit_button("התחבר", use_container_width=True):
                try:
                    df_users, _, admin_ids = get_all_data()
                    uid_clean = str(uid).strip()
                    pwd_clean = str(pwd).strip()
                    df_users['מספר משתמש'] = df_users['מספר משתמש'].astype(str).str.strip()
                    df_users['סיסמה'] = df_users['סיסמה'].astype(str).str.strip()
                    user = df_users[(df_users['מספר משתמש'] == uid_clean) & (df_users['סיסמה'] == pwd_clean)]
                    if not user.empty:
                        st.session_state.authenticated = True
                        st.session_state.user = user.iloc[0].to_dict()
                        st.session_state.is_admin = uid_clean in [str(x).strip() for x in admin_ids]
                        st.rerun()
                    else:
                        st.error("פרטים שגויים")
                except Exception as e:
                    st.error(f"שגיאה: {e}")
else:
    u = st.session_state.user
    is_admin = st.session_state.is_admin
    df_users, df_actions, _ = get_all_data()
    st.sidebar.title(f"שלום, {u['שם משתמש']}")
    
    if not ai_configured:
        st.sidebar.error("⚠️ מפתח AI לא נמצא!")
    
    if st.sidebar.button("יציאה"):
        st.session_state.authenticated = False
        st.rerun()
        
    col_dash, col_chat = st.columns([1, 1.5])
    with col_dash:
        st.metric("יתרה", f"₪{df_users[df_users['מספר משתמש'].astype(str) == str(u['מספר משתמש'])]['יתרה'].iloc[0]:,.2f}")
        if is_admin: st.dataframe(df_actions.tail(10), hide_index=True)
        else: st.dataframe(process_data_for_display(df_actions, u['מספר משתמש']).tail(8), hide_index=True)
        
    with col_chat:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(msg["content"])
        if prompt := st.chat_input("שאל אותי..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("חושב..."):
                    try:
                        context = df_users.to_csv() if is_admin else process_data_for_display(df_actions, u['מספר משתמש']).to_csv()
                        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"{SYSTEM_MANUAL}\n{context}\n{prompt}")
                        st.write(res.text)
                        st.session_state.messages.append({"role": "assistant", "content": res.text})
                    except Exception as e:
                        # כאן התיקון החשוב - הדפסת השגיאה המלאה
                        st.error(f"שגיאה מפורטת: {str(e)}")
