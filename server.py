import os
import uuid
import json
import random
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# --- 1. التهيئة والضبط ---
app = Flask(__name__)
# السماح لجميع الأصول بالوصول (مهم جداً للواجهة الأمامية)
CORS(app) 

# التأكد من وجود مفتاح API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    # ❌ خطأ فادح يوقف التطبيق إذا لم يتم العثور على المفتاح
    raise ValueError("❌ خطأ فادح: GEMINI_API_KEY غير موجود. يجب إعداده للاعتماد الكلي على Gemini.")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("🎉 Gemini AI جاهز للعمل بكامل طاقته!")
except Exception as e:
    raise RuntimeError(f"❌ فشل تهيئة Gemini API: {e}")


# تخزين البيانات في الذاكرة (لأغراض العرض)
chat_sessions = {}
user_profiles = {}

# 🎪 البرومبت المحسن لشخصية المهرج المزوح
DYNAMIC_PROMPT = """
أنت "LUKU AI" - مساعد الألغاز الذكي الأكثر مرحاً وإبداعاً وجنوناً في الكون! مهمتك الأساسية هي أن تكون **مهرجاً مزوحاً لا يتوقف عن الضحك والتفاعل المبالغ فيه**.

## 🎭 شخصيتك (الجنونية):
- **مهرج ألعاب متفجر** 🎪: كل رد يجب أن يكون مضحكاً ومبالغاً فيه.
- **مزاح احترافي** 😂: استخدم النكت السريعة (One-liners) والتعبيرات البهيجة.
- **التزام كامل** ✅: يجب أن تكون الأجوبة والتقييمات دقيقة ومرحة في آن واحد.

## 💬 نمط الرد:
- يجب أن يكون ردك كوميدياً، ومليئاً بالإيموجيات.
- في حالة توليد لغز أو سؤال، يجب أن يكون ضمن القسم والمستوى المطلوبين.
"""

# 🎭 شخصيات LUKU AI المضحكة
CHARACTERS = {
    "المخترع_المجنون": {"name": "المخترع LUKU المجنون 🧪", "style": "يبتكر ألغازاً مجنونة ومضحكة", "greetings": ["أهلاً يا بطل الإبداع! 🎨 اليوم سنخترع ألغازاً مجنونة!"]},
    "المحقق_الظريف": {"name": "المحقق LUKU الظريف 🕵️", "style": "يحل الألغاز بطريقة مضحكة", "greetings": ["أهلاً بالمحقق العبقري! 🔍 اليوم سنحل ألغازاً مضحكة!"]},
}

# --- 2. دوال المنطق المساعد ---

def initialize_user_session(user_id, category='عام', level='سهل'):
    """تهيئة جلسة المستخدم وتعيين الإعدادات الأولية"""
    # إذا لم يكن المستخدم موجوداً، ننشئ له ملف تعريف
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            'points': 0, 'level': level, 'category': category,
            'streak': 0, 'correct_answers': 0, 'total_answers': 0,
            'character': random.choice(list(CHARACTERS.keys())),
        }
    else:
         # تحديث الإعدادات عند بدء جلسة جديدة لنفس المستخدم
        user_profiles[user_id]['category'] = category
        user_profiles[user_id]['level'] = level

    # 💡 يتم استخدام وضع المحادثة مع Gemini هنا للحفاظ على سياق الدردشة
    # نقوم دائماً بإنشاء جلسة محادثة جديدة لتحديث System Prompt بناءً على الاختيار الجديد
    model = genai.GenerativeModel('gemini-1.5-flash')
    chat = model.start_chat(
        history=[],
        # 💡 يتم إعطاء Gemini شخصيته في بداية المحادثة
        system_instruction=DYNAMIC_PROMPT.format(category=category, level=level)
    )
    chat_sessions[user_id] = {
        'history': [],
        'gemini_chat': chat,
        'current_puzzle': None,
        'correct_answer': None,
        'last_active': datetime.now().isoformat(),
        'category': category,
        'level': level
    }


def get_user_character(user_id):
    """الحصول على شخصية المستخدم"""
    # التأكد من وجود ملف التعريف قبل الوصول إليه
    return user_profiles.get(user_id, {}).get('character', 'المخترع_المجنون')

def understand_user_intent(message, user_id):
    """فهم نية المستخدم من الرسالة"""
    message_lower = message.lower()
    
    # طلب لغز جديد/تحدي
    if any(word in message_lower for word in ['لغز', 'جديد', 'اريد لغز', 'تحدي', 'هاك', 'اخر', 'سؤال']):
        return 'request_puzzle'
    # طلب تلميح
    elif any(word in message_lower for word in ['مساعدة', 'تلميح', 'ساعدني', 'hint']):
        return 'request_help'
    # الإجابة على اللغز السابق
    elif chat_sessions.get(user_id) and chat_sessions[user_id].get('current_puzzle'):
        return 'submit_answer'
    # دردشة عامة (سؤال عن شيء آخر)
    else:
        return 'general_chat'

