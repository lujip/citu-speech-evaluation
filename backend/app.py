from flask import Flask, jsonify, request
import threading
from flask_cors import CORS
from test_eval import run_full_evaluation
import json
import pyttsx3
import os
import subprocess

app = Flask(__name__)
CORS(app)

# --- Question bank ---
questions = [
    {
        "text": "Describe a situation when you had to explain something difficult to someone.",
        "keywords": ["explain", "situation", "difficult", "understand", "communication"]
    },
    {
        "text": "Do you agree or disagree: Students should be required to take public speaking courses in college.",
        "keywords": ["public speaking", "students", "college", "required", "communication"]
    },
    {
        "text": "Talk about a time when you worked as part of a group. What was your role?",
        "keywords": ["group", "teamwork", "role", "collaboration", "responsibility"]
    },
    {
        "text": "If you could make one improvement to your school, what would it be and why?",
        "keywords": ["improvement", "school", "problem", "solution", "education"]
    },
    {
        "text": "Describe a person you admire and explain why.",
        "keywords": ["admire", "person", "inspiration", "reason", "qualities"]
    }
]

current_question = {"text": questions[0]["text"]}
current_index = 0

def speak(text):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if "female" in voice.name.lower() or "zira" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.say(text)
    engine.runAndWait()

@app.route("/question", methods=["GET"])
def get_current_question():
    return jsonify(current_question)

@app.route("/next_question", methods=["POST"])
def next_question():
    global current_index, current_question
    if current_index + 1 < len(questions):
        current_index += 1
        current_question["text"] = questions[current_index]["text"]
        threading.Thread(target=speak, args=(current_question["text"],)).start()
        return jsonify({"success": True, "question": current_question})
    else:
        # Loop back to the first question
        current_index = 0
        current_question["text"] = questions[current_index]["text"]
        threading.Thread(target=speak, args=(current_question["text"],)).start()
        return jsonify({"success": True, "question": current_question})

@app.route("/evaluate", methods=["POST"])
def evaluate():
    question = request.form.get("question")
    keywords = request.form.getlist("keywords")
    audio = request.files.get("audio")
    if not question or not keywords or not audio:
        return jsonify({"success": False, "message": "Missing question, keywords, or audio file."}), 400
    audio_webm_path = "uploaded_answer.webm"
    audio_wav_path = "uploaded_answer.wav"
    audio.save(audio_webm_path)
    # Convert webm/ogg to wav using ffmpeg
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_webm_path, audio_wav_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return jsonify({"success": False, "message": f"Audio conversion failed: {str(e)}"}), 500
    result = run_full_evaluation(question, keywords, audio_wav_path)
    import gc
    gc.collect()
    # Separate evaluation and comment
    evaluation = result.get("evaluation", {})
    gpt_judgment = result.get("gpt_judgment", "")
    comment = None
    # Try to extract comment from gpt_judgment if it's a JSON string
    try:
        import json as _json
        gpt_eval = _json.loads(gpt_judgment) if isinstance(gpt_judgment, str) and gpt_judgment.strip().startswith('{') else None
        if gpt_eval and 'comment' in gpt_eval:
            comment = gpt_eval['comment']
    except Exception:
        pass
    if not comment:
        comment = gpt_judgment
    # Remove uploaded and converted files after processing
    for path in [audio_webm_path, audio_wav_path]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as cleanup_err:
            print(f"Cleanup failed: {cleanup_err}")
    # Print all output for checking
    print("\n--- Evaluation Output ---")
    print(f"Transcript: {result.get('transcript')}")
    print(f"Audio Metrics: {result.get('audio_metrics')}")
    print(f"Evaluation: {evaluation}")
    print(f"Comment: {comment}")
    print("--- End of Output ---\n")
    # Return separated evaluation and comment
    return jsonify({
        "transcript": result.get("transcript"),
        "audio_metrics": result.get("audio_metrics"),
        "evaluation": evaluation,
        "comment": comment
    })

if __name__ == "__main__":
    # Optionally speak the first question at startup
    threading.Thread(target=speak, args=(current_question["text"],)).start()
    app.run(port=5000)
