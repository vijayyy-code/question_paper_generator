import streamlit as st
from fpdf import FPDF
import os
import re

class QuestionPaper(FPDF):
    def header(self):
        self.set_y(8)
        self.set_font("Helvetica", '', 10)
        self.cell(0, 10, f'{self.page_no()}', align='C')
        self.set_x(-40) 
        self.cell(30, 10, 'EBCS22E24', align='R')
        self.ln(10)

    def header_layout(self, sub_code, sub_name, session):
        # --- LOGO SECTION ---
        logo_path = 'image.png' 
        if os.path.exists(logo_path):
            self.image(logo_path, 12, 18, 22)

        self.set_y(15)
        self.set_font("Helvetica", 'B', 12)
        self.cell(0, 6, "Dr. M.G.R.", align='C', ln=True)
        self.set_font("Helvetica", 'B', 14)
        self.cell(0, 7, "EDUCATIONAL AND RESEARCH INSTITUTE", align='C', ln=True)
        self.set_font("Helvetica", '', 10)
        self.cell(0, 5, "DEEMED TO BE UNIVERSITY", align='C', ln=True)
        self.cell(0, 5, "(University with Special Autonomy Status)", align='C', ln=True)
        
        self.ln(4)
        self.set_font("Helvetica", 'B', 11)
        self.cell(0, 6, f"B.TECH DEGREE EXAMINATIONS, {session}", align='C', ln=True)
        self.cell(0, 6, sub_code, align='C', ln=True)
        self.cell(0, 6, sub_name.upper(), align='C', ln=True)
        
        self.ln(3)
        self.set_font("Helvetica", 'B', 10)
        self.cell(0, 5, "REGISTER NUMBER", align='C', ln=True)
        
        start_x = 70 
        y_box = self.get_y() + 1
        for i in range(10):
            self.rect(start_x + (i * 7), y_box, 6, 6)
        
        self.ln(10)
        self.set_font("Helvetica", 'B', 10)
        self.cell(95, 5, "Time: Three Hours", align='L')
        self.set_x(105)
        self.cell(95, 5, "Maximum Marks: 100", align='R')
        self.ln(6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

def clean_text(text):
    replacements = {
        "Δ": "Delta", "Σ": "Sigma", "Ω": "Omega", "Θ": "Theta", "π": "pi", 
        "α": "alpha", "β": "beta", "γ": "gamma", "λ": "lambda", "μ": "mu",
        "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...",
        "±": "+/-", "×": "x", "÷": "/", "≈": "~", "≠": "!=", "≤": "<=", "≥": ">="
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    
    lines = text.split('\n')
    filtered = []
    for line in lines:
        clean = line.strip()
        if not clean: continue
        
        if (any(keyword in clean.upper() for keyword in ["UNIT", "PAGE", "TOTAL HOURS"]) or
            re.match(r'^\d+\s+EBCS22E24$', clean)):
            continue
        
        clean = clean.replace("7780.", "")
        clean = re.sub(r'^\d+\s+EBCS22E24\s*', '', clean)
        clean = re.sub(r'^[Qq]\d+[\.\s]*', '', clean)
        clean = re.sub(r'\s*[\(\[]\s*\d+\s*(?:marks?\s*)?[\)\]]\s*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s*[\(\[]\s*\d+\s*(?:marks?\s*)?[\)\]]', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'(This question requires|Note:|Expected).*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        if clean:
            filtered.append(clean)
    return filtered

def generate_pdf(sub_code, sub_name, session, content):
    pdf = QuestionPaper()
    pdf.alias_nb_pages() 
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.header_layout(sub_code, sub_name, session)
    
    lines = clean_text(content)
    pA, pB, pC = 1, 11, 19
    current_part = None

    for line in lines:
        upper_line = line.upper()
        
        # Section Detection
        if "PART - A" in upper_line or "PART A" in upper_line:
            current_part = "A"; pdf.ln(2)
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(0, 8, "PART - A (10 x 1 = 10 Marks)", align='C', ln=True)
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(0, 6, "Answer ALL Questions", align='C', ln=True); pdf.ln(2)
            continue
        elif "PART - B" in upper_line or "PART B" in upper_line:
            current_part = "B"; pdf.ln(4)
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(0, 8, "PART - B (5 x 6 = 30 Marks)", align='C', ln=True)
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(0, 6, "Answer ANY FIVE Questions", align='C', ln=True); pdf.ln(2)
            continue
        elif "PART - C" in upper_line or "PART C" in upper_line:
            current_part = "C"; pdf.ln(4)
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(0, 8, "PART - C (5 x 12 = 60 Marks)", align='C', ln=True)
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(0, 6, "Answer ALL Questions", align='C', ln=True); pdf.ln(2)
            continue

        pdf.set_font("Helvetica", '', 10)
        
        if current_part == "A":
            # Detection for options starting with a, b, c, d or numbers 1, 2, 3, 4
            # matches "a.", "(a)", "a)", "1.", etc.
            if re.match(r'^[a-dA-D1-4][\.\)\s]', line) or re.match(r'^\([a-dA-D1-4]\)', line):
                pdf.set_x(25) # More indentation for options
                pdf.multi_cell(0, 5, line)
            else:
                pdf.ln(1)
                pdf.multi_cell(0, 5, f"Q{pA}. {line}")
                pA += 1
            pdf.ln(1)
            
        elif current_part == "B":
            pdf.multi_cell(0, 5, f"Q{pB}. {line}")
            pB += 1; pdf.ln(2)
            
        elif current_part == "C":
            if "(OR)" in upper_line:
                pdf.ln(1)
                pdf.set_font("Helvetica", 'B', 10)
                pdf.cell(0, 6, "(OR)", align='C', ln=True)
                pdf.set_font("Helvetica", '', 10)
            else:
                pdf.multi_cell(0, 5, f"Q{pC}. {line}")
                pC += 1
            pdf.ln(2)

    return bytes(pdf.output())

# Streamlit UI
st.set_page_config(page_title="MGR QP Formatter", layout="centered")
st.title("📝 MGR Professional QP Formatter")

col1, col2 = st.columns(2)
with col1:
    s_name = st.text_input("Subject Name", "MACHINE LEARNING")
    sess = st.text_input("Exam Session", "NOV/DEC-2025")
with col2:
    s_code = st.text_input("Subject Code", "EBCS22E24")

raw_text = st.text_area("Paste Content Here:", height=400)

if st.button("GENERATE FINAL PDF"):
    if raw_text:
        try:
            pdf_bytes = generate_pdf(s_code, s_name, sess, raw_text)
            st.success("✅ PDF Generated with a/b/c/d Option Formatting!")
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"{s_code}_Final.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"An error occurred: {e}")