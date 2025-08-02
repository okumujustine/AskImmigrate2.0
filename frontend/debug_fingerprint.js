/**
 * Debug script to test browser fingerprinting
 * Copy and paste this into different browser consoles to test fingerprint uniqueness
 */

// Test browser fingerprinting
console.log('=== Browser Fingerprinting Debug ===');

// Test the browser info collection
function getBrowserInfo() {
  return {
    userAgent: navigator.userAgent || 'unknown',
    language: navigator.language || 'unknown',
    platform: navigator.platform || 'unknown',
    screenResolution: `${screen.width}x${screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'unknown',
    cookieEnabled: navigator.cookieEnabled,
    doNotTrack: navigator.doNotTrack || null,
  };
}

const browserInfo = getBrowserInfo();
console.log('Browser Info:', browserInfo);

// Create fingerprint string
const fingerprintString = [
  browserInfo.userAgent,
  browserInfo.language,
  browserInfo.platform,
  browserInfo.screenResolution,
  browserInfo.timezone,
  browserInfo.cookieEnabled.toString(),
  browserInfo.doNotTrack || 'null'
].join('|');

console.log('Fingerprint String:', fingerprintString);

// Simple hash function
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

const baseHash = simpleHash(fingerprintString);
console.log('Base Hash:', baseHash);

// Check localStorage
const STORAGE_KEY = 'askimmigrate_client_id';
const existingFingerprint = localStorage.getItem(STORAGE_KEY);
console.log('Existing Fingerprint in localStorage:', existingFingerprint);

// Clear localStorage for testing
localStorage.removeItem(STORAGE_KEY);
console.log('Cleared localStorage');

// Generate new fingerprint
const sessionComponent = simpleHash(Date.now().toString()).slice(0, 4);
const newFingerprint = `${baseHash}-${sessionComponent}`;
console.log('Generated New Fingerprint:', newFingerprint);

// Store it
localStorage.setItem(STORAGE_KEY, newFingerprint);
console.log('Stored new fingerprint');

console.log('=== End Debug ===');
