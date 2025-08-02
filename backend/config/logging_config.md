# Logging Configuration for AskImmigrate API
# This file provides logging setup documentation and can be extended for advanced configurations

## Current Logging Setup

### Log Levels
- INFO: General application flow, requests, responses
- ERROR: Exceptions, failed requests, system errors
- WARNING: Recoverable issues, fallbacks (currently used in utils.py)

### Log Destinations
1. **File Logging**: `backend/outputs/api.log`
   - Persistent logging for production debugging
   - Automatic rotation recommended for production
   
2. **Console Logging**: Standard output
   - Real-time monitoring during development
   - Docker container logs in production

### Log Format
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```
Example:
```
2025-08-02 10:30:45,123 - backend.code.api - INFO - GET /health - Health check requested
```

## What Gets Logged

### Request Lifecycle
- ✅ Request start: Method, path, client IP
- ✅ Request completion: Status code, duration
- ✅ Request errors: Exception details, duration

### Business Logic
- ✅ Session creation and filtering
- ✅ Question processing (privacy-safe truncation)
- ✅ Answer retrieval and response building
- ✅ Client fingerprint operations

### System Health
- ✅ Application startup/shutdown
- ✅ Session statistics and isolation metrics
- ✅ Error tracking with stack traces

## Privacy Considerations
- Questions truncated to 100 characters in logs
- Client fingerprints logged as "provided/not provided"
- Full session IDs logged for debugging
- No sensitive user data in logs

## Production Recommendations
1. **Log Rotation**: Implement logrotate or similar
2. **Log Aggregation**: Consider ELK stack or similar
3. **Monitoring**: Set up alerts on ERROR level logs
4. **Storage**: Ensure sufficient disk space for logs

## Docker Integration
- Logs written to stdout/stderr for container visibility
- Log files mounted to persistent volume if needed
- Environment-based log level configuration recommended
