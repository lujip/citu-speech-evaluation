import React, { useEffect, useState, useRef } from 'react';
import './App.css';
import axios from 'axios';
import Header from './components/header/Header.jsx';

const KEYWORDS = ["stress", "calm", "angry", "patience", "solution"];

const App = () => {
  // --- State and refs ---
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [audioUrl, setAudioUrl] = useState(null);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const sourceRef = useRef(null);
  const streamRef = useRef(null);

  // --- Fetch the first question on mount ---
  useEffect(() => {
    const fetchQuestion = async () => {
      try {
        const res = await axios.get("http://localhost:5000/question");
        setQuestion(res.data.text);
      } catch (err) {
        setQuestion("Could not load question.");
      }
    };
    fetchQuestion();
  }, []);

  // --- Draw waveform on canvas ---
  const drawWaveform = () => {
    if (!analyserRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    analyserRef.current.getByteTimeDomainData(dataArrayRef.current);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#1d4ed8';
    ctx.beginPath();
    let sliceWidth = WIDTH / dataArrayRef.current.length;
    let x = 0;
    for (let i = 0; i < dataArrayRef.current.length; i++) {
      let v = dataArrayRef.current[i] / 128.0;
      let y = (v * HEIGHT) / 2;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      x += sliceWidth;
    }
    ctx.lineTo(WIDTH, HEIGHT / 2);
    ctx.stroke();
    animationRef.current = requestAnimationFrame(drawWaveform);
  };

  // --- Recording logic ---
  const startRecording = async () => {
    setResult(null);
    setRecording(true);
    setAudioUrl(null);
    audioChunksRef.current = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    analyserRef.current = audioContextRef.current.createAnalyser();
    const source = audioContextRef.current.createMediaStreamSource(stream);
    sourceRef.current = source;
    source.connect(analyserRef.current);
    analyserRef.current.fftSize = 2048;
    const bufferLength = analyserRef.current.fftSize;
    dataArrayRef.current = new Uint8Array(bufferLength);
    drawWaveform();
    const mediaRecorder = new window.MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        audioChunksRef.current.push(e.data);
      }
    };
    mediaRecorder.onstop = handleStop;
    mediaRecorder.start();
  };

  const stopRecording = () => {
    setRecording(false);
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  // --- Handle stop and send audio to backend ---
  const handleStop = async () => {
    setLoading(true);
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
    setAudioUrl(URL.createObjectURL(audioBlob));
    const formData = new FormData();
    formData.append('question', question);
    KEYWORDS.forEach(k => formData.append('keywords', k));
    formData.append('audio', audioBlob, 'answer.wav');
    try { 
      const res = await axios.post("http://localhost:5000/evaluate", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(res.data);
    } catch (err) {
      alert("Error during evaluation: " + err.message);
    }
    setLoading(false);
  };

  // --- Helper to display metrics and nested objects ---
  const prettyPrint = (obj) => {
    if (!obj) return null;
    return (
      <ul style={{ paddingLeft: 20 }}>
        {Object.entries(obj).map(([k, v]) => (
          <li key={k}>
            <b>{k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</b>{' '}
            {typeof v === 'object' && v !== null
              ? prettyPrint(v)
              : (typeof v === 'number' ? v.toFixed(2) : v)}
          </li>
        ))}
      </ul>
    );
  };

  // --- Main render ---
  return (
    <div>
      <Header/>
      <div className="main-content">
        <div className="content-card">
          <div className="content-row">
            {/* Left: Question and controls */}
            <section className="question-block">
              <h2 className="speech-title">Speech Evaluation App</h2>
              <div className="question-section">
                <h2>Current Question:</h2>
                <p>{question || "Waiting for question..."}</p>
                <div className="question-buttons">
                  <button onClick={startRecording} disabled={loading || recording || !question}>
                    Start Answering
                  </button>
                  <button
                    style={{ marginLeft: '10px' }}
                    onClick={stopRecording}
                    disabled={loading || !recording}
                  >
                    Stop Answering
                  </button>
                  <button
                    style={{ marginLeft: '10px' }}
                    onClick={async () => {
                      try {
                        const res = await axios.post("http://localhost:5000/next_question");
                        if (res.data.success) {
                          setQuestion(res.data.question.text);
                          setResult(null);
                          setAudioUrl(null);
                        } else {
                          alert(res.data.message || "No more questions.");
                        }
                      } catch (err) {
                        alert("Error fetching next question: " + err.message);
                      }
                    }}
                    disabled={loading || recording}
                  >
                    Next Question
                  </button>
                </div>
                {recording && (
                  <div style={{ margin: '16px 0', textAlign: 'center' }}>
                    <div className="recording-status">Recording... Speak now!</div>
                    <canvas
                      ref={canvasRef}
                      width={700}
                      height={80}
                      className="waveform-canvas"
                    />
                  </div>
                )}
              </div>
            </section>
            {/* Right: Avatar */}
            <aside className="avatar-block">
              <div className="avatar-placeholder">Avatar</div>
            </aside>
          </div>
          {/* Results Section */}
          {loading && (
            <div className="loading-overlay">
              <div className="loading-spinner" />
              <div className="loading-text">Evaluating...</div>
            </div>
          )}
          {result && (
            <section className="result-section">
              <h3>Results</h3>
              <div className="result-grid">
                <div className="result-block">
                  <span className="result-label">Transcript</span>
                  <div className="result-value">{result.transcript}</div>
                </div>
                <div className="result-block">
                  <span className="result-label">Audio Metrics</span>
                  <div className="result-value">{prettyPrint(result.audio_metrics)}</div>
                  <span className="result-label" style={{marginTop: '1rem'}}>Scores</span>
                  <div className="result-value">
                    {prettyPrint(
                      Object.fromEntries(
                        Object.entries(result.evaluation || {}).filter(([k]) => k !== 'transcript' && k !== 'comment')
                      )
                    )}
                  </div>
                </div>
                <div className="result-block gpt-feedback-wide">
                  <span className="result-label">Feedback</span>
                  <div className="result-value" style={{whiteSpace: 'pre-line'}}>{result.comment}</div>
                </div>
              </div>
              {audioUrl && (
                <div style={{ marginTop: 24, textAlign: 'center' }}>
                  <audio controls src={audioUrl} style={{ width: '100%' }} />
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;