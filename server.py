from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import uuid
import os
import json
import random
from datetime import datetime, timedelta
import hashlib

# تهيئة تطبيق Flask
app = Flask(__name__)
CORS(app)  # تمكين CORS

# استخدام مفتاح API من متغير البيئة
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("🎉 Gemini API جاهز لتوليد ألغاز فريدة!")
else:
    print("🤖 وضع التجربة - سيتم استخدام ألغاز متنوعة")

# تخزين البيانات
chat_sessions = {}
user_profiles = {}
leaderboard = {}

# 🎪 البرومبت المحسن لتوليد ألغاز فريدة ومرحة
DYNAMIC_PROMPT = """
أنت "LUKU AI" - مساعد الألغاز الذكي الأكثر مرحاً وإبداعاً في الكون! 

## 🎯 مهمتك:
1. **ابتكر ألغازاً جديدة** في كل مرة - لا تكرر الألغاز
2. **كن مرحاً ومضحكاً** - استخدم النكت والتلميحات المضحكة
3. **تفاعل بذكاء** مع إجابات المستخدم
4. **استخدم الإيموجيات** بشكل مبدع وجذاب

## 🎭 شخصيتك:
- **مقدم ألعاب مشهور** 🎪
- **صديق مرح ومضحك** 😄
- **مشجع محترف** 🏆
- **مبدع ألغاز خارق** 🧠

## 💬 نمط الرد:
- ابدأ مباشرة بلغز فريد ومرح
- استخدم نبرة حماسية ومضحكة
- تفاعل مع إجابات المستخدم بذكاء
- حافظ على الإثارة والمرح

المجال: {category}
المستوى: {level}
الرسالة: {message}

**هام جداً:** يجب أن تكون الألغاز جديدة ومبتكرة في كل مرة، ولا تكرر نفس الألغاز!
"""

# 🎲 مكتبة ألغاز احتياطية مرحة مع تنوع أكبر
FUNNY_PUZZLES = {
    "رياضة": [
        "🏀 في الملعب دائماً أراقب الجميع، أتحكم في اللعبة لكنني لا ألعب! من أكون؟ (الجواب: الحكم)",
        "⚽ أركض في الملعب، ألعب بالكرة، لكن عندما أتعب... أجلس على الكرسي! من أكون؟ (الجواب: اللاعب البديل)",
        "🎯 في الملعب ولكنني لا أتعب، أراقب اللاعبين وأحمل بطاقات ملونة! من أكون؟ (الجواب: الحكم)",
        "🥅 أحمي الشبكة بكل قوة، أمنع الأهداف بجسدي، من أكون؟ (الجواب: حارس المرمى)",
        "⏱️ أراقب الوقت بدقة، أحدد نهاية المباراة، لكنني لا أملك ساعة! من أكون؟ (الجواب: حكم الساحة)"
    ],
    "ثقافة": [
        "📚 أملك صفحات كثيرة، أحكي قصصاً لا تنتهي، لكنني لا أتحدث! من أكون؟ (الجواب: الكتاب)",
        "🎭 على المساهر أظهر، أضحك وأبكي، لكن مشاعري مزيفة! من أكون؟ (الجواب: الممثل)",
        "🎨 أرسم لوحات جميلة، أعبر عن المشاعر، لكن بلا فرشاة! من أكون؟ (الجواب: الفنان)",
        "🎵 أتكون من نغمات وحروف، أعبر عن المشاعر، من أكون؟ (الجواب: الأغنية)",
        "📖 أحمل حكمة الأجيال، أنقل المعرفة، لكنني لا أتكلم! من أكون؟ (الجواب: الكتاب)"
    ],
    "منطق": [
        "🕳️ كلما أخذت مني أكثر... كبرت أكثر! من أكون؟ (الجواب: الحفرة)",
        "📶 أصعد وأهبط طوال اليوم، لكنني لا أتحرك من مكاني! من أكون؟ (الجواب: السلم)",
        "🔄 ليس لي بداية ولا نهاية، لكنني في كل مكان! من أكون؟ (الجواب: الدائرة)",
        "🔢 أزيد عندما أنقص، وأنقص عندما أزيد! من أكون؟ (الجواب: العمر)",
        "💡 أضيء لكنني لا أحترق، أعمل بالكهرباء لكنني لست مصباحاً! من أكون؟ (الجواب: الفكرة)"
    ],
    "دين": [
        "🕌 أنا أول من دعا إلى الله، عشت في زمن الطوفان! من أكون؟ (الجواب: نوح عليه السلام)",
        "📖 أنزلت في شهر رمضان، أهدي الناس إلى طريق الحق! ما أنا؟ (الجواب: القرآن الكريم)",
        "🌙 في السماء أظهر، أهدي المسافرين، وأحدد أوقات الصلاة! من أكون؟ (الجواب: القمر)",
        "🕋 أتوجه إليكم في صلاتكم، لكنني لست في السماء! من أكون؟ (الجواب: الكعبة)",
        "🌅 أعلن بداية الصيام، ونهاية الإفطار، من أكون؟ (الجواب: الأذان)"
    ],
    "ترفيه": [
        "🎬 على الشاشة أظهر، أجعلك تضحك وتبكي، لكنني لست حقيقياً! من أكون؟ (الجواب: الفيلم)",
        "🎮 في العالم الافتراضي أعيش، أتحدى اللاعبين، وأقدم المغامرات! من أكون؟ (الجواب: لعبة الفيديو)",
        "🎪 تحت الخيمة أقدم العروض، أضحك الأطفال والكبار! من أكون؟ (الجواب: المهرج)",
        "🎤 أمسك بالميكروفون، أشدو بالأغاني، وأسعد الجمهور! من أكون؟ (الجواب: المغني)",
        "📺 أدخل بيوتكم كل يوم، أقدم البرامج والمسلسلات! من أكون؟ (الجواب: التلفزيون)"
    ]
}

