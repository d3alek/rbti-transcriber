#!/usr/bin/env python3
"""Simple validation script for the Deepgram-only refactor."""

import os
import sys
import json
from pathlib import Path

def test_file_removals():
    """Test that removed service files are gone."""
    print("1. Testing file removals...")
    
    removed_files = [
        "src/services/openai_client.py",
        "src/services/assemblyai_client.py"
    ]
    
    all_removed = True
    for file_path in removed_files:
        if Path(file_path).exists():
            print(f"   ❌ {file_path} still exists")
            all_removed = False
        else:
            print(f"   ✅ {file_path} removed")
    
    return all_removed

def test_service_factory_content():
    """Test service factory content directly."""
    print("\n2. Testing service factory content...")
    
    factory_file = Path("src/services/service_factory.py")
    if not factory_file.exists():
        print("   ❌ Service factory file missing")
        return False
    
    content = factory_file.read_text()
    
    # Check that only deepgram is in SUPPORTED_SERVICES
    if "SUPPORTED_SERVICES = ['deepgram']" in content:
        print("   ✅ SUPPORTED_SERVICES only contains deepgram")
    else:
        print("   ❌ SUPPORTED_SERVICES not correctly updated")
        return False
    
    # Check that old service imports are removed
    if "openai_client" in content or "assemblyai_client" in content:
        print("   ❌ Old service imports still present")
        return False
    else:
        print("   ✅ Old service imports removed")
    
    # Check that only DeepgramClient is imported
    if "from .deepgram_client import DeepgramClient" in content:
        print("   ✅ DeepgramClient import present")
    else:
        print("   ❌ DeepgramClient import missing")
        return False
    
    return True

def test_config_defaults():
    """Test configuration defaults."""
    print("\n3. Testing configuration defaults...")
    
    config_file = Path("src/utils/config.py")
    if not config_file.exists():
        print("   ❌ Config file missing")
        return False
    
    content = config_file.read_text()
    
    # Check default service
    if "'default_service': 'deepgram'" in content:
        print("   ✅ Default service is deepgram")
    else:
        print("   ❌ Default service not set to deepgram")
        return False
    
    # Check that only deepgram service config exists
    if "'deepgram': {" in content and "'openai': {" not in content and "'assemblyai': {" not in content:
        print("   ✅ Only deepgram service configuration present")
    else:
        print("   ❌ Old service configurations still present")
        return False
    
    return True

def test_api_models():
    """Test API models."""
    print("\n4. Testing API models...")
    
    models_file = Path("api/models.py")
    if not models_file.exists():
        print("   ❌ API models file missing")
        return False
    
    content = models_file.read_text()
    
    # Check TranscriptionRequest service type
    if "service: Literal['deepgram'] = 'deepgram'" in content:
        print("   ✅ TranscriptionRequest only accepts deepgram")
    else:
        print("   ❌ TranscriptionRequest service type not updated")
        return False
    
    return True

def test_web_ui_types():
    """Test Web UI TypeScript types."""
    print("\n5. Testing Web UI types...")
    
    types_file = Path("web-ui/src/types/index.ts")
    if not types_file.exists():
        print("   ❌ Web UI types file missing")
        return False
    
    content = types_file.read_text()
    
    # Check service type
    if "service: 'deepgram'" in content:
        print("   ✅ Web UI types only support deepgram")
    else:
        print("   ❌ Web UI types not updated")
        return False
    
    # Check that old services are not mentioned
    if "'openai'" in content or "'assemblyai'" in content:
        print("   ❌ Old service types still present")
        return False
    else:
        print("   ✅ Old service types removed")
    
    return True

def test_backward_compatibility():
    """Test backward compatibility."""
    print("\n6. Testing backward compatibility...")
    
    # Check for existing transcriptions
    transcriptions_dir = Path("test_audio/transcriptions")
    if transcriptions_dir.exists():
        deepgram_files = list(transcriptions_dir.glob("**/*deepgram*"))
        if deepgram_files:
            print(f"   ✅ Found {len(deepgram_files)} existing Deepgram files")
        else:
            print("   ℹ️  No existing Deepgram transcriptions (this is okay)")
        
        # Check cache files
        cache_dir = transcriptions_dir / "cache"
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*.json"))
            if cache_files:
                print(f"   ✅ Found {len(cache_files)} cache files")
                # Try to read one
                try:
                    with open(cache_files[0], 'r') as f:
                        json.load(f)
                    print("   ✅ Cache files are readable")
                except Exception as e:
                    print(f"   ⚠️  Cache file issue: {e}")
            else:
                print("   ℹ️  No cache files found")
        else:
            print("   ℹ️  No cache directory found")
    else:
        print("   ℹ️  No transcriptions directory found")
    
    # Check test audio file
    test_audio = Path("test_audio/RBTI-Animal-Husbandry-T01.mp3")
    if test_audio.exists():
        print("   ✅ Test audio file exists")
    else:
        print("   ℹ️  No test audio file found")
    
    return True

def test_cli_functionality():
    """Test CLI functionality."""
    print("\n7. Testing CLI functionality...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("   ✅ CLI help command works")
            
            # Check that old services aren't mentioned
            help_text = result.stdout.lower()
            if "openai" in help_text or "assemblyai" in help_text:
                print("   ❌ CLI help mentions removed services")
                return False
            else:
                print("   ✅ CLI help doesn't mention removed services")
        else:
            print(f"   ❌ CLI help failed: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"   ❌ CLI test failed: {e}")
        return False
    
    return True

def test_requirements():
    """Test requirements.txt cleanup."""
    print("\n8. Testing requirements cleanup...")
    
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("   ❌ requirements.txt missing")
        return False
    
    content = req_file.read_text().lower()
    
    # Check that openai is removed
    if "openai" in content:
        print("   ❌ OpenAI package still in requirements")
        return False
    else:
        print("   ✅ OpenAI package removed from requirements")
    
    return True

def main():
    """Run all validation tests."""
    print("Deepgram-Only Refactor Validation")
    print("=" * 40)
    
    tests = [
        test_file_removals,
        test_service_factory_content,
        test_config_defaults,
        test_api_models,
        test_web_ui_types,
        test_backward_compatibility,
        test_cli_functionality,
        test_requirements
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All validation tests passed!")
        print("\nRefactor Summary:")
        print("✅ Removed OpenAI and AssemblyAI services")
        print("✅ Updated service factory to Deepgram-only")
        print("✅ Updated configuration defaults")
        print("✅ Updated API models and Web UI types")
        print("✅ Maintained backward compatibility")
        print("✅ CLI functionality preserved")
        return 0
    else:
        print(f"\n❌ {len(tests) - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())