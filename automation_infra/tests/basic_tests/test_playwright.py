from playwright.sync_api import Browser
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_login_page(browser: Browser, base_config):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto("https://playwright.dev/python/")
    name = page.locator(".navbar__title").inner_text()
    assert name == "Playwright for Python"
