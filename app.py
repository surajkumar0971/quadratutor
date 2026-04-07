from io import BytesIO
import html
import json
import mimetypes
import os
import random
import re
from collections import Counter
from datetime import datetime
import time
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, send_file
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from assignment_generator import (
    build_assignment_items,
    generate_assignment_pdf_from_items,
    generate_assignment_questions_from_text,
)
from werkzeug.utils import secure_filename

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None


def load_local_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


load_local_env()

app = Flask(__name__)

LIBRARY_DIR = os.path.join(app.root_path, "library_uploads")
LIBRARY_INDEX_PATH = os.path.join(LIBRARY_DIR, "library_index.json")
DATA_TEXT_PATH = os.path.join(app.root_path, "data", "data.txt")
DATA_JSON_PATH = os.path.join(app.root_path, "data", "qa_database.json")
ALLOWED_LIBRARY_EXTENSIONS = {
    ".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".ppt", ".pptx"
}

questions = []
answers = []
qa_records = []
last_question = ""

STOP_WORDS = {
    "the", "and", "for", "that", "with", "this", "from", "have", "were", "your",
    "into", "about", "there", "their", "they", "them", "then", "than", "also",
    "because", "while", "where", "which", "what", "when", "will", "would", "should",
    "could", "been", "being", "are", "was", "is", "of", "to", "in", "on", "a", "an",
    "as", "it", "by", "or", "at", "be", "if", "we", "you", "can", "used", "using",
    "use", "during", "after", "before", "through", "these", "those", "such", "many",
    "more", "most", "some", "each", "other", "only", "very"
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}
BUILTIN_TOPIC_KNOWLEDGE = {
    "nalanda university": "Nalanda University was an ancient center of learning in India, located in present-day Bihar. It was famous for higher education, large libraries, and students who came from different parts of Asia to study subjects such as philosophy, medicine, mathematics, and Buddhism.",
    "pythagoras": "Pythagoras theorem says that in a right triangle, the square of the longest side is equal to the sum of the squares of the other two sides. If the two shorter sides are a and b, and the longest side is c, then a^2 + b^2 = c^2. This works only for a right-angled triangle.",
    "pythagorean": "Pythagoras theorem says that in a right triangle, the square of the longest side is equal to the sum of the squares of the other two sides. If the two shorter sides are a and b, and the longest side is c, then a^2 + b^2 = c^2. This works only for a right-angled triangle.",
    "newton law": "Newton's laws of motion explain how objects move. The first law says an object stays at rest or keeps moving unless a force acts on it. The second law says force equals mass into acceleration. The third law says every action has an equal and opposite reaction.",
    "force": "Force is a push or pull that can change the motion of an object. It can make something move, stop, speed up, slow down, or change direction. Force is measured in newtons.",
    "motion": "Motion means a change in the position of an object with time. It can be slow, fast, uniform, or accelerated depending on how the object moves.",
    "velocity": "Velocity is speed in a particular direction. It tells us not only how fast something is moving, but also where it is moving.",
    "acceleration": "Acceleration is the rate at which velocity changes with time. An object accelerates when it speeds up, slows down, or changes direction.",
    "gravity": "Gravity is the force that pulls objects toward the Earth or toward any massive body. It gives weight to objects and keeps planets in orbit.",
    "work": "In physics, work is done when a force moves an object through a distance. Work equals force multiplied by displacement in the direction of the force.",
    "energy": "Energy is the capacity to do work. It exists in many forms such as kinetic, potential, heat, light, and electrical energy.",
    "power": "Power is the rate at which work is done or energy is transferred. It tells us how quickly a task is completed.",
    "photosynthesis": "Photosynthesis is the process by which green plants make their own food using sunlight, carbon dioxide, and water. It produces glucose as food and oxygen as a by-product.",
    "respiration": "Respiration is the process by which living cells release energy from food. In this process, glucose breaks down to produce energy, carbon dioxide, and water.",
    "osmosis": "Osmosis is the movement of water molecules from a region of higher water concentration to a region of lower water concentration through a semipermeable membrane.",
    "diffusion": "Diffusion is the movement of particles from a region of higher concentration to a region of lower concentration until they spread evenly.",
    "cell": "A cell is the basic structural and functional unit of life. All living organisms are made of cells.",
    "tissue": "A tissue is a group of similar cells working together to perform a specific function.",
    "dna": "DNA is the genetic material that carries instructions for growth, functioning, and reproduction in living organisms.",
    "ecosystem": "An ecosystem is a system formed by living organisms and their physical environment interacting with each other.",
    "acid base": "An acid-base reaction happens when an acid and a base react with each other to form salt and water. Acids give H plus ions and bases give OH minus ions. When they combine, neutralization happens.",
    "neutralization": "Neutralization is a chemical reaction in which an acid reacts with a base to form salt and water.",
    "atom": "An atom is the smallest unit of an element that retains the properties of that element. It is made of protons, neutrons, and electrons.",
    "molecule": "A molecule is formed when two or more atoms join together chemically. It can contain atoms of the same or different elements.",
    "compound": "A compound is a substance made when two or more different elements combine chemically in a fixed ratio.",
    "mixture": "A mixture is formed when two or more substances combine physically without chemical bonding. The components can usually be separated by physical methods.",
    "oxidation": "Oxidation is a process in which a substance loses electrons, gains oxygen, or loses hydrogen.",
    "reduction": "Reduction is a process in which a substance gains electrons, loses oxygen, or gains hydrogen.",
    "triangle": "A triangle is a three-sided closed shape. It has three sides, three angles, and the sum of its angles is always 180 degrees.",
    "area": "Area is the amount of surface covered by a two-dimensional shape. It is measured in square units.",
    "perimeter": "Perimeter is the total length of the boundary of a closed figure.",
    "percentage": "Percentage means a value out of one hundred. It is used to compare quantities, discounts, marks, profit, and many daily life situations.",
    "profit loss": "Profit happens when selling price is greater than cost price, and loss happens when cost price is greater than selling price.",
    "algebra": "Algebra is the branch of mathematics in which letters and symbols are used to represent numbers and relationships.",
    "probability": "Probability tells us how likely an event is to happen. Its value lies between 0 and 1.",
    "trigonometry": "Trigonometry is the branch of mathematics that studies relationships between the sides and angles of triangles.",
    "e commerce": "E-commerce means buying and selling goods or services through the internet. Examples include online shopping websites and digital payment platforms.",
    "democracy": "Democracy is a system of government in which people choose their leaders by voting and take part in decision-making directly or indirectly.",
    "constitution": "A constitution is the supreme set of laws and principles according to which a country is governed.",
    "parliament": "Parliament is the law-making body of a country. It discusses national issues, makes laws, and checks the work of the government.",
    "blockchain": "Blockchain is a digital record system in which data is stored in blocks linked together in a secure and transparent chain. It is widely used in cryptocurrencies and secure transactions.",
    "artificial intelligence": "Artificial intelligence is the ability of a computer system to perform tasks that normally require human intelligence, such as learning, reasoning, and decision-making.",
    "machine learning": "Machine learning is a part of artificial intelligence in which computers learn patterns from data and improve their performance without being explicitly programmed for every task.",
    "cloud computing": "Cloud computing means using computing services such as storage, databases, and software over the internet instead of only on a local computer.",
    "operating system": "An operating system is system software that manages computer hardware, files, memory, and running applications. Examples are Windows, Linux, and Android.",
    "database": "A database is an organized collection of data that can be stored, managed, and accessed efficiently.",
    "algorithm": "An algorithm is a step-by-step method or procedure used to solve a problem or complete a task.",
    "python": "Python is a high-level programming language known for its simple syntax and wide use in web development, automation, data science, and artificial intelligence.",
    "loop": "A loop is a programming structure that repeats a block of code until a condition changes or a sequence ends.",
    "function": "A function is a reusable block of code that performs a specific task and can be called whenever needed.",
    "stack": "A stack is a linear data structure that follows the Last In First Out rule. The last item added is the first item removed.",
    "queue": "A queue is a linear data structure that follows the First In First Out rule. The first item added is the first item removed.",
}


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def infer_topic_from_prompt(question):
    cleaned = clean_text(question)
    cleaned = re.sub(r"^(what is|explain|define|tell me about)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" ?.:").title()


def build_record(question, answer, topic=""):
    safe_question = clean_text(question)
    safe_answer = clean_text(answer)
    safe_topic = clean_text(topic) or infer_topic_from_prompt(safe_question)
    return {
        "question": safe_question,
        "answer": safe_answer,
        "topic": safe_topic,
        "search_text": " ".join([safe_question, safe_topic, safe_answer]).lower()
    }


def parse_text_data_file():
    records = []
    if not os.path.exists(DATA_TEXT_PATH):
        return records

    with open(DATA_TEXT_PATH, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            question, answer = line.split(":", 1)
            record = build_record(question, answer)
            if record["question"] and record["answer"]:
                records.append(record)
    return records


def save_records_to_json(records):
    os.makedirs(os.path.dirname(DATA_JSON_PATH), exist_ok=True)
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def load_data():
    global questions, answers, qa_records

    records = []
    if os.path.exists(DATA_JSON_PATH):
        try:
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, list):
                for item in loaded:
                    if isinstance(item, dict):
                        record = build_record(
                            item.get("question", ""),
                            item.get("answer", ""),
                            item.get("topic", "")
                        )
                        if record["question"] and record["answer"]:
                            records.append(record)
        except Exception:
            records = []

    if not records:
        records = parse_text_data_file()
        save_records_to_json(records)

    qa_records = records
    questions = [record["question"] for record in records]
    answers = [record["answer"] for record in records]


load_data()

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform([record["search_text"] for record in qa_records] or [""])


def ensure_library_storage():
    os.makedirs(LIBRARY_DIR, exist_ok=True)
    if not os.path.exists(LIBRARY_INDEX_PATH):
        with open(LIBRARY_INDEX_PATH, "w", encoding="utf-8") as file:
            json.dump([], file)


def read_library_index():
    ensure_library_storage()
    try:
        with open(LIBRARY_INDEX_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def write_library_index(items):
    ensure_library_storage()
    with open(LIBRARY_INDEX_PATH, "w", encoding="utf-8") as file:
        json.dump(items, file, ensure_ascii=False, indent=2)


def normalize_filter(value):
    return clean_text(value).lower()


def build_library_preview_url(item_id):
    return f"/library/file/{item_id}"


def build_library_download_url(item_id):
    return f"/library/download/{item_id}"


def serialize_library_item(item):
    return {
        "id": item["id"],
        "title": item["title"],
        "board": item["board"],
        "class_level": item["class_level"],
        "subject": item["subject"],
        "material_type": item["material_type"],
        "filename": item["filename"],
        "extension": item["extension"],
        "uploaded_at": item["uploaded_at"],
        "preview_url": build_library_preview_url(item["id"]),
        "download_url": build_library_download_url(item["id"])
    }


def matches_library_filters(item, search="", subject="", board="", class_level="", material_type=""):
    haystack = " ".join([
        item.get("title", ""),
        item.get("board", ""),
        item.get("class_level", ""),
        item.get("subject", ""),
        item.get("material_type", ""),
        item.get("filename", "")
    ]).lower()

    if search and search not in haystack:
        return False
    if subject and subject != normalize_filter(item.get("subject", "")):
        return False
    if board and board != normalize_filter(item.get("board", "")):
        return False
    if class_level and class_level != normalize_filter(item.get("class_level", "")):
        return False
    if material_type and material_type != normalize_filter(item.get("material_type", "")):
        return False
    return True


def save_new_data(question, answer):
    records = []
    if os.path.exists(DATA_JSON_PATH):
        try:
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, list):
                records = loaded
        except Exception:
            records = []

    safe_question = clean_text(question)
    safe_answer = clean_text(answer)
    updated = False
    for item in records:
        if normalize_phrase(item.get("question", "")) == normalize_phrase(safe_question):
            item["question"] = safe_question
            item["answer"] = safe_answer
            item["topic"] = infer_topic_from_prompt(safe_question)
            updated = True
            break

    if not updated:
        records.append({
            "question": safe_question,
            "answer": safe_answer,
            "topic": infer_topic_from_prompt(safe_question)
        })

    save_records_to_json(records)
    with open(DATA_TEXT_PATH, "w", encoding="utf-8") as file:
        for item in records:
            file.write(f"{item['question']}: {item['answer']}\n")
    load_data()
    global vectorizer, X
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform([record["search_text"] for record in qa_records] or [""])


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", clean_text(text))
    return [part.strip(" -\t") for part in parts if len(part.strip()) > 20]


def extract_keywords(text, limit=10):
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    filtered = [word for word in words if word not in STOP_WORDS]
    return [word for word, _count in Counter(filtered).most_common(limit)]


def keyword_set(text):
    return set(extract_keywords(text, limit=12))


def dedupe_preserve(items, limit):
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
        if len(result) == limit:
            break
    return result


def normalize_phrase(text):
    lowered = clean_text(text).lower()
    lowered = re.sub(r"[^a-z0-9\s]", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def sentence_score(sentence, keywords):
    lowered = sentence.lower()
    score = sum(2 for keyword in keywords if keyword in lowered)
    score += min(len(sentence.split()) / 12, 3)
    return score


def extract_key_points(sentences, keywords, limit=4):
    if not sentences:
        return []

    ranked = sorted(sentences, key=lambda item: sentence_score(item, keywords), reverse=True)
    points = []
    seen = set()

    for sentence in ranked:
        trimmed = clean_text(sentence)
        trimmed = re.sub(r"^(for example|example|also|because|therefore|however)\s*[:, -]*", "", trimmed, flags=re.IGNORECASE)
        if len(trimmed) < 18:
            continue
        if any(fragment in trimmed.lower() for fragment in ["daily life ke kisi", "connect karke samjho", "simple language"]):
            continue

        words = trimmed.split()
        compact = " ".join(words[:12]).rstrip(",;:")

        compact = compact.rstrip(".") + "."
        key = normalize_phrase(compact)
        if key and key not in seen:
            points.append(compact)
            seen.add(key)
        if len(points) == limit:
            break

    return points


def build_notes_payload(text, title="Study Notes"):
    sentences = split_sentences(text)
    if not sentences:
        return {
            "title": title,
            "overview": "Please provide more detailed content so proper notes can be created.",
            "sections": [],
            "keywords": []
        }

    keywords = extract_keywords(text, limit=8)
    ranked = sorted(sentences, key=lambda item: sentence_score(item, keywords), reverse=True)
    overview = " ".join(ranked[:3])[:650].strip()

    sections = [
        {"heading": "Chapter Overview", "bullets": [overview or sentences[0]]},
        {"heading": "Core Concepts", "bullets": dedupe_preserve(ranked[:5], 5)},
        {
            "heading": "Important Explanations",
            "bullets": dedupe_preserve(ranked[5:10] if len(ranked) > 5 else sentences[2:8], 5)
        },
        {"heading": "Quick Revision Points", "bullets": dedupe_preserve(sentences[:4] + ranked[:3], 6)}
    ]

    return {
        "title": title,
        "overview": overview or sentences[0],
        "sections": sections,
        "keywords": keywords
    }


def shuffled(items):
    values = list(items)
    random.shuffle(values)
    return values


def determine_quiz_count(text, sentences):
    word_count = len(re.findall(r"\b\w+\b", text or ""))
    sentence_count = len(sentences)

    if word_count < 25 or sentence_count <= 1:
        return 1
    if word_count < 60 or sentence_count <= 2:
        return 2
    if word_count < 120 or sentence_count <= 4:
        return 3
    if word_count < 220 or sentence_count <= 6:
        return 4
    if word_count < 320 or sentence_count <= 8:
        return 5
    if word_count < 450 or sentence_count <= 10:
        return 6
    if word_count < 650:
        return 7
    return min(10, max(7, sentence_count // 2))


def normalize_quiz_count(requested_count, text, sentences):
    default_count = determine_quiz_count(text, sentences)
    try:
        numeric_count = int(requested_count)
    except (TypeError, ValueError):
        return default_count
    return max(1, min(100, numeric_count))


def normalize_quiz_mode(value):
    allowed = {"mixed", "mcq", "true_false", "fill_blank"}
    cleaned = clean_text(value).lower().replace("-", "_")
    return cleaned if cleaned in allowed else "mixed"


def normalize_quiz_difficulty(value):
    allowed = {"easy", "medium", "hard"}
    cleaned = clean_text(value).lower()
    return cleaned if cleaned in allowed else "medium"


def choose_answer_word(sentence, difficulty="medium"):
    words = [word for word in re.findall(r"\b[A-Za-z]{4,}\b", sentence) if word.lower() not in STOP_WORDS]
    if not words:
        return ""
    if difficulty == "easy":
        return words[0]
    if difficulty == "hard":
        return max(words, key=len)
    return words[min(1, len(words) - 1)]


def build_mcq_question(sentence, keywords, difficulty="medium"):
    answer = choose_answer_word(sentence, difficulty)
    if not answer:
        return None

    question = re.sub(rf"\b{re.escape(answer)}\b", "_____", sentence, count=1, flags=re.IGNORECASE)
    distractors = dedupe_preserve([word for word in keywords if word.lower() != answer.lower()], 3)
    while len(distractors) < 3:
        distractors.append(f"option{len(distractors) + 1}")

    return {
        "question": question,
        "answer": answer,
        "options": shuffled([answer] + distractors[:3]),
        "type": "MCQ",
        "difficulty": difficulty.title()
    }


def build_true_false_question(sentence, keywords, difficulty="medium"):
    trimmed = clean_text(sentence)
    if not trimmed:
        return None

    words = [word for word in re.findall(r"\b[A-Za-z]{4,}\b", trimmed) if word.lower() not in STOP_WORDS]
    if not words:
        return None

    statement = trimmed
    correct_answer = "True"

    if difficulty != "easy" and keywords:
        answer_word = words[0]
        replacement = next((word for word in keywords if word.lower() != answer_word.lower()), "")
        if replacement:
            statement = re.sub(rf"\b{re.escape(answer_word)}\b", replacement, statement, count=1, flags=re.IGNORECASE)
            correct_answer = "False"

    return {
        "question": statement,
        "answer": correct_answer,
        "options": ["True", "False"],
        "type": "True/False",
        "difficulty": difficulty.title()
    }


def build_fill_blank_question(sentence, keywords, difficulty="medium"):
    answer = choose_answer_word(sentence, difficulty)
    if not answer:
        return None

    question = re.sub(rf"\b{re.escape(answer)}\b", "_____", sentence, count=1, flags=re.IGNORECASE)
    distractors = dedupe_preserve([word for word in keywords if word.lower() != answer.lower()], 3)
    while len(distractors) < 3:
        distractors.append(f"option{len(distractors) + 1}")

    return {
        "question": f"Fill in the blank: {question}",
        "answer": answer,
        "options": shuffled([answer] + distractors[:3]),
        "type": "Fill Blanks",
        "difficulty": difficulty.title()
    }


def build_quiz_item(sentence, keywords, mode="mixed", difficulty="medium", index=0):
    mode_cycle = ["mcq", "true_false", "fill_blank"]
    effective_mode = mode_cycle[index % len(mode_cycle)] if mode == "mixed" else mode

    if effective_mode == "true_false":
        return build_true_false_question(sentence, keywords, difficulty)
    if effective_mode == "fill_blank":
        return build_fill_blank_question(sentence, keywords, difficulty)
    return build_mcq_question(sentence, keywords, difficulty)


def build_quiz_payload(text, title="Practice Quiz", requested_count=None, quiz_mode="mixed", difficulty="medium"):
    sentences = split_sentences(text)
    keywords = extract_keywords(text, limit=12)
    target_count = normalize_quiz_count(requested_count, text, sentences)
    quiz_mode = normalize_quiz_mode(quiz_mode)
    difficulty = normalize_quiz_difficulty(difficulty)
    quiz_items = []

    ranked_sentences = sentences
    if difficulty == "easy":
        ranked_sentences = sorted(sentences, key=lambda item: len(item))
    elif difficulty == "hard":
        ranked_sentences = sorted(sentences, key=lambda item: len(item), reverse=True)

    for index, sentence in enumerate(ranked_sentences):
        quiz_item = build_quiz_item(sentence, keywords, quiz_mode, difficulty, index=index)
        if not quiz_item:
            continue
        quiz_items.append(quiz_item)
        if len(quiz_items) >= target_count:
            break

    if len(quiz_items) < target_count:
        fallback_keywords = keywords[:max(4, target_count)] or ["topic", "concept", "example", "summary"]
        question_templates = [
            "Which keyword is most closely related to this study material?",
            "What should be revised first from this content?",
            "Which term appears as a major idea in the material?",
            "Which word best matches the main topic of these notes?",
            "Which idea should a student remember from this material?",
            "Which term is most likely part of the main explanation?",
            "Which keyword fits the chapter summary best?",
            "Which concept is highlighted by these notes?",
            "Which word belongs to the important revision list?",
            "Which option matches a major study point from this material?"
        ]

        template_index = 0
        while len(quiz_items) < target_count:
            answer = fallback_keywords[template_index % len(fallback_keywords)]
            question = f"{question_templates[template_index % len(question_templates)]} ({template_index + 1})"
            if any(item["question"] == question for item in quiz_items):
                template_index += 1
                continue
            distractors = [word for word in fallback_keywords if word != answer]
            while len(distractors) < 3:
                distractors.append(f"option{len(distractors) + 1}")
            quiz_items.append({
                "question": question,
                "answer": answer,
                "options": shuffled([answer] + distractors[:3]),
                "type": "MCQ",
                "difficulty": difficulty.title()
            })
            template_index += 1

    return {
        "title": title,
        "items": quiz_items[:target_count],
        "count": len(quiz_items[:target_count]),
        "requested_count": target_count,
        "mode": quiz_mode,
        "difficulty": difficulty
    }


def extract_video_id(link):
    parsed = urlparse(link)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        return parsed.path.strip("/").split("/")[0]

    if "youtube.com" in host:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]
        if parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
            return parsed.path.strip("/").split("/")[1]

    return ""


def fetch_youtube_page(video_id):
    response = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=REQUEST_HEADERS, timeout=12)
    response.raise_for_status()
    return response.text


def fetch_youtube_oembed(link):
    response = requests.get(
        "https://www.youtube.com/oembed",
        params={"url": link, "format": "json"},
        headers=REQUEST_HEADERS,
        timeout=10
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "title": clean_text(payload.get("title", "")),
        "description": "",
        "channel": clean_text(payload.get("author_name", ""))
    }


def fetch_youtube_data_api_metadata(video_id):
    youtube_api_key = get_youtube_data_api_settings()
    if not youtube_api_key:
        raise RuntimeError("YOUTUBE_API_KEY is not set.")

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "id": video_id,
            "part": "snippet",
            "key": youtube_api_key
        },
        headers=REQUEST_HEADERS,
        timeout=12
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])
    if not items:
        raise ValueError("Video details not found from YouTube Data API.")

    snippet = items[0].get("snippet", {})
    return {
        "title": clean_text(snippet.get("title", "")) or f"YouTube Video {video_id}",
        "description": clean_text(snippet.get("description", "")),
        "channel": clean_text(snippet.get("channelTitle", ""))
    }


