# -*- coding: utf-8 -*-
"""端到端验证：案例undefined / 品牌详情 / 报告自然周 / rednote入口 / 日历 / JS错误"""
import sys, base64, time, traceback
sys.stdout.reconfigure(encoding="utf-8")
from collector_automation import get_collector_automation

errors, bad_resp, result = [], [], {}
auto = get_collector_automation()


def close_modal(page):
    try:
        page.evaluate("() => { document.querySelectorAll('.modal-close-btn').forEach(b=>b.click()); if(typeof closeModal==='function') closeModal(); }")
        page.wait_for_timeout(700)
    except Exception:
        pass


try:
    print("[1] 启动 CDP Edge ...")
    auto.start_browser(account="default")
    time.sleep(6)
    from playwright.sync_api import sync_playwright
    auth = "Basic " + base64.b64encode(b"Zachary:ID082610").decode()
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
        page.on("console", lambda m: errors.append("CONSOLE.ERROR: " + m.text) if m.type == "error" else None)
        page.on("response", lambda r: bad_resp.append(f"{r.status} {r.url[:90]}") if r.status >= 400 else None)
        page.on("requestfailed", lambda r: bad_resp.append("FAIL " + r.url[:90]))
        READ_MODAL = "() => {const els=document.querySelectorAll('.modal-body-content');if(els.length)return els[els.length-1].innerText;return document.getElementById('modalContent')?.innerText||'';}"
        page.set_extra_http_headers({"Authorization": auth})
        page.set_viewport_size({"width": 1440, "height": 900})
        try:
            cdp_sess = ctx.new_cdp_session(page)
            cdp_sess.send("Network.setCacheDisabled", {"cacheDisabled": True})
        except Exception as _ce:
            print("setCacheDisabled跳过:", _ce)

        print("[2] 打开首页 ...")
        page.goto("http://127.0.0.1:8200/", wait_until="networkidle")
        page.wait_for_timeout(3000)

        print("[3] 案例库 viewCase C-01 ...")
        page.evaluate("() => navigateTo('cases')")
        page.wait_for_timeout(2500)
        page.evaluate("() => CaseLibrary.viewCase('C-01')")
        page.wait_for_timeout(2500)
        case_txt = page.evaluate(READ_MODAL)
        result["case_title_undefined"] = "undefined" in case_txt
        result["case_has_event"] = ("事件概述" in case_txt) and ("暂无概述" not in case_txt)
        result["case_head"] = case_txt.split("\n")[:7]
        close_modal(page)

        print("[4] 品牌业态 viewBrand ...")
        page.evaluate("() => navigateTo('brands')")
        page.wait_for_timeout(2500)
        page.evaluate("() => BrandIndustry.viewBrand('gaga CENTRAL')")
        page.wait_for_timeout(2500)
        brand_txt = page.evaluate(READ_MODAL)
        result["brand_has_recent"] = "相关笔记" in brand_txt
        result["brand_head"] = brand_txt.split("\n")[:11]
        close_modal(page)

        print("[5] 报告中心默认自然周 ...")
        page.evaluate("() => navigateTo('reports')")
        page.wait_for_timeout(2000)
        page.evaluate("() => ReportCenter.generateReport('weekly')")
        page.wait_for_timeout(1500)
        result["weekly_start"] = page.evaluate("() => document.getElementById('report-start')?.value")
        result["weekly_end"] = page.evaluate("() => document.getElementById('report-end')?.value")
        page.evaluate("() => {const s=document.getElementById('report-type-select');s.value='monthly';s.dispatchEvent(new Event('change'));}")
        page.wait_for_timeout(600)
        result["monthly_start"] = page.evaluate("() => document.getElementById('report-start')?.value")
        close_modal(page)

        print("[6] rednote 入口 ...")
        result["rednote_top_hidden"] = page.evaluate("() => {const b=document.getElementById('rednoteBtn');return b?getComputedStyle(b).display==='none':'no-btn'}")
        result["rednote_alt_in_settings"] = page.evaluate("() => !!document.getElementById('rednoteAltEntry')")

        print("[7] 舆情日历核对 08-28 ...")
        page.evaluate("() => navigateTo('calendar')")
        page.wait_for_timeout(3000)
        page.evaluate("() => openDayNotes('2026-08-28')")
        page.wait_for_timeout(2000)
        cal_txt = page.evaluate(READ_MODAL)
        result["calendar_0828"] = cal_txt.split("\n")[:9]
        close_modal(page)

        print("[8] 保持页面观察 30s（轮询/实时同步）...")
        page.wait_for_timeout(30000)
        page.screenshot(path="_shots/e2e_final.png", full_page=False)
        result["js_errors"] = sorted(set(errors))[:15]
        result["bad_responses"] = sorted(set(bad_resp))[:15]
        try:
            page.close()
        except Exception:
            pass

    print("==== E2E RESULT ====")
    for k, v in result.items():
        print(k, "=>", v)
    print("JS错误数:", len(set(errors)), "| 4xx/5xx数:", len(set(bad_resp)))
except Exception as e:
    print("E2E异常:", e)
    traceback.print_exc()
finally:
    try:
        auto.stop_browser()
    except Exception:
        pass
