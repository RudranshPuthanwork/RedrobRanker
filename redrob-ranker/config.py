# ── JD TARGETS ──────────────────────────────────────────────────────────────
EXPERIENCE_SWEET_SPOT = (6, 8)
EXPERIENCE_ACCEPTABLE = (4, 11)

TARGET_LOCATIONS = [
    "Pune", "Noida", "Delhi", "New Delhi", "Gurugram", "Gurgaon",
    "Hyderabad", "Mumbai", "Bengaluru", "Bangalore", "NCR"
]

NOTICE_IDEAL_DAYS = 30
NOTICE_ACCEPTABLE_DAYS = 90

# ── SERVICES FIRMS ───────────────────────────────────────────────────────────
SERVICES_FIRMS = [
    "TCS", "Tata Consultancy", "Infosys", "Wipro", "Accenture",
    "Cognizant", "Capgemini", "HCL", "Tech Mahindra", "Mphasis",
    "Hexaware", "Mindtree", "NIIT Technologies", "Birlasoft"
]

# ── NON-TECHNICAL TITLES ─────────────────────────────────────────────────────
NON_TECH_TITLES = [
    "HR Manager", "Human Resources", "Marketing Manager", "Graphic Designer",
    "Content Writer", "Operations Manager", "Sales Manager", "Finance",
    "Recruiter", "Account Manager", "Business Development"
]

# ── CORE SKILL WEIGHTS ───────────────────────────────────────────────────────
CORE_SKILL_WEIGHTS = {
    "embeddings": 1.0,
    "sentence-transformers": 1.0,
    "sentence transformers": 1.0,
    "vector search": 1.0,
    "vector database": 1.0,
    "semantic search": 1.0,
    "faiss": 0.9,
    "pinecone": 0.9,
    "weaviate": 0.9,
    "qdrant": 0.9,
    "milvus": 0.9,
    "elasticsearch": 0.85,
    "opensearch": 0.85,
    "information retrieval": 1.0,
    "ranking": 0.85,
    "reranking": 0.9,
    "nlp": 0.8,
    "natural language processing": 0.8,
    "rag": 0.9,
    "retrieval augmented generation": 0.9,
    "llm": 0.7,
    "large language model": 0.7,
    "python": 0.6,
    "pytorch": 0.5,
    "transformers": 0.6,
    "huggingface": 0.6,
    "lora": 0.5,
    "qlora": 0.5,
    "fine-tuning": 0.5,
    "learning to rank": 0.8,
    "xgboost": 0.4,
    "ndcg": 0.6,
    "a/b testing": 0.4,
    # anti-signals
    "computer vision": -0.2,
    "image classification": -0.2,
    "speech recognition": -0.2,
    "robotics": -0.4,
    "tts": -0.1,
}

# ── CAREER DESCRIPTION KEYWORDS ──────────────────────────────────────────────
CAREER_CORE_TERMS = [
    "embedding", "vector", "retrieval", "ranking", "search", "recommendation",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "elasticsearch",
    "deployed", "production", "real users", "shipped", "launched",
    "nlp", "language model", "bert", "transformer", "fine-tun", "rag",
    "semantic", "hybrid search", "dense retrieval", "bm25", "rerank",
    "recall", "precision", "relevance", "index", "query"
]

CAREER_ANTI_TERMS = [
    "mechanical", "hardware", "cad", "solidworks", "ansys",
    "accounting", "procurement", "supply chain", "customer support",
    "brand design", "packaging", "editorial"
]

# ── TITLE CATEGORIES ─────────────────────────────────────────────────────────
HIGH_VALUE_TITLES = [
    "ML Engineer", "Machine Learning Engineer", "AI Engineer",
    "Applied Scientist", "Research Engineer", "NLP Engineer",
    "Search Engineer", "Ranking Engineer", "Recommendation Engineer",
    "RecSys Engineer", "Applied ML", "Applied AI", "MLE"
]

MEDIUM_VALUE_TITLES = [
    "Software Engineer", "Backend Engineer", "Data Scientist",
    "Data Engineer", "Platform Engineer", "Infrastructure Engineer",
    "Full Stack Engineer", "Senior Engineer"
]

# ── SCORING WEIGHTS ──────────────────────────────────────────────────────────
WEIGHTS = {
    "career":     0.35,
    "skills":     0.25,
    "experience": 0.20,
    "location":   0.10,
    "behavioral": 0.10,
}

BEHAVIORAL_MULTIPLIER_RANGE = (0.5, 1.0)
