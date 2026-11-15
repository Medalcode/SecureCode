"""Unit tests for centralized Argon2id policy configuration."""

import pytest

from securecode.api.security import (
    ARGON2ID_SETTINGS,
    Type,
    hash_password,
    verify_password,
)


class TestArgon2idPolicy:
    """Tests for centralized Argon2id configuration values."""

    def test_memory_cost_is_64_miB(self):
        """memory_cost equivale a 64 MiB."""
        expected = 64 * 1024
        actual = ARGON2ID_SETTINGS["memory_cost"]
        assert actual == expected

    def test_time_cost_is_3(self):
        """time_cost es 3."""
        assert ARGON2ID_SETTINGS["time_cost"] == 3

    def test_parallelism_is_2(self):
        """parallelism es 2."""
        assert ARGON2ID_SETTINGS["parallelism"] == 2

    def test_hash_len_is_32(self):
        """hash_len es 32."""
        assert ARGON2ID_SETTINGS["hash_len"] == 32

    def test_type_is_argon2id(self):
        """el tipo configurado es Argon2id (Type.ID)."""
        assert ARGON2ID_SETTINGS["type"] is Type.ID

    def test_hash_password_generates_verifiable_hash(self):
        """hash_password() genera un hash verificable por verify_password()."""
        password = "TestPassword123!@#"
        hashed = hash_password(password)
        assert hashed is not None
        assert verify_password(password, hashed) is True

        # Verify wrong password fails
        assert verify_password("WrongPassword123!@#", hashed) is False

    def test_settings_are_valid_and_consistent(self):
        """Los valores de configuracion son validos y consistentes."""
        settings = ARGON2ID_SETTINGS
        # memory_cost must be a positive integer multiple of 64 KiB
        assert isinstance(settings["memory_cost"], int)
        assert settings["memory_cost"] > 0
        # time_cost must be positive
        assert isinstance(settings["time_cost"], int)
        assert settings["time_cost"] > 0
        # parallelism must be positive
        assert isinstance(settings["parallelism"], int)
        assert settings["parallelism"] > 0
        # hash_len must be positive
        assert isinstance(settings["hash_len"], int)
        assert settings["hash_len"] > 0
        # type must be Type.ID
        assert settings["type"] is Type.ID

    def test_hash_password_same_password_different_hashes(self):
        """Argon2id genera sal aleatoria: misma contraseña produce hashes diferentes."""
        password = "Argon2idTestPassword!23"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Ambos hashes verifican correctamente la misma contraseña
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
        # Los hashes son diferentes (Argon2id usa sal aleatoria)
        assert hash1 != hash2