def fetch_youtube_metadata(page_html):
    soup = BeautifulSoup(page_html, "html.parser")

    title = ""
    title_meta = soup.find("meta", attrs={"property": "og:title"})
    if title_meta and title_meta.get("content"):
        title = title_meta["content"].strip()
    elif soup.title and soup.title.text:
        title = soup.title.text.replace("- YouTube", "").strip()

    description = ""
    description_tag = soup.find("meta", attrs={"property": "og:description"})
    if description_tag and description_tag.get("content"):
        description = description_tag["content"]
    else:
        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and description_tag.get("content"):
            description = description_tag["content"]

    channel = ""
    channel_tag = soup.find("link", attrs={"itemprop": "name"})
    if channel_tag and channel_tag.get("content"):
        channel = channel_tag["content"]
    else:
        channel_meta = soup.find("meta", attrs={"itemprop": "author"})
        if channel_meta and channel_meta.get("content"):
            channel = channel_meta["content"]

    return {"title": title or "YouTube Study Session", "description": clean_text(description), "channel": channel}


def extract_caption_base_url(page_html):
    patterns = [
        r'"captionTracks":\[(.*?)\]',
        r'"playerCaptionsTracklistRenderer":\{"captionTracks":\[(.*?)\]'
    ]

    for pattern in patterns:
        match = re.search(pattern, page_html)
        if not match:
            continue

        track_blob = match.group(1)
        base_url_match = re.search(r'"baseUrl":"(.*?)"', track_blob)
        if base_url_match:
            base_url = base_url_match.group(1)
            return html.unescape(unquote(base_url.replace("\\u0026", "&").replace("\\/", "/")))

    return ""


