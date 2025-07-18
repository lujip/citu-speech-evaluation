# Speech Evaluation Web Application

This project is a full-stack speech evaluation web app using React (Vite) for the frontend and Python (Flask) for the backend. It leverages Deepgram API for speech-to-text and OpenAI API for evaluation.

---

## Features
- Record and upload speech answers to questions
- Automatic transcription (Deepgram)
- AI-powered evaluation and feedback (OpenAI)
- Audio analysis (pitch, speed, etc.)
- Modern, responsive UI

---

## Prerequisites
- **Node.js** (v16+ recommended)
- **Python** (3.8+ recommended)
- **pip** (Python package manager)
- **ffmpeg** (for audio conversion)

---

## 1. Clone the Repository
```sh
git clone <your-repo-url>
cd SpeechEvalMain
```

---

## 2. Backend Setup (Python)

### a. Create and activate a virtual environment (recommended)
```sh
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### b. Install Python requirements
```sh
pip install -r requirements.txt
```

### c. Set up API keys
Create a file called `.env` in the `backend/` folder with the following content:
```
OPENAI_API_KEY=your_openai_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```
**Never commit this file to git!**

### d. Install ffmpeg
- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your PATH.
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### e. Run the backend server
```sh
python app.py
```
The backend will start on [http://localhost:5000](http://localhost:5000)

---

## 3. Frontend Setup (React + Vite)

### a. Install dependencies
```sh
npm install
```

### b. Start the frontend
```sh
npm run dev
```
The frontend will start on [http://localhost:5173](http://localhost:5173) (or as shown in your terminal).

---

## 4. Usage
- Open your browser to the frontend URL.
- Click "Start Answering" to record your answer.
- Click "Stop Answering" to finish and upload.
- View transcript, audio metrics, and AI feedback.
- Click "Next Question" to proceed.

---

## 5. Troubleshooting
- **API errors:** Ensure your `.env` file is correct and you have internet access.
- **ffmpeg not found:** Make sure ffmpeg is installed and in your system PATH.
- **Port conflicts:** If 5000 or 5173 are in use, stop other services or change the port.
- **CORS issues:** The backend uses Flask-CORS; if you have issues, check browser console and backend logs.

---

## 6. Project Structure
```
SpeechEvalMain/
  backend/         # Python Flask backend
    app.py
    test_eval.py
    requirements.txt
    .env           # (your API keys, not committed)
  src/             # React frontend
    App.jsx
    ...
  public/
  package.json
  README.md
```

---

## 7. Credits
- [Deepgram API](https://deepgram.com/)
- [OpenAI API](https://openai.com/)
- [Vite](https://vitejs.dev/)
- [React](https://react.dev/)

---

## 8. License
MIT (or your chosen license)
