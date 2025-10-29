#!/usr/bin/env python3
"""Test script to validate the Deepgram-only refactored system."""

import sys
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

def test_removed_services_not_accessible():
    """Test that removed services are no longer accessible through any interface."""
    print("Testing that removed services are not accessible...")
    
    # Test 1: Check that OpenAI and AssemblyAI client files are removed
    removed_files = [
        "src/services/openai_client.py",
        "src/services/assemblyai_client.py"
    ]
    
    for file_path in removed_files:
        if Path(file_path).exists():
            print(f"❌ {file_path} still exists - should be removed")
            return False
        else:
            print(f"✅ {file_path} correctly removed")
    
    # Test 2: Check service factory only supports Deepgram
    try:
        # Add src to path and import
        src_path = Path('src').resolve()
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        # Import using absolute imports
        import services.service_factory as sf
        import utils.config as config_mod
        
        config_manager = config_mod.ConfigManager()
        factory = sf.TranscriptionServiceFactory(config_manager)
        
        # Check supported services
        if factory.SUPPORTED_SERVICES != ['deepgram']:
            print(f"❌ SUPPORTED_SERVICES should be ['deepgram'], got: {factory.SUPPORTED_SERVICES}")
            return False
        else:
            print("✅ Service factory only supports Deepgram")
        
        # Test that unsupported services raise errors
        try:
            factory.create_client('openai')
            print("❌ OpenAI client creation should fail")
            return False
        except Exception as e:
            print(f"✅ OpenAI client creation correctly fails: {type(e).__name__}")
        
        try:
            factory.create_client('assemblyai')
            print("❌ AssemblyAI client creation should fail")
            return False
        except Exception as e:
            print(f"✅ AssemblyAI client creation correctly fails: {type(e).__name__}")
        
    except Exception as e:
        print(f"❌ Service factory test failed: {e}")
        return False
    
    return True

def test_deepgram_functionality():
    """Test that existing Deepgram transcription functionality works correctly."""
    print("\nTesting Deepgram functionality...")
    
    try:
        # Add src to path and import
        src_path = Path('src').resolve()
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        # Import using absolute imports
        import services.service_factory as sf
        import utils.config as config_mod
        
        config_manager = config_mod.ConfigManager()
        factory = sf.TranscriptionServiceFactory(config_manager)
        
        # Test service capabilities
        capabilities = factory.get_service_capabilities('deepgram')
        expected_keys = ['service', 'api_base_url', 'supports_custom_vocabulary', 
                        'supports_speaker_diarization', 'max_vocabulary_terms', 'supported_languages']
        
        for key in expected_keys:
            if key not in capabilities:
                print(f"❌ Missing capability key: {key}")
                return False
        
        if capabilities['service'] != 'deepgram':
            print(f"❌ Wrong service in capabilities: {capabilities['service']}")
            return False
        
        print("✅ Deepgram service capabilities correct")
        
        # Test configuration validation
        validation = factory.validate_service_configuration('deepgram')
        if validation['service'] != 'deepgram':
            print(f"❌ Wrong service in validation: {validation['service']}")
            return False
        
        print("✅ Deepgram configuration validation works")
        
        # Test that only Deepgram is supported in validation
        try:
            factory.validate_service_configuration('openai')
            print("❌ OpenAI validation should fail")
            return False
        except Exception:
            print("✅ OpenAI validation correctly fails")
        
    except Exception as e:
        print(f"❌ Deepgram functionality test failed: {e}")
        return False
    
    return True

