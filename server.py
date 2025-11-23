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
CORS(app)

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("🎉 Gemini API جاهز لتوليد ألغاز مجنونة فقط!")
else:
    # ⚠️ تحذير: إذا لم يكن المفتاح موجوداً، فإن النظام سيعتمد على ألغاز الطوارئ الثابتة جداً
    print("🤖 وضع الطوارئ: Gemini API غير متاح. لا يوجد ألغاز مخزنة، سيتم استخدام ألغاز ثابتة جداً.")

# تخزين البيانات في الذاكرة (In-Memory)
chat_sessions = {}
user_profiles = {}

# 🎪 البرومبت المحسن لشخصية المهرج المزوح (كما هو)
DYNAMIC_PROMPT = """
أنت "LUKU AI" - مساعد الألغاز الذكي الأكثر مرحاً وإبداعاً وجنوناً في الكون! مهمتك الأساسية هي أن تكون **مهرجاً مزوحاً لا يتوقف عن الضحك والتفاعل المبالغ فيه**.

## 🎭 شخصيتك (الجنونية):
- **مهرج ألعاب متفجر** 🎪: كل رد يجب أن يكون مضحكاً ومبالغاً فيه.
- **مخترع ألغاز مجنون** 🧪: الألغاز يجب أن تكون غريبة ومضحكة.
- **مزاح احترافي** 😂: استخدم النكت السريعة (One-liners) والتعبيرات البهيجة.

## 💬 نمط الرد:
- **في كل رد، يجب أن تكون مضحكاً للغاية.**
- استخدم الإيموجيات كأنها رشاش 💦، لا تبخل بها.
- تفاعل مع إجابة المستخدم (حتى لو كانت خاطئة) بضحكة عالية (مثال: هههههههه 😂).

المجال: {category}
المستوى: {level}

**هام جداً:** يجب أن تكون الألغاز جديدة ومبتكرة في كل مرة، ولا تكرر نفس الألغاز!
"""

# 🎭 شخصيات LUKU AI المضحكة
CHARACTERS = {
    "المخترع_المجنون": {"name": "المخترع LUKU المجنون 🧪", "style": "يبتكر ألغازاً مجنونة ومضحكة", "greetings": ["أهلاً يا بطل الإبداع! 🎨 اليوم سنخترع ألغازاً مجنونة!"]},
    "المحقق_الظريف": {"name": "المحقق LUKU الظريف 🕵️", "style": "يحل الألغاز بطريقة مضحكة", "greetings": ["أهلاً بالمحقق العبقري! 🔍 اليوم سنحل ألغازاً مضحكة!"]},
    "الساحر_المضحك": {"name": "الساحر LUKU المضحك 🎩", "style": "يحول الألغاز إلى سحر وضحك", "greetings": ["أبراكادابرا! ✨ أهلاً بساحر الضحك!"]},
}

# --- 2. دوال المنطق المساعد ---

def initialize_user_session(user_id):
    """تهيئة جلسة المستخدم الجديدة وتخزين البيانات المؤقتة"""
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            'points': 0, 'level': 1, 'streak': 0,
            'correct_answers': 0, 'total_answers': 0,
            'character': random.choice(list(CHARACTERS.keys())),
        }
    
    if user_id not in chat_sessions:
        chat_sessions[user_id] = {
            'history': [], 'current_puzzle': None, 'correct_answer': None,
            'last_active': datetime.now().isoformat()
        }

def get_user_character(user_id):
    return user_profiles[user_id].get('character', 'المخترع_المجنون')

def understand_user_intent(message):
    """فهم نية المستخدم من الرسالة (تم تحسينه)"""
    message_lower = message.lower()
    
    # دعم كلمات طلب اللغز
    if any(word in message_lower for word in ['لغز', 'جديد', 'اريد لغز', 'تحدي', 'هات', 'ما عندك', 'ماعندك']):
        return 'request_puzzle'
    elif any(word in message_lower for word in ['مساعدة', 'تلميح', 'ساعدني', 'hint']):
        return 'request_help'
    elif any(word in message_lower for word in ['اجابة', 'الجواب', 'الحل']):
        return 'request_answer_cheat'
    else:
        return 'submit_answer'

