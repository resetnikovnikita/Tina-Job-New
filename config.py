"""
config.py — все настройки, каналы, категории
"""
import os

if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

API_ID         = int(os.getenv("API_ID", "0"))
API_HASH       = os.getenv("API_HASH", "")
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

YUKASSA_SHOP_ID    = os.getenv("YUKASSA_SHOP_ID", "")
YUKASSA_SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY", "")
WEBHOOK_URL        = os.getenv("WEBHOOK_URL", "")

CHECK_INTERVAL    = 1500
POSTS_LIMIT       = 5
FREE_TRIAL_DAYS   = 4
PROMO_CODE        = "TINANEWJOB"
PROMO_DISCOUNT    = 0.35
DAILY_CHECK_LIMIT = 3

PLANS = {
    "2w": {"label": "2 недели",  "price": 420,  "days": 14},
    "1m": {"label": "1 месяц",   "price": 750,  "days": 30},
    "3m": {"label": "3 месяца",  "price": 1500, "days": 90},
}

CATEGORIES = {
    "video":   "🎬 Видеомонтаж",
    "design":  "🎨 Дизайн / иллюстрации",
    "smm":     "📱 SMM / маркетинг",
    "copy":    "✍️ Копирайтинг",
    "dev":     "💻 Программирование",
    "3d":      "🧊 3D моделирование",
    "photo":   "📸 Фотография",
    "finance": "💰 Бухгалтерия",
    "admin":   "🗂 Ассистент / менеджер",
    "tutor":   "📚 Репетиторство",
    "easy":    "🌱 Без опыта / студентам",
    "transl":  "🌐 Переводы",
    "legal":   "⚖️ Юридические услуги",
    "voice":   "🎙 Озвучка / подкасты",
}

CHANNELS_BY_CATEGORY = {
    "video": [
        "reels_job", "SearchEditorr", "montazhery_ru",
        "video_editing_jobs", "reelsjobs_ru", "vakansii_reelsmaker",
        "Edit_Jobs", "neiro_ai_vacancy",
    ],
    "design": [
        "designer_jobs", "designer_ru", "ui_ux_jobs",
        "designjob_ru", "figma_jobs_ru", "web_design_jobs", "graphicjobs",
        "Infographics_chat", "Designs_squad", "workfordesigner",
        "MPdesigns", "vakansii_dizaynerov", "Designs_job",
    ],
    "smm": [
        "vacancysmm", "smm_leads", "ttargetjob",
        "smmlancer", "targetjob", "tg_smm_jobs", "marketing_jobs_ru", "dnative",
        "smmfreelancer", "smmtheworkkp", "smm_top_vacancy",
        "Traffic_jobs", "Content_Jobss",
    ],
    "copy": [
        "textmoney", "textodromo", "copywrite_jobs",
        "workforwriters", "content_freelance", "seo_copywrite_jobs", "tg_copywriters",
    ],
    "dev": [
        "it_jobs_ru", "python_jobs_ru", "getmatch_jobs",
        "js_jobs_ru", "flutter_jobs_ru", "backend_jobs_ru", "remote_it_jobs", "tg_dev_jobs",
        "Python_Jbs", "Jobs_for_IT", "it_vacancy_relocation",
    ],
    "3d": [
        "CGFreelance", "jobs_3d_ru", "blender_jobs",
        "cg_freelance_ru", "archviz_jobs", "viz_jobs_ru",
    ],
    "photo": [
        "photojobs_ru", "rueventjob", "photo_freelance_ru", "photographer_jobs",
    ],
    "finance": [
        "buh_remote", "financefreelance", "buhgalter_jobs",
        "fin_freelance_ru", "nalogi_jobs_ru",
    ],
    "admin": [
        "distantsiya", "ipomogator", "GetClient", "udafrii",
        "normlbot", "assistant_jobs_ru", "pm_jobs_ru", "vacansia_ru",
        "MPlace_jobs", "MPmanagers", "menedgermarketpleisov",
        "MP_Seller", "MPcase", "Jobs_MP", "LeadMagnet_MP",
    ],
    "tutor": [
        "repetitor_jobs", "online_teach_jobs", "edujobs",
        "teach_online_jobs", "edu_freelance_ru",
    ],
    "easy": [
        "distantsiya", "ipomogator", "freelancetaverna",
        "Koteyka_Freelancer", "podrabotka_ru", "students_job_ru", "bez_opyta_ru",
        "rabota_is_doma_vakansii", "freelance_joob", "work_from_lina",
    ],
    "transl": [
        "translate_jobs_ru", "linguist_jobs_ru", "perevod_freelance", "transl_remote_ru",
    ],
    "legal": [
        "legal_freelance_ru", "yurist_jobs_ru", "law_remote_jobs",
    ],
    "voice": [
        "voice_jobs_ru", "podcast_jobs_ru", "ozvuchka_freelance", "voice_actor_jobs",
    ],
}

GLOBAL_CHANNELS = [
    "distantsiya", "ipomogator", "GetClient", "udafrii",
    "normlbot", "freelancetaverna", "Koteyka_Freelancer",
    "fl_ru_jobs", "kwork_jobs", "mediajobs",
    "sova_freelance", "Remotjob", "ruwiw", "liberty_job",
    "frilancekomfort", "worldeventjob", "talentedpeoples",
    "TRemoters", "worksvsem", "prostranstvowork",
    "sferadeytelnosti", "startfreelancer", "theypaywell",
    "butukovuy_lux", "freelanceeboom", "theypaygood",
    "Uyut_frilans", "eagle_to_work", "g00djob4all",
    "Auraworker", "AuraLead", "auraremote",
]

