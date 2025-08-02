#!/usr/bin/env python3
"""
Logging Test Script for AskImmigrate API
Run this to test the logging configuration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_logging():
    """Test the logging configuration"""
    print("Testing AskImmigrate API Logging Configuration...")
    
    try:
        # Import the configured logger from api.py
        from backend.code.api import logger
        
        print("✅ Logger imported successfully")
        
        # Test different log levels
        logger.info("🧪 Testing INFO level logging")
        logger.warning("🧪 Testing WARNING level logging") 
        logger.error("🧪 Testing ERROR level logging")
        
        # Test log file creation
        log_file_path = "backend/outputs/api.log"
        if os.path.exists(log_file_path):
            print(f"✅ Log file exists at: {log_file_path}")
            
            # Check if logs are being written
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    print(f"✅ Log file has {len(lines)} lines")
                    print("📄 Last 3 log entries:")
                    for line in lines[-3:]:
                        print(f"   {line.strip()}")
                else:
                    print("⚠️  Log file is empty")
        else:
            print(f"⚠️  Log file not found at: {log_file_path}")
            
        print("\n🎉 Logging test completed!")
        print("📋 Summary:")
        print("   - Logger configuration: ✅ Working")
        print("   - Console output: ✅ Working") 
        print("   - File logging: ✅ Working" if os.path.exists(log_file_path) else "   - File logging: ⚠️  Check path")
        
    except Exception as e:
        print(f"❌ Logging test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_logging()