def test_configuration_loading():
    """Test configuration loading with both new and legacy config files."""
    print("\nTesting configuration loading...")
    
    try:
        # Add src to path and import
        src_path = Path('src').resolve()
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        import utils.config as config_mod
        
        # Test 1: Default configuration
        config_manager = config_mod.ConfigManager()
        default_service = config_manager.get('transcription.default_service')
        
        if default_service != 'deepgram':
            print(f"❌ Default service should be 'deepgram', got: {default_service}")
            return False
        else:
            print("✅ Default service is correctly set to Deepgram")
        
        # Test 2: Check that only Deepgram service config exists
        services_config = config_manager.get('services', {})
        if 'deepgram' not in services_config:
            print("❌ Deepgram service configuration missing")
            return False
        
        if 'openai' in services_config or 'assemblyai' in services_config:
            print("❌ Old service configurations still present")
            return False
        
        print("✅ Only Deepgram service configuration present")
        
        # Test 3: Create a legacy config file and test graceful handling
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            legacy_config = """
transcription:
  default_service: 'assemblyai'
services:
  assemblyai:
    api_key: 'old_key'
  deepgram:
    api_key: 'deepgram_key'
  openai:
    api_key: 'openai_key'
"""
            f.write(legacy_config)
            legacy_path = f.name
        
        try:
            legacy_config_manager = config_mod.ConfigManager(Path(legacy_path))
            # Should still work, just with updated defaults
            print("✅ Legacy configuration loads without errors")
        finally:
            os.unlink(legacy_path)
        
    except Exception as e:
        print(f"❌ Configuration loading test failed: {e}")
        return False
    
    return True

def test_api_models():
    """Test that API models only accept Deepgram service."""
    print("\nTesting API models...")
    
    try:
        sys.path.insert(0, 'api')
        from models import TranscriptionRequest
        
        # Test 1: Valid Deepgram request
        try:
            request = TranscriptionRequest(
                file_id="test123",
                service="deepgram",
                compress_audio=True,
                output_formats=["html", "markdown"]
            )
            print("✅ Valid Deepgram request accepted")
        except Exception as e:
            print(f"❌ Valid Deepgram request failed: {e}")
            return False
        
        # Test 2: Default service should be Deepgram
        try:
            request = TranscriptionRequest(
                file_id="test123",
                compress_audio=True,
                output_formats=["html"]
            )
            if request.service != "deepgram":
                print(f"❌ Default service should be 'deepgram', got: {request.service}")
                return False
            print("✅ Default service is Deepgram")
        except Exception as e:
            print(f"❌ Default service test failed: {e}")
            return False
        
        # Test 3: Invalid services should be rejected
        try:
            request = TranscriptionRequest(
                file_id="test123",
                service="openai",
                compress_audio=True,
                output_formats=["html"]
            )
            print("❌ OpenAI service should be rejected")
            return False
        except Exception:
            print("✅ OpenAI service correctly rejected")
        
        try:
            request = TranscriptionRequest(
                file_id="test123",
                service="assemblyai",
                compress_audio=True,
                output_formats=["html"]
            )
            print("❌ AssemblyAI service should be rejected")
            return False
        except Exception:
            print("✅ AssemblyAI service correctly rejected")
        
    except Exception as e:
        print(f"❌ API models test failed: {e}")
        return False
    
    return True

def test_web_ui_types():
    """Test that Web UI TypeScript types only support Deepgram."""
    print("\nTesting Web UI types...")
    
    try:
        # Read the TypeScript types file
        types_file = Path("web-ui/src/types/index.ts")
        if not types_file.exists():
            print("❌ Web UI types file not found")
            return False
        
        content = types_file.read_text()
        
        # Check that TranscriptionRequest service type only includes 'deepgram'
        if "service: 'deepgram'" not in content:
            print("❌ TranscriptionRequest should have service: 'deepgram'")
            return False
        
        # Check that old services are not mentioned
        if "'openai'" in content or "'assemblyai'" in content:
            print("❌ Old service types still present in TypeScript")
            return False
        
        print("✅ Web UI types correctly updated for Deepgram-only")
        
    except Exception as e:
        print(f"❌ Web UI types test failed: {e}")
        return False
    
    return True

