# questions.py

QUESTION_BANK = {
    "Background": [
        "Where have you studied previously and what qualifications did you obtain?",
        "Can you explain any gaps in your study or employment history?",
    ],
    "Study destination": [
        "Why have you chosen to study in the UK rather than your home country or another destination like the US or Canada?",
        "The costs of studying in the UK are higher than in your home country. Why incur these extra costs?",
    ],
    "Institution choice": [
        "Why did you choose this university over others in the UK?",
        "What do you know about the city or area where your university is located?",
    ],
    "Course choice": [
        "Why did you choose this specific course?",
        "How does this course relate to your previous education or work experience?",
    ],
    "Course knowledge": [
        "What are the names or topics of some modules you will study?",
        "How long does your course last and how is it structured?",
    ],
    "Finances": [
        "How do you plan to pay for your tuition fees and living expenses in the UK?",
        "Who is financing your studies and what is the source of those funds?",
    ],
    "Accommodation": [
        "Where will you be living while studying in the UK?",
        "How will you travel from your accommodation to campus?",
    ],
    "Future plans": [
        "What do you plan to do after completing your course?",
        "Do you intend to return to your home country after your studies?",
    ],
}

QUESTION_ORDER = [
    "Background",
    "Study destination",
    "Institution choice",
    "Course choice",
    "Course knowledge",
    "Finances",
    "Accommodation",
    "Future plans",
]

QUESTION_HINTS = {
    "Study destination": (
        "Mention 1–2 concrete reasons: course quality, recognition, Graduate Route, "
        "or proximity, based on your own research."
    ),
    "Institution choice": (
        "Mention a specific feature: ranking, facilities, department strength, or placement links, "
        "and how you found this out."
    ),
    "Course choice": (
        "Link the course to your previous study, work experience, and career goal, in your own words."
    ),
    "Course knowledge": "Name at least one real module, assessment method, and practical outcome.",
    "Finances": (
        "Explain the funding source, total amount, how long funds have been held, and what evidence you "
        "have (bank statements, sponsor letter)."
    ),
    "Accommodation": "Say where you will live, approximate cost, and how you will commute.",
    "Background": "Give a short timeline (years and institutions) and explain any gaps honestly.",
    "Future plans": (
        "State your post-study plan in your home country and how the course helps you return and progress there."
    ),
}

ANSWER_TIPS = {
    "default": "Use: direct answer → one specific detail → one short link to your goal.",
    "Study destination": "Mention one UK-specific academic advantage and one career reason.",
    "Institution choice": "Mention one university strength and one department or location reason backed by facts.",
    "Course choice": "Connect previous study or work directly to this exact course and career path.",
    "Course knowledge": "Mention a real module, assessment style, and practical outcome or accreditation.",
    "Finances": "State source of funds, total amount, how long they have been held, and documents you will show.",
    "Accommodation": "Name where you will stay, estimated cost, and how you will commute to campus.",
    "Background": "Give a clear timeline and explain gaps honestly, with what you were doing.",
    "Future plans": "Describe a specific job or role in your home country and how the course prepares you.",
}

RED_FLAGS = [
    "i don't know",
    "not sure",
    "my agent",
    "i haven't researched",
    "i plan to stay",
    "might not return",
    "i just want",
]

POSITIVE = [
    "because",
    "specifically",
    "module",
    "dissertation",
    "placement",
    "nhs",
    "career",
    "return",
    "back home",
    "sponsor",
    "tuition",
]

DEFAULT_THINK_TIME = 2
DEFAULT_MIN_WORDS = 20
QUESTION_TIME_SECONDS = 3 * 60