def fetch_transcript_text(video_id):
    page_html = fetch_youtube_page(video_id)
    caption_url = extract_caption_base_url(page_html)
    if not caption_url:
        return "", page_html

    if "fmt=json3" not in caption_url:
        separator = "&" if "?" in caption_url else "?"
        caption_url = f"{caption_url}{separator}fmt=json3"

    response = requests.get(caption_url, headers=REQUEST_HEADERS, timeout=12)
    response.raise_for_status()
    payload = response.json()

    transcript_parts = []
    for event in payload.get("events", []):
        for segment in event.get("segs", []):
            text = segment.get("utf8", "").replace("\n", " ").strip()
            if text:
                transcript_parts.append(text)

    return clean_text(" ".join(transcript_parts)), page_html


def fetch_youtube_context(link):
    video_id = extract_video_id(link)
    if not video_id:
        raise ValueError("Invalid YouTube link.")

    transcript_text = ""
    metadata = {"title": "YouTube Study Session", "description": "", "channel": ""}

    try:
        transcript_text, page_html = fetch_transcript_text(video_id)
        metadata = fetch_youtube_metadata(page_html)
    except Exception:
        metadata = fetch_youtube_oembed(link)

    source_text = transcript_text or clean_text(f"{metadata['title']}. {metadata['description']}. Channel {metadata['channel']}")

    metadata["video_id"] = video_id
    metadata["text"] = source_text
    metadata["used_transcript"] = bool(transcript_text)
    return metadata


def build_fallback_video_context(link):
    video_id = extract_video_id(link)
    title = f"YouTube Video {video_id}" if video_id else "YouTube Study Session"
    channel = ""
    try:
        oembed_data = fetch_youtube_oembed(link)
        title = oembed_data.get("title") or title
        channel = oembed_data.get("channel", "")
    except Exception:
        pass

    topic_hint = extract_topic_from_question(title) or "the main topic"
    topic_label = topic_hint.title() if topic_hint else "Main Topic"
    fallback_text = clean_text(
        f"{title}. This study video appears to be about {topic_label}. "
        "Focus on the definition, key ideas, process, examples, and short revision points."
    )

    return {
        "title": title,
        "description": "Transcript could not be fetched, so notes were created from the available video title and topic hint.",
        "channel": channel,
        "video_id": video_id,
        "text": fallback_text,
        "used_transcript": False,
        "used_fallback": True
    }


def build_video_notes_payload(video_context):
    source_text = clean_text(video_context.get("text", ""))
    title = video_context.get("title", "YouTube Study Notes")
    description = clean_text(video_context.get("description", ""))
    try:
        llm_summary = summarize_with_gemini_v2(source_text)
        summary_lines = [clean_text(line.lstrip("-•* ")) for line in llm_summary.splitlines() if clean_text(line)]
        title_line = next((line.replace("Title:", "").strip() for line in summary_lines if line.lower().startswith("title:")), title)
        highlight_lines = [
            line for line in summary_lines
            if not line.lower().startswith("title:") and "key highlights" not in line.lower()
        ]
        highlight_lines = highlight_lines[:8] or [
            "Main topic explained clearly",
            "Important concepts highlighted",
            "Quick revision points prepared"
        ]
        return {
            "title": title_line or title,
            "overview": highlight_lines[0],
            "sections": [
                {"heading": "Key Highlights", "bullets": highlight_lines[:4]},
                {"heading": "Quick Revision", "bullets": highlight_lines[4:8] or highlight_lines[:3]}
            ],
            "keywords": extract_keywords(" ".join(highlight_lines), limit=6)
        }
    except Exception:
        pass

    if not video_context.get("used_fallback"):
        return build_notes_payload(source_text, title=title)

    base_text = clean_text(f"{title}. {description}")
    keywords = extract_keywords(base_text, limit=6)
    topic = extract_topic_from_question(title).title() or title
    quick_points = [
        f"Topic: {topic}",
        "Definition or basic meaning",
        "Main process or working steps",
        "Important example or use case",
        "Quick revision summary"
    ]

    return {
        "title": title,
        "overview": f"This video is being summarized from its title and topic hint. Study {topic} by focusing on meaning, important ideas, steps, examples, and exam revision points.",
        "sections": [
            {
                "heading": "Chapter Overview",
                "bullets": [
                    f"The video mainly appears to discuss {topic}.",
                    "Start with the simple meaning of the topic and then move to the key explanation."
                ]
            },
            {
                "heading": "Core Concepts",
                "bullets": [
                    f"Understand what {topic} means in simple words.",
                    "Identify the main ideas, rules, or principles related to the topic.",
                    "Notice any process, stages, or structure explained in the video."
                ]
            },
            {
                "heading": "Important Explanations",
                "bullets": [
                    "Write one short definition.",
                    "Add one example or real-life use.",
                    "Revise any formula, rule, or conclusion linked to the topic."
                ]
            },
            {
                "heading": "Quick Revision Points",
                "bullets": quick_points
            }
        ],
        "keywords": keywords or ["topic", "definition", "concept", "example", "summary"]
    }


def fetch_transcript_with_api(video_id):
    if YouTubeTranscriptApi is None:
        raise RuntimeError("youtube-transcript-api is not installed on this system.")

    transcript_items = YouTubeTranscriptApi.get_transcript(video_id)
    transcript_text = clean_text(" ".join(item.get("text", "") for item in transcript_items))
    if not transcript_text:
        raise ValueError("Transcript not available for this video.")
    return transcript_text


def summarize_with_gemini(transcript_text):
    gemini_api_key, gemini_model = get_gemini_settings()
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    prompt = (
        "You are a professional YouTube video summarizer.\n\n"
        "Summarize the given transcript in a clean and structured format like YouTube highlights.\n\n"
        "Rules:\n\n"
        "- Give a Title\n"
        "- Add section: Key Highlights\n"
        "- Use bullet points (5–8 points)\n"
        "- Keep language simple and student-friendly\n"
        "- Avoid long paragraphs\n"
        "- Focus only on important concepts\n\n"
        f"Transcript:\n{transcript_text[:18000]}"
    )

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        },
        timeout=45
    )
    response.raise_for_status()
    payload = response.json()

    candidates = payload.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini did not return any summary.")

    parts = candidates[0].get("content", {}).get("parts", [])
    summary_text = "\n".join(
        part.get("text", "").strip()
        for part in parts
        if part.get("text", "").strip()
    )
    if not summary_text:
        raise RuntimeError("Gemini returned an empty summary.")
    return summary_text.strip()


def extract_pdf_text(file_storage):
    if PdfReader is None:
        raise RuntimeError("PDF support library is not installed on this system.")

    reader = PdfReader(BytesIO(file_storage.read()))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return clean_text(" ".join(pages))


def extract_pdf_text_with_layout(file_storage):
    if PdfReader is None:
        raise RuntimeError("PDF support library is not installed on this system.")

    reader = PdfReader(BytesIO(file_storage.read()))
    pages = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            pages.append(page_text.strip())

    combined = "\n\n".join(pages)
    combined = combined.replace("\r\n", "\n")
    combined = re.sub(r"[ \t]+", " ", combined)
    combined = re.sub(r"\n{3,}", "\n\n", combined)
    return combined.strip()