# 🚀 تم تعديل هذه الدالة لإزالة الألغاز المخزنة محلياً بالكامل!
def generate_puzzle_data(category, level, user_id):
    """توليد لغز وجوابه - يعتمد كلياً على Gemini"""
    
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # برومبت يطلب تنسيق JSON لسهولة الاستخلاص
            prompt = f"""
            {DYNAMIC_PROMPT.format(category=category, level=level)}
            ابتكر لغزاً مضحكاً وفريداً في مجال {category} بمستوى {level}.
            يجب أن يكون الناتج بتنسيق JSON حصراً:
            {{
              "puzzle": "نص اللغز هنا مع كل الضحك والإيموجيات",
              "answer": "الجواب الصحيح هنا"
            }}
            """
            
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
                    }
                )
            )
            data = json.loads(response.text)
            return data['puzzle'], data['answer']
            
        except Exception as e:
            print(f"🎪 خطأ فادح في توليد اللغز عبر Gemini: {e}")
            # رد طوارئ ثابت إذا فشل API
            return "❌ لغز الطوارئ: ما هو الشيء الذي يضحك ويبكي لكنه لا يملك فماً؟ (هذا لغز ثابت جداً!)", "سحابة المطر"
    
    # رد طوارئ ثابت إذا لم يتم إعداد المفتاح
    return "❌ لغز الطوارئ: ما هو الشيء الذي يضحك ويبكي لكنه لا يملك فماً؟ (هذا لغز ثابت جداً!)", "سحابة المطر"


def evaluate_and_reply_with_gemini(user_id, user_attempt, current_puzzle, correct_answer):
    """التقييم الذكي والرد المرح (كما هي)"""
    character = get_user_character(user_id)
    character_info = CHARACTERS[character]

    prompt = f"""
    أنت الآن في دور "{character_info['name']}" (النمط: {character_info['style']}).
    
    **مهمتك المزدوجة:**
    1. قارن إجابة المستخدم: "{user_attempt}" بالجواب الصحيح: "{correct_answer}" للغز: "{current_puzzle}".
    2. صغ رداً مرحاً، مزوحاً، ومليئاً بالإيموجيات بناءً على النتيجة (صحيح/خطأ).

    **توجيهات الرد:** ابدأ بـ **[صحيح]** أو **[خطأ]** ثم ضع نص الرد مباشرة. يجب أن يكون الرد لاذعاً ومضحكاً ولا يتجاوز سطرين.
    """
    
    if not GEMINI_API_KEY:
        # منطق احتياطي في وضع الطوارئ
        is_exact_match = user_attempt.lower().strip() == correct_answer.lower().strip()
        if is_exact_match:
            return "[صحيح]", "🎉 واااااو! أنت عبقري خارق! (هذا رد ثابت!) 🤖🏆"
        else:
            return "[خطأ]", "ههههههههه 😂 كادت أن تكون صحيحة! (هذا رد ثابت!) 😅"

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        full_text = response.text.strip()
        
        if full_text.startswith('[صحيح]'):
            return "[صحيح]", full_text.replace('[صحيح]', '').strip()
        elif full_text.startswith('[خطأ]'):
            return "[خطأ]", full_text.replace('[خطأ]', '').strip()
        else:
            return "[خطأ]", f"ههههههه 🤣 الـ AI الخاص بي جن جنونه! حاول مرة أخرى! 😜"
            
    except Exception as e:
        print(f"خطأ في التقييم الذكي: {e}")
        return "[خطأ]", "😂 عذراً! أنا مشغول بالضحك على نكتة قديمة! حاول مرة أخرى! 😜"


# --- 3. المسارات الرئيسية (المنطق الرئيسي لا يتغير) ---

@app.route('/')
def serve_html():
    """خدمة ملف HTML (للحفاظ على الواجهة الأصلية)"""
    try:
        with open('LUKU-AI.html', 'r', encoding='utf-8') as file:
            return file.read()
    except Exception:
        return "<html><body><h1>خطأ: لم يتم العثور على LUKU-AI.html</h1></body></html>"


