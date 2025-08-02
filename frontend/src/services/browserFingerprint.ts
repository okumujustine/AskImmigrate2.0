/**
 * Browser Fingerprinting Service for Anonymous User Isolation
 * Generates consistent unique identifiers per browser for session isolation
 */

interface BrowserInfo {
  userAgent: string;
  language: string;
  platform: string;
  screenResolution: string;
  timezone: string;
  cookieEnabled: boolean;
  doNotTrack: string | null;
}

/**
 * Generate a simple hash from a string (for consistent fingerprinting)
 */
function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Collect browser-specific information for fingerprinting
 */
function getBrowserInfo(): BrowserInfo {
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

/**
 * Generate a consistent browser fingerprint
 */
export function generateBrowserFingerprint(): string {
  try {
    const browserInfo = getBrowserInfo();
    
    // Create a consistent string from browser characteristics
    const fingerprintString = [
      browserInfo.userAgent,
      browserInfo.language,
      browserInfo.platform,
      browserInfo.screenResolution,
      browserInfo.timezone,
      browserInfo.cookieEnabled.toString(),
      browserInfo.doNotTrack || 'null'
    ].join('|');
    
    // Generate hash and add timestamp component for additional uniqueness
    const baseHash = simpleHash(fingerprintString);
    const sessionComponent = simpleHash(Date.now().toString()).slice(0, 4);
    
    return `${baseHash}-${sessionComponent}`;
  } catch (error) {
    console.warn('Failed to generate browser fingerprint, using fallback:', error);
    // Fallback fingerprint if browser APIs are not available
    return `fallback-${simpleHash(Date.now().toString() + Math.random().toString())}`;
  }
}

/**
 * Get or create a persistent browser fingerprint using localStorage
 */
export function getPersistentBrowserFingerprint(): string {
  const STORAGE_KEY = 'askimmigrate_client_id';
  
  try {
    // Try to get existing fingerprint from localStorage
    const existingFingerprint = localStorage.getItem(STORAGE_KEY);
    
    if (existingFingerprint && existingFingerprint.length > 0) {
      return existingFingerprint;
    }
    
    // Generate new fingerprint and store it
    const newFingerprint = generateBrowserFingerprint();
    localStorage.setItem(STORAGE_KEY, newFingerprint);
    
    console.log('Generated new browser fingerprint:', newFingerprint);
    return newFingerprint;
    
  } catch (error) {
    console.warn('localStorage not available, using session-only fingerprint:', error);
    // Fallback to session-only fingerprint if localStorage is not available
    return generateBrowserFingerprint();
  }
}

/**
 * Clear the stored browser fingerprint (for testing or reset purposes)
 */
export function clearBrowserFingerprint(): void {
  const STORAGE_KEY = 'askimmigrate_client_id';
  
  try {
    localStorage.removeItem(STORAGE_KEY);
    console.log('Browser fingerprint cleared');
  } catch (error) {
    console.warn('Failed to clear browser fingerprint:', error);
  }
}

/**
 * Get browser info for debugging purposes
 */
export function getBrowserFingerprintInfo(): BrowserInfo & { fingerprint: string } {
  const browserInfo = getBrowserInfo();
  const fingerprint = getPersistentBrowserFingerprint();
  
  return {
    ...browserInfo,
    fingerprint
  };
}
