// src/App.tsx - Updated with UI language selector always enabled

import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import { ChatInput } from "./components/ChatInput";
import { ChatMessage } from "./components/ChatMessage";
import { ChatSidebar } from "./components/ChatSidebar";
import { LoadingMessage } from "./components/LoadingMessage";
import { SessionStatus } from "./components/SessionStatus";
import { LanguageSelector } from "./components/LanguageSelector";
import {
  askQuestion,
  createNewChatSession,
  getChatSessions,
} from "./services/api";
import { getPersistentBrowserFingerprint } from "./services/browserFingerprint";
import multilingualService from "./services/multilingualService";
import type { ChatSession, User } from "./types/chat";

function App() {
  // Initialize user with browser fingerprint for anonymous isolation
  const [user] = useState<User>(() => {
    const clientId = getPersistentBrowserFingerprint();
    return { id: clientId, name: "User" };
  });

  // Language state
  const [currentLanguage, setCurrentLanguage] = useState<string>(() =>
    multilingualService.getCurrentLanguage()
  );
  const [uiStrings, setUiStrings] = useState(() =>
    multilingualService.getUIStrings(currentLanguage)
  );
  const [exampleQuestions, setExampleQuestions] = useState(() =>
    multilingualService.getExampleQuestions(currentLanguage)
  );
  const [multilingualAvailable] = useState(true); // Always enabled for UI language switching

  // Chat state
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponseMetadata, setLastResponseMetadata] = useState<any>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentSession?.messages]);

  // UI Language selector is always enabled
  useEffect(() => {
    console.log(
      "UI language selector enabled for interface language switching"
    );
  }, []);

  // Handle language changes
  const handleLanguageChange = (languageCode: string) => {
    console.log("Changing UI language to:", languageCode);

    multilingualService.setLanguage(languageCode);
    setCurrentLanguage(languageCode);

    // Update UI strings and examples
    const newStrings = multilingualService.getUIStrings(languageCode);
    const newExamples = multilingualService.getExampleQuestions(languageCode);

    setUiStrings(newStrings);
    setExampleQuestions(newExamples);

    // Show language change notification
    console.log(`Language changed to ${languageCode}`);
  };

  const loadChatSessions = useCallback(async () => {
    try {
      const sessions = await getChatSessions(user.id);
      setChatSessions(sessions);
      if (sessions.length > 0) {
        setCurrentSession(sessions[0]);
      }
    } catch (error) {
      console.error("Failed to load chat sessions:", error);
      setError(uiStrings.errorLoading);
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
        title: uiStrings.newChat,
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      setChatSessions([chatSession, ...chatSessions]);
      setCurrentSession(chatSession);
      setError(null);
      setLastResponseMetadata(null);
    } catch (error) {
      console.error("Failed to create new chat:", error);
      setError(uiStrings.errorCreating);
    }
  };

  const handleSessionSelect = (sessionId: string) => {
    const session = chatSessions.find((s) => s.id === sessionId);
    if (session) {
      setCurrentSession(session);
      setError(null);
      setLastResponseMetadata(null);
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

      // Ask question with multilingual support (auto-detection)
      const result = await askQuestion(question, user.id, sessionToUse?.id);

      // Store response metadata for debugging
      if (result.metadata) {
        setLastResponseMetadata(result.metadata);
        console.log("Response metadata:", result.metadata);
      }

      // Update the current session with the new message
      const isNewChat =
        sessionToUse?.title === uiStrings.newChat || !sessionToUse;
      const updatedSession: ChatSession = {
        id: result.sessionId,
        title: isNewChat
          ? question.slice(0, 50) + (question.length > 50 ? "..." : "")
          : sessionToUse!.title,
        messages: [...(sessionToUse?.messages || []), result.message],
        createdAt: sessionToUse?.createdAt || new Date(),
        updatedAt: new Date(),
      };

      // Update sessions list
      const updatedSessions = sessionToUse
        ? chatSessions.map((s) =>
            s.id === sessionToUse.id ? updatedSession : s
          )
        : [updatedSession, ...chatSessions];

      setChatSessions(updatedSessions);
      setCurrentSession(updatedSession);

      // If we detected a different language than UI, show info but don't force switch
      if (
        result.language &&
        result.language !== currentLanguage &&
        result.language !== "en"
      ) {
        const langInfo = multilingualService
          .getSupportedLanguages()
          .find((l) => l.code === result.language);
        if (langInfo && langInfo.available) {
          console.log(
            `Question detected in ${langInfo.nativeName}. Response generated in that language.`
          );
        }
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      setError(uiStrings.errorSending);
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
        uiStrings={uiStrings}
        languageSelector={
          <LanguageSelector
            currentLanguage={currentLanguage}
            onLanguageChange={handleLanguageChange}
          />
        }
      />

      <main className="chat-main">
        <SessionStatus
          hasSessionId={
            currentSession
              ? !currentSession.id.startsWith("new-session-")
              : false
          }
          sessionId={currentSession?.id}
          responseMetadata={lastResponseMetadata}
        />

        <div className="chat-container">
          {currentSession && currentSession.messages.length > 0 ? (
            <div className="messages-container">
              {currentSession.messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && <LoadingMessage uiStrings={uiStrings} />}
              <div ref={messagesEndRef} />
            </div>
          ) : (
            <div className="empty-state">
              <h1>{uiStrings.welcome}</h1>
              <p>{uiStrings.welcomeDescription}</p>
              <div className="example-questions">
                <h3>{uiStrings.exampleQuestions}</h3>
                <ul>
                  {exampleQuestions.map((question, index) => (
                    <li key={index}>{question}</li>
                  ))}
                </ul>
              </div>

              <div className="language-features">
                <p className="language-note">
                  🌍{" "}
                  {currentLanguage === "en"
                    ? "Ask questions in any language - responses will match your question language!"
                    : "¡Haga preguntas en cualquier idioma - las respuestas coincidirán con el idioma de su pregunta!"}
                </p>
                <p className="ui-language-note">
                  💡{" "}
                  {currentLanguage === "en"
                    ? "Use the language selector above to change the interface language."
                    : "Use el selector de idioma arriba para cambiar el idioma de la interfaz."}
                </p>
              </div>
            </div>
          )}

          {error && <div className="error-message">{error}</div>}
        </div>

        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          hasSessionId={
            currentSession
              ? !currentSession.id.startsWith("new-session-")
              : false
          }
          uiStrings={uiStrings}
        />
      </main>
    </div>
  );
}

export default App;
