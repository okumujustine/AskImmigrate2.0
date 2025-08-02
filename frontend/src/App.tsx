import { useCallback, useEffect, useRef, useState } from 'react';
import './App.css';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { ChatSidebar } from './components/ChatSidebar';
import { LoadingMessage } from './components/LoadingMessage';
import { SessionStatus } from './components/SessionStatus';
import { askQuestion, createNewChatSession, getChatSessions } from './services/api';
import { getPersistentBrowserFingerprint } from './services/browserFingerprint';
import type { ChatSession, User } from './types/chat';

function App() {
  // Initialize user with browser fingerprint for anonymous isolation
  const [user] = useState<User>(() => {
    const clientId = getPersistentBrowserFingerprint();
    return { id: clientId, name: 'User' };
  });
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentSession?.messages]);

  const loadChatSessions = useCallback(async () => {
    try {
      const sessions = await getChatSessions(user.id);
      setChatSessions(sessions);
      if (sessions.length > 0) {
        setCurrentSession(sessions[0]);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
      setError('Failed to load chat sessions');
    }
  }, [user.id]);

  useEffect(() => {
    loadChatSessions();
  }, [loadChatSessions]);

  const handleNewChat = async () => {
    try {
      const newSession = await createNewChatSession(user.id);
      const chatSession: ChatSession = {
        id: newSession.id,
        title: 'New Chat',
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      
      setChatSessions([chatSession, ...chatSessions]);
      setCurrentSession(chatSession);
      setError(null);
    } catch (error) {
      console.error('Failed to create new chat:', error);
      setError('Failed to create new chat');
    }
  };

  const handleSessionSelect = (sessionId: string) => {
    const session = chatSessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSession(session);
      setError(null);
    }
  };

  const handleSendMessage = async (question: string) => {
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      // If no current session, create a new one
      let sessionToUse = currentSession;
      if (!sessionToUse) {
        await handleNewChat();
        sessionToUse = currentSession;
      }

      const { message, sessionId } = await askQuestion(
        question,
        user.id,
        sessionToUse?.id
      );

      // Update the current session with the new message
      const isNewChat = sessionToUse?.title === 'New Chat' || !sessionToUse;
      const updatedSession: ChatSession = {
        id: sessionId,
        title: isNewChat ? question.slice(0, 50) + (question.length > 50 ? '...' : '') : sessionToUse!.title,
        messages: [...(sessionToUse?.messages || []), message],
        createdAt: sessionToUse?.createdAt || new Date(),
        updatedAt: new Date(),
      };

      // Update sessions list
      const updatedSessions = sessionToUse
        ? chatSessions.map(s => s.id === sessionToUse.id ? updatedSession : s)
        : [updatedSession, ...chatSessions];

      setChatSessions(updatedSessions);
      setCurrentSession(updatedSession);
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <ChatSidebar
        chatSessions={chatSessions}
        currentSessionId={currentSession?.id || null}
        onSessionSelect={handleSessionSelect}
        onNewChat={handleNewChat}
      />
      
      <main className="chat-main">
        <SessionStatus 
          hasSessionId={currentSession ? !currentSession.id.startsWith('new-session-') : false}
          sessionId={currentSession?.id}
        />
        
        <div className="chat-container">
          {currentSession && currentSession.messages.length > 0 ? (
            <div className="messages-container">
              {currentSession.messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && <LoadingMessage />}
              <div ref={messagesEndRef} />
            </div>
          ) : (
            <div className="empty-state">
              <h1>Welcome to AskImmigrate</h1>
              <p>Ask any question about immigration and get detailed answers.</p>
              <div className="example-questions">
                <h3>Example questions:</h3>
                <ul>
                  <li>"What is an F1 visa?"</li>
                  <li>"How to apply for a Green Card?"</li>
                  <li>"What documents do I need for H1B?"</li>
                </ul>
              </div>
            </div>
          )}
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
        </div>
        
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          hasSessionId={currentSession ? !currentSession.id.startsWith('new-session-') : false}
        />
      </main>
    </div>
  );
}

export default App;
