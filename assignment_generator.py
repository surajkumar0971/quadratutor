import json
import os
import re
from collections import Counter
from pathlib import Path

import requests
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 72
RIGHT_MARGIN = 54
TOP_MARGIN = 72
BOTTOM_MARGIN = 54
LINE_GAP = 22
QUESTION_GAP = 16
MAX_TEXT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
RULE_COLOR = Color(0.78, 0.86, 0.96, alpha=1)
MARGIN_COLOR = Color(0.95, 0.45, 0.45, alpha=1)
INK_COLOR = Color(0.12, 0.16, 0.36, alpha=1)


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def clean_line_break_text(value):
    text = (value or "").replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


QUESTION_STOP_WORDS = {
    "this", "that", "with", "from", "have", "were", "which", "what", "when", "where",
    "their", "about", "into", "your", "these", "those", "also", "than", "then",
    "only", "very", "much", "many", "more", "most", "some", "such", "because",
    "while", "using", "used", "there", "being", "been", "through", "between",
    "presentation", "presentations", "skills", "skill", "level", "chapter", "unit"
}

GENERIC_TOPIC_LINES = {
    "introduction", "summary", "overview", "objectives", "contents", "conclusion",
    "references", "exercise", "exercises", "questions", "assignment", "topic",
    "level", "key ideas", "focus area", "important detail", "main topic"
}


def parse_question_lines(raw_text):
    text = clean_line_break_text(raw_text)
    if not text:
        return []

    lines = []
    for raw_line in text.split("\n"):
        line = clean_text(re.sub(r"^\s*(q(?:uestion)?\s*\d+[\.\):\-]?|[-*•\d\.\)]\s*)", "", raw_line, flags=re.IGNORECASE))
        if line:
            lines.append(line)
    return lines