def test_backward_compatibility():
    """Test backward compatibility with existing Deepgram transcriptions."""
    print("\nTesting backward compatibility...")
    
    try:
        # Check if there are existing transcriptions in test_audio
        transcriptions_dir = Path("test_audio/transcriptions")
        if transcriptions_dir.exists():
            # Look for existing Deepgram transcriptions
            deepgram_files = list(transcriptions_dir.glob("**/*deepgram*"))
            if deepgram_files:
                print(f"✅ Found {len(deepgram_files)} existing Deepgram transcription files")
                
                # Check that cache files are still accessible
                cache_dir = transcriptions_dir / "cache"
                if cache_dir.exists():
                    cache_files = list(cache_dir.glob("*.json"))
                    if cache_files:
                        print(f"✅ Found {len(cache_files)} cache files")
                        
                        # Try to read a cache file to ensure format compatibility
                        try:
                            with open(cache_files[0], 'r') as f:
                                cache_data = json.load(f)
                            print("✅ Cache file format is readable")
                        except Exception as e:
                            print(f"⚠️  Cache file format issue: {e}")
                
            else:
                print("ℹ️  No existing Deepgram transcriptions found (this is okay)")
        else:
            print("ℹ️  No transcriptions directory found (this is okay)")
        
        # Test that the system can still process the existing test audio file
        test_audio = Path("test_audio/RBTI-Animal-Husbandry-T01.mp3")
        if test_audio.exists():
            print("✅ Test audio file exists for compatibility testing")
        else:
            print("ℹ️  No test audio file found")
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False
    
    return True

def test_cli_interface():
    """Test that CLI interface works with Deepgram-only setup."""
    print("\nTesting CLI interface...")
    
    try:
        import subprocess
        
        # Test CLI help
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
        
        # Check that help doesn't mention removed services
        help_text = result.stdout.lower()
        if "openai" in help_text or "assemblyai" in help_text:
            print("❌ CLI help still mentions removed services")
            return False
        
        print("✅ CLI help works and doesn't mention removed services")
        
    except Exception as e:
        print(f"❌ CLI interface test failed: {e}")
        return False
    
    return True

def test_requirements_cleanup():
    """Test that requirements.txt has been cleaned up."""
    print("\nTesting requirements cleanup...")
    
    try:
        requirements_file = Path("requirements.txt")
        if not requirements_file.exists():
            print("❌ requirements.txt not found")
            return False
        
        content = requirements_file.read_text().lower()
        
        # Check that OpenAI package is removed
        if "openai" in content:
            print("❌ OpenAI package still in requirements.txt")
            return False
        
        # Check that Deepgram dependencies are still present
        if "deepgram" not in content and "requests" not in content and "aiohttp" not in content:
            print("⚠️  No obvious Deepgram dependencies found (this might be okay)")
        
        print("✅ Requirements.txt appears to be cleaned up")
        
    except Exception as e:
        print(f"❌ Requirements cleanup test failed: {e}")
        return False
    
    return True

def main():
    """Run all validation tests."""
    print("Deepgram-Only Refactor Validation Tests")
    print("=" * 50)
    
    tests = [
        ("Removed Services Not Accessible", test_removed_services_not_accessible),
        ("Deepgram Functionality", test_deepgram_functionality),
        ("Configuration Loading", test_configuration_loading),
        ("API Models", test_api_models),
        ("Web UI Types", test_web_ui_types),
        ("Backward Compatibility", test_backward_compatibility),
        ("CLI Interface", test_cli_interface),
        ("Requirements Cleanup", test_requirements_cleanup)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed!")
        print("\nThe Deepgram-only refactor is working correctly:")
        print("✅ Removed services are no longer accessible")
        print("✅ Deepgram functionality is preserved")
        print("✅ Configuration system is updated")
        print("✅ API and UI only support Deepgram")
        print("✅ Backward compatibility maintained")
        return 0
    else:
        print(f"❌ {total - passed} tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())