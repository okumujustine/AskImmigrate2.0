/**
 * Session Storage Service for Client-Isolated Session Management
 * Handles persistence of chat sessions scoped to browser fingerprint
 */

import type { ChatSession } from '../types/chat';
import { getPersistentBrowserFingerprint } from './browserFingerprint';

const SESSIONS_STORAGE_KEY = 'askimmigrate_sessions';
const SESSION_EXPIRY_DAYS = 30; // Sessions expire after 30 days

interface StoredSession {
  session: ChatSession;
  clientFingerprint: string;
  expiresAt: number;
}

interface SessionStorage {
  sessions: StoredSession[];
  lastUpdated: number;
}

/**
 * Get the current client fingerprint
 */
function getCurrentClientFingerprint(): string {
  return getPersistentBrowserFingerprint();
}

/**
 * Get all stored sessions from localStorage
 */
function getStoredSessions(): SessionStorage {
  try {
    const stored = localStorage.getItem(SESSIONS_STORAGE_KEY);
    if (!stored) {
      return { sessions: [], lastUpdated: Date.now() };
    }
    
    const parsed: SessionStorage = JSON.parse(stored);
    
    // Clean up expired sessions
    const now = Date.now();
    const validSessions = parsed.sessions.filter(s => s.expiresAt > now);
    
    if (validSessions.length !== parsed.sessions.length) {
      // Save cleaned up sessions
      const cleaned: SessionStorage = {
        sessions: validSessions,
        lastUpdated: now
      };
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(cleaned));
      return cleaned;
    }
    
    return parsed;
  } catch (error) {
    console.warn('Failed to load stored sessions:', error);
    return { sessions: [], lastUpdated: Date.now() };
  }
}

/**
 * Save sessions to localStorage
 */
function saveStoredSessions(sessionStorage: SessionStorage): void {
  try {
    sessionStorage.lastUpdated = Date.now();
    localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessionStorage));
  } catch (error) {
    console.warn('Failed to save sessions to localStorage:', error);
  }
}

/**
 * Get sessions for the current client only
 */
export function getClientSessions(): ChatSession[] {
  const clientFingerprint = getCurrentClientFingerprint();
  const stored = getStoredSessions();
  
  return stored.sessions
    .filter(s => s.clientFingerprint === clientFingerprint)
    .map(s => ({
      ...s.session,
      // Convert string dates back to Date objects
      createdAt: new Date(s.session.createdAt),
      updatedAt: new Date(s.session.updatedAt),
    }))
    .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()); // Most recent first
}

/**
 * Save a session for the current client
 */
export function saveClientSession(session: ChatSession): void {
  const clientFingerprint = getCurrentClientFingerprint();
  const stored = getStoredSessions();
  
  const expiresAt = Date.now() + (SESSION_EXPIRY_DAYS * 24 * 60 * 60 * 1000);
  
  const storedSession: StoredSession = {
    session: {
      ...session,
      updatedAt: new Date(), // Update timestamp
    },
    clientFingerprint,
    expiresAt
  };
  
  // Remove existing session with same ID
  const filteredSessions = stored.sessions.filter(s => s.session.id !== session.id);
  
  // Add the new/updated session
  const updatedStorage: SessionStorage = {
    sessions: [...filteredSessions, storedSession],
    lastUpdated: Date.now()
  };
  
  saveStoredSessions(updatedStorage);
}

/**
 * Update an existing session for the current client
 */
export function updateClientSession(sessionId: string, updates: Partial<ChatSession>): void {
  const sessions = getClientSessions();
  const sessionIndex = sessions.findIndex(s => s.id === sessionId);
  
  if (sessionIndex !== -1) {
    const updatedSession = {
      ...sessions[sessionIndex],
      ...updates,
      updatedAt: new Date()
    };
    
    saveClientSession(updatedSession);
  }
}

/**
 * Delete a session for the current client
 */
export function deleteClientSession(sessionId: string): void {
  const clientFingerprint = getCurrentClientFingerprint();
  const stored = getStoredSessions();
  
  const filteredSessions = stored.sessions.filter(
    s => !(s.session.id === sessionId && s.clientFingerprint === clientFingerprint)
  );
  
  const updatedStorage: SessionStorage = {
    sessions: filteredSessions,
    lastUpdated: Date.now()
  };
  
  saveStoredSessions(updatedStorage);
}

/**
 * Clear all sessions for the current client
 */
export function clearClientSessions(): void {
  const clientFingerprint = getCurrentClientFingerprint();
  const stored = getStoredSessions();
  
  const filteredSessions = stored.sessions.filter(
    s => s.clientFingerprint !== clientFingerprint
  );
  
  const updatedStorage: SessionStorage = {
    sessions: filteredSessions,
    lastUpdated: Date.now()
  };
  
  saveStoredSessions(updatedStorage);
}

/**
 * Get storage statistics for debugging
 */
export function getSessionStorageStats(): {
  totalSessions: number;
  clientSessions: number;
  storageSize: number;
  lastUpdated: Date;
  currentClient: string;
} {
  const stored = getStoredSessions();
  const clientFingerprint = getCurrentClientFingerprint();
  const clientSessions = stored.sessions.filter(s => s.clientFingerprint === clientFingerprint);
  
  let storageSize = 0;
  try {
    const storedString = localStorage.getItem(SESSIONS_STORAGE_KEY) || '';
    storageSize = new Blob([storedString]).size;
  } catch (error) {
    // Ignore size calculation errors
  }
  
  return {
    totalSessions: stored.sessions.length,
    clientSessions: clientSessions.length,
    storageSize,
    lastUpdated: new Date(stored.lastUpdated),
    currentClient: clientFingerprint
  };
}
