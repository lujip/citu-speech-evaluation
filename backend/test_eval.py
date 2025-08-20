# test_eval.py - Evaluation and analysis logic for Speech Evaluation Web App
#
# This file contains all the core logic for transcribing, analyzing, and evaluating
# speech answers. Each section is commented for a step-by-step walkthrough.

import pyttsx3
import sounddevice as sd
import soundfile as sf
# import whisper
import language_tool_python
import parselmouth
import numpy as np
import os
from openai import OpenAI
import gc
from dotenv import load_dotenv
from deepgram import DeepgramClient, PrerecordedOptions
from google import genai
from pydantic import BaseModel

# 1. Load environment variables (API keys, etc.)
load_dotenv()

# 2. Set up OpenAI client for evaluation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
client_gemini = genai.Client(api_key=GEMINI_API_KEY)


# this is the detailed prompt used for GPT-based evaluation
detailed_gpt_prompt = '''
You are an English language speaking examiner following international speaking rubrics (e.g., IELTS, TOEFL, CEFR).

Question: {question}
Student's Answer: {answer}

Evaluate the response using the following 5 categories:

    Task Relevance – Does the response appropriately and fully address the prompt? [IELTS, TOEFL]
    Grammar and Lexis – Is the grammar accurate and vocabulary appropriate? Evaluate range and correctness. [CEFR, IELTS]
    Discourse Management – Is the response well-structured, connected, and cohesive? Are ideas extended and logically organized? [CEFR, TOEFL]
    Pronunciation and Fluency – Is the speech fluent, with minimal unnatural pauses or hesitation? Deduct for filler words like 'uh', 'um', 'kanang', 'like'. [IELTS, CEFR]
    Coherence and Appropriateness – Does the tone fit an academic or formal setting? Is the response socially and culturally appropriate? [CEFR]

P.S. Scoring are based on a 1-10 scale, with 10 being perfect. And provide comment also.
'''

