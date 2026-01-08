import os
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

# קבלת המפתח בצורה מאובטחת מהגדרות השרת
my_api_key = os.environ.get("GEMINI_API_KEY")

# הגדרת המוח של גוגל
if my_api_key:
    genai.configure(api_key=my_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    # קבלת מספר הטלפון מימות המשיח
    phone = request.args.get('ApiPhone', 'אורח')
    
    # בדיקה שהמפתח קיים
    if not my_api_key:
        return "id_list_message=t-יש תקלה בהגדרות המפתח"

    # --- כאן בהמשך נוסיף את הקריאה לשיטס ---
    # כרגע נבדוק שג'ימיני עונה לנו
    
    try:
        # שליחת שאלה לניסיון ל-Gemini
        chat_response = model.generate_content(f"תגיד שלום נחמד וקצר למספר טלפון {phone}")
        text_answer = chat_response.text
        
        # ניקוי כוכביות או סימנים שיכולים להפריע להקראה
        text_answer = text_answer.replace('*', '') 
        
    except Exception as e:
        text_answer = "הייתה שגיאה בתקשורת עם גוגל"

    # התשובה לימות המשיח
    return f"id_list_message=t-{text_answer}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
