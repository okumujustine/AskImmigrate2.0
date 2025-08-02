import { Bot, User } from 'lucide-react';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../types/chat';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  return (
    <div className="conversation-container">
      {/* User Question */}
      <div className="message user-message">
        <div className="message-content">
          <div className="message-text">{message.question}</div>
        </div>
        <div className="message-avatar">
          <User size={20} />
        </div>
      </div>
      
      {/* AI Answer */}
      <div className="message ai-message">
        <div className="message-avatar">
          <Bot size={20} />
        </div>
        <div className="message-content">
          <div className="message-text">
            <ReactMarkdown>{message.answer}</ReactMarkdown>
          </div>
          <div className="message-timestamp">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};