def extract_text_from_uploaded_study_file(file_storage):
    filename = (file_storage.filename or "").lower()
    if filename.endswith(".pdf"):
        return extract_pdf_text_with_layout(file_storage)
    if filename.endswith(".txt"):
        text = file_storage.read().decode("utf-8", errors="ignore")
        text = text.replace("\r\n", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    raise RuntimeError("Only PDF and TXT files are supported.")


def expand_answer_for_chat(question, answer_source):
    sentences = split_sentences(answer_source) or [clean_text(answer_source)]
    core = " ".join(sentences[:3]).strip()
    if not core:
        return clean_text(answer_source)

    topic = extract_topic_from_question(question).title() or "This topic"
    subject = detect_subject(question)
    example = build_real_life_example(question, answer_source).replace("Real-life example:", "").strip()

    if subject == "math":
        add_on = f" In simple terms, {topic} is understood by identifying the given information, choosing the right formula, and applying it carefully."
    elif subject == "python":
        add_on = f" In programming terms, {topic} should be understood by looking at its purpose, syntax, and output."
    elif subject == "physics":
        add_on = f" In physics, {topic} becomes clearer when we connect it to motion, force, energy, or daily-life observation."
    elif subject == "chemistry":
        add_on = f" In chemistry, {topic} is easier to understand when we relate it to substances, reactions, and observable changes."
    else:
        add_on = f" In simple language, {topic} can be understood by focusing on its meaning, main idea, and why it is important."

    if example:
        add_on += f" {example}"

    return clean_text(f"{core} {add_on}")


def build_youtube_summary_fallback_v2(metadata):
    title = clean_text(metadata.get("title", "")) or "YouTube Video Summary"
    description = clean_text(metadata.get("description", ""))
    channel = clean_text(metadata.get("channel", ""))
    topic = extract_topic_from_question(title).title() or title

    bullets = [
        f"- Main topic: {topic}",
        "- Focus on the basic definition and main idea.",
        "- Note the important concepts, steps, or rules from the video.",
        "- Keep one example or application for revision.",
        "- Write short points that are easy to study later."
    ]
    if channel:
        bullets.insert(1, f"- Channel: {channel}")
    if description:
        bullets.insert(2, f"- Video focus: {description[:140]}")

    return f"Title: {title}\n\nKey Highlights:\n" + "\n".join(bullets[:8])


def summarize_with_gemini_v2(source_text):
    prompt = (
        "You are a professional summarizer.\n"
        "Create structured notes:\n\n"
        "- Title\n"
        "- Key Highlights (bullet points)\n"
        "- Keep simple and clean\n"
        "- Focus only on important concepts\n\n"
        f"Transcript:\n{source_text[:18000]}"
    )
    summary_text = call_gemini_text(prompt, timeout=45)
    if not summary_text:
        raise RuntimeError("Gemini returned an empty summary.")
    return summary_text.strip()


def build_youtube_mindmap_fallback(metadata):
    title = clean_text(metadata.get("title", "")) or "YouTube Video"
    topic = extract_topic_from_question(title).title() or title
    description = clean_text(metadata.get("description", ""))

    lines = [
        f"# {title}",
        "",
        "## Overview",
        f"- Main idea: {topic}",
        "- Focus on the definition and key concept",
        "## Important Concepts",
        "- Main rules, process, or explanation",
        "- Key example or application",
        "## Quick Revision",
        "- Write short points for exam revision"
    ]
    if description:
        lines.insert(4, f"- Video hint: {description[:140]}")
    return "\n".join(lines)


def generate_mindmap_with_gemini(source_text):
    prompt = (
        "You are an expert teacher.\n\n"
        "Convert the content into a Markdown mind map.\n\n"
        "Rules:\n"
        "- Use # for main topic\n"
        "- Use ## for subtopics\n"
        "- Use - for points\n"
        "- Keep structure clean\n"
        "- Do not write long paragraphs\n\n"
        "Example format:\n"
        "# AI/ML Course\n\n"
        "## Basics\n"
        "- Python\n"
        "- SQL\n\n"
        "## Advanced\n"
        "- Machine Learning\n"
        "- Deep Learning\n\n"
        f"Content:\n{source_text[:18000]}"
    )
    mindmap_text = call_gemini_text(prompt, timeout=45)
    if not mindmap_text:
        raise RuntimeError("Gemini returned an empty mind map.")
    return mindmap_text.strip()


def build_mindmap_fallback(source_text):
    topic = extract_topic_from_question(source_text).title() or clean_text(source_text[:80]) or "Study Topic"
    keywords = extract_keywords(source_text, limit=10)
    branches = dedupe_preserve([word.title() for word in keywords if word.lower() not in topic.lower()], 6)
    if not branches:
        branches = ["Definition", "Key Ideas", "Examples", "Applications"]

    lines = [f"# {topic}"]
    for branch in branches[:6]:
        lines.append(f"## {branch}")
        lines.append(f"- Important point about {branch.lower()}")
        lines.append(f"- Relation of {branch.lower()} with {topic.lower()}")
    return "\n".join(lines).strip()


def fetch_youtube_summary_source_v2(url, video_id):
    transcript_text = ""
    metadata = {"title": f"YouTube Video {video_id}", "description": "", "channel": ""}

    try:
        transcript_text = fetch_transcript_with_api(video_id)
    except Exception:
        transcript_text = ""

    try:
        metadata = fetch_youtube_data_api_metadata(video_id)
    except Exception:
        try:
            page_html = fetch_youtube_page(video_id)
            metadata = fetch_youtube_metadata(page_html)
        except Exception:
            try:
                metadata = fetch_youtube_oembed(url)
            except Exception:
                pass

    source_text = transcript_text or clean_text(
        f"{metadata.get('title', '')}. {metadata.get('description', '')}. Channel {metadata.get('channel', '')}"
    )
    if not source_text:
        source_text = clean_text(f"{metadata.get('title', '')}. {metadata.get('channel', '')}") or f"YouTube video {video_id}"

    return {
        "video_id": video_id,
        "transcript_text": transcript_text,
        "source_text": source_text,
        "metadata": metadata,
        "used_transcript": bool(transcript_text)
    }


def extract_topic_from_question(user_input):
    cleaned = re.sub(r"[^\w\s-]", " ", user_input.lower())
    cleaned = re.sub(r"\b(what|is|are|how|why|explain|define|tell|me|about|the|a|an)\b", " ", cleaned)
    cleaned = clean_text(cleaned)
    return cleaned or user_input


def extract_equation_text(user_input):
    match = re.search(r"([0-9a-zA-Z+\-*/().\s]*=[0-9a-zA-Z+\-*/().\s]*)", user_input)
    if not match:
        return ""
    equation = clean_text(match.group(1))
    equation = re.sub(r"\b(solve|this|question|please|find|calculate)\b", "", equation, flags=re.IGNORECASE)
    return clean_text(equation)


def parse_linear_side(side_text):
    text = side_text.replace(" ", "")
    if not text:
        return {}, 0.0
    if text[0] not in "+-":
        text = "+" + text

    terms = re.findall(r"[+-][^+-]+", text)
    coeffs = {}
    constant = 0.0

    for term in terms:
        if re.search(r"[a-zA-Z]", term):
            match = re.fullmatch(r"([+-])(\d*(?:\.\d+)?)?([a-zA-Z]+)", term)
            if not match:
                return None, None
            sign, number_text, variable = match.groups()
            magnitude = float(number_text) if number_text not in ("", None) else 1.0
            value = magnitude if sign == "+" else -magnitude
            coeffs[variable] = coeffs.get(variable, 0.0) + value
        else:
            try:
                constant += float(term)
            except ValueError:
                return None, None

    return coeffs, constant


def solve_detected_equation(user_input):
    equation = extract_equation_text(user_input)
    if "=" not in equation:
        return None

    left_text, right_text = equation.split("=", 1)
    left_coeffs, left_const = parse_linear_side(left_text)
    right_coeffs, right_const = parse_linear_side(right_text)

    if left_coeffs is None or right_coeffs is None:
        return None

    variables = sorted(set(left_coeffs) | set(right_coeffs))
    combined_coeffs = {var: left_coeffs.get(var, 0.0) - right_coeffs.get(var, 0.0) for var in variables}
    rhs_value = right_const - left_const

    if not variables:
        verdict = "This is not a variable equation."
        return {
            "mode": "blackboard",
            "title": equation,
            "steps": lines_to_voice_steps([
                "Let's solve this step by step ✍️",
                "Step 1: Understand / Given",
                f"→ Equation: {equation}",
                "Step 2: Check both sides",
                f"→ Left and right are just numbers",
                "Step 3: Final Answer",
                f"→ {verdict}"
            ]),
            "final_answer": verdict,
            "notes": ["No variable is present, so this is not a solvable algebraic equation."],
            "quiz": []
        }

    if len(variables) > 1:
        reduced = " + ".join(
            [f"{combined_coeffs[var]:g}{var}" for var in variables if abs(combined_coeffs[var]) > 1e-9]
        ) or "0"
        final_answer = "One equation with multiple variables does not give a unique answer."
        return {
            "mode": "blackboard",
            "title": equation,
            "steps": lines_to_voice_steps([
                "Let's solve this step by step ✍️",
                "Step 1: Understand / Given",
                f"→ Equation: {equation}",
                f"→ Variables: {', '.join(variables)}",
                "Step 2: Rearrange",
                f"→ {reduced} = {rhs_value:g}",
                "Step 3: Check unknowns",
                f"→ Unknowns = {len(variables)}",
                "Step 4: Reason",
                "→ We need the same number of independent equations as variables",
                "Step 5: Final Answer",
                "→ No unique solution from one equation"
            ]),
            "final_answer": final_answer,
            "notes": [
                f"There are {len(variables)} variables but only 1 equation.",
                "You need one more independent equation to find exact values.",
                "Example: if x = 1, then y = 2 for 2x + 2y = 6."
            ],
            "quiz": []
        }

    variable = variables[0]
    coefficient = combined_coeffs.get(variable, 0.0)
    if abs(coefficient) < 1e-9:
        final_answer = "No unique solution exists."
        return {
            "mode": "blackboard",
            "title": equation,
            "steps": lines_to_voice_steps([
                "Let's solve this step by step ✍️",
                "Step 1: Understand / Given",
                f"→ Equation: {equation}",
                "Step 2: Rearrange",
                f"→ 0{variable} = {rhs_value:g}",
                "Step 3: Final Answer",
                f"→ {final_answer}"
            ]),
            "final_answer": final_answer,
            "notes": ["Coefficient of the variable becomes zero after rearranging."],
            "quiz": []
        }

    solution = rhs_value / coefficient
    final_answer = f"{variable} = {solution:g}"
    rearranged = f"{coefficient:g}{variable} = {rhs_value:g}"
    return {
        "mode": "blackboard",
        "title": equation,
        "steps": lines_to_voice_steps([
            "Let's solve this step by step ✍️",
            "Step 1: Understand / Given",
            f"→ Equation: {equation}",
            f"→ Variable: {variable}",
            "Step 2: Move constants and like terms",
            f"→ {rearranged}",
            "Step 3: Divide both sides",
            f"→ {variable} = {rhs_value:g} / {coefficient:g}",
            "Step 4: Solve step-by-step",
            f"→ {variable} = {solution:g}",
            "Step 5: Final Answer",
            f"→ {final_answer}"
        ]),
        "final_answer": final_answer,
        "notes": [
            "Bring variable terms to one side.",
            "Bring constants to the other side.",
            f"Divide by the coefficient of {variable}."
        ],
        "quiz": []
    }


def classify_question(user_input):
    lowered = user_input.lower()
    if "quiz" in lowered:
        return "quiz"
    if "notes" in lowered:
        return "notes"
    if any(token in lowered for token in ["animation", "draw", "json steps"]):
        return "animation"
    if lowered.startswith("why"):
        return "why"
    if lowered.startswith("how"):
        return "how"
    if lowered.startswith("what"):
        return "what"
    if "difference" in lowered or "differentiate" in lowered:
        return "difference"
    if "example" in lowered or "real life" in lowered:
        return "example"
    if any(token in lowered for token in ["solve", "equation", "calculate", "reaction", "code", "program", "derive"]):
        return "problem"
    return "general"


def detect_output_mode(user_input):
    lowered = user_input.lower()
    if "quiz" in lowered:
        return "quiz"
    if "notes" in lowered:
        return "notes"
    if any(token in lowered for token in ["animation", "draw", "json steps"]):
        return "animation"
    if any(token in lowered for token in ["solve", "calculate", "find", "equation", "reaction", "numerical"]):
        return "blackboard"
    return "concept"


def is_numerical_query(user_input):
    lowered = user_input.lower()
    if any(token in lowered for token in ["solve", "calculate", "equation", "profit", "loss", "percentage", "speed", "velocity"]):
        return True
    return bool(re.search(r"\d", lowered))


def detect_subject(user_input):
    lowered = user_input.lower()
    if any(token in lowered for token in ["python", "code", "program", "function", "loop", "list"]):
        return "python"
    if any(token in lowered for token in ["computer science", "cs"]):
        return "cs"
    if any(token in lowered for token in ["information technology", "it subject", "it "]):
        return "it"
    if any(token in lowered for token in [
        "math", "equation", "percentage", "profit", "loss", "algebra", "calculate",
        "triangle", "theorem", "geometry", "trigonometry", "pythagoras", "area", "perimeter"
    ]):
        return "math"
    if any(token in lowered for token in ["physics", "force", "motion", "speed", "velocity", "acceleration"]):
        return "physics"
    if any(token in lowered for token in ["chemistry", "reaction", "acid", "base", "molecule", "compound"]):
        return "chemistry"
    return "general"


def normalize_subject_name(value):
    lowered = clean_text(value).lower()
    aliases = {
        "math": "maths",
        "maths": "maths",
        "mathematics": "maths",
        "cs": "cs",
        "computer science": "cs",
        "python": "cs",
        "it": "it",
        "information technology": "it",
        "physics": "physics",
        "chemistry": "chemistry",
        "biology": "biology"
    }
    return aliases.get(lowered, lowered)


def detect_class_level(user_input):
    lowered = user_input.lower()
    match = re.search(r"\bclass\s*(1[0-2]|[1-9])\b", lowered)
    if match:
        return f"class {match.group(1)}"
    match = re.search(r"\b(1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th)\b", lowered)
    if match:
        digits = re.match(r"\d+", match.group(1))
        if digits:
            return f"class {digits.group(0)}"
    return ""


def get_builtin_topic_explanation(user_input):
    lowered = user_input.lower()
    for topic_key, explanation in BUILTIN_TOPIC_KNOWLEDGE.items():
        if topic_key in lowered:
            return explanation
    return ""


def build_definition_fallback(user_input):
    topic = extract_topic_from_question(user_input).strip()
    if not topic:
        return ""

    topic_title = topic.title()
    subject = detect_subject(user_input)

    if subject == "math":
        return (
            f"{topic_title} is a mathematics topic. It is understood by identifying the given values, "
            "choosing the correct formula or theorem, and then applying it step by step."
        )
    if subject == "physics":
        return (
            f"{topic_title} is a physics concept. It explains how quantities such as force, motion, "
            "energy, or speed behave in the real world."
        )
    if subject == "chemistry":
        return (
            f"{topic_title} is a chemistry topic. It is related to substances, reactions, formulas, "
            "and the changes that happen during chemical processes."
        )
    if subject == "python":
        return (
            f"{topic_title} is a programming topic. It can be understood by looking at its purpose, "
            "syntax, logic, and output."
        )

    return (
        f"{topic_title} is a topic that can be understood by first knowing its meaning, then its main features, "
        "importance, and one simple real-life example."
    )


def build_subject_fallback(topic, subject):
    safe_topic = topic.title() or "This Topic"
    if subject == "math":
        return (
            f"{safe_topic} is a math topic. To understand it, first identify the given values, then choose the "
            "correct formula or theorem, apply it carefully, and check the final answer."
        )
    if subject == "physics":
        return (
            f"{safe_topic} is a physics concept. Physics explains how quantities like force, motion, speed, energy, "
            "or acceleration behave in real life."
        )
    if subject == "chemistry":
        return (
            f"{safe_topic} is a chemistry topic. In chemistry, we study substances, reactions, changes, formulas, "
            "and how compounds behave."
        )
    if subject == "python":
        return (
            f"{safe_topic} is a coding topic. To understand it, break it into input, logic, process, and output."
        )
    return ""


def build_generic_topic_explanation(user_input):
    topic = extract_topic_from_question(user_input)
    subject = detect_subject(user_input)
    keywords = extract_keywords(topic, limit=3)
    primary = keywords[0].title() if keywords else (topic.title() or "This Topic")
    secondary = keywords[1].title() if len(keywords) > 1 else "Main Idea"

    if subject == "math":
        return (
            f"{primary} is a math concept. In maths, we first understand what is given, then choose the correct "
            f"formula, connect it with {secondary}, apply the steps carefully, and finally verify the answer."
        )
    if subject == "physics":
        return (
            f"{primary} is a physics concept. In physics, we understand what quantity is changing, what force or law "
            f"is involved, how motion or energy behaves, and then connect it with a real-life example."
        )
    if subject == "chemistry":
        return (
            f"{primary} is a chemistry topic. In chemistry, we study substances, reactions, changes, formulas, "
            f"and how one substance changes into another under specific conditions."
        )
    if subject == "python":
        return (
            f"{primary} is a programming topic. To understand it clearly, break it into input, logic, processing, "
            f"and output, then check how each line or step affects the result."
        )

    return (
        f"{primary} is an important concept. To understand it clearly, first know its meaning, then identify its main idea, "
        f"see how it works, connect it with {secondary}, and finally relate it to a real-life example."
    )


def build_handwritten_steps(question, answer_source):
    subject = detect_subject(question)
    topic = extract_topic_from_question(question)
    keywords = extract_keywords(f"{question} {answer_source}", limit=4)

    if subject == "math":
        return [
            f"Step 1: Question ko dhyan se read karo aur identify karo ki {topic} me kya nikalna hai.",
            "Step 2: Given values ya known information ko alag likho.",
            "Step 3: Formula ya basic rule apply karo.",
            "Step 4: Calculation ko line by line karo, shortcut mat lo.",
            "Step 5: Final answer ko simple language me verify karo."
        ]
    if subject == "python":
        return [
            f"Step 1: Samjho code ka goal kya hai, yani {topic} se kya problem solve ho rahi hai.",
            "Step 2: Input, process, aur output ko board par alag likho.",
            "Step 3: Har line ka role samjho, variable kis value ko hold kar raha hai dekho.",
            "Step 4: Dry run karo, yani line by line execution imagine karo.",
            "Step 5: End me output check karo aur real example se match karo."
        ]
    if subject == "physics":
        return [
            f"Step 1: Situation imagine karo, jaise bike, cricket ball, ya moving object me {topic} ka use.",
            "Step 2: Known quantity aur unknown quantity ko note karo.",
            "Step 3: Physics law ya formula choose karo.",
            "Step 4: Units ke saath substitution karo.",
            "Step 5: Final result ko daily life motion ke example se verify karo."
        ]
    if subject == "chemistry":
        return [
            f"Step 1: Reactants aur products ko clearly alag likho for {topic}.",
            "Step 2: Dekho reaction kis type ki hai, jaise combination, displacement, acid-base.",
            "Step 3: Equation ko balance karo step by step.",
            "Step 4: Observe karo kis substance ka color, gas, ya precipitate ban raha hai.",
            "Step 5: End me reaction ko daily lab ya household example se connect karo."
        ]

    focus = keywords[0] if keywords else (topic or "topic")
    support = keywords[1] if len(keywords) > 1 else "main idea"
    return [
        f"Step 1: Sabse pehle {focus} ka basic meaning simple words me likho.",
        f"Step 2: Ab dekho {support} is concept ke andar kya role play karta hai.",
        "Step 3: Teacher ki tarah isko cause, process, aur result me tod kar samjho.",
        "Step 4: Ek chhota real-life example ya daily use case se isko connect karo.",
        "Step 5: End me 2 ya 3 revision points likh kar concept ko recall karo."
    ]


def build_real_life_example(question, answer):
    source = f"{question} {answer}".lower()
    if "python" in source or "programming" in source or "code" in source:
        return "Real-life example: Python ko calculator banana, marks sheet process karna, ya simple automation script likhne se samjho."
    if "physics" in source or "force" in source or "motion" in source:
        return "Real-life example: physics ko bike chalane, cricket me ball spin hone, aur brakes lagane se samjho."
    if "math" in source or "percentage" in source or "profit" in source:
        return "Real-life example: math ko shopping discount, pocket money, EMI, aur daily budget planning se samjho."
    if "e-commerce" in source or "commerce" in source or "online shopping" in source:
        return "Real-life example: Amazon, Flipkart, Myntra, ya food delivery apps e-commerce ke real-life examples hain."
    if "computer" in source or "stack" in source or "queue" in source:
        return "Real-life example: browser back button stack jaisa kaam karta hai, aur ticket counter line queue jaisi hoti hai."

    topic = extract_keywords(f"{question} {answer}", limit=1)
    subject = topic[0] if topic else "this concept"
    return f"Real-life example: {subject} ko kisi simple daily life example ke saath relate karke samjho."


def build_diagram_payload(question):
    lowered = question.lower()
    if "pythagoras" in lowered or "pythagorean" in lowered:
        return {
            "type": "triangle",
            "title": "Pythagoras Triangle",
            "labels": {
                "a": "a side",
                "b": "b side",
                "c": "c side (hypotenuse)"
            }
        }
    if "force" in lowered or "motion" in lowered:
        return {
            "type": "force",
            "title": "Force Diagram",
            "labels": {
                "object": "Object",
                "force": "Force →",
                "motion": "Motion"
            }
        }
    if ("acid" in lowered and "base" in lowered) or "reaction" in lowered:
        return {
            "type": "reaction",
            "title": "Reaction Flow",
            "labels": {
                "left": "Acid",
                "middle": "Reaction",
                "right": "Salt + Water"
            }
        }
    return None


def build_formula_sheet_response(user_input):
    lowered = user_input.lower()
    class_level = detect_class_level(user_input) or "class 1 to 12"

    if "trigonometry" in lowered or "trigonometric" in lowered:
        answer = (
            f"Trigonometric formula sheet for {class_level}:\n"
            "sin^2A + cos^2A = 1\n"
            "1 + tan^2A = sec^2A\n"
            "1 + cot^2A = cosec^2A\n"
            "sin A / cos A = tan A\n"
            "cos A / sin A = cot A\n"
            "1 / cos A = sec A\n"
            "1 / sin A = cosec A\n\n"
            "These formulas are used to convert one trigonometric ratio into another and to solve trigonometry questions quickly."
        )
        return build_structured_response(user_input, answer)

    if ("math" in lowered or "maths" in lowered or "mathematics" in lowered) and "formula" in lowered:
        answer = (
            f"Important maths formula sheet for {class_level}:\n"
            "Area of rectangle = length × breadth\n"
            "Perimeter of rectangle = 2(l + b)\n"
            "Area of square = side × side\n"
            "Perimeter of square = 4 × side\n"
            "Area of triangle = 1/2 × base × height\n"
            "Simple Interest = (P × R × T) / 100\n"
            "Percentage = (Part / Total) × 100\n"
            "Average = Sum of observations / Number of observations\n"
            "a^2 - b^2 = (a - b)(a + b)\n"
            "(a + b)^2 = a^2 + 2ab + b^2\n"
            "(a - b)^2 = a^2 - 2ab + b^2\n\n"
            "For higher classes, trigonometry, algebra, mensuration, and percentage formulas are the most commonly used."
        )
        return build_structured_response(user_input, answer)

    if "physics" in lowered and "formula" in lowered:
        answer = (
            f"Important physics formula sheet for {class_level}:\n"
            "Speed = Distance / Time\n"
            "Velocity = Displacement / Time\n"
            "Acceleration = Change in velocity / Time\n"
            "Force = Mass × Acceleration\n"
            "Work = Force × Displacement\n"
            "Power = Work / Time\n"
            "Pressure = Force / Area\n"
            "Momentum = Mass × Velocity\n"
            "Density = Mass / Volume\n"
            "Ohm's Law: V = I × R\n"
            "\n"
            "These formulas are commonly used in motion, force, work, and energy chapters."
        )
        return build_structured_response(user_input, answer)

    if "chemistry" in lowered and "formula" in lowered:
        answer = (
            f"Common chemistry formula sheet for {class_level}:\n"
            "Water = H2O\n"
            "Carbon dioxide = CO2\n"
            "Sodium chloride = NaCl\n"
            "Sulphuric acid = H2SO4\n"
            "Hydrochloric acid = HCl\n"
            "Ammonia = NH3\n"
            "Calcium carbonate = CaCO3\n\n"
            "These formulas represent important compounds used in school chemistry."
        )
        return build_structured_response(user_input, answer)

    if "formula" in lowered and any(token in lowered for token in ["class 1", "class 2", "class 3", "class 4", "class 5", "class 6", "class 7", "class 8", "class 9", "class 10", "class 11", "class 12", "all"]):
        answer = (
            "Formula sheet overview for classes 1 to 12:\n"
            "Maths: percentage, average, area, perimeter, algebra, trigonometry\n"
            "Physics: speed, velocity, acceleration, force, work, power, pressure, electricity\n"
            "Chemistry: H2O, CO2, NaCl, HCl, H2SO4, NH3, CaCO3 and basic reaction formulas\n\n"
            "Ask subject-wise formula sheet like 'maths formula sheet', 'physics formula sheet', or 'chemistry formula sheet' for a clearer list."
        )
        return build_structured_response(user_input, answer)

    return None


def build_blackboard_lines(question, answer_source):
    sentences = split_sentences(answer_source) or [clean_text(answer_source)]
    topic = extract_topic_from_question(question).title()
    keywords = extract_keywords(f"{question} {answer_source}", limit=5)
    core_keyword = keywords[0].title() if keywords else topic or "Concept"
    support_keyword = keywords[1].title() if len(keywords) > 1 else "Main Idea"
    final_line = sentences[0]

    return [
        "Let's solve this step by step ✍️",
        "",
        "Step 1: Understand / Given",
        f"→ Topic: {topic or 'Question'}",
        f"→ Main clue: {core_keyword}",
        "",
        "Step 2: Formula / Concept",
        f"→ Use the idea of {core_keyword}",
        f"→ Connect it with {support_keyword}",
        "",
        "Step 3: Apply",
        f"→ Read the meaning carefully",
        f"→ Pick the correct rule or concept",
        "",
        "Step 4: Solve step-by-step",
        f"→ {sentences[0]}",
        f"→ {sentences[1] if len(sentences) > 1 else 'Break it into small simple steps.'}",
        "",
        "Step 5: Final Answer",
        f"→ {final_line}",
        "",
        f"Final Answer: {final_line}"
    ]


def build_concept_board_lines(question, answer_source):
    sentences = split_sentences(answer_source) or [clean_text(answer_source)]
    key_points = extract_key_points(sentences[1:] or sentences, extract_keywords(answer_source, limit=8), limit=3)
    example = build_real_life_example(question, answer_source).replace("Real-life example:", "Example →")

    lines = [
        "Let's understand this on the board ✍️",
        "",
        "Step 1: What is it?",
        f"→ {sentences[0]}",
        "",
        "Step 2: Core idea",
        f"→ {sentences[1] if len(sentences) > 1 else sentences[0]}",
        "",
        "Step 3: Remember these points"
    ]

    for point in key_points or [sentences[0]]:
        lines.append(f"→ {point}")

    lines.extend([
        "",
        "Step 4: Example",
        example
    ])
    return lines


def lines_to_voice_steps(lines):
    steps = []
    step_number = 1
    for line in lines:
        cleaned = clean_text(line)
        if not cleaned:
            continue
        voice = cleaned.replace("→", "").strip()
        if cleaned.lower().startswith("step "):
            voice = f"Ab {voice.lower()}."
        elif cleaned.lower().startswith("final answer"):
            voice = f"Final answer ye hai: {voice.split(':', 1)[-1].strip()}"
        else:
            voice = f"Board par likh rahe hain: {voice}"
        steps.append({
            "step": step_number,
            "text": cleaned,
            "voice": voice
        })
        step_number += 1
    return steps


def build_animation_payload(question, answer_source):
    lines = build_blackboard_lines(question, answer_source) if is_numerical_query(question) else build_concept_board_lines(question, answer_source)
    return lines_to_voice_steps(lines)[:10]


def build_notes_response_text(question, answer_source):
    payload = build_notes_payload(answer_source, title=extract_topic_from_question(question).title() or "Class Notes")
    lines = [payload["title"], ""]
    for section in payload.get("sections", [])[:3]:
        lines.append(f"{section['heading']}:")
        for bullet in section.get("bullets", [])[:4]:
            lines.append(f"- {bullet}")
        lines.append("")
    if payload.get("keywords"):
        lines.append("Keywords:")
        for keyword in payload["keywords"][:6]:
            lines.append(f"- {keyword}")
    return "\n".join(lines).strip()


def build_chat_final_answer(question, answer_source, notes):
    sentences = split_sentences(answer_source) or [clean_text(answer_source)]
    body = " ".join(sentences[:3]).strip()
    if not body:
        body = clean_text(answer_source)
    return body


def build_quiz_response_text(question, answer_source):
    payload = build_quiz_payload(answer_source, title=extract_topic_from_question(question).title() or "Practice Quiz")
    lines = []
    for index, item in enumerate(payload.get("items", [])[:5], start=1):
        lines.append(f"Q{index}: {item['question']}")
    lines.append("")
    lines.append("Answers:")
    for index, item in enumerate(payload.get("items", [])[:5], start=1):
        lines.append(f"{index}. {item['answer']}")
    return "\n".join(lines).strip()


def build_structured_response(question, answer_source):
    mode = detect_output_mode(question)
    title = extract_topic_from_question(question).title() or "Quadratutor Lesson"
    diagram = build_diagram_payload(question)

    if mode == "animation":
        steps = build_animation_payload(question, answer_source)
        return {
            "mode": "animation",
            "title": title,
            "steps": steps,
            "final_answer": steps[-1]["text"] if steps else "",
            "notes": [],
            "quiz": [],
            "diagram": diagram
        }

    if mode == "notes":
        payload = build_notes_payload(answer_source, title=title)
        notes = []
        for section in payload.get("sections", [])[:3]:
            notes.extend(section.get("bullets", [])[:2])
        steps = lines_to_voice_steps([
            "Let's understand this on the board ✍️",
            f"→ Topic: {payload.get('title', title)}",
            f"→ Summary: {payload.get('overview', '')}"
        ])
        return {
            "mode": "notes",
            "title": payload.get("title", title),
            "steps": steps,
            "final_answer": build_chat_final_answer(question, payload.get("overview", ""), notes[:6]),
            "notes": notes[:6],
            "quiz": [],
            "diagram": diagram
        }

    if mode == "quiz":
        payload = build_quiz_payload(answer_source, title=title)
        quiz_items = [
            {"question": item["question"], "answer": item["answer"]}
            for item in payload.get("items", [])[:5]
        ]
        steps = lines_to_voice_steps([
            "Let's understand this on the board ✍️",
            f"→ Topic: {title}",
            "→ Quiz ready from easy to hard"
        ])
        return {
            "mode": "quiz",
            "title": payload.get("title", title),
            "steps": steps,
            "final_answer": "",
            "notes": [],
            "quiz": quiz_items,
            "diagram": diagram
        }

    if mode == "blackboard" or is_numerical_query(question):
        lines = build_blackboard_lines(question, answer_source)
        notes = extract_key_points(split_sentences(answer_source), extract_keywords(answer_source, limit=8), limit=4)
        return {
            "mode": "blackboard",
            "title": title,
            "steps": lines_to_voice_steps(lines),
            "final_answer": build_chat_final_answer(question, answer_source, notes),
            "notes": notes,
            "quiz": [],
            "diagram": diagram
        }

    lines = build_concept_board_lines(question, answer_source)
    notes = extract_key_points(split_sentences(answer_source), extract_keywords(answer_source, limit=8), limit=4)
    return {
        "mode": "concept",
        "title": title,
        "steps": lines_to_voice_steps(lines),
        "final_answer": build_chat_final_answer(question, answer_source, notes),
        "notes": notes,
        "quiz": [],
        "diagram": diagram
    }


def extract_response_text(payload):
    if not isinstance(payload, dict):
        return ""

    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"].strip()

    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text_value = content.get("text")
            if isinstance(text_value, str) and text_value.strip():
                parts.append(text_value.strip())
    return "\n".join(parts).strip()


def get_openai_settings():
    return (
        os.environ.get("OPENAI_API_KEY", "").strip(),
        os.environ.get("OPENAI_MODEL", "gpt-4.1").strip()
    )


def get_gemini_settings():
    return (
        os.environ.get("GEMINI_API_KEY", "").strip(),
        os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
    )


def get_youtube_data_api_settings():
    return os.environ.get("YOUTUBE_API_KEY", "").strip()


def get_gemini_model_candidates():
    _api_key, configured_model = get_gemini_settings()
    candidates = [
        configured_model,
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001"
    ]

    ordered = []
    for model_name in candidates:
        cleaned = (model_name or "").strip()
        if cleaned and cleaned not in ordered:
            ordered.append(cleaned)
    return ordered


def extract_gemini_text(payload):
    candidates = payload.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [
        part.get("text", "").strip()
        for part in parts
        if part.get("text", "").strip()
    ]
    return "\n".join(text_parts).strip()


def call_gemini_text(prompt, timeout=45):
    gemini_api_key, gemini_model = get_gemini_settings()
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    last_error = "Gemini request could not be completed."
    for model_name in get_gemini_model_candidates():
        rate_limited = False
        try:
            for retry_delay in (0, 1.5, 3.0):
                if retry_delay:
                    time.sleep(retry_delay)

                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {"text": prompt}
                                ]
                            }
                        ]
                    },
                    timeout=timeout
                )
                response.raise_for_status()
                payload = response.json()
                text = extract_gemini_text(payload)
                if text:
                    return text

                prompt_feedback = payload.get("promptFeedback", {})
                block_reason = prompt_feedback.get("blockReason")
                if block_reason:
                    raise RuntimeError(f"Gemini blocked the request on {model_name}: {block_reason}")

                last_error = f"Gemini returned an empty response on {model_name}."
        except requests.RequestException as exc:
            details = ""
            status_code = getattr(exc.response, "status_code", None) if getattr(exc, "response", None) is not None else None
            if getattr(exc, "response", None) is not None:
                try:
                    details = exc.response.text[:300]
                except Exception:
                    details = ""
            if status_code == 429:
                rate_limited = True
                last_error = (
                    "Gemini rate limit hit ho gayi hai. "
                    "Thoda wait karke dobara try karein, ya Google AI Studio me quota/billing check karein."
                )
            else:
                last_error = f"Gemini request failed on {model_name}: {exc}"
                if details:
                    last_error = f"{last_error} | {details}"
            if status_code == 404:
                continue
            if rate_limited:
                raise RuntimeError(last_error) from exc
            raise RuntimeError(last_error) from exc
        except RuntimeError as exc:
            last_error = str(exc)
            if "blocked" in last_error.lower():
                raise

    raise RuntimeError(last_error)


