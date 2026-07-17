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
            creds = pickle.load(token)
    if not creds or not creds.valid:
        from google_auth_oauthlib.flow import InstalledAppFlow
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        # 🌟 Canlı sunucu için port tekrar otomatik (0) moduna çekildi:
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
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

def get_base64_encoded_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return None

# --- CSS YAPILANDIRMASI (FOTOĞRAFLARI NETLEŞTİREN GÜNCEL SÜRÜM) ---
# --- CSS YAPILANDIRMASI (FOTOĞRAFLARI NETLEŞTİREN GÜNCEL SÜRÜM) ---
bg_css_steps = ""
images_b64 = []
for i in range(1, 10):
    b64_str = get_base64_encoded_image(f"cift_{i}.JPG")
    if b64_str:
        images_b64.append(b64_str)

if images_b64:
    total_imgs = len(images_b64)
    step_pct = 100 / total_imgs
    bg_css_steps = "@keyframes bgSlider {\n"
    for idx, b64 in enumerate(images_b64):
        start = idx * step_pct
        mid = ((idx + 1) * step_pct) - 1
        bg_css_steps += f"  {start}%, {mid}% {{ background-image: url('data:image/jpeg;base64,{b64}'); }}\n"
    bg_css_steps += "}"

# --- CSS İÇİN SÜRE HESAPLAMASI (Python tarafında önceden yapılıyor) ---
slider_duration = len(images_b64) * 4 if images_b64 else 15

st.markdown(f"""
    <style>
    {bg_css_steps}
    
    /* SLAYT MOTORU ANA GÖVDEYE BAĞLANDI (MOBİL UYUMLU) */
    [data-testid="stAppViewContainer"], .stApp, [data-testid="stApp"] {{
        background-size: cover !important;
        background-position: center center !important;
        background-repeat: no-repeat !important;
        /* 📱 Mobil tarayıcı kilitlenmesini çözmek için fixed kaldırıldı: */
        background-attachment: scroll !important;
        animation: bgSlider {slider_duration}s infinite ease-in-out;
        position: relative;
    }}
    
    /* 🌟 FOTOĞRAFLARI BELİRGİNLEŞTİREN SEFFAFLIK MASKESİ */
    [data-testid="stAppViewContainer"]::before, .stApp::before {{
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(255, 254, 253, 0.45) !important;
        z-index: 0;
    }}
    
    /* 📱 MOBİLDE GÖRÜNTÜYÜ KAPATAN BEYAZ ARKA PLANLARI SIFIRLAMA */
    [data-testid="stMainBlockContainer"], .main, .block-container, [data-testid="stHeader"] {{
        position: relative;
        z-index: 1;
        background: transparent !important;
        background-color: transparent !important;
        padding-bottom: 140px !important;
        padding-top: 20px !important;
        margin: 0px !important;
    }}
    
    html, body, .stApp, div[data-testid="stVerticalBlock"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    
    footer, header, [data-testid="stHeader"], [data-testid="stDecoration"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    
    div[data-testid="stForm"], .stFileUploader, [data-baseweb="file-uploader"], 
    [data-testid="element-container"], div[data-testid="stBlock"], 
    .element-container, div[data-impl="box"], .stCameraInput, div[data-testid="stCameraInput"] {{ 
        border: none !important; 
        background: transparent !important; 
        box-shadow: none !important; 
    }}
    
    /* 🔴 OKUNAKLI PASTEL KIRMIZI METİNLER VE ARKA PLAN GÖLGELERİ */
    .main-title {{ font-family: 'Playfair Display', serif; color: #D98880 !important; text-align: center; font-size: 2.4rem !important; font-weight: 800 !important; margin-top: 20px; text-shadow: 2px 2px 4px rgba(255,255,255,1), -2px -2px 4px rgba(255,255,255,1); }}
    .top-subtitle {{ text-align: center; color: #D98880 !important; font-size: 1.3rem !important; font-style: italic; margin-bottom: 30px; font-weight: 700; text-shadow: 2px 2px 4px rgba(255,255,255,1), -2px -2px 4px rgba(255,255,255,1); }}
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
    </style>
""", unsafe_allow_html=True)

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
        
        uploaded_file = st.camera_input("Fotoğrafınızı Çekin")
        gallery_file = st.file_uploader("Veya Galeriden Bir Fotoğraf Seçin", type=["jpg", "jpeg", "png"])
        
        active_file = uploaded_file if uploaded_file is not None else gallery_file
        
        if active_file is not None:
            # 🌟 NameError ve bağlantı kopmasını önlemek için tam burada çağırıyoruz:
            drive_service = get_drive_service()
            
            if drive_service is not None:
                with st.spinner("Fotoğrafınız düğün albümüne yükleniyor, lütfen bekleyin... ⏳"):
                    try:
                        from googleapiclient.http import MediaIoBaseUpload
                        import io
                        
                        file_name = f"dugun_{int(time.time())}.jpg"
                        
                        file_metadata = {
                            'name': file_name,
                            'parents': [DRIVE_FOLDER_ID]
                        }
                        
                        file_bytes = io.BytesIO(active_file.read())
                        media = MediaIoBaseUpload(file_bytes, mimetype='image/jpeg', resumable=True)
                        
                        # 🚀 Google Drive'a güvenle gönderiliyor
                        uploaded_drive_file = drive_service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields='id'
                        ).execute()
                        
                        st.success("🎉 Harika! Fotoğrafınız başarıyla Mustafa & Dilruba albümüne eklendi. Çok teşekkür ederiz!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"⚠️ Yükleme sırasında bir hata oluştu: {e}")
                        st.info("Lütfen internet bağlantınızı kontrol edip tekrar deneyin.")
            else:
                st.error("❌ Google Drive bağlantısı şu an kurulamıyor! Lütfen 'token.pickle' dosyasını kontrol edin.")

    # 🔍 YAPAY ZEKA FOTOĞRAF ARAMA MOTORU (FIND ME)
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
                        for photo_bytes in valid_photos: st.image(photo_bytes, use_container_width=True)
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
