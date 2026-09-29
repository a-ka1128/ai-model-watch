# AI Model Watch

Local-first AI model intelligence and weekly report platform.

## Current MVP slice

This repository starts with the Phase 1 foundation from the project specification:

- SQLite raw document database
- Official source registry for OpenAI, Anthropic, and Google
- RSS/Atom official collector plus an HTML index adapter for sources without RSS
- Content hashing for idempotent collection
- Provider interfaces for local relevance filtering and claim extraction
- Reddit public RSS collection for Phase 1 community evidence
- X API v2 recent-search collection for public AI-model posts
- Evidence-backed claim persistence and Korean weekly report generation
- CLI commands for database initialization and one-shot collection

The implementation deliberately keeps collection and analysis separate. A document is stored before any LLM processing, and analysis outputs are expected to be structured JSON.

## Quick start

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
py -m ai_model_watch init-db
py -m ai_model_watch collect-official
py -m ai_model_watch collect-reddit
py -m ai_model_watch collect-x
py -m ai_model_watch analyze --provider heuristic
py -m ai_model_watch translate --limit 100
py -m ai_model_watch cluster-claims
py -m ai_model_watch generate-report
py -m ai_model_watch run-weekly
py -m pytest
```

After installing the optional API dependencies, expose the stored evidence with:

```powershell
uvicorn ai_model_watch.api:create_app --factory --reload
```

Available endpoints are `/health`, `/documents`, `/claims`, `/clusters`, and `/reports/latest`. The API is read-only; collection and analysis remain explicit CLI/worker operations.

The default database is `data/ai_model_watch.db`. Set `AI_MODEL_WATCH_DB` to use another path.

### Korean translation

Original document text is always kept unchanged. Optional Korean translation is
stored separately in `translated_title` and `translated_content`. It uses the
configured local OpenAI-compatible endpoint (for example Ollama), so it does
not require a cloud translation API. Set these values in `.env` when the local
LLM is running:

```env
AI_MODEL_WATCH_LLM=openai-compatible
AI_MODEL_WATCH_LLM_ENDPOINT=http://127.0.0.1:11434
AI_MODEL_WATCH_LLM_MODEL=your-local-model
AI_MODEL_WATCH_TRANSLATION=true
AI_MODEL_WATCH_TRANSLATION_LIMIT=100
```

Then run `py -m ai_model_watch translate --limit 100`. Translation failures
are isolated per document and do not delete or overwrite the original.

### X collection

Copy `.env.example` to `.env` and put an X API v2 Bearer Token in
`AI_MODEL_WATCH_X_BEARER_TOKEN`. The token is read locally and is never written
to the database or report. Then run:

```powershell
py -m ai_model_watch collect-x
```

X collection is disabled by default. This protects against accidental API
usage while the account is on a plan that does not include post search. To
explicitly enable it later, set both `AI_MODEL_WATCH_ENABLE_X=true` and
`AI_MODEL_WATCH_X_BEARER_TOKEN` in `.env`. Until then, `run-weekly` collects
official sources and Reddit only, and `collect-x` exits without making an API
request.

## Repository layout

```text
src/ai_model_watch/
  cli.py              Command-line entry point
  config.py           Environment-backed settings
  database.py         SQLite schema and persistence
  models.py           Typed domain models
  sources.py          Phase 1 source registry
  collectors/         Source collection adapters
  llm/                Local LLM adapter contracts and providers
  analysis.py         Document-to-claim pipeline
  reporting.py        Evidence-linked Korean weekly report
tests/                Unit tests
```

Set `AI_MODEL_WATCH_LLM=openai-compatible`, `AI_MODEL_WATCH_LLM_ENDPOINT`, and `AI_MODEL_WATCH_LLM_MODEL` to use an Ollama/llama.cpp/vLLM-compatible local endpoint. The default `heuristic` provider is deterministic and intended only for offline smoke tests; it labels claims as community-level evidence and does not create precision scores.

`run_weekly.ps1` executes collection, analysis, clustering, and report generation as one repeatable job. It is meant to run on the local machine (see Windows automatic startup below), since the database, local LLM and GPU live there. `.github/workflows/ci.yml` only runs the test suite on pushes and pull requests; the weekly pipeline is intentionally not run in GitHub Actions.

## Windows automatic startup

Run once from PowerShell:

```powershell
.\setup_windows_autostart.ps1 -StartNow
```

This registers user-level tasks for the API, production dashboard, Control Panel, and Monday weekly pipeline. The dashboard is available at `http://127.0.0.1:3000` while the computer is on. To remove the tasks:

