import os
import subprocess
from google import genai
from google.genai.errors import ServerError
import time
import streamlit as st
import tempfile
import shutil

# 頁面設定
st.set_page_config(
    page_title="音檔轉錄工具",
    page_icon="🎙️",
    layout="wide"
)

def get_audio_duration(input_file):
    """取得音檔長度（秒）"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def split_audio_with_ffmpeg(input_file, chunk_length_minutes=10, output_dir='audio_chunks'):
    """用 ffmpeg 切割音檔"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    duration_seconds = get_audio_duration(input_file)
    duration_minutes = duration_seconds / 60
    
    st.info(f"📊 音檔總長度：{duration_minutes:.2f} 分鐘")
    
    chunk_length_seconds = chunk_length_minutes * 60
    total_chunks = int((duration_seconds + chunk_length_seconds - 1) // chunk_length_seconds)
    
    st.info(f"✂️ 將切割成 {total_chunks} 個 {chunk_length_minutes} 分鐘的片段")
    
    chunk_files = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(total_chunks):
        start_time = i * chunk_length_seconds
        output_file = os.path.join(output_dir, f"chunk_{i+1:02d}.mp3")
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-ss', str(start_time),
            '-t', str(chunk_length_seconds),
            '-acodec', 'copy',
            '-y',
            output_file
        ]
        
        status_text.text(f"正在生成片段 {i+1}/{total_chunks}...")
        subprocess.run(cmd, capture_output=True)
        
        if os.path.exists(output_file):
            chunk_files.append(output_file)
        
        progress_bar.progress((i + 1) / total_chunks)
    
    status_text.text("✅ 音檔切割完成！")
    return chunk_files

def transcribe_chunk_with_context(client, audio_file_path, chunk_number, system_instruction, model_name, previous_transcript=""):
    """轉錄單一片段"""
    with open(audio_file_path, 'rb') as f:
        audio_bytes = f.read()
    
    if previous_transcript:
        context_prompt = f"""
這是第 {chunk_number} 段音檔的轉錄任務。

**前面已轉錄的內容：**
{previous_transcript}

**重要：**
- 請延續上述逐字稿中的講者命名
- 保持一致的講者對應關係
- 這段是接續前面的對話

請轉錄這段音檔。
"""
    else:
        context_prompt = "這是第 1 段音檔。請開始轉錄，並辨識說話者。"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    {
                        'parts': [
                            {
                                'inline_data': {
                                    'mime_type': 'audio/mp3',
                                    'data': audio_bytes
                                }
                            },
                            {
                                'text': context_prompt
                            }
                        ]
                    }
                ],
                config={
                    'system_instruction': system_instruction
                }
            )
            return response.text
            
        except ServerError as e:
            if '503' in str(e) or 'overloaded' in str(e).lower():
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    st.warning(f"⚠️ 伺服器過載，{wait_time}秒後重試...（第{attempt+1}/{max_retries}次）")
                    time.sleep(wait_time)
                else:
                    st.error(f"❌ 片段 {chunk_number} 轉錄失敗")
                    return None
            else:
                raise