# 3. (Optional) Simple GPT-based answer evaluation
#    - Returns a score and comment for a given question/answer
#    - Used for basic feedback
def judge_answer(question, answer):
    """
    Evaluate an answer using basic GPT criteria.
    
    :param question: The question that was asked
    :type question: str
    :param answer: The student's answer to evaluate
    :type answer: str
    :returns: JSON string containing score (1-10) and feedback comment
    :rtype: str
    """
    prompt = (
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        "Evaluate the answer based on:\n"
        "- Relevance to the question\n"
        "- Clarity and grammar\n"
        "- Professional tone\n\n"
        "Return a JSON with:\n"
        "{score: (1-10), comment: 'your feedback'}"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

# 4. (Recommended) Detailed GPT-based answer evaluation
#    - Returns a JSON with category scores and feedback
#    - Used for more granular, rubric-based feedback
def judge_answer_detailed(question, answer, scores=None):
    """
    Evaluate an answer using detailed GPT criteria with category scores.
    
    :param question: The question that was asked
    :type question: str
    :param answer: The student's answer to evaluate
    :type answer: str
    :param scores: Optional system scores for reference
    :type scores: dict or None
    :returns: JSON string containing overall score, category scores, and feedback comment
    :rtype: str
    """
    if not answer.strip():
        return """{
    "score": 0,
    "category_scores": {
    "task_relevance": 0,
    "grammar_lexis": 0,
    "discourse_management": 0,
    "pronunciation_fluency": 0,
    "coherence_appropriateness": 0
  },
  "comment": "The transcript was empty or unintelligible. Please ensure the response is clearly audible."
}"""
    scores_text = ""
    if scores:
        scores_text = "\nSystem Scores (for reference):\n" + "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in scores.items()) + "\n"
    
    # Use the detailed_gpt_prompt and append JSON format requirements
    prompt = detailed_gpt_prompt.format(
        question=question,
        answer=answer
    ) + """

Return a JSON object:
{
  "score": (1–10 overall),
  "category_scores": {
    "task_relevance": x,
    "grammar_lexis": x,
    "discourse_management": x,
    "pronunciation_fluency": x,
    "coherence_appropriateness": x
  },
  "comment": "Give constructive feedback. If present, mention filler words, grammar errors, or disorganization."
}"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()


# These are the Pydantic models used for structured responses
# They define the expected structure of the evaluation results
class CategoryScores(BaseModel):
    task_relevance: int
    grammar_lexis: int
    discourse_management: int
    pronunciation_fluency: int
    coherence_appropriateness: int

class Verdict(BaseModel):
    score: int
    category_scores: CategoryScores
    comment: str

def judge_answer_gemini(question, answer, scores=None) -> dict:
    """
    Evaluate an answer using Google Gemini AI with structured response format.
    
    :param question: The question that was asked
    :type question: str
    :param answer: The student's answer to evaluate
    :type answer: str
    :param scores: Optional system scores for reference
    :type scores: dict or None
    :returns: Dictionary containing score, category scores, and feedback comment
    :rtype: dict
    """
    try:
        prompt = detailed_gpt_prompt.format(
            question=question,
            answer=answer
        )

        response = client_gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": Verdict,
            }
        )

        # Use the parsed response directly
        if response and hasattr(response, 'parsed'):
            result: Verdict = response.parsed
            return result.dict()
        else:
            print("No parsed response from Gemini")
            return create_error_verdict("No valid response from Gemini")

    except Exception as e:
        print(f"Error in Gemini evaluation: {e}")
        return create_error_verdict(f"Gemini evaluation failed: {str(e)}")

def create_error_verdict(error_message: str) -> dict:
    """
    Create a default error verdict.
    
    :param error_message: The error message to include in the verdict
    :type error_message: str
    :returns: Dictionary containing default error verdict with zero scores
    :rtype: dict
    """
    return {
        "score": 0,
        "category_scores": {
            "task_relevance": 0,
            "grammar_lexis": 0,
            "discourse_management": 0,
            "pronunciation_fluency": 0,
            "coherence_appropriateness": 0
        },
        "comment": f"Error: {error_message}"
    }

# 5. (Legacy) Record audio from microphone and save to file
#    - Not used in main app, but useful for testing
def record_audio(file_name, duration=10):
    """
    Record audio from microphone and save to file.
    
    :param file_name: The filename to save the recorded audio
    :type file_name: str
    :param duration: Duration of recording in seconds
    :type duration: int
    :returns: None
    :rtype: None
    """
    fs = 44100
    print(f"🎙️ Recording for {duration} seconds...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    sf.write(file_name, audio, fs)
    print("✅ Recording saved.\n")

# 6. (Legacy) Transcribe audio using Whisper (local model)
#    - Not used in main app, but can be used for offline testing, does not detect filler words

# Use smaller model and configure for GPU efficiency
# model = whisper.load_model("small") 
# def transcribe_audio(file_path):
#     with torch.cuda.amp.autocast():  # Use automatic mixed precision
#         result = model.transcribe(file_path, word_timestamps=True, language="en")
#     return result["text"]

# 7. Transcribe audio using Deepgram API (main method)
#    - Converts audio to text, detects fillers, etc.

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable is not set. Please set it in your .env file.")

def transcribe_audio_deepgram(audio_path):
    """
    Transcribe audio using Deepgram API with filler word detection.
    
    :param audio_path: Path to the audio file to transcribe
    :type audio_path: str
    :returns: Dictionary containing transcript, fillers, and word data, or None if failed
    :rtype: dict or None
    """
    try:
        dg_client = DeepgramClient(DEEPGRAM_API_KEY)
        
        mimetype = "audio/wav"
        if audio_path.endswith(".mp3"):
            mimetype = "audio/mpeg"
        elif audio_path.endswith(".flac"):
            mimetype = "audio/flac"
                
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        print("Setting up transcription options...")
        options = PrerecordedOptions(
            smart_format=True,
            model="nova-2",
            language="en-US",
            detect_topics=True,
            utterances=True
        )
        
        payload = {
            "buffer": audio_data,
        }
        
        response = dg_client.listen.rest.v("1").transcribe_file(payload, options)
        
        if not response or not response.results:
            return None
        
        result = response.results
        channel = result.channels[0]
        alternative = channel.alternatives[0]
        
        transcription_result = {
            "transcript": alternative.transcript,
            "fillers": [w for w in alternative.words if hasattr(w, 'type') and w.type == 'filler'],
            "words": alternative.words
        }
        
        print(f"Transcription successful: {transcription_result['transcript'][:50]}...")
        return transcription_result
        
    except Exception as e:
        print(f"Deepgram transcription error: {str(e)}")
        return None

# 8. Grammar check using LanguageTool
#    - Returns a list of grammar issues
tool = language_tool_python.LanguageTool('en-US')
def check_grammar(text):
    """
    Check grammar and language issues in the provided text.
    
    :param text: The text to check for grammar issues
    :type text: str
    :returns: List of grammar issues found by LanguageTool
    :rtype: list
    """
    return tool.check(text)

# 9. Analyze audio for pitch, duration, and estimated words per minute
#    - Used for additional feedback
def analyze_audio(file_path):
    """
    Analyze audio file for pitch, duration, and estimated speaking rate.
    
    :param file_path: Path to the audio file to analyze
    :type file_path: str
    :returns: Dictionary containing duration, average pitch, and estimated words per minute
    :rtype: dict
    """
    snd = parselmouth.Sound(file_path)
    pitch = snd.to_pitch()
    duration = snd.duration
    pitch_values = pitch.selected_array['frequency']
    pitch_values = pitch_values[pitch_values != 0]
    avg_pitch = np.mean(pitch_values) if len(pitch_values) else 0
    words_estimate = duration / 0.4
    words_per_min = (words_estimate / duration) * 60
    return {
        "duration": round(duration, 2),
        "avg_pitch_hz": round(avg_pitch, 2),
        "estimated_wpm": round(words_per_min, 2)
    }

# 10. Wrap up all results for the frontend
#     - Returns transcript, audio metrics, and (optionally) evaluation
#     - This is the main callable from app.py
#     - Calls Deepgram, analyzes audio, and gets GPT feedback from OpenAI
#     - Returns all results

def evaluate_answer(transcript, audio_metrics, expected_keywords):
    """
    Basic evaluation function that returns transcript and audio metrics.
    
    :param transcript: The transcribed text from audio
    :type transcript: str
    :param audio_metrics: Dictionary containing audio analysis results
    :type audio_metrics: dict
    :param expected_keywords: List of keywords expected in the answer
    :type expected_keywords: list
    :returns: Dictionary containing transcript and audio metrics
    :rtype: dict
    """
    return {
        "transcript": transcript,
        "audio_metrics": audio_metrics,
    }

def run_full_evaluation(question, keywords, audio_file, use_deepgram=True):
    """
    Main evaluation function that processes audio and returns complete results.
    
    :param question: The question that was asked to the student
    :type question: str
    :param keywords: Expected keywords for the answer evaluation
    :type keywords: list
    :param audio_file: Path to the audio file containing the student's answer
    :type audio_file: str
    :param use_deepgram: Whether to use Deepgram for transcription (default: True)
    :type use_deepgram: bool
    :returns: Complete evaluation results including transcript, metrics, and scores, or error dict if failed
    :rtype: dict
    """
    try:
        # Validate input parameters
        if not question or not audio_file:
            return {
                "error": "INVALID_INPUT",
                "message": "Question and audio file are required",
                "status_code": 400
            }
        
        # Check if audio file exists
        if not os.path.exists(audio_file):
            return {
                "error": "FILE_NOT_FOUND",
                "message": f"Audio file not found: {audio_file}",
                "status_code": 404
            }
        
        # Get transcription
        transcript_data = transcribe_audio_deepgram(audio_file)
        if not transcript_data:
            return {
                "error": "TRANSCRIPTION_FAILED",
                "message": "Audio transcription failed - no data returned from Deepgram",
                "status_code": 502
            }
        
        transcript = transcript_data.get("transcript")
        if not transcript or not transcript.strip():
            return {
                "error": "EMPTY_TRANSCRIPT",
                "message": "Transcription failed - no speech detected in audio",
                "status_code": 422
            }
        
        # Get audio metrics
        audio_metrics = analyze_audio(audio_file)
        if not audio_metrics:
            return {
                "error": "AUDIO_ANALYSIS_FAILED",
                "message": "Audio analysis failed - unable to process audio file",
                "status_code": 422
            }
            
        # Get evaluation (using Gemini)
        evaluation_result = judge_answer_gemini(question, transcript, audio_metrics)
        
        # Check if evaluation was successful
        if "error" in evaluation_result:
            return {
                "error": "EVALUATION_FAILED",
                "message": f"AI evaluation failed: {evaluation_result.get('comment', 'Unknown error')}",
                "status_code": 502
            }
        
        # Cleanup
        gc.collect()
            
        # Structure the response to match frontend expectations
        return {
            "success": True,
            "transcript": transcript,
            "transcript_data": transcript_data,
            "audio_metrics": audio_metrics,
            "evaluation": {
                "score": evaluation_result.get("score", 0),
                "category_scores": evaluation_result.get("category_scores", {}),
            },
            "comment": evaluation_result.get("comment", "No feedback available.")
        }
            
    except FileNotFoundError as e:
        return {
            "error": "FILE_NOT_FOUND",
            "message": f"Required file not found: {str(e)}",
            "status_code": 404
        }
    except PermissionError as e:
        return {
            "error": "PERMISSION_DENIED",
            "message": f"Permission denied accessing file: {str(e)}",
            "status_code": 403
        }
    except ValueError as e:
        return {
            "error": "INVALID_INPUT",
            "message": f"Invalid input provided: {str(e)}",
            "status_code": 400
        }
    except Exception as e:
        print(f"Unexpected error in run_full_evaluation: {str(e)}")
        return {
            "error": "INTERNAL_ERROR",
            "message": f"An unexpected error occurred: {str(e)}",
            "status_code": 500
        }
