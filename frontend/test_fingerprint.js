/**
 * Browser Fingerprint Comparison Script
 * Run this in different browsers to compare fingerprints
 */

console.log('🔍 Browser Fingerprint Analysis');
console.log('=================================');

// Detect browser name from user agent
function getBrowserName() {
  const userAgent = navigator.userAgent;
  if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) return 'Chrome';
  if (userAgent.includes('Edg')) return 'Edge';
  if (userAgent.includes('Firefox')) return 'Firefox';
  if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) return 'Safari';
  if (userAgent.includes('Opera')) return 'Opera';
  return 'Unknown';
}

// Extract browser version
function getBrowserVersion() {
  const userAgent = navigator.userAgent;
  const browserName = getBrowserName();
  
  let versionMatch;
  switch (browserName) {
    case 'Chrome':
      versionMatch = userAgent.match(/Chrome\/(\d+\.\d+)/);
      break;
    case 'Edge':
      versionMatch = userAgent.match(/Edg\/(\d+\.\d+)/);
      break;
    case 'Firefox':
      versionMatch = userAgent.match(/Firefox\/(\d+\.\d+)/);
      break;
    case 'Safari':
      versionMatch = userAgent.match(/Version\/(\d+\.\d+)/);
      break;
    default:
      versionMatch = null;
  }
  
  return versionMatch ? versionMatch[1] : 'Unknown';
}

// Collect browser info
const browserInfo = {
  userAgent: navigator.userAgent || 'unknown',
  language: navigator.language || 'unknown',
  platform: navigator.platform || 'unknown',
  screenResolution: `${screen.width}x${screen.height}`,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'unknown',
  cookieEnabled: navigator.cookieEnabled,
  doNotTrack: navigator.doNotTrack || null,
  browserName: getBrowserName(),
  browserVersion: getBrowserVersion(),
  hardwareConcurrency: navigator.hardwareConcurrency || 0,
  deviceMemory: navigator.deviceMemory || undefined,
};

console.log('Browser Information:');
console.table(browserInfo);

// Generate fingerprint string
const fingerprintString = [
  browserInfo.userAgent,
  browserInfo.language,
  browserInfo.platform,
  browserInfo.screenResolution,
  browserInfo.timezone,
  browserInfo.cookieEnabled.toString(),
  browserInfo.doNotTrack || 'null',
  browserInfo.browserName,
  browserInfo.browserVersion,
  browserInfo.hardwareConcurrency.toString(),
  browserInfo.deviceMemory?.toString() || 'unknown'
].join('|');

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
const persistentComponent = simpleHash(browserInfo.browserName + browserInfo.browserVersion).slice(0, 4);
const fingerprint = `${baseHash}-${persistentComponent}`;

console.log('');
console.log('Fingerprint Details:');
console.log('Fingerprint String:', fingerprintString);
console.log('Base Hash:', baseHash);
console.log('Persistent Component:', persistentComponent);
console.log('🔑 FINAL FINGERPRINT:', fingerprint);

// Check current stored fingerprint
const stored = localStorage.getItem('askimmigrate_client_id');
console.log('');
console.log('Stored Client ID:', stored);

if (stored !== fingerprint) {
  console.log('⚠️  Stored fingerprint differs from calculated fingerprint');
  console.log('This might indicate the fingerprint algorithm changed');
} else {
  console.log('✅ Stored fingerprint matches calculated fingerprint');
}

console.log('');
console.log('🧪 Test Instructions:');
console.log('1. Copy this FINAL FINGERPRINT value');
console.log('2. Run this script in another browser');
console.log('3. Compare the FINAL FINGERPRINT values');
console.log('4. They should be different for proper isolation!');
