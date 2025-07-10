import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from playwright.async_api import Page, Browser, BrowserContext, ElementHandle

from automation.core import JobAutomator

@pytest.fixture
async def automator():
    """Fixture to create a JobAutomator instance with mocked Playwright objects."""
    with patch('playwright.async_api.async_playwright') as mock_playwright_context:
        mock_playwright_instance = AsyncMock()
        mock_playwright_context.start.return_value = mock_playwright_instance

        mock_browser = AsyncMock(spec=Browser)
        mock_playwright_instance.chromium.launch.return_value = mock_browser

        mock_context = AsyncMock(spec=BrowserContext)
        mock_browser.new_context.return_value = mock_context

        mock_page = AsyncMock(spec=Page)
        mock_context.new_page.return_value = mock_page

        # Mock page methods that might be called during setup or in the methods
        mock_page.on = MagicMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.screenshot = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        automator_instance = JobAutomator(headless=True)
        automator_instance.playwright = mock_playwright_instance
        automator_instance.browser = mock_browser
        automator_instance.context = mock_context
        automator_instance.page = mock_page

        yield automator_instance

        # Ensure cleanup if necessary, though mocks usually handle this
        if hasattr(automator_instance, 'close') and asyncio.iscoroutinefunction(automator_instance.close):
             await automator_instance.close()


@pytest.mark.asyncio
async def test_click_send_message_button_success(automator: JobAutomator):
    """Test successful click of the 'Send message' button."""
    mock_button = AsyncMock(spec=ElementHandle)
    mock_button.is_enabled.return_value = True

    # Configure wait_for_selector to return our mock button for one of the selectors
    async def side_effect_wait_for_selector(selector, state, timeout):
        if selector == 'button:has-text("Send Message")':
            return mock_button
        raise TimeoutError("Selector not found") # Simulate timeout for other selectors

    automator.page.wait_for_selector = AsyncMock(side_effect=side_effect_wait_for_selector)

    result = await automator.click_send_message_button()

    assert result is True
    automator.page.wait_for_selector.assert_any_call('button:has-text("Send Message")', state="visible", timeout=5000)
    mock_button.is_enabled.assert_called_once()
    mock_button.click.assert_called_once()
    automator.page.screenshot.assert_not_called() # No error screenshots

@pytest.mark.asyncio
async def test_click_send_message_button_not_found(automator: JobAutomator):
    """Test 'Send message' button not found."""
    automator.page.wait_for_selector = AsyncMock(side_effect=TimeoutError("Button not found"))

    result = await automator.click_send_message_button()

    assert result is False
    automator.page.screenshot.assert_called_once_with(path="send_message_button_not_found.png")

@pytest.mark.asyncio
async def test_click_send_message_button_disabled(automator: JobAutomator):
    """Test 'Send message' button found but disabled."""
    mock_button = AsyncMock(spec=ElementHandle)
    mock_button.is_enabled.return_value = False # Simulate disabled button

    # Return this disabled button for the first valid selector
    automator.page.wait_for_selector = AsyncMock(return_value=mock_button)

    result = await automator.click_send_message_button()

    assert result is False
    mock_button.is_enabled.assert_called() # is_enabled is checked
    mock_button.click.assert_not_called() # Click should not happen
    automator.page.screenshot.assert_called_once_with(path="send_message_button_not_found.png") # Because it will iterate and not find an enabled one

@pytest.mark.asyncio
async def test_click_send_message_button_runtime_error(automator: JobAutomator):
    """Test RuntimeError if page is not initialized."""
    automator.page = None # Simulate page not being initialized
    with pytest.raises(RuntimeError, match="Page not initialized"):
        await automator.click_send_message_button()

@pytest.mark.asyncio
async def test_click_view_job_button_success(automator: JobAutomator):
    """Test successful click of a 'View job' button."""
    mock_button_1 = AsyncMock(spec=ElementHandle)
    mock_button_1.is_visible.return_value = True
    mock_button_1.is_enabled.return_value = True
    mock_button_1.scroll_into_view_if_needed = AsyncMock()
    mock_button_1.click = AsyncMock()

    # query_selector_all returns a list of these mock buttons
    automator.page.query_selector_all = AsyncMock(return_value=[mock_button_1])

    result = await automator.click_view_job_button(job_index=0)

    assert result is True
    automator.page.query_selector_all.assert_any_call('a:has-text("View Job")') # Example selector
    mock_button_1.scroll_into_view_if_needed.assert_called_once()
    mock_button_1.click.assert_called_once()
    automator.page.wait_for_load_state.assert_called_once_with("domcontentloaded", timeout=10000)
    automator.page.screenshot.assert_not_called()

@pytest.mark.asyncio
async def test_click_view_job_button_not_found(automator: JobAutomator):
    """Test 'View job' button not found."""
    automator.page.query_selector_all = AsyncMock(return_value=[]) # No buttons found

    result = await automator.click_view_job_button()

    assert result is False
    automator.page.screenshot.assert_called_once_with(path="view_job_button_not_found.png")