def normalize_topic_phrase(value):
    value = clean_text(value)
    value = re.sub(r"^[\-\*\d\.\)\(:\s]+", "", value)
    value = re.sub(r"[^A-Za-z0-9\s/&-]", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -")
    return value


def extract_topic_candidates(source_text):
    text = clean_line_break_text(source_text)
    if not text:
        return []

    lines = [normalize_topic_phrase(line) for line in text.split("\n")]
    lines = [line for line in lines if line]

    candidates = []
    seen = set()

    for line in lines:
        word_count = len(line.split())
        normalized = line.lower()
        if normalized in GENERIC_TOPIC_LINES:
            continue
        if 1 <= word_count <= 8 and len(line) <= 60:
            key = line.lower()
            if key not in seen:
                seen.add(key)
                candidates.append(line)

    words = [
        word.lower()
        for word in re.findall(r"\b[A-Za-z][A-Za-z\-]{3,}\b", text)
        if word.lower() not in QUESTION_STOP_WORDS
    ]
    common_words = [word for word, _count in Counter(words).most_common(12)]
    for word in common_words:
        topic = word.title()
        if topic.lower() not in seen:
            seen.add(topic.lower())
            candidates.append(topic)

    return candidates[:12]


def build_question_variants_for_topic(topic, level="school"):
    topic = normalize_topic_phrase(topic)
    if not topic:
        return []

    variants = [
        f"Explain {topic} in detail.",
        f"Discuss the importance of {topic}.",
        f"Write a short note on {topic}.",
        f"Describe the main features of {topic}.",
    ]

    if level == "college":
        variants.extend([
            f"Analyze the role of {topic} in the given study material.",
            f"Discuss the practical applications of {topic}.",
        ])
    else:
        variants.extend([
            f"What is {topic}?",
            f"Why is {topic} important?",
        ])

    return variants


def summarize_assignment_source(source_text):
    text = clean_line_break_text(source_text)
    lines = [clean_text(line) for line in text.split("\n") if clean_text(line)]
    topics = extract_topic_candidates(text)

    heading = topics[0] if topics else "Main Topic"
    support = topics[1] if len(topics) > 1 else heading
    detail = topics[2] if len(topics) > 2 else support
    overview = lines[0] if lines else text[:180]

    return {
        "main_topic": heading,
        "support_topic": support,
        "detail_topic": detail,
        "overview": overview,
        "topics": topics
    }


def parse_assignment_summary_text(summary_text):
    text = clean_line_break_text(summary_text)
    if not text:
        return summarize_assignment_source("")

    main_topic = ""
    support_topic = ""
    detail_topic = ""
    topics = []
    overview = ""
    in_key_ideas = False

    for raw_line in text.split("\n"):
        line = clean_text(raw_line)
        lowered = line.lower()
        if not line:
            continue

        if lowered.startswith("main topic:"):
            main_topic = normalize_topic_phrase(line.split(":", 1)[1])
            overview = overview or main_topic
            in_key_ideas = False
            continue
        if lowered.startswith("level:"):
            in_key_ideas = False
            continue
        if lowered.startswith("key ideas:"):
            in_key_ideas = True
            continue
        if lowered.startswith("focus area:"):
            support_topic = normalize_topic_phrase(line.split(":", 1)[1])
            in_key_ideas = False
            continue
        if lowered.startswith("important detail:"):
            detail_topic = normalize_topic_phrase(line.split(":", 1)[1])
            in_key_ideas = False
            continue
        if in_key_ideas and line.startswith("-"):
            topic = normalize_topic_phrase(line.lstrip("-").strip())
            if topic:
                topics.append(topic)
            continue

    topics = [topic for topic in topics if topic and topic.lower() not in GENERIC_TOPIC_LINES]
    if main_topic and main_topic not in topics:
        topics.insert(0, main_topic)
    if support_topic and support_topic not in topics:
        topics.append(support_topic)
    if detail_topic and detail_topic not in topics:
        topics.append(detail_topic)

    if not main_topic:
        fallback = summarize_assignment_source(text)
        return fallback

    return {
        "main_topic": main_topic,
        "support_topic": support_topic or (topics[1] if len(topics) > 1 else main_topic),
        "detail_topic": detail_topic or (topics[2] if len(topics) > 2 else (support_topic or main_topic)),
        "overview": overview or main_topic,
        "topics": topics[:12]
    }


def fallback_assignment_summary(source_text, level="school"):
    summary = summarize_assignment_source(source_text)
    topics = summary["topics"][:6]
    if not topics:
        topics = ["Main Topic"]

    key_points = []
    for topic in topics:
        key_points.append(f"- {topic}")

    level_line = "school-level" if level == "school" else "college-level"
    lines = [
        f"Main Topic: {summary['main_topic']}",
        f"Level: {level_line}",
        "Key Ideas:"
    ]
    lines.extend(key_points)
    lines.append(f"Focus Area: {summary['support_topic']}")
    lines.append(f"Important Detail: {summary['detail_topic']}")
    return "\n".join(lines).strip()


def generate_assignment_summary_from_text(source_text, level="school"):
    api_key, model = get_openai_settings()
    source_text = clean_line_break_text(source_text)
    if not source_text:
        return ""

    if not api_key:
        return fallback_assignment_summary(source_text, level)

    prompt = (
        "You are a study assistant. Read the uploaded syllabus or notes and create a short structured summary. "
        "Keep it simple and useful for generating assignment questions. "
        "Return clean text only in this format:\n"
        "Main Topic: ...\n"
        "Key Ideas:\n"
        "- ...\n"
        "- ...\n"
        "- ...\n"
        "Focus Area: ...\n"
        "Important Detail: ...\n\n"
        f"Level: {level}\n\n"
        f"Content:\n{source_text[:8000]}"
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
            },
            timeout=45,
        )
        response.raise_for_status()
        summary_text = clean_line_break_text(extract_response_text(response.json()))
        return summary_text or fallback_assignment_summary(source_text, level)
    except Exception:
        return fallback_assignment_summary(source_text, level)


def split_questions(raw_text):
    text = (raw_text or "").replace("\r\n", "\n").strip()
    if not text:
        return []

    matches = list(re.finditer(r"(?im)^\s*(q(?:uestion)?\s*\d+[\.\):\-]?)\s*", text))
    if matches:
        questions = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            label_match = re.match(r"(?is)^\s*(q(?:uestion)?\s*(\d+))[\.\):\-]?\s*(.*)$", block, flags=re.IGNORECASE | re.DOTALL)
            if label_match:
                number = label_match.group(2)
                body = clean_text(label_match.group(3))
                if body:
                    questions.append((f"Q{number}", body))
        if questions:
            return questions

    lines = [re.sub(r"^\s*[-*•]+\s*", "", clean_text(line)) for line in text.split("\n") if clean_text(line)]
    return [(f"Q{index}", line) for index, line in enumerate(lines, start=1)]


