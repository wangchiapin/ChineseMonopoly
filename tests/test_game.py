# 華語大富翁測試：不改遊戲本體，完全用畫面操作（擲骰子用 window.__nextDice 指定點數）
# 涵蓋：設定畫面每個選項、擲骰／走格／說對／說錯、獎金、起點獎金、三種結束方式、老師工具、設定每個值、75 張圖、手機版面
import sys, json
from playwright.sync_api import sync_playwright
import common
from common import *

R = Runner()
ZH = {'v': 1, 'script': 'trad', 'lang': 'zh', 'phon': 'pinyin', 'rate': 'normal'}

def page(p, settings=ZH, width=1280, height=800, route_fn=None):
    if route_fn: common.route = route_fn
    return open_page(p, settings=settings, width=width, height=height, wait=500)

def state(pg):
    return pg.evaluate("(()=>{const G=window.__mono.G;return {phase:G.phase,cur:G.cur,n:G.n,c:G.c,r:G.r,players:G.players.map(p=>({name:p.name,pos:p.pos,coins:p.coins,laps:p.laps}))}})()")

def roll(pg, d):
    pg.evaluate("window.__nextDice=%d" % d)
    pg.click('[data-act=roll]')
    pg.wait_for_function("['answer','goLanded'].includes(window.__mono.G.phase)", timeout=8000)

def start(pg): pg.click('[data-act=start]'); pg.wait_for_selector('#board')

def set_tools(pg, i, **kw):
    pg.click('[data-act=tools]')
    for f, v in kw.items():
        pg.fill('[data-tp="%d"][data-f="%s"]' % (i, f), str(v))
    pg.click('[data-act=closeTools]')

def reward(pg, v):
    pg.wait_for_selector('[data-act=reward]')
    pg.click('[data-act=reward][data-v="%d"]' % v)

def finish_turn_correct(pg, v=0):
    pg.click('[data-act=correct]'); reward(pg, v)

def saved_default(pg):
    d = json.loads(pg.evaluate("localStorage.getItem('hanziGames.settings')"))
    return {k: d[k] for k in ('script', 'lang', 'phon', 'rate')}

def wait_ready(pg): pg.wait_for_function("window.__mono.G.phase==='ready'||window.__mono.G.phase==='over'", timeout=8000)

