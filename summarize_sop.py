import os
import json
from docx import Document
from docxtpl import DocxTemplate
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
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
1. "PROCESS OVERVIEW": Must be a nested JSON object with keys "System", "Trigger", "TAT", "Accuracy". Extract these if they exist in the DOCX; otherwise, set them to null. Use key: `process_overview`
2. "1. REQUEST VALIDATION": A short summary string or array of bullet points. Use key: `request_validation`
3. "2. PAYROLL SETUP": A short summary string or array of bullet points. Use key: `payroll_setup`
4. "3. CONFIGURATION": A short summary string or array of bullet points. Use key: `configuration`
5. "4. PROCESSING": A short summary string or array of bullet points. Use key: `processing`
6. "5. QUALITY CHECK (CRITICAL)": A short summary string or array of bullet points. Use key: `quality_check`
7. "6. ADMIN FEE VALIDATION": A short summary string or array of bullet points. Use key: `admin_fee_validation`
8. "7. APPROVAL FLOW": A short summary string or array of bullet points. Use key: `approval_flow`
9. "8. FINALIZATION": A short summary string or array of bullet points. Use key: `finalization`
10. "SPECIAL CASES (IF NEEDED)": A short summary string or array of bullet points. Use key: `special_cases`
11. "QUICK CHECKLIST": Synthesize a high-level array of checklist items based on the overall document steps. Use key: `quick_checklist`
12. "FULL SOP LINK": Extract if present, else null. Use key: `full_sop_link`
13. "Frequency": Extract if present, else null. Use key: `frequency`
14. "CONTACT": Extract if present, else null. Use key: `contact`

Ensure the output is strictly in JSON format using the keys specified above (e.g. `request_validation`, not `1. REQUEST VALIDATION`). Note that if information like TAT, Accuracy, Frequency, or Contact is missing from the DOCX source text, you must output null for them.
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

def save_as_docx(data, template_path, output_path):
    """Uses docxtpl to fill a docx template with dictionary data."""
    doc = DocxTemplate(template_path)
    
    # Render the template with the provided context dictionary
    doc.render(data)
    
    # Save the populated docx to the output path
    doc.save(output_path)
    print(f"Saved DOCX filled template to {output_path}")

def save_as_html(data, template_path, output_path):
    """Uses jinja2 to fill an HTML template with dictionary data."""
    template_dir, template_name = os.path.split(template_path)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    
    html_out = template.render(data)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_out)
    print(f"Saved HTML filled template to {output_path}")

def save_as_pdf(html_path, pdf_path):
    """Uses playwright to convert an HTML file to PDF."""
    # Convert absolute or relative HTML path to a file:// URI
    file_uri = f"file:///{os.path.abspath(html_path).replace(chr(92), '/')}"
    
    with sync_playwright() as p:
        # Launch headless chromium
        browser = p.chromium.launch()
        page = browser.new_page()
        # Navigate to the local HTML file
        page.goto(file_uri)
        # Wait for fonts/styles to load (if any network resources are used)
        page.wait_for_load_state("networkidle")
        
        # Save as PDF (print background to keep colors)
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()
    print(f"Saved PDF to {pdf_path}")


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
    
    # Use standard templates for standalone run
    template_docx = r"c:\Users\Intern\summary & chatbot\input\template.docx"
    output_docx = r"c:\Users\Intern\summary & chatbot\output\summary.docx"
    if os.path.exists(template_docx):
        save_as_docx(summary_data, template_docx, output_docx)
    else:
        print(f"Template not found at {template_docx}, skipping save_as_docx")
        
    template_html = r"c:\Users\Intern\summary & chatbot\input\template.html"
    output_html = r"c:\Users\Intern\summary & chatbot\output\summary.html"
    output_pdf = r"c:\Users\Intern\summary & chatbot\output\summary.pdf"
    
    if os.path.exists(template_html):
        save_as_html(summary_data, template_html, output_html)
        # Also generate PDF
        save_as_pdf(output_html, output_pdf)
    else:
        print(f"HTML Template not found at {template_html}, skipping save_as_html and save_as_pdf")
        
    print("Done!")