# 🎭 شخصيات LUKU AI المضحكة
CHARACTERS = {
    "المخترع_المجنون": {
        "name": "المخترع LUKU المجنون 🧪", 
        "style": "يبتكر ألغازاً مجنونة ومضحكة",
        "greetings": [
            "أهلاً يا بطل الإبداع! 🎨 اليوم سنخترع ألغازاً مجنونة!",
            "المخترع المجنون LUKU في الخدمة! 🔬 مستعد لبعض الجنون؟",
            "ياااااه! 🚀 لنبتكر ألغازاً ستجعل عقلك يدور! 💫"
        ]
    },
    "المحقق_الظريف": {
        "name": "المحقق LUKU الظريف 🕵️", 
        "style": "يحل الألغاز بطريقة مضحكة",
        "greetings": [
            "أهلاً بالمحقق العبقري! 🔍 اليوم سنحل ألغازاً مضحكة!",
            "المحقق الظريف LUKU جاهز! 🕵️‍♂️ هل أنت مستعد للضحك؟",
            "لغز جديد ينتظر حلك! 🎯 لكن هذه المرة... سيكون مضحكاً! 😂"
        ]
    },
    "الساحر_المضحك": {
        "name": "الساحر LUKU المضحك 🎩", 
        "style": "يحول الألغاز إلى سحر وضحك",
        "greetings": [
            "أبراكادابرا! ✨ أهلاً بساحر الضحك!",
            "الساحر المضحك LUKU هنا! 🎪 لنحول الألغاز إلى ضحك!",
            "هيهيهي! 🎭 مستعد لبعض السحر والضحك؟ 🌟"
        ]
    }
}

def get_funny_response(is_correct=True, user_message=""):
    """إرجاع ردود مضحكة بناءً على الإجابة"""
    
    if is_correct:
        responses = [
            f"واو! 🎉 إجابة رائعة! {user_message} - هذا يجعلني أرقص من الفرح! 💃",
            f"مذهل! 🚀 {user_message} - حتى الروبوتات تحترم ذكاءك! 🤖",
            f"برافو! 🏆 {user_message} - إجابة تجعل نيوتن يغار منك! 🍎",
            f"رائع! 🔥 {user_message} - كأنك تقرأ أفكاري السرية! 🧠",
            f"إبداع! 🌟 {user_message} - هذه الإجابة تستحق وسام العبقرية! 🎖️"
        ]
    else:
        responses = [
            f"هههه! 😂 {user_message} - إجابة مبدعة... لكن خاطئة! جرب مرة أخرى! 💫",
            f"أوه! 🎪 {user_message} - كادت أن تكون صحيحة... مثل كوب شاي بلا سكر! ☕",
            f"مضحك! 🎭 {user_message} - كانت محاولة شجاعة! الجواب الصحيح قريب! 🎯",
            f"لا بأس! 🌈 {user_message} - حتى العباقرة يخطئون! جرب مرة أخرى! 💪",
            f"ههه! 🤣 {user_message} - إجابة ستجعل أينشتاين يضحك! حاول مرة أخرى! 🧠"
        ]
    
    return random.choice(responses)

