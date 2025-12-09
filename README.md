# 🤖 GAMA AI – Intelligent Chatbot System

GAMA AI is a modern, responsive, and feature-rich intelligent chatbot system built using **Flask (Python)** for the backend and **HTML/CSS/JavaScript** for the frontend.  
The chatbot supports real-time conversations, multi-turn context, and file-based analysis including PDFs, text files, and images.

This project was collaboratively developed by **two team members**.

---

## 🚀 Features

### 🔹 Real-Time AI Chat
- Multi-turn conversation (AI remembers previous messages)
- Smooth chat bubble rendering
- Typing animation for realistic feel

### 🔹 File Upload & Smart Analysis
- Supports: **PDF**, **TXT**, **Images**
- Extracts content and generates:
  - Summaries
  - Explanations
  - Q&A based on your file

### 🔹 Chat History Management
- Sidebar with saved chats
- Rename chats for better organization
- Persistent chat titles

### 🔹 Theme Switching
- Light Mode  
- Dark Mode  
- Robotic / Neon Mode  
- User preference saved in browser storage

### 🔹 Clean & Responsive UI
- Fully responsive layout (mobile + desktop)
- Smooth animations
- Modern clean design

### 🔹 Secure Backend
- API keys stored in `.env` (backend only)
- Safe file handling
- Proper validation and error responses

---

## 🛠️ Tech Stack

### **Frontend**
- HTML5  
- CSS3  
- JavaScript (Vanilla JS)  

### **Backend**
- Python 3.x  
- Flask Framework  

### **AI Layer**
- GAMA AI (Gemini API backend)  
- Structured prompt engineering  
- Context-aware dialogue and file analysis  

### **Tools**
- VS Code  
- Git & GitHub  
- Python libraries for file extraction and text processing  

---

## 🏗️ Project Architecture

The GAMA AI Chatbot uses a modular architecture that separates logic into five layers.

---

### **1️⃣ Frontend Layer (HTML/CSS/JS)**  
Manages all user interactions and UI rendering.

- Chat interface + login page + sidebar
- Handles user input and file uploads
- Renders messages in real time
- Theme switching logic
- Stores chat history in localStorage

---

### **2️⃣ Backend Layer (Flask / Python)**  
Core controller connecting UI to AI.

- API endpoints:
  - `/chat`
  - `/upload`
  - `/rename`
  - `/download`
- Validates input and processes files
- Stores API keys securely in `.env`
- Handles timeout & retry logic for stability

---

### **3️⃣ AI Integration Layer (GAMA AI / Gemini API)**  
Responsible for generating intelligent responses.

- Builds prompts for chat & file summarization
- Handles multi-turn context
- Converts model output to structured JSON  
- Ensures safe & optimized token usage

---

### **4️⃣ File Processing Pipeline**  
Extracts and processes file content.

- Supports PDFs, text files, images
- Extracts text using Python libraries
- Cleans and chunks content
- Sends relevant extracted text to AI for:
  - Summaries
  - Explanations
  - Q&A
  - Insights

---

### **5️⃣ Session & State Management**
Ensures smooth, consistent chat experience.

- Stores chat titles & theme in localStorage
- Sends only relevant context to backend
- Each chat session remains isolated
- Provides organized sidebar history

---


