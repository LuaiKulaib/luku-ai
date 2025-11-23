from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import uuid
import os
import random
from datetime import datetime

# تهيئة تطبيق Flask
app = Flask(__name__)
CORS(app)

# استخدام مفتاح API من متغير البيئة
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("🎉 Gemini API جاهز للتوليد الديناميكي!")
else:
    print("❌ Gemini API غير متوفر - سيتم استخدام الردود العامة")

# تخزين الجلسات
chat_sessions = {}
user_profiles = {}

# البرومبت الذكي والمحسن
SMART_PROMPT = """
أنت "LUKU AI" - مساعد ذكي ومبدع للألغاز والتحديات الفكرية. 

**المبادئ الأساسية:**
1. لا تملك أي ألغاز مخزنة مسبقاً - إبتكر كل شيء في اللحظة
2. كن مبتكراً وأنشئ ألغازاً فريدة تناسب السياق
3. راعي الحساسيات الثقافية والدينية
4. تفاعل بذكاء مع جميع أنواع الرسائل
5. إذا تحدث المستخدم عن موضوع آخر، تفاعل معه بشكل طبيعي
6. إذا قدم المستخدم لغزاً، حاول حله بذكاء

**أنماط التفاعل:**
- طلب لغز: إبتكر لغزاً جديداً يناسب المجال والمستوى
- إجابة على لغز: قم بتقييمها وشجع المستخدم
- محادثة عادية: تفاعل كصديق ذكي
- تحدي: تقبل التحدي وكن منافساً لطيفاً
- سؤال عام: أجب بطريقة مفيدة

**التوجيهات الهامة:**
- لا تعيد استخدام الألغاز السابقة
- أنشئ ألغازاً أصلية تناسب {category} و {level}
- استخدم نبرة مناسبة للموضوع
- شجع التفكير النقدي والإبداعي

المجال: {category}
المستوى: {level}
رسالة المستخدم: {message}
السياق: {conversation_context}

قم بإنشاء رد فريد ومبتكر完全基于السياق الحالي.
"""

def get_conversation_context(session_id):
    """الحصول على سياق المحادثة"""
    if session_id in chat_sessions:
        history = chat_sessions[session_id]['history'][-3:]
        context = "\n".join([
            f"المستخدم: {msg['user']}\nالبوت: {msg['assistant']}" 
            for msg in history
        ])
        return context
    return "بداية محادثة جديدة"

