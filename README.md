# Medicine OCR and Contextual Information System
This project is a web-based system that extracts and provides contextual information about medicines from uploaded images of medicine labels.  
It combines **OCR (TyphoonOCR)** for text extraction, **Qwen3 LLM** for reasoning and response generation, and a **local text-file database** for retrieving medicine-specific details.  
The backend is implemented using **FastAPI** with preprocessing powered by **OpenCV** and **PIL**.

## Features
- Upload a medicine label image.
- Image preprocessing (noise reduction, thresholding, binarization).
- OCR using **TyphoonOCR API**.
- Medicine name extraction (exact and fuzzy matching).
- Context retrieval from a local text-file database.
- Contextual response generation using **Qwen3 LLM**.
- Outputs structured Markdown with:
  - ชื่อยาและรายละเอียด  
  - ข้อควรระวัง  
  - ผลข้างเคียง  

```bash
git clone https://github.com/v89intern-superai/MedicineOCRandContextualInformationSystem.git
```

---

## Medicine OCR and Contextual Information System - **Frontend**

### **Installation**
```bash
cd MedicineOCRandContextualInformationSystem/frontend
npm install
```

### **Start**
```bash
npm run dev
```

---

## Medicine OCR and Contextual Information System - **Backend**

For this part you also need **Ollama** as Model Inference

### **Installation**
```bash
cd MedicineOCRandContextualInformationSystem/backend
pip install -r requirements.txt
```

Create a .env file in the backend/ directory:
```
API_KEY="<your_typhoon_api_key_here>"
```
Get your API_KEY from https://playground.opentyphoon.ai/settings/api-key

### **Start**
```bash
uvicorn main:app --reload --port 5000
```


