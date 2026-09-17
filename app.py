import os
import shutil
import zipfile
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Body
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from summarize_sop import read_docx, generate_summary, save_as_json, save_as_txt, save_as_docx, save_as_html, save_as_pdf, merge_docx_files
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(BASE_DIR / ".env")

app = FastAPI(
    title="SOP Summarizer & Chatbot API",
    description="Upload DOCX SOP files to get structured extraction, multi-format artifacts, and interactive chatbot assistance."
)

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str
    context: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []

@app.get("/")
def read_root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SOP Summarizer & Chatbot API"}

@app.post("/summarize")
def summarize_document(file: UploadFile = File(...)):
    base_name = os.path.splitext(file.filename or "document")[0]
    safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_")).strip() or "sop_document"
    
    output_dir = BASE_DIR / "output" / safe_base_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    temp_docx_path = BASE_DIR / f"temp_{file.filename}"
    extracted_text_path = output_dir / "extracted_text.txt"
    output_json_path = output_dir / "summary.json"
    output_txt_path = output_dir / "summary.txt"
    output_docx_path = output_dir / "summary_filled.docx"
    merged_docx_path = output_dir / "combined_summary.docx"
    output_html_path = output_dir / "summary.html"
    output_pdf_path = output_dir / "summary.pdf"
    output_zip_path = BASE_DIR / "output" / f"{safe_base_name}_summary_files.zip"
    
    template_docx = BASE_DIR / "input" / "template_grid.docx"
    template_html = BASE_DIR / "input" / "template.html"
    
    try:
        with open(temp_docx_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Read DOCX
        document_text = read_docx(str(temp_docx_path))
        
        # Save extracted text
        with open(extracted_text_path, "w", encoding="utf-8") as f:
            f.write(document_text)
        
        # 2. Generate Summary via OpenAI
        summary_data = generate_summary(document_text)
        
        # 3. Save as JSON, TXT, DOCX, and HTML
        save_as_json(summary_data, str(output_json_path))
        save_as_txt(summary_data, str(output_txt_path))
        
        has_docx = False
        if template_docx.exists():
            save_as_docx(summary_data, str(template_docx), str(output_docx_path))
            merge_docx_files(str(temp_docx_path), str(output_docx_path), str(merged_docx_path))
            has_docx = True
            
        has_html = False
        has_pdf = False
        if template_html.exists():
            save_as_html(summary_data, str(template_html), str(output_html_path))
            has_html = True
            try:
                save_as_pdf(str(output_html_path), str(output_pdf_path))
                has_pdf = True
            except Exception as pdf_err:
                print(f"[WARN] PDF generation via Playwright skipped: {pdf_err}")
        
        # 4. Zip the files together
        with zipfile.ZipFile(output_zip_path, 'w') as zipf:
            zipf.write(str(extracted_text_path), arcname="extracted_text.txt")
            zipf.write(str(output_json_path), arcname="summary.json")
            zipf.write(str(output_txt_path), arcname="summary.txt")
            if has_docx:
                if output_docx_path.exists():
                    zipf.write(str(output_docx_path), arcname="summary_filled.docx")
                if merged_docx_path.exists():
                    zipf.write(str(merged_docx_path), arcname="combined_summary.docx")
            if has_html and output_html_path.exists():
                zipf.write(str(output_html_path), arcname="summary.html")
            if has_pdf and output_pdf_path.exists():
                zipf.write(str(output_pdf_path), arcname="summary.pdf")
            
        return {
            "status": "success",
            "session_id": safe_base_name,
            "filename": file.filename,
            "summary": summary_data,
            "files_available": {
                "json": output_json_path.exists(),
                "txt": output_txt_path.exists(),
                "docx": output_docx_path.exists(),
                "summary_docx": output_docx_path.exists(),
                "combined_docx": merged_docx_path.exists(),
                "html": output_html_path.exists(),
                "pdf": output_pdf_path.exists(),
                "zip": output_zip_path.exists(),
            },
            "download_urls": {
                "zip": f"/api/summary/download/{safe_base_name}/zip",
                "pdf": f"/api/summary/download/{safe_base_name}/pdf",
                "docx": f"/api/summary/download/{safe_base_name}/summary_docx",
                "summary_docx": f"/api/summary/download/{safe_base_name}/summary_docx",
                "combined_docx": f"/api/summary/download/{safe_base_name}/combined_docx",
                "html": f"/api/summary/download/{safe_base_name}/html",
                "json": f"/api/summary/download/{safe_base_name}/json",
                "txt": f"/api/summary/download/{safe_base_name}/txt",
            }
        }
        
    finally:
        if temp_docx_path.exists():
            try:
                os.remove(temp_docx_path)
            except Exception:
                pass

@app.get("/download/{session_id}/{file_type}")
def download_file(session_id: str, file_type: str):
    output_dir = BASE_DIR / "output" / session_id
    zip_path = BASE_DIR / "output" / f"{session_id}_summary_files.zip"
    
    file_map = {
        "zip": (zip_path, f"{session_id}_summary.zip", "application/zip"),
        "pdf": (output_dir / "summary.pdf", f"{session_id}_summary.pdf", "application/pdf"),
        "docx": (output_dir / "summary_filled.docx", f"{session_id}_summary_filled.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "summary_docx": (output_dir / "summary_filled.docx", f"{session_id}_summary_filled.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "combined_docx": (output_dir / "combined_summary.docx", f"{session_id}_combined_summary.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "html": (output_dir / "summary.html", f"{session_id}_summary.html", "text/html"),
        "json": (output_dir / "summary.json", f"{session_id}_summary.json", "application/json"),
        "txt": (output_dir / "summary.txt", f"{session_id}_summary.txt", "text/plain"),
        "extracted_text": (output_dir / "extracted_text.txt", f"{session_id}_extracted_text.txt", "text/plain"),
    }
    
    if file_type not in file_map:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{file_type}'. Supported: {list(file_map.keys())}")
        
    path, filename, media_type = file_map[file_type]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Requested file not found: {filename}")
        
    return FileResponse(
        path=str(path), 
        filename=filename, 
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

