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
אתה הנציג הדיגיטלי של שיעבודא פון. תפקידך לשמש כמנתח נתונים של המשתמש.
מותר לך לסכם לו את הפעולות, לחשב הוצאות/הכנסות, ולענות על שאלות בצורה אדיבה.
"""

# --- חיבורים לגוגל שיטס ---
@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    secret_dir = "/etc/secrets"
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url"]
    
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

# --- שולף את רשימת המפתחות ---
@st.cache_resource
def get_api_keys():
    keys = []
    try:
        if "gemini_api_key" in st.secrets:
            val = st.secrets["gemini_api_key"]
            if isinstance(val, dict):
                # תומך במפתח אחד או ברשימה עם פסיקים
                raw_keys = val.get("api_keys", val.get("api_key", ""))
                keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            else:
                keys = [k.strip() for k in str(val).split(",") if k.strip()]
    except: pass
        
    if not keys:
        for path in ["/etc/secrets/api_key", "/etc/secrets/gemini_api_key"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read().strip().replace('"', '').replace("'", "")
                    keys = [k.strip() for k in content.split(",") if k.strip()]
                    break
    return keys

@st.cache_data(ttl=60)
def get_all_data():
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    df_users = pd.DataFrame(sh.worksheet("משתמשים").get_all_records())
    df_actions = pd.DataFrame(sh.worksheet("פעולות").get_all_records())
    try:
        admin_ids = pd.DataFrame(sh.worksheet("מנהלים").get_all_records()).iloc[:, 0].astype(str).tolist()
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
        try: amount = float(row.get('סכום', 0))
        except: amount = 0
        if is_sender: return f"העברה ל-{row['שם יעד']}", -amount
        else: return f"התקבל מ-{row['שם מקור']}", amount

    results = my_actions.apply(lambda row: clean_row(row), axis=1)
    my_actions['תיאור'] = [res[0] for res in results]
    my_actions['סכום נטו'] = [res[1] for res in results]
    return my_actions

# --- האפליקציה ---
api_keys_pool = get_api_keys()

if "messages" not in st.session_state: st.session_state.messages = []
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🤖 כניסה למערכת")
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
    if not api_keys_pool:
        st.sidebar.error("⚠️ לא הוגדרו מפתחות AI!")
    else:
        st.sidebar.caption(f"מפתחות גיבוי פעילים: {len(api_keys_pool)}")
        
    if st.sidebar.button("יציאה"):
        st.session_state.authenticated = False
        st.rerun()
        
    col_dash, col_chat = st.columns([1, 1.5])
    with col_dash:
        st.metric("יתרה", f"₪{df_users[df_users['מספר משתמש'].astype(str) == str(u['מספר משתמש'])]['יתרה'].iloc[0]:,.2f}")
        if is_admin: st.dataframe(df_actions.tail(10), hide_index=True)
        else: st.dataframe(process_data_for_display(df_actions, u['מספר משתמש']).tail(8), hide_index=True)
        
    with col_chat:
        # הצגת ההיסטוריה כולל הטוקנים
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): 
                st.write(msg["content"])
                if "tokens" in msg:
                    st.caption(f"🪙 {msg['tokens']}")
                    
        if prompt := st.chat_input("שאל אותי (לדוגמה: תסכם לי הוצאות)..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("חושב... (וסורק את כל הפעולות)"):
                    
                    # הכנת המידע - שליחת כללללל הפעולות כמו שביקשת!
                    if is_admin:
                        context = f"משתמשים:\n{df_users.to_csv()}\nפעולות:\n{df_actions.to_csv()}"
                    else:
                        my_act = process_data_for_display(df_actions, u['מספר משתמש'])
                        curr_row = df_users[df_users['מספר משתמש'].astype(str) == str(u['מספר משתמש'])]
                        context = f"פרטים:\n{curr_row.to_csv()}\nפעולות מלאות:\n{my_act.to_csv()}"
                    
                    # מנגנון Fallback - מנסה מפתח אחרי מפתח
                    success = False
                    last_error = ""
                    
                    for key in api_keys_pool:
                        try:
                            genai.configure(api_key=key)
                            
                            # חיפוש מודל פעיל
                            valid_model = None
                            for m in genai.list_models():
                                if 'generateContent' in m.supported_generation_methods:
                                    valid_model = m.name
                                    if 'flash' in m.name.lower(): break
                            if not valid_model: valid_model = 'gemini-pro'
                                
                            # הרצת הבקשה (עם הגבלת אורך תשובה כדי לחסוך)
                            model = genai.GenerativeModel(valid_model)
                            config = genai.types.GenerationConfig(max_output_tokens=300)
                            
                            res = model.generate_content(
                                f"{SYSTEM_MANUAL}\n{context}\nשאלה: {prompt}",
                                generation_config=config
                            )
                            
                            # שליפת נתוני טוקנים אם קיימים
                            tokens_info = ""
                            try:
                                usage = res.usage_metadata
                                tokens_info = f"טוקנים שבוזבזו: {usage.total_token_count}"
                            except: pass
                            
                            # הצגה למשתמש
                            st.write(res.text)
                            if tokens_info: st.caption(f"🪙 {tokens_info}")
                            
                            # שמירה
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": res.text,
                                "tokens": tokens_info
                            })
                            
                            success = True
                            break # הכל עבד מעולה! עוצר את הלולאה ולא מנסה מפתחות אחרים
                            
                        except Exception as e:
                            last_error = str(e)
                            print(f"Key failed: {e}")
                            continue # עובר למפתח הבא ברשימה

                    if not success:
                        st.error(f"לא הצלחתי לענות. כל המפתחות נוסו ונכשלו. שגיאה אחרונה: {last_error}")
