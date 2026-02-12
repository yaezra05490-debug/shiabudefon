import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- הגדרת הדף ---
st.set_page_config(page_title="שיעבודא פון", layout="centered", direction="rtl")

# --- התחברות לגוגל ---
# וודא שב-Streamlit Secrets השמות הם בדיוק:
# [gcp_service_account] ...
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'

@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def get_data():
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    
    # שליפת נתונים
    ws_users = sh.worksheet("משתמשים")
    df_users = pd.DataFrame(ws_users.get_all_records())
    
    ws_actions = sh.worksheet("פעולות")
    df_actions = pd.DataFrame(ws_actions.get_all_records())
    
    return df_users, df_actions

# --- האתר עצמו ---
st.title("🤖 סוכן שיעבודא פון")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.form("login"):
        st.write("נא להזין פרטי הזדהות:")
        uid = st.text_input("מספר משתמש")
        pwd = st.text_input("סיסמה", type="password")
        if st.form_submit_button("כניסה"):
            try:
                with st.spinner("בודק פרטים..."):
                    users, _ = get_data()
                    # המרה לטקסט כדי למנוע בעיות
                    users['מספר משתמש'] = users['מספר משתמש'].astype(str)
                    users['סיסמה'] = users['סיסמה'].astype(str)
                    
                    user = users[(users['מספר משתמש'] == str(uid)) & (users['סיסמה'] == str(pwd))]
                    
                    if not user.empty:
                        st.session_state.authenticated = True
                        st.session_state.user = user.iloc[0].to_dict()
                        st.success("מחובר!")
                        st.rerun()
                    else:
                        st.error("פרטים שגויים")
            except Exception as e:
                st.error(f"שגיאה: {e}")

else:
    # מסך אחרי התחברות
    u = st.session_state.user
    st.write(f"שלום **{u['שם משתמש']}**")
    st.metric("יתרה", f"₪{u['יתרה']}")
    
    st.divider()
    st.write("פעולות אחרונות:")
    
    _, actions = get_data()
    # סינון לפי עמודה E (מספר משתמש מקור)
    actions['מספר משתמש מקור'] = actions['מספר משתמש מקור'].astype(str)
    my_actions = actions[actions['מספר משתמש מקור'] == str(u['מספר משתמש'])]
    
    if not my_actions.empty:
        # מציג עמודות רלוונטיות (תאריך, סכום, תיאור)
        st.dataframe(my_actions[['תאריך לועזי', 'סכום', 'טקסט קצר']].tail(5), hide_index=True)
    else:
        st.write("אין פעולות להצגה.")

    if st.button("יציאה"):
        st.session_state.authenticated = False
        st.rerun()

# fix