def parse_structured_json(text):
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def get_openai_structured_response(user_input, preferred_language="hinglish"):
    openai_api_key, openai_model = get_openai_settings()
    if not openai_api_key:
        return None

    schema_hint = {
        "mode": "blackboard / concept / notes / quiz / animation",
        "title": "Topic name",
        "steps": [{"step": 1, "text": "Short handwritten-style line", "voice": "Natural teacher explanation for this step"}],
        "final_answer": "Final result if applicable",
        "notes": ["Short bullet note"],
        "quiz": [{"question": "Question text", "answer": "Answer text"}],
        "diagram": {"type": "triangle / force / reaction or null"}
    }
    prompt = (
        "You are Quadratutor Ultra AI. Return only valid JSON. "
        "Teach like a real teacher writing on a blackboard. "
        "Use short board-style steps, simple voice explanations, and no extra text outside JSON. "
        "Choose mode from blackboard, concept, notes, quiz, animation. "
        f"Preferred language style: {preferred_language}. "
        f"Required JSON shape example: {json.dumps(schema_hint, ensure_ascii=False)} "
        f"User question: {user_input}"
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": openai_model,
                "input": prompt
            },
            timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        response_text = extract_response_text(payload)
        structured = parse_structured_json(response_text)
        if not isinstance(structured, dict) and response_text.strip():
            return build_structured_response(user_input, response_text)
        if not isinstance(structured, dict):
            return None

        structured.setdefault("mode", "concept")
        structured.setdefault("title", extract_topic_from_question(user_input).title() or "Quadratutor Lesson")
        structured.setdefault("steps", [])
        structured.setdefault("final_answer", "")
        structured.setdefault("notes", [])
        structured.setdefault("quiz", [])
        structured.setdefault("diagram", build_diagram_payload(user_input))
        return structured
    except Exception:
        return None


