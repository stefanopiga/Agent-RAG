"""
Pytest-playwright configuration and fixtures for E2E tests.

Fixtures organized by category:
- Browser configuration: browser_context_args, streamlit_app_url
- Test isolation: reset_streamlit_session
- Network interception: mock_openai_api, mock_langfuse_api
- Health check: wait_for_streamlit_app
- Timeout configuration: e2e_timeouts

Reference: docs/stories/5/5-4/5-4-implement-playwright-e2e-tests.md
Reference: docs/stories/5/5-4/5-4-technical-debt-analysis.md (CRITICAL gaps)
"""

import os
import time
from typing import Generator

import pytest
import requests
from playwright.sync_api import Page, Route

# ============================================================================
# ENVIRONMENT CONFIGURATION
# Reference: Technical Debt Analysis - Gap #7 (Environment-Specific Configuration)
# ============================================================================

# Base URL configurabile via environment variable
STREAMLIT_E2E_URL = os.getenv("STREAMLIT_E2E_URL", "http://localhost:8501")
E2E_TIMEOUT = int(os.getenv("E2E_TIMEOUT", "30000"))  # 30s default


@pytest.fixture(scope="session")
def streamlit_app_url() -> str:
    """
    Get Streamlit app URL from environment.

    Configurable via STREAMLIT_E2E_URL environment variable.
    Default: http://localhost:8501
    """
    return STREAMLIT_E2E_URL


# ============================================================================
# TIMEOUT CONFIGURATION
# Reference: Technical Debt Analysis - Gap #9 (Test Timeout Configuration)
# ============================================================================


@pytest.fixture(scope="session")
def e2e_timeouts() -> dict:
    """
    E2E test timeout configuration.

    Returns dict with timeout values for different operations:
    - navigation: Page load timeout (30s default)
    - element_wait: Element visibility timeout (10s default)
    - api_call: API response timeout (60s default)
    - short_wait: Quick element checks (5s default)
    """
    return {
        "navigation": int(os.getenv("E2E_NAVIGATION_TIMEOUT", "30000")),
        "element_wait": int(os.getenv("E2E_ELEMENT_TIMEOUT", "10000")),
        "api_call": int(os.getenv("E2E_API_TIMEOUT", "60000")),
        "short_wait": int(os.getenv("E2E_SHORT_TIMEOUT", "5000")),
    }


