import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# --- תיקון השגיאה: הסרנו את direction="rtl" מכאן ---
st.set_page_config(page_title="שיעבודא פון", layout="wide")

# --- הוספת יישור לימין (RTL) בצורה תקינה ---
st.markdown("""
<style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    /* התאמות נוספות לכותרות */
    h1, h2, h3, p, div {
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# --- משתנים גלובליים ---
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'
# כאן נכנס המדריך הטכני שה-AI ילמד בהמשך
SYSTEM_MANUAL = """
כרגע אין מידע טכני ספציפי. 
אם שואלים אותך שאלות טכניות, תענה שאתה עדיין לומד את המערכת.
"""

# --- פונקציות חיבור ---
@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource
def configure_genai():
    try:
        genai.configure(api_key=st.secrets["gemini_api_key"])
    except Exception as e:
        st.error(f"תקלה בחיבור ל-AI: {e}")

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
        # מניחים שהעמודה הראשונה היא המספר המזהה
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
    
    if my_actions.empty:
        return pd.DataFrame()

    def clean_row(row):
        is_sender = str(row['מספר משתמש מקור']) == user_id
        try:
            amount = float(row['סכום'])
        except:
            amount = 0
        
        if is_sender:
            return f"העברה ל-{row['שם יעד']}", -amount
        else:
            return f"התקבל מ-{row['שם מקור']}", amount

    my_actions[['תיאור', 'סכום נטו']] = my_actions.apply(
        lambda row: pd.Series(clean_row(row)), axis=1
    )
    return my_actions

# --- האפליקציה ---
configure_genai()

if "messages" not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# --- מסך כניסה ---
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
                    
                    df_users['מספר משתמש'] = df_users['מספר משתמש'].astype(str)
                    df_users['סיסמה'] = df_users['סיסמה'].astype(str)
                    
                    user = df_users[(df_users['מספר משתמש'] == str(uid)) & (df_users['סיסמה'] == str(pwd))]
                    
                    if not user.empty:
                        st.session_state.authenticated = True
                        st.session_state.user = user.iloc[0].to_dict()
                        # בדיקת מנהל
                        st.session_state.is_admin = str(uid) in [str(x) for x in admin_ids]
                        st.rerun()
                    else:
                        st.error("פרטים שגויים")
                except Exception as e:
                    st.error(f"שגיאה בהתחברות: {e}")

# --- מסך פנימי ---
else:
    u = st.session_state.user
    is_admin = st.session_state.is_admin
    
    df_users, df_actions, _ = get_all_data()
    
    st.sidebar.title(f"שלום, {u['שם משתמש']}")
    role = "מנהל" if is_admin else "משתמש"
    st.sidebar.caption(f"מחובר כ: {role}")
    
    if st.sidebar.button("יציאה"):
        st.session_state.authenticated = False
        st.rerun()

    col_dash, col_chat = st.columns([1, 1.5])

    with col_dash:
        st.subheader("נתונים")
        st.metric("יתרה", f"₪{u['יתרה']}")
        
        st.divider()
        if is_admin:
            st.info("מצב מנהל: רואה את כל הפעולות")
            st.dataframe(df_actions.tail(10).iloc[::-1], hide_index=True)
        else:
            st.write("פעולות אחרונות:")
            my_data = process_data_for_display(df_actions, u['מספר משתמש'])
            if not my_data.empty:
                display = my_data[['תאריך לועזי', 'תיאור', 'סכום נטו']].tail(10).iloc[::-1]
                st.dataframe(display, hide_index=True)
            else:
                st.write("אין פעולות.")

    with col_chat:
        st.subheader("💬 צ'אט חכם")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("שאל שאלה..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("חושב..."):
                    try:
                        # הכנת המידע ל-AI
                        context = ""
                        if is_admin:
                            users_csv = df_users.to_csv(index=False)
                            actions_csv = df_actions.tail(500).to_csv(index=False)
                            context = f"משתמשים:\n{users_csv}\nפעולות:\n{actions_csv}"
                            role_inst = "אתה מנהל על. יש לך גישה להכל."
                        else:
                            my_data = process_data_for_display(df_actions, u['מספר משתמש'])
                            context = my_data.to_csv(index=False)
                            role_inst = "אתה עוזר למשתמש ספציפי. ענה רק על הנתונים שלו."

                        prompt_text = f"""
                        {role_inst}
                        הנחיות טכניות (System Manual):
                        {SYSTEM_MANUAL}
                        
                        הנתונים הרלוונטיים:
                        {context}
                        
                        שאלה: {prompt}
                        """
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt_text)
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        
                    except Exception as e:
                        st.error("שגיאה ב-AI")
                        print(e)
