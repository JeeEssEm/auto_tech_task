import httpx

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    
    # Retry on network/timeout errors
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    
    # Retry on JSON/schema validation errors from LLM response
    if isinstance(exc, ValueError):
        return "Invalid JSON/schema from LLM" in str(exc)
    
    return False
