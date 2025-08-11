import { Bot, Loader2 } from "lucide-react";
import React from "react";

interface LoadingMessageProps {
  uiStrings?: Record<string, string>;
}

export const LoadingMessage: React.FC<LoadingMessageProps> = ({
  uiStrings,
}) => {
  return (
    <div className="conversation-container">
      <div className="message ai-message">
        <div className="message-avatar">
          <Bot size={20} />
        </div>
        <div className="message-content">
          <div className="loading-content">
            <Loader2 className="spinner" size={16} />
            <span>{uiStrings?.thinking}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
