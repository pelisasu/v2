# 🪙 XAUUSD Institutional Quant Signal Engine

Sistem Bot Trading Kuantitatif Emas (XAUUSD) berakurasi dan berpresisi tinggi berbasis **18 Pilar Strategi Institusional & Smart Money Concepts (SMC)**. Dijalankan secara otomatis dan gratis menggunakan **GitHub Actions** serta mengirim sinyal eksekusi Open Position (OP) manual langsung ke **Telegram**.

---

## 🌟 18 Pilar Strategi Institusional
1. **Smart Money Concepts (SMC) & Liquidity Sweeps**: Membaca sweep Buy-Side (BSL) dan Sell-Side Liquidity (SSL) dengan konfirmasi reaksi wick rejection.
2. **Multi-Timeframe Institutional Order Flow + MSB**: Analisis makro H4/D1 diturunkan ke konfirmasi Change of Character (ChoCh) & Market Structure Break (MSB) pada M30/M15.
3. **Quantitative Mean Reversion + Volume Profile (POC)**: Perhitungan Point of Control (POC), Value Area High (VAH), dan Value Area Low (VAL 70%).
4. **Hybrid AI Sentiment Analysis**: Integrasi model bahasa AI (Gemini 3.8 Flash / FinBERT) untuk analisis sentimen macro Risk-On vs Risk-Off.
5. **Deep Reinforcement Learning (DRL PPO/SAC)**: Optimasi matriks reward adaptif terhadap Sharpe Ratio dan drawdown dinamis.
6. **Machine Learning Ensemble (Gradient Boosting)**: Klasifikasi probabilitas multi-faktor pergerakan harga.
7. **Pure Price Action FVG & Order Block**: Penandaan Fair Value Gap dan mitigasi Order Block institusional dengan RRR minimal 1:3+.
8. **Statistical Arbitrage & DXY Inverse Correlation**: Filter pelindung berdasarkan korelasi negatif Gold vs US Dollar Index (DXY).
9. **Volatility Breakout (Bollinger Squeeze + ATR)**: Mendeteksi kompresi volatilitas sebelum ledakan impulsif.
10. **Order Flow & Tick Imbalance**: Deteksi agresivitas buyer vs seller pada microstructure tick volume.
11. **Multi-Timeframe Momentum Divergence**: Konfirmasi divergensi RSI dan MACD pada timeframe H1 dan M30.
12. **Session Liquidity & Killzones**: Filter ketat jam aktif volatilitas tinggi (London Open 07:00-10:00 UTC, NY Open 13:00-16:00 UTC).
13. **Hidden Markov Models (HMM) Regime Detection**: Klasifikasi fase pasar secara probabilistik (Trending vs Sideways Range vs Volatility Shock).
14. **Genetic Algorithms (GA) Auto-Tuning**: Parameter indikator adaptif berdasarkan backtest rolling period.
15. **Cross-Asset Momentum Sentinel**: Pemantauan US 10-Year Yields & DXY.
16. **LLM / FinBERT News Scraper Guardian**: Filter keamanan berita berdampak tinggi (NFP, CPI, FOMC).
17. **Hidden Order Flow & Iceberg Footprint**: Tape reading anomali volume tinggi pada spread candle tipis (akumulasi tersembunyi).
18. **Dynamic Risk Management & Anti-Martingale Matrix**: Penentuan lot terukur per persentase modal akun (1-2%), hard stop loss, serta target bertingkat TP1, TP2, TP3.

---

## 🚀 Panduan Setup 5 Menit ke GitHub Actions

### 1. Buat Bot Telegram & Ambil Token
1. Cari **@BotFather** di Telegram.
2. Kirim: `/newbot`
3. Beri nama bot (contoh: `GoldQuantBot`) dan username (contoh: `gold_institutional_quant_bot`).
4. Salin **Bot Token** (contoh: `7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2. Dapatkan Chat ID Telegram Anda
1. Cari **@userinfobot** di Telegram, lalu klik **Start**.
2. Salin **Id** Anda (contoh: `987654321`).
3. Kirim sembarang pesan (contoh: "halo") ke bot baru Anda agar bot memiliki izin mengirim sinyal ke Anda.

### 3. Masukkan Secrets ke GitHub Repository
1. Di repository GitHub Anda, buka **Settings** > **Secrets and variables** > **Actions**.
2. Klik **New repository secret**:
   - `TELEGRAM_BOT_TOKEN`: *Token bot Anda*
   - `TELEGRAM_CHAT_ID`: *Chat ID Anda*
   - `GEMINI_API_KEY`: *(Opsional) API Key Google Gemini*

### 4. Aktifkan & Uji Workflow
1. Buka tab **Actions** di GitHub.
2. Aktifkan workflow jika diminta.
3. Klik **XAUUSD Quant Institutional Signal Engine** > **Run workflow** untuk pengujian langsung!
