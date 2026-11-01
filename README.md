# ChineseMonopoly（華語大富翁）

課堂互動遊戲：大富翁風格的一圈棋盤，擲骰子走到格子，玩家說出圖片的中文，老師按說對／說錯並發獎金。

- 單檔 `index.html`，圖片在 `images/`（75 張，來自收納小達人，圖號對應物品 id）
- 設定共用 `hanziGames.settings`（字體、介面語言、拼音注音、語速），讀音照 GoodTeacher
- 字庫目前只有收納小達人的 75 個物品；總字庫建好後，在 `POOL` 加進去、在設定畫面加一個來源勾選框
- 測試：`python3 tests/test_game.py`（需要 playwright；擲骰用 `window.__nextDice` 指定點數）
