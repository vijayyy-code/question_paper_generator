# app.py
import streamlit as st
from PyPDF2 import PdfReader
import docx
import io
import re
from one_mark import generate_one_mark_questions
from six_marks import generate_six_mark_questions
from twelve_marks import generate_twelve_mark_questions

st.set_page_config(page_title="Question Paper Generator", layout="wide")
st.title("📘 Question Paper Generator")

# ---------------------------
# Upload Files
# ---------------------------
col1, col2 = st.columns(2)

with col1:
    syllabus_file = st.file_uploader("Upload Syllabus", 
                                     type=["pdf", "txt", "docx"],
                                     key="syllabus")
    
with col2:
    book_file = st.file_uploader("Upload Reference Material", 
                                 type=["pdf", "txt", "docx"],
                                 key="book")

# ---------------------------
# Configuration
# ---------------------------
col3, col4 = st.columns(2)
with col3:
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
with col4:
    questions_per_unit = st.number_input("MCQs per Unit", min_value=1, max_value=10, value=2)

# ---------------------------
# Helper function to extract text
# ---------------------------
def extract_text_from_file(uploaded_file):
    """Extract text from PDF, TXT, or DOCX files."""
    if uploaded_file is None:
        return ""
    
    file_type = uploaded_file.type.lower()
    content = uploaded_file.read()
    
    try:
        if file_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
            
        elif file_type == "text/plain":
            return content.decode("utf-8")
            
        elif "word" in file_type or uploaded_file.name.endswith('.docx'):
            doc = docx.Document(io.BytesIO(content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
            
        else:
            st.error(f"Unsupported file type: {uploaded_file.type}")
            return ""
            
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return ""

# ---------------------------
# Generate Question Paper
# ---------------------------
if syllabus_file and book_file and st.button("Generate Complete Question Paper", type="primary"):
    with st.spinner("Processing files..."):
        # Extract text from files
        syllabus_text = extract_text_from_file(syllabus_file)
        book_text = extract_text_from_file(book_file)
    
    if not syllabus_text or not book_text:
        st.error("Could not extract text from files. Please check file formats.")
        st.stop()
    
    st.success("Content extracted successfully!")
    
    # Split syllabus into units - IMPROVED PARSING
    lines = syllabus_text.splitlines()
    units = []
    current_unit = ""
    
    # Better regex pattern for detecting units
    unit_patterns = [
        r"UNIT\s+[IVXLCDM]+",  # UNIT I, UNIT II, etc.
        r"Unit\s+[IVXLCDM]+",  # Unit I, Unit II, etc.
        r"UNIT\s+\d+",         # UNIT 1, UNIT 2, etc.
        r"Unit\s+\d+"          # Unit 1, Unit 2, etc.
    ]
    
    for line in lines:
        line_upper = line.upper()
        is_unit_line = False
        
        # Check if line contains any unit pattern
        for pattern in unit_patterns:
            if re.search(pattern, line_upper):
                is_unit_line = True
                break
        
        # Also check for common unit indicators
        if not is_unit_line and ("UNIT" in line_upper or "Unit" in line_upper):
            # Check if followed by Roman numeral or number
            if re.search(r"UNIT.*[IVXLCDM1-9]", line_upper):
                is_unit_line = True
        
        if is_unit_line:
            if current_unit:
                units.append(current_unit.strip())
            current_unit = line.strip()
        elif current_unit and line.strip():
            # Skip lines that are just hours (e.g., "9 Hrs", "9 Hours")
            if not re.search(r"^\d+\s*(Hrs|Hours|hrs|hours)$", line.strip()):
                current_unit += " " + line.strip()
    
    if current_unit:
        units.append(current_unit.strip())
    
    # Clean up units - remove excessive whitespace
    cleaned_units = []
    for unit in units:
        # Remove multiple spaces
        unit = re.sub(r'\s+', ' ', unit)
        # Remove trailing/leading whitespace
        unit = unit.strip()
        if unit:  # Only add non-empty units
            cleaned_units.append(unit)
    
    units = cleaned_units
    
    # If no units found, create default units
    if not units:
        units = [
            "UNIT I: INTRODUCTION TO COMPILER DESIGN",
            "UNIT II: LEXICAL ANALYSIS AND SYNTAX ANALYSIS", 
            "UNIT III: INTERMEDIATE CODE GENERATION",
            "UNIT IV: CODE OPTIMIZATION",
            "UNIT V: CODE GENERATION AND ERROR HANDLING"
        ]
        st.warning("No units detected in syllabus. Using default unit names.")
    
    # Display detected units
    st.write(f"**Found {len(units)} units**")
    with st.expander("View Detected Units", expanded=False):
        for i, unit in enumerate(units, 1):
            st.write(f"**Unit {i}:** {unit[:100]}...")
    
    # Initialize tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Complete Paper", "🔤 One-Mark MCQs", "📚 Six-Mark Questions", "📖 Twelve-Mark Questions"])
    
    # Generate One-Mark Questions (Q1-Q10)
    with tab1, st.spinner("Generating one-mark questions..."):
        all_one_mark_questions = []
        question_counter = 1
        
        for i, unit in enumerate(units):
            try:
                questions = generate_one_mark_questions(
                    book_text, 
                    unit, 
                    questions_per_unit, 
                    difficulty,
                    start_qno=question_counter
                )
                if "No new questions" not in questions:
                    all_one_mark_questions.append((unit, questions))
                    question_counter += questions_per_unit
            except Exception as e:
                st.error(f"Error generating one-mark questions for {unit}: {str(e)[:100]}...")
                # Fallback
                fallback = f"**{unit}**\n\n"
                for q in range(questions_per_unit):
                    fallback += f"Q{question_counter}. [Question generation failed - please try again]\nA. Option A\nB. Option B\nC. Option C\nD. Option D\n\n"
                    question_counter += 1
                all_one_mark_questions.append((unit, fallback))
    
    # Generate Six-Mark Questions (Q11-Q18)
    with tab1, st.spinner("Generating six-mark questions..."):
        try:
            six_mark_questions = generate_six_mark_questions(book_text, units, difficulty)
        except Exception as e:
            st.error(f"Error generating six-mark questions: {str(e)[:100]}...")
            # Fallback six-mark questions
            six_mark_questions = ""
            for i in range(11, 19):
                six_mark_questions += f"Q{i}. Explain the key concepts from the syllabus with examples.\n\n"
    
    # Generate Twelve-Mark Questions (Q19-Q28)
    with tab1, st.spinner("Generating twelve-mark questions..."):
        try:
            twelve_mark_questions = generate_twelve_mark_questions(book_text, units, difficulty)
        except Exception as e:
            st.error(f"Error generating twelve-mark questions: {str(e)[:100]}...")
            # Fallback twelve-mark questions
            twelve_mark_questions = ""
            for i in range(19, 29):
                twelve_mark_questions += f"Q{i}. Discuss in detail the important concepts and applications from the syllabus with comprehensive analysis and examples.\n\n"
    
    # Display Complete Paper in Tab 1
    with tab1:
        st.subheader("📝 Complete Question Paper")
        
        full_paper = "**PART A - One Mark Questions (10 x 1 = 10 Marks)**\n\n"
        
        # Add one-mark questions
        for unit, questions in all_one_mark_questions:
            unit_name = unit.split(':')[0] if ':' in unit else unit
            full_paper += f"**{unit_name}**\n"
            full_paper += questions + "\n\n"
        
        full_paper += "\n**PART B - Six Mark Questions (8 x 6 = 48 Marks)**\n\n"
        full_paper += six_mark_questions
        
        full_paper += "\n**PART C - Twelve Mark Questions (10 x 12 = 120 Marks)**\n\n"
        full_paper += twelve_mark_questions
        
        st.text_area("Full Question Paper", full_paper, height=1000, key="full_paper")
        
        # Download button
        st.download_button(
            label="📥 Download Question Paper",
            data=full_paper,
            file_name="question_paper.txt",
            mime="text/plain"
        )
    
    # Display One-Mark MCQs in Tab 2
    with tab2:
        st.subheader("🔤 One-Mark Multiple Choice Questions")
        
        for unit, questions in all_one_mark_questions:
            unit_display = unit.split(':')[0] if ':' in unit else unit
            with st.expander(f"{unit_display}", expanded=True):
                st.text_area(f"Questions", questions, height=200, key=f"one_mark_{unit}")
    
    # Display Six-Mark Questions in Tab 3
    with tab3:
        st.subheader("📚 Six-Mark Descriptive Questions")
        st.info("Questions 11-18: First 3 units (2 questions each), Last 2 units (1 question each)")
        
        st.text_area("Six-Mark Questions (Q11-Q18)", six_mark_questions, height=400, key="six_marks")
    
    # Display Twelve-Mark Questions in Tab 4
    with tab4:
        st.subheader("📖 Twelve-Mark Descriptive Questions")
        st.info("Questions 19-28: Each unit has 2 questions (Total: 10 questions)")
        
        st.text_area("Twelve-Mark Questions (Q19-Q28)", twelve_mark_questions, height=500, key="twelve_marks")
        
        # Show distribution
        st.markdown("---")
        st.subheader("📊 Question Distribution")
        
        dist_data = {
            "Unit": ["I", "II", "III", "IV", "V"],
            "MCQs (1 mark)": [questions_per_unit] * 5,
            "Descriptive (6 marks)": [2, 2, 2, 1, 1],
            "Descriptive (12 marks)": [2, 2, 2, 2, 2]
        }
        
        st.table(dist_data)
        
        total_marks = (len(units) * questions_per_unit * 1) + (8 * 6) + (10 * 12)
        st.success(f"**Total Marks: {total_marks}** (MCQs: {len(units)*questions_per_unit}, 6-mark: 48, 12-mark: 120)")