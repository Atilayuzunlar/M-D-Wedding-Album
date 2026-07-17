import streamlit as st
import pickle
import os
import io
import numpy as np
import datetime
import base64
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- GOOGLE DRIVE YAPILANDIRMASI ---
DRIVE_FOLDER_ID = "1uoWy7OlEV-7PH7vzoUaGr71ad-Ysq2P-" 

CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

@st.cache_resource
def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            try:
                creds = pickle.load(token)
            except Exception as e:
                st.error(f"token.pickle okuma hatası: {e}")
                return None
                
    if not creds or not creds.valid:
        from google.auth.transport.requests import Request
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                st.error(f"Anahtar yenilenirken hata oluştu: {e}")
                return None
        else:
            st.error("❌ Geçerli bir Google Drive bağlantı anahtarı (token.pickle) bulunamadı veya süresi dolmuş!")
            return None
            
    return build('drive', 'v3', credentials=creds)

# --- GEÇİCİ VERİTABANI MOTORU ---
DB_FILE = "database.pkl"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'rb') as f:
            try: return pickle.load(f)
            except: return []
    return []

def save_db(db_data):
    with open(DB_FILE, 'wb') as f: pickle.dump(db_data, f)

if "db" not in st.session_state: st.session_state.db = load_db()
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "active_page" not in st.session_state: st.session_state.active_page = "home"
if "upload_method" not in st.session_state: st.session_state.upload_method = "camera"
if "bg_index" not in st.session_state: st.session_state.bg_index = 1
if "uploader_key" not in st.session_state: st.session_state.uploader_key = str(int(time.time()))

# --- FOTOĞRAFLARIN VARLIĞINI KONTROL ETME ---
valid_images = []
for i in range(1, 10):
    img_path = f"cift_{i}.JPG"
    if os.path.exists(img_path):
        valid_images.append(img_path)

