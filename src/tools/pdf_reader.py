import os
from pathlib import Path
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

def extract_text_from_pdf_locally(pdf_path: str) -> str:
    """
    Extracts text from a PDF file using local tools to ensure privacy.
    First tries pdfplumber for machine-readable text.
    If the page appears to be a scanned image, falls back to pytesseract.
    """
    extracted_text = []
    
    print(f"Extracting text locally from {pdf_path}...")
    
    try:
        # Try pdfplumber first
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    extracted_text.append(f"--- Page {i+1} ---\n{text}")
                else:
                    # Fallback to OCR if page text is very sparse (likely an image)
                    print(f"Page {i+1} appears to be an image. Running OCR...")
                    try:
                        images = convert_from_path(pdf_path, first_page=i+1, last_page=i+1, dpi=300)
                        if images:
                            ocr_text = pytesseract.image_to_string(images[0])
                            extracted_text.append(f"--- Page {i+1} (OCR) ---\n{ocr_text}")
                    except Exception as e:
                        print(f"OCR failed for page {i+1}: {e}")
                        extracted_text.append(f"--- Page {i+1} ---\n[UNREADABLE IMAGE]")
    except Exception as e:
        print(f"Failed to open PDF with pdfplumber: {e}. Attempting full OCR fallback...")
        try:
            images = convert_from_path(pdf_path, dpi=300)
            for i, img in enumerate(images):
                print(f"Running OCR on page {i+1}...")
                ocr_text = pytesseract.image_to_string(img)
                extracted_text.append(f"--- Page {i+1} (OCR) ---\n{ocr_text}")
        except Exception as ocr_err:
            raise RuntimeError(f"Complete failure extracting text from PDF: {ocr_err}")

    return "\n\n".join(extracted_text)

def get_patient_text(patient_id: str, patients_dir: str = "data/patients") -> str:
    """
    Returns patient text from all source documents for this patient.

    Priority:
      1. Pre-computed full_ocr.txt (fast path, used in tests / CI).
      2. All *.pdf files found in the patient directory, each extracted and
         concatenated in alphabetical order. Each source is labelled with its
         filename so the agent can attribute facts and detect cross-document
         conflicts (e.g., conflicting diagnoses between admission note and
         progress note).
      3. Fallback: a root-level PDF named after the patient (legacy support).
    """
    patient_dir = Path(patients_dir) / patient_id
    ocr_path = patient_dir / "full_ocr.txt"

    # Fast path: use cached OCR text
    if ocr_path.exists():
        with open(ocr_path) as f:
            return f.read()

    # Primary path: extract and concatenate ALL PDFs in the patient folder
    if patient_dir.exists():
        pdfs = sorted(patient_dir.glob("*.pdf"))  # sorted for determinism
        if pdfs:
            all_text = []
            for pdf in pdfs:
                print(f"Processing {pdf.name}...")
                doc_text = extract_text_from_pdf_locally(str(pdf))
                all_text.append(f"=== SOURCE DOCUMENT: {pdf.name} ===\n{doc_text}")
            return "\n\n".join(all_text)

    # Legacy fallback: root-level PDF
    alt_path = Path("patient 2 (1).pdf")
    if alt_path.exists():
        print(f"Using legacy root PDF: {alt_path}")
        return f"=== SOURCE DOCUMENT: {alt_path.name} ===\n{extract_text_from_pdf_locally(str(alt_path))}"

    raise FileNotFoundError(
        f"Could not find any PDF or OCR cache for patient '{patient_id}'. "
        f"Expected files in: {patient_dir}/"
    )

