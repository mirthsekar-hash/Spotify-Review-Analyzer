"""Inspect Streamlit sidebar and FAB DOM order (dev utility)."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        sidebar_info = page.evaluate(
            """() => {
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (!sidebar) return { error: 'no sidebar' };
            const content = sidebar.querySelector('[data-testid="stSidebarContent"]') || sidebar;
            const children = [...content.children].map((el, i) => ({
                i,
                tag: el.tagName,
                testid: el.getAttribute('data-testid'),
                className: (el.className || '').slice(0, 120),
                text: (el.innerText || '').slice(0, 80).replace(/\\n/g, ' | '),
            }));
            const nav = sidebar.querySelector('[data-testid="stSidebarNav"]');
            const brand = sidebar.querySelector('.sra-brand-wrap');
            return {
                childCount: children.length,
                children: children.slice(0, 15),
                hasSidebarNav: !!nav,
                navDisplay: nav ? getComputedStyle(nav).display : null,
                navText: nav ? nav.innerText.slice(0, 100) : null,
                brandIndexAmongSiblings: brand ? [...brand.parentElement?.parentElement?.children || []].findIndex(c => c.contains(brand)) : -1,
                firstChildText: children[0]?.text || '',
            };
        }"""
        )

        fab_info = page.evaluate(
            """() => {
            const btns = [...document.querySelectorAll('button')];
            const fab = btns.find(b => b.title === 'Open AI Research Assistant' || b.getAttribute('aria-label') === 'Open AI Research Assistant');
            if (!fab) {
                return { found: false, buttonTitles: btns.map(b => b.title || b.innerText.slice(0,20)).slice(0, 20) };
            }
            let el = fab;
            const chain = [];
            for (let i = 0; i < 8 && el; i++) {
                chain.push({
                    tag: el.tagName,
                    testid: el.getAttribute('data-testid'),
                    className: (el.className || '').slice(0, 150),
                    style: el.getAttribute('style'),
                    pos: getComputedStyle(el).position,
                    bottom: getComputedStyle(el).bottom,
                    right: getComputedStyle(el).right,
                });
                el = el.parentElement;
            }
            const rect = fab.getBoundingClientRect();
            return {
                found: true,
                rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                viewport: { w: window.innerWidth, h: window.innerHeight },
                chain,
            };
        }"""
        )

        # Click FAB and close panel
        fab_btn = page.locator('button[title="Open AI Research Assistant"]')
        if fab_btn.count():
            fab_btn.first.click()
            time.sleep(2)
            close_btn = page.locator('button[title="Close chat"]')
            if close_btn.count():
                close_btn.first.click()
                time.sleep(2)

        fab_after_close = page.evaluate(
            """() => {
            const btns = [...document.querySelectorAll('button')];
            const fab = btns.find(b => b.title === 'Open AI Research Assistant');
            if (!fab) return { found: false };
            const rect = fab.getBoundingClientRect();
            let p = fab.parentElement;
            return {
                found: true,
                rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                parentClass: p ? p.className : null,
                parentPos: p ? getComputedStyle(p).position : null,
                text: fab.innerText,
            };
        }"""
        )

        print("=== SIDEBAR ===")
        print(json.dumps(sidebar_info, indent=2))
        print("=== FAB (initial) ===")
        print(json.dumps(fab_info, indent=2))
        print("=== FAB (after close) ===")
        print(json.dumps(fab_after_close, indent=2))

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
