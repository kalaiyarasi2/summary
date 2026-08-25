import os
import shutil
import zipfile
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from summarize_sop import read_docx, generate_summary, save_as_json, save_as_txt

app = FastAPI(
    title="SOP Summarizer API",
    description="Upload a DOCX file to get a structured JSON and TXT summary."
)

@app.get("/")
def read_root():
    # Redirect to the Swagger UI so users don't see a 404 at the root
    return RedirectResponse(url="/docs")

@app.post("/summarize")
async def summarize_document(file: UploadFile = File(...)):
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Temporary paths
    temp_docx_path = f"temp_{file.filename}"
    output_json_path = os.path.join(output_dir, "summary.json")
    output_txt_path = os.path.join(output_dir, "summary.txt")
    output_zip_path = os.path.join(output_dir, "summary_files.zip")
    
    try:
        # Save uploaded DOCX file temporarily
        with open(temp_docx_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Read DOCX
        document_text = read_docx(temp_docx_path)
        
        # 2. Generate Summary via OpenAI
        summary_data = generate_summary(document_text)
        
        # 3. Save as JSON and TXT
        save_as_json(summary_data, output_json_path)
        save_as_txt(summary_data, output_txt_path)
        
        # 4. Zip the files together
        with zipfile.ZipFile(output_zip_path, 'w') as zipf:
            zipf.write(output_json_path, arcname="summary.json")
            zipf.write(output_txt_path, arcname="summary.txt")
            
        # 5. Return the ZIP file
        return FileResponse(
            path=output_zip_path, 
            filename="summary_files.zip", 
            media_type="application/zip"
        )
        
    finally:
        # Clean up temporary DOCX
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