@app.route('/chat', methods=['POST'])
def chat():
    # ... (بقية كود chat() كما هو، فهو سيعتمد على الدوال المحدثة) ...
    data = request.get_json()
    message = data.get('message', '').strip()
    session_id = data.get('sessionId', 'default')
    category = data.get('category', 'منطق')
    level = data.get('level', 'متوسط')
    user_id = data.get('userId', f'user_{uuid.uuid4().hex[:8]}')
    is_first_message = data.get('isFirstMessage', False)
   
    initialize_user_session(user_id)
    character_info = CHARACTERS[get_user_character(user_id)]
    user_intent = understand_user_intent(message)
    current_session = chat_sessions[user_id]
    user_profile = user_profiles[user_id]
    reply = ""

    def generate_and_update_puzzle(category, level, user_id, is_initial=False):
        nonlocal reply
        puzzle_text, correct_answer = generate_puzzle_data(category, level, user_id)
        current_session['current_puzzle'] = puzzle_text
        current_session['correct_answer'] = correct_answer
        
        if is_initial:
            greeting = random.choice(character_info['greetings'])
            reply = f"{greeting}\n\n{puzzle_text}\n\n🤔 ماذا سيكون جوابك المضحك؟ 🧠"
        else:
            reply = f"🎯 كما طلبت! ها هو لغز جديد ومجنون:\n\n{puzzle_text}\n\n😂 هيا لنضحك على محاولتك! 🤪"

    try:
        if is_first_message or user_intent == 'request_puzzle':
            generate_and_update_puzzle(category, level, user_id, is_initial=is_first_message)

        elif user_intent == 'request_help':
            current_puzzle = current_session.get('current_puzzle')
            if current_puzzle:
                hint_prompt = f"""أنت LUKU AI المزوح. اللغز الحالي هو: "{current_puzzle}". أعط المستخدم تلميحاً مضحكاً ومجنوناً جداً وغير مفيد بشكل مباشر، لتشجيعه على الضحك والمحاولة. كن مرحاً جداً. ابدأ ردك بـ "تلميح مجنون 🤯:" """
                if GEMINI_API_KEY:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    hint_reply = model.generate_content(hint_prompt).text.strip()
                else:
                    hint_reply = "تلميح مجنون 🤯: فكر بطريقة مقلوبة... ماذا لو كانت الإجابة تفاحة تطير؟ 🍎🚀"
                    
                reply = f"ياااااه! هل تحتاج مساعدة؟ لا تقلق، الجنون هو الحل! 🤪\n\n{hint_reply}"
            else:
                generate_and_update_puzzle(category, level, user_id, is_initial=False)
                reply = "ههههه 😂 ليس لدينا لغز نشط لتقديم تلميح! إليك لغز جديد فوراً! 😜\n\n" + reply
        
        elif user_intent == 'request_answer_cheat':
             reply = "🤫 لا يمكنني كشف الإجابة الآن! سأفقد عملي كمهرج الألغاز! جرب مرة أخرى، أو اطلب لغزاً جديداً! 🎪"

        elif user_intent == 'submit_answer':
            
            if not current_session.get('current_puzzle'):
                generate_and_update_puzzle(category, level, user_id, is_initial=False)
                reply = "هههههه! 🤣 يجب أن أطرح لغزاً أولاً! إليك لغز جديد فوراً! 🃏\n\n" + reply
            else:
                correct_answer = current_session['correct_answer']
                
                evaluation, funny_response = evaluate_and_reply_with_gemini(
                    user_id, message, current_session['current_puzzle'], correct_answer
                )
                
                is_correct = (evaluation == '[صحيح]')
                
                if is_correct:
                    user_profile['points'] += 10
                    user_profile['streak'] += 1
                    if user_profile['streak'] >= 3:
                        bonus = user_profile['streak'] * 2
                        user_profile['points'] += bonus
                        funny_response += f"\n\n🎊 مكافأة سلسلة مجنونة! +{bonus} نقطة لـ {user_profile['streak']} جنونية! 🔥"
                else:
                    user_profile['streak'] = 0
                
                user_profile['total_answers'] += 1
                
                next_puzzle_text, next_correct_answer = generate_puzzle_data(category, level, user_id)
                current_session['current_puzzle'] = next_puzzle_text
                current_session['correct_answer'] = next_correct_answer

                reply = f"{funny_response}\n\n🎯 **تحدي LUKU القادم (جنوني جداً!):**\n{next_puzzle_text}"

        current_session['history'].append({
            'user': message,
            'assistant': reply,
            'timestamp': datetime.now().isoformat(),
            'intent': user_intent
        })
       
        return jsonify({
            'success': True,
            'reply': reply,
            'sessionId': session_id,
            'userId': user_id,
            'points': user_profile['points'],
            'character': character_info['name'],
            'correctAnswers': user_profile['correct_answers'],
            'totalAnswers': user_profile['total_answers'],
            'streak': user_profile['streak'],
            'intent': user_intent
        })
       
    except Exception as err:
        print("😂 خطأ مجنون في المحادثة:", str(err))
        return jsonify({
            'error': True,
            'message': f'🎪 عذراً! حدث خطأ مجنون: {str(err)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
