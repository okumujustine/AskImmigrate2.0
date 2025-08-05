import { Bot, Brain, Search, Sparkles } from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface LoadingMessageProps {
  startTime?: number;
}

const loadingMessages = [
  "Analyzing your question",
  "Searching immigration database",
  "Processing legal information",
  "Reviewing relevant documents",
  "Compiling comprehensive answer"
];

export const LoadingMessage: React.FC<LoadingMessageProps> = ({ startTime }) => {
  const [showDelayedMessage, setShowDelayedMessage] = useState(false);
  const [dots, setDots] = useState('');
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);

  useEffect(() => {
    if (!startTime) return;

    const timer = setTimeout(() => {
      setShowDelayedMessage(true);
    }, 4000);

    return () => clearTimeout(timer);
  }, [startTime]);

  useEffect(() => {
    const dotsInterval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(dotsInterval);
  }, []);

  useEffect(() => {
    if (!showDelayedMessage) return;
    
    const messageInterval = setInterval(() => {
      setCurrentMessageIndex(prev => (prev + 1) % loadingMessages.length);
    }, 2000);

    return () => clearInterval(messageInterval);
  }, [showDelayedMessage]);

  return (
    <div className="conversation-container">
      <div className="message ai-message">
        <div className="message-avatar">
          <Bot size={20} />
        </div>
        <div className="message-content">
          <div className="loading-content">
            <div className="elegant-loader">
              <div className="loader-dots">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
              {showDelayedMessage ? (
                <Search className="search-icon" size={16} />
              ) : (
                <Brain className="brain-icon" size={16} />
              )}
            </div>
            <div className="loading-text">
              {showDelayedMessage ? (
                <div className="delayed-message">
                  <div className="quality-message">
                    <Sparkles size={14} className="sparkle-icon" />
                    <span>Taking our time to provide you with the most accurate and comprehensive answer{dots}</span>
                  </div>
                  <div className="process-indicator">
                    <span className="process-text">{loadingMessages[currentMessageIndex]}{dots}</span>
                  </div>
                  <div className="patience-note">
                    We're analyzing multiple sources to ensure quality
                  </div>
                </div>
              ) : (
                <span className="thinking-text">{loadingMessages[0]}{dots}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