def normalize_structured_payload(structured, user_input):
    if not isinstance(structured, dict):
        return None

    structured.setdefault("mode", "concept")
    structured.setdefault("title", extract_topic_from_question(user_input).title() or "Quadratutor Lesson")
    structured.setdefault("steps", [])
    structured.setdefault("final_answer", "")
    structured.setdefault("notes", [])
    structured.setdefault("quiz", [])
    structured.setdefault("diagram", build_diagram_payload(user_input))
    return structured


def get_gemini_direct_response(user_input, preferred_language="hinglish"):
    prompt = (
        "You are Quadratutor AI, a professional teacher. "
        "Answer the student's question directly in simple, correct, student-friendly language. "
        "Do not return JSON. Do not add unnecessary headings. "
        f"Preferred language style: {preferred_language}. "
        f"Student question: {user_input}"
    )
    response_text = call_gemini_text(prompt, timeout=45)
    if not response_text.strip():
        raise RuntimeError("Gemini direct answer was empty.")
    return build_structured_response(user_input, response_text)


def get_gemini_structured_response(user_input, preferred_language="hinglish"):
    global last_gemini_error

    schema_hint = {
        "mode": "blackboard / concept / notes / quiz / animation",
        "title": "Topic name",
        "steps": [{"step": 1, "text": "Short handwritten-style line", "voice": "Natural teacher explanation for this step"}],
        "final_answer": "Direct answer in 2-5 simple sentences",
        "notes": ["Short bullet note"],
        "quiz": [{"question": "Question text", "answer": "Answer text"}],
        "diagram": {"type": "triangle / force / reaction or null"}
    }
    prompt = (
        "You are Quadratutor Ultra AI, a professional teacher. "
        "Return only valid JSON with no markdown fences. "
        "Understand the student's question properly and answer accurately. "
        "Choose mode from blackboard, concept, notes, quiz, animation. "
        "If it is a normal question, give a direct and correct answer. "
        "If it is numerical, solve it carefully and keep final_answer exact. "
        "If the user asks for notes, fill notes with short bullet points. "
        "If the user asks for quiz, provide exactly 5 question-answer pairs. "
        "Keep language simple, student-friendly, and natural. "
        f"Preferred language style: {preferred_language}. "
        "final_answer is very important and must directly answer the user's question clearly. "
        f"Required JSON shape example: {json.dumps(schema_hint, ensure_ascii=False)} "
        f"User question: {user_input}"
    )

    try:
        response_text = call_gemini_text(prompt, timeout=45)
        structured = parse_structured_json(response_text)
        if not isinstance(structured, dict) and response_text.strip():
            last_gemini_error = ""
            return build_structured_response(user_input, response_text)
        normalized = normalize_structured_payload(structured, user_input)
        if normalized:
            last_gemini_error = ""
            return normalized
        raise RuntimeError("Gemini returned invalid structured JSON.")
    except Exception as structured_error:
        try:
            direct_response = get_gemini_direct_response(user_input, preferred_language)
            last_gemini_error = ""
            return direct_response
        except Exception as direct_error:
            last_gemini_error = str(direct_error or structured_error)[:240]
            return None


