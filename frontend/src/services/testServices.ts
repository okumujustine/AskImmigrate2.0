/**
 * Test file for browser fingerprinting
 * Run this in browser console to test the services
 */

import {
  getPersistentBrowserFingerprint,
  getBrowserFingerprintInfo
} from './browserFingerprint';

console.log('=== Browser Fingerprinting Tests ===');

const fingerprint1 = getPersistentBrowserFingerprint();
console.log('First fingerprint:', fingerprint1);

const fingerprint2 = getPersistentBrowserFingerprint();
console.log('Second fingerprint:', fingerprint2);
console.log('Consistent fingerprints:', fingerprint1 === fingerprint2);

const browserInfo = getBrowserFingerprintInfo();
console.log('Browser info:', browserInfo);

console.log('\n=== Tests Complete ===');

export { }; // Keep this so the file is treated as a module
