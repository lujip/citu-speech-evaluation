// EmojiAvatar.jsx
import React, { useState, useEffect } from 'react';
import './EmojiAvatar.css';

const EmojiAvatar = ({ isTalking = false, onTalkingToggle = null }) => {
  const [isBlinking, setIsBlinking] = useState(false);
  const [mouthState, setMouthState] = useState('smile'); // 'smile', 'medium', 'open'

  // Function to handle talking toggle (only if onTalkingToggle is provided)
  const handleTalkingToggle = () => {
    if (onTalkingToggle) {
      onTalkingToggle();
    }
  };

  // Removed automatic talking - now only triggered by button
  // useEffect(() => {
  //   const talkInterval = setInterval(() => {
  //     setIsTalking(true);
  //     setTimeout(() => setIsTalking(false), 2000); // talk for 2 seconds
  //   }, 4000);

  //   return () => clearInterval(talkInterval);
  // }, []);

  // Fluid mouth animation during talking
  useEffect(() => {
    let mouthInterval;
    
    if (isTalking) {
      // Create a sequence of mouth states for natural talking
      const talkingSequence = ['smile', 'medium', 'open', 'medium', 'open', 'smile', 'medium'];
      let sequenceIndex = 0;
      
      mouthInterval = setInterval(() => {
        setMouthState(talkingSequence[sequenceIndex]);
        sequenceIndex = (sequenceIndex + 1) % talkingSequence.length;
      }, 150); // Smoother transitions every 150ms
    } else {
      // Smooth transition back to smile
      setMouthState('smile');
    }

    return () => {
      if (mouthInterval) clearInterval(mouthInterval);
    };
  }, [isTalking]);

  // Blink every 3–5 seconds with more natural timing
  useEffect(() => {
    const blink = () => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), 120); // slightly shorter blink duration
    };

    const scheduleNextBlink = () => {
      const nextBlinkTime = Math.random() * 3000 + 2000; // 2–5 sec
      setTimeout(() => {
        blink();
        scheduleNextBlink();
      }, nextBlinkTime);
    };

    scheduleNextBlink();
  }, []);

  return (
    <div className="emoji-container">
      {/* Floating wrapper for the entire avatar */}
      <div className="floating-wrapper">
        {/* Halo */}
        <div className="halo"></div>
        
        {/* Face */}
        <div className="face">
          {/* Eyes */}
          <div className="eyes">
            <div className={`eye left ${isBlinking ? 'blink' : ''}`}></div>
            <div className={`eye right ${isBlinking ? 'blink' : ''}`}></div>
          </div>

          {/* Mouth */}
          <div className="mouth">
            {mouthState === 'open' && <div className={`mouth-open ${isTalking ? 'animated' : ''}`}></div>}
            {mouthState === 'medium' && <div className="mouth-medium"></div>}
            {mouthState === 'smile' && <div className="mouth-smile"></div>}
          </div>
        </div>

        {/* Cloud underneath */}
        <div className="cloud"></div>

        {/* Star particles */}
        <div className="stars-container">
          <div className="star"></div>
          <div className="star"></div>
          <div className="star"></div>
          <div className="star"></div>
          <div className="star"></div>
          <div className="star"></div>
          <div className="star"></div>
          <div className="star"></div>
        </div>

        {/* Wind effects */}
        <div className="wind-container">
          <div className="wind-line"></div>
          <div className="wind-line"></div>
          <div className="wind-line"></div>
          <div className="wind-line"></div>
          <div className="wind-line"></div>
          <div className="wind-particle"></div>
          <div className="wind-particle"></div>
          <div className="wind-particle"></div>
          <div className="wind-particle"></div>
          <div className="wind-particle"></div>
        </div>
      </div>

      {/* Button to manually trigger talking (only show if onTalkingToggle is provided) */}
      {onTalkingToggle && (
        <button onClick={handleTalkingToggle} className="talk-button">
          {isTalking ? 'Stop Talking' : 'Start Talking'}
        </button>
      )}
    </div>
  );
};

export default EmojiAvatar;