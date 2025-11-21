# Single-Stock-Futures AI Agent Instructions

This document outlines the architecture, workflows, and conventions for the Single-Stock-Futures project. AI agents should use this context to generate accurate and consistent code.

## 1. Project Overview & Architecture

This is a **Python Flask** web application that provides a real-time dashboard for Taiwan Single Stock Futures (SSF). It uses **AsyncIO** and **Server-Sent Events (SSE)** to stream data from external sources (Taifex, Yahoo Finance) to the browser without requiring a database or API keys.

### Core Components
- **`app.py` (Server):** The Flask entry point. It sets up the `/stream_scrape` route which bridges Python's `asyncio` loop with Flask's synchronous generator to stream SSE data.
- **`scraper.py` (Logic):** Contains the core business logic:
  - `fetch_ssf_list()`: Retrieves the official list of futures from `openapi.taifex.com.tw`.
  - `get_target_contracts()`: Calculates the correct futures contract codes (e.g., `202512`) based on the current date and the "3rd Wednesday" expiration rule.
  - Uses `aiohttp` for high-concurrency scraping (default limit: 40).
- **`templates/index.html` (Frontend):** A single-page interface using vanilla JavaScript. It consumes the SSE stream and handles **client-side sorting** (Stock Code > Futures Type > Contract Month) to reduce server load.
- **`config.py`:** Stores constants like `MONTH_CODES` (F, G, H...) and `NAME_MAPPING`.

## 2. Critical Workflows

### Development & Running
- **Install Dependencies:** `pip install -r requirements.txt`
- **Start Server:** `python app.py` (Runs on `http://127.0.0.1:5000`)
- **Stop Server:** `Ctrl + C` in the terminal.

### Debugging
- The application prints system logs (`[系統]`) and errors (`[錯誤]`) to the console.
- If scraping fails (e.g., Yahoo blocks requests), check the console for HTTP status codes or timeout errors.

## 3. Coding Conventions & Patterns

### AsyncIO & Streaming
- **Pattern:** The project relies heavily on `asyncio` and `aiohttp`. Do not use blocking `requests` calls inside the main scraping loop.
- **SSE Bridge:** When adding new data streams, follow the `generate_stream_bridge` pattern in `app.py` to safely run an async generator within a Flask view.

### Data Handling
- **Contract Logic:** Always use `get_target_contracts()` to determine valid contract months. Do not hardcode months.
- **Stock Identification:**
  - Standard Futures: Usually just the stock code (e.g., `CDF`).
  - Mini Futures: Identified by starting with `Q` or being the second contract in the list. Logic is in `fetch_ssf_list`.

### Frontend (Vanilla JS)
- **No Frameworks:** Do not introduce React, Vue, or jQuery. Use standard DOM APIs (`document.getElementById`, `createElement`).
- **Dynamic Sorting:** The frontend receives data in random order (due to async scraping). The `insertRow` logic or `dataset` attributes in `index.html` are responsible for placing rows in the correct visual order.

## 4. External Dependencies
- **Taifex Open API:** `https://openapi.taifex.com.tw/v1/SSFLists` (Source of truth for list).
- **Yahoo Finance:** (Implicit dependency for price data) - Scraped via HTTP requests mimicking a browser.

## 5. Common Pitfalls
- **Timezones:** The system relies on the local machine's time to calculate contract months. Ensure date logic accounts for month rollovers (Dec -> Jan).
- **Rate Limiting:** `CONCURRENCY_LIMIT` in `config.py` prevents getting banned by target sites. Do not increase this arbitrarily.
