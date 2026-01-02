# twelve_marks.py
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
HISTORY_FILE = "twelve_mark_history.json"

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
def extract_relevant_content_twelve_marks(full_text: str, unit: str, max_chars: int = 4000):
    """
    Extract relevant portion for twelve-mark questions
    """
    # Get unit name and extract keywords
    unit_lines = unit.split('\n')
    unit_first_line = unit_lines[0].strip()
    unit_name = unit_first_line.split(':')[0].strip().upper()
    
    import re
    
    # Extract meaningful words from unit description
    unit_description = ' '.join(unit_lines).lower()
    words = re.findall(r'\b[a-z]{4,}\b', unit_description)
    
    common_words = {'with', 'this', 'that', 'from', 'have', 'has', 'are', 'was', 'were', 'learning', 'machine', 'hours', 'hrs'}
    keywords = [word for word in words if word not in common_words][:10]
    
    keywords.append(unit_name.lower().replace('unit ', ''))
    
    # Find sentences containing keywords
    sentences = full_text.split('.')
    relevant_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(keyword.lower() in sentence_lower for keyword in keywords):
            relevant_sentences.append(sentence.strip())
        
        if sum(len(s) for s in relevant_sentences) > max_chars:
            break
    
    if not relevant_sentences:
        return full_text[:3000]
    
    return '. '.join(relevant_sentences)[:max_chars]

# ---------------------------
# History functions for twelve marks
# ---------------------------
def load_twelve_mark_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_twelve_mark_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def hash_twelve_mark_question(q):
    return hashlib.sha256(q.strip().lower().encode()).hexdigest()

# ---------------------------
# API Call with Retry Logic
# ---------------------------
@retry_with_exponential_backoff
def make_groq_api_call_twelve_marks(body: dict):
    """
    Make API call to Groq with built-in retry logic for rate limits.
    """
    resp = requests.post(BASE_URL, headers=HEADERS, json=body, timeout=60)
    if resp.status_code != 200:
        error_msg = resp.json().get("error", {}).get("message", resp.text)
        raise Exception(f"Groq API Error: {resp.status_code} - {error_msg}")
    return resp.json()

# ---------------------------
# Generate twelve-mark questions
# ---------------------------
def generate_twelve_mark_questions(full_content: str, units: list, difficulty: str):
    """
    Generate twelve-mark questions with distribution:
    - Each unit: 2 questions each
    - Total: 10 questions (Q19-Q28)
    """
    history = load_twelve_mark_history()
    seed = random.randint(1000, 9999)
    
    all_questions = []
    question_counter = 19  # Start from Q19
    
    # All units get 2 questions each
    for unit_idx, unit in enumerate(units):
        unit_name = unit.split(':')[0].strip()
        unit_history = history.get(unit_name, [])
        
        # Extract relevant content
        relevant_content = extract_relevant_content_twelve_marks(full_content, unit)
        
        system_msg = "You are an expert university professor creating twelve-mark questions."
        
        user_prompt = f"""Generate EXACTLY 2 NEW twelve-mark descriptive questions.

UNIT: {unit}
DIFFICULTY: {difficulty}
MARKS: 12 marks each

RELEVANT CONTENT:
{relevant_content}

Rules:
- Each question should require comprehensive explanation, analysis, and application
- Questions should test in-depth understanding, critical thinking, and problem-solving skills
- Make questions challenging for {difficulty} difficulty
- Each question should be unique and not repeated
- Questions should be suitable for 12 marks (approximately 250-300 words answer)
- Questions should cover different aspects/topics of the unit
- Format strictly as:
Q[number]. [Question text]

[Seed: {seed}]
"""
        
        body = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 600
        }
        
        try:
            # Make API call with retry logic
            data = make_groq_api_call_twelve_marks(body)
            raw_text = data["choices"][0]["message"]["content"]
            
            # Split questions
            questions = []
            lines = raw_text.strip().split('\n')
            current_question = ""
            
            for line in lines:
                if line.strip().startswith('Q'):
                    if current_question:
                        questions.append(current_question.strip())
                    current_question = line.strip()
                elif current_question:
                    current_question += " " + line.strip()
            
            if current_question:
                questions.append(current_question.strip())
            
            # Filter and add to final list
            questions_added = 0
            for q in questions:
                if q and q.startswith('Q') and questions_added < 2:
                    q_hash = hash_twelve_mark_question(q)
                    if q_hash not in unit_history:
                        # Renumber question
                        q_text = q.split('.', 1)
                        if len(q_text) > 1:
                            q = f"Q{question_counter}.{q_text[1]}"
                        else:
                            q = f"Q{question_counter}."
                        
                        all_questions.append(q)
                        unit_history.append(q_hash)
                        question_counter += 1
                        questions_added += 1
            
            # Update history
            history[unit_name] = unit_history
            save_twelve_mark_history(history)
            
            # Delay between units
            time.sleep(1.5)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error for {unit_name}: {e}")
        except Exception as e:
            raise Exception(f"Error generating twelve-mark questions for {unit_name}: {str(e)}")
    
    # Ensure we have exactly 10 questions
    if len(all_questions) < 10:
        remaining = 10 - len(all_questions)
        fallback_questions = [
            f"Q{i}. Discuss in detail the important concepts and applications from this unit with appropriate examples and analysis."
            for i in range(question_counter, question_counter + remaining)
        ]
        all_questions.extend(fallback_questions)
    
    return "\n\n".join(all_questions[:10])  # Return exactly 10 questions