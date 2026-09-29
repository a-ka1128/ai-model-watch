import pytest

from ai_model_watch.llm.openai_compatible import OpenAICompatibleProvider, validate_korean_translation


def test_names_and_urls_survive_translation_and_source_review():
    provider = OpenAICompatibleProvider('http://localhost:11434', 'test')
    calls = []
    def complete(system, user, schema=None):
        calls.append(system)
        return '{"title_ko":"Claude Code와 Codex가 필요한가요?","content_ko":"Foundry에서 Codex를 사용합니다. https://example.com/test"}'
    provider._complete = complete
    result = provider.translate('Do I need Claude Code and Codex?', 'Foundry uses Codex. https://example.com/test')
    assert 'Claude Code' in result.title_ko
    assert 'https://example.com/test' in result.content_ko
    assert len(calls) == 2


def test_missing_product_name_cannot_be_published():
    provider = OpenAICompatibleProvider('http://localhost:11434', 'test')
    provider._complete = lambda *args: '{"title_ko":"코딩 도구","content_ko":"코딩 도구를 사용합니다."}'
    with pytest.raises(ValueError, match='product name'):
        provider.translate('Codex', 'Using Codex')


@pytest.mark.parametrize('text', ['비ograms 퍼즐', '에이전트 허arness', '코데кс 플러그인'])
def test_mixed_translation_artifacts_are_rejected(text):
    with pytest.raises(ValueError):
        validate_korean_translation('Codex, nonogram and harness', text)


def test_product_name_with_korean_particle_is_valid():
    validate_korean_translation('Claude Code with Codex', 'Claude Code를 Codex와 함께 사용합니다.')
