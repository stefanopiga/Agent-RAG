"""
E2E tests for Streamlit query workflow.

Tests the complete user journey:
1. Navigate to Streamlit app
2. Enter query in chat input
3. Submit query
4. Verify response is displayed

Uses pytest-playwright for browser automation.
Reference: docs/stories/5/5-4/5-4-implement-playwright-e2e-tests.md

AC Coverage:
- AC#1 (AC#13): Simulates user query and validates response
- AC#2 (AC#14): Screenshot/video recording for debugging
- AC#3 (AC#15): Headless mode execution (default behavior)
"""

import os

import pytest
from playwright.sync_api import Page, expect

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# pytest markers for E2E and slow tests
pytestmark = [pytest.mark.e2e, pytest.mark.slow]


# ============================================================================
# QUERY WORKFLOW TESTS (AC#1 / AC#13)
# Reference: Story 5-4 Task 2 - Implement Streamlit query workflow E2E test
# ============================================================================


class TestStreamlitQueryWorkflow:
    """E2E tests for Streamlit query workflow (AC#1/AC#13)."""

    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_streamlit_app_loads_successfully(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Verify Streamlit app loads without errors.

        Arrange: Streamlit app running
        Act: Navigate to app URL
        Assert: App loads, no error displayed, sidebar visible
        """
        # Arrange & Act
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Assert: No Streamlit exception displayed
        error_element = page.locator('[data-testid="stException"]')
        expect(error_element).not_to_be_visible(timeout=e2e_timeouts["short_wait"])

        # Assert: Sidebar is visible
        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Assert: Chat input is visible (main interaction element)
        chat_input = page.locator('[data-testid="stChatInput"]')
        expect(chat_input).to_be_visible(timeout=e2e_timeouts["element_wait"])

    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_streamlit_query_workflow_complete(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Test complete query workflow: input -> submit -> response.

        Arrange: Streamlit app running, navigate to app
        Act: Enter query and submit
        Assert: Response is displayed in chat

        This test verifies AC#13: simulates user query and validates response.
        """
        # Arrange: Navigate to app
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Act: Find chat input and enter query
        # Note: stChatInput is a <div>, the actual textarea is inside
        chat_input_container = page.locator('[data-testid="stChatInput"]')
        expect(chat_input_container).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Find the actual textarea inside the container
        chat_input = chat_input_container.locator("textarea")

        # Enter test query
        test_query = "What is this document about?"
        chat_input.fill(test_query)
        chat_input.press("Enter")

        # Assert: User message appears in chat
        user_message = page.locator('[data-testid="stChatMessage"]').filter(
            has_text=test_query
        )
        expect(user_message).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Assert: Assistant response appears (wait longer for LLM response)
        # Look for chat messages - should have at least 2 (user + assistant)
        chat_messages = page.locator('[data-testid="stChatMessage"]')
        expect(chat_messages).to_have_count(
            2, timeout=e2e_timeouts["api_call"]
        )

        # Take screenshot after workflow completion (AC#14)
        page.screenshot(path="tests/e2e/screenshots/query_workflow_success.png")

    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_streamlit_sidebar_stats_visible(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Verify sidebar stats section is visible.

        Arrange: Streamlit app running
        Act: Navigate to app
        Assert: Session Stats section visible in sidebar
        """
        # Arrange & Act
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Assert: Sidebar exists
        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Assert: Session Stats header exists
        stats_header = sidebar.locator("text=Session Stats")
        expect(stats_header).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Assert: Metrics are displayed
        queries_text = sidebar.locator("text=Queries")
        expect(queries_text).to_be_visible(timeout=e2e_timeouts["short_wait"])

        cost_text = sidebar.locator("text=Cost")
        expect(cost_text).to_be_visible(timeout=e2e_timeouts["short_wait"])

        latency_text = sidebar.locator("text=Avg Latency")
        expect(latency_text).to_be_visible(timeout=e2e_timeouts["short_wait"])


# ============================================================================
# SCREENSHOT/VIDEO TESTS (AC#2 / AC#14)
# Reference: Story 5-4 Task 2 - Screenshot/video capture
# ============================================================================


class TestScreenshotVideoRecording:
    """E2E tests for screenshot/video recording functionality (AC#2/AC#14)."""

    def test_screenshot_capture_after_page_load(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Verify screenshot can be captured after page load.

        This test validates AC#14: screenshot capture for debugging.
        """
        # Arrange & Act
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Wait for main content to load
        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Act: Take screenshot
        screenshot_path = "tests/e2e/screenshots/page_load_test.png"
        page.screenshot(path=screenshot_path)

        # Assert: Screenshot file exists
        assert os.path.exists(screenshot_path), f"Screenshot not saved at {screenshot_path}"
        assert os.path.getsize(screenshot_path) > 0, "Screenshot file is empty"

    def test_screenshot_capture_full_page(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Verify full page screenshot can be captured.

        Captures entire scrollable page, not just viewport.
        """
        # Arrange & Act
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Act: Take full page screenshot
        screenshot_path = "tests/e2e/screenshots/full_page_test.png"
        page.screenshot(path=screenshot_path, full_page=True)

        # Assert: Screenshot file exists and has content
        assert os.path.exists(screenshot_path), f"Screenshot not saved at {screenshot_path}"
        assert os.path.getsize(screenshot_path) > 0, "Screenshot file is empty"


# ============================================================================
# HEADLESS MODE TESTS (AC#3 / AC#15)
# Reference: Story 5-4 Task 5 - Verify headless mode
# ============================================================================


class TestHeadlessMode:
    """E2E tests for headless mode execution (AC#3/AC#15)."""

    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_headless_mode_execution(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Verify tests execute correctly in headless mode.

        pytest-playwright runs in headless mode by default.
        This test validates AC#15: E2E tests execute in headless mode.
        """
        # Arrange & Act
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Wait for Streamlit app to fully initialize - wait for chat input
        chat_input = page.locator('[data-testid="stChatInput"]')
        expect(chat_input).to_be_visible(timeout=e2e_timeouts["element_wait"])
        # Assert: Page loaded successfully (proves headless mode works)
        title = page.title()
        assert "Docling RAG Agent" in title or "Streamlit" in title, (
            f"Unexpected page title: {title}"
        )

        # Assert: Chat input visible (UI rendered correctly in headless)
        chat_input = page.locator('[data-testid="stChatInput"]')
        expect(chat_input).to_be_visible(timeout=e2e_timeouts["element_wait"])


# ============================================================================
# TEST ISOLATION TESTS
# Reference: Technical Debt Analysis - Gap #1 (Test Isolation)
# ============================================================================


class TestIsolation:
    """Tests to verify test isolation and session state cleanup."""

    def test_session_state_isolated_first(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        First test to verify session isolation.

        Submits a query and verifies it appears.
        Next test should NOT see this query.
        """
        # Arrange
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Act: Submit a unique query
        # Note: stChatInput is a <div>, the actual textarea is inside
        chat_input_container = page.locator('[data-testid="stChatInput"]')
        expect(chat_input_container).to_be_visible(timeout=e2e_timeouts["element_wait"])

        chat_input = chat_input_container.locator("textarea")
        unique_query = "ISOLATION_TEST_QUERY_FIRST_12345"
        chat_input.fill(unique_query)
        chat_input.press("Enter")

        # Assert: Query appears
        user_message = page.locator('[data-testid="stChatMessage"]').filter(
            has_text=unique_query
        )
        expect(user_message).to_be_visible(timeout=e2e_timeouts["element_wait"])

    def test_session_state_isolated_second(
        self,
        page: Page,
        streamlit_app_url: str,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Second test to verify session isolation.

        Should NOT see the query from the first test.
        This verifies reset_streamlit_session fixture works.
        """
        # Arrange
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Assert: Previous test's query should NOT be visible
        previous_query = page.locator("text=ISOLATION_TEST_QUERY_FIRST_12345")
        expect(previous_query).not_to_be_visible(timeout=e2e_timeouts["short_wait"])

        # Assert: Chat should be empty (fresh session)
        chat_messages = page.locator('[data-testid="stChatMessage"]')
        # Should have 0 chat messages (fresh session)
        expect(chat_messages).to_have_count(0, timeout=e2e_timeouts["short_wait"])

# ============================================================================
# NETWORK INTERCEPTION TESTS
# Reference: Technical Debt Analysis - Gap #3 (Network Interception)
# ============================================================================


class TestNetworkInterception:
    """Tests for network interception functionality."""

    @pytest.mark.skip(reason="Requires mocked backend - run manually")
    def test_with_mocked_openai_api(
        self,
        page: Page,
        streamlit_app_url: str,
        mock_openai_api: None,
        wait_for_streamlit_app: None,
        e2e_timeouts: dict,
    ) -> None:
        """
        Test query workflow with mocked OpenAI API.

        Uses network interception to mock OpenAI responses.
        This enables deterministic tests without API costs.
        """
        # Arrange
        page.goto(streamlit_app_url, timeout=e2e_timeouts["navigation"])
        page.wait_for_load_state("networkidle", timeout=e2e_timeouts["navigation"])

        # Act: Submit query (will use mocked API)
        # Note: stChatInput is a <div>, the actual textarea is inside
        chat_input_container = page.locator('[data-testid="stChatInput"]')
        expect(chat_input_container).to_be_visible(timeout=e2e_timeouts["element_wait"])

        # Find the actual textarea inside the container
        chat_input = chat_input_container.locator("textarea")
        chat_input.fill("Test query with mocked API")
        chat_input.press("Enter")

        # Assert: Response contains mocked content
        # Note: Actual response depends on how app handles mocked API
        chat_messages = page.locator('[data-testid="stChatMessage"]')
        expect(chat_messages).to_have_count(2, timeout=e2e_timeouts["api_call"])

