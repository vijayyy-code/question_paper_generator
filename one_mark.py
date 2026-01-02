# one_mark.py
import os
import json
import hashlib
import random
import time
import requests
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
HISTORY_FILE = "question_history.json"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# ---------------------------
# Exponential Backoff Retry Decorator
# ---------------------------
def retry_with_exponential_backoff(
    func=None,
    initial_delay: float = 2.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    max_retries: int = 5,
    max_delay: float = 60.0,
    errors_to_retry: tuple = (Exception,)
):
    """
    Exponential backoff decorator for handling API rate limits.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(max_retries + 1):  # +1 for the initial attempt
                try:
                    return func(*args, **kwargs)
                except errors_to_retry as e:
                    # Check if it's a rate limit error (429)
                    is_rate_limit = "429" in str(e) or "Rate limit" in str(e) or "rate limit" in str(e)
                    
                    # If it's the last attempt or not a rate limit error, re-raise
                    if i == max_retries or not is_rate_limit:
                        raise e
                    
                    # Calculate sleep time with jitter
                    sleep_time = delay
                    if jitter:
                        sleep_time = delay * (0.5 + random.random())
                    if sleep_time > max_delay:
                        sleep_time = max_delay
                    
                    print(f"⚠️ Rate limit hit. Retrying in {sleep_time:.2f} seconds... (Attempt {i+1}/{max_retries})")
                    time.sleep(sleep_time)
                    
                    # Increase delay for next retry
                    delay *= exponential_base
            return func(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)

# ---------------------------
# Text processing utilities
# ---------------------------
def extract_relevant_content(full_text: str, unit: str, max_chars: int = 4000):
    """
    Extract only the relevant portion of the book text for the given unit
    to reduce token usage.
    """
    # Get unit name and extract keywords from unit description
    unit_lines = unit.split('\n')
    unit_first_line = unit_lines[0].strip()
    unit_name = unit_first_line.split(':')[0].strip().upper()
    
    # Extract important words from unit description (nouns, proper nouns)
    import re
    
    # Get all words from unit description
    unit_description = ' '.join(unit_lines).lower()
    # Extract meaningful words (3+ characters, not common stop words)
    common_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'has', 'are', 'was', 'were'}
    
    # Use regex to find potential keywords
    words = re.findall(r'\b[a-z]{4,}\b', unit_description)
    keywords = [word for word in words if word not in common_words][:10]  # Take top 10 unique words
    
    # Add unit name as keyword
    keywords.append(unit_name.lower().replace('unit ', ''))
    
    # If still no keywords, use generic ones based on unit number
    if not keywords:
        generic_keywords = {
            "I": ["introduction", "basics", "fundamentals", "overview"],
            "II": ["supervised", "regression", "classification"],
            "III": ["unsupervised", "clustering", "dimensionality"],
            "IV": ["neural", "network", "kernel", "svm"],
            "V": ["probabilistic", "bayesian", "markov", "graphical"]
        }
        unit_num = unit_name.replace("UNIT", "").strip()
        keywords = generic_keywords.get(unit_num, [unit_name.lower()])
    
    # Find sentences containing keywords
    sentences = full_text.split('.')
    relevant_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(keyword.lower() in sentence_lower for keyword in keywords):
            relevant_sentences.append(sentence.strip())
        
        # Limit total characters
        if sum(len(s) for s in relevant_sentences) > max_chars:
            break
    
    if not relevant_sentences:
        # If no keyword matches, take first 3000 characters
        return full_text[:3000]
    
    return '. '.join(relevant_sentences)[:max_chars]

# ---------------------------
# History functions
# ---------------------------
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def hash_question(q):
    return hashlib.sha256(q.strip().lower().encode()).hexdigest()

# ---------------------------
# API Call with Retry Logic
# ---------------------------
@retry_with_exponential_backoff
def make_groq_api_call(body: dict):
    """
    Make API call to Groq with built-in retry logic for rate limits.
    """
    resp = requests.post(BASE_URL, headers=HEADERS, json=body, timeout=60)
    if resp.status_code != 200:
        error_msg = resp.json().get("error", {}).get("message", resp.text)
        raise Exception(f"Groq API Error: {resp.status_code} - {error_msg}")
    return resp.json()

# ---------------------------
# Generate one-mark questions per unit
# ---------------------------
def generate_one_mark_questions(full_content: str, unit: str, questions_per_unit: int, difficulty: str, start_qno: int = 1):
    history = load_history()
    seed = random.randint(1000, 9999)
    
    # Extract only relevant content for this unit
    relevant_content = extract_relevant_content(full_content, unit)
    
    # Get unit-specific history
    unit_name = unit.split(':')[0].strip()
    unit_history = history.get(unit_name, [])
    
    system_msg = "You are an expert university question paper setter."

    user_prompt = f"""Generate EXACTLY {questions_per_unit} NEW one-mark MCQs.

UNIT: {unit}
DIFFICULTY: {difficulty}

RELEVANT CONTENT (for this unit only):
{relevant_content}

Rules:
- Each question must have 4 options (A–D)
- Only generate the question and options, do NOT include the answers
- Each question should be unique and phrased differently
- Strictly syllabus-based
- Ensure questions are not repeated from previous sessions
- Format strictly:

Q1. Question?
A. Option
B. Option
C. Option
D. Option

Q2. Question?
A. Option
B. Option
C. Option
D. Option

[Seed: {seed}]
"""

    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512
    }

    try:
        # Make API call with retry logic
        data = make_groq_api_call(body)
        raw_text = data["choices"][0]["message"]["content"]
        
        raw_questions = raw_text.strip().split("\n\n")
        final_questions = []
        new_hashes = []
        
        for q in raw_questions:
            if q.strip() and "Q" in q[:10]:  # Filter for actual questions
                q_hash = hash_question(q)
                # Check both unit history and global uniqueness
                if q_hash not in unit_history:
                    final_questions.append(q)
                    new_hashes.append(q_hash)
                    unit_history.append(q_hash)
            if len(final_questions) == questions_per_unit:
                break
        
        if final_questions:
            # Update history
            history[unit_name] = unit_history
            save_history(history)
        
        # Reduced delay to 1.5 seconds between units
        time.sleep(1.5)
        
        if not final_questions:
            return f"No new questions generated for {unit}. All were duplicates."
        
        # Renumber questions sequentially
        questions_text = ""
        for i, q in enumerate(final_questions, start=start_qno):
            # Extract question text (removing old Q1., Q2., etc.)
            lines = q.split('\n')
            question_lines = []
            for line in lines:
                if line.strip().startswith('Q'):
                    # Replace Q1., Q2., etc. with new number
                    parts = line.split('.', 1)
                    if len(parts) > 1:
                        question_lines.append(f"Q{i}.{parts[1]}")
                    else:
                        question_lines.append(f"Q{i}.")
                else:
                    question_lines.append(line)
            questions_text += '\n'.join(question_lines) + '\n\n'
        
        return questions_text.strip()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")
    except Exception as e:
        # For any other exception, raise it
        raise Exception(f"Error generating questions for {unit_name}: {str(e)}")