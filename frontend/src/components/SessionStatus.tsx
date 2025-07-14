import { MessageSquare } from 'lucide-react';
import React from 'react';

interface SessionStatusProps {
  hasSessionId: boolean;
  sessionId?: string;
}

export const SessionStatus: React.FC<SessionStatusProps> = ({ hasSessionId, sessionId }) => {
  const truncateSessionId = (id: string, maxLength: number = 20) => {
    if (id.length <= maxLength) return id;
    return id.substring(0, maxLength) + '...';
  };

  const displayText = hasSessionId 
    ? `Session: ${truncateSessionId(sessionId || '', 20)}`
    : 'Ready to chat';

  return (
    <div className="session-status">
      <div className="status-indicator">
        <MessageSquare size={16} className="status-icon" />
        <span 
          className="status-text"
          title={hasSessionId && sessionId && sessionId.length > 20 ? `Session: ${sessionId}` : undefined}
        >
          {displayText}
        </span>
      </div>
    </div>
  );
};