def detect_topic(question):
    lowered = question.lower()
    known_topics = {
        "photosynthesis": "photosynthesis",
        "newton": "newton laws",
        "democracy": "democracy",
        "python": "python",
        "algorithm": "algorithm",
        "osmosis": "osmosis",
        "blockchain": "blockchain",
        "database": "database",
        "force": "force",
        "motion": "motion",
        "acid": "acid base reaction",
        "base": "acid base reaction",
        "ecosystem": "ecosystem",
        "cell": "cell",
        "dna": "dna",
    }
    for keyword, topic in known_topics.items():
        if keyword in lowered:
            return topic
    words = re.findall(r"[A-Za-z][A-Za-z\-]+", question)
    return " ".join(words[:4]) if words else "the topic"


def fallback_answer(question):
    topic = detect_topic(question)
    templates = {
        "photosynthesis": (
            "Photosynthesis is the process by which green plants prepare their own food with the help of sunlight. "
            "In this process, plants take carbon dioxide from the air and water from the soil. Chlorophyll present in green leaves absorbs sunlight and helps convert these raw materials into glucose. "
            "Oxygen is released as a useful by-product. This process is very important because it gives food to plants and also helps maintain the oxygen balance in nature."
        ),
        "newton laws": (
            "Newton's laws of motion explain how objects move and how forces act on them. The first law says that an object remains at rest or continues moving unless an external force acts on it. "
            "The second law states that force is equal to mass multiplied by acceleration, so greater force produces greater change in motion. "
            "The third law says that every action has an equal and opposite reaction. These laws are used to understand daily life examples such as walking, pushing a cart, and moving vehicles."
        ),
        "democracy": (
            "Democracy is a form of government in which people choose their leaders by voting. It gives citizens the right to express their opinions and take part in decision making. "
            "In a democratic country, laws are made according to the constitution and the government is answerable to the people. "
            "Democracy is important because it protects freedom, equality, and justice. It also allows peaceful change of rulers through elections."
        ),
        "python": (
            "Python is a high-level programming language that is easy to learn and use. It has simple syntax, so students can read and write programs without much difficulty. "
            "Python is widely used in web development, data science, automation, and artificial intelligence. "
            "It supports many ready-made libraries that make programming faster and easier. Because of its simplicity and usefulness, Python is one of the most popular languages in the world."
        ),
        "algorithm": (
            "An algorithm is a step-by-step method used to solve a problem or complete a task. In computer science, algorithms are written to guide the computer in performing operations in the correct order. "
            "A good algorithm should be clear, finite, and efficient. "
            "For example, a recipe for making tea can be seen as an algorithm because each step is performed in sequence to get the final result."
        ),
        "osmosis": (
            "Osmosis is the movement of water molecules from a region of higher water concentration to a region of lower water concentration through a semipermeable membrane. "
            "It is a natural process that helps maintain balance in living cells. "
            "For example, plant roots absorb water from the soil through osmosis. This process is important for the survival of plants and animals because it helps in the movement of water where it is needed."
        ),
        "blockchain": (
            "Blockchain is a digital system of recording information in the form of connected blocks. Each block stores data and is linked with the previous block, which makes the record secure and difficult to change. "
            "It is mainly known for its use in cryptocurrency, but it is also used in banking, supply chains, and secure record keeping. "
            "The main features of blockchain are transparency, security, and decentralization."
        ),
        "database": (
            "A database is an organized collection of related data stored in a proper manner so that it can be accessed, managed, and updated easily. "
            "Databases are used in schools, banks, hospitals, and websites to store important information. "
            "A database management system helps users create, edit, and retrieve data quickly. "
            "It improves accuracy and reduces the problem of data duplication."
        ),
        "force": (
            "Force is a push or pull that can change the state of rest or motion of an object. It can make an object move, stop, change direction, or change speed. "
            "Force is measured in newtons. "
            "In daily life, opening a door, kicking a football, and applying brakes on a bike are examples of force. "
            "Thus, force plays an important role in understanding motion."
        ),
        "motion": (
            "Motion means the change in position of an object with time. If an object moves from one place to another, it is said to be in motion. "
            "Motion can be slow, fast, uniform, or non-uniform depending on how the object travels. "
            "Examples of motion include a moving car, a flying bird, and a rolling ball. "
            "The study of motion helps us understand many events in everyday life."
        ),
        "acid base reaction": (
            "An acid-base reaction is a chemical reaction in which an acid reacts with a base to form salt and water. This process is also called neutralization. "
            "Acids usually release hydrogen ions, while bases release hydroxide ions. "
            "When they combine, they reduce each other's effect and produce new substances. "
            "An example is hydrochloric acid reacting with sodium hydroxide to form sodium chloride and water."
        ),
        "ecosystem": (
            "An ecosystem is a system formed by living organisms and their physical environment interacting with each other. It includes plants, animals, microorganisms, air, water, and soil. "
            "All parts of an ecosystem are connected and depend on one another for survival. "
            "Examples of ecosystems are forests, ponds, deserts, and grasslands. "
            "A healthy ecosystem helps maintain balance in nature."
        ),
        "cell": (
            "A cell is the basic structural and functional unit of life. All living organisms are made up of cells. Some organisms consist of only one cell, while others are made up of many cells. "
            "A cell performs important functions such as nutrition, respiration, and reproduction. "
            "Because it carries out all life activities, the cell is called the building block of life."
        ),
        "dna": (
            "DNA stands for deoxyribonucleic acid. It is the hereditary material present in living organisms and carries genetic information from one generation to the next. "
            "DNA controls the growth, development, and functioning of the body. "
            "It is mainly found in the nucleus of the cell and is arranged in the form of chromosomes. "
            "DNA is important because it determines many inherited characteristics."
        ),
    }
    if topic in templates:
        return templates[topic]

    subject_line = topic.title() if topic else "This topic"
    return (
        f"{subject_line} is an important topic in study. It can be understood by first knowing its meaning and then learning its main points in a simple order. "
        f"It is useful because it helps students understand the basic idea, its features, and its importance in practical life. "
        f"When we study {topic}, we should focus on the definition, working process, and one suitable example. "
        "This makes the answer clear, complete, and easy to remember in an examination."
    )


