import { MessageSquare } from "lucide-react";
import React from "react";

interface SessionStatusProps {
  hasSessionId: boolean;
  sessionId?: string;
  uiStrings: Record<string, string>;
}

export const SessionStatus: React.FC<SessionStatusProps> = ({
  hasSessionId,
  sessionId,
  uiStrings,
}) => {
  const truncateSessionId = (id: string, maxLength: number = 20) => {
    if (id.length <= maxLength) return id;
    return id.substring(0, maxLength) + "...";
  };

  const displayText = hasSessionId
    ? `${uiStrings.sessionActive} ${truncateSessionId(sessionId || "", 20)}`
    : uiStrings.sessionReady;

  return (
    <div className="session-status">
      <div className="status-indicator">
        <MessageSquare size={16} className="status-icon" />
        <span
          className="status-text"
          title={
            hasSessionId && sessionId && sessionId.length > 20
              ? `${uiStrings.sessionActive} ${sessionId}`
              : undefined
          }
        >
          {displayText}
        </span>
      </div>
    </div>
  );
};
