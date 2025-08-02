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
  browserName: string;
  browserVersion: string;
  hardwareConcurrency: number;
  deviceMemory: number | undefined;
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
 * Detect browser name from user agent
 */
function getBrowserName(): string {
  const userAgent = navigator.userAgent;
  if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) return 'Chrome';
  if (userAgent.includes('Edg')) return 'Edge';
  if (userAgent.includes('Firefox')) return 'Firefox';
  if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) return 'Safari';
  if (userAgent.includes('Opera')) return 'Opera';
  return 'Unknown';
}

/**
 * Extract browser version
 */
function getBrowserVersion(): string {
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
    browserName: getBrowserName(),
    browserVersion: getBrowserVersion(),
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    deviceMemory: (navigator as any).deviceMemory || undefined,
  };
}

/**
 * Generate a consistent browser fingerprint
 */
export function generateBrowserFingerprint(): string {
  try {
    const browserInfo = getBrowserInfo();
    
    // Create a consistent string from browser characteristics
    // Include browser name and version for better differentiation
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
    
    // Generate hash - remove timestamp component to ensure consistency
    const baseHash = simpleHash(fingerprintString);
    
    // Add a small random component that gets stored persistently
    const persistentComponent = simpleHash(browserInfo.browserName + browserInfo.browserVersion).slice(0, 4);
    
    return `${baseHash}-${persistentComponent}`;
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