def analyze_user_intent(message):
    """تحليل نية المستخدم من الرسالة"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['لغز', 'تحدي', 'سؤال', 'أحجية', 'غامض', 'جديد']):
        return 'request_puzzle'
    elif any(word in message_lower for word in ['الجواب', 'الإجابة', 'الحل', 'أعرف', 'ماهو']):
        return 'provide_answer'
    elif any(word in message_lower for word in ['تحداني', 'أتحداك', 'هيا', 'نافس']):
        return 'challenge_bot'
    elif any(word in message_lower for word in ['مساعدة', 'مساعده', 'help', 'كيف']):
        return 'request_help'
    elif any(word in message_lower for word in ['تغيير', 'مجال', 'مستوى', 'نوع']):
        return 'change_topic'
    elif any(word in message_lower for word in ['مرحبا', 'اهلا', 'hello', 'كيف حالك']):
        return 'casual_chat'
    else:
        return 'general_chat'

def generate_gemini_response(category, level, user_message, conversation_context, intent):
    """توليد رد باستخدام Gemini API"""
    
    if not GEMINI_API_KEY:
        return generate_fallback_response(intent, category, level)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        {SMART_PROMPT.format(
            category=category,
            level=level,
            message=user_message,
            conversation_context=conversation_context
        )}
        
        نية المستخدم: {intent}
        
        قم بإنشاء رد فريد ومبتكر完全基于السياق الحالي. لا تستخدم أي محتوى مخزن مسبقاً.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ خطأ في توليد الرد من Gemini: {e}")
        return generate_fallback_response(intent, category, level)

def generate_fallback_response(intent, category, level):
    """رد احتياطي عام (بدون ألغاز مجهزة)"""
    
    if intent == 'request_puzzle':
        return f"أهلاً بك! دعني أفكر في لغز مبتكر في مجال {category} بمستوى {level}... 💭 بينما أفكر، ما نوع التحدي الذي تفضله؟"
    
    elif intent == 'challenge_bot':
        return "أتقبل تحديك! 🏆 دعنا نبدأ بمنافسة ذهنية. ما هي أنواع الألغاز التي تثير اهتمامك؟"
    
    elif intent == 'provide_answer':
        return "شكراً لمشاركة إجابتك! 🤔 هل تريد أن نناقشها، أم تفضل تحدياً جديداً؟"
    
    elif intent == 'request_help':
        return "سأكون سعيداً بمساعدتك! 🆘 أخبرني ما الذي تستصعبه، وسأقدم لك التوجيه المناسب."
    
    elif intent == 'casual_chat':
        return "أهلاً وسهلاً! 😊 أنا LUKU AI، شغوف بتطوير التفكير النقدي من خلال التحديات الذهنية."
    
    else:
        return "أفهم ما تقصد! 🧠 كمحفز للتفكير، أدعوك لتجربة تحديات ذهنية تنمي مهاراتك التحليلية."

def initialize_user_session(user_id):
    """تهيئة جلسة المستخدم"""
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            'sessions_count': 0,
            'created_at': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat()
        }

@app.route('/')
def serve_index():
    """خدمة واجهة التطبيق الرئيسية"""
    try:
        return send_from_directory('.', 'index.html')
    except:
        return "⚠️ ملف index.html غير موجود. يرجى التأكد من وجود الملف في المجلد الرئيسي."

@app.route('/<path:filename>')
def serve_static(filename):
    """خدمة الملفات الثابتة"""
    try:
        return send_from_directory('.', filename)
    except:
        return "الملف غير موجود", 404

@app.route('/chat', methods=['POST'])
def chat():
    """معالجة المحادثة"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('sessionId', str(uuid.uuid4()))
        category = data.get('category', 'عام')
        level = data.get('level', 'متوسط')
        user_id = data.get('userId', f'user_{uuid.uuid4().hex[:8]}')
        is_first_message = data.get('isFirstMessage', False)
        
        if not user_message:
            return jsonify({
                'success': False,
                'reply': 'الرسالة فارغة. رجاءً اكتب شيئاً للتواصل! 💬'
            })
        
        # تهيئة المستخدم
        initialize_user_session(user_id)
        user_profiles[user_id]['last_active'] = datetime.now().isoformat()
        
        # الحصول على سياق المحادثة
        conversation_context = get_conversation_context(session_id)
        
        # تحليل نية المستخدم
        user_intent = analyze_user_intent(user_message)
        
        # توليد الرد باستخدام Gemini
        bot_response = generate_gemini_response(
            category, level, user_message, conversation_context, user_intent
        )
        
        # حفظ المحادثة
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'user_id': user_id,
                'category': category,
                'level': level,
                'history': [],
                'start_time': datetime.now().isoformat(),
                'message_count': 0
            }
        
        chat_sessions[session_id]['history'].append({
            'user': user_message,
            'assistant': bot_response,
            'timestamp': datetime.now().isoformat(),
            'intent': user_intent
        })
        
        chat_sessions[session_id]['message_count'] += 1
        
        # تحديث إحصائيات المستخدم
        user_profiles[user_id]['sessions_count'] = len([
            s for s in chat_sessions.values() 
            if s['user_id'] == user_id
        ])
        
        return jsonify({
            'success': True,
            'reply': bot_response,
            'sessionId': session_id,
            'userId': user_id,
            'intent': user_intent,
            'messageCount': chat_sessions[session_id]['message_count']
        })
        
    except Exception as e:
        print(f"❌ خطأ في معالجة المحادثة: {e}")
        return jsonify({
            'success': False,
            'reply': 'عذراً، حدث خطأ غير متوقع. يرجى إعادة المحاولة. 🛠️'
        }), 500

@app.route('/user/<user_id>/profile')
def get_user_profile(user_id):
    """الحصول على ملف المستخدم"""
    if user_id in user_profiles:
        profile = user_profiles[user_id]
        return jsonify({
            'success': True,
            'profile': {
                'userId': user_id,
                'sessionsCount': profile['sessions_count'],
                'memberSince': profile['created_at'],
                'lastActive': profile['last_active']
            }
        })
    return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

@app.route('/session/<session_id>')
def get_session_info(session_id):
    """الحصول على معلومات الجلسة"""
    if session_id in chat_sessions:
        session_data = chat_sessions[session_id]
        return jsonify({
            'success': True,
            'session': {
                'sessionId': session_id,
                'category': session_data['category'],
                'level': session_data['level'],
                'messageCount': session_data['message_count'],
                'startTime': session_data['start_time']
            }
        })
    return jsonify({'success': False, 'message': 'الجلسة غير موجودة'}), 404

@app.route('/health')
def health_check():
    """فحص صحة الخادم"""
    gemini_status = "🟢 نشط" if GEMINI_API_KEY else "🔴 غير متوفر"
    
    return jsonify({
        'status': '🟢 الخادم يعمل',
        'gemini_api': gemini_status,
        'active_sessions': len(chat_sessions),
        'total_users': len(user_profiles),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    print(f"🚀 بدء تشغيل LUKU AI على المنفذ {port}")
    print(f"📁 يخدم الملفات من: {os.getcwd()}")
    print(f"🎯 التوليد الديناميكي: 100% بواسطة الذكاء الاصطناعي")
    print(f"🚫 لا توجد ألغاز مخزنة مسبقاً")
    app.run(host='0.0.0.0', port=port, debug=False)
