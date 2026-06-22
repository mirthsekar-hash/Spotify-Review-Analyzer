"""Verify sidebar brand order and FAB positioning."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        time.sleep(5)

        sidebar = page.evaluate(
            """() => {
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            const nav = sidebar?.querySelector('[data-testid="stSidebarNav"]');
            const user = sidebar?.querySelector('[data-testid="stSidebarUserContent"]');
            const brand = sidebar?.querySelector('.sra-brand-wrap');
            const firstUserText = user?.innerText?.split('\\n').filter(Boolean)[0] || '';
            return {
                navDisplay: nav ? getComputedStyle(nav).display : null,
                brandInUserContent: !!brand,
                firstUserText,
                brandTitle: brand?.querySelector('.sra-brand-title')?.innerText || null,
            };
        }"""
        )

        fab_initial = page.evaluate(
            """() => {
            const fab = document.querySelector('.st-key-sra_research_fab');
            if (!fab) return { found: false };
            const cs = getComputedStyle(fab);
            const rect = fab.getBoundingClientRect();
            const styles = [...document.querySelectorAll('style')].map(s => s.textContent || '');
            const hasFabCss = styles.some(t => t.includes('st-key-sra_research_fab'));
            return {
                found: true,
                position: cs.position,
                bottom: cs.bottom,
                right: cs.right,
                rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                viewport: { w: window.innerWidth, h: window.innerHeight },
                hasFabCss,
            };
        }"""
        )

        # Open panel
        page.locator(".st-key-sra_research_fab button").first.click()
        time.sleep(2)
        panel_open = page.evaluate(
            """() => {
            const panel = document.querySelector('.st-key-sra_chat_panel');
            if (!panel) return { found: false };
            const cs = getComputedStyle(panel);
            return { found: true, position: cs.position, bottom: cs.bottom, right: cs.right };
        }"""
        )

        # Close panel
        page.locator('button', has_text="✕").first.click()
        time.sleep(2)
        fab_after = page.evaluate(
            """() => {
            const fab = document.querySelector('.st-key-sra_research_fab');
            if (!fab) return { found: false };
            const cs = getComputedStyle(fab);
            const rect = fab.getBoundingClientRect();
            return {
                found: true,
                position: cs.position,
                rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                viewport: { w: window.innerWidth, h: window.innerHeight },
            };
        }"""
        )

        results = {
            "sidebar": sidebar,
            "fab_initial": fab_initial,
            "panel_open": panel_open,
            "fab_after_close": fab_after,
        }
        print(json.dumps(results, indent=2))

        ok = (
            sidebar.get("navDisplay") in (None, "none")
            and sidebar.get("brandTitle") == "Spotify Review Analyzer"
            and fab_initial.get("found")
            and fab_initial.get("position") == "fixed"
            and fab_after.get("position") == "fixed"
            and fab_after.get("rect", {}).get("x", 0) > 1000
        )
        print("PASS" if ok else "FAIL")
        browser.close()
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
