"""Tests for configuration loading and validation."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from storyforge.config import (
    LLMBackendConfig,
    ProjectConfig,
    load_config,
    load_yaml_file,
)


class TestLLMBackendConfig:
    def test_basic_config(self):
        cfg = LLMBackendConfig(
            provider="openai",
            model="gpt-4o-mini",
            tier="small",
            api_key="sk-test",
        )
        assert cfg.provider == "openai"
        assert cfg.api_key == "sk-test"

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-from-env")
        cfg = LLMBackendConfig(
            provider="openai",
            model="gpt-4o-mini",
            tier="small",
            api_key_env="TEST_API_KEY",
        )
        assert cfg.api_key == "sk-from-env"

    def test_api_key_env_missing_warns(self, monkeypatch, caplog):
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
        import logging
        with caplog.at_level(logging.WARNING):
            cfg = LLMBackendConfig(
                provider="openai",
                model="gpt-4o-mini",
                tier="small",
                api_key_env="NONEXISTENT_KEY",
            )
        assert cfg.api_key is None
        assert "NONEXISTENT_KEY" in caplog.text

    def test_explicit_api_key_overrides_env(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-from-env")
        cfg = LLMBackendConfig(
            provider="openai",
            model="gpt-4o-mini",
            tier="small",
            api_key="sk-explicit",
            api_key_env="TEST_API_KEY",
        )
        assert cfg.api_key == "sk-explicit"

    def test_defaults(self):
        cfg = LLMBackendConfig(
            provider="ollama",
            model="llama3:8b",
            tier="small",
        )
        assert cfg.max_tokens == 4096
        assert cfg.context_window == 8192
        assert cfg.requests_per_minute == 60
        assert cfg.default_temperature == 0.7


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        config_data = {
            "project": {
                "name": "Test Novel",
                "author": "Tester",
            },
            "llm_backends": {
                "test_backend": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "tier": "small",
                    "api_key": "sk-test",
                },
            },
            "agents": {
                "world": {"type": "world", "llm_backend": "test_backend"},
                "plot": {"type": "plot", "llm_backend": "test_backend"},
                "writing": {"type": "writing", "llm_backend": "test_backend"},
            },
        }
        config_path = tmp_path / "project.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        cfg = load_config(tmp_path)
        assert cfg.project.name == "Test Novel"
        assert "test_backend" in cfg.llm_backends

    def test_load_missing_config(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Project config not found"):
            load_config(tmp_path)


class TestLoadYamlFile:
    def test_load_valid(self, tmp_path):
        path = tmp_path / "test.yaml"
        path.write_text("key: value\n")
        result = load_yaml_file(path)
        assert result == {"key": "value"}

    def test_load_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_yaml_file(tmp_path / "nonexistent.yaml")

    def test_load_empty(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("")
        result = load_yaml_file(path)
        assert result == {}
