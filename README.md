# 🌿 Visual RAG Chatbot — Browser Extension

An experiment I built to answer a simple question:

> “What if you could ask questions about any image on the internet, especially on Pinterest, and get meaningful answers instantly?”

This project is a Chrome extension + local AI backend that lets you do exactly that.

Hover over any image on a webpage, click **Analyse**, and start asking questions. The system combines visual understanding, page context, and web knowledge to give grounded answers — all running locally.

---

##  Why I built this

Most tools today:

- Either understand images  
- Or retrieve information  

Very few actually **combine both in a meaningful way**.

I wanted to explore:

- How far I can push a fully local RAG system  
- Whether combining vision + retrieval + LLMs can give better answers  
- And how this would work directly inside a browser  

---

##  What it can do

- Ask *“Who is this person?”* on a news image  
- Ask *“Explain this outfit”* on Pinterest  
- Ask *“What are the features?”* on a product page  

The answers are not just guesses — they’re built from:

- Image understanding  
- Page content  
- Live web context  

---

##  How it works (high level)

### When you click Analyse:

- The image is described using a vision model  
- Relevant page content is extracted  
- Extra context is pulled from web search  
- Everything is embedded and stored  

### When you ask a question:

- The system retrieves the most relevant pieces  
- Feeds them into a local LLM  
- Generates a grounded answer  

> Note: Some internal logic is intentionally abstracted — the goal is to show system design, not expose every implementation detail.

---

##  Tech used

- **Ollama** → runs models locally  
- **Llama 3.2** → answer generation  
- **Moondream** → image understanding  
- **Sentence Transformers** → embeddings  
- **FAISS** → vector search  
- **Flask** → backend  
- **Chrome Extension (Manifest V3)** → frontend  

---

## ️ Setup (quick)

```bash
# install models
ollama pull llama3.2
ollama pull moondream

# backend
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

python app.py