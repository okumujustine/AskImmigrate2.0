/**
 * Clear All Session Data Script
 * Run this in browser console to completely reset session data
 */

console.log('🧹 Clearing all session data...');

// Clear browser fingerprint
try {
  localStorage.removeItem('askimmigrate_client_id');
  console.log('✅ Cleared browser fingerprint');
} catch (e) {
  console.log('❌ Failed to clear browser fingerprint:', e);
}

// Clear session storage
try {
  localStorage.removeItem('askimmigrate_sessions');
  console.log('✅ Cleared session storage');
} catch (e) {
  console.log('❌ Failed to clear session storage:', e);
}

// Clear any other related data
try {
  // Clear all localStorage items that start with 'askimmigrate'
  const keysToRemove = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith('askimmigrate')) {
      keysToRemove.push(key);
    }
  }
  
  keysToRemove.forEach(key => {
    localStorage.removeItem(key);
    console.log(`✅ Cleared ${key}`);
  });
  
  if (keysToRemove.length === 0) {
    console.log('ℹ️  No additional askimmigrate data found');
  }
  
} catch (e) {
  console.log('❌ Failed to clear additional data:', e);
}

console.log('🎉 Session data cleared! Refresh the page to start fresh.');
console.log('');
console.log('🔍 To test browser isolation:');
console.log('1. Run this script in Chrome');
console.log('2. Run this script in Edge');
console.log('3. Refresh both browsers');
console.log('4. Create a chat session in each browser');
console.log('5. Verify sessions are isolated (not visible in other browser)');
