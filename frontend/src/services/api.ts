import type { Message } from '../types/chat';
import { mockAskQuestion } from './mockApi';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8088';
const USE_MOCK_API = false; // Set to true to use mock API instead of real API

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

export const askQuestion = async (
  question: string,
  userId: string,
  chatSessionId?: string
): Promise<{ message: Message; sessionId: string }> => {
  if (USE_MOCK_API) {
    return mockAskQuestion(question, userId, chatSessionId);
  }

  try {
    const requestBody: { question: string; session_id?: string } = {
      question,
    };

    // Include session_id if we have one
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
    
    // Create message from the API response
    const message: Message = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      question: question,
      answer: cleanAnswer(data.answer, question),
      timestamp: new Date(),
    };

    return {
      message,
      sessionId: data.session_id,
    };
  } catch (error) {
    console.error('Error asking question:', error);
    throw error;
  }
};

// Function to get session messages from your API
export const getSessionMessages = async (
  _userId: string,
  sessionId: string
): Promise<Message[]> => {
  if (USE_MOCK_API) {
    // For mock, return empty array - messages are added as user interacts
    return [];
  }

  try {
    const response = await fetch(`${API_BASE_URL}/answers/${sessionId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch session messages');
    }

    const data: Array<{ question: string; answer: string }> = await response.json();
    
    // Convert the API response to Message format
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
    // Return empty array for mock - sessions will be created as user interacts
    return [];
  }

  try {
    const response = await fetch(`${API_BASE_URL}/session-ids`);
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

export const createNewChatSession = async (userId: string) => {
  if (USE_MOCK_API) {
    return {
      id: `session-${Date.now()}`,
      userId,
      title: 'New Chat',
      createdAt: new Date().toISOString(),
    };
  }

  // For your API, new sessions are created automatically when sending the first message
  // So we just return a placeholder that will be replaced when the first message is sent
  return {
    id: `new-session-${Date.now()}`,
    userId,
    title: 'New Chat',
    createdAt: new Date().toISOString(),
  };
};