@pytest.mark.asyncio
async def test_click_view_job_button_index_out_of_range(automator: JobAutomator):
    """Test 'View job' button index out of range."""
    mock_button_1 = AsyncMock(spec=ElementHandle)
    mock_button_1.is_visible.return_value = True
    mock_button_1.is_enabled.return_value = True

    automator.page.query_selector_all = AsyncMock(return_value=[mock_button_1]) # Only one button

    result = await automator.click_view_job_button(job_index=1) # Requesting second button

    assert result is False
    automator.page.screenshot.assert_called_once_with(path="view_job_button_index_error.png")

@pytest.mark.asyncio
async def test_click_view_job_button_not_visible_or_disabled(automator: JobAutomator):
    """Test 'View job' buttons are found but none are suitable (e.g. not visible/disabled)."""
    mock_button_invisible = AsyncMock(spec=ElementHandle)
    mock_button_invisible.is_visible.return_value = False # Not visible
    mock_button_invisible.is_enabled.return_value = True

    mock_button_disabled = AsyncMock(spec=ElementHandle)
    mock_button_disabled.is_visible.return_value = True
    mock_button_disabled.is_enabled.return_value = False # Disabled

    # query_selector_all returns these unsuitable buttons
    automator.page.query_selector_all = AsyncMock(return_value=[mock_button_invisible, mock_button_disabled])

    result = await automator.click_view_job_button(job_index=0)

    assert result is False # Should be false as no *suitable* button is found
    automator.page.screenshot.assert_called_once_with(path="view_job_button_not_found.png")


@pytest.mark.asyncio
async def test_click_view_job_button_uses_correct_selector_order(automator: JobAutomator):
    """Test that click_view_job_button tries selectors in order and uses the first one that works."""
    mock_button_good = AsyncMock(spec=ElementHandle)
    mock_button_good.is_visible.return_value = True
    mock_button_good.is_enabled.return_value = True
    mock_button_good.scroll_into_view_if_needed = AsyncMock()
    mock_button_good.click = AsyncMock()

    # Mock query_selector_all to behave differently based on selector
    async def qsa_side_effect(selector_str):
        if selector_str == 'a:has-text("View Job")': # First selector, returns nothing
            return []
        elif selector_str == 'button:has-text("View Job")': # Second selector, returns the good button
            return [mock_button_good]
        return [] # Default for other selectors

    automator.page.query_selector_all = AsyncMock(side_effect=qsa_side_effect)

    result = await automator.click_view_job_button(job_index=0)

    assert result is True
    # Check that it was called with both selectors (or at least up to the one that worked)
    automator.page.query_selector_all.assert_any_call('a:has-text("View Job")')
    automator.page.query_selector_all.assert_any_call('button:has-text("View Job")')
    mock_button_good.click.assert_called_once()
    automator.page.wait_for_load_state.assert_called_once()

@pytest.mark.asyncio
async def test_click_view_job_button_exception_during_click(automator: JobAutomator):
    """Test handling of an exception during the button click itself."""
    mock_button = AsyncMock(spec=ElementHandle)
    mock_button.is_visible.return_value = True
    mock_button.is_enabled.return_value = True
    mock_button.scroll_into_view_if_needed = AsyncMock()
    mock_button.click = AsyncMock(side_effect=Exception("Click failed unexpectedly")) # Simulate click error

    automator.page.query_selector_all = AsyncMock(return_value=[mock_button])

    result = await automator.click_view_job_button(job_index=0)

    assert result is False
    mock_button.click.assert_called_once()
    automator.page.screenshot.assert_called_once_with(path="view_job_button_error.png")

@pytest.mark.asyncio
async def test_click_view_job_button_runtime_error(automator: JobAutomator):
    """Test RuntimeError if page is not initialized for view_job_button."""
    automator.page = None # Simulate page not being initialized
    with pytest.raises(RuntimeError, match="Page not initialized"):
        await automator.click_view_job_button()

# Example of how to mock a specific element handle property
@pytest.mark.asyncio
async def test_element_handle_properties_mocked(automator: JobAutomator):
    mock_el = AsyncMock(spec=ElementHandle)
    mock_el.is_enabled.return_value = True # Mocking a method

    # If ElementHandle had properties like `innerText` (it uses methods like inner_text())
    # you might mock them using PropertyMock if needed, but for methods, return_value is fine.
    # For example, if it was a property:
    # type(mock_el).some_property = PropertyMock(return_value="some value")

    assert await mock_el.is_enabled() is True

    # This test is more of a demonstration of mocking ElementHandle methods
    # and doesn't directly test JobAutomator functionality beyond setup.
    # It can be useful for understanding how to set up more complex mocks.
    automator.page.wait_for_selector = AsyncMock(return_value=mock_el)
    # Dummy call to show it works with the automator's page
    btn = await automator.page.wait_for_selector("dummy")
    assert await btn.is_enabled() is True

# Add more tests as needed, for example, for different numbers of buttons,
# different job_index values, and specific error conditions during Playwright calls.

# To run these tests:
# Ensure pytest and pytest-asyncio are installed:
# pip install pytest pytest-asyncio
# Then run from the root of your project:
# pytest automation/test_core_buttons.py
