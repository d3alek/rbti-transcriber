#!/usr/bin/env python3
"""Simple test script to verify Audio Transcription System installation."""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import click
        print("✅ Click imported successfully")
    except ImportError as e:
        print(f"❌ Click import failed: {e}")
        return False
    
    try:
        import yaml
        print("✅ PyYAML imported successfully")
    except ImportError as e:
        print(f"❌ PyYAML import failed: {e}")
        return False
    
    try:
        import aiohttp
        print("✅ aiohttp imported successfully")
    except ImportError as e:
        print(f"❌ aiohttp import failed: {e}")
        return False
    
    try:
        import aiofiles
        print("✅ aiofiles imported successfully")
    except ImportError as e:
        print(f"❌ aiofiles import failed: {e}")
        return False
    
    return True

def test_project_structure():
    """Test that project structure is correct."""
    print("\nTesting project structure...")
    
    required_paths = [
        "src/cli/main.py",
        "src/services/transcription_client.py",
        "src/services/assemblyai_client.py",
        "src/services/deepgram_client.py",
        "src/formatters/html_formatter.py",
        "src/formatters/markdown_formatter.py",
        "src/utils/config.py",
        "config.yaml",
        "requirements.txt"
    ]
    
    all_exist = True
    for path in required_paths:
        if Path(path).exists():
            print(f"✅ {path}")
        else:
            print(f"❌ {path} - Missing")
            all_exist = False
    
    return all_exist

def test_cli_help():
    """Test that CLI help command works."""
    print("\nTesting CLI help command...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "Transcribe MP3 files" in result.stdout:
            print("✅ CLI help command works")
            return True
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def test_config_loading():
    """Test that configuration can be loaded."""
    print("\nTesting configuration loading...")
    
    try:
        sys.path.insert(0, 'src')
        from utils.config import ConfigManager
        
        config_manager = ConfigManager()
        default_service = config_manager.get('transcription.default_service')
        
        if default_service:
            print(f"✅ Configuration loaded, default service: {default_service}")
            return True
        else:
            print("❌ Configuration loading failed")
            return False
    
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_ffmpeg():
    """Test FFmpeg availability (optional)."""
    print("\nTesting FFmpeg availability (optional)...")
    
    try:
        import shutil
        if shutil.which('ffmpeg'):
            print("✅ FFmpeg is available - audio compression will work")
            return True
        else:
            print("⚠️  FFmpeg not found - audio compression will be disabled")
            return True  # Not a failure, just a warning
    
    except Exception as e:
        print(f"⚠️  FFmpeg test failed: {e}")
        return True  # Not a failure

def main():
    """Run all tests."""
    print("Audio Transcription System - Installation Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Project Structure", test_project_structure),
        ("CLI Help", test_cli_help),
        ("Configuration", test_config_loading),
        ("FFmpeg (Optional)", test_ffmpeg)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Installation looks good.")
        print("\nNext steps:")
        print("1. Set your API keys in environment variables or .env file")
        print("2. Try: python -m src.cli.main --help")
        print("3. Create a test directory with MP3 files")
        return 0
    else:
        print("❌ Some tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())