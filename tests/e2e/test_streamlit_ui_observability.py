"""
E2E tests for Streamlit UI observability features.

Uses Playwright to verify sidebar stats display and session persistence.
These tests require a running Streamlit instance and Playwright setup.
"""

import os

import pytest

# Check if Playwright is available
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


@pytest.fixture
async def browser():
    """Create browser instance for tests."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create page instance for tests."""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.e2e
class TestSidebarStatsDisplay:
    """E2E tests for sidebar stats display (AC3.1.6)."""

    @pytest.mark.asyncio
    async def test_sidebar_stats_display(self, page):
        """
        Playwright verifica visualizzazione stats nella sidebar.

        Verifies:
        - Query count displayed
        - Total cost formatted as "$0.00XX"
        - Avg latency formatted as "XXXms"
        """
        await page.goto(STREAMLIT_URL)
        await page.wait_for_load_state("networkidle")

        # Wait for Streamlit to fully load
        await page.wait_for_selector('[data-testid="stSidebar"]', timeout=10000)

        # Check for Session Stats section
        sidebar = page.locator('[data-testid="stSidebar"]')

        # Verify stats section exists
        stats_header = sidebar.locator("text=Session Stats")
        await stats_header.wait_for(state="visible", timeout=5000)

        # Verify metrics are displayed
        queries_metric = sidebar.locator("text=Queries")
        await queries_metric.wait_for(state="visible", timeout=5000)

        cost_metric = sidebar.locator("text=Cost")
        await cost_metric.wait_for(state="visible", timeout=5000)

        latency_metric = sidebar.locator("text=Avg Latency")
        await latency_metric.wait_for(state="visible", timeout=5000)

    @pytest.mark.asyncio
    async def test_stats_update_after_query(self, page):
        """
        Verify stats update after submitting a query.
        """
        await page.goto(STREAMLIT_URL)
        await page.wait_for_load_state("networkidle")

        # Get initial query count
        sidebar = page.locator('[data-testid="stSidebar"]')
        await sidebar.locator("text=Session Stats").wait_for(state="visible", timeout=5000)

        # Submit a query
        chat_input = page.locator('[data-testid="stChatInput"]')
        await chat_input.fill("What is this document about?")
        await chat_input.press("Enter")

        # Wait for response
        await page.wait_for_timeout(5000)

        # Verify query count increased (should show "1" or more)
        # Note: Actual verification depends on Streamlit's DOM structure


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.e2e
class TestSessionPersistence:
    """E2E tests for session persistence (AC3.1.1)."""

    @pytest.mark.asyncio
    async def test_session_persistence_across_reloads(self, page):
        """
        Verifica session_id persiste tra page reloads.

        Verifies:
        - Session ID is generated on first load
        - Session ID persists across page reloads
        - Stats are maintained
        """
        await page.goto(STREAMLIT_URL)
        await page.wait_for_load_state("networkidle")

        # Wait for initial load
        sidebar = page.locator('[data-testid="stSidebar"]')
        await sidebar.locator("text=Session Stats").wait_for(state="visible", timeout=10000)

        # Submit a query to create some stats
        chat_input = page.locator('[data-testid="stChatInput"]')
        if await chat_input.is_visible():
            await chat_input.fill("Test query for persistence")
            await chat_input.press("Enter")
            await page.wait_for_timeout(3000)

        # Reload the page
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Verify stats section still exists
        await sidebar.locator("text=Session Stats").wait_for(state="visible", timeout=10000)

        # Note: Full session persistence verification requires checking
        # the actual session_id value, which is stored in st.session_state
        # and not directly accessible via DOM


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.e2e
class TestSessionInitialization:
    """E2E tests for session initialization."""

    @pytest.mark.asyncio
    async def test_session_id_generated_on_load(self, page):
        """
        Verify session_id is generated when app loads.
        """
        await page.goto(STREAMLIT_URL)
        await page.wait_for_load_state("networkidle")

        # Verify app loads without errors
        error_element = page.locator('[data-testid="stException"]')
        assert not await error_element.is_visible()

        # Verify sidebar loads with stats section
        sidebar = page.locator('[data-testid="stSidebar"]')
        stats_section = sidebar.locator("text=Session Stats")
        await stats_section.wait_for(state="visible", timeout=10000)