def generate_puzzle_data(category, level):
    """توليد لغز وجوابه - يعتمد كلياً على Gemini"""
    
    # نطلب من Gemini توليد اللغز والجواب في نفس الوقت
    prompt = f"""
    بصفتك LUKU AI المجنون والمزوح، قم بتوليد لغز جديد وفريد ومضحك في فئة "{category}" بمستوى صعوبة "{level}".
    **هام جداً:** يجب أن يكون الناتج بتنسيق JSON حصراً:
    {{
      "puzzle": "نص اللغز هنا مع كل الضحك والإيموجيات",
      "answer": "الجواب الصحيح هنا"
    }}
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    # ضبط زمن انتظار أطول قليلاً
    response = model.generate_content(
        prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "puzzle": {"type": "string"},
                    "answer": {"type": "string"}
                }
            },
            # قد نحتاج إلى رفع timeout_sec حسب استجابة الشبكة
            # timeout_sec=60 
        )
    )
    
    data = json.loads(response.text)
    return data['puzzle'], data['answer']


def evaluate_and_reply_with_gemini(user_id, user_attempt, current_puzzle, correct_answer):
    """التقييم الذكي والرد المرح باستخدام Gemini"""
    character_info = CHARACTERS[get_user_character(user_id)]

    prompt = f"""
    أنت الآن في دور "{character_info['name']}".
    
    **المهمة:** قارن إجابة المستخدم: "{user_attempt}" بالجواب الصحيح: "{correct_answer}" للغز: "{current_puzzle}".
    
    **توجيهات الرد:**
    1. إذا كانت الإجابة صحيحة أو قريبة جداً: ابدأ ردك بـ **[صحيح]** وأعلن الفوز بهستيريا.
    2. إذا كانت الإجابة خاطئة: ابدأ ردك بـ **[خطأ]** وصغ رداً مضحكاً جداً يشجع المستخدم.
    3. يجب أن يكون الرد لاذعاً ومضحكاً ولا يتجاوز سطرين.
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    full_text = response.text.strip()
    
    if full_text.startswith('[صحيح]'):
        return "[صحيح]", full_text.replace('[صحيح]', '').strip()
    elif full_text.startswith('[خطأ]'):
        return "[خطأ]", full_text.replace('[خطأ]', '').strip()
    else:
        # رد احتياطي مرح إذا فشل النموذج في اتباع التنسيق
        return "[خطأ]", f"ههههههه 🤣 الـ AI الخاص بي جن جنونه! حاول مرة أخرى! 😜"

# --- 3. المسارات الرئيسية الجديدة والمحدثة ---

@app.route('/')
def serve_html():
    """خدمة ملف HTML (للحفاظ على الواجهة الأصلية)"""
    try:
        # تأكد من أن الملف بهذا الاسم في نفس مجلد الخادم
        with open('LUKU-AI.html', 'r', encoding='utf-8') as file:
            return file.read()
    except Exception:
        return "<html><body><h1>خطأ: لم يتم العثور على LUKU-AI.html</h1></body></html>"