def resolve_language(question, preferred_language):
    lowered = question.lower()
    if "hinglish" in lowered:
        return "hinglish"
    if "english" in lowered:
        return "english"
    if "hindi" in lowered:
        return "hindi"
    return preferred_language or "hinglish"


def get_labels(language):
    if language == "english":
        return {
            "teacher": "Teacher Explanation:",
            "board": "Blackboard Notes:",
            "steps": "Handwritten Steps:",
            "styles": "Answer Styles:",
            "style_1": "1. Short exam style:",
            "style_2": "2. Easy explanation:",
            "style_3": "3. Key points:"
        }
    if language == "hindi":
        return {
            "teacher": "शिक्षक समझा रहा है:",
            "board": "बोर्ड नोट्स:",
            "steps": "हैंडरिटन स्टेप्स:",
            "styles": "उत्तर के तरीके:",
            "style_1": "1. छोटा एग्जाम स्टाइल:",
            "style_2": "2. आसान हिंदी समझ:",
            "style_3": "3. मुख्य बिंदु:"
        }
    return {
        "teacher": "Teacher Explanation:",
        "board": "Blackboard Notes:",
        "steps": "Handwritten Steps:",
        "styles": "Answer Styles:",
        "style_1": "1. Short exam style:",
        "style_2": "2. Easy Hinglish explanation:",
        "style_3": "3. Key points:"
    }


def get_display_labels(language):
    if language == "hindi":
        return {
            "teacher": "शिक्षक समझा रहा है:",
            "board": "ब्लैकबोर्ड नोट्स:",
            "steps": "हैंडरिटन स्टेप्स:",
            "styles": "उत्तर के तरीके:",
            "style_1": "1. छोटा एग्जाम स्टाइल:",
            "style_2": "2. आसान हिंदी समझ:",
            "style_3": "3. मुख्य बिंदु:"
        }
    return get_labels(language)


def format_smart_answer(question, answer_source, language="hinglish"):
    return build_structured_response(question, answer_source)


def get_exact_known_answer(user_input):
    normalized_query = normalize_phrase(user_input)
    if not normalized_query:
        return None

    for record in qa_records:
        if normalize_phrase(record.get("question", "")) == normalized_query:
            return record.get("answer", "")
    return None


def build_richer_local_answer(question, answer_source):
    topic = infer_topic_from_prompt(question)
    topic_key = normalize_phrase(topic)
    collected = []
    seen = set()

    def add_part(text):
        cleaned = clean_text(text)
        if not cleaned:
            return
        key = normalize_phrase(cleaned)
        if key and key not in seen:
            collected.append(cleaned)
            seen.add(key)

    add_part(answer_source)

    for record in qa_records:
        record_topic = normalize_phrase(record.get("topic", ""))
        record_question = normalize_phrase(record.get("question", ""))
        if topic_key and (record_topic == topic_key or topic_key in record_question):
            add_part(record.get("answer", ""))
        if len(collected) >= 2:
            break

    return " ".join(collected[:2]).strip() or clean_text(answer_source)


def get_best_known_answer(user_input):
    if not qa_records:
        return None, 0.0

    user_vec = vectorizer.transform([user_input])
    similarity = cosine_similarity(user_vec, X)
    index = similarity.argmax()
    confidence = float(similarity[0][index])
    query_terms = keyword_set(user_input)
    record = qa_records[index]
    question_terms = keyword_set(record.get("search_text", ""))
    overlap = len(query_terms & question_terms)
    if confidence > 0.62 or (confidence > 0.48 and overlap >= 2):
        return record.get("answer", ""), confidence
    return None, confidence


def get_response(user_input, preferred_language="hinglish"):
    global last_question

    lowered = user_input.lower()
    language = resolve_language(user_input, preferred_language)
    last_question = user_input

    if "who are you" in lowered:
        identity = (
            "I am Quadratutor, an AI-powered learning assistant developed by "
            "Suraj, Mohd Rihan Malik, Mohd Raza, and Sagar Shah."
        )
        return format_smart_answer(user_input, identity, language)

    if "hello" in lowered:
        greeting = "Hello! Ask me anything and I will explain it in simple teacher style."
        if language == "hindi":
            greeting = "नमस्ते! आप कुछ भी पूछ सकते हैं, मैं शिक्षक की तरह समझाऊंगा।"
        elif language != "english":
            greeting = "Hello! Jo bhi puchoge, main teacher ki tarah simple Hinglish me samjhaunga."
        return build_structured_response(user_input, greeting)

    equation_response = solve_detected_equation(user_input)
    if equation_response:
        return equation_response

    formula_response = build_formula_sheet_response(user_input)
    if formula_response:
        return formula_response

    exact_answer = get_exact_known_answer(user_input)
    if exact_answer:
        return format_smart_answer(user_input, exact_answer, language)

    matched_answer, _confidence = get_best_known_answer(lowered)
    if matched_answer:
        return format_smart_answer(user_input, build_richer_local_answer(user_input, matched_answer), language)

    builtin_answer = get_builtin_topic_explanation(user_input)
    if builtin_answer:
        return format_smart_answer(user_input, build_richer_local_answer(user_input, builtin_answer), language)

    definition_fallback = build_definition_fallback(user_input)
    if definition_fallback:
        return format_smart_answer(user_input, definition_fallback, language)

    subject = detect_subject(user_input)
    subject_fallback = build_subject_fallback(extract_topic_from_question(user_input), subject)
    if subject_fallback:
        return format_smart_answer(user_input, subject_fallback, language)

    generic_answer = build_generic_topic_explanation(user_input)
    if generic_answer:
        return format_smart_answer(user_input, generic_answer, language)

    last_question = user_input
    question_type = classify_question(user_input)
    fallback = (
        f"This looks like a {question_type} type question. I will explain it from the topic words I understood "
        "and give you a basic teacher-style answer."
    )
    return build_structured_response(user_input, fallback)


def build_notes_text(payload):
    lines = [payload.get("title", "Notes"), "", f"Overview: {payload.get('overview', '')}", ""]
    for section in payload.get("sections", []):
        lines.append(section.get("heading", "Section"))
        for bullet in section.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    keywords = payload.get("keywords", [])
    if keywords:
        lines.append("Keywords: " + ", ".join(keywords))
    return "\n".join(lines).strip()


def escape_pdf_text(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def simple_pdf_bytes(title, body):
    lines = [title] + [""] + body.splitlines()
    y = 780
    text_commands = ["BT", "/F1 12 Tf", "50 780 Td", "14 TL"]
    first_line = True

    for raw_line in lines[:45]:
        line = escape_pdf_text(raw_line[:100] or " ")
        if first_line:
            text_commands.append(f"({line}) Tj")
            first_line = False
        else:
            text_commands.append("T*")
            text_commands.append(f"({line}) Tj")
        y -= 14
        if y < 60:
            break

    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n")
    objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("latin-1") + stream + b"\nendstream endobj\n")
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_position = len(pdf)
    pdf += f"xref\n0 {len(offsets)}\n".encode("latin-1")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("latin-1")
    pdf += (
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("latin-1")
    )
    return pdf


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api-status")
def api_status():
    openai_api_key, openai_model = get_openai_settings()
    return jsonify({
        "provider": "openai",
        "openai_connected": bool(openai_api_key),
        "openai_model": openai_model or "gpt-4.1"
    })


@app.route("/chat", methods=["POST"])
def chat():
    global last_question, vectorizer, X

    data = request.json or {}
    user_input = (data.get("message") or "").strip()
    language = data.get("language", "hinglish")
    teach_answer = clean_text(data.get("teach_answer", ""))
    teach_question = clean_text(data.get("teach_question", ""))

    if teach_answer:
        question_to_save = teach_question or last_question
        if not question_to_save:
            return jsonify({"response": "No question available to teach right now."})

        save_new_data(question_to_save, teach_answer)
        return jsonify({
            "response": f"Saved. Next time I will answer '{question_to_save}' from your taught answer."
        })

    if not user_input:
        return jsonify({"response": "Please type a question."})

    if user_input.lower().startswith("teach:"):
        answer = user_input.replace("teach:", "").strip()

        if last_question:
            save_new_data(last_question, answer)
            load_data()
            vectorizer = TfidfVectorizer()
            X = vectorizer.fit_transform([record["search_text"] for record in qa_records] or [""])
            return jsonify({"response": "Got it! I learned and updated my knowledge."})
        return jsonify({"response": "No question to learn from!"})

    return jsonify({"response": get_response(user_input, language)})


@app.route("/generate-notes", methods=["POST"])
def generate_notes():
    text = request.json.get("text", "")
    return jsonify(build_notes_payload(text, title="Generated Notes"))


@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    text = request.json.get("text", "")
    count = request.json.get("count")
    quiz_mode = request.json.get("quiz_mode", "mixed")
    difficulty = request.json.get("difficulty", "medium")
    return jsonify(build_quiz_payload(
        text,
        title="Generated Quiz",
        requested_count=count,
        quiz_mode=quiz_mode,
        difficulty=difficulty
    ))