KEYWORDS_BY_CATEGORY = {
    "video": {
        "hashtags": ["#монтажер","#монтажёр","#рилсмейкер","#reelsmaker","#видеомонтаж","#монтажист","#reels","#рилс","#монтаж","#shortsmaker"],
        "keywords": ["ищу монтажера","нужен монтажер","требуется монтажер","ищу монтажёра","нужен монтажёр","ищу рилсмейкера","нужен рилсмейкер","монтаж рилс","video editor","capcut","нужен видеограф"],
        "stop": ["ищу работу","предлагаю услуги","услуги монтажа","моё портфолио"],
    },
    "design": {
        "hashtags": ["#дизайнер","#графическийдизайн","#uxdesign","#uidesign","#иллюстратор","#вебдизайн","#логотип","#figma","#дизайн"],
        "keywords": ["ищу дизайнера","нужен дизайнер","требуется дизайнер","ищу иллюстратора","нужен ui/ux","graphic designer","web designer","нужен верстальщик","дизайн логотипа"],
        "stop": ["ищу работу","предлагаю услуги","услуги дизайнера"],
    },
    "smm": {
        "hashtags": ["#smm","#сммщик","#таргет","#таргетолог","#контентмейкер","#маркетинг"],
        "keywords": ["ищу smm","нужен smm","требуется smm","ищу таргетолога","нужен таргетолог","ищем контент-менеджера","ведение соцсетей","ищу маркетолога","ведение telegram","ведение тг канала"],
        "stop": ["ищу работу","предлагаю услуги","услуги smm"],
    },
    "copy": {
        "hashtags": ["#копирайтер","#копирайтинг","#автор","#контент","#seo","#сео","#редактор","#журналист"],
        "keywords": ["ищу копирайтера","нужен копирайтер","требуется копирайтер","ищем автора","нужен автор статей","написание текстов","нужен seo-специалист","нужен сценарист"],
        "stop": ["ищу работу","предлагаю услуги","услуги копирайтера"],
    },
    "dev": {
        "hashtags": ["#разработчик","#программист","#developer","#backend","#frontend","#fullstack","#python","#javascript","#flutter","#android","#ios"],
        "keywords": ["ищу разработчика","нужен разработчик","требуется программист","ищем backend","нужен frontend","ищу flutter","нужен python","нужен react","нужен telegram бот","нужен wordpress"],
        "stop": ["ищу работу","ищу заказы","предлагаю услуги"],
    },
    "3d": {
        "hashtags": ["#3d","#3dмоделирование","#blender","#3dmax","#визуализация","#3dart","#cg"],
        "keywords": ["ищу 3d","нужен 3d","требуется 3d моделер","нужна 3d визуализация","blender artist","3d modeling","ищу моделера","нужен визуализатор","нужна анимация"],
        "stop": ["ищу работу","предлагаю услуги"],
    },
    "photo": {
        "hashtags": ["#фотограф","#photographer","#фотосъемка","#предметнаясъемка","#ретушер"],
        "keywords": ["ищу фотографа","нужен фотограф","ищем ретушера","предметная съёмка","фото для маркетплейса","продуктовая фотосъёмка"],
        "stop": ["ищу работу","предлагаю услуги","услуги фотографа"],
    },
    "finance": {
        "hashtags": ["#бухгалтер","#финансист","#бухгалтерия","#налоги","#1с"],
        "keywords": ["ищу бухгалтера","нужен бухгалтер","требуется бухгалтер","удалённый бухгалтер","ведение учёта","сдача отчётности"],
        "stop": ["ищу работу","предлагаю услуги"],
    },
    "admin": {
        "hashtags": ["#ассистент","#помощник","#администратор","#менеджер"],
        "keywords": ["ищу ассистента","нужен ассистент","виртуальный помощник","личный помощник удалённо","нужен операционный менеджер","ищу аккаунт-менеджера","нужен pm","ищу project manager"],
        "stop": ["ищу работу","предлагаю услуги"],
    },
    "tutor": {
        "hashtags": ["#репетитор","#преподаватель","#онлайн_урок","#куратор"],
        "keywords": ["ищу репетитора","нужен репетитор","ищу преподавателя","нужен ментор","ищу куратора курса","преподавание онлайн"],
        "stop": ["предлагаю услуги репетитора","ищу учеников"],
    },
    "easy": {
        "hashtags": ["#безопыта","#студентам","#подработка","#удалёнка","#удаленка","#начинающим"],
        "keywords": ["без опыта","для студентов","начинающим","обучим","обучаем","опыт не нужен","подработка","парт-тайм","part time","гибкий график","не требуется опыт","работа из дома"],
        "stop": ["ищу работу","ищу подработку","предлагаю услуги"],
    },
    "transl": {
        "hashtags": ["#переводчик","#перевод","#translator","#локализация"],
        "keywords": ["ищу переводчика","нужен переводчик","перевод текста","локализация","нужен синхронный переводчик"],
        "stop": ["предлагаю услуги переводчика"],
    },
    "legal": {
        "hashtags": ["#юрист","#адвокат","#договор"],
        "keywords": ["ищу юриста","нужен юрист","составить договор","юридическая консультация удалённо"],
        "stop": ["предлагаю юридические услуги"],
    },
    "voice": {
        "hashtags": ["#озвучка","#диктор","#подкаст","#voiceover"],
        "keywords": ["ищу диктора","нужен диктор","требуется озвучка","нужен голос для ролика","озвучить видео"],
        "stop": ["предлагаю услуги диктора"],
    },
}