# ============================================================================
# BROWSER CONTEXT CONFIGURATION
# Reference: Story 5-4 Task 1 - browser_context_args fixture
# ============================================================================


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """
    Configure pytest-playwright browser context.

    Extends default pytest-playwright browser_context_args with:
    - Viewport size: 1280x720 (standard desktop)
    - Locale: it-IT (Italian locale)
    - Timezone: Europe/Rome
    - User agent: Custom for testing identification
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "it-IT",
        "timezone_id": "Europe/Rome",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) E2E-Test-Agent/1.0",
    }


# ============================================================================
# STREAMLIT APP HEALTH CHECK
# Reference: Technical Debt Analysis - Gap #10 (App Health Check)
# ============================================================================


@pytest.fixture(scope="session")
def wait_for_streamlit_app(streamlit_app_url: str) -> None:
    """
    Wait for Streamlit app to be ready before running tests.

    Polls Streamlit health endpoint until app is responsive.
    Raises RuntimeError if app not ready after max attempts.
    """
    max_attempts = 30
    health_url = f"{streamlit_app_url}/_stcore/health"

    for attempt in range(max_attempts):
        try:
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)

    raise RuntimeError(
        f"Streamlit app not ready at {streamlit_app_url} after {max_attempts} attempts. "
        "Ensure Streamlit is running: streamlit run app.py"
    )


# ============================================================================
# TEST ISOLATION - SESSION STATE CLEANUP
# Reference: Technical Debt Analysis - Gap #1 (CRITICAL: Test Isolation)
# ============================================================================


@pytest.fixture(autouse=True)
def reset_streamlit_session(page: Page, streamlit_app_url: str) -> Generator[None, None, None]:
    """
    Reset Streamlit session state before each test.

    CRITICAL for test isolation:
    - Clears browser cookies/localStorage before test
    - Navigates to app with fresh session
    - Clears cookies after test for cleanup

    This ensures each test starts with clean state and
    prevents test interdependence.
    """
    # Pre-test: Clear all cookies and storage
    page.context.clear_cookies()

    yield

    # Post-test: Clear cookies to ensure clean state for next test
    page.context.clear_cookies()


# ============================================================================
# NETWORK INTERCEPTION - API MOCKING
# Reference: Technical Debt Analysis - Gap #3 (CRITICAL: Network Interception)
# ============================================================================


@pytest.fixture
def mock_openai_api(page: Page) -> Generator[None, None, None]:
    """
    Mock OpenAI API calls for deterministic tests.

    Intercepts calls to OpenAI API and returns mocked responses.
    This enables:
    - Deterministic test results (no API variability)
    - No API costs during test execution
    - Testing without real OpenAI credentials
    - Testing error scenarios

    Usage:
        def test_with_mocked_api(page, mock_openai_api):
            # API calls are mocked
            ...
    """

    def handle_openai_route(route: Route) -> None:
        """Handle OpenAI API requests with mocked responses."""
        route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "id": "chatcmpl-test-123",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "gpt-4o-mini",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a mocked response for E2E testing. The document contains information about RAG systems and document processing."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }""",
        )

    # Intercept OpenAI API calls
    page.route("**/api.openai.com/**", handle_openai_route)
    page.route("**/v1/chat/completions", handle_openai_route)

    yield

    # Cleanup: Remove route handlers
    page.unroute("**/api.openai.com/**")
    page.unroute("**/v1/chat/completions")


@pytest.fixture
def mock_langfuse_api(page: Page) -> Generator[None, None, None]:
    """
    Mock LangFuse API calls for deterministic tests.

    Intercepts calls to LangFuse API and returns mocked responses.
    Prevents external API calls during testing.

    Usage:
        def test_with_mocked_langfuse(page, mock_langfuse_api):
            # LangFuse calls are mocked
            ...
    """

    def handle_langfuse_route(route: Route) -> None:
        """Handle LangFuse API requests with mocked responses."""
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"status": "ok", "id": "test-trace-id"}',
        )

    # Intercept LangFuse API calls
    page.route("**/langfuse.com/**", handle_langfuse_route)
    page.route("**/api/public/**", handle_langfuse_route)

    yield

    # Cleanup: Remove route handlers
    page.unroute("**/langfuse.com/**")
    page.unroute("**/api/public/**")


@pytest.fixture
def mock_all_external_apis(
    mock_openai_api: None, mock_langfuse_api: None
) -> Generator[None, None, None]:
    """
    Mock all external API calls for fully deterministic tests.

    Combines OpenAI and LangFuse mocking for complete isolation
    from external services.

    Usage:
        def test_fully_isolated(page, mock_all_external_apis):
            # All external APIs are mocked
            ...
    """
    yield


# ============================================================================
# SCREENSHOT AND VIDEO HELPERS
# Reference: Story 5-4 AC#14 - Screenshot/video recording for debugging
# ============================================================================


@pytest.fixture
def screenshot_on_failure(
    page: Page, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    """
    Capture screenshot on test failure.

    Automatically saves screenshot to tests/e2e/screenshots/ when test fails.
    Useful for debugging CI/CD failures.
    """
    yield

    # Check if test failed
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        test_name = request.node.name
        screenshot_path = f"tests/e2e/screenshots/failure_{test_name}.png"
        page.screenshot(path=screenshot_path)


# ============================================================================
# PYTEST HOOKS FOR FAILURE REPORTING
# ============================================================================


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for screenshot_on_failure fixture."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
