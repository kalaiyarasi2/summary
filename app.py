import os
import shutil
import zipfile
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from summarize_sop import read_docx, generate_summary, save_as_json, save_as_txt, save_as_docx, save_as_html, save_as_pdf

app = FastAPI(
    title="SOP Summarizer API",
    description="Upload a DOCX file to get a structured JSON and TXT summary."
)

@app.get("/")
def read_root():
    # Redirect to the Swagger UI so users don't see a 404 at the root
    return RedirectResponse(url="/docs")

@app.post("/summarize")
def summarize_document(file: UploadFile = File(...)):
    # Create output directory based on the input filename
    base_name = os.path.splitext(file.filename)[0]
    output_dir = os.path.join("output", base_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # Temporary paths
    temp_docx_path = f"temp_{file.filename}"
    extracted_text_path = os.path.join(output_dir, "extracted_text.txt")
    output_json_path = os.path.join(output_dir, "summary.json")
    output_txt_path = os.path.join(output_dir, "summary.txt")
    output_docx_path = os.path.join(output_dir, "summary_filled.docx")
    output_html_path = os.path.join(output_dir, "summary.html")
    output_pdf_path = os.path.join(output_dir, "summary.pdf")
    output_zip_path = os.path.join("output", f"{base_name}_summary_files.zip")
    
    # Path to the base templates
    template_docx = os.path.join("input", "template_grid.docx")
    template_html = os.path.join("input", "template.html")
    
    try:
        # Save uploaded DOCX file temporarily
        with open(temp_docx_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Read DOCX
        document_text = read_docx(temp_docx_path)
        
        # Save extracted text
        with open(extracted_text_path, "w", encoding="utf-8") as f:
            f.write(document_text)
        
        # 2. Generate Summary via OpenAI
        summary_data = generate_summary(document_text)
        
        # 3. Save as JSON, TXT, DOCX, and HTML
        save_as_json(summary_data, output_json_path)
        save_as_txt(summary_data, output_txt_path)
        
        has_docx = False
        if os.path.exists(template_docx):
            save_as_docx(summary_data, template_docx, output_docx_path)
            has_docx = True
            
        has_html = False
        has_pdf = False
        if os.path.exists(template_html):
            save_as_html(summary_data, template_html, output_html_path)
            has_html = True
            save_as_pdf(output_html_path, output_pdf_path)
            has_pdf = True
        
        # 4. Zip the files together
        with zipfile.ZipFile(output_zip_path, 'w') as zipf:
            zipf.write(extracted_text_path, arcname="extracted_text.txt")
            zipf.write(output_json_path, arcname="summary.json")
            zipf.write(output_txt_path, arcname="summary.txt")
            if has_docx:
                zipf.write(output_docx_path, arcname="summary_filled.docx")
            if has_html:
                zipf.write(output_html_path, arcname="summary.html")
            if has_pdf:
                zipf.write(output_pdf_path, arcname="summary.pdf")
            
        # 5. Return the ZIP file
        return FileResponse(
            path=output_zip_path, 
            filename=f"{base_name}_summary.zip", 
            media_type="application/zip"
        )
        
    finally:
        # Clean up temporary DOCX
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