with sync_playwright() as p:
    # ===== A. 設定畫面 =====
    print('A. 設定畫面')
    b, pg, errs = page(p)
    R.check(pg.locator('[data-pn]').count() == 2, '預設 2 位玩家')
    R.check(pg.locator('.chip.on[data-k=n]').inner_text() == '24', '預設 24 格')
    for _ in range(4): pg.click('[data-act=addp]')
    R.check(pg.locator('[data-pn]').count() == 6 and pg.locator('[data-act=addp]').count() == 0, '最多 6 位，新增鈕消失')
    for _ in range(5): pg.click('[data-act=delp]')
    R.check(pg.locator('[data-pn]').count() == 1 and pg.locator('[data-act=delp]').count() == 0, '最少 1 位，刪除鈕消失')
    pg.click('[data-act=addp]'); pg.click('[data-act=addp]')
    pg.fill('[data-pn="0"]', 'Ana'); pg.fill('[data-pn="1"]', 'Luis')
    for v in (12, 16, 20, 24, 32, 40):
        pg.click('.chip[data-k=n][data-v="%d"]' % v)
        R.check(pg.input_value('[data-cfg=n]') == str(v), '格子數按鈕 %d → 輸入框跟著變' % v)
    pg.click('.chip[data-k=n][data-v="12"]')
    pg.click('[data-act=start]'); pg.wait_for_selector('#board')
    s = state(pg)
    R.check(s['n'] == 12 and pg.locator('.tile').count() == 12, '12 格棋盤有 12 個格子')
    R.check([x['name'] for x in s['players']] == ['Ana', 'Luis', '玩家 3'], '玩家名字（空白用預設名）')
    pg.click('[data-act=endAsk]'); pg.click('[data-act=endYes]'); pg.click('[data-act=backSetup]')
    R.check(pg.input_value('[data-pn="0"]') == 'Ana', '回設定畫面後名字還在（已存檔）')
    for typed, want in (('14', 14), ('15', 16), ('8', 12), ('50', 40)):
        pg.fill('[data-cfg=n]', typed)
        pg.click('[data-act=start]', timeout=3000); pg.wait_for_selector('#board', timeout=3000)   # 輸入後直接按開始，一次就要成功
        s = state(pg); n = pg.locator('.tile').count()
        R.check(s['n'] == want and n == want, '自訂格子數 %s → %d 格' % (typed, want))
        pos = pg.evaluate("[...document.querySelectorAll('.tile')].map(t=>t.style.gridRow+'/'+t.style.gridColumn)")
        R.check(len(set(pos)) == want, '  %d 格的位置沒有重疊' % want)
        pg.click('[data-act=endAsk]'); pg.click('[data-act=endYes]'); pg.click('[data-act=backSetup]')
    pg.click('.chip[data-k=n][data-v="24"]')
    # 結束方式
    pg.click('.chip[data-k=endMode][data-v=coins]')
    R.check(pg.locator('[data-cfg=coinsTarget]').count() == 1 and pg.locator('[data-cfg=laps]').count() == 0, '結束方式：金幣數 → 只出現金幣輸入')
    pg.click('.chip[data-k=endMode][data-v=manual]')
    R.check(pg.locator('[data-cfg=coinsTarget]').count() == 0 and pg.locator('[data-cfg=laps]').count() == 0, '結束方式：老師按結束 → 沒有輸入')
    pg.click('.chip[data-k=endMode][data-v=laps]')
    R.check(pg.locator('[data-cfg=laps]').count() == 1, '結束方式：繞圈數 → 出現圈數輸入')
    # 起點獎金開關
    R.check(pg.locator('[data-cfg=goAmount]').count() == 1, '起點獎金預設開啟，有金額輸入')
    pg.uncheck('[data-cfg=goOn]')
    R.check(pg.locator('[data-cfg=goAmount]').count() == 0, '關掉起點獎金 → 金額輸入消失')
    pg.check('[data-cfg=goOn]')
    R.check(pg.locator('[data-cfg=goAmount]').count() == 1, '再打開 → 金額輸入回來')
    # 字庫來源
    R.check(pg.locator('input[type=checkbox][disabled]').count() == 2, '字庫來源兩個勾選框（總字庫尚未建立、不能選）')
    errs_a = list(errs); b.close()
    R.check(not errs_a, 'A 沒有 pageerror %s' % errs_a)

    # ===== B. 擲骰、走格、說對、說錯 =====
    print('B. 回合流程')
    b, pg, errs = page(p)
    pg.fill('[data-pn="0"]', 'Ana'); pg.fill('[data-pn="1"]', 'Luis')
    pg.fill('[data-cfg=startMoney]', '100')
    pg.fill('[data-preset="0"]', '5'); pg.fill('[data-preset="1"]', '30'); pg.fill('[data-preset="2"]', '80')
    start(pg)
    s = state(pg)
    R.check(s['phase'] == 'ready' and s['cur'] == 0 and all(x['coins'] == 100 for x in s['players']), '開局：輪到第 1 位，每人 100 金幣')
    R.check(pg.locator('.tile.go').count() == 1 and pg.locator('.tile').count() == 24, '棋盤 24 格，1 個出發格')
    R.check(pg.locator('.tile[data-i="0"] .pawns svg').count() == 2, '兩個棋子都在出發格')
    # 1~6 點
    for d in range(1, 7):
        pg.evaluate("window.__nextDice=%d" % d)
        pg.click('[data-act=roll]'); pg.wait_for_function("['answer','goLanded'].includes(window.__mono.G.phase)", timeout=8000)
        s = state(pg); me = s['players'][s['cur']]
        R.check(me['pos'] == d, '擲到 %d → 走到第 %d 格' % (d, d))
        R.check(pg.locator('#dice i.on').count() == {1:1,2:2,3:3,4:4,5:5,6:6}[d], '  骰子畫面有 %d 個點' % d)
        R.check(pg.locator('.tile.cur').count() == 1 and pg.get_attribute('.tile.cur', 'data-i') == str(d), '  目前格子有黃框')
        pg.click('[data-act=wrong]'); wait_ready(pg)
        s = state(pg)
        R.check(s['players'][(s['cur'] - 1) % 2]['pos'] == 0, '  說錯 → 退回出發格')
        pg.click('[data-act=skip]')  # 換回 Ana 繼續
    s = state(pg)
    R.check(s['cur'] == 0 and all(x['coins'] == 100 for x in s['players']), '說錯不扣不加金幣；跳過後輪回第 1 位')
    # 看答案
    roll(pg, 2)
    R.check(pg.locator('.deed .ans').count() == 0 and pg.locator('[data-act=reveal]').count() == 1, '還沒看答案：不顯示中文')
    pg.click('[data-act=reveal]')
    R.check(pg.locator('.deed .hz').count() == 1 and pg.locator('.deed .ph').count() == 1, '看答案：顯示中文＋拼音')
    word = pg.inner_text('.deed .hz')
    sp = pg.evaluate("window.__spoken.slice(-1)[0]")
    R.check(sp and sp['text'] == word and sp['lang'] == 'zh-TW', '看答案會念出中文（繁體、zh-TW）：%s' % word)
    pg.click('[data-act=speakIt]')
    R.check(pg.evaluate("window.__spoken.length") == 2, '「念一次」再念一次')
    # 說對→獎金按鈕用自訂快捷鍵
    pg.click('[data-act=correct]')
    R.check([pg.get_attribute('[data-act=reward] >> nth=%d' % i, 'data-v') for i in range(4)] == ['5', '30', '80', '0'], '獎金按鈕 = 設定的快捷鍵 5／30／80 ＋ 不發')
    reward(pg, 30)
    s = state(pg)
    R.check(s['players'][0]['coins'] == 130 and s['players'][0]['pos'] == 2, '說對 +30 → 130 金幣，留在新格子')
    R.check(s['cur'] == 1, '換第 2 位')
    roll(pg, 4); pg.click('[data-act=correct]')
    pg.fill('#customReward', '45'); pg.click('[data-act=rewardCustom]')
    s = state(pg)
    R.check(s['players'][1]['coins'] == 145, '自訂獎金 45 → 145 金幣')
    roll(pg, 1); pg.click('[data-act=correct]'); reward(pg, 0)
    s = state(pg)
    R.check(s['players'][0]['coins'] == 130 and s['players'][0]['pos'] == 3, '不發獎金：金幣不變，仍然前進')
    roll(pg, 1); pg.click('[data-act=correct]'); reward(pg, 5)
    s = state(pg)
    R.check(s['players'][1]['coins'] == 150, '快捷鍵 +5')
    R.check(pg.locator('.srow').count() == 2 and '150' in pg.inner_text('.srow >> nth=1'), '計分板顯示金幣')
    b.close(); R.check(not errs, 'B 沒有 pageerror %s' % errs)

    # ===== C. 起點獎金、繞圈 =====
    print('C. 起點獎金')
    b, pg, errs = page(p)
    pg.fill('[data-cfg=goAmount]', '50'); pg.fill('[data-cfg=laps]', '5')
    start(pg)
    set_tools(pg, 0, pos=22)       # 24 格：22 + 3 → 經過起點，落在第 1 格
    roll(pg, 3)
    R.check(state(pg)['players'][0]['pos'] == 1, '從 22 擲 3 → 走到第 1 格（繞過起點）')
    pg.click('[data-act=wrong]'); wait_ready(pg)
    s = state(pg)
    R.check(s['players'][0]['pos'] == 22 and s['players'][0]['laps'] == 0 and s['players'][0]['coins'] == 100, '說錯：退回 22，沒有圈數、沒有起點獎金')
    roll(pg, 3); pg.click('[data-act=correct]'); reward(pg, 10)   # 輪到第 2 位，走 3 步，不過起點
    s = state(pg); R.check(s['players'][1]['coins'] == 110 and s['players'][1]['laps'] == 0, '沒過起點：只有獎金')
    roll(pg, 3); pg.click('[data-act=correct]'); reward(pg, 10)
    s = state(pg)
    R.check(s['players'][0]['laps'] == 1 and s['players'][0]['coins'] == 160, '說對：+10 獎金 ＋ 起點獎金 50 ＝ 160，圈數 1')
    # 剛好落在出發格
    set_tools(pg, 0, pos=21); set_tools(pg, 1, pos=1)
    # 輪到第 2 位（索引 1）；先跳過到第 1 位
    pg.click('[data-act=skip]')
    roll(pg, 3)
    R.check(state(pg)['phase'] == 'goLanded' and pg.locator('.deed .gobig').count() == 1, '剛好走到出發格：不問問題，顯示「回到起點」')
    pg.click('[data-act=goNext]')
    s = state(pg)
    R.check(s['players'][0]['laps'] == 2 and s['players'][0]['coins'] == 210, '落在出發格 → 圈數 +1、起點獎金 +50')
    b.close(); R.check(not errs, 'C 沒有 pageerror %s' % errs)

    # 關閉起點獎金
    b, pg, errs = page(p)
    pg.uncheck('[data-cfg=goOn]'); start(pg)
    set_tools(pg, 0, pos=22); roll(pg, 3); pg.click('[data-act=correct]'); reward(pg, 0)
    s = state(pg); R.check(s['players'][0]['laps'] == 1 and s['players'][0]['coins'] == 100, '起點獎金關閉：有圈數，沒有獎金')
    b.close()

    # ===== D. 三種結束方式 =====
    print('D. 結束方式')
    b, pg, errs = page(p)   # 繞圈
    pg.fill('[data-cfg=laps]', '1'); start(pg)
    set_tools(pg, 0, pos=23, coins=500); roll(pg, 2)
    pg.click('[data-act=correct]'); reward(pg, 0)
    R.check(pg.locator('.winner').count() == 1 and state(pg)['phase'] == 'over', '繞滿 1 圈 → 結束，出現排名')
    R.check('玩家 1' in pg.inner_text('.winner') and pg.locator('.rank').count() == 2, '勝者是金幣最多的玩家 1，排名 2 列')
    pg.click('[data-act=again]'); pg.wait_for_selector('#board')
    s = state(pg); R.check(s['phase'] == 'ready' and all(x['pos'] == 0 and x['laps'] == 0 and x['coins'] == 100 for x in s['players']), '再玩一次：全部重來')
    pg.click('[data-act=endAsk]'); pg.click('[data-act=endYes]'); pg.click('[data-act=backSetup]')
    R.check(pg.locator('[data-pn]').count() == 2, '回設定畫面')
    # 金幣
    pg.click('.chip[data-k=endMode][data-v=coins]'); pg.fill('[data-cfg=coinsTarget]', '120'); start(pg)
    roll(pg, 2); pg.click('[data-act=correct]'); reward(pg, 10)
    R.check(state(pg)['phase'] == 'ready', '110 < 120：還沒結束')
    roll(pg, 2); pg.click('[data-act=correct]'); reward(pg, 10)
    roll(pg, 1); pg.click('[data-act=correct]'); reward(pg, 10)
    R.check(state(pg)['phase'] == 'over' and pg.locator('.winner').count() == 1, '金幣達到 120 → 結束')
    pg.click('[data-act=backSetup]')
    # 老師按結束
    pg.click('.chip[data-k=endMode][data-v=manual]'); start(pg)
    set_tools(pg, 0, laps=9, coins=9999); roll(pg, 1); pg.click('[data-act=correct]'); reward(pg, 50)
    R.check(state(pg)['phase'] == 'ready', '老師按結束模式：圈數、金幣再多也不會自動結束')
    pg.click('[data-act=endAsk]'); pg.click('[data-act=closeModal]')
    R.check(state(pg)['phase'] == 'ready' and pg.locator('.overlay').count() == 0, '結束遊戲 → 取消：繼續玩')
    pg.click('[data-act=endAsk]'); pg.click('[data-act=endYes]')
    R.check(state(pg)['phase'] == 'over' and pg.locator('.rank').count() == 2, '結束遊戲 → 是：出現排名')
    b.close(); R.check(not errs, 'D 沒有 pageerror %s' % errs)

    # ===== E. 老師工具、單人、6 人 =====
    print('E. 老師工具／人數')
    b, pg, errs = page(p)
    for _ in range(4): pg.click('[data-act=addp]')
    start(pg)
    R.check(state(pg)['phase'] == 'ready' and len(state(pg)['players']) == 6, '6 位玩家開局')
    seq = []
    for i in range(7):
        seq.append(state(pg)['cur']); pg.click('[data-act=skip]')
    R.check(seq == [0, 1, 2, 3, 4, 5, 0], '6 人輪流，第 7 次輪回第 1 位')
    set_tools(pg, 2, name='Maria', coins=777, pos=5, laps=3)
    s = state(pg)['players'][2]
    R.check(s == {'name': 'Maria', 'pos': 5, 'coins': 777, 'laps': 3}, '老師工具：改名字／金幣／所在格／圈數')
    R.check(pg.locator('.tile[data-i="5"] .pawns svg').count() == 1, '棋子跟著搬到第 5 格')
    R.check('777' in pg.inner_text('#panel') and 'Maria' in pg.inner_text('#panel'), '計分板更新')
    set_tools(pg, 2, pos=999); R.check(state(pg)['players'][2]['pos'] == 23, '所在格超過範圍 → 限制在最後一格')
    b.close()
    b, pg, errs = page(p)
    for _ in range(1): pg.click('[data-act=delp]')
    start(pg)
    R.check(len(state(pg)['players']) == 1, '單人遊戲')
    roll(pg, 2); pg.click('[data-act=correct]'); reward(pg, 0)
    R.check(state(pg)['cur'] == 0 and state(pg)['phase'] == 'ready', '單人：下一回合還是自己')
    roll(pg, 2); pg.click('[data-act=wrong]'); wait_ready(pg)
    R.check(state(pg)['players'][0]['pos'] == 2, '單人說錯：退回上一回合的位置（第 2 格）')
    b.close()

    # ===== F. 設定每個值 =====
    print('F. 設定（字體／語言／讀音／語速）')
    b, pg, errs = page(p)
    start(pg); roll(pg, 3)
    word_t = pg.evaluate("(()=>{const G=window.__mono.G;return G.tiles[G.players[G.cur].pos]})()")
    pg.click('[data-act=reveal]')
    R.check(pg.inner_text('.deed .hz') == word_t['zh'], '繁體：顯示繁體字')
    pg.click('[data-act=settings] >> nth=0')
    def setS(k, v): pg.click('[data-act=setS][data-k=%s][data-v=%s]' % (k, v)); pg.wait_for_timeout(120)
    def saved(): return json.loads(pg.evaluate("localStorage.getItem('hanziGames.settings')"))
    setS('script', 'simp'); R.check(saved()['script'] == 'simp' and pg.inner_text('.deed .hz') == word_t['zhs'], '簡體：存檔、畫面換成簡體字')
    R.check('设置' in pg.inner_text('.modal'), '  介面文字變簡體')
    setS('script', 'trad'); R.check(saved()['script'] == 'trad' and pg.inner_text('.deed .hz') == word_t['zh'], '繁體：切回來')
    for ph in ('pinyin', 'zhuyin', 'both', 'off'):
        setS('phon', ph); want = {'pinyin': 1, 'zhuyin': 1, 'both': 2, 'off': 0}[ph]
        txt = pg.inner_text('.deed .ans')
        ok = pg.locator('.deed .ph').count() == want
        if ph == 'pinyin': ok = ok and word_t['py'] in txt
        if ph == 'zhuyin': ok = ok and word_t['zy'] in txt
        if ph == 'both': ok = ok and word_t['py'] in txt and word_t['zy'] in txt
        R.check(saved()['phon'] == ph and ok, '讀音 %s：存檔、畫面正確' % ph)
    for rt, want in (('slow', 0.45), ('normal', 0.65), ('fast', 0.85)):
        setS('rate', rt); pg.click('[data-act=closeModal]'); pg.click('[data-act=speakIt]')
        got = pg.evaluate("window.__spoken.slice(-1)[0].rate")
        R.check(saved()['rate'] == rt and abs(got - want) < 1e-9, '語速 %s：存檔、念字速度 %s' % (rt, want))
        pg.click('[data-act=settings] >> nth=0')
    for lg, key in (('es', 'Ajustes'), ('en', 'Settings'), ('zh', '設定')):
        setS('lang', lg); R.check(saved()['lang'] == lg and key in pg.inner_text('.modal'), '介面語言 %s：存檔、文字變了' % lg)
    pg.click('[data-act=closeModal]')
    b.close()
    # 重新整理後設定還在（不預設設定，完全用畫面按）
    b, pg, errs = page(p, settings=None)
    R.check(saved_default(pg) == {'script': 'trad', 'lang': 'es', 'phon': 'pinyin', 'rate': 'normal'}, '第一次開：預設 繁體／Español／拼音／中速')
    pg.click('[data-act=settings]')
    for k, v in (('script', 'simp'), ('lang', 'zh'), ('phon', 'both'), ('rate', 'fast')):
        pg.click('[data-act=setS][data-k=%s][data-v=%s]' % (k, v)); pg.wait_for_timeout(100)
    pg.reload(); pg.wait_for_timeout(400)
    R.check(saved_default(pg) == {'script': 'simp', 'lang': 'zh', 'phon': 'both', 'rate': 'fast'}, '重新整理後四個設定都還在')
    R.check('开始游戏' in pg.inner_text('#app'), '重新整理後簡體中文介面生效')
    b.close(); R.check(not errs, 'F 沒有 pageerror %s' % errs)

    # ===== G. 75 張圖都載得到；缺圖時顯示文字 =====
    print('G. 圖片')
    b, pg, errs = page(p)
    bad = pg.evaluate("""async()=>{const out=[];await Promise.all(window.__mono.POOL.map(it=>new Promise(res=>{const i=new Image();i.onload=()=>res();i.onerror=()=>{out.push(it.id);res()};i.src='images/圖片'+it.id+'.webp'})));return out}""")
    R.check(len(bad) == 0 and pg.evaluate("window.__mono.POOL.length") == 75, '75 個物品、75 張圖都載得到 %s' % bad)
    bad2 = pg.evaluate("window.__mono.POOL.filter(it=>!it.zh||!it.zhs||!it.py||!it.zy).map(it=>it.id)")
    R.check(not bad2, '每個物品都有繁／簡／拼音／注音 %s' % bad2)
    b.close()
    def route_noimg(r):
        u = r.request.url
        if u.startswith('file:') and u.endswith('.webp'): return r.abort()
        return common.route0(r)
    common.route0 = common.route
    b, pg, errs = page(p, route_fn=route_noimg); start(pg)
    pg.wait_for_timeout(500)
    R.check(pg.locator('.tile .pic .fb').count() == 23 and pg.locator('.tile .pic img').count() == 0, '圖片壞掉：每格改顯示文字（沒有外文就顯示？）')
    b.close()
    common.route = common.route0

    # ===== H. 版面 =====
    print('H. 版面')
    for (w, h) in ((1280, 800), (1024, 700), (390, 800)):
        b, pg, errs = page(p, width=w, height=h); start(pg)
        ov = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        bw = pg.evaluate("document.getElementById('board').getBoundingClientRect().width")
        R.check(ov <= 1 and bw <= w, '%dx%d：沒有橫向捲動，棋盤寬 %d' % (w, h, bw))
        if w == 390:
            ti = pg.evaluate("(()=>{const t=document.querySelector('.tile[data-i=\"1\"]').getBoundingClientRect();return [t.width,t.height]})()")
            R.check(ti[0] >= 30 and ti[1] >= 30, '手機：格子夠大（%dx%d）' % (ti[0], ti[1]))
        b.close()

print('\n失敗 %d 項' % R.fails)
sys.exit(1 if R.fails else 0)
