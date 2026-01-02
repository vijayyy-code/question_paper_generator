# six_marks.py
import os
import json
import hashlib
import random
import time
import requests
import re  # Added import for regex
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
HISTORY_FILE = "six_mark_history.json"

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
def extract_relevant_content_six_marks(full_text: str, unit: str, max_chars: int = 4000):
    """
    Extract relevant portion for six-mark questions
    """
    # Get unit name and extract keywords
    unit_lines = unit.split('\n')
    unit_first_line = unit_lines[0].strip()
    unit_name = unit_first_line.split(':')[0].strip().upper()
    
    # Extract meaningful words from unit description
    unit_description = ' '.join(unit_lines).lower()
    words = re.findall(r'\b[a-z]{4,}\b', unit_description)
    
    common_words = {'with', 'this', 'that', 'from', 'have', 'has', 'are', 'was', 'were', 'learning', 'machine'}
    keywords = [word for word in words if word not in common_words][:8]
    
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
# History functions for six marks
# ---------------------------
def load_six_mark_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_six_mark_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def hash_six_mark_question(q):
    return hashlib.sha256(q.strip().lower().encode()).hexdigest()

# ---------------------------
# API Call with Retry Logic
# ---------------------------
@retry_with_exponential_backoff
def make_groq_api_call_six_marks(body: dict):
    """
    Make API call to Groq with built-in retry logic for rate limits.
    """
    resp = requests.post(BASE_URL, headers=HEADERS, json=body, timeout=60)
    if resp.status_code != 200:
        error_msg = resp.json().get("error", {}).get("message", resp.text)
        raise Exception(f"Groq API Error: {resp.status_code} - {error_msg}")
    return resp.json()

# ---------------------------
# Generate six-mark questions
# ---------------------------
def generate_six_mark_questions(full_content: str, units: list, difficulty: str):
    """
    Generate six-mark questions with distribution:
    - Units 1-3: 2 questions each (6 questions)
    - Units 4-5: 1 question each (2 questions)
    Total: 8 questions (Q11-Q18)
    """
    history = load_six_mark_history()
    seed = random.randint(1000, 9999)
    
    all_questions = []
    question_counter = 11  # Start from Q11
    
    # Define distribution: (unit_index, questions_count)
    distribution = [
        (0, 2),  # Unit 1: 2 questions
        (1, 2),  # Unit 2: 2 questions
        (2, 2),  # Unit 3: 2 questions
        (3, 1),  # Unit 4: 1 question
        (4, 1),  # Unit 5: 1 question
    ]
    
    for unit_idx, num_questions in distribution:
        if unit_idx >= len(units):
            continue
            
        unit = units[unit_idx]
        unit_name = unit.split(':')[0].strip()
        unit_history = history.get(unit_name, [])
        
        # Extract relevant content
        relevant_content = extract_relevant_content_six_marks(full_content, unit)
        
        system_msg = "You are an expert university professor creating six-mark questions."
        
        user_prompt = f"""Generate EXACTLY {num_questions} NEW six-mark descriptive questions.

UNIT: {unit}
DIFFICULTY: {difficulty}
MARKS: 6 marks each

RELEVANT CONTENT:
{relevant_content}

Rules:
- Each question should require detailed explanation or step-by-step solution
- Questions should test analytical and application skills
- Make questions challenging for {difficulty} difficulty
- Each question should be unique and not repeated
- Questions should be suitable for 6 marks (approximately 150-200 words answer)
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
            "max_tokens": 512
        }
        
        try:
            # Make API call with retry logic
            data = make_groq_api_call_six_marks(body)
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
            for q in questions:
                if q and q.startswith('Q'):
                    # FIXED: Clean the question text before processing
                    # Remove any malformed numbers after Q (like "Q17.5017")
                    q_clean = q
                    
                    # Check for malformed pattern like "Q17.5017"
                    malformed_pattern = r'^Q\d+\.\d+'
                    if re.match(malformed_pattern, q):
                        # Extract the question text after the number
                        parts = re.split(r'^Q\d+\.\d+', q, 1)
                        if len(parts) > 1 and parts[1].strip():
                            # Keep the question text after cleaning
                            q_clean = f"Q{question_counter}.{parts[1].strip()}"
                        else:
                            q_clean = f"Q{question_counter}."
                    else:
                        # Normal renumbering for well-formed questions
                        q_parts = q.split('.', 1)
                        if len(q_parts) > 1:
                            q_clean = f"Q{question_counter}.{q_parts[1]}"
                        else:
                            q_clean = f"Q{question_counter}."
                    
                    q_hash = hash_six_mark_question(q_clean)
                    if q_hash not in unit_history:
                        all_questions.append(q_clean)
                        unit_history.append(q_hash)
                        question_counter += 1
                        
                        if len([q for _, count in distribution[:unit_idx+1] 
                               for _ in range(count)]) == len(all_questions) - 11:
                            break
            
            # Update history
            history[unit_name] = unit_history
            save_six_mark_history(history)
            
            # Reduced delay between units
            time.sleep(1.5)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error for {unit_name}: {e}")
        except Exception as e:
            # For any other exception, raise it
            raise Exception(f"Error generating six-mark questions for {unit_name}: {str(e)}")
    
    # Ensure we have exactly 8 questions
    if len(all_questions) < 8:
        # Generate remaining questions from any unit
        remaining = 8 - len(all_questions)
        # Simplified fallback
        fallback_questions = [
            f"Q{i}. Explain the key concepts covered in this unit with suitable examples."
            for i in range(question_counter, question_counter + remaining)
        ]
        all_questions.extend(fallback_questions)
    
    return "\n\n".join(all_questions[:8])  # Return exactly 8 questions