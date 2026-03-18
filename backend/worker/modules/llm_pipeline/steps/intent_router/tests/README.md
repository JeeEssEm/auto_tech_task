# IntentRouter E2E Tests

End-to-end tests for the IntentRouter module that validate behavior extraction and quote accuracy against a real LLM.

## Prerequisites

1. **Running LLM**: You need a LocalLLM or OpenAI-compatible API endpoint
   - For local Ollama: `ollama serve` with model `gpt-oss:20b`
   - For cloud (OpenAI, etc.): valid API key

2. **Python environment**: Tests use `pytest` and `pytest-asyncio`
   ```bash
   pip install pytest pytest-asyncio
   ```

## Configuration

Configure IntentRouter via environment variables (in `.env` or export):

```bash
# For local Ollama
export LLM_PIPELINE_V3_INTENT_ROUTER_PROVIDER=local
export LLM_PIPELINE_V3_INTENT_ROUTER_BASE_URL=http://localhost:11434/v1
export LLM_PIPELINE_V3_INTENT_ROUTER_MODEL=gpt-oss:20b

# For cloud (OpenAI, etc.)
export LLM_PIPELINE_V3_INTENT_ROUTER_PROVIDER=cloud
export LLM_PIPELINE_V3_INTENT_ROUTER_BASE_URL=https://api.openai.com/v1
export LLM_PIPELINE_V3_INTENT_ROUTER_MODEL=gpt-4
export LLM_PIPELINE_V3_INTENT_ROUTER_API_KEY=sk-...
```

## Running Tests

### Run all E2E tests:

```bash
cd /path/to/auto_tech_task
pytest backend/worker/modules/llm_pipeline/steps/intent_router/tests/ -v -s
```

### Run specific test file:

```bash
pytest backend/worker/modules/llm_pipeline/steps/intent_router/tests/test_intent_router_e2e.py -v
```

### Run by behavior class:

```bash
# Test Architect behavior
pytest backend/worker/modules/llm_pipeline/steps/intent_router/tests/test_intent_router_e2e.py::TestIntentRouterArchitect -v

# Test Guardian behavior
pytest backend/worker/modules/llm_pipeline/steps/intent_router/tests/test_intent_router_e2e.py::TestIntentRouterGuardian -v
```

### Run parameterized scenario tests:

```bash
pytest backend/worker/modules/llm_pipeline/steps/intent_router/tests/test_scenarios.py -v
```

### Skip slow tests:

```bash
pytest ... -m "not slow"
```

### Run with logging output:

```bash
pytest ... -v -s --log-cli-level=DEBUG
```

## Test Structure

### Test Files

1. **test_intent_router_e2e.py** - Main E2E test suite
   - `TestIntentRouterArchitect` - Tests for TZ modification requests
   - `TestIntentRouterConsultant` - Tests for Q&A requests
   - `TestIntentRouterHarvester` - Tests for new information/facts
   - `TestIntentRouterGuardian` - Tests for off-topic filtering
   - `TestIntentRouterInterrogator` - Tests for missing data detection
   - `TestIntentRouterMixed` - Tests for multi-behavior activation
   - `TestIntentRouterResponseValidity` - Schema and structure validation

2. **test_scenarios.py** - Parameterized tests
   - `TestIntentRouterParametrized` - Behavior activation with different inputs
   - `TestIntentRouterQuoteAccuracy` - Quote substring extraction validation
   - `TestIntentRouterErrorHandling` - Edge cases and error handling
   - `TestIntentRouterPerformance` - Sequential and concurrent request handling

3. **conftest.py** - Pytest configuration and fixtures
   - Async event loop setup
   - Settings loading from environment
   - LLM adapter initialization
   - Test data provider

## Expected Behavior

Each test validates:

1. **Response Schema**: IntentRouterResponse contains valid behaviors
2. **Behavior Activation**: Correct behaviors activated for given input
3. **Quote Accuracy**: Each behavior's `user_prompt` is an exact substring from the input
4. **Enum Validity**: All roles and reasons are valid enum values

### Example Test Flow

```python
# Input
user_prompt = "перегенируй блок ТЗ с требованием к СУБД, поставь mysql, и еще напиши код быстрой сортировки"

# Expected output
behaviors = [
    {
        "role": "Architect",
        "reason": "new_fact_detected",
        "user_prompt": "перегенируй блок ТЗ с требованием к СУБД, поставь mysql"  # EXACT QUOTE
    },
    {
        "role": "Guardian",
        "reason": "offtopic_segment",
        "user_prompt": "напиши код быстрой сортировки"  # EXACT QUOTE
    }
]
```

## Troubleshooting

### LLM Connection Issues

```
ERROR: Failed to load IntentRouter settings
  - Ensure LLM endpoint is running and reachable
  - Check base URL: http://localhost:11434/v1 (for Ollama)
  - Verify model exists: ollama list | grep gpt-oss
```

### JSON Parsing Errors

```
Error: "Invalid JSON/schema from LLM (retryable)"
  - LLM is not returning valid JSON
  - Check temperature is not too high (default 0.1)
  - Verify system prompt includes JSON schema
```

### Timeout Issues

```
Error: "timeout waiting for response"
  - Increase timeout: LLM_PIPELINE_V3_INTENT_ROUTER_TIMEOUT_SECONDS=60
  - Ensure LLM model is fully loaded
  - Check system resources (CPU/memory)
```

## Performance Notes

- Local Ollama: 5-15 seconds per request (depends on model and hardware)
- Cloud APIs: 2-5 seconds per request
- Retries on invalid JSON: Up to 3 additional attempts per request

## Logs

Test logs are written to `intent_router_test.log` in the current directory.

Full request/response logs (including tokens) are in individual adapter logs.

## Contributing New Tests

To add new test scenarios:

1. Add test case to appropriate test class in `test_intent_router_e2e.py`
2. Use `IntentRouterRequest` with your test prompt
3. Assert on `IntentRouterResponse.behaviors`
4. Verify `user_prompt` is exact substring of input

Example:

```python
@pytest.mark.asyncio
async def test_my_scenario(self, intent_router):
    request = IntentRouterRequest(
        user_prompt="My test input with some keywords",
        attachments=[],
    )

    result = await intent_router.extract_behaviours(request)

    assert isinstance(result, IntentRouterResponse)
    assert len(result.behaviors) > 0
    # Your assertions here
    for behavior in result.behaviors:
        assert behavior.user_prompt in request.user_prompt
```