def main():
    st.title("🎙️ 音檔轉錄工具")
    st.markdown("### 使用 Gemini AI 進行專業逐字稿轉錄")
    
    # 側邊欄：設定區
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # API Key 輸入
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="請輸入你的 Google Gemini API Key"
        )
        
        # 模型選擇
        model_choice = st.selectbox(
            "選擇 AI 模型",
            options=["gemini-2.5-pro", "gemini-2.5-flash"],
            index=0,
            help="Pro 模型更準確但較慢，Flash 模型較快但可能稍不準確"
        )

        # 切割長度設定
        chunk_length = st.slider(
            "音檔切割長度（分鐘）",
            min_value=5,
            max_value=20,
            value=10,
            help="較長的片段可能更準確，但處理時間更長"
        )
        
        st.markdown("---")
        st.markdown("### 📋 使用說明")
        st.markdown("""
        1. 輸入你的 Gemini API Key
        2. 上傳音檔（必填）
        3. 上傳或輸入訪談紀錄（選填）
        4. 設定與會人員資訊
        5. 調整切割長度（可選）
        6. 點擊「開始轉錄」
        """)
    
    # 主要區域
    st.subheader("📤 檔案上傳")
    
    # 音檔上傳
    audio_file = st.file_uploader(
        "上傳音檔 *",
        type=['mp3', 'wav', 'm4a'],
        help="請上傳要轉錄的音檔（支援 MP3, WAV, M4A 格式）"
    )
    
    if audio_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.audio(audio_file)
        with col2:
            file_size = len(audio_file.getvalue()) / (1024 * 1024)
            st.metric("檔案大小", f"{file_size:.2f} MB")
    
    st.markdown("---")
    
    # 訪談紀錄上傳區
    st.subheader("📋 訪談紀錄（選填）")
    meeting_notes_file = st.file_uploader(
        "上傳訪談紀錄",
        type=['md', 'txt'],
        help="提供訪談背景資訊、會議議程等，可提高轉錄準確度"
    )
    
    # 如果沒有上傳訪談紀錄，提供手動輸入欄位
    if not meeting_notes_file:
        meeting_notes_manual = st.text_area(
            "或直接輸入訪談紀錄",
            placeholder="例如：會議主題、討論議程、背景資訊等...",
            height=100
        )
    else:
        meeting_notes_manual = None
        st.success(f"✅ 已上傳訪談紀錄：{meeting_notes_file.name}")
    
    st.markdown("---")
    
    # 與會人員自定區
    st.subheader("👥 與會人員設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**受訪者**")
        interviewees = st.text_area(
            "受訪者列表",
            placeholder="每行一位，格式：職稱 - 姓名\n例如：\n公關處 - 王大明\n市場部 - 林小美",
            height=150,
            help="請依照格式輸入受訪者資訊"
        )
    
    with col2:
        st.markdown("**訪談者**")
        interviewers = st.text_area(
            "訪談者列表",
            placeholder="每行一位，格式：角色 - 姓名\n例如：\n主訪 - 陳宣諭\n副訪 - 許芳慈",
            height=150,
            help="請依照格式輸入訪談者資訊"
        )
    
    # 額外的講者特徵說明
    with st.expander("🎤 講者特徵補充說明（選填）"):
        speaker_characteristics = st.text_area(
            "描述講者的聲音特徵、性別或說話習慣",
            placeholder="例如：\n- 陳宣諭：女性，聲音較扁，常說「對對對」、「OK, OK」、「了解」\n- 許芳慈：女性，聲音溫柔，語速較慢\n- xxx：男性，線上參與，音質可能較差",
            height=120
        )
    
    st.markdown("---")
    
    # 系統指令設定
    st.subheader("🎯 轉錄設定")
    
    # 根據使用者輸入動態生成系統指令
    def generate_system_instruction():
        base_instruction = "你是一個專業的逐字稿轉錄助手。請使用繁體中文進行回覆。\n\n"
        
        # 加入與會人員資訊
        if interviewees or interviewers:
            base_instruction += "**與會人員：**\n"
            if interviewees:
                base_instruction += "受訪者：\n"
                for line in interviewees.strip().split('\n'):
                    if line.strip():
                        base_instruction += f"- {line.strip()}\n"
            if interviewers:
                base_instruction += "\n訪談者：\n"
                for line in interviewers.strip().split('\n'):
                    if line.strip():
                        base_instruction += f"- {line.strip()}\n"
            base_instruction += "\n"
        
        # 加入講者特徵
        if speaker_characteristics:
            base_instruction += "**講者特徵：**\n"
            base_instruction += speaker_characteristics + "\n\n"
        
        # 基本轉錄要求
        base_instruction += """**轉錄要求：**
1. 根據聲音特徵和對話內容辨識說話者
2. 使用格式：「說話者姓名: 對話內容」
3. 不要加上時間戳記
4. 保持講者命名的一致性
"""
        return base_instruction
    
    # 顯示自動生成的系統指令
    auto_instruction = generate_system_instruction()
    
    use_custom = st.checkbox("使用自訂系統指令", value=False)
    
    if use_custom:
        system_instruction = st.text_area(
            "自訂系統指令",
            value=auto_instruction,
            height=300,
            help="可以根據需求調整轉錄指令"
        )
    else:
        system_instruction = auto_instruction
        with st.expander("📝 預覽自動生成的系統指令"):
            st.code(system_instruction, language="markdown")
    
    # 開始轉錄按鈕
    st.markdown("---")
    
    if st.button("🚀 開始轉錄", type="primary", use_container_width=True):
        # 驗證輸入
        if not api_key:
            st.error("❌ 請輸入 Gemini API Key")
            return
        
        if not audio_file:
            st.error("❌ 請上傳音檔")
            return
        
        # 創建臨時目錄
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 儲存上傳的音檔
            audio_path = os.path.join(temp_dir, audio_file.name)
            with open(audio_path, 'wb') as f:
                f.write(audio_file.getvalue())
            
            # 讀取訪談紀錄（支援檔案上傳或手動輸入）
            meeting_notes = ""
            if meeting_notes_file:
                meeting_notes = meeting_notes_file.getvalue().decode('utf-8')
            elif meeting_notes_manual:
                meeting_notes = meeting_notes_manual
            
            # 如果有訪談紀錄，加入系統指令
            if meeting_notes:
                system_instruction = f"""你是一個專業的逐字稿轉錄助手。請使用繁體中文進行回覆。

**訪談背景資訊：**
{meeting_notes}

{system_instruction}
"""
            
            # 建立客戶端
            client = genai.Client(api_key=api_key)
            
            # 切割音檔
            st.markdown("### 📝 處理進度")
            chunk_dir = os.path.join(temp_dir, 'chunks')
            chunk_files = split_audio_with_ffmpeg(audio_path, chunk_length, chunk_dir)
            
            # 準備輸出
            st.markdown("### 🎯 轉錄中...")
            output_container = st.container()
            accumulated_transcript = ""
            full_transcript = ""
            
            # 進度追蹤
            total_chunks = len(chunk_files)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 逐個轉錄
            for i, chunk_file in enumerate(chunk_files, 1):
                status_text.text(f"正在轉錄片段 {i}/{total_chunks}...")
                
                transcript = transcribe_chunk_with_context(
                    client,
                    chunk_file,
                    i,
                    system_instruction,
                    model_choice,
                    accumulated_transcript
                )
                
                if transcript:
                    # 顯示當前片段
                    with output_container:
                        st.markdown(f"#### 片段 {i}")
                        st.markdown(transcript)
                        st.markdown("---")
                    
                    # 累積完整逐字稿
                    full_transcript += f"\n\n## 片段 {i}\n\n{transcript}\n\n"
                    
                    # 更新累積的上下文（只保留最近 2 個片段）
                    accumulated_transcript += f"\n\n## 片段 {i}\n{transcript}\n"
                    if i > 2:
                        lines = accumulated_transcript.split("## 片段")
                        if len(lines) > 3:
                            accumulated_transcript = "## 片段" + "## 片段".join(lines[-2:])
                    
                    st.success(f"✅ 片段 {i} 轉錄完成")
                
                # 更新進度
                progress_bar.progress(i / total_chunks)
                
                # 避免 API 請求過快
                if i < total_chunks:
                    time.sleep(5)
            
            status_text.text("✅ 全部轉錄完成！")
            
            # 提供下載
            st.markdown("---")
            st.markdown("### 📥 下載逐字稿")
            
            # 產生完整逐字稿
            final_output = f"""# 訪談逐字稿

**轉錄時間：** {time.strftime('%Y年%m月%d日 %H:%M:%S')}

---

{full_transcript}
"""
            
            st.download_button(
                label="📄 下載完整逐字稿 (Markdown)",
                data=final_output,
                file_name=f"逐字稿_{time.strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
            # 成功訊息
            st.success("🎉 轉錄完成！請下載逐字稿。")
            
        except Exception as e:
            st.error(f"❌ 發生錯誤：{str(e)}")
        
        finally:
            # 清理臨時檔案
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()