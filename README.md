# Single-Stock-Futures
台灣市場個股期貨即時看板 / Taiwan Stock Futures Real-time Dashboard

一個簡潔美觀的台灣個股期貨即時看板，提供主要個股期貨的即時價格、漲跌幅、成交量等資訊。

## 功能特色

- 🚀 即時更新：每5秒自動刷新資料
- 📊 豐富資訊：顯示價格、漲跌幅、開盤價、最高價、最低價、成交量
- 🎨 美觀介面：採用漸層背景和卡片式設計
- 📱 響應式設計：支援桌面和行動裝置
- 🔴🟢 視覺化漲跌：紅色表示上漲，綠色表示下跌

## 支援的個股期貨

- 2330 台積電期貨
- 2317 鴻海期貨
- 2454 聯發科期貨
- 2881 富邦金期貨
- 2882 國泰金期貨
- 2412 中華電期貨
- 2308 台達電期貨
- 2303 聯電期貨

## 安裝說明

### 系統需求

- Python 3.8 或更高版本
- pip (Python 套件管理工具)

### 安裝步驟

1. 克隆此專案：
```bash
git clone https://github.com/HeimlichLin/Single-Stock-Futures.git
cd Single-Stock-Futures
```

2. 安裝相依套件：
```bash
pip install -r requirements.txt
```

## 使用說明

1. 啟動應用程式：
```bash
python app.py
```

如需啟用開發模式（含除錯功能）：
```bash
FLASK_ENV=development python app.py
```

2. 開啟瀏覽器，前往：
```
http://localhost:5000
```

3. 即可看到即時更新的個股期貨看板

## API 端點

### 取得所有期貨資料
```
GET /api/futures
```

回傳所有個股期貨的即時資料。

### 取得特定期貨資料
```
GET /api/futures/<symbol>
```

回傳指定代碼的個股期貨詳細資料。

範例：
```bash
curl http://localhost:5000/api/futures/2330
```

## 技術架構

- **後端**：Flask (Python Web Framework)
- **前端**：HTML5, CSS3, JavaScript (Vanilla JS)
- **資料格式**：JSON
- **更新機制**：前端輪詢 (Polling)

## 注意事項

此應用程式使用模擬資料進行展示。在實際應用中，您需要：

1. 整合真實的期貨交易所 API
2. 實作適當的認證機制
3. 考慮使用 WebSocket 進行更即時的資料推送
4. 加入錯誤處理和資料驗證

## 授權

MIT License

## 貢獻

歡迎提交 Pull Request 或開 Issue 討論新功能！