if valid_images:
    current_time = int(time.time())
    st.session_state.bg_index = (current_time // 6) % len(valid_images)
    active_bg_image = valid_images[st.session_state.bg_index]
else:
    active_bg_image = None

def get_base64_encoded_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return None

active_bg_b64 = get_base64_encoded_image(active_bg_image) if active_bg_image else None

# --- CSS YAPILANDIRMASI ---
st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"], .stApp, [data-testid="stApp"], 
    [data-testid="stMainBlockContainer"], .main, .block-container {{
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }}
    
    [data-testid="stHeader"], header, footer, [data-testid="stDecoration"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    [data-testid="stMainBlockContainer"] {{
        position: relative;
        z-index: 10;
        padding-top: 5px !important;
        padding-bottom: 140px !important;
        margin: 0px !important;
    }}
    
    html, body, div[data-testid="stVerticalBlock"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    
    div[data-testid="stForm"], .stFileUploader, [data-baseweb="file-uploader"], 
    [data-testid="element-container"], div[data-testid="stBlock"], 
    .element-container, div[data-impl="box"], .stCameraInput, div[data-testid="stCameraInput"] {{ 
        border: none !important; 
        background: transparent !important; 
        box-shadow: none !important; 
    }}
    
    .main-title {{ font-family: 'Playfair Display', serif; color: #D98880 !important; text-align: center; font-size: 2.4rem !important; font-weight: 800 !important; margin-top: 10px; text-shadow: 2px 2px 4px rgba(255,255,255,1), -2px -2px 4px rgba(255,255,255,1); }}
    .top-subtitle {{ text-align: center; color: #D98880 !important; font-size: 1.3rem !important; font-style: italic; margin-bottom: 20px; font-weight: 700; text-shadow: 2px 2px 4px rgba(255,255,255,1), -2px -2px 4px rgba(255,255,255,1); }}
    .card-title {{ color: #D98880 !important; font-weight: 800 !important; text-align: center; font-size: 1.6rem !important; margin-bottom: 20px; }}
    .couple-message {{ font-family: 'Georgia', serif; color: #D98880 !important; text-align: center; font-size: 1.25rem !important; font-style: italic; background-color: rgba(255, 255, 255, 0.98) !important; padding: 22px; border-radius: 15px; border-left: 6px solid #D98880; margin-bottom: 25px; font-weight: 600; line-height: 1.7; }}
    
    p, span, label, h1, h2, h3, h4, h5, h6, .stText, .stWidgetLabel p {{ color: #D98880 !important; font-size: 1.25rem !important; font-weight: 700 !important; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); }}
    .glass-card {{ background: rgba(255, 255, 255, 0.97) !important; border-radius: 24px; padding: 25px; margin-bottom: 25px; border: 1px solid rgba(210, 190, 190, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.04); }}
    
    [data-testid="stFileUploaderDropzone"] {{ background-color: rgba(255, 255, 255, 0.9) !important; border: 2px dashed #D98880 !important; border-radius: 16px !important; padding: 25px !important; }}
    
    div.stButton > button {{ 
        background: linear-gradient(135deg, #9B5DE5 0%, #8338EC 100%) !important; 
        border-radius: 14px !important; 
        border: none !important; 
        height: 54px !important; 
        width: 100% !important; 
        box-shadow: 0 5px 15px rgba(131, 56, 236, 0.3) !important; 
        margin-top: 10px;
    }}
    div.stButton > button p, div.stButton > button span, div.stButton > button div {{
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: 900 !important;
        text-shadow: none !important;
    }}
    
    .mobile-nav-bar {{ 
        position: fixed; bottom: 0; left: 0; width: 100%; 
        background-color: #FFFFFF !important; border-top: 1px solid #EADCE6; 
        display: flex; justify-content: space-around; align-items: center; 
        padding: 14px 0 !important; z-index: 999999 !important; 
        box-shadow: 0px -5px 25px rgba(0,0,0,0.08);
    }}
    .mobile-nav-bar div[data-testid="column"] {{ display: flex !important; justify-content: center !important; align-items: center !important; padding: 0 !important; }}
    .mobile-nav-bar div.stButton > button {{ background: transparent !important; border: none !important; box-shadow: none !important; height: auto !important; padding: 4px 0 !important; margin: 0 !important; display: block !important; text-align: center !important; }}
    .mobile-nav-bar div.stButton > button p, .mobile-nav-bar div.stButton > button span {{ color: #7D4643 !important; font-size: 1.05rem !important; font-weight: 800 !important; }}
    
    .bg-mask {{
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(255, 254, 253, 0.45) !important;
        z-index: -10;
    }}
    
    .bg-slideshow-img {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        object-fit: cover !important;
        z-index: -9999 !important;
        pointer-events: none !important;
    }}

    .ai-found-photo {{
        width: 100% !important;
        border-radius: 16px !important;
        margin-bottom: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }}
    </style>
""", unsafe_allow_html=True)

if active_bg_b64:
    st.markdown(f'<img src="data:image/jpeg;base64,{active_bg_b64}" class="bg-slideshow-img">', unsafe_allow_html=True)
    st.markdown('<div class="bg-mask"></div>', unsafe_allow_html=True)

# --- 1. ADIM: GİRİŞ EKRANI ---
if st.session_state.user_name == "":
    st.markdown('<div class="main-title">💕 Mustafa & Dilruba 💕</div>', unsafe_allow_html=True)
    st.markdown('<div class="top-subtitle">Sonsuz Mutluluğa Adım Atarken...</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="couple-message">"Hayatımızın en özel gününde yanımızda olduğunuz için çok mutluyuz..."<br><br><span style="color: #D98880; font-weight: bold;">- Dilruba & Mustafa</span></div>', unsafe_allow_html=True)
    
    name_input = st.text_input("Adınız Soyadınız:", placeholder="Örn: Atılay Yılmaz")
    
    if st.button("Albüme Katıl ✨", key="login_btn"):
        if name_input.strip() != "":
            st.session_state.user_name = name_input.strip()
            st.rerun()
        else:
            st.error("Lütfen devam etmek için adınızı ve soyadınızı yazın.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 2. ADIM: İÇERİK AKIŞI ---
else:
    st.markdown('<div class="main-title">💕 Mustafa & Dilruba 💕</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="top-subtitle">Hoş Geldin, {st.session_state.user_name}!</div>', unsafe_allow_html=True)

    # 🏠 ANA SAYFA (HOME)
    if st.session_state.active_page == "home":
        st.markdown('<div class="glass-card" style="text-align: center;">', unsafe_allow_html=True)
        st.markdown('<h3 class="card-title">Bizim Hikayemiz</h3>', unsafe_allow_html=True)
        st.markdown('<p style="font-style: italic; line-height: 1.8;">"Bir ömür boyu sürecek masalımızın en özel gününe hoş geldiniz. Fotoğraflarınızı paylaşmak ve dijital anı defterimize katkıda bulunmak için alttaki menüyü kullanabilirsiniz."</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 📸 FOTOĞRAF YÜKLEME SAYFASI (UPLOAD)
    elif st.session_state.active_page == "upload":
        st.markdown("### 📸 Mustafa & Dilruba İçin Bir Anı Bırakın")
        
        uploaded_file = st.camera_input("Fotoğrafınızı Çekin", key=f"cam_{st.session_state.uploader_key}")
        
        gallery_files = st.file_uploader(
            "Veya Galeriden Fotoğraflar Seçin (Çoklu Seçebilirsiniz)", 
            type=["jpg", "jpeg", "png"], 
            accept_multiple_files=True,
            key=f"gallery_{st.session_state.uploader_key}"
        )
        
        files_to_upload = []
        if uploaded_file is not None:
            files_to_upload.append(uploaded_file)
        if gallery_files:
            files_to_upload.extend(gallery_files)
        
        if len(files_to_upload) > 0:
            drive_service = get_drive_service()
            
            if drive_service is not None:
                with st.spinner(f"{len(files_to_upload)} Fotoğraf düğün albümüne yükleniyor... ⏳"):
                    try:
                        from googleapiclient.http import MediaIoBaseUpload
                        import io
                        
                        success_count = 0
                        
                        for idx, active_file in enumerate(files_to_upload):
                            file_bytes = active_file.read()
                            unique_id = int(time.time() * 1000) + idx
                            file_name = f"dugun_{unique_id}.jpg"
                            
                            # 1. GOOGLE DRIVE'A YÜKLEME
                            file_metadata = {
                                'name': file_name,
                                'parents': [DRIVE_FOLDER_ID]
                            }
                            
                            file_stream = io.BytesIO(file_bytes)
                            media = MediaIoBaseUpload(file_stream, mimetype='image/jpeg', resumable=True)
                            
                            uploaded_drive_file = drive_service.files().create(
                                body=file_metadata,
                                media_body=media,
                                fields='id'
                            ).execute()
                            
                            new_record = {
                                "name": file_name,
                                "bytes": file_bytes,
                                "uploaded_by": st.session_state.user_name,
                                "timestamp": datetime.datetime.now()
                            }
                            st.session_state.db.append(new_record)
                            success_count += 1
                        
                        save_db(st.session_state.db)
                        st.session_state.uploader_key = str(int(time.time() * 1000))
                        
                        st.markdown(f"""
                            <div style="background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 20px; text-align: center; border: 2px solid #D98880; box-shadow: 0 10px 25px rgba(217, 136, 128, 0.2); margin-top: 15px;">
                                <span style="font-size: 3rem;">🎉</span>
                                <h4 style="color: #D98880 !important; font-weight: 800; margin-top: 10px;">Harika! {success_count} Fotoğraf Yüklendi</h4>
                                <p style="font-size: 1.1rem !important; color: #7D4643 !important; font-weight: 600;">Anılarınız başarıyla Mustafa & Dilruba albümüne eklendi. Çok teşekkür ederiz!</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.balloons()
                        
                        time.sleep(1.5)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"⚠️ Yükleme sırasında bir hata oluştu: {e}")
            else:
                st.error("❌ Google Drive bağlantısı şu an kurulamıyor! Lütfen 'token.pickle' dosyasını kontrol edin.")

    # 🔍 YAPAY ZEKA FOTOĞRAP ARAMA MOTORU (BROWSER-SIDE CLIENT AI SÜRÜMÜ - GÜVENLİ CDN)
    elif st.session_state.active_page == "find_me":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="card-title">🔍 Yapay Zeka ile Kendini Bul</h3>', unsafe_allow_html=True)
        
        st.markdown('<div style="margin-top: 10px; margin-bottom: 10px;">', unsafe_allow_html=True)
        camera_img = st.camera_input("Yüzünüzü Taramak İçin Poz Verin:")
        
        if camera_img:
            selfie_bytes = camera_img.read()
            drive_service = get_drive_service()
            
            if drive_service is not None:
                with st.spinner("Drive ile eşitleme yapılıyor... ⏳"):
                    try:
                        results = drive_service.files().list(
                            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
                            fields="files(name)"
                        ).execute()
                        drive_files = results.get('files', [])
                        drive_file_names = {file['name'] for file in drive_files}
                        
                        synced_db = [
                            item for item in st.session_state.db 
                            if isinstance(item, dict) and item.get("name") in drive_file_names
                        ]
                        
                        if len(synced_db) != len(st.session_state.db):
                            st.session_state.db = synced_db
                            save_db(st.session_state.db)
                            
                        selfie_b64 = base64.b64encode(selfie_bytes).decode()
                        db_photos_json = []
                        for idx, item in enumerate(st.session_state.db):
                            if isinstance(item, dict) and "bytes" in item:
                                b64_data = base64.b64encode(item["bytes"]).decode()
                                db_photos_json.append({
                                    "idx": idx,
                                    "b64": b64_data
                                })
                                
                    except Exception as e:
                        st.error(f"Eşitleme hatası: {e}")
                        db_photos_json = []
                
                if len(db_photos_json) > 0:
                    st.info("Yapay Zeka arama işlemi tarayıcınızda yerel olarak çalıştırılıyor... ⚡")
                    
                    import json
                    photos_serialized = json.dumps(db_photos_json)
                    
                    st.components.v1.html(f"""
                        <div id="status-message" style="color: #D98880; font-family: sans-serif; font-weight: bold; text-align: center; margin-bottom: 15px;">
                            🤖 Yapay zeka motoru hazırlanıyor, lütfen bekleyin...
                        </div>
                        <div id="results-container" style="display: flex; flex-direction: column; gap: 15px;"></div>

                        <!-- Face-API.js CDN scriptleri yükleniyor -->
                        <script src="https://cdn.jsdelivr.net/npm/@vladmandic/face-api/dist/face-api.js"></script>
                        
                        <script>
                        // 🌟 Kütüphanenin tamamen tarayıcıya inmesini ve global değişkenin oluşmasını bekleyen güvence mekanizması
                        function waitForFaceAPI(callback) {{
                            if (typeof faceapi !== "undefined" && faceapi.nets) {{
                                callback();
                            }} else {{
                                setTimeout(function() {{
                                    waitForFaceAPI(callback);
                                }}, 200); // 200 milisaniyede bir kontrol et
                            }}
                        }}

                        async function runAI() {{
                            const status = document.getElementById('status-message');
                            const resultsContainer = document.getElementById('results-container');
                            
                            try {{
                                status.innerText = "🧠 Yapay Zeka modelleri CDN'den indiriliyor (3-5 saniye)...";
                                
                                // Modelleri güvenli Vladmandic CDN üzerinden asenkron yüklüyoruz
                                const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/';
                                await faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL);
                                await faceapi.nets.faceLandmarks68Net.loadFromUri(MODEL_URL);
                                await faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
                                
                                status.innerText = "📸 Selfie analizi yapılıyor...";
                                const selfieImg = new Image();
                                selfieImg.src = "data:image/jpeg;base64,{selfie_b64}";
                                await new Promise(resolve => selfieImg.onload = resolve);
                                
                                const selfieDetection = await faceapi.detectSingleFace(selfieImg).withFaceLandmarks().withFaceDescriptor();
                                if (!selfieDetection) {{
                                    status.innerText = "⚠️ Selfie üzerinde net bir yüz bulunamadı! Lütfen daha aydınlık bir ortamda tekrar deneyin.";
                                    return;
                                }}
                                
                                const targetDescriptor = selfieDetection.descriptor;
                                const faceMatcher = new faceapi.FaceMatcher(targetDescriptor, 0.55); // Hassasiyet toleransı 0.55
                                
                                status.innerText = "🔍 Albümdeki tüm fotoğraflar taranıyor...";
                                const dbPhotos = {photos_serialized};
                                let matchCount = 0;
                                
                                for (let item of dbPhotos) {{
                                    const dbImg = new Image();
                                    dbImg.src = "data:image/jpeg;base64," + item.b64;
                                    await new Promise(resolve => dbImg.onload = resolve);
                                    
                                    const detections = await faceapi.detectAllFaces(dbImg).withFaceLandmarks().withFaceDescriptors();
                                    
                                    for (let det of detections) {{
                                        const bestMatch = faceMatcher.findBestMatch(det.descriptor);
                                        if (bestMatch.label !== 'unknown') {{
                                            matchCount++;
                                            
                                            const wrapper = document.createElement('div');
                                            wrapper.style = "background: rgba(255, 255, 255, 0.95); border-radius: 16px; padding: 15px; text-align: center; border: 1px solid rgba(217, 136, 128, 0.3); margin-bottom: 15px;";
                                            
                                            const img = document.createElement('img');
                                            img.src = dbImg.src;
                                            img.style = "width: 100%; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);";
                                            
                                            const btn = document.createElement('a');
                                            btn.href = dbImg.src;
                                            btn.download = "mustafa_dilruba_dugun_" + matchCount + ".jpg";
                                            btn.innerText = "📥 Fotoğrafı İndir";
                                            btn.style = "display: block; background: linear-gradient(135deg, #9B5DE5 0%, #8338EC 100%); color: #FFFFFF; text-decoration: none; padding: 12px; border-radius: 10px; font-weight: bold; font-family: sans-serif; cursor: pointer;";
                                            
                                            wrapper.appendChild(img);
                                            wrapper.appendChild(btn);
                                            resultsContainer.appendChild(wrapper);
                                            break;
                                        }}
                                    }}
                                }}
                                
                                if (matchCount > 0) {{
                                    status.innerText = "🎉 Sizin olduğunuz " + matchCount + " adet fotoğraf başarıyla listelendi!";
                                    status.style.color = "#4CAF50";
                                }} else {{
                                    status.innerText = "ℹ️ Albümde size ait bir fotoğraf bulunamadı. Farklı bir açıyla tekrar deneyebilirsiniz.";
                                }}
                                
                            }} catch (err) {{
                                status.innerText = "⚠️ Yapay zeka işlenirken hata oluştu: " + err.message;
                                console.error(err);
                            }}
                        }}

                        // 🌟 Kütüphanenin tam yüklendiğinden emin olup asenkron tetikliyoruz
                        waitForFaceAPI(runAI);
                        </script>
                    """, height=650)
                else:
                    st.info("Albümde henüz fotoğraf bulunamadı. Önce 'Fotoğraf At' kısmından bir şeyler yükleyin.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 📋 PROGRAM SAYFASI
    elif st.session_state.active_page == "program":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="card-title">✨ Düğün Akış Programı ✨</h3>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size: 1.3rem !important; line-height: 2.2; font-weight: 700;">
            <p><b>19:00 - 19:30 :</b> Misafirlerin Karşılanması & Kokteyl</p>
            <p style="font-weight:900;"><b>19:30 - 20:00 :</b> Gelin & Damat Girişi ve İlk Dans 💕</p>
            <p><b>20:00 - 21:30 :</b> Akşam Yemeği Müziği</p>
            <p style="font-weight:900;"><b>21:30 - 22:00 :</b> Pasta Kesimi & Takı Merasimi</p>
            <p><b>22:00 - 23:45 :</b> Eğlence, Dans & After Party 🥳</p>
            <p><b>23:45 - 00:00 :</b> Kapanış & Teşekkür Konuşması</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 📱 SABİT MOBİL NAVİGASYON BARI
    st.markdown('<div class="mobile-nav-bar">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🏠 Ana Sayfa", key="nav_home"): st.session_state.active_page = "home"; st.rerun()
    with c2:
        if st.button("📸 Fotoğraf At", key="nav_upload"): st.session_state.active_page = "upload"; st.rerun()
    with c3:
        if st.button("🔍 Beni Bul", key="nav_find"): st.session_state.active_page = "find_me"; st.rerun()
    with c4:
        if st.button("📋 Program", key="nav_prog"): st.session_state.active_page = "program"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
