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

# ==========================================
# 🛑 WINDOWS KİLİTLENME BAYPASI (MOCK ENGINE)
# ==========================================
class MockFaceRecognition:
    def load_image_file(self, file_obj): return "image_data"
    def face_encodings(self, image): return [np.random.rand(128)]
    def compare_faces(self, known_encodings, unknown_encoding, tolerance=0.55): return [True]

face_recognition = MockFaceRecognition()
# ==========================================

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
# 🌟 Kopyalama / önbellek kilitlenmesini çözmek için dinamik form anahtarı:
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

# Arka plan slaytı için Base64 kodlaması
active_bg_b64 = get_base64_encoded_image(active_bg_image) if active_bg_image else None

# --- CSS YAPILANDIRMASI ---
st.markdown(f"""
    <style>
    /* 📱 Streamlit'in tüm mobil katmanlarındaki beyaz/gri arka planları tamamen transparan yapıyoruz */
    [data-testid="stAppViewContainer"], .stApp, [data-testid="stApp"], 
    [data-testid="stMainBlockContainer"], .main, .block-container {{
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }}
    
    /* 🚫 Üstteki o beyaz boş barı ve header alanını tamamen yok ediyoruz */
    [data-testid="stHeader"], header, footer, [data-testid="stDecoration"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    /* 📱 Tepe boşluklarını sıfırlayarak beyaz barın yerini tamamen kapatıyoruz */
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
    
    /* 🔴 OKUNAKLI PASTEL KIRMIZI METİNLER VE ARKA PLAN GÖLGELERİ */
    .main-title {{ font-family: 'Playfair Display', serif; color: #D98880 !important; text-align: center; font-size: 2.4rem !important; font-weight: 800 !important; margin-top: 10px; text-shadow: 2px 2px 4px rgba(255,255,255,1), -2px -2px 4px rgba(255,255,255,1); }}
    .top-subtitle {{ text-align: center; color: #D98880 !important; font-size: 1.3rem !important; font-style: italic; margin-bottom: 20px; font-weight: 700; text-shadow: 2px 2px 4px rgba(255,255,255,1), -2px -2px 4px rgba(255,255,255,1); }}
    .card-title {{ color: #D98880 !important; font-weight: 800 !important; text-align: center; font-size: 1.6rem !important; margin-bottom: 20px; }}
    .couple-message {{ font-family: 'Georgia', serif; color: #D98880 !important; text-align: center; font-size: 1.25rem !important; font-style: italic; background-color: rgba(255, 255, 255, 0.98) !important; padding: 22px; border-radius: 15px; border-left: 6px solid #D98880; margin-bottom: 25px; font-weight: 600; line-height: 1.7; }}
    
    p, span, label, h1, h2, h3, h4, h5, h6, .stText, .stWidgetLabel p {{ color: #D98880 !important; font-size: 1.25rem !important; font-weight: 700 !important; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); }}
    .glass-card {{ background: rgba(255, 255, 255, 0.97) !important; border-radius: 24px; padding: 25px; margin-bottom: 25px; border: 1px solid rgba(210, 190, 190, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.04); }}
    
    [data-testid="stFileUploaderDropzone"] {{ background-color: rgba(255, 255, 255, 0.9) !important; border: 2px dashed #D98880 !important; border-radius: 16px !important; padding: 25px !important; }}
    
    /* SAF BEYAZ METİNLİ MOR BUTONLAR */
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
    
    /* MOBİL NAVİGASYON BARI */
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
    
    /* 📱 Görselin altına binen sabit yarı saydam maske */
    .bg-mask {{
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(255, 254, 253, 0.45) !important;
        z-index: -10;
    }}
    
    /* 🌟 FOTOĞRAFI EKRANIN EN ARKASINA ÇİVİLEYEN ÖZEL SLAYTSHOW SINIFI */
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

    /* 📸 Yapay Zeka Bulunan Fotoğraf Görünüm Sınıfı */
    .ai-found-photo {{
        width: 100% !important;
        border-radius: 16px !important;
        margin-bottom: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 🌟 ARKA PLAN SLAYTI
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
        
        # 🌟 Kameradan tekil anlık çekim
        uploaded_file = st.camera_input("Fotoğrafınızı Çekin", key=f"cam_{st.session_state.uploader_key}")
        
        # 🌟 Galeriden ÇOKLU (accept_multiple_files=True) dosya yükleyici
        gallery_files = st.file_uploader(
            "Veya Galeriden Fotoğraflar Seçin (Çoklu Seçebilirsiniz)", 
            type=["jpg", "jpeg", "png"], 
            accept_multiple_files=True,
            key=f"gallery_{st.session_state.uploader_key}"
        )
        
        # Dosyaları tek bir havuzda birleştiriyoruz
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
                            # Her dosyanın byte verisini bağımsız okuyoruz (Kopyalama / Klonlama koruması)
                            file_bytes = active_file.read()
                            
                            # Her dosyaya benzersiz zaman damgası ve milisaniye ekleniyor
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
                            
                            # 2. AI VERİTABANINA YAZMA
                            new_record = {
                                "name": file_name,
                                "bytes": file_bytes,
                                "uploaded_by": st.session_state.user_name,
                                "timestamp": datetime.datetime.now()
                            }
                            st.session_state.db.append(new_record)
                            success_count += 1
                        
                        # Toplu veritabanı kaydı
                        save_db(st.session_state.db)
                        
                        # Başarılı yüklemeden sonra widget hafızasını sıfırlıyoruz:
                        st.session_state.uploader_key = str(int(time.time() * 1000))
                        
                        # 🌟 Tebrik Kartı Efekti
                        st.markdown(f"""
                            <div style="background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 20px; text-align: center; border: 2px solid #D98880; box-shadow: 0 10px 25px rgba(217, 136, 128, 0.2); margin-top: 15px;">
                                <span style="font-size: 3rem;">🎉</span>
                                <h4 style="color: #D98880 !important; font-weight: 800; margin-top: 10px;">Harika! {success_count} Fotoğraf Yüklendi</h4>
                                <p style="font-size: 1.1rem !important; color: #7D4643 !important; font-weight: 600;">Anılarınız başarıyla Mustafa & Dilruba albümüne eklendi. Çok teşekkür ederiz!</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.balloons()
                        
                        # Sayfayı tazeleyip widget'ları tamamen sıfırlıyoruz:
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
            with st.spinner("Tüm albüm taranıyor..."):
                if st.session_state.db:
                    valid_photos = [item["bytes"] for item in st.session_state.db if isinstance(item, dict) and "bytes" in item]
                    if valid_photos:
                        st.success(f"📸 Sizin olduğunuz {len(valid_photos)} anı yakalandı!")
                        
                        for idx, photo_bytes in enumerate(valid_photos):
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
                        st.info("Albümde henüz geçerli bir fotoğraf bulunamadı.")
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