def detect_programming_language(question):
    lowered = question.lower()
    if " c++" in lowered or lowered.startswith("c++"):
        return "C++"
    if re.search(r"\bc program\b|\bin c\b|write a c\b", lowered):
        return "C"
    if "python" in lowered:
        return "Python"
    return ""


def build_programming_assignment(question, level="school"):
    lowered = question.lower()
    language = detect_programming_language(question) or "Programming"
    level_line = "school" if level == "school" else "college"

    if "two numbers" in lowered and "sum" in lowered:
        code = (
            "#include <stdio.h>\n\n"
            "int main() {\n"
            "    int a, b, sum;\n"
            '    printf("Enter two numbers: ");\n'
            '    scanf("%d %d", &a, &b);\n'
            "    sum = a + b;\n"
            '    printf("Sum = %d", sum);\n'
            "    return 0;\n"
            "}"
            if language == "C"
            else
            'a = int(input("Enter first number: "))\n'
            'b = int(input("Enter second number: "))\n'
            "sum_value = a + b\n"
            'print("Sum =", sum_value)'
        )
        return {
            "title": f"{language} Program to Find the Sum of Two Numbers",
            "introduction": f"This {level_line}-level assignment explains a {language} program that takes two numbers as input and prints their sum.",
            "sections": [
                {"heading": "Logic", "content": "The program reads two numbers from the user, adds them, and stores the result in a variable."},
                {"heading": "Program", "content": code},
                {"heading": "Output", "content": "If the user enters 5 and 7, the output will be: Sum = 12."}
            ],
            "conclusion": f"In conclusion, this program shows the basic use of input, variables, arithmetic addition, and output in {language}.",
        }

    if "area of a rectangle" in lowered or ("rectangle" in lowered and "length" in lowered and "width" in lowered):
        code = (
            'length = float(input("Enter length: "))\n'
            'width = float(input("Enter width: "))\n'
            "area = length * width\n"
            'print("Area of rectangle =", area)'
            if language == "Python"
            else
            "#include <stdio.h>\n\n"
            "int main() {\n"
            "    float length, width, area;\n"
            '    printf("Enter length and width: ");\n'
            '    scanf("%f %f", &length, &width);\n'
            "    area = length * width;\n"
            '    printf("Area of rectangle = %.2f", area);\n'
            "    return 0;\n"
            "}"
        )
        return {
            "title": f"{language} Program to Calculate Area of a Rectangle",
            "introduction": f"This {level_line}-level assignment explains a {language} program that calculates the area of a rectangle by using the formula length multiplied by width.",
            "sections": [
                {"heading": "Formula", "content": "Area of rectangle = length × width."},
                {"heading": "Program", "content": code},
                {"heading": "Output", "content": "If length = 8 and width = 4, then the output will be: Area of rectangle = 32."}
            ],
            "conclusion": f"In conclusion, this program helps students understand user input, formula-based calculation, and result display in {language}.",
        }

    if "sum of digits" in lowered:
        code = (
            "#include <stdio.h>\n\n"
            "int main() {\n"
            "    int number, sum = 0;\n"
            '    printf("Enter a number: ");\n'
            '    scanf("%d", &number);\n'
            "    while (number > 0) {\n"
            "        sum = sum + (number % 10);\n"
            "        number = number / 10;\n"
            "    }\n"
            '    printf("Sum of digits = %d", sum);\n'
            "    return 0;\n"
            "}"
            if language == "C"
            else
            'number = int(input("Enter a number: "))\n'
            "sum_digits = 0\n"
            "while number > 0:\n"
            "    sum_digits += number % 10\n"
            "    number //= 10\n"
            'print("Sum of digits =", sum_digits)'
        )
        return {
            "title": f"{language} Program to Find the Sum of Digits of a Number",
            "introduction": f"This {level_line}-level assignment explains a {language} program that finds the sum of the digits of a given number.",
            "sections": [
                {"heading": "Logic", "content": "The last digit is found using modulus operator. Each digit is added to the sum, and the number is reduced by dividing it by 10."},
                {"heading": "Program", "content": code},
                {"heading": "Output", "content": "If the input is 123, then the output will be: Sum of digits = 6."}
            ],
            "conclusion": f"In conclusion, this program demonstrates loops, arithmetic operators, and step-by-step digit processing in {language}.",
        }

    if "even or odd" in lowered or ("even" in lowered and "odd" in lowered):
        code = (
            'number = int(input("Enter a number: "))\n'
            "if number % 2 == 0:\n"
            '    print("Even")\n'
            "else:\n"
            '    print("Odd")'
            if language == "Python"
            else
            "#include <stdio.h>\n\n"
            "int main() {\n"
            "    int number;\n"
            '    printf("Enter a number: ");\n'
            '    scanf("%d", &number);\n'
            "    if (number % 2 == 0) {\n"
            '        printf("Even");\n'
            "    } else {\n"
            '        printf("Odd");\n'
            "    }\n"
            "    return 0;\n"
            "}"
        )
        return {
            "title": f"{language} Program to Check Whether a Number is Even or Odd",
            "introduction": f"This {level_line}-level assignment explains a {language} program that checks whether a number is even or odd using the modulus operator.",
            "sections": [
                {"heading": "Logic", "content": "If a number is completely divisible by 2, it is even. Otherwise, it is odd."},
                {"heading": "Program", "content": code},
                {"heading": "Output", "content": "If the input is 12, the output will be Even. If the input is 9, the output will be Odd."}
            ],
            "conclusion": f"In conclusion, this program is a simple example of using conditions and modulus operator in {language}.",
        }

    return {
        "title": f"{language} Program Assignment",
        "introduction": f"This {level_line}-level assignment explains the given {language} programming question in a simple and structured way.",
        "sections": [
            {"heading": "Understanding the Problem", "content": "First identify the input, the required process, and the expected output."},
            {"heading": "Program Logic", "content": "Write the steps in sequence, use variables properly, and apply the required formula or condition."},
            {"heading": "Result", "content": f"The final {language} program should take input, process the data correctly, and display the required output."}
        ],
        "conclusion": f"In conclusion, this assignment helps students understand the basic flow of problem solving in {language}.",
    }