COURSE_PROFILES = {
    "UG – Business & Management": {
        "examples": "Business Management; International Business; Business Administration; Entrepreneurship",
        "extra_tip": (
            "Mention business modules like strategy, operations, leadership, entrepreneurship, or "
            "international business, and explain how they fit your career plan."
        ),
        "keywords": [
            "business",
            "management",
            "strategy",
            "leadership",
            "operations",
            "entrepreneurship",
            "international business",
            "organisation",
            "business environment",
        ],
    },
    "UG – Cyber Security & Networks": {
        "examples": "Cyber Security; Network Computing; Information Security; Digital Forensics",
        "extra_tip": (
            "Mention topics like information security, ethical hacking, network security, digital forensics, "
            "or risk management, and explain how they relate to your planned role."
        ),
        "keywords": [
            "cyber security",
            "information security",
            "network security",
            "ethical hacking",
            "digital forensics",
            "risk",
            "threat",
            "soc",
            "penetration testing",
            "security",
        ],
    },
    "UG – Data Science & AI": {
        "examples": "Data Science; Artificial Intelligence; Machine Learning; Business Analytics",
        "extra_tip": (
            "Mention analytics, machine learning, statistics, Python, big data, or AI applications, and "
            "explain how these skills support your future work."
        ),
        "keywords": [
            "data science",
            "artificial intelligence",
            "machine learning",
            "analytics",
            "statistics",
            "python",
            "big data",
            "data visualisation",
            "predictive",
            "model",
        ],
    },
    "UG – Education": {
        "examples": "Education Studies; Primary Education; Teaching Studies; Childhood Education",
        "extra_tip": (
            "Mention curriculum, pedagogy, inclusive education, classroom practice, or educational leadership, "
            "and connect the course to your teaching or education role."
        ),
        "keywords": [
            "education",
            "teaching",
            "pedagogy",
            "curriculum",
            "classroom",
            "inclusive education",
            "childhood",
            "learning",
            "teacher",
            "assessment",
        ],
    },
    "PG – Cyber Security": {
        "examples": "MSc Cyber Security; MSc Information Security; MSc Digital Forensics",
        "extra_tip": (
            "Mention cyber risk, governance, security operations, network defence, penetration testing, or "
            "digital forensics, and explain the specific role you want after graduation."
        ),
        "keywords": [
            "cyber security",
            "information security",
            "governance",
            "risk",
            "digital forensics",
            "penetration testing",
            "security operations",
            "network defence",
            "security policy",
            "compliance",
        ],
    },
    "PG – Data Science, AI & Analytics": {
        "examples": "MSc Data Science; MSc Artificial Intelligence; MSc Business Analytics; Big Data Analytics",
        "extra_tip": (
            "Mention machine learning, statistical modelling, analytics, data engineering, AI, or visualisation, "
            "and explain how the programme supports your technical career goals."
        ),
        "keywords": [
            "data science",
            "analytics",
            "machine learning",
            "artificial intelligence",
            "statistical modelling",
            "data engineering",
            "python",
            "big data",
            "visualisation",
            "predictive analytics",
        ],
    },
    "PG – Public Health": {
        "examples": "Master of Public Health; Public Health and Community Studies; Global Health",
        "extra_tip": (
            "Mention epidemiology, health promotion, policy, biostatistics, environmental health, or "
            "population health, and explain how this supports your work back home."
        ),
        "keywords": [
            "public health",
            "epidemiology",
            "health promotion",
            "policy",
            "biostatistics",
            "population health",
            "community health",
            "global health",
            "prevention",
            "environmental health",
        ],
    },
    "PG – Pre-registration Nursing": {
        "examples": (
            "MSc Adult Nursing (Pre-registration); Master of Nursing with Pre-Registration (Adult); "
            "MSc Nursing (Pre-registration - Adult); MSc Nursing Studies (Adult) Pre-registration"
        ),
        "extra_tip": (
            "Mention that this is a graduate-entry route into registered nursing, and refer to clinical "
            "placements, NMC standards, patient care, evidence-based practice, simulation, and registration."
        ),
        "keywords": [
            "pre-registration nursing",
            "adult nursing",
            "nursing",
            "clinical placement",
            "placements",
            "nmc",
            "patient care",
            "evidence-based practice",
            "simulation",
            "registered nurse",
            "professional registration",
        ],
    },
    # Add more tracks as needed (Finance, MBA, Logistics, etc.)
}