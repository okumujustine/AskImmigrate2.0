/**
 * Test file for browser fingerprinting
 * Run this in browser console to test the services
 */

import {
  getPersistentBrowserFingerprint,
  getBrowserFingerprintInfo
} from './browserFingerprint';

console.log('=== Browser Fingerprinting Tests ===');

// Generate and compare fingerprints
const fingerprint1 = getPersistentBrowserFingerprint();
console.log('First fingerprint:', fingerprint1);

const fingerprint2 = getPersistentBrowserFingerprint();
console.log('Second fingerprint (should match):', fingerprint2);
console.log('Consistent fingerprints:', fingerprint1 === fingerprint2);

// Print browser metadata
const browserInfo = getBrowserFingerprintInfo();
console.log('Browser info:', browserInfo);

console.log('\n=== Tests Complete ===');

export {}; // Makes this a module and avoids top-level redeclaration issues
