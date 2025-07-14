# AskImmigrate RAG Tool UI

A modern, responsive chat interface for an immigration-focused RAG (Retrieval-Augmented Generation) tool. Built with React, TypeScript, and Vite.

## Features

- **Chat Interface**: Clean, modern chat UI similar to ChatGPT with side-by-side conversation layout
- **Markdown Rendering**: Full markdown support for rich text formatting in AI responses
- **Multiple Chat Sessions**: Users can create and manage multiple chat sessions with status indicators
- **Session Management**: Visual indicators for new/existing sessions in sidebar and chat area
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Real-time Loading States**: Visual feedback while processing questions
- **Error Handling**: Graceful error handling with user-friendly messages
- **Mock API Integration**: Includes demo responses for testing with markdown examples

## Demo Questions

Try asking these questions to see the RAG tool in action:

- "What is an F1 visa?"
- "How to apply for a Green Card?"
- "What documents do I need for H1B?"
- "Show me markdown formatting" (demonstrates rich text rendering)
- Any other immigration-related question

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   Navigate to `http://localhost:5173` (or the port shown in your terminal)

## API Integration

### Current Setup (Mock API)

The application currently uses a mock API for demonstration purposes. Set `USE_MOCK_API = false` in `src/services/api.ts` to use your real API.

### Real API Integration

The application is configured to work with your backend API and includes automatic answer cleaning to remove question prefixes. The API endpoints used are:

1. **POST `/query`** - Send a question and get a response
   ```typescript
   // Request body (new question)
   {
     "question": "What is an F1 visa?"
   }
   
   // Request body (continue existing session)
   {
     "question": "Tell me more about this",
     "session_id": "how-can-i-get-an-f1-39e655f2"
   }
   
   // Response
   {
     "answer": "An F1 visa is a non-immigrant student visa...",
     "session_id": "how-can-i-get-an-f1-39e655f2"
   }
   ```

2. **GET `/session-ids`** - Get all available session IDs
   ```json
   [
     "the-immigration-proc-71bddffb",
     "how-can-i-get-an-f1-39e655f2",
     "test-session-20250713-172554"
   ]
   ```

3. **GET `/history/{session_id}`** - Get conversation history for a session
   ```json
   [
     {
       "question": "What is eb5",
       "answer": "The EB-5 visa program is a United States immigration program..."
     },
     {
       "question": "explain more?",
       "answer": "I understand that you're looking for more information..."
     }
   ]
   ```

### API Configuration

To switch between mock and real API:

```typescript
// In src/services/api.ts
const API_BASE_URL = 'http://127.0.0.1:8088';  // Your API URL
const USE_MOCK_API = false;  // Set to true for demo mode
```

## Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_URL=https://your-api-domain.com/api
```

## Building for Production

```bash
npm run build
```

## Technologies Used

- **React 19** - UI framework
- **TypeScript** - Type safety and better development experience
- **Vite** - Fast build tool and development server
- **React Markdown** - Markdown rendering for rich text content
- **Lucide React** - Modern icon library
- **CSS3** - Responsive styling with modern features

## Architecture

The application follows a component-based architecture with:
- Type-safe API integration
- Reusable UI components
- Centralized state management
- Responsive design patterns
- Error boundaries and loading states
