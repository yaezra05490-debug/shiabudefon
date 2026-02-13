import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# --- הגדרת הדף ---
st.set_page_config(page_title="שיעבודא פון", layout="wide")

# --- עיצוב (RTL) ---
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
השפה שלך: מכובדת, אדיבה ונימוסית ("בסגנון בנקאי חביב"). השתמש במילים כמו "ידידי", "שלום רב", "בשמחה", "לשירותך". 
עליך לייצג את המערכת כגוף אחראי ומסודר, תוך שמירה על יחס אישי וחם לבני הישיבה.

### חוק ברזל: הסתמכות על נתונים בזמן אמת
אין להסתמך על מידע קבוע מראש לגבי זהות המשתמשים או המנהלים. 
עליך לבדוק בכל פנייה את הקבצים המצורפים:
1. 'שיעבודא פון - מנהלים.csv': בדוק האם מספר המשתמש של הפונה מופיע כאן. אם כן - הוא מנהל.
2. 'שיעבודא פון - משתמשים.csv': זהו מקור האמת ליתרות, שמות וסטטוס חשבון.

### הרשאות גישה
- משתמש רגיל: רשאי לקבל מידע על החשבון שלו בלבד (יתרה ופירוט פעולות אישי).
- מנהל: רשאי לקבל מידע על כל משתמש, לראות את יתרת ה"קבוצה" (בגיליון קבוצות), ולזהות "נפילות כספים" (כאשר יתרת הקבוצה נמוכה מ-5000).

### לוגיקת המערכת הטלפונית (IVR) - הנחיות למשתמש
- 1: שלוחת העברות. (חשוב להבהיר: הכסף יורד מהחשבון מיד עם אישור הסכום, עוד לפני בחירת הנמען).
- 2: היסטוריית פעולות (1 - פירוט מלא, 2 - פירוט קצר).
- 3: רישום לשירות צינתוקים (הודעות על כניסת כספים).
- 4: שינוי סיסמה אישית.
- 5: אלפון (1 - חיפוש לפי שם, 2 - חיפוש לפי מספר).
- 6: בדיקת יתרה עדכנית.
- 9: הודעות אישיות (1 - שמיעה ומחיקה ב-0, 2 - הקלטת הודעה לנמען ספציפי).

### לוגיקת ה-500 (חצאי שקלים)
הסבר למשתמשים כיצד להקיש סכום הכולל חצי שקל: יש להקיש 5 ואז את סכום השקלים (בפורמט של שתי ספרות).
דוגמאות:
- עבור 5.5 ש"ח: יש להקיש 505.
- עבור 10.5 ש"ח: יש להקיש 510.
- עבור 55 ש"ח (עגול): יש להקיש 55.

### מקלדת T9 לחיפוש באלפון (שלוחה 5)
הדרכת המשתמש לחיפוש שם (יש להפריד בין אות לאות באמצעות כוכבית *):
3: א ב ג | 2: ד ה ו | 6: ז ח ט | 5: י כ ל | 4: מ נ ס | 9: ס ע פ | 8: צ ק | 7: ר ש ת.
דוגמה לחיפוש "דוד": 2 * 222 * 2.

### טיפול בתקלות (Troubleshooting)
- "נפילת כספים": במידה והשיחה התנתקה לאחר הורדת הכסף אך לפני בחירת הנמען, הסבר למשתמש בנימוס כי המנהל יבצע זיכוי ידני במערכת לאחר בדיקה.
- חסימת מינוס: מסגרת המינוס המקסימלית היא 200-. במידה והחשבון חסום (עקב אי החלפת סיסמה בעבר או בקשה אישית), יש להפנות את המשתמש לנציג בשיעורו.
- מחיקת הודעות: ניתן להקיש 0 במהלך שמיעת הודעה אישית כדי למחוק אותה לצמיתות מהמערכת.