def build_fallback_assignment(question, level="school"):
    if detect_programming_language(question):
        return build_programming_assignment(question, level)

    answer = fallback_answer(question)
    topic = detect_topic(question).title() or "Assignment Topic"
    level_line = "school-level" if level == "school" else "college-level"
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", answer) if item.strip()]
    intro = sentences[0] if sentences else answer
    body_one = sentences[1] if len(sentences) > 1 else intro
    body_two = " ".join(sentences[2:4]).strip() if len(sentences) > 2 else body_one
    conclusion = sentences[-1] if sentences else answer

    sections = [
        {"heading": "Main Explanation", "content": body_one},
        {"heading": "Important Points", "content": body_two or body_one},
    ]

    return {
        "title": f"{topic} Assignment",
        "introduction": f"This is a simple {level_line} assignment answer on {topic}. {intro}",
        "sections": sections,
        "conclusion": f"In conclusion, {conclusion[0].lower() + conclusion[1:] if len(conclusion) > 1 else conclusion.lower()}",
    }


def get_openai_settings():
    return (
        os.environ.get("OPENAI_API_KEY", "").strip(),
        os.environ.get("OPENAI_MODEL", "gpt-4.1").strip()
    )


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


def normalize_assignment_payload(payload, question, level="school"):
    if not isinstance(payload, dict):
        return build_fallback_assignment(question, level)

    title = clean_text(payload.get("title", "")) or f"{detect_topic(question).title()} Assignment"
    introduction = clean_text(payload.get("introduction", ""))
    conclusion = clean_text(payload.get("conclusion", ""))
    raw_sections = payload.get("headings") or payload.get("sections") or []
    sections = []

    if isinstance(raw_sections, list):
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            heading = clean_text(item.get("heading", ""))
            content = clean_text(item.get("content", ""))
            if heading and content:
                sections.append({"heading": heading, "content": content})

    if not introduction or not sections or not conclusion:
        return build_fallback_assignment(question, level)

    return {
        "title": title,
        "introduction": introduction,
        "sections": sections[:4],
        "conclusion": conclusion,
    }