```powershell
.\stop_windows_autostart.ps1
```

자동 실행 모드의 DB와 로그는 프로젝트 권한 문제를 피하기 위해 `%LOCALAPPDATA%\AI_Model_Watch`에 저장됩니다.

관리 창을 하나만 띄우려면:

```powershell
.\start_control_panel.ps1
```

이 창에서 시작, 중지, 재시작, 수집 실행, 사이트 열기, 로그 폴더 열기와 현재 API/Website 상태 확인을 할 수 있습니다. 백엔드와 프론트엔드의 PowerShell 창은 숨겨진 상태로 실행됩니다. `수집 실행`은 공식 사이트와 Reddit 수집·분석·클러스터링·주간 리포트 생성을 즉시 시작하며, 진행 상황은 `weekly.log`에 기록됩니다.

## Evidence rules

The database keeps source metadata and raw documents separate from future claims and findings. No recommendation or confidence score is generated without stored evidence. Unavailable metadata is represented as `NULL`/`Unknown`, not guessed.
# 한글 기사 읽기

대시보드의 기본 화면은 한글로 정리된 글 목록입니다. 글 카드를 누르면 외부 사이트 대신
내부 상세 페이지에서 핵심 요약, 주요 내용, 주의할 점, 한글 본문을 읽을 수 있습니다.
원문은 상세 페이지 아래의 출처 링크로 확인할 수 있습니다.

컨트롤 패널의 **수집 실행**은 자료 수집 → 실제 본문 추출 → 로컬 LLM 번역·요약 → 저장을 실행합니다.
Ollama가 실행 중이어야 합니다. 현재 로컬 설정은 `qwen3-vl:8b-instruct`, 회당 최대 30건입니다.
긴 본문은 나누어 번역하며, 번역·요약이 완료된 글만 목록에 표시합니다.
공식 사이트는 개별 글 HTML을, Reddit은 공개 Atom 피드의 글 본문을 사용합니다.
이미지·링크 전용 글, 접근 차단 페이지는 실패로 기록하고 24시간 후 재시도합니다.
X는 기존 설정대로 비활성화되어 있습니다.

기존 데이터도 아래 명령으로 본문 수집 및 한글 기사 정리를 진행할 수 있습니다.
자동 실행과 동일한 데이터베이스를 지정해야 대시보드에 반영됩니다.

```powershell
$env:AI_MODEL_WATCH_DB = "$env:LOCALAPPDATA\AI_Model_Watch\ai_model_watch.db"
uv run python -m ai_model_watch translate --limit 30
```

# 번역 품질과 밝은 테마

전체 화면은 크림색 바탕·흰 카드·녹색 포인트의 밝은 테마를 사용합니다.
번역 모델은 분석 모델과 별도로 `AI_MODEL_WATCH_TRANSLATION_MODEL`로 지정할 수 있으며,
현재 설정은 로컬 `qwen3:14b`입니다. 추가 다운로드나 유료 외부 API는 사용하지 않습니다.

번역은 초안 생성 후 원문과 대조하는 교정을 거칩니다. 제품명·URL은 보호하고,
깨진 혼합 문자나 제품명 누락을 발견하면 새 결과 저장을 중단합니다.
요약·주요 내용은 번역문이 아닌 원문을 근거로 생성합니다.
자동 교정이 의미상의 오류를 전부 찾아내는 것은 아니므로 원문 확인 기능도 유지합니다.

이미 게시된 글을 현재 모델로 다시 번역하려면 다음 명령을 사용합니다.
`--force`는 새로운 웹 요청 없이 저장된 본문을 다시 번역합니다.

```powershell
$env:AI_MODEL_WATCH_DB = "$env:LOCALAPPDATA\AI_Model_Watch\ai_model_watch.db"
uv run python -m ai_model_watch translate --force --limit 30
```

