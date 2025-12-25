# =========================================================
# FB COMMENT TOOL - FULL ORIGINAL CODE + SAFE FIX
# =========================================================

import streamlit as st
import time
import threading
import gc
import json
import os
import uuid
import random
from pathlib import Path
from collections import deque
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="FB Comment Tool",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= KEEP ALIVE =================
KEEP_ALIVE_JS = """
<script>
setInterval(function(){
    fetch(window.location.href,{method:'HEAD'}).catch(()=>{});
},25000);

setInterval(function(){
    document.dispatchEvent(
        new MouseEvent('mousemove',{
            bubbles:true,
            clientX:Math.random()*300,
            clientY:Math.random()*300
        })
    );
},60000);
</script>
"""

# ================= CSS =================
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
*{font-family:'Poppins',sans-serif;}

.stApp{
background-image:url('https://i.postimg.cc/TYhXd0gG/d0a72a8cea5ae4978b21e04a74f0b0ee.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
}

.main .block-container{
background:rgba(255,255,255,0.08);
backdrop-filter:blur(8px);
border-radius:12px;
padding:20px;
border:1px solid rgba(255,255,255,0.12);
}

.stButton>button{
background:linear-gradient(45deg,#ff6b6b,#4ecdc4);
color:white;
border:none;
border-radius:8px;
padding:.6rem 1.5rem;
font-weight:600;
width:100%;
}

label{
color:white!important;
font-size:13px!important;
font-weight:500!important;
}

.console-box{
background:rgba(0,0,0,.6);
border-radius:8px;
padding:10px;
font-family:monospace;
font-size:11px;
color:#00ff88;
max-height:200px;
overflow-y:auto;
}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)
st.markdown(KEEP_ALIVE_JS, unsafe_allow_html=True)

# ================= CONSTANTS =================
STICKER_IDS = [
'369239263222822','126361874215276','126362187548578',
'126361967548600','126362100881920','344403172622564',
'184571475493841','789355251153389'
]

LOGS_DIR = "session_logs"
SESSIONS_FILE = "sessions_registry.json"
MAX_LOGS = 30
os.makedirs(LOGS_DIR, exist_ok=True)

# ================= SESSION =================
class Session:
    __slots__ = ['id','running','count','logs','idx','driver','start_time']
    def __init__(self, sid):
        self.id = sid
        self.running = False
        self.count = 0
        self.logs = deque(maxlen=MAX_LOGS)
        self.idx = 0
        self.driver = None
        self.start_time = None

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.logs.append(line)
        try:
            with open(f"{LOGS_DIR}/{self.id}.log","a") as f:
                f.write(line+"\n")
        except:
            pass

# ================= MANAGER =================
@st.cache_resource
def get_session_manager():
    return SessionManager()

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self):
        sid = uuid.uuid4().hex[:8].upper()
        s = Session(sid)
        self.sessions[sid] = s
        return s

    def get_active(self):
        return [s for s in self.sessions.values() if s.running]

manager = get_session_manager()

# ================= BROWSER =================
def setup_browser():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")

    chrome_bin = None
    for p in ["/usr/bin/chromium","/usr/bin/chromium-browser","/usr/bin/google-chrome"]:
        if Path(p).exists():
            chrome_bin = p
            break
    if chrome_bin:
        opts.binary_location = chrome_bin

    return webdriver.Chrome(options=opts)

# ================= FIND COMMENT BOX =================
def find_comment_input(driver):
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[aria-label*="comment" i][contenteditable="true"]',
        'div[contenteditable="true"]'
    ]
    for s in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, s)
            el.click()
            return el
        except:
            continue
    return None