@app.route("/generate-quiz-upload", methods=["POST"])
def generate_quiz_upload():
    uploaded_file = request.files.get("file")
    count = request.form.get("count")
    quiz_mode = request.form.get("quiz_mode", "mixed")
    difficulty = request.form.get("difficulty", "medium")

    if not uploaded_file:
        return jsonify({"error": "Please upload a PDF file."}), 400
    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        text = extract_pdf_text(uploaded_file)
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500
    except Exception:
        return jsonify({"error": "Could not read the PDF. Please try another file."}), 400

    if not text:
        return jsonify({"error": "This PDF did not contain readable text for quiz generation."}), 400

    payload = build_quiz_payload(
        text,
        title="Quiz from PDF",
        requested_count=count,
        quiz_mode=quiz_mode,
        difficulty=difficulty
    )
    payload["source"] = uploaded_file.filename
    payload["source_text"] = text
    return jsonify(payload)


@app.route("/generate-assignment", methods=["POST"])
def generate_assignment():
    text = request.json.get("text", "")
    level = clean_text(request.json.get("level", "school")).lower() or "school"
    try:
        items = build_assignment_items(text, level=level)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"title": "AI Assignment Generator", "items": items, "level": level})


@app.route("/generate-assignment-questions-upload", methods=["POST"])
def generate_assignment_questions_upload():
    uploaded_file = request.files.get("file")
    level = clean_text(request.form.get("level", "school")).lower() or "school"
    count = request.form.get("count", "5")

    if not uploaded_file:
        return jsonify({"error": "Please upload syllabus or notes first."}), 400

    try:
        source_text = extract_text_from_uploaded_study_file(uploaded_file)
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        return jsonify({"error": "Could not read the uploaded file."}), 400

    if not source_text:
        return jsonify({"error": "This file did not contain readable study content."}), 400

    try:
        question_count = max(1, min(20, int(count)))
    except (TypeError, ValueError):
        question_count = 5

    generated = generate_assignment_questions_from_text(source_text, level=level, count=question_count)
    questions = generated.get("questions", [])
    summary = generated.get("summary", "")
    formatted = "\n".join(f"Q{index}. {question}" for index, question in enumerate(questions, start=1))
    return jsonify({
        "title": "Generated Assignment Questions",
        "questions": questions,
        "question_groups": generated.get("question_groups", []),
        "formatted_questions": formatted,
        "source": uploaded_file.filename,
        "summary": summary,
        "level": level
    })


@app.route("/download-assignment-pdf", methods=["POST"])
def download_assignment_pdf():
    payload = request.json or {}
    items = payload.get("items", [])
    level = clean_text(payload.get("level", "school")).lower() or "school"
    if not items:
        text = payload.get("text", "")
        try:
            items = build_assignment_items(text, level=level)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    buffer = BytesIO()
    generate_assignment_pdf_from_items(items, buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="assignment.pdf",
        mimetype="application/pdf"
    )


@app.route("/youtube-study", methods=["POST"])
def youtube_study():
    data = request.json or {}
    link = data.get("link", "").strip()
    mode = data.get("mode", "notes")
    transcript = clean_text(data.get("transcript", ""))
    count = data.get("count")
    quiz_mode = data.get("quiz_mode", "mixed")
    difficulty = data.get("difficulty", "medium")

    if transcript:
        video_context = {
            "title": "Transcript-Based YouTube Study",
            "description": "Generated directly from pasted transcript.",
            "channel": "",
            "video_id": extract_video_id(link),
            "text": transcript,
            "used_transcript": True,
            "used_manual_transcript": True
        }
    else:
        if not link:
            return jsonify({"error": "Please provide a YouTube link or paste a transcript."}), 400
        try:
            video_context = fetch_youtube_context(link)
        except Exception:
            video_context = build_fallback_video_context(link)

    source_text = video_context["text"] or video_context["title"]
    payload = (
        build_quiz_payload(
            source_text,
            title=video_context["title"],
            requested_count=count,
            quiz_mode=quiz_mode,
            difficulty=difficulty
        )
        if mode == "quiz"
        else build_video_notes_payload(video_context)
    )
    payload["video"] = video_context
    return jsonify(payload)


@app.route("/youtube-transcript", methods=["POST"])
def youtube_transcript():
    data = request.json or {}
    url = clean_text(data.get("url", ""))
    if not url:
        return jsonify({"error": "Please provide a YouTube URL."}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube link."}), 400

    metadata = {"title": f"YouTube Video {video_id}", "description": "", "channel": ""}
    try:
        metadata = fetch_youtube_data_api_metadata(video_id)
    except Exception:
        try:
            metadata = fetch_youtube_oembed(url)
        except Exception:
            pass

    try:
        transcript_text = fetch_transcript_with_api(video_id)
        message = "Transcript fetched successfully."
        source_used = "transcript"
    except Exception:
        transcript_text = clean_text(
            f"Title: {metadata.get('title', f'YouTube Video {video_id}')}. "
            f"Description: {metadata.get('description', 'Description not available.')}. "
            f"Channel: {metadata.get('channel', 'Unknown channel')}."
        )
        message = "Transcript not available, so title and description were used instead."
        source_used = "title_description"

    return jsonify({
        "success": True,
        "video_id": video_id,
        "title": metadata.get("title", f"YouTube Video {video_id}"),
        "transcript_text": transcript_text,
        "source_used": source_used,
        "message": message
    })


@app.route("/youtube-summarizer", methods=["POST"])
def youtube_summarizer():
    data = request.json or {}
    url = clean_text(data.get("url", ""))
    if not url:
        return jsonify({"success": False, "error": "Please provide a YouTube URL."}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"success": False, "error": "Invalid YouTube link."}), 400

    summary_source = fetch_youtube_summary_source_v2(url, video_id)
    try:
        summary_text = summarize_with_gemini_v2(summary_source["source_text"])
    except Exception:
        summary_text = build_youtube_summary_fallback_v2(summary_source["metadata"])

    if not clean_text(summary_text):
        summary_text = build_youtube_summary_fallback_v2(summary_source["metadata"])

    return jsonify({
        "success": True,
        "video_id": video_id,
        "transcript_text": summary_source["transcript_text"],
        "used_transcript": summary_source["used_transcript"],
        "source_used": "transcript" if summary_source["used_transcript"] else "title_description",
        "message": "" if summary_source["used_transcript"] else "Transcript not available, summary created from video title and description.",
        "summary": summary_text
    })


@app.route("/youtube-mindmap", methods=["POST"])
def youtube_mindmap():
    data = request.json or {}
    url = clean_text(data.get("url", ""))
    prompt = clean_text(data.get("prompt", ""))
    if not url and not prompt:
        return jsonify({"success": False, "error": "Please provide a YouTube URL or prompt."}), 400

    if prompt and not url:
        try:
            mindmap_text = generate_mindmap_with_gemini(prompt)
        except Exception:
            mindmap_text = build_mindmap_fallback(prompt)

        return jsonify({
            "success": True,
            "video_id": "",
            "transcript_text": "",
            "used_transcript": False,
            "source_used": "prompt",
            "message": "Prompt analyzed for mind map generation.",
            "mind_map": mindmap_text
        })

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"success": False, "error": "Invalid YouTube link."}), 400

    mindmap_source = fetch_youtube_summary_source_v2(url, video_id)
    try:
        mindmap_text = generate_mindmap_with_gemini(mindmap_source["source_text"])
    except Exception:
        mindmap_text = build_youtube_mindmap_fallback(mindmap_source["metadata"])

    if not clean_text(mindmap_text):
        mindmap_text = build_youtube_mindmap_fallback(mindmap_source["metadata"])

    return jsonify({
        "success": True,
        "video_id": video_id,
        "transcript_text": mindmap_source["transcript_text"],
        "used_transcript": mindmap_source["used_transcript"],
        "source_used": "transcript" if mindmap_source["used_transcript"] else "title_description",
        "message": "" if mindmap_source["used_transcript"] else "Transcript not available, mind map created from video title and description.",
        "mind_map": mindmap_text
    })


@app.route("/simplify-notes", methods=["POST"])
def simplify_notes():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return jsonify({"error": "Please upload a PDF file."}), 400
    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        text = extract_pdf_text(uploaded_file)
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500
    except Exception:
        return jsonify({"error": "Could not read the PDF. Please try another file."}), 400

    payload = build_notes_payload(text, title="Simplified PDF Notes")
    payload["source"] = uploaded_file.filename
    payload["source_text"] = text
    payload["quiz"] = build_quiz_payload(text, title="Quiz from PDF Notes", requested_count=5, quiz_mode="mixed", difficulty="medium")
    return jsonify(payload)


@app.route("/download-notes-pdf", methods=["POST"])
def download_notes_pdf():
    payload = request.json or {}
    title = clean_text(payload.get("title", "Quadratutor Notes")) or "Quadratutor Notes"
    body = build_notes_text(payload)
    pdf_bytes = simple_pdf_bytes(title, body)
    return send_file(
        BytesIO(pdf_bytes),
        as_attachment=True,
        download_name="quadratutor-notes.pdf",
        mimetype="application/pdf"
    )


@app.route("/library/upload", methods=["POST"])
def library_upload():
    uploaded_file = request.files.get("file")
    title = clean_text(request.form.get("title", ""))
    board = clean_text(request.form.get("board", ""))
    class_level = clean_text(request.form.get("class_level", ""))
    subject = clean_text(request.form.get("subject", ""))
    material_type = clean_text(request.form.get("material_type", ""))

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Please choose a file to upload."}), 400

    extension = os.path.splitext(uploaded_file.filename)[1].lower()
    if extension not in ALLOWED_LIBRARY_EXTENSIONS:
        return jsonify({"error": "Unsupported file type. Please upload PDF, text, image, or common document files."}), 400

    ensure_library_storage()
    item_id = uuid4().hex[:12]
    safe_name = secure_filename(uploaded_file.filename) or f"file{extension}"
    stored_name = f"{item_id}_{safe_name}"
    file_path = os.path.join(LIBRARY_DIR, stored_name)
    uploaded_file.save(file_path)

    item = {
        "id": item_id,
        "title": title or os.path.splitext(safe_name)[0].replace("_", " ").title(),
        "board": board or "General",
        "class_level": class_level or "General",
        "subject": subject or "General",
        "material_type": material_type or "Notes",
        "filename": safe_name,
        "stored_name": stored_name,
        "extension": extension,
        "uploaded_at": datetime.now().strftime("%d %b %Y, %I:%M %p")
    }

    items = read_library_index()
    items.insert(0, item)
    write_library_index(items)
    return jsonify({"item": serialize_library_item(item)})


@app.route("/library/items", methods=["GET"])
def library_items():
    search = normalize_filter(request.args.get("search", ""))
    subject = normalize_filter(request.args.get("subject", ""))
    board = normalize_filter(request.args.get("board", ""))
    class_level = normalize_filter(request.args.get("class_level", ""))
    material_type = normalize_filter(request.args.get("material_type", ""))

    items = read_library_index()
    filtered = [
        serialize_library_item(item)
        for item in items
        if matches_library_filters(item, search, subject, board, class_level, material_type)
    ]
    return jsonify({"items": filtered})


@app.route("/library/file/<item_id>", methods=["GET"])
def library_file(item_id):
    items = read_library_index()
    item = next((entry for entry in items if entry["id"] == item_id), None)
    if not item:
        return "File not found.", 404

    file_path = os.path.join(LIBRARY_DIR, item["stored_name"])
    if not os.path.exists(file_path):
        return "Stored file is missing.", 404

    mimetype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return send_file(file_path, mimetype=mimetype)


@app.route("/library/download/<item_id>", methods=["GET"])
def library_download(item_id):
    items = read_library_index()
    item = next((entry for entry in items if entry["id"] == item_id), None)
    if not item:
        return "File not found.", 404

    file_path = os.path.join(LIBRARY_DIR, item["stored_name"])
    if not os.path.exists(file_path):
        return "Stored file is missing.", 404

    mimetype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return send_file(file_path, as_attachment=True, download_name=item["filename"], mimetype=mimetype)


if __name__ == "__main__":
    app.run(debug=True)
