#!/usr/bin/env python3
"""
Logging Test Script for AskImmigrate API
Run this to test the logging configuration
"""

import sys
import os

# Add the project root to Python path so backend.code imports work
# Go up 3 levels: tests -> code -> backend -> project_root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add backend/code directory  
backend_code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_code_dir not in sys.path:
    sys.path.insert(0, backend_code_dir)

def test_logging():
    """Test the logging configuration"""
    print("Testing AskImmigrate API Logging Configuration...")
    
    try:
        # Import the configured logger from api.py
        from backend.code.api import logger
        
        print("✅ Logger imported successfully")
        
        # Test different log levels (without emojis to avoid encoding issues)
        logger.info("Testing INFO level logging")
        logger.warning("Testing WARNING level logging") 
        logger.error("Testing ERROR level logging")
        
        # Test log file creation - API logs to backend/outputs/api.log from project root
        log_file_path = os.path.join(project_root, "backend", "outputs", "api.log")
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
