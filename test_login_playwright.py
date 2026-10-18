"""
Playwright automated test suite for Dayflow HRMS Login & Account Switching:
1. Desktop Viewport: Login page UI rendering & 6 demo account autofill cards
2. Password Show/Hide toggle
3. Autofill Demo Credentials (HR Admin & Employee)
4. Successful Login as HR Admin
5. Account Switching: Visiting /login/ while authenticated, switching from HR Admin to Employee
6. Mobile Viewport (390x844): Mobile login UI, autofill & responsive layout
7. Logout verification
"""
import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
SERVER_PROC = None

def ensure_server():
    global SERVER_PROC
    try:
        urllib.request.urlopen(f"{BASE_URL}/login/", timeout=2)
        print("[OK] Django server is already running on port 8000")
        return
    except Exception:
        pass

    print("Starting Django development server on 127.0.0.1:8000...")
    venv_python = sys.executable
    SERVER_PROC = subprocess.Popen(
        [venv_python, "-u", "backend/manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    # Wait for server to start
    for i in range(20):
        time.sleep(1)
        try:
            res = urllib.request.urlopen(f"{BASE_URL}/login/", timeout=3)
            if res.status == 200:
                print(f"[OK] Django server started successfully (in {i+1}s)")
                return
        except Exception:
            pass
    raise RuntimeError("Failed to start Django server within 20 seconds")


def cleanup_server():
    global SERVER_PROC
    if SERVER_PROC:
        print("Stopping Django server...")
        SERVER_PROC.terminate()
        try:
            SERVER_PROC.wait(timeout=3)
        except Exception:
            SERVER_PROC.kill()
        print("[OK] Django server stopped")


def run_tests():
    ensure_server()

    passed = 0
    failed = 0

    def record(name, condition, details=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name} {details}")
        else:
            failed += 1
            print(f"  [FAIL] {name} - {details}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("\n=== 1. DESKTOP LOGIN UI & AUTOFILL CARDS ===")
        context.clear_cookies()
        page.goto(f"{BASE_URL}/login/")
        page.wait_for_selector("#f")

        record("Login page title contains 'Sign in'", "Sign in" in page.title())
        record("Page heading is 'Welcome back'", page.locator("h1").inner_text() == "Welcome back")

        demo_cards = page.locator(".demo-card")
        record("6 Demo Account Autofill cards exist", demo_cards.count() == 6, f"(Found {demo_cards.count()})")

        card_text = page.locator(".demo-grid").inner_text()
        for role in ["HR Admin", "HR Manager", "Super Admin", "Manager", "Recruiter", "Employee"]:
            record(f"Demo card for '{role}' is present", role in card_text)

        # Capture desktop login screenshot
        os.makedirs("test_artifacts", exist_ok=True)
        page.screenshot(path="test_artifacts/desktop_login_page.png")
        print("  [INFO] Captured desktop screenshot -> test_artifacts/desktop_login_page.png")

        print("\n=== 2. PASSWORD TOGGLE VISIBILITY ===")
        pw_input = page.locator("#password")
        pw_toggle = page.locator("#pw-toggle")

        record("Password field default type is 'password'", pw_input.get_attribute("type") == "password")
        pw_toggle.click()
        record("Password field type toggles to 'text'", pw_input.get_attribute("type") == "text")
        pw_toggle.click()
        record("Password field type toggles back to 'password'", pw_input.get_attribute("type") == "password")

        print("\n=== 3. AUTOFILL DEMO CREDENTIALS ===")
        email_input = page.locator("#email")
        btn = page.locator("#go")

        # Click HR Admin card
        hr_card = page.locator(".demo-card").filter(has_text="HR Admin").first
        hr_card.click()

        record("HR Admin email autofilled", email_input.input_value() == "hradmin@dayflow.dev")
        record("Password autofilled", pw_input.input_value() == "Dayflow@2026")
        record("Card marked with active class", "active" in (hr_card.get_attribute("class") or ""))
        record("Button text updated with role", "HR Admin" in btn.inner_text())

        # Click Employee card to test switching autofill
        emp_card = page.locator(".demo-card").filter(has_text="Employee").first
        emp_card.click()

        record("Switched autofill to Employee email", email_input.input_value() == "employee@dayflow.dev")
        record("Employee card marked with active class", "active" in (emp_card.get_attribute("class") or ""))
        record("Button text updated to Employee", "Employee" in btn.inner_text())

        print("\n=== 4. SIGN IN AS HR ADMIN ===")
        hr_card.click()
        btn.click()

        page.wait_for_url("**/dashboard/**", timeout=8000)
        record("Redirected to /dashboard/ after login", "/dashboard/" in page.url)

        page.wait_for_selector(".topbar")
        topbar_text = page.locator(".topbar").inner_text()
        record("Topbar shows HR Admin user Hetal Shah", "Hetal Shah" in topbar_text or "HR Admin" in topbar_text)

        print("\n=== 5. ACCOUNT SWITCHING (PREVIOUS ACCOUNT OVERWRITE FIX) ===")
        # Navigate to /login/ while authenticated as HR Admin
        page.goto(f"{BASE_URL}/login/")
        page.wait_for_selector(".logged-in-banner")

        banner = page.locator(".logged-in-banner")
        record("Login page does NOT force-redirect to dashboard", "/login/" in page.url)
        record("Active session banner is displayed", banner.is_visible())
        record("Banner identifies current user as Hetal Shah (HR Admin)", "Hetal Shah" in banner.inner_text())

        # Switch to Employee using Autofill
        emp_card = page.locator(".demo-card").filter(has_text="Employee").first
        emp_card.click()
        record("Autofilled Employee credentials while on login page", email_input.input_value() == "employee@dayflow.dev")

        btn.click()
        page.wait_for_url("**/dashboard/**", timeout=8000)
        record("Successfully redirected to dashboard after account switch", "/dashboard/" in page.url)

        # Verify current user is now Esha Patel (Employee) and not Hetal Shah
        page.wait_for_selector(".topbar")
        topbar_text = page.locator(".topbar").inner_text()
        record("Topbar now shows Employee Esha Patel", "Esha Patel" in topbar_text)
        record("HR Admin is cleanly replaced (no session collision)", "Hetal Shah" not in topbar_text)

        print("\n=== 6. MOBILE VIEWPORT TEST (390x844 - iPhone) ===")
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        mobile_page = mobile_context.new_page()
        mobile_page.goto(f"{BASE_URL}/login/")
        mobile_page.wait_for_selector("#f")

        # Capture mobile login screenshot
        mobile_page.screenshot(path="test_artifacts/mobile_login_page.png")
        print("  [INFO] Captured mobile screenshot -> test_artifacts/mobile_login_page.png")

        # Check mobile responsiveness
        card_box = mobile_page.locator(".auth .card").bounding_box()
        record("Login card fits inside mobile viewport (<= 390px)", card_box["width"] <= 390, f"(Width: {card_box['width']}px)")

        # Verify demo accounts on mobile
        mobile_demo_cards = mobile_page.locator(".demo-card")
        record("All 6 demo cards render on mobile", mobile_demo_cards.count() == 6)

        # Test mobile autofill
        mobile_recruiter_card = mobile_page.locator(".demo-card").filter(has_text="Recruiter").first
        mobile_recruiter_card.click()

        m_email = mobile_page.locator("#email")
        record("Mobile autofill sets Recruiter email", m_email.input_value() == "recruiter@dayflow.dev")

        # Test mobile submit
        mobile_page.locator("#go").click()
        mobile_page.wait_for_url("**/dashboard/**", timeout=8000)
        record("Mobile login redirects to /dashboard/", "/dashboard/" in mobile_page.url)

        # Verify mobile bottom nav exists
        mobile_bottom_nav = mobile_page.locator(".bottom-nav")
        record("Mobile bottom navigation is visible", mobile_bottom_nav.is_visible())

        print("\n=== 7. LOGOUT VERIFICATION ===")
        mobile_page.goto(f"{BASE_URL}/logout/")
        mobile_page.wait_for_url("**/login/**", timeout=8000)
        record("Visiting /logout/ cleanly redirects to /login/", "/login/" in mobile_page.url)

        # Verify session is ended
        mobile_page.goto(f"{BASE_URL}/dashboard/")
        record("Accessing /dashboard/ after logout redirects to /login/", "/login/" in mobile_page.url)

        browser.close()

    print(f"\n==========================================")
    print(f"PLAYWRIGHT TESTS COMPLETED: {passed} PASSED, {failed} FAILED")
    print(f"==========================================")
    return failed == 0

if __name__ == "__main__":
    try:
        success = run_tests()
        cleanup_server()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        cleanup_server()
        sys.exit(1)
