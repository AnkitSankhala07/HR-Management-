"""
Playwright automated test suite for Dayflow HRMS Login & Multi-Account Support:
1. Desktop Viewport: Login page UI rendering & 6 demo account autofill cards
2. Password Show/Hide toggle
3. Autofill Demo Credentials (HR Admin & Employee)
4. Multi-account concurrent sessions test (Tab 1 HR Admin, Tab 2 Employee)
5. Verify Tab 1 is NOT logged out when Tab 2 logs in
6. Tab 1 internal link navigation maintains active account
7. 1-click Account Switcher in UI
8. Selective logout (switches to remaining signed-in account)
9. Mobile Viewport (390x844): Mobile login UI, autofill & responsive layout
10. Final logout verification
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
        # Shared context represents the same browser session/cookies
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.clear_cookies()

        print("\n=== 1. DESKTOP LOGIN UI & AUTOFILL CARDS ===")
        page = context.new_page()
        page.goto(f"{BASE_URL}/login/")
        page.wait_for_selector("#f")

        record("Login page title contains 'Sign in'", "Sign in" in page.title())
        record("Page heading is 'Welcome back'", page.locator("h1").inner_text() == "Welcome back")

        demo_cards = page.locator(".demo-card")
        record("6 Demo Account Autofill cards exist", demo_cards.count() == 6, f"(Found {demo_cards.count()})")

        card_text = page.locator(".demo-grid").inner_text()
        for role in ["HR Admin", "HR Manager", "Super Admin", "Manager", "Recruiter", "Employee"]:
            record(f"Demo card for '{role}' is present", role in card_text)

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

        print("\n=== 4. MULTI-ACCOUNT CONCURRENT SESSIONS (TAB 1 & TAB 2) ===")
        # Log in as HR Admin in Tab 1
        hr_card.click()
        btn.click()
        page.wait_for_url("**/dashboard/**", timeout=8000)
        page.wait_for_selector(".topbar")
        record("Tab 1 logged in as HR Admin Hetal Shah", "Hetal Shah" in page.locator(".topbar").inner_text())

        # Open Tab 2 in the same browser session and log in as Employee
        tab2 = context.new_page()
        tab2.goto(f"{BASE_URL}/login/")
        tab2.wait_for_selector("#f")
        record("Tab 2 shows already signed in banner for HR Admin", tab2.locator(".logged-in-banner").is_visible())

        tab2.locator(".demo-card").filter(has_text="Employee").first.click()
        tab2.locator("#go").click()
        tab2.wait_for_url("**/dashboard/**", timeout=8000)
        tab2.wait_for_selector(".topbar")
        record("Tab 2 logged in as Employee Esha Patel", "Esha Patel" in tab2.locator(".topbar").inner_text())

        print("\n=== 5. VERIFY TAB 1 (HR ADMIN) IS NOT LOGGED OUT ===")
        # Bring tab1 to front and reload / navigate
        page.bring_to_front()
        page.reload()
        page.wait_for_selector(".topbar")
        topbar1_after = page.locator(".topbar").inner_text()

        record("Tab 1 (HR Admin) is STILL active and NOT logged out!", "Hetal Shah" in topbar1_after or "HR Admin" in topbar1_after)
        record("Tab 1 did NOT get replaced by Employee", "Esha Patel" not in topbar1_after)

        # Navigate within Tab 1 to Attendance
        page.locator(".sidebar .nav a[data-nav='/attendance/']").click()
        page.wait_for_url("**/attendance/**", timeout=8000)
        record("Tab 1 can navigate internal links as HR Admin", "/attendance/" in page.url)

        # Check Tab 2 is ALSO still Employee
        tab2.bring_to_front()
        tab2.reload()
        tab2.wait_for_selector(".topbar")
        topbar2_after = tab2.locator(".topbar").inner_text()
        record("Tab 2 (Employee) is ALSO simultaneously active!", "Esha Patel" in topbar2_after)

        print("\n=== 6. ACCOUNT SWITCHER UI TEST ===")
        # Open profile dropdown in tab2
        tab2.locator("#profile-trigger").click()
        tab2.wait_for_selector("#user-popover.open")

        popover_text = tab2.locator("#user-popover").inner_text()
        record("User popover lists both HR Admin and Employee", "Hetal Shah" in popover_text and "Esha Patel" in popover_text)

        # 1-Click switch to HR Admin in tab2
        hr_switch_link = tab2.locator("#user-popover a").filter(has_text="HR Admin").first
        hr_switch_link.click()
        tab2.wait_for_url("**/dashboard/**", timeout=8000)
        tab2.wait_for_selector(".topbar")
        record("1-Click switched Tab 2 to HR Admin without password prompt", "Hetal Shah" in tab2.locator(".topbar").inner_text())

        print("\n=== 7. SELECTIVE LOGOUT TEST ===")
        # Log out of HR Admin only (Employee should remain active)
        tab2.locator("#profile-trigger").click()
        tab2.wait_for_selector("#user-popover.open")
        tab2.locator("#user-popover a").filter(has_text="Log out (HR Admin)").first.click()
        tab2.wait_for_url("**/dashboard/**", timeout=8000)

        # Verify Tab 2 automatically switches to remaining active account (Employee)
        tab2.wait_for_selector(".topbar")
        record("Selective logout switches to remaining Employee account", "Esha Patel" in tab2.locator(".topbar").inner_text())

        # Now log out of Employee (all accounts logged out)
        tab2.locator("#profile-trigger").click()
        tab2.wait_for_selector("#user-popover.open")
        tab2.locator("#user-popover a").filter(has_text="Log out (Employee)").first.click()
        tab2.wait_for_url("**/login/**", timeout=8000)
        record("Final logout cleanly redirects to /login/", "/login/" in tab2.url)

        print("\n=== 8. MOBILE VIEWPORT TEST (390x844 - iPhone) ===")
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        mobile_page = mobile_context.new_page()
        mobile_page.goto(f"{BASE_URL}/login/")
        mobile_page.wait_for_selector("#f")

        # Check mobile responsiveness
        card_box = mobile_page.locator(".auth .card").bounding_box()
        record("Login card fits inside mobile viewport (<= 390px)", card_box["width"] <= 390, f"(Width: {card_box['width']}px)")

        # Verify demo accounts on mobile
        mobile_demo_cards = mobile_page.locator(".demo-card")
        record("All 6 demo cards render on mobile", mobile_demo_cards.count() == 6)

        # Test mobile autofill & submit
        mobile_page.locator(".demo-card").filter(has_text="Recruiter").first.click()
        mobile_page.locator("#go").click()
        mobile_page.wait_for_url("**/dashboard/**", timeout=8000)
        record("Mobile login redirects to /dashboard/", "/dashboard/" in mobile_page.url)

        # Verify mobile bottom nav exists
        mobile_bottom_nav = mobile_page.locator(".bottom-nav")
        record("Mobile bottom navigation is visible", mobile_bottom_nav.is_visible())

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
