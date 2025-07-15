import pyttsx3
import sounddevice as sd
import soundfile as sf
import whisper
import language_tool_python
import parselmouth
import numpy as np
import os
import openai
from openai import OpenAI
import gc
from dotenv import load_dotenv

load_dotenv()

# --- OpenAI setup ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# --- GPT-based answer evaluation (simple) ---
def judge_answer(question, answer):
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

# --- GPT-based answer evaluation (detailed) ---
def judge_answer_2(question, answer, scores=None):
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
    prompt = (
        f"You are an English language speaking examiner following international speaking rubrics (e.g., IELTS, TOEFL, CEFR).\n\n"
        f"Question: {question}\n"
        f"Student's Answer: {answer}\n\n"
        "Evaluate the response using the following 5 categories:\n"
        "1. **Task Relevance** – Does the response appropriately and fully address the prompt? [IELTS, TOEFL]\n"
        "2. **Grammar and Lexis** – Is the grammar accurate and vocabulary appropriate? Evaluate range and correctness. [CEFR, IELTS]\n"
        "3. **Discourse Management** – Is the response well-structured, connected, and cohesive? Are ideas extended and logically organized? [CEFR, TOEFL]\n"
        "4. **Pronunciation and Fluency** – Is the speech fluent, with minimal unnatural pauses or hesitation? Deduct for filler words like 'uh', 'um', 'kanang', 'like'. [IELTS, CEFR]\n"
        "5. **Coherence and Appropriateness** – Does the tone fit an academic or formal setting? Is the response socially and culturally appropriate? [CEFR]\n\n"
        "Return a JSON object:\n"
        "{\n"
        "  \"score\": (1–10 overall),\n"
        "  \"category_scores\": {\n"
        "    \"task_relevance\": x,\n"
        "    \"grammar_lexis\": x,\n"
        "    \"discourse_management\": x,\n"
        "    \"pronunciation_fluency\": x,\n"
        "    \"coherence_appropriateness\": x\n"
        "  },\n"
        "  \"comment\": \"Give constructive feedback. If present, mention filler words, grammar errors, or disorganization.\"\n"
        "}"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

# --- Audio recording (legacy, not used) ---
def record_audio(file_name, duration=10):
    fs = 44100
    print(f"🎙️ Recording for {duration} seconds...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    sf.write(file_name, audio, fs)
    print("✅ Recording saved.\n")

# --- Whisper transcription (legacy, not used) ---
model = whisper.load_model("medium")
def transcribe_audio(file_path):
    result = model.transcribe(file_path, word_timestamps=True, language="en")
    return result["text"]

# --- Deepgram transcription ---
import asyncio
from deepgram import Deepgram
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

def transcribe_audio_deepgram(audio_path):
    async def transcribe_async():
        dg_client = Deepgram(DEEPGRAM_API_KEY)
        mimetype = "audio/wav"
        if audio_path.endswith(".mp3"):
            mimetype = "audio/mpeg"
        elif audio_path.endswith(".flac"):
            mimetype = "audio/flac"
        with open(audio_path, 'rb') as audio_file:
            source = {
                'buffer': audio_file,
                'mimetype': mimetype
            }
            response = await dg_client.transcription.prerecorded(
                source,
                {
                    'punctuate': False,
                    'language': 'en',
                    'utterances': True,
                    'filler_words': True,
                    'diarize': False,
                    'model': 'nova'
                }
            )
        full_transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
        words = response['results']['channels'][0]['alternatives'][0].get('words', [])
        fillers = [w for w in words if w.get("type") == "filler"]
        return {
            "transcript": full_transcript,
            "fillers": fillers,
            "words": words
        }
    return asyncio.run(transcribe_async())

# --- Grammar check ---
tool = language_tool_python.LanguageTool('en-US')
def check_grammar(text):
    return tool.check(text)

# --- Audio analysis ---
def analyze_audio(file_path):
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

# --- Evaluation wrapper ---
def evaluate_answer(transcript, audio_metrics, expected_keywords):
    return {
        "transcript": transcript,
        "audio_metrics": audio_metrics,
    }

# --- Main evaluation entry point ---
def run_full_evaluation(question, keywords, audio_file, use_deepgram=True):
    transcript_data = transcribe_audio_deepgram(audio_file)
    transcript = transcript_data["transcript"]
    audio_metrics = analyze_audio(audio_file)
    try:
        gpt_judgment = judge_answer_2(question, transcript, audio_metrics)
        import json as _json
        gpt_result = _json.loads(gpt_judgment) if gpt_judgment.strip().startswith('{') else {}
    except Exception as e:
        gpt_judgment = f"GPT evaluation failed: {str(e)}"
        gpt_result = {}
    gc.collect()
    return {
        "transcript": transcript,
        "transcript_data": transcript_data,
        "audio_metrics": audio_metrics,
        "evaluation": gpt_result,
        "gpt_judgment": gpt_judgment
    }
