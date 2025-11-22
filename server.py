from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import uuid
import os

# تهيئة تطبيق Flask
app = Flask(__name__)
CORS(app)  # تمكين CORS

# استخدام مفتاح API الخاص بك

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

# تخزين المحادثات
chat_sessions = {}

# prompt النظام
SYSTEM_PROMPT = """
أنت مساعد باسم "LUKU AI"، مختص بالكامل في الألعاب، الألغاز، الأسئلة المنطقية.
إذا سُئلت عن شيء خارج هذا المجال، اكتب: "عذرًا أنا مساعد LUKU AI مختص في الألعاب والألغاز فقط."
كن مرحًا وابتكر ألغاز وأسئلة ذكاء ممتعة، استخدم الإيموجيات بشكل مناسب.
قدم الألغاز بناءً على المجال ومستوى الصعوبة المحدد.
"""

# إنشاء أو استرجاع جلسة محادثة
def get_chat_session(session_id, category="", level=""):
    if session_id not in chat_sessions:
        # إنشاء نموذج جديد
        model = genai.GenerativeModel('gemini-1.5-flash')
       
        # بدء محادثة جديدة مع تعليمات النظام
        chat = model.start_chat(history=[
            {
                'role': 'user',
                'parts': [f"{SYSTEM_PROMPT}\n\nالمجال: {category}\nمستوى الصعوبة: {level}"]
            },
            {
                'role': 'model',
                'parts': ["مرحبًا! أنا LUKU AI، مساعدك المختص في الألغاز والألعاب. كيف يمكنني مساعدتك اليوم؟ 🧩"]
            }
        ])
       
        chat_sessions[session_id] = {
            'chat': chat,
            'category': category,
            'level': level,
            'history': []
        }
   
    return chat_sessions[session_id]

# مسار للدردشة
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('sessionId', 'default')
        category = data.get('category', '')
        level = data.get('level', '')
       
        if not message:
            return jsonify({
                'error': True,
                'message': 'الرسالة مطلوبة'
            }), 400
       
        session = get_chat_session(session_id, category, level)
        session['history'].append({'role': 'user', 'content': message})
       
        # إرسال الرسالة إلى Gemini AI
        response = session['chat'].send_message(message)
        reply = response.text
       
        session['history'].append({'role': 'assistant', 'content': reply})
       
        return jsonify({
            'success': True,
            'reply': reply,
            'sessionId': session_id
        })
       
    except Exception as err:
        print("Error in /chat endpoint:", err)
       
        # معالجة أنواع مختلفة من الأخطاء
        error_message = "حدث خطأ أثناء معالجة طلبك"
       
        if "API_KEY" in str(err):
            error_message = "مفتاح API غير صالح أو غير موجود"
        elif "network" in str(err):
            error_message = "خطأ في الاتصال بالشبكة"
       
        return jsonify({
            'error': True,
            'message': error_message
        }), 500

# مسار لإنشاء جلسة جديدة
@app.route('/session/new', methods=['POST'])
def new_session():
    try:
        data = request.get_json()
        category = data.get('category', '')
        level = data.get('level', '')
       
        session_id = f"session_{uuid.uuid4().hex}"
       
        # إنشاء جلسة جديدة
        get_chat_session(session_id, category, level)
       
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'message': 'تم إنشاء جلسة جديدة بنجاح'
        })
       
    except Exception as err:
        print("Error in /session/new endpoint:", err)
        return jsonify({
            'error': True,
            'message': 'حدث خطأ أثناء إنشاء الجلسة'
        }), 500

# مسار للحصول على تاريخ المحادثة
@app.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    try:
        if session_id not in chat_sessions:
            return jsonify({
                'error': True,
                'message': 'الجلسة غير موجودة'
            }), 404
       
        session = chat_sessions[session_id]
       
        return jsonify({
            'success': True,
            'history': session['history'],
            'category': session['category'],
            'level': session['level']
        })
       
    except Exception as err:
        print("Error in /history endpoint:", err)
        return jsonify({
            'error': True,
            'message': 'حدث خطأ أثناء جلب التاريخ'
        }), 500

# مسار لحذف جلسة
@app.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    try:
        if session_id in chat_sessions:
            del chat_sessions[session_id]
           
            return jsonify({
                'success': True,
                'message': 'تم حذف الجلسة بنجاح'
            })
        else:
            return jsonify({
                'error': True,
                'message': 'الجلسة غير موجودة'
            }), 404
           
    except Exception as err:
        print("Error in /session endpoint:", err)
        return jsonify({
            'error': True,
            'message': 'حدث خطأ أثناء حذف الجلسة'
        }), 500

# middleware للتعامل مع المسارات غير المعرفة
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': True,
        'message': 'مسار غير موجود'
    }), 404

if __name__ == '__main__':
    app.run(port=3000, debug=True)