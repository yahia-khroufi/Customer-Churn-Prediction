"""Vérification navigateur : python scripts/smoke_ui.py --url http://127.0.0.1:8000."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / "artifacts" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        # Edge est déjà installé sur Windows ; aucun téléchargement Chromium requis.
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#submit")).to_be_enabled()
        expect(page.locator("#health-status")).to_have_text("Modèle disponible")
        page.screenshot(path=str(output / "desktop-form.png"), full_page=True)
        page.get_by_role("button", name="Nouveau client", exact=True).click()
        page.locator("#submit").click()
        expect(page.locator("#result")).to_be_visible()
        expect(page.locator("#prediction-badge")).to_contain_text("Churn =")
        first_score = page.locator("#score").inner_text()
        with page.expect_download() as download:
            page.locator("#download").click()
        assert download.value.suggested_filename == "churn-prediction.json"
        page.screenshot(path=str(output / "desktop-result.png"), full_page=True)
        page.get_by_role("button", name="Client fidèle", exact=True).click()
        expect(page.locator("#stale-notice")).to_be_visible()
        expect(page.locator("#download")).to_be_disabled()
        page.locator("#submit").click()
        expect(page.locator("#stale-notice")).to_be_hidden()
        assert page.locator("#score").inner_text() != first_score

        page.locator("#InternetService").select_option("No")
        expect(page.locator("#OnlineSecurity")).to_have_value("No internet service")
        expect(page.locator("#OnlineSecurity")).to_be_disabled()
        page.locator("#PhoneService").select_option("No")
        expect(page.locator("#MultipleLines")).to_have_value("No phone service")
        page.locator("#TotalCharges").fill("")
        page.locator("#submit").click()
        expect(page.locator("#stale-notice")).to_be_hidden()
        expect(page.locator("#error-message")).to_be_hidden()

        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#reset").click()
        expect(page.locator("#empty-state")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.locator("#submit").click()
        expect(page.locator("#result")).to_be_visible()
        page.screenshot(path=str(output / "mobile-result.png"), full_page=True)

        page.route("**/predict", lambda route: route.fulfill(status=503, content_type="application/json", body='{"detail":"Modèle indisponible"}'))
        page.locator("#submit").click()
        expect(page.locator("#error-message")).to_contain_text("Modèle indisponible")
        expect(page.locator("#submit")).to_be_enabled()
        assert not errors, errors
        browser.close()
    print(f"UI_OK : desktop, mobile, prédictions, téléchargement et erreurs. Captures : {output}")


if __name__ == "__main__":
    main()