# ================= MAIN WORKER =================
def run_session(session, post_url, cookies, comments, delay, images, only_sticker):

    driver = setup_browser()
    session.driver = driver
    session.running = True
    session.start_time = time.strftime("%H:%M:%S")

    driver.get("https://www.facebook.com/")
    time.sleep(8)

    # -------- cookies --------
    for c in cookies.split(";"):
        if "=" in c:
            k,v = c.strip().split("=",1)
            try:
                driver.add_cookie({
                    "name":k,"value":v,
                    "domain":".facebook.com","path":"/"
                })
            except:
                pass

    driver.get(post_url)
    time.sleep(15)

    img_idx = 0
    txt_idx = 0

    while session.running:

        comment_input = find_comment_input(driver)
        if not comment_input:
            session.log("❌ Comment box not found")
            break

        # ========== ONLY STICKER ==========
        if only_sticker:
            sid = random.choice(STICKER_IDS)
            session.log(f"Sticker: {sid}")
            driver.execute_script("""
                const b=document.querySelector('div[aria-label*="sticker" i]');
                if(b)b.click();
            """)
            time.sleep(2)

        else:
            # ========== IMAGE ==========
            media_attached = False
            if images:
                img = images[img_idx % len(images)]
                img_idx += 1
                session.log("Uploading image")

                driver.execute_script("""
                    const b=document.querySelector('div[aria-label*="Photo"]');
                    if(b)b.click();
                """)
                time.sleep(2)

                try:
                    f = driver.find_element(By.CSS_SELECTOR,"input[type='file']")
                    f.send_keys(os.path.abspath(img))
                    time.sleep(8)
                    media_attached = True
                except:
                    session.log("❌ Image upload failed")

            # 🔥 FIX: RE-FIND COMMENT BOX AFTER IMAGE
            if media_attached:
                time.sleep(4)
                comment_input = find_comment_input(driver)
                if not comment_input:
                    continue

            # ========== TEXT ==========
            txt = comments[txt_idx % len(comments)]
            txt_idx += 1

            driver.execute_script("""
                arguments[0].focus();
                arguments[0].click();
                document.execCommand('insertText',false,arguments[1]);
                arguments[0].dispatchEvent(new Event('input',{bubbles:true}));
            """, comment_input, txt)

        # ========== SEND ==========
        driver.execute_script("""
            const b=document.querySelector(
                'div[aria-label="Comment"],div[aria-label="Post"],div[aria-label*="Post"]'
            );
            if(b)b.click();
        """)

        session.count += 1
        session.log(f"✅ Comment #{session.count}")
        time.sleep(delay)

    try:
        driver.quit()
    except:
        pass

    session.running = False
    session.log("Stopped")
    gc.collect()

# ================= STREAMLIT UI =================
st.markdown("<h1 style='text-align:center'>💬 FB Comment Tool</h1>", unsafe_allow_html=True)

post_url = st.text_input("Post URL")
cookies = st.text_area("Cookies")
delay = st.number_input("Delay (seconds)",10,3600,30)

mode = st.radio(
    "Mode",
    ["Only Text","Text + Image","Only Sticker"]
)

images = []
if mode == "Text + Image":
    imgs = st.file_uploader(
        "Upload Images",
        type=["jpg","jpeg","png"],
        accept_multiple_files=True
    )
    if imgs:
        os.makedirs("temp_uploads",exist_ok=True)
        for img in imgs:
            p = f"temp_uploads/{uuid.uuid4().hex}_{img.name}"
            with open(p,"wb") as f:
                f.write(img.getbuffer())
            images.append(p)

txt_file = st.file_uploader("Comments TXT",type=["txt"])
comments = ["Nice post"]
if txt_file:
    comments = [c for c in txt_file.read().decode().splitlines() if c.strip()]

if st.button("START"):
    if not post_url or not cookies:
        st.error("Post URL & Cookies required")
    else:
        s = manager.create_session()
        threading.Thread(
            target=run_session,
            args=(
                s,
                post_url,
                cookies,
                comments,
                delay,
                images if mode=="Text + Image" else None,
                mode=="Only Sticker"
            ),
            daemon=True
        ).start()
        st.success(f"Session Started: {s.id}")
