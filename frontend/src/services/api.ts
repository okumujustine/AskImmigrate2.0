import type { Message } from '../types/chat';
import { mockAskQuestion } from './mockApi';
import { getPersistentBrowserFingerprint } from './browserFingerprint';
import { multilingualService } from './multilingualService';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8088';
const USE_MOCK_API = false; // Set to true to use mock API instead of real API

interface MultilingualResponse {
  answer: string;
  session_id: string;
  language: string;
  metadata: {
    translation_method?: string;
    confidence?: number;
    processing_time?: number;
    target_language?: string;
    multilingual_processing?: boolean;
    service_health?: string;
    [key: string]: any;
  };
}

// Helper function to clean answers by removing question prefixes
const cleanAnswer = (answer: string, question: string): string => {
  let cleaned = answer;
  
  // Split the answer into lines to process line by line
  const lines = cleaned.split('\n');
  let startIndex = 0;
  
  // Find where the actual answer starts by skipping question lines
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip empty lines
    if (line === '') {
      continue;
    }
    
    // Check if this line contains a question prefix
    if (line.match(/^Your Question:/i) || 
        line.match(/^Question:/i) || 
        line.match(/^Q:/i) ||
        line.match(/^Su Pregunta:/i) ||
        line.match(/^Pregunta:/i) ||
        line.includes(question)) {
      startIndex = i + 1;
      continue;
    }
    
    // If we reach here, this line doesn't look like a question, so start from here
    startIndex = i;
    break;
  }
  
  // Join the remaining lines
  cleaned = lines.slice(startIndex).join('\n');
  
  // Remove leading whitespace and empty lines
  cleaned = cleaned.replace(/^\s*\n*/, '').trim();
  
  return cleaned;
};

// Auto-detect language from user input
const detectQuestionLanguage = async (question: string): Promise<string> => {
  try {
    const detection = await multilingualService.detectLanguage(question);
    if (detection.supported && detection.confidence > 0.6) {
      return detection.language;
    }
  } catch (error) {
    console.warn('Language detection failed:', error);
  }
  
  // Fallback to current UI language
  return multilingualService.getCurrentLanguage();
};

export const askQuestion = async (
  question: string,
  userId: string,
  chatSessionId?: string
): Promise<{ message: Message; sessionId: string; language?: string; metadata?: any }> => {
  if (USE_MOCK_API) {
    const result = await mockAskQuestion(question, userId, chatSessionId);
    return { ...result, language: 'en' };
  }

  try {
    // Get client fingerprint for session isolation
    const clientFingerprint = getPersistentBrowserFingerprint();
    
    // Detect question language or use current UI language
    const questionLanguage = await detectQuestionLanguage(question);
    
    // Determine if we should use multilingual endpoint
    const useMultilingual = questionLanguage !== 'en' || multilingualService.getCurrentLanguage() !== 'en';
    
    if (useMultilingual) {
      // Use multilingual endpoint
      return await askQuestionMultilingual(question, userId, chatSessionId, questionLanguage, clientFingerprint);
    } else {
      // Use standard endpoint for English
      return await askQuestionStandard(question, userId, chatSessionId, clientFingerprint);
    }
    
  } catch (error) {
    console.error('Error asking question:', error);
    throw error;
  }
};