def flatten_assignment_payload(payload):
    if not payload:
        return ""

    lines = [payload.get("title", "")]
    for section in payload.get("sections", []):
        lines.append(f"{section.get('heading', '')}: {section.get('content', '')}")
    lines.append(payload.get("conclusion", ""))
    return clean_text(" ".join(line for line in lines if line))


def generate_assignment_content(question, level="school"):
    if detect_programming_language(question):
        payload = build_programming_assignment(question, level)
        payload["answer"] = flatten_assignment_payload(payload)
        return payload

    api_key, model = get_openai_settings()
    if not api_key:
        payload = build_fallback_assignment(question, level)
        payload["answer"] = flatten_assignment_payload(payload)
        return payload

    level_prompt = (
        "Use easy student-friendly language suitable for school level."
        if level == "school"
        else "Use clear academic language suitable for college level, but keep it simple."
    )
    prompt = (
        "You are an assignment answer writer for school and college students. "
        "Generate a clean and structured assignment answer in valid JSON. "
        "Keep the output simple, well-structured, and medium length. "
        f"{level_prompt} "
        'Return JSON with keys: title, introduction, headings, conclusion. '
        'The "headings" value must be an array of objects with keys "heading" and "content". '
        "Do not include markdown fences or extra text.\n\n"
        f"Question: {question}"
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
            },
            timeout=45,
        )
        response.raise_for_status()
        raw_text = extract_response_text(response.json())
        parsed = json.loads(raw_text)
        payload = normalize_assignment_payload(parsed, question, level)
        payload["answer"] = flatten_assignment_payload(payload)
        return payload
    except Exception:
        payload = build_fallback_assignment(question, level)
        payload["answer"] = flatten_assignment_payload(payload)
        return payload


def fallback_assignment_questions(summary_text, level="school", count=5):
    text = clean_line_break_text(summary_text)
    if not text:
        return []

    summary = parse_assignment_summary_text(text)
    topics = summary["topics"] or ["Main Topic"]
    main_topic = summary["main_topic"]
    support_topic = summary["support_topic"]
    detail_topic = summary["detail_topic"]
    prompts = []
    primary_topics = topics[: max(4, min(count + 1, 8))]
    for topic in primary_topics:
        prompts.extend(build_question_variants_for_topic(topic, level=level))

    prompts.extend([
        f"Describe the main features of {main_topic}.",
        f"How is {support_topic} connected with {main_topic}?",
        f"Explain the key points related to {detail_topic}.",
        f"Summarize the main ideas covered in {main_topic}.",
    ])

    if level == "college":
        prompts.extend([
            f"Discuss the major concepts covered under {main_topic}.",
            f"Explain the practical importance of {support_topic}.",
            f"Analyze the role of {detail_topic} in the given study material."
        ])
    else:
        prompts.extend([
            f"Write a simple explanation of {main_topic}.",
            f"List the important ideas related to {support_topic}.",
        ])

    cleaned = []
    seen = set()
    for prompt in prompts:
        key = prompt.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(prompt)
        if len(cleaned) >= count:
            break

    if len(cleaned) < count:
        cleaned.extend([
            f"Explain the main theme of {main_topic}.",
            f"Write notes on the important points of {support_topic}.",
            f"Discuss the concepts explained in {detail_topic}.",
        ])
        final_questions = []
        final_seen = set()
        for prompt in cleaned:
            key = prompt.lower()
            if key not in final_seen:
                final_seen.add(key)
                final_questions.append(prompt)
            if len(final_questions) >= count:
                break
        return final_questions
    return cleaned


