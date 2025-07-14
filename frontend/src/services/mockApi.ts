import type { Message } from '../types/chat';

// Mock demo responses for different questions in the new JSON format
const mockResponses: Record<string, { question: string; answer: string }> = {
  'markdown': {
    question: 'Show me markdown formatting',
    answer: `# Immigration Guide: Markdown Example

This response demonstrates **markdown formatting** capabilities:

## Headers and Text Formatting

- **Bold text** for emphasis
- *Italic text* for subtle emphasis
- \`Inline code\` for technical terms like Form I-485

## Lists and Organization

### Unordered Lists:
- First item
- Second item with **bold text**
- Third item with *italic text*

### Ordered Lists:
1. File Form I-130 or I-140
2. Wait for priority date to become current
3. File Form I-485 (Adjustment of Status)
4. Attend biometrics appointment
5. Complete interview if required

## Code Blocks

Here's an example API request:
\`\`\`json
{
  "question": "What is a Green Card?",
  "session_id": "immigration-session-123"
}
\`\`\`

## Blockquotes

> **Important Note:** Always consult with a qualified immigration attorney for your specific situation. Immigration law is complex and changes frequently.

## Tables

| Visa Type | Duration | Work Authorization |
|-----------|----------|-------------------|
| F-1 | Program length | Limited on-campus |
| H-1B | 3 years (renewable) | Employer-specific |
| Green Card | Permanent | Unlimited |

## Links and Additional Resources

For more information, visit [USCIS Official Website](https://www.uscis.gov).

---

*This example showcases various markdown elements that will be properly rendered in the chat interface.*`
  },

  'f1 visa': {
    question: 'What is an F1 visa?',
    answer: 'An F1 visa is a non-immigrant student visa that allows international students to study in the United States. Here are the key details:\n\n**Purpose:** Full-time academic study at an accredited U.S. college, university, seminary, conservatory, academic high school, elementary school, or other academic institution or language training program.\n\n**Requirements:**\n- Acceptance at a Student and Exchange Visitor Program (SEVP)-approved school\n- Form I-20 from your chosen institution\n- Proof of financial support\n- Valid passport\n- SEVIS fee payment\n\n**Duration:** Valid for the length of your academic program plus any authorized practical training period.\n\n**Work Authorization:** Limited on-campus work opportunities and potential for Curricular Practical Training (CPT) and Optional Practical Training (OPT).'
  },

  'green card': {
    question: 'How to apply for a Green Card?',
    answer: 'A Green Card (permanent residence) can be obtained through several pathways:\n\n**Family-based Immigration:**\n- Immediate relatives of U.S. citizens (spouse, unmarried children under 21, parents)\n- Family preference categories for other relatives\n\n**Employment-based Immigration:**\n- EB-1: Priority workers (extraordinary ability, outstanding professors/researchers, multinational executives)\n- EB-2: Advanced degree professionals or exceptional ability\n- EB-3: Skilled workers, professionals, and other workers\n\n**Application Process:**\n1. File Form I-485 (if in the U.S.) or consular processing (if abroad)\n2. Attend biometrics appointment\n3. Complete interview (if required)\n4. Receive decision\n\n**Required Documents:**\n- Birth certificate\n- Medical examination\n- Police certificates\n- Financial documents\n- Photos'
  },

  'h1b': {
    question: 'What documents do I need for H1B?',
    answer: 'The H1B visa requires specific documentation from both the employer and employee:\n\n**Employer Documents:**\n- Labor Condition Application (LCA) certified by Department of Labor\n- Form I-129 (Petition for Nonimmigrant Worker)\n- Evidence of employer\'s ability to pay the offered wage\n- Job description and requirements\n\n**Employee Documents:**\n- Bachelor\'s degree or equivalent\n- Transcripts and diploma evaluations\n- Resume demonstrating relevant experience\n- Valid passport\n- Form DS-160 (Online Nonimmigrant Visa Application)\n\n**Supporting Evidence:**\n- Proof that the position requires a specialty occupation\n- Evidence of employer-employee relationship\n- Itinerary for multiple work locations (if applicable)\n\n**Application Timeline:**\n- H1B cap registration: March\n- Petition filing: April 1st\n- Consular processing or change of status\n- Start date: October 1st (earliest)'
  }
};

export const mockAskQuestion = async (
  question: string,
  _userId: string,
  chatSessionId?: string
): Promise<{ message: Message; sessionId: string }> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 1000));

  // Find the best matching response
  const questionLower = question.toLowerCase();
  let responseData: { question: string; answer: string } | null = null;
  
  for (const [key, value] of Object.entries(mockResponses)) {
    if (questionLower.includes(key)) {
      responseData = value;
      break;
    }
  }

  // Default response if no match found
  if (!responseData) {
    responseData = {
      question: question,
      answer: `Thank you for your question about immigration. While I don't have a specific answer for "${question}" in my current knowledge base, I recommend consulting with an immigration attorney or checking the official USCIS website for the most accurate and up-to-date information.\n\nFor general immigration questions, you might want to ask about:\n- F1 visa requirements\n- Green Card application process\n- H1B documentation\n- Work authorization options\n- Family-based immigration\n\nPlease feel free to ask a more specific question, and I'll do my best to help!`
    };
  }

  const message: Message = {
    id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    question: responseData.question,
    answer: responseData.answer,
    timestamp: new Date(),
  };

  return {
    message,
    sessionId: chatSessionId || `session-${Date.now()}`,
  };
};
