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

# 🌟 GERÇEK YÜZ TANIMA MOTORUNU ENTEGRE EDİYORUZ (MOCK KALDIRILDI)
import face_recognition

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
        st.markdown('<p style="font-style: italic; line-height: 1.8;">"Bir ömür boyu sürecek masalımızın en özel gününe hoş geldiniz. Fotoğraflarınızı paylaşmak ve dijital anı devterimize katkıda bulunmak için alttaki menüyü kullanabilirsiniz."</p>', unsafe_allow_html=True)
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
                            
                            # 2. AI VERİTABANINA YAZMA (Yüz tanımlama verisiyle birlikte)
                            # Fotoğraftaki yüz kodlamalarını (encoding) hesaplıyoruz
                            temp_io = io.BytesIO(file_bytes)
                            loaded_image = face_recognition.load_image_file(temp_io)
                            face_encodings = face_recognition.face_encodings(loaded_image)
                            
                            new_record = {
                                "name": file_name,
                                "bytes": file_bytes,
                                "encodings": face_encodings, # 🌟 Gerçek yüz kodlamaları
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

    # 🔍 YAPAY ZEKA FOTOĞRAP ARAMA MOTORU (FIND ME)
    elif st.session_state.active_page == "find_me":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="card-title">🔍 Yapay Zeka ile Kendini Bul</h3>', unsafe_allow_html=True)
        
        st.markdown('<div style="margin-top: 10px; margin-bottom: 10px;">', unsafe_allow_html=True)
        camera_img = st.camera_input("Yüzünüzü Taramak İçin Poz Verin:")
        
        if camera_img:
            selfie_bytes = camera_img.read()
            drive_service = get_drive_service()
            
            if drive_service is not None:
                with st.spinner("Drive ile eşitleme yapılıyor ve albüm taranıyor... ⏳"):
                    try:
                        # 1. 🌟 DRIVE SENKRONİZASYONU (Silinenleri Veritabanından Atıyoruz)
                        results = drive_service.files().list(
                            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
                            fields="files(name)"
                        ).execute()
                        drive_files = results.get('files', [])
                        # Güncel dosya isimlerini set yapıyoruz
                        drive_file_names = {file['name'] for file in drive_files}
                        
                        # database.pkl'i güncelle (Drive'da yoksa sil)
                        synced_db = [
                            item for item in st.session_state.db 
                            if isinstance(item, dict) and item.get("name") in drive_file_names
                        ]
                        
                        # Eğer veritabanı değiştiyse kaydet
                        if len(synced_db) != len(st.session_state.db):
                            st.session_state.db = synced_db
                            save_db(st.session_state.db)
                        
                        # 2. 🌟 GERÇEK YÜZ TARAMA SÜRECİ
                        # Giriş yapılan selfienin yüz kodlamasını alıyoruz
                        selfie_io = io.BytesIO(selfie_bytes)
                        selfie_image = face_recognition.load_image_file(selfie_io)
                        selfie_encodings = face_recognition.face_encodings(selfie_image)
                        
                        if len(selfie_encodings) > 0:
                            target_encoding = selfie_encodings[0]
                            matched_photos = []
                            
                            # Veritabanındaki güncel fotoğrafları tek tek analiz ediyoruz
                            for item in st.session_state.db:
                                if not isinstance(item, dict) or "bytes" not in item:
                                    continue
                                    
                                # Eğer fotoğrafta önceden hesaplanmış yüz kodlaması yoksa şimdi hesaplayıp kaydedelim
                                if "encodings" not in item or not item["encodings"]:
                                    img_io = io.BytesIO(item["bytes"])
                                    loaded_img = face_recognition.load_image_file(img_io)
                                    item["encodings"] = face_recognition.face_encodings(loaded_img)
                                    save_db(st.session_state.db)
                                
                                # Fotoğraftaki her yüzü kullanıcının yüzüyle karşılaştırıyoruz
                                for face_enc in item["encodings"]:
                                    # 0.50 tolerans eşleşme doğruluğunu artırır (düşük sayı = daha seçici/doğru)
                                    match = face_recognition.compare_faces([face_enc], target_encoding, tolerance=0.50)
                                    if match[0]:
                                        matched_photos.append(item["bytes"])
                                        break  # Bir eşleşme yeterli
                            
                            # 3. 🌟 SONUÇLARI GÖSTERME
                            if matched_photos:
                                st.success(f"📸 Sizin olduğunuz {len(matched_photos)} anı yakalandı!")
                                for idx, photo_bytes in enumerate(matched_photos):
                                    photo_b64 = base64.b64encode(photo_bytes).decode()
                                    st.markdown(f'<img src="data:image/jpeg;base64,{photo_b64}" class="ai-found-photo">', unsafe_allow_html=True)
                                    
                                    st.download_button(
                                        label="📥 Fotoğrafı İndir",
                                        data=photo_bytes,
                                        file_name=f"mustafa_dilruba_dugun_{idx+1}.jpg",
                                        mime="image/jpeg",
                                        key=f"download_{idx}"
                                    )
                                    st.write("---")
                            else:
                                st.info("Albümde size ait bir fotoğraf bulunamadı. Başka bir açıyla poz vermeyi deneyebilirsiniz!")
                        else:
                            st.warning("⚠️ Çekilen fotoğrafta net bir yüz algılanamadı. Lütfen daha aydınlık bir ortamda tekrar deneyin.")
                            
                    except Exception as e:
                        st.error(f"Eşitleme/Tarama hatası: {e}")
            else:
                st.error("❌ Google Drive bağlantısı kurulamadı.")
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
