import os
import re
import io
import json
import cv2
import requests
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import ChatOllama
from pydantic import BaseModel
from difflib import get_close_matches
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")

UPLOAD_DIR = "uploads"
TXT_FOLDER = "../txt_database"
LLM_MODEL = "qwen3:4b"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- OCR & Preprocessing -------------------
def preprocess_image(file_path: str) -> Image.Image:
    img = cv2.imread(file_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=12)
    if np.mean(gray) < 127:
        gray = cv2.bitwise_not(gray)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, 2
    )
    clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((1, 1), np.uint8))
    cv2.imwrite("./uploads/preprocess.png", clean)
    return Image.fromarray(clean).convert("RGB")

def run_typhoon_ocr(img: Image.Image, api_key: str, model_name: str) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    files = {"file": ("uploaded.png", buf, "image/png")}
    data = {"params": json.dumps({
        "model": model_name,
        "task_type": "default",
        "max_tokens": 2048,
        "temperature": 0.01,
        "top_p": 0.1,
        "repetition_penalty": 1.1,
    })}
    headers = {"Authorization": f"Bearer {api_key}"}
    res = requests.post("https://api.opentyphoon.ai/v1/ocr", files=files, data=data, headers=headers)
    if res.status_code != 200:
        return f"Error: {res.status_code}, {res.text}"

    texts = []
    for page in res.json().get("results", []):
        if page.get("success") and page.get("message"):
            content = page["message"]["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(content)
                texts.append("\n".join(extract_strings_from_json(parsed)))
            except json.JSONDecodeError:
                texts.append(content.strip())
    return "\n".join(texts)

def extract_strings_from_json(obj):
    texts = []
    if isinstance(obj, dict):
        for v in obj.values():
            texts.extend(extract_strings_from_json(v))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(extract_strings_from_json(item))
    elif isinstance(obj, str):
        texts.append(obj)
    return texts

# ------------------- Medicine Name Matching -------------------
def extract_medicine_name(ocr_text: str) -> Optional[str]:
    med_files = [os.path.splitext(f)[0] for f in os.listdir(TXT_FOLDER) if f.endswith(".txt")]
    lines = [line.strip().upper() for line in ocr_text.splitlines() if line.strip()]

    # Exact line match
    for line in lines:
        for med in med_files:
            if line.upper() == med.upper():
                return med

    # Fuzzy match
    all_text = " ".join(lines).upper()
    matches = get_close_matches(all_text, [m.upper() for m in med_files], n=1, cutoff=0.6)
    return matches[0] if matches else None

def load_medicine_file(med_name: str) -> Optional[str]:
    filename = re.sub(r"[^a-zA-Z0-9ก-๙]", "_", med_name) + ".txt"
    path = os.path.join(TXT_FOLDER, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

# ------------------- FastAPI Endpoints -------------------
@app.post("/ocr")
async def ocr_only(file: UploadFile = File(...), api_key: str = api_key):
    path = os.path.join(UPLOAD_DIR, "uploaded.png")
    with open(path, "wb") as f:
        f.write(await file.read())
    processed_img = preprocess_image(path)
    ocr_text = run_typhoon_ocr(processed_img, api_key, "typhoon-ocr-preview")
    return {"ocr_text": ocr_text}

class OCRTextRequest(BaseModel):
    ocr_text: str

@app.post("/rag")
async def rag_only(request: OCRTextRequest):
    ocr_text = request.ocr_text

    # Extract medicine name using LLM
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    name_prompt = f"""
คุณเป็นผู้ช่วยให้ข้อมูลยา
ให้ตอบว่ายาจากข้อความจาก OCR คือยาอะไร
ตอบเฉพาะชื่อยาเป็นภาษาอังกฤษ

ข้อความจาก OCR:
{ocr_text}
"""
    response = llm.invoke(name_prompt)
    med_name_response = getattr(response, "content", str(response)).strip()
    med_name = med_name_response.split("</think>")[1].strip().upper() if "</think>" in med_name_response else med_name_response.strip().upper()

    if med_name == "NONE":
        return {"error": "No medicine detected from OCR text."}

    # Load medicine context
    context_text = load_medicine_file(med_name)
    if not context_text:
        med_files = [os.path.splitext(f)[0] for f in os.listdir(TXT_FOLDER) if f.endswith(".txt")]
        matches = get_close_matches(med_name.upper(), [m.upper() for m in med_files], n=1, cutoff=0.6)
        if matches:
            context_text = load_medicine_file(matches[0])
            med_name = matches[0]

    if not context_text:
        return {"error": f"Medicine file for '{med_name}' not found."}

    # Generate final LLM answer
    prompt = f"""
คุณเป็นผู้ช่วยให้ข้อมูลยา
ให้คุณให้ข้อมูลเกี่ยวกับยาตัวนี้โดยใช้ "ข้อมูลประกอบ" และ "ข้อความจาก OCR" ด้านล่าง

ข้อความจาก OCR:
{ocr_text}

ชื่อยาที่ตรวจพบ:
{med_name}

ข้อมูลประกอบ:
{context_text}

คำตอบสุดท้ายให้เป็น Markdown โดยมีหัวข้อดังนี้

ชื่อยาและรายละเอียด
ข้อควรระวัง
ผลข้างเคียง

ห้ามเติมยาอื่นที่ไม่อยู่ในข้อความจาก OCR
ตอบเป็นภาษาไทยล้วน ยกเว้นชื่อยาให้ตอบเป็นภาษาอังกฤษและวงเล็บเป็นภาษาไทยด้วย
"""
    response = llm.invoke(prompt)
    llm_text = getattr(response, "content", str(response))
    llm_text = llm_text.split("</think>")[1].strip() if "</think>" in llm_text else llm_text.strip()

    return {"llm_text": llm_text, "med_name": med_name}