def generate_unique_puzzle(category, level, user_id, used_puzzles):
    """توليد لغز فريد غير مكرر"""
    
    # توليد بصمة فريدة بناءً على الوقت والمستخدم والفئة
    unique_seed = f"{datetime.now().strftime('%Y%m%d%H%M')}_{user_id[:8]}_{category}"
    random.seed(hash(unique_seed) % 10000)
    
    if category in FUNNY_PUZZLES:
        available_puzzles = [p for p in FUNNY_PUZZLES[category] if p not in used_puzzles]
        
        if available_puzzles:
            puzzle = random.choice(available_puzzles)
        else:
            # إذا تم استخدام جميع الألغاز، نعيد استخدام أحدها مع تعديل
            puzzle = random.choice(FUNNY_PUZZLES[category])
            # إضافة تعديل بسيط لتجنب التكرار المباشر
            puzzle = puzzle.replace("!", "🎯").replace("؟", "🤔")
    else:
        puzzle = generate_gemini_funny_puzzle(category, level)
    
    # إضافة لمسات مرحة
    funny_intros = [
        "🎪 هيا نلعب! ها هو لغز مضحك: ",
        "😂 استعد للضحك! هذا اللغز سيجعلك تضحك: ",
        "🎭 ياااااه! لغز جديد مضحك: ",
        "🤣 ضحك ومتعة! جرب هذا اللغز: ",
        "🎊 مرح وفرح! ها هو لغز ممتع: "
    ]
    
    return f"{random.choice(funny_intros)}\n\n{puzzle}"

def generate_gemini_funny_puzzle(category, level):
    """استخدام Gemini لتوليد ألغاز مضحكة وفريدة"""
    if not GEMINI_API_KEY:
        # ألغاز احتياطية مضحكة ومتنوعة
        backup_puzzles = [
            f"😂 في عالم {category}، ما هو الشيء الذي يرى كل شيء لكنه لا يتكلم؟ (تلميح: 🤐)",
            f"🎭 في {category}، ما الذي يملك أسناناً لكنه لا يعض؟ (تلميح: 😁)",
            f"🤣 في {category}، ما الذي يملك قلباً لكنه لا ينبض؟ (تلميح: 💖)",
            f"🎪 في {category}، ما الذي يملك مدناً بلا بيوت؟ (تلميح: 🗺️)",
            f"😄 في {category}، ما الذي ينام ويقظ لكنه لا يتعب؟ (تلميح: 🛌)",
            f"🧩 في {category}، ما الذي يكبر كلما ضغطت عليه؟ (تلميح: 🎈)",
            f"🎯 في {category}، ما الذي يخترق الزجاج ولا يكسره؟ (تلميح: 🌞)",
            f"🤔 في {category}، ما الذي يتحرك بلا أرجل ويبكي بلا عيون؟ (تلميح: ☁️)"
        ]
        return random.choice(backup_puzzles)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        {DYNAMIC_PROMPT.format(category=category, level=level, message="")}
        
        ابتكر لغزاً مضحكاً وفريداً في مجال {category} بمستوى {level}.
        يجب أن يكون اللغز:
        - مضحكاً ومرحاً
        - جديداً تماماً وغير مكرر
        - مكتوباً بالعربية
        - يحتوي على إيموجيات مناسبة
        - مناسب للمستوى {level}
        
        ابدأ مباشرة باللغز المضحك!
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"🎪 خطأ في توليد اللغز: {e}")
        return "🎲 ها هو لغز مضحك: ما الذي ينام ويقظ لكنه لا يتعب؟ (الجواب: السرير) 🛌"

def initialize_user_session(user_id):
    """تهيئة جلسة المستخدم الجديدة"""
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            'points': 0,
            'level': 1,
            'streak': 0,
            'correct_answers': 0,
            'total_answers': 0,
            'achievements': [],
            'character': random.choice(list(CHARACTERS.keys())),
            'join_date': datetime.now().isoformat(),
            'used_puzzles': [],
            'last_active': datetime.now().isoformat()
        }
    
    if user_id not in leaderboard:
        leaderboard[user_id] = {
            'score': 0,
            'rank': len(leaderboard) + 1,
            'last_active': datetime.now().isoformat()
        }

def get_user_character(user_id):
    """الحصول على شخصية المستخدم"""
    return user_profiles[user_id].get('character', 'المخترع_المجنون')

