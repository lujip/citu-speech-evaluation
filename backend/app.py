# app.py - Flask backend for Speech Evaluation Web App
#
# This file handles the API endpoints, question management, audio file handling,
# and orchestration of the evaluation process. See comments throughout for a walkthrough.

from flask import Flask, jsonify, request
import threading
from flask_cors import CORS
from test_eval import run_full_evaluation
import json
import pyttsx3
import os
import subprocess

# 1. Initialize Flask app and enable CORS for frontend-backend communication
app = Flask(__name__)
CORS(app)

# 2. Define the set of questions and keywords for evaluation
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

# 3. Track the current question and index
current_question = {"text": questions[0]["text"]}
current_index = 0

# 4. Text-to-speech function to read questions aloud (runs in a thread)
def speak(text):
    """
    Convert text to speech using pyttsx3 engine with female voice preference.
    
    :param text: The text to be spoken aloud
    :type text: str
    :returns: None
    :rtype: None
    """
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if "female" in voice.name.lower() or "zira" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.say(text)
    engine.runAndWait()

# 5. API endpoint: Get the current question
@app.route("/question", methods=["GET"])
def get_current_question():
    """
    GET endpoint to retrieve the current question.
    
    :returns: JSON response containing the current question text
    :rtype: flask.Response
    """
    return jsonify(current_question)

# 6. API endpoint: Move to the next question (loops to start if at end)
@app.route("/next_question", methods=["POST"])
def next_question():
    """
    POST endpoint to advance to the next question in the sequence.
    
    Advances to the next question in the predefined list. If at the end of the list,
    loops back to the first question. Also triggers text-to-speech for the new question.
    
    :returns: JSON response with success status and the new question
    :rtype: flask.Response
    """
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

# 7. API endpoint: Evaluate an audio answer
#    - Receives question, keywords, and audio file from frontend
#    - Converts audio to WAV (if needed)
#    - Calls run_full_evaluation (see test_eval.py)
#    - Returns transcript, metrics, evaluation, and feedback
@app.route("/evaluate", methods=["POST"])
def evaluate():
    """
    POST endpoint to evaluate a student's audio answer.
    
    Receives a question, keywords, and audio file from the frontend, processes the audio
    through transcription and evaluation pipeline, and returns comprehensive results.
    
    Expected form data:
    - question: The question that was asked
    - keywords: List of expected keywords for evaluation
    - audio: Audio file containing the student's answer (webm/ogg format)
    
    :returns: JSON response containing transcript, audio metrics, evaluation scores, and feedback
    :rtype: flask.Response
    
    Response format:
    {
        "transcript": str,
        "audio_metrics": dict,
        "evaluation": dict,
        "comment": str
    }
    
    Error responses:
    - 400: Missing required fields (question, keywords, or audio)
    - 500: Audio conversion failure or evaluation pipeline failure
    """
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
            # Call the evaluation pipeline
    try:
        result = run_full_evaluation(question, keywords, audio_wav_path)
        if not result:
            return jsonify({"success": False, "message": "Speech transcription failed. Please try again."}), 500
        
        import gc
        gc.collect()
        
        # Get evaluation and comment from result
        evaluation = result.get("evaluation", {})
        comment = result.get("comment", "No feedback available.")  # Get comment directly from result
        
    except Exception as e:
        print(f"Evaluation error: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred during evaluation. Please try again."}), 500
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

# 8. Start the Flask app (and optionally speak the first question)
if __name__ == "__main__":
    threading.Thread(target=speak, args=(current_question["text"],)).start()
    app.run(port=5000)
