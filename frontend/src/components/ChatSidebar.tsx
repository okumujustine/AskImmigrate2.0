import { MessageCircle, Plus } from 'lucide-react';
import React from 'react';
import type { ChatSession } from '../types/chat';

interface ChatSidebarProps {
  chatSessions: ChatSession[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  chatSessions,
  currentSessionId,
  onSessionSelect,
  onNewChat,
}) => {
  const isNewSession = (sessionId: string) => sessionId.startsWith('new-session-');
  
  const truncateTitle = (title: string, maxLength: number = 30) => {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  };

  const truncateSessionId = (sessionId: string, maxLength: number = 25) => {
    if (sessionId.length <= maxLength) return sessionId;
    return sessionId.substring(0, maxLength) + '...';
  };

  return (
    <div className="chat-sidebar">
      <div className="sidebar-header">
        <h2>AskImmigrate</h2>
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={16} />
          New Chat
        </button>
      </div>
      
      <div className="chat-sessions">
        {chatSessions.map((session) => (
          <div
            key={session.id}
            className={`chat-session-item ${
              session.id === currentSessionId ? 'active' : ''
            } ${isNewSession(session.id) ? 'new-session' : ''}`}
            onClick={() => onSessionSelect(session.id)}
          >
            <div className="session-icon-container">
              <MessageCircle size={16} />
            </div>
            <div className="session-info">
              <div 
                className="session-title"
                title={
                  (session.title === session.id && session.title.length > 25) ||
                  (session.title !== session.id && session.title.length > 30)
                    ? session.title 
                    : undefined
                }
              >
                {session.title === session.id ? 
                  truncateSessionId(session.title) : 
                  truncateTitle(session.title)
                }
              </div>
              <div className="session-date">
                {session.updatedAt.toLocaleDateString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