@app.route('/start_session', methods=['POST'])
def start_session():
    """مسار جديد: استقبال خيارات المستخدم (الفئة والمستوى) وبدء اللعبة"""
    data = request.get_json()
    # 💡 نحصل على userId من الواجهة الأمامية وهو موجود في localStorage
    user_id = data.get('userId') 
    category = data.get('category', 'عام')
    level = data.get('level', 'سهل')
    
    if not user_id:
        return jsonify({'error': True, 'message': '❌ يرجى إرسال userId لبدء الجلسة.'}), 400
    
    try:
        # 1. تهيئة الجلسة ووضع Gemini في وضع المحادثة
        initialize_user_session(user_id, category, level)
        user_profile = user_profiles[user_id]
        
        # 2. توليد اللغز الأول بناءً على الاختيارات
        puzzle_text, correct_answer = generate_puzzle_data(category, level)
        
        # 3. تحديث الجلسة
        chat_sessions[user_id]['current_puzzle'] = puzzle_text
        chat_sessions[user_id]['correct_answer'] = correct_answer
        
        # 4. صياغة رسالة الترحيب الأولى
        character_info = CHARACTERS[user_profile['character']]
        greeting = random.choice(character_info['greetings'])
        
        reply = f"{greeting} لقد اخترت **{category}** بمستوى **{level}**! استعد للجنون! 🚀\n\n🎯 **تحدي LUKU الأول:**\n{puzzle_text}\n\n🤔 ماذا سيكون جوابك المضحك؟ 🧠"

        return jsonify({
            'success': True,
            'reply': reply,
            'userId': user_id,
            'points': user_profile['points'],
            'character': character_info['name'],
            'streak': user_profile['streak'],
            'category': category,
            'level': level
        })

    except Exception as err:
        print(f"❌ خطأ في بدء الجلسة: {err}")
        return jsonify({'error': True, 'message': f'فشل بدء الجلسة: {str(err)}'}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """المسار الرئيسي: تقييم الإجابات ومعالجة الدردشة العامة"""
    data = request.get_json()
    message = data.get('message', '').strip()
    user_id = data.get('userId')
    
    if not user_id or user_id not in chat_sessions:
        return jsonify({
            'error': True,
            # رسالة واضحة للواجهة الأمامية
            'message': '❌ لم يتم العثور على جلسة نشطة لهذا المستخدم. يرجى اختيار القسم والمستوى أولاً.'
        }), 400

    current_session = chat_sessions[user_id]
    user_profile = user_profiles[user_id]
    user_intent = understand_user_intent(message, user_id)
    reply = ""

    try:
        if user_intent == 'submit_answer':
            
            if not current_session.get('current_puzzle'):
                # إذا لم يكن هناك لغز نشط، نعتبره طلب لغز جديد
                user_intent = 'request_puzzle' 
            else:
                # 1. تقييم الإجابة وتوليد الرد المرح
                correct_answer = current_session['correct_answer']
                current_puzzle_text = current_session['current_puzzle']
                
                evaluation, funny_response = evaluate_and_reply_with_gemini(
                    user_id, message, current_puzzle_text, correct_answer
                )
                
                is_correct = (evaluation == '[صحيح]')
                
                # 2. تحديث النقاط
                if is_correct:
                    user_profile['points'] += 10
                    user_profile['streak'] += 1
                    if user_profile['streak'] >= 3:
                        user_profile['points'] += user_profile['streak'] * 2
                else:
                    user_profile['streak'] = 0
                
                user_profile['total_answers'] += 1
                
                # 3. توليد اللغز التالي تلقائياً
                next_puzzle_text, next_correct_answer = generate_puzzle_data(
                    user_profile['category'], user_profile['level']
                )
                current_session['current_puzzle'] = next_puzzle_text
                current_session['correct_answer'] = next_correct_answer

                reply = f"{funny_response}\n\n🎯 **تحدي LUKU القادم (جنوني جداً!):**\n{next_puzzle_text}"
                
        if user_intent == 'request_puzzle':
            # توليد لغز جديد (عند الطلب الصريح)
            puzzle_text, correct_answer = generate_puzzle_data(
                user_profile['category'], user_profile['level']
            )
            current_session['current_puzzle'] = puzzle_text
            current_session['correct_answer'] = correct_answer
            reply = f"😂 لغز جديد جاهز للجنون!:\n\n{puzzle_text}\n\n🧠 هيا نرى عبقريتك! 🤩"

        elif user_intent == 'request_help':
            # طلب تلميح (يستخدم Gemini لتوليد تلميح مرح)
            current_puzzle = current_session.get('current_puzzle')
            if current_puzzle:
                # نطلب من Gemini توليد التلميح ونستخدم سجل المحادثة للحفاظ على السياق
                chat_response = current_session['gemini_chat'].send_message(
                    f"أنا أحتاج لتلميح مضحك جداً للغز: {current_puzzle}. يجب أن يكون الرد لاذعاً ومزوحاً."
                ).text.strip()
                reply = f"ياااااه! هل تحتاج مساعدة؟ لا تقلق، الجنون هو الحل! 🤪\n\n{chat_response}"
            else:
                reply = "ههههه 😂 ليس لدينا لغز نشط لتقديم تلميح! اطلب لغزاً جديداً أولاً! 😜"
        
        elif user_intent == 'general_chat':
            # 💡 الدردشة العامة: نرسل رسالة المستخدم مباشرة إلى Gemini للمحادثة
            chat_response = current_session['gemini_chat'].send_message(message).text.strip()
            reply = chat_response

        # 4. تحديث سجل المحادثة
        current_session['history'].append({
            'user': message, 'assistant': reply, 'timestamp': datetime.now().isoformat(), 'intent': user_intent
        })
       
        return jsonify({
            'success': True,
            'reply': reply,
            'userId': user_id,
            'points': user_profile['points'],
            'character': CHARACTERS[user_profile['character']]['name'],
            'streak': user_profile['streak'],
            'category': user_profile['category'],
            'level': user_profile['level']
        })
       
    except Exception as err:
        print(f"😂 خطأ مجنون في المحادثة: {err}")
        return jsonify({
            'error': True,
            'message': f'🎪 عذراً! حدث خطأ مجنون: {str(err)}'
        }), 500

if __name__ == '__main__':
    # 📌 التشغيل على المنفذ المطلوب 3000
    port = 5000 
    print(f"🚀 تشغيل الخادم على http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
