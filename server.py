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
"""

# 🎲 مكتبة ألغاز احتياطية مرحة
FUNNY_PUZZLES = {
    "رياضة": [
        "🏀 في الملعب دائماً أراقب الجميع، أتحكم في اللعبة لكنني لا ألعب! من أكون؟ (الجواب: الحكم)",
        "⚽ أركض في الملعب، ألعب بالكرة، لكن عندما أتعب... أجلس على الكرسي! من أكون؟ (الجواب: اللاعب البديل)",
        "🎯 في الملعب ولكنني لا أتعب، أراقب اللاعبين وأحمل بطاقات ملونة! من أكون؟"
    ],
    "ثقافة": [
        "📚 أملك صفحات كثيرة، أحكي قصصاً لا تنتهي، لكنني لا أتحدث! من أكون؟ (الجواب: الكتاب)",
        "🎭 على المساهر أظهر، أضحك وأبكي، لكن مشاعري مزيفة! من أكون؟ (الجواب: الممثل)",
        "🎨 أرسم لوحات جميلة، أعبر عن المشاعر، لكن بلا فرشاة! من أكون؟"
    ],
    "منطق": [
        "🕳️ كلما أخذت مني أكثر... كبرت أكثر! من أكون؟ (الجواب: الحفرة)",
        "📶 أصعد وأهبط طوال اليوم، لكنني لا أتحرك من مكاني! من أكون؟ (الجواب: السلم)",
        "🔄 ليس لي بداية ولا نهاية، لكنني في كل مكان! من أكون؟"
    ],
    "دين": [
        "🕌 أنا أول من دعا إلى الله، عشت في زمن الطوفان! من أكون؟ (الجواب: نوح عليه السلام)",
        "📖 أنزلت في شهر رمضان، أهدي الناس إلى طريق الحق! ما أنا؟ (الجواب: القرآن الكريم)",
        "🌙 في السماء أظهر، أهدي المسافرين، وأحدد أوقات الصلاة! من أكون؟"
    ],
    "ترفيه": [
        "🎬 على الشاشة أظهر، أجعلك تضحك وتبكي، لكنني لست حقيقياً! من أكون؟ (الجواب: الفيلم)",
        "🎮 في العالم الافتراضي أعيش، أتحدى اللاعبين، وأقدم المغامرات! من أكون؟",
        "🎪 تحت الخيمة أقدم العروض، أضحك الأطفال والكبار! من أكون؟"
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

def generate_funny_puzzle(category, level, user_id):
    """توليد لغز مضحك وفريد"""
    
    # توليد بصمة فريدة لتجنب التكرار
    unique_seed = f"{datetime.now().strftime('%Y%m%d%H%M')}_{user_id[:8]}"
    random.seed(hash(unique_seed) % 10000)
    
    if category in FUNNY_PUZZLES:
        puzzle = random.choice(FUNNY_PUZZLES[category])
        
        # إضافة لمسات مرحة
        funny_intros = [
            "🎪 هيا نلعب! ها هو لغز مضحك: ",
            "😂 استعد للضحك! هذا اللغز سيجعلك تضحك: ",
            "🎭 ياااااه! لغز جديد مضحك: ",
            "🤣 ضحك ومتعة! جرب هذا اللغز: ",
            "🎊 مرح وفرح! ها هو لغز ممتع: "
        ]
        
        return f"{random.choice(funny_intros)}\n\n{puzzle}"
    else:
        return generate_gemini_funny_puzzle(category, level)

def generate_gemini_funny_puzzle(category, level):
    """استخدام Gemini لتوليد ألغاز مضحكة"""
    if not GEMINI_API_KEY:
        # ألغاز احتياطية مضحكة
        backup_puzzles = [
            f"😂 في عالم {category}، ما هو الشيء الذي يرى كل شيء لكنه لا يتكلم؟ (تلميح: 🤐)",
            f"🎭 في {category}، ما الذي يملك أسناناً لكنه لا يعض؟ (تلميح: 😁)",
            f"🤣 في {category}، ما الذي يملك قلباً لكنه لا ينبض؟ (تلميح: 💖)",
            f"🎪 في {category}، ما الذي يملك مدناً بلا بيوت؟ (تلميح: 🗺️)",
            f"😄 في {category}، ما الذي ينام ويقظ لكنه لا يتعب؟ (تلميح: 🛌)"
        ]
        return random.choice(backup_puzzles)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        {DYNAMIC_PROMPT.format(category=category, level=level, message="")}
        
        ابتكر لغزاً مضحكاً وفريداً في مجال {category} بمستوى {level}.
        يجب أن يكون اللغز:
        - مضحكاً ومرحاً
        - جديداً تماماً
        - مكتوباً بالعربية
        - يحتوي على إيموجيات مناسبة
        
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
            'last_puzzles': []
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
        
        if is_first_message:
            # 🎪 بدء محادثة جديدة بمقدمة مضحكة
            greeting = random.choice(character_info['greetings'])
            puzzle = generate_funny_puzzle(category, level, user_id)
            
            reply = f"{greeting}\n\n{puzzle}\n\n🤔 فكر جيداً وأجب... 🧠"
            
        else:
            # 🎭 معالجة ردود المستخدم بطريقة مضحكة
            # محاكاة تقييم الإجابة (يمكن تطوير هذا الجزء)
            is_correct = len(message) > 2  # محاكاة بسيطة
            
            funny_response = get_funny_response(is_correct, message)
            next_puzzle = generate_funny_puzzle(category, level, user_id)
            
            reply = f"{funny_response}\n\n🎯 التحدي القادم:\n{next_puzzle}"
            
            # تحديث النقاط
            if is_correct:
                user_profiles[user_id]['points'] += 10
                user_profiles[user_id]['correct_answers'] += 1
                user_profiles[user_id]['streak'] += 1
            else:
                user_profiles[user_id]['streak'] = 0
            
            user_profiles[user_id]['total_answers'] += 1
        
        # حفظ المحادثة
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'history': [],
                'user_id': user_id,
                'start_time': datetime.now().isoformat()
            }
        
        chat_sessions[session_id]['history'].append({
            'user': message,
            'assistant': reply,
            'timestamp': datetime.now().isoformat()
        })
       
        return jsonify({
            'success': True,
            'reply': reply,
            'sessionId': session_id,
            'userId': user_id,
            'points': user_profiles[user_id]['points'],
            'character': character_info['name'],
            'correctAnswers': user_profiles[user_id]['correct_answers'],
            'totalAnswers': user_profiles[user_id]['total_answers']
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
        return jsonify({
            'success': True,
            'profile': {
                'points': profile['points'],
                'level': profile['level'],
                'streak': profile['streak'],
                'correct_answers': profile['correct_answers'],
                'total_answers': profile['total_answers'],
                'character': CHARACTERS[profile['character']]['name'],
                'join_date': profile['join_date']
            },
            'message': '🎉 ها هو ملفك الشخصي الممتع!'
        })
    return jsonify({'error': 'المستخدم غير موجود'}), 404

@app.route('/puzzle/funny')
def get_funny_puzzle():
    """الحصول على لغز مضحك عشوائي"""
    category = request.args.get('category', random.choice(list(FUNNY_PUZZLES.keys())))
    user_id = request.args.get('user_id', f'guest_{random.randint(1000, 9999)}')
    
    puzzle = generate_funny_puzzle(category, 'متوسط', user_id)
    
    return jsonify({
        'success': True,
        'puzzle': puzzle,
        'category': category,
        'message': '😂 ها هو لغز مضحك من LUKU AI!'
    })

@app.route('/health')
def health_check():
    return jsonify({
        'status': '✅ الخادم يعمل وبكامل طاقته المرحة!',
        'users_count': len(user_profiles),
        'sessions_active': len(chat_sessions),
        'message': '🎪 LUKU AI جاهز للضحك والألغاز!'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    print(f"🎉 بدء تشغيل LUKU AI المضحك على المنفذ {port}")
    print(f"🎯 الميزات: ألغاز مضحكة، شخصيات مرحة، تفاعل ذكي")
    print(f"😂 جاهز لجعل التعلم متعة والتفكير ضحك! 🚀")
    app.run(host='0.0.0.0', port=port, debug=False)