import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# --- הגדרת הדף (בלי המילה הבעייתית direction) ---
st.set_page_config(page_title="שיעבודא פון", layout="wide")

# --- הוספת יישור לימין (RTL) דרך CSS ---
st.markdown("""
<style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    h1, h2, h3, p, div, input, .stTextInput > label, .stSelectbox > label {
        text-align: right;
    }
    /* תיקון ליישור של הצ'אט */
    .stChatMessage {
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# --- משתנים גלובליים ---
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'
SYSTEM_MANUAL = """
הנחיות טכניות (טרם הוזנו).
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
        # המרה בטוחה של המזהים לטקסט
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

    # שימוש ב-apply בצורה בטוחה יותר למניעת שגיאות
    if not my_actions.empty:
        results = my_actions.apply(lambda row: clean_row(row), axis=1)
        # פיצול התוצאות לעמודות
        my_actions['תיאור'] = [res[0] for res in results]
        my_actions['סכום נטו'] = [res[1] for res in results]
        
    return my_actions

# --- התחלת האפליקציה ---
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
        st.title("🔐 כניסה למערכת")
        with st.form("login"):
            uid = st.text_input("מספר משתמש")
            pwd = st.text_input("סיסמה", type="password")
            if st.form_submit_button("התחבר", use_container_width=True):
                try:
                    df_users, _, admin_ids = get_all_data()
                    
                    # ניקוי רווחים והמרה לטקסט
                    df_users['מספר משתמש'] = df_users['מספר משתמש'].astype(str).str.strip()
                    df_users['סיסמה'] = df_users['סיסמה'].astype(str).str.strip()
                    uid_clean = str(uid).strip()
                    pwd_clean = str(pwd).strip()
                    
                    user = df_users[(df_users['מספר משתמש'] == uid_clean) & (df_users['סיסמה'] == pwd_clean)]
                    
                    if not user.empty:
                        st.session_state.authenticated = True
                        st.session_state.user = user.iloc[0].to_dict()
                        # בדיקת מנהל
                        st.session_state.is_admin = uid_clean in [str(x).strip() for x in admin_ids]
                        st.rerun()
                    else:
                        st.error("פרטים שגויים")
                except Exception as e:
                    st.error(f"שגיאה בהתחברות: {e}")

# --- מסך ראשי ---
else:
    u = st.session_state.user
    is_admin = st.session_state.is_admin
    
    # טעינה מחדש כדי לקבל נתונים עדכניים
    df_users, df_actions, _ = get_all_data()
    
    st.sidebar.title(f"שלום, {u['שם משתמש']}")
    role = "מנהל מערכת" if is_admin else "משתמש רגיל"
    st.sidebar.info(f"מחובר כ: {role}")
    
    if st.sidebar.button("יציאה", type="primary"):
        st.session_state.authenticated = False
        st.rerun()

    # חלוקת מסך
    col_dash, col_chat = st.columns([1, 1.5])

    # צד ימין - נתונים
    with col_dash:
        st.subheader("📊 תמונת מצב")
        
        # עדכון יתרה מהטבלה החדשה (ולא מהזיכרון הישן)
        current_balance = df_users[df_users['מספר משתמש'].astype(str) == str(u['מספר משתמש'])]['יתרה'].iloc[0]
        st.metric("יתרה נוכחית", f"₪{current_balance:,.2f}")
        
        st.divider()
        
        if is_admin:
            st.success("מצב מנהל פעיל")
            st.write("פעולות אחרונות בכל המערכת:")
            st.dataframe(df_actions.tail(10).iloc[::-1], hide_index=True, use_container_width=True)
        else:
            st.write("הפעולות האחרונות שלי:")
            my_data = process_data_for_display(df_actions, u['מספר משתמש'])
            
            if not my_data.empty:
                display = my_data[['תאריך לועזי', 'תיאור', 'סכום נטו']].tail(10).iloc[::-1]
                
                # צביעת סכומים
                def color_vals(val):
                    color = 'red' if val < 0 else 'green'
                    return f'color: {color}; font-weight: bold;'
                
                st.dataframe(display.style.map(color_vals, subset=['סכום נטו']).format({'סכום נטו': '₪{:.2f}'}), 
                             hide_index=True, use_container_width=True)
            else:
                st.info("לא נמצאו פעולות בחשבון זה.")

    # צד שמאל - צ'אט
    with col_chat:
        st.subheader("💬 עוזר חכם")

        # הצגת הודעות קודמות
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # קלט חדש
        if prompt := st.chat_input("שאל אותי שאלה..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("חושב..."):
                    try:
                        # הכנת הנתונים ל-AI
                        context_str = ""
                        if is_admin:
                            users_csv = df_users[['מספר משתמש', 'שם משתמש', 'יתרה']].to_csv(index=False)
                            actions_csv = df_actions.tail(200).to_csv(index=False)
                            context_str = f"משתמשים:\n{users_csv}\n\nפעולות אחרונות:\n{actions_csv}"
                            sys_role = "אתה מנהל המערכת. יש לך גישה לכל הנתונים. ענה על שאלות לגבי כל משתמש."
                        else:
                            my_data = process_data_for_display(df_actions, u['מספר משתמש'])
                            context_str = my_data.to_csv(index=False)
                            sys_role = f"אתה העוזר של {u['שם משתמש']}. ענה רק על הנתונים שלו."

                        full_prompt = f"""
                        {sys_role}
                        
                        המדריך הטכני של המערכת:
                        {SYSTEM_MANUAL}
                        
                        הנתונים לניתוח:
                        {context_str}
                        
                        שאלה: {prompt}
                        """
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(full_prompt)
                        
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        
                    except Exception as e:
                        st.error("שגיאה בתקשורת עם ה-AI")
                        st.error(e)