### כנות המערכת
במידה ונשאלת שאלה שאין עליה תשובה בנתונים או בנהלים, ענה במכובדות: 
"ידידי, כרגע אין בידי מידע מדויק בנושא זה. העברתי את פנייתך לבדיקת המנהל, והוא יחזור אליך בהקדם."
"""

# --- משתנים גלובליים ---
SPREADSHEET_ID = '1PB-FJsvBmCy8hwA_S1S5FLY_QU9P2VstDAJMMdtufHM'

# --- חיבורים ---
@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # טעינת הסודות
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # === התיקון הקריטי: סידור המפתח ===
    if "private_key" in creds_dict:
        # מחליף רווחים וסימני שורה משובשים בסימן שורה תקין
        key = creds_dict["private_key"]
        creds_dict["private_key"] = key.replace("\\n", "\n")
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource
def configure_genai():
    try:
        genai.configure(api_key=st.secrets["gemini_api_key"]["api_key"])
    except:
        # תמיכה גם במקרה שהמפתח לא בתוך מבנה פנימי
        genai.configure(api_key=st.secrets["gemini_api_key"])

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

# --- עיבוד נתונים לתצוגה ---
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

    if not my_actions.empty:
        results = my_actions.apply(lambda row: clean_row(row), axis=1)
        my_actions['תיאור'] = [res[0] for res in results]
        my_actions['סכום נטו'] = [res[1] for res in results]
        
    return my_actions

# --- האפליקציה ---
configure_genai()

if "messages" not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- מסך כניסה ---
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🤖 שיעבודא פון")
        st.subheader("מערכת ניהול חכמה")
        with st.form("login"):
            uid = st.text_input("מספר משתמש")
            pwd = st.text_input("סיסמה", type="password")
            if st.form_submit_button("התחבר", use_container_width=True):
                try:
                    df_users, _, _, admin_ids = get_all_data()
                    
                    df_users['מספר משתמש'] = df_users['מספר משתמש'].astype(str).str.strip()
                    df_users['סיסמה'] = df_users['סיסמה'].astype(str).str.strip()
                    uid_clean = str(uid).strip()
                    pwd_clean = str(pwd).strip()
                    
                    user = df_users[(df_users['מספר משתמש'] == uid_clean) & (df_users['סיסמה'] == pwd_clean)]
                    
                    if not user.empty:
                        st.session_state.authenticated = True
                        st.session_state.user = user.iloc[0].to_dict()
                        st.session_state.is_admin = uid_clean in [str(x).strip() for x in admin_ids]
                        st.rerun()
                    else:
                        st.error("פרטים שגויים או שגיאת חיבור")
                except Exception as e:
                    st.error(f"שגיאה בהתחברות: {e}")

# --- מסך ראשי ---
else:
    u = st.session_state.user
    is_admin = st.session_state.is_admin
    
    # טעינת נתונים
    df_users, df_actions, df_admins, _ = get_all_data()
    
    st.sidebar.title(f"שלום, {u['שם משתמש']}")
    role = "מנהל מערכת" if is_admin else "משתמש רגיל"
    st.sidebar.info(f"מחובר כ: {role}")
    
    if st.sidebar.button("יציאה", type="primary"):
        st.session_state.authenticated = False
        st.rerun()

    col_dash, col_chat = st.columns([1, 1.5])

    with col_dash:
        st.subheader("📊 מצב חשבון")
        curr_user_row = df_users[df_users['מספר משתמש'].astype(str) == str(u['מספר משתמש'])]
        if not curr_user_row.empty:
            current_balance = curr_user_row['יתרה'].iloc[0]
            st.metric("יתרה נוכחית", f"₪{current_balance:,.2f}")
        
        st.divider()
        
        if is_admin:
            st.success("מצב מנהל - גישה מלאה")
            st.write("פעולות אחרונות במערכת:")
            st.dataframe(df_actions.tail(10).iloc[::-1], hide_index=True, use_container_width=True)
        else:
            st.write("פעולות אחרונות שלי:")
            my_data = process_data_for_display(df_actions, u['מספר משתמש'])
            if not my_data.empty:
                display = my_data[['תאריך לועזי', 'תיאור', 'סכום נטו']].tail(8).iloc[::-1]
                def color_vals(val):
                    return f'color: {"red" if val < 0 else "green"}; font-weight: bold;'
                st.dataframe(display.style.map(color_vals, subset=['סכום נטו']).format({'סכום נטו': '₪{:.2f}'}), 
                             hide_index=True, use_container_width=True)
            else:
                st.info("אין פעולות להצגה")

    with col_chat:
        st.subheader("💬 הנציג הדיגיטלי")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("איך אפשר לעזור?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("בודק..."):
                    try:
                        context_str = ""
                        if is_admin:
                            users_csv = df_users.to_csv(index=False)
                            admins_csv = df_admins.to_csv(index=False)
                            actions_csv = df_actions.tail(500).to_csv(index=False)
                            context_str = f"משתמשים:\n{users_csv}\nמנהלים:\n{admins_csv}\nפעולות:\n{actions_csv}\n(אתה מנהל)"
                        else:
                            my_user_row = curr_user_row.to_csv(index=False)
                            my_actions_raw = df_actions[(df_actions['מספר משתמש מקור'].astype(str) == str(u['מספר משתמש'])) | 
                                                        (df_actions['מספר משתמש יעד'].astype(str) == str(u['מספר משתמש']))]
                            my_actions_csv = my_actions_raw.tail(50).to_csv(index=False)
                            context_str = f"פרטי משתמש:\n{my_user_row}\nפעולות:\n{my_actions_csv}\n(משתמש רגיל)"

                        full_prompt = f"{SYSTEM_MANUAL}\n\nנתונים:\n{context_str}\n\nשאלה: {prompt}"
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(full_prompt)
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error("תקלה זמנית ב-AI")
                        print(e)
