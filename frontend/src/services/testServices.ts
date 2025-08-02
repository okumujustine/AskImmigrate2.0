/**
 * Test file for browser fingerprinting and session storage
 * Run this in browser console to test the services
 */

import { 
  getPersistentBrowserFingerprint,
  getBrowserFingerprintInfo
} from './browserFingerprint';

import {
  getClientSessions,
  saveClientSession,
  updateClientSession,
  deleteClientSession,
  getSessionStorageStats
} from './sessionStorage';

import type { ChatSession, Message } from '../types/chat';

// Test browser fingerprinting
console.log('=== Browser Fingerprinting Tests ===');

const fingerprint1 = getPersistentBrowserFingerprint();
console.log('First fingerprint:', fingerprint1);

const fingerprint2 = getPersistentBrowserFingerprint();
console.log('Second fingerprint:', fingerprint2);
console.log('Consistent fingerprints:', fingerprint1 === fingerprint2);

const browserInfo = getBrowserFingerprintInfo();
console.log('Browser info:', browserInfo);

// Test session storage
console.log('\n=== Session Storage Tests ===');

// Create test messages
const testMessages: Message[] = [
  {
    id: '1',
    question: 'What is an F-1 visa?',
    answer: 'The F-1 visa is a student visa...',
    timestamp: new Date()
  },
  {
    id: '2', 
    question: 'How do I extend it?',
    answer: 'To extend your F-1 visa...',
    timestamp: new Date()
  }
];

// Create test session
const testSession: ChatSession = {
  id: 'test-session-1',
  title: 'F-1 Visa Questions',
  messages: testMessages,
  createdAt: new Date(),
  updatedAt: new Date()
};

// Test saving session
saveClientSession(testSession);
console.log('Session saved');

// Test loading sessions
const loadedSessions = getClientSessions();
console.log('Loaded sessions:', loadedSessions);

// Test updating session
updateClientSession('test-session-1', { title: 'Updated F-1 Visa Questions' });
console.log('Session updated');

// Test session stats
const stats = getSessionStorageStats();
console.log('Storage stats:', stats);

// Test clearing specific session
deleteClientSession('test-session-1');
console.log('Session deleted');

const finalSessions = getClientSessions();
console.log('Final sessions:', finalSessions);

console.log('\n=== Tests Complete ===');

export { }; // Make this a module
