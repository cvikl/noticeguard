"""Provider migration safeguards; no network or real credentials."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.genai.errors import ClientError
from app.llm import LLM, LLMUnavailable, detect_provider


def test_default_is_gemini_even_with_claude_installed(monkeypatch):
    monkeypatch.delenv('LLM_PROVIDER', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'unused-test-key')
    monkeypatch.setattr('app.llm.shutil.which', lambda _: '/usr/bin/claude')
    assert detect_provider() == 'gemini'


def test_explicit_legacy_provider_remains_available_for_historical_comparison(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'claude_cli')
    assert detect_provider() == 'claude_cli'


def test_provider_caches_do_not_mix():
    args = ('same prompt', 'same evidence', 0.0, 0, 'same system')
    assert LLM(provider='gemini').cache_key(*args) != LLM(provider='claude_cli',model='sonnet').cache_key(*args)


def gemini_with_response(monkeypatch, response):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-never-sent')
    llm = LLM(provider='gemini',model='gemini-2.5-flash',use_cache=False)
    generate = Mock(return_value=response)
    llm._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    return llm, generate


def test_mapping_output_budget_is_not_consumed_by_thinking(monkeypatch):
    llm,generate = gemini_with_response(monkeypatch,SimpleNamespace(text='{"covers":"yes"}'))
    llm.complete('classify',system='system',temperature=0.7,max_tokens=512)
    cfg = generate.call_args.kwargs['config']
    assert cfg.thinking_config.thinking_budget == 0
    assert cfg.max_output_tokens == 512 and cfg.temperature == 0.7
    assert cfg.automatic_function_calling.disable is True
    assert cfg.system_instruction == 'system'


def test_empty_response_is_unavailable(monkeypatch):
    llm,_ = gemini_with_response(monkeypatch,SimpleNamespace(text=''))
    with pytest.raises(LLMUnavailable,match='returned no text'):
        llm.complete('tag evidence')


def test_provider_errors_do_not_expose_payloads(monkeypatch):
    llm,generate = gemini_with_response(monkeypatch,None)
    generate.side_effect = ClientError(403,{'error':{'message':'sensitive provider detail'}})
    with pytest.raises(LLMUnavailable) as exc:
        llm.complete('tag evidence')
    assert '403' in str(exc.value)
    assert 'sensitive provider detail' not in str(exc.value)


def test_parallel_extraction_initialises_one_gemini_client(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import time
    from google import genai
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-never-sent')
    llm = LLM(provider='gemini',model='gemini-2.5-flash',use_cache=False)
    client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(return_value=SimpleNamespace(text='OK'))))
    def create(**kwargs):
        time.sleep(0.02)
        return client
    factory = Mock(side_effect=create)
    monkeypatch.setattr(genai,'Client',factory)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: llm.complete(str(i)).text,range(4)))
    assert results == ['OK']*4
    assert factory.call_count == 1


def test_gemini3_reserves_output_for_thinking(monkeypatch):
    llm,generate = gemini_with_response(monkeypatch,SimpleNamespace(text='{"covers":"yes"}'))
    llm.model = 'gemini-3.8-flash'
    llm.complete('classify',max_tokens=512)
    cfg = generate.call_args.kwargs['config']
    assert cfg.thinking_config.thinking_level.value.lower() == 'low'
    assert cfg.max_output_tokens == 4608