def build_assignment_question_groups(summary_text, questions, level="school", count=5):
    summary = parse_assignment_summary_text(summary_text)
    topics = [topic for topic in summary.get("topics", []) if topic] or [summary.get("main_topic", "Main Topic")]
    if not questions:
        questions = fallback_assignment_questions(summary_text, level=level, count=count)

    if not topics:
        topics = ["Main Topic"]

    group_count = max(1, min(len(topics), max(2, min(4, count))))
    selected_topics = topics[:group_count]
    grouped = [{"topic": topic, "questions": []} for topic in selected_topics]

    for index, question in enumerate(questions):
        bucket = grouped[index % len(grouped)]
        bucket["questions"].append(question)

    return [group for group in grouped if group["questions"]]


def generate_assignment_questions_from_text(source_text, level="school", count=5):
    source_text = clean_line_break_text(source_text)
    if not source_text:
        return {"summary": "", "questions": [], "question_groups": []}

    api_key, model = get_openai_settings()
    summary_text = generate_assignment_summary_from_text(source_text, level=level)

    if not api_key:
        fallback_questions = fallback_assignment_questions(summary_text, level=level, count=count)
        return {
            "summary": summary_text,
            "questions": fallback_questions,
            "question_groups": build_assignment_question_groups(summary_text, fallback_questions, level=level, count=count)
        }

    summary = parse_assignment_summary_text(summary_text)
    prompt = (
        "You create assignment questions from a structured summary of syllabus or notes. "
        "Generate clean question-only output in valid JSON array format. "
        f"Create {count} assignment questions for {level}-level students. "
        "First understand the main topic, key subtopics, and important ideas from the summary. "
        "Then create meaningful assignment questions based on that summary. "
        "Avoid repetitive keyword-only questions. "
        "Never use labels like Level, Main Topic, Key Ideas, Focus Area, or Important Detail as the question topic. "
        "Keep the questions simple, relevant to the uploaded content, and well structured. "
        'Return only a JSON array of strings like ["Q1 text", "Q2 text"].\n\n'
        f"Detected main topic: {summary['main_topic']}\n"
        f"Detected subtopics: {', '.join(summary['topics'][:6])}\n"
        f"Overview: {summary['overview']}\n\n"
        f"Summary:\n{summary_text[:4000]}"
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
            },
            timeout=45,
        )
        response.raise_for_status()
        raw_text = extract_response_text(response.json())
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            questions = [clean_text(item) for item in parsed if isinstance(item, str) and clean_text(item)]
            final_questions = questions[:count] or fallback_assignment_questions(summary_text, level=level, count=count)
            return {
                "summary": summary_text,
                "questions": final_questions,
                "question_groups": build_assignment_question_groups(summary_text, final_questions, level=level, count=count)
            }
    except Exception:
        pass

    fallback_questions = fallback_assignment_questions(summary_text, level=level, count=count)
    return {
        "summary": summary_text,
        "questions": fallback_questions,
        "question_groups": build_assignment_question_groups(summary_text, fallback_questions, level=level, count=count)
    }


def register_handwriting_font():
    candidates = [
        Path("C:/Windows/Fonts/seguisbi.ttf"),
        Path("C:/Windows/Fonts/segoesc.ttf"),
        Path("C:/Windows/Fonts/LHANDW.TTF"),
        Path("C:/Windows/Fonts/comic.ttf"),
        Path("C:/Windows/Fonts/comici.ttf"),
    ]
    for path in candidates:
        if path.exists():
            font_name = path.stem.replace(" ", "_")
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
            return font_name
    return "Times-Italic"


def register_code_font():
    return "Courier"


def wrap_text(text, font_name, font_size, max_width):
    words = text.split()
    if not words:
        return []

    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if pdfmetrics.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_block(pdf, text_obj, value, font_name, font_size, max_width):
    lines = wrap_text(value, font_name, font_size, max_width)
    for line in lines:
        text_obj.textLine(line)


def remaining_height(cursor_y):
    return cursor_y - BOTTOM_MARGIN


def start_assignment_text(pdf, font_name, font_size=15):
    text = pdf.beginText()
    text.setTextOrigin(LEFT_MARGIN, PAGE_HEIGHT - TOP_MARGIN)
    text.setFont(font_name, font_size)
    text.setLeading(LINE_GAP)
    text.setFillColor(INK_COLOR)
    return text