// Standard English API call
const askQuestionStandard = async (
  question: string,
  userId: string,
  chatSessionId: string | undefined,
  clientFingerprint: string
): Promise<{ message: Message; sessionId: string; language: string }> => {
  const requestBody: { 
    question: string; 
    session_id?: string;
    client_fingerprint: string;
  } = {
    question,
    client_fingerprint: clientFingerprint,
  };

  if (chatSessionId) {
    requestBody.session_id = chatSessionId;
  }

  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new Error('Failed to get response from API');
  }

  const data: { answer: string; session_id: string } = await response.json();
  
  const message: Message = {
    id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    question: question,
    answer: cleanAnswer(data.answer, question),
    timestamp: new Date(),
  };

  return {
    message,
    sessionId: data.session_id,
    language: 'en'
  };
};
// Multilingual API call
const askQuestionMultilingual = async (
  question: string,
  userId: string,
  chatSessionId: string | undefined,
  detectedLanguage: string,
  clientFingerprint: string
): Promise<{ message: Message; sessionId: string; language: string; metadata: any }> => {
  const requestBody: {
    question: string;
    language: string;
    client_fingerprint: string;
    session_id?: string;  // Optional now
  } = {
    question,
    language: detectedLanguage === 'auto' ? 'auto' : detectedLanguage,
    client_fingerprint: clientFingerprint,
  };

  // CHANGE: Only send session_id if it's a real backend session (not frontend temp)
  if (chatSessionId && !chatSessionId.startsWith('new-')) {
    requestBody.session_id = chatSessionId;
  }
  // If no valid session_id, backend will create new session

  console.log('Making multilingual request:', { 
    language: detectedLanguage, 
    question: question.substring(0, 50),
    hasSessionId: !!requestBody.session_id,
    sessionId: requestBody.session_id
  });

  const response = await fetch(`${API_BASE_URL}/api/chat/multilingual`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('Multilingual API error:', errorText);
    throw new Error(`Multilingual API failed: ${response.status}`);
  }

  const data: MultilingualResponse = await response.json();
  
  console.log('Multilingual response received:', {
    language: data.language,
    method: data.metadata.translation_method,
    answerLength: data.answer.length,
    returnedSessionId: data.session_id  // Log what session ID backend returned
  });
  
  const message: Message = {
    id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    question: question,
    answer: cleanAnswer(data.answer, question),
    timestamp: new Date(),
  };

  return {
    message,
    sessionId: data.session_id,  // Use whatever session ID backend returns
    language: data.language,
    metadata: data.metadata
  };
};

// Function to get session messages from your API
export const getSessionMessages = async (
  _userId: string,
  sessionId: string
): Promise<Message[]> => {
  if (USE_MOCK_API) {
    return [];
  }

  try {
    const response = await fetch(`${API_BASE_URL}/answers/${sessionId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch session messages');
    }

    const data: Array<{ question: string; answer: string }> = await response.json();
    
    return data.map((msg, index) => ({
      id: `${sessionId}-${index}-${Date.now()}`,
      question: msg.question,
      answer: cleanAnswer(msg.answer, msg.question),
      timestamp: new Date(),
    }));
  } catch (error) {
    console.error('Error fetching session messages:', error);
    return [];
  }
};

export const getChatSessions = async (userId: string) => {
  if (USE_MOCK_API) {
    return [];
  }

  try {
    const clientFingerprint = getPersistentBrowserFingerprint();
    
    const url = new URL(`${API_BASE_URL}/session-ids`);
    url.searchParams.append('client_fingerprint', clientFingerprint);
    
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error('Failed to fetch chat sessions');
    }
    
    const sessionIds: string[] = await response.json();
    
    // Convert session IDs to ChatSession format
    const sessions = await Promise.all(
      sessionIds.map(async (sessionId) => {
        const messages = await getSessionMessages(userId, sessionId);
        const title = messages.length > 0 
          ? messages[0].question.substring(0, 50) + (messages[0].question.length > 50 ? '...' : '')
          : sessionId;
        
        return {
          id: sessionId,
          title,
          messages,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
      })
    );
    
    return sessions;
  } catch (error) {
    console.error('Error fetching chat sessions:', error);
    return [];
  }
};


// Health check for multilingual services
export const checkMultilingualHealth = async (): Promise<{
  available: boolean;
  languages: string[];
  status: string;
}> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/multilingual/health`);
    if (response.ok) {
      const health = await response.json();
      return {
        available: true, // Always show UI language selector
        languages: health.capabilities ? Object.keys(health.capabilities).filter(k => health.capabilities[k]) : ['en', 'es'],
        status: health.status
      };
    }
  } catch (error) {
    console.warn('Multilingual health check failed:', error);
  }
  
  // Always return true for UI language selection, even if backend is unavailable
  return {
    available: true, // UI language selector always available
    languages: ['en', 'es', 'fr', 'pt'],
    status: 'ui_only'
  };
};