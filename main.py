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

# --- המוח של המערכת ---
SYSTEM_MANUAL = """
אתה "הנציג הדיגיטלי של שיעבודא פון". תפקידך לשמש כמנתח נתונים וכמרכז מידע עבור משתמשי המערכת.
השפה שלך: מכובדת, אדיבה ונימוסית.
חוקים:
1. הסתמכות על נתונים בזמן אמת בלבד.
2. משתמש רגיל רואה רק את שלו, מנהל רואה הכל.
3. לוגיקת IVR: 1-העברות, 2-פעולות, 3-צינתוקים, 4-סיסמה, 5-אלפון, 6-יתרה.
"""

# --- משתנים גלובליים ---
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'

# --- חיבורים ---
@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    secret_dir = "/etc/secrets"
    
    # רשימת המפתחות שאנחנו צריכים כדי לבנות את ההרשאה
    required_keys = [
        "type", "project_id", "private_key_id", "private_key", 
        "client_email", "client_id", "auth_uri", "token_uri", 
        "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    
    creds_dict = {}
    
    # איסוף הנתונים מהקבצים הנפרדים
    for key in required_keys:
        path = os.path.join(secret_dir, key)
        if os.path.exists(path):
            with open(path, "r") as f:
                # קריאת התוכן וניקוי רווחים מיותרים
                creds_dict[key] = f.read().strip()
                
                # תיקון מיוחד למפתח הפרטי - המרת ירידות שורה טקסטואליות לאמיתיות
                if key == "private_key":
                     creds_dict[key] = creds_dict[key].replace("\\n", "\n").replace('"', '')

    # בדיקה שיש לנו מספיק נתונים
    if "private_key" in creds_dict and "client_email" in creds_dict:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    else:
        # ניסיון אחרון - אולי זה בכל זאת בקובץ JSON אחד?
        json_path = os.path.join(secret_dir, "service_account.json")
        if os.path.exists(json_path):
            creds = Credentials.from_service_account_file(json_path, scopes=scopes)
            return gspread.authorize(creds)
            
        st.error("לא הצלחתי להרכיב את פרטי ההתחברות מהקבצים בשרת.")
        st.stop()

@st.cache_resource
def configure_genai():
    api_key_path = "/etc/secrets/api_key"
    try:
        # קודם ננסה לקרוא מהקובץ
        if os.path.exists(api_key_path):
            with open(api_key_path, "r") as f:
                key = f.read().strip().replace('"', '')
                genai.configure(api_key=key)
        # אם לא, ננסה דרך הסודות הרגילים
        elif "gemini_api_key" in st.secrets:
            if "api_key" in st.secrets["gemini_api_key"]:
                genai.configure(api_key=st.secrets["gemini_api_key"]["api_key"])
            else:
                genai.configure(api_key=st.secrets["gemini_api_key"])
    except:
        pass

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
        df_admins = pd.DataFrame()
        
    return df_users, df_actions, df_admins, admin_ids

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
configure_genai()

if "messages" not in st.session_state: st.session_state.messages = []
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

# מסך כניסה
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🤖 כניסה למערכת")
        with st.form("login"):
            uid = st.text_input("מספר משתמש")
            pwd = st.text_input("סיסמה", type="password")
            if st.form_submit_button("התחבר", use_container_width=True):
                try:
                    df_users, _, _, admin_ids = get_all_data()
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
                    st.error(f"שגיאה בהתחברות: {e}")

# מסך ראשי
else:
    u = st.session_state.user
    is_admin = st.session_state.is_admin
    df_users, df_actions, df_admins, _ = get_all_data()
    
    st.sidebar.title(f"שלום, {u['שם משתמש']}")
    if st.sidebar.button("יציאה"):
        st.session_state.authenticated = False
        st.rerun()

    col_dash, col_chat = st.columns([1, 1.5])

    with col_dash:
        st.subheader("📊 מצב חשבון")
        curr_row = df_users[df_users['מספר משתמש'].astype(str) == str(u['מספר משתמש'])]
        if not curr_row.empty:
            st.metric("יתרה נוכחית", f"₪{curr_row['יתרה'].iloc[0]:,.2f}")
        
        st.divider()
        if is_admin:
            st.dataframe(df_actions.tail(10).iloc[::-1], hide_index=True)
        else:
            my_data = process_data_for_display(df_actions, u['מספר משתמש'])
            if not my_data.empty:
                display = my_data[['תאריך לועזי', 'תיאור', 'סכום נטו']].tail(8).iloc[::-1]
                st.dataframe(display, hide_index=True)

    with col_chat:
        st.subheader("💬 צ'אט")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(msg["content"])
            
        if prompt := st.chat_input("שאל אותי..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("חושב..."):
                    try:
                        context = ""
                        if is_admin:
                            context = f"משתמשים:\n{df_users.to_csv()}\nפעולות:\n{df_actions.tail(100).to_csv()}"
                        else:
                            my_act = process_data_for_display(df_actions, u['מספר משתמש'])
                            context = f"פרטים:\n{curr_row.to_csv()}\nפעולות:\n{my_act.to_csv()}"
                        
                        full_prompt = f"{SYSTEM_MANUAL}\n{context}\nשאלה: {prompt}"
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        res = model.generate_content(full_prompt)
                        st.write(res.text)
                        st.session_state.messages.append({"role": "assistant", "content": res.text})
                    except Exception as e:
                        st.error("שגיאה ב-AI")
                        print(e)
