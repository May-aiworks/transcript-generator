# transcript# 音檔轉錄工具

使用 Gemini AI 進行專業逐字稿轉錄的 Streamlit 應用程式。

## 功能特色

- 🎙️ 支援 MP3 音檔上傳
- ✂️ 自動切割長音檔
- 🤖 使用 Google Gemini 2.5 Pro 以及 2.5 flash 進行轉錄
- 📝 保持講者命名一致性
- 💾 可下載 Markdown 格式逐字稿
- 📋 支援會議紀錄上傳以提高準確度

## 本地運行

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 安裝 ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
從 [ffmpeg.org](https://ffmpeg.org/download.html) 下載並安裝

### 3. 運行應用

```bash
streamlit run app.py
```

應用會在 `http://localhost:8501` 開啟

$\;$

## 部署到 Streamlit Community Cloud

### 步驟 1：準備 GitHub Repository

1. 在 GitHub 創建一個新的 repository
2. 上傳以下檔案：
   - `app.py`
   - `requirements.txt`
   - `packages.txt`（重要！用於安裝 ffmpeg）
   - `README.md`

### 步驟 2：部署

1. 前往 [share.streamlit.io](https://share.streamlit.io)
2. 登入你的 GitHub 帳號
3. 點擊 "New app"
4. 選擇你的 repository
5. 主檔案路徑填入 `app.py`
6. 點擊 "Deploy"

### 步驟 3：等待部署完成

- 首次部署需要 5-10 分鐘
- `packages.txt` 會自動安裝 ffmpeg
- 部署完成後會得到一個公開連結

## 使用方式

1. 選擇欲使用的模型
2. **輸入 API Key**：在側邊欄輸入你的 Gemini API Key
3. **上傳音檔**：上傳要轉錄的 MP3 檔案
4. **設定參數**：調整切割長度和系統指令（可選）
5. **開始轉錄**：點擊「開始轉錄」按鈕
6. **下載結果**：轉錄完成後下載 Markdown 格式的逐字稿

## 取得 Gemini API Key

1. 前往 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登入你的 Google 帳號
3. 點擊 "Get API Key"
4. 創建新的 API key 並複製

## 注意事項

### Streamlit Community Cloud 限制

- **記憶體**：約 1GB RAM
- **休眠**：12 小時無訪問會自動休眠
- **同時使用**：建議不要多人同時使用

### 優化建議

- 音檔盡量不要超過 1 小時
- 轉錄時不要關閉瀏覽器
- 如果失敗可以重試

### 成本考量

- Streamlit Cloud 部署：**免費**
- Gemini API 費用：
  - 免費額度：每天 15 次請求
  - 付費後：依使用量計費

## 故障排除

### 問題：應用顯示 "over resource limits"

**解決方案：**
1. 重新啟動應用（從管理介面）
2. 減少音檔長度
3. 減少切割片段長度

### 問題：ffmpeg not found

**解決方案：**
- 確認 `packages.txt` 檔案存在
- 重新部署應用

### 問題：轉錄失敗或中斷

**解決方案：**
1. 檢查 API Key 是否正確
2. 確認 API 額度是否用完
3. 檢查網路連線
4. 重試轉錄

## 進階設定

### 自訂系統指令

在應用中可以修改「系統指令」欄位，例如：

```
你是一個專業的逐字稿轉錄助手。

**與會人員：**
- 主持人：XXX
- 與會者：YYY, ZZZ

**轉錄要求：**
1. 辨識說話者
2. 使用格式：「姓名: 內容」
3. 保持一致性
```

### 調整切割長度

- **5 分鐘**：適合短會議，處理快
- **10 分鐘**（推薦）：平衡速度與準確度
- **15-20 分鐘**：適合長音檔，減少 API 請求次數
