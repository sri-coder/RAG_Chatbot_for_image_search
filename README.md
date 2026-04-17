# Visual RAG Chatbot (Browser Extension)

A Chrome extension that lets you ask questions about any image on a webpage.

Hover over an image, click **Analyse**, and start asking questions. The system uses a mix of image understanding, page context, and retrieval to generate answers, all running locally.

---

## Why I built this


Personally, I used to get curious about the images I see on Pinterest when I use it during my leisure time. Usually I look at the images and get intrigued, where is this place? Can this flower survive in my country? Oh it looks nice, what's the name of this food? Aww the animal looks too cute what is the name of it? But the only way I could learn more the images is by using external tools like Google lens. So I decided to build my own system that can be used for learning about the image without having to leave the website I'm currently using. 

Most tools either:
- understand images  
- or retrieve information  

I wanted to explore what happens when you combine both in a single system, especially in a real-world setting like a browser. 

---

## What it does

- Ask “Who is this person?” on a news image  
- Ask “Explain this outfit” on Pinterest  
- Ask “What are the features?” on a product page  

The responses are generated using:
- image understanding  
- page content  
- additional retrieved context  

---

## How it works

When you click **Analyse**:
- The image is processed using a vision model  
- Page content is extracted  
- Additional context is retrieved  
- Everything is stored for querying  

When you ask a question:
- Relevant context is retrieved  
- Passed to a local LLM  
- A response is generated  

---

## Tech Stack

- Ollama (local models)
- Llama 3.2 (LLM)
- Moondream (vision)
- Sentence Transformers (embeddings)
- FAISS (vector search)
- Flask (backend)
- Chrome Extension (Manifest V3)

---

## Setup

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