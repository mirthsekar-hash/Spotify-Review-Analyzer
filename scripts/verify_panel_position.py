from playwright.sync_api import sync_playwright
import time, json

with sync_playwright() as p:
    page = p.chromium.launch(headless=True).new_page(viewport={"width": 1280, "height": 720})
    page.goto("http://localhost:8501", wait_until="networkidle", timeout=60000)
    time.sleep(5)
    page.locator(".st-key-sra_research_fab button").first.click()
    time.sleep(4)
    info = page.evaluate(
        """() => {
        const marker = document.querySelector('.sra-chat-panel-marker');
        let panelBlock = null;
        if (marker) {
            let el = marker.parentElement;
            while (el) {
                if (el.getAttribute('data-testid') === 'stVerticalBlock') {
                    panelBlock = el;
                    break;
                }
                el = el.parentElement;
            }
        }
        const cs = panelBlock ? getComputedStyle(panelBlock) : null;
        const r = panelBlock ? panelBlock.getBoundingClientRect() : null;
        return {
            hasMarker: !!marker,
            panelPos: cs?.position,
            panelBottom: cs?.bottom,
            panelRight: cs?.right,
            rect: r ? { x: r.x, y: r.y, w: r.width, h: r.height } : null,
            fabPos: getComputedStyle(document.querySelector('.st-key-sra_research_fab')).position,
        };
    }"""
    )
    print(json.dumps(info, indent=2))