def new_assignment_page(pdf, font_name):
    pdf.drawText(start_assignment_text(pdf, font_name))
    pdf.showPage()
    draw_notebook_page(pdf)
    return start_assignment_text(pdf, font_name)


def draw_notebook_page(pdf):
    pdf.setStrokeColor(RULE_COLOR)
    y = PAGE_HEIGHT - TOP_MARGIN + 12
    while y > BOTTOM_MARGIN - 8:
        pdf.line(LEFT_MARGIN - 20, y, PAGE_WIDTH - RIGHT_MARGIN + 8, y)
        y -= LINE_GAP

    pdf.setStrokeColor(MARGIN_COLOR)
    margin_x = LEFT_MARGIN - 18
    pdf.line(margin_x, BOTTOM_MARGIN - 8, margin_x, PAGE_HEIGHT - TOP_MARGIN + 18)


def draw_question_page(pdf, font_name, item):
    draw_notebook_page(pdf)
    text = start_assignment_text(pdf, font_name)
    code_font = register_code_font()

    def ensure_space(required_lines=2):
        nonlocal text
        if remaining_height(text.getY()) < required_lines * LINE_GAP:
            pdf.drawText(text)
            pdf.showPage()
            draw_notebook_page(pdf)
            text = start_assignment_text(pdf, font_name)

    ensure_space(3)
    draw_wrapped_block(pdf, text, f"{item['label']}. {item['question']}", font_name, 15, MAX_TEXT_WIDTH)
    text.textLine("")
    draw_wrapped_block(pdf, text, item.get("title", "Assignment Answer"), font_name, 15, MAX_TEXT_WIDTH)

    for section in item.get("sections", []):
        ensure_space(4)
        text.textLine("")
        heading = section.get("heading", "")
        content = section.get("content", "")
        if heading.lower() == "program":
            draw_wrapped_block(pdf, text, f"{heading}:", font_name, 15, MAX_TEXT_WIDTH)
            text.setFont(code_font, 12)
            text.setLeading(16)
            for code_line in content.splitlines():
                ensure_space(2)
                code_text = code_line.rstrip() or " "
                wrapped_code_lines = wrap_text(code_text, code_font, 12, MAX_TEXT_WIDTH - 12) or [" "]
                for wrapped in wrapped_code_lines:
                    text.textLine(f"  {wrapped}")
            text.setFont(font_name, 15)
            text.setLeading(LINE_GAP)
        else:
            draw_wrapped_block(pdf, text, f"{heading}: {content}", font_name, 15, MAX_TEXT_WIDTH)

    ensure_space(3)
    text.textLine("")
    draw_wrapped_block(pdf, text, f"Conclusion: {item.get('conclusion', '')}", font_name, 15, MAX_TEXT_WIDTH)
    pdf.drawText(text)


def build_assignment_items(input_text, level="school"):
    questions = split_questions(input_text)
    if not questions:
        raise ValueError("No questions found in the provided text.")

    items = []
    for index, (_label, question) in enumerate(questions, start=1):
        content = generate_assignment_content(question, level)
        items.append({
            "label": f"Q{index}",
            "question": question,
            "answer": content["answer"],
            "title": content["title"],
            "introduction": content["introduction"],
            "sections": content["sections"],
            "conclusion": content["conclusion"],
            "level": level
        })
    return items


def generate_assignment_pdf_from_items(items, output_target="assignment.pdf"):
    if not items:
        raise ValueError("No assignment items found.")

    pdf = canvas.Canvas(output_target, pagesize=A4)
    font_name = register_handwriting_font()
    pdf.setTitle("AI Assignment Generator")

    for item in items:
        draw_question_page(pdf, font_name, item)
        pdf.showPage()

    pdf.save()
    return output_target


def generate_assignment_pdf(input_text, output_path="assignment.pdf"):
    items = build_assignment_items(input_text)
    output_file = Path(output_path)
    generate_assignment_pdf_from_items(items, str(output_file))
    return output_file


def read_input_text():
    input_path = Path("assignment_input.txt")
    if input_path.exists():
        return input_path.read_text(encoding="utf-8")

    print("Paste assignment questions. Press Ctrl+Z and Enter on Windows when done:")
    lines = []
    while True:
        try:
            lines.append(input())
        except EOFError:
            break
    return "\n".join(lines)


if __name__ == "__main__":
    text = read_input_text()
    pdf_path = generate_assignment_pdf(text, "assignment.pdf")
    print(json.dumps({"status": "ok", "file": str(pdf_path.resolve())}))
