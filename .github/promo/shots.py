import asyncio
from playwright.async_api import async_playwright
URL="https://luka2pac-cyber.github.io/freeride-sella/?promo=1"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={"width":480,"height":900},device_scale_factor=2.25)
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(6000)
        await pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'));document.querySelectorAll('iframe').forEach(f=>f.remove())")
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path="out/hero.jpg",type="jpeg",quality=92)
        shots={"chips":".hero .chips","mini":"#mini","lifts":"#lifts","charts":"#neve .charts","days":"#meteo .days",
               "ava":"#sicurezza .avabox","kit":"#sicurezza .kit","map":"#map","routes":"#routes","corsi":"#corsi .pro","neve_head":"#neve .head"}
        for k,sel in shots.items():
            el=await pg.query_selector(sel)
            if not el: print("missing",k,sel); continue
            await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(1200)
            await el.screenshot(path=f"out/{k}.png"); print("ok",k)
        for i,sel in enumerate(["#chSnow","#chSloB"]):
            el=await pg.query_selector(sel)
            box=await el.evaluate_handle("e=>e.closest('.chart')")
            await box.as_element().screenshot(path=f"out/chart{i}.png")
        await b.close()
asyncio.run(main())