def understand_user_intent(message):
    """فهم نية المستخدم من الرسالة"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['لغز', 'لغز جديد', 'اريد لغز', 'اعطني لغز', 'تحدي']):
        return 'request_puzzle'
    elif any(word in message_lower for word in ['اجابة', 'الجواب', 'الحل', 'اعرف', 'ماهو']):
        return 'request_answer'
    elif any(word in message_lower for word in ['مساعدة', 'مساعده', 'مساعدة', 'help']):
        return 'request_help'
    elif any(word in message_lower for word in ['مجال', 'تخصص', 'نوع', 'فئة']):
        return 'change_category'
    elif any(word in message_lower for word in ['مستوى', 'صعوبة', 'سهل', 'صعب']):
        return 'change_level'
    else:
        return 'general_chat'

# 🎯 المسارات الرئيسية المحدثة
@app.route('/')
def serve_html():
    """خدمة الموقع الرئيسي"""
    try:
        with open('LUKU-AI.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except Exception as e:
        return f"""
        <html>
        <head><title>LUKU AI</title></head>
        <body style="background: #0b0e14; color: white; text-align: center; padding: 50px;">
            <h1>🧩 LUKU AI - مساعد الألغاز المضحك</h1>
            <p>⚠️ خطأ في تحميل الموقع: {str(e)}</p>
            <p>✅ الخادم يعمل بشكل صحيح</p>
        </body>
        </html>
        """

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('sessionId', 'default')
        category = data.get('category', 'عام')
        level = data.get('level', 'متوسط')
        user_id = data.get('userId', f'user_{uuid.uuid4().hex[:8]}')
        is_first_message = data.get('isFirstMessage', False)
       
        # تهيئة المستخدم
        initialize_user_session(user_id)
        
        # الحصول على شخصية المستخدم
        character = get_user_character(user_id)
        character_info = CHARACTERS[character]
        
        # فهم نية المستخدم
        user_intent = understand_user_intent(message)
        
        if is_first_message:
            # 🎪 بدء محادثة جديدة بمقدمة مضحكة
            greeting = random.choice(character_info['greetings'])
            puzzle = generate_unique_puzzle(category, level, user_id, user_profiles[user_id]['used_puzzles'])
            
            # حفظ اللغز المستخدم
            user_profiles[user_id]['used_puzzles'].append(puzzle)
            if len(user_profiles[user_id]['used_puzzles']) > 20:  # الحد الأقصى للتخزين
                user_profiles[user_id]['used_puzzles'].pop(0)
                
            reply = f"{greeting}\n\n{puzzle}\n\n🤔 فكر جيداً وأجب... 🧠"
            
        else:
            if user_intent == 'request_puzzle':
                # طلب لغز جديد
                puzzle = generate_unique_puzzle(category, level, user_id, user_profiles[user_id]['used_puzzles'])
                user_profiles[user_id]['used_puzzles'].append(puzzle)
                if len(user_profiles[user_id]['used_puzzles']) > 20:
                    user_profiles[user_id]['used_puzzles'].pop(0)
                    
                reply = f"🎯 كما طلبت! ها هو لغز جديد:\n\n{puzzle}\n\n🤔 جاهز للتحدي؟"
                
            elif user_intent == 'request_answer':
                # طلب الإجابة
                reply = "🤫 لا يمكنني كشف الإجابة الآن! حاول التفكير مرة أخرى، أو اطلب لغزاً جديداً! 🎪"
                
            elif user_intent == 'request_help':
                # طلب المساعدة
                reply = f"🆘 أنا هنا لمساعدتك! يمكنك:\n• طلب لغز جديد بقول 'اريد لغز'\n• تغيير المجال\n• تغيير مستوى الصعوبة\n• أو ببساطة محادثة عادية! 💬"
                
            else:
                # 🎭 معالجة ردود المستخدم بطريقة مضحكة
                is_correct = len(message) > 3  # محاكاة أكثر ذكاءً
                
                funny_response = get_funny_response(is_correct, message)
                next_puzzle = generate_unique_puzzle(category, level, user_id, user_profiles[user_id]['used_puzzles'])
                user_profiles[user_id]['used_puzzles'].append(next_puzzle)
                if len(user_profiles[user_id]['used_puzzles']) > 20:
                    user_profiles[user_id]['used_puzzles'].pop(0)
                
                reply = f"{funny_response}\n\n🎯 التحدي القادم:\n{next_puzzle}"
                
                # تحديث النقاط
                if is_correct:
                    user_profiles[user_id]['points'] += 10
                    user_profiles[user_id]['correct_answers'] += 1
                    user_profiles[user_id]['streak'] += 1
                    
                    # مكافآت السلسلة
                    if user_profiles[user_id]['streak'] % 5 == 0:
                        bonus = user_profiles[user_id]['streak'] * 2
                        user_profiles[user_id]['points'] += bonus
                        reply += f"\n\n🎊 مكافأة سلسلة! +{bonus} نقطة لـ {user_profiles[user_id]['streak']} إجابات صحيحة متتالية! 🔥"
                else:
                    user_profiles[user_id]['streak'] = 0
                
                user_profiles[user_id]['total_answers'] += 1
        
        # تحديث وقت النشاط
        user_profiles[user_id]['last_active'] = datetime.now().isoformat()
        
        # حفظ المحادثة
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'history': [],
                'user_id': user_id,
                'start_time': datetime.now().isoformat(),
                'category': category,
                'level': level
            }
        
        chat_sessions[session_id]['history'].append({
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
            'points': user_profiles[user_id]['points'],
            'character': character_info['name'],
            'correctAnswers': user_profiles[user_id]['correct_answers'],
            'totalAnswers': user_profiles[user_id]['total_answers'],
            'streak': user_profiles[user_id]['streak'],
            'intent': user_intent
        })
       
    except Exception as err:
        print("😂 خطأ مضحك في المحادثة:", str(err))
        return jsonify({
            'error': True,
            'message': f'🎪 عذراً! حدث خطأ مضحك: {str(err)}'
        }), 500

# 🎊 مسارات إضافية مرحة
@app.route('/user/<user_id>/profile')
def get_user_profile(user_id):
    """الحصول على ملف المستخدم بطريقة مرحة"""
    if user_id in user_profiles:
        profile = user_profiles[user_id]
        accuracy = (profile['correct_answers'] / profile['total_answers'] * 100) if profile['total_answers'] > 0 else 0
        
        return jsonify({
            'success': True,
            'profile': {
                'points': profile['points'],
                'level': profile['level'],
                'streak': profile['streak'],
                'correct_answers': profile['correct_answers'],
                'total_answers': profile['total_answers'],
                'accuracy': round(accuracy, 1),
                'character': CHARACTERS[profile['character']]['name'],
                'join_date': profile['join_date'],
                'last_active': profile['last_active']
            },
            'message': '🎉 ها هو ملفك الشخصي الممتع!'
        })
    return jsonify({'error': 'المستخدم غير موجود'}), 404

@app.route('/puzzle/funny')
def get_funny_puzzle():
    """الحصول على لغز مضحك عشوائي"""
    category = request.args.get('category', random.choice(list(FUNNY_PUZZLES.keys())))
    user_id = request.args.get('user_id', f'guest_{random.randint(1000, 9999)}')
    
    initialize_user_session(user_id)
    puzzle = generate_unique_puzzle(category, 'متوسط', user_id, user_profiles[user_id]['used_puzzles'])
    user_profiles[user_id]['used_puzzles'].append(puzzle)
    
    return jsonify({
        'success': True,
        'puzzle': puzzle,
        'category': category,
        'message': '😂 ها هو لغز مضحك من LUKU AI!'
    })

@app.route('/user/<user_id>/change_category', methods=['POST'])
def change_user_category(user_id):
    """تغيير مجال المستخدم"""
    if user_id in user_profiles:
        data = request.get_json()
        new_category = data.get('category', 'عام')
        
        user_profiles[user_id]['used_puzzles'] = []  # مسح الألغاز المستخدمة
        
        return jsonify({
            'success': True,
            'message': f'🎯 تم تغيير المجال إلى {new_category}! استمتع بألغاز جديدة!',
            'new_category': new_category
        })
    return jsonify({'error': 'المستخدم غير موجود'}), 404

@app.route('/health')
def health_check():
    return jsonify({
        'status': '✅ الخادم يعمل وبكامل طاقته المرحة!',
        'users_count': len(user_profiles),
        'sessions_active': len(chat_sessions),
        'puzzles_available': sum(len(puzzles) for puzzles in FUNNY_PUZZLES.values()),
        'message': '🎪 LUKU AI جاهز للضحك والألغاز!'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    print(f"🎉 بدء تشغيل LUKU AI الذكي على المنفذ {port}")
    print(f"🎯 الميزات: ألغاز فريدة، تفاعل ذكي، شخصيات مرحة")
    print(f"😂 جاهز لجعل التعلم متعة والتفكير إبداعاً! 🚀")
    app.run(host='0.0.0.0', port=port, debug=False)