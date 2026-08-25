import os
import json
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (like OPENAI_API_KEY) from .env file
load_dotenv()

def read_docx(file_path):
    """Reads text from a .docx file."""
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def generate_summary(text):
    """Uses OpenAI API to summarize the text based on specific headers."""
    client = OpenAI() # Assumes OPENAI_API_KEY is in environment

    system_prompt = """
You are an expert payroll processor and technical writer. 
Your task is to read the provided SOP document and write a concise, high-level summary for each of the following specific headers. 
DO NOT copy and paste exact text or step-by-step instructions from the document. Instead, synthesize the information into brief summaries or short bullet points for each section.

Headers to summarize and expected format:
1. "PROCESS OVERVIEW": Must be a nested JSON object with keys "System", "Trigger", "TAT", "Accuracy". Extract these if they exist in the DOCX; otherwise, set them to null.
2. "1. REQUEST VALIDATION": A short summary string or array of bullet points.
3. "2. PAYROLL SETUP": A short summary string or array of bullet points.
4. "3. CONFIGURATION": A short summary string or array of bullet points.
5. "4. PROCESSING": A short summary string or array of bullet points.
6. "5. QUALITY CHECK (CRITICAL)": A short summary string or array of bullet points.
7. "6. ADMIN FEE VALIDATION": A short summary string or array of bullet points.
8. "7. APPROVAL FLOW": A short summary string or array of bullet points.
9. "8. FINALIZATION": A short summary string or array of bullet points.
10. "SPECIAL CASES (IF NEEDED)": A short summary string or array of bullet points.
11. "QUICK CHECKLIST": Synthesize a high-level array of checklist items based on the overall document steps.
12. "FULL SOP LINK": Extract if present, else null.
13. "Frequency": Extract if present, else null.
14. "CONTACT": Extract if present, else null.

Ensure the output is strictly in JSON format. The keys MUST be exactly as listed above. Note that if information like TAT, Accuracy, Frequency, or Contact is missing from the DOCX source text, you must output null for them.
"""

    response = client.chat.completions.create(
        model="gpt-4o", # You can change this to gpt-3.5-turbo if needed
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the SOP document text:\n\n{text}"}
        ],
        response_format={ "type": "json_object" },
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)

def save_as_json(data, output_path):
    """Saves a dictionary to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"Saved JSON summary to {output_path}")

def save_as_txt(data, output_path):
    """Saves a dictionary to a formatted TXT file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for key, value in data.items():
            f.write(f"{key}\n")
            f.write("-" * len(key) + "\n")
            if isinstance(value, list):
                for item in value:
                    f.write(f"- {item}\n")
            elif isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    f.write(f"  * {sub_key}: {sub_val}\n")
            else:
                f.write(f"{value}\n")
            f.write("\n")
    print(f"Saved TXT summary to {output_path}")

if __name__ == "__main__":
    input_docx = r"c:\Users\Intern\summary & chatbot\input\SOP_Emplova_Off-cycle Payroll Process_V1.1 (1).docx"
    output_json = r"c:\Users\Intern\summary & chatbot\output\summary.json"
    output_txt = r"c:\Users\Intern\summary & chatbot\output\summary.txt"

    print("Reading DOCX file...")
    try:
        document_text = read_docx(input_docx)
    except Exception as e:
        print(f"Error reading docx: {e}")
        exit(1)

    print("Generating summary via OpenAI...")
    try:
        summary_data = generate_summary(document_text)
    except Exception as e:
        print(f"Error generating summary: {e}")
        exit(1)

    print("Saving outputs...")
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    save_as_json(summary_data, output_json)
    save_as_txt(summary_data, output_txt)
    print("Done!")
