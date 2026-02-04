"""
Unit tests for SecureKeyManager.

These tests MUST FAIL until security.py is implemented.

Tests:
- T020: SecureKeyManager functionality
"""

import os
import pytest


class TestSecureKeyManager:
    """Tests for secure API key handling per Constitution II."""

    def test_reads_key_from_environment(self):
        """SecureKeyManager should read API key from GEMINI_API_KEY env var."""
        from agent_auditor.security import SecureKeyManager
        
        os.environ["GEMINI_API_KEY"] = "test-key-12345"
        
        manager = SecureKeyManager()
        key = manager.get_key()
        
        assert key == "test-key-12345"

    def test_raises_without_env_var(self):
        """SecureKeyManager should raise if GEMINI_API_KEY is not set."""
        from agent_auditor.security import SecureKeyManager, APIKeyNotFoundError
        
        # Ensure env var is not set
        os.environ.pop("GEMINI_API_KEY", None)
        
        with pytest.raises(APIKeyNotFoundError):
            manager = SecureKeyManager()
            manager.get_key()

    def test_key_never_in_str_repr(self):
        """API key should never appear in str() or repr()."""
        from agent_auditor.security import SecureKeyManager
        
        os.environ["GEMINI_API_KEY"] = "AIzaSyD_secret_key_12345"
        
        manager = SecureKeyManager()
        
        assert "AIzaSyD" not in str(manager)
        assert "AIzaSyD" not in repr(manager)
        assert "secret" not in str(manager)
        assert "secret" not in repr(manager)

    def test_key_masked_display(self):
        """get_masked_key() should show only first/last 2 chars."""
        from agent_auditor.security import SecureKeyManager
        
        os.environ["GEMINI_API_KEY"] = "AIzaSyD_my_secret_key"
        
        manager = SecureKeyManager()
        masked = manager.get_masked_key()
        
        # Should show something like "AI***...ey"
        assert masked.startswith("AI")
        assert masked.endswith("ey")
        assert "secret" not in masked
        assert len(masked) < len("AIzaSyD_my_secret_key")

    def test_sanitize_removes_key_from_string(self):
        """sanitize() should remove API key from any string."""
        from agent_auditor.security import SecureKeyManager
        
        os.environ["GEMINI_API_KEY"] = "secret_api_key_123"
        
        manager = SecureKeyManager()
        
        dirty = "Error occurred with key secret_api_key_123 in request"
        clean = manager.sanitize(dirty)
        
        assert "secret_api_key_123" not in clean
        assert "[REDACTED]" in clean or "***" in clean

    def test_sanitize_error_creates_safe_exception(self):
        """create_safe_error() should return exception without key."""
        from agent_auditor.security import SecureKeyManager
        
        os.environ["GEMINI_API_KEY"] = "my_secret_key_value"
        
        manager = SecureKeyManager()
        
        original_error = Exception("Failed with key my_secret_key_value")
        safe_error = manager.create_safe_error(original_error)
        
        assert "my_secret_key_value" not in str(safe_error)

    def test_validates_key_format(self):
        """SecureKeyManager should validate key looks like a Gemini key."""
        from agent_auditor.security import SecureKeyManager, InvalidAPIKeyError
        
        # Empty key should fail
        os.environ["GEMINI_API_KEY"] = ""
        
        with pytest.raises(InvalidAPIKeyError):
            manager = SecureKeyManager()
            manager.validate()

    def test_supports_alternative_env_var(self):
        """SecureKeyManager should also check AISTUDIO__API_KEY."""
        from agent_auditor.security import SecureKeyManager
        
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["AISTUDIO__API_KEY"] = "alt_key_from_aistudio"
        
        manager = SecureKeyManager()
        key = manager.get_key()
        
        assert key == "alt_key_from_aistudio"


class TestSecurityPatterns:
    """Test security patterns and constants."""

    def test_sensitive_patterns_defined(self):
        """SENSITIVE_PATTERNS should be defined for log filtering."""
        from agent_auditor.security import SENSITIVE_PATTERNS
        
        assert isinstance(SENSITIVE_PATTERNS, (list, tuple))
        assert len(SENSITIVE_PATTERNS) > 0

    def test_patterns_match_common_key_formats(self):
        """Patterns should match AIzaSy and similar key formats."""
        from agent_auditor.security import SENSITIVE_PATTERNS
        import re
        
        test_keys = [
            "AIzaSyD_test_key_123",
            "AIzaSyA_another_key",
        ]
        
        for key in test_keys:
            matched = any(re.search(pattern, key) for pattern in SENSITIVE_PATTERNS)
            assert matched, f"Pattern should match {key}"
