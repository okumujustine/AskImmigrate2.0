export interface Message {
  id: string;
  question: string;
  answer: string;
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface User {
  id: string;
  name: string;
}

// API Response interfaces for the new JSON format
export interface ApiQuestionAnswer {
  question: string;
  answer: string;
}

export interface ApiResponse {
  session_id: string;
  // For single question response
  question?: string;
  answer?: string;
  // For multiple messages response
  messages?: ApiQuestionAnswer[];
}
