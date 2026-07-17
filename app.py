import streamlit as st
import pickle
import os
import io
import numpy as np
import datetime
import base64
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from PIL import Image

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

# --- 🌟 ORTAK BULUT VERİTABANI MOTORU (GOOGLE DRIVE INTEGRATED) ---
DB_FILE_NAME = "database.pkl"

def get_db_file_id(drive_service):
    """Google Drive'da database.pkl dosyasının ID'sini bulur, yoksa oluşturur."""
    try:
        results = drive_service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and name = '{DB_FILE_NAME}' and trashed = false",
            fields="files(id)"
        ).execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        return None
    except:
        return None

def download_global_db(drive_service):
    """Google Drive'dan database.pkl dosyasını çeker ve yükler."""
    file_id = get_db_file_id(drive_service)
    if not file_id:
        return [] # Henüz dosya oluşturulmamışsa boş liste dön
    
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_io.seek(0)
        return pickle.load(file_io)
    except Exception as e:
        # Bozuk piksel veya okuma hatası durumunda boş veri dön
        return []

def upload_global_db(drive_service, db_data):
    """database.pkl verilerini Google Drive'a yükler veya günceller."""
    try:
        file_io = io.BytesIO()
        pickle.dump(db_data, file_io)
        file_io.seek(0)
        
        file_id = get_db_file_id(drive_service)
        
        media = MediaIoBaseUpload(file_io, mimetype='application/octet-stream', resumable=True)
        
        if file_id:
            # Varsa güncelle
            drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Yoksa sıfırdan oluştur
            file_metadata = {
                'name': DB_FILE_NAME,
                'parents': [DRIVE_FOLDER_ID]
            }
            drive_service.files().create(
                body=file_metadata,
                media_body=media
            ).execute()
    except Exception as e:
        st.error(f"Global veritabanı senkronize edilemedi: {e}")

# --- SEANS YAPILANDIRMASI ---
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

# --- SAF PYTHON BİYOMETRİK YÜZ VE IŞIK KARTOGRAFİSİ ---
def extract_pure_biyometric_vector(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img_resized = img.resize((64, 64))
        img_np = np.array(img_resized, dtype=np.float32)
        
        # 1. Cilt Rengi Segmentasyonu
        r = img_np[:, :, 0]
        g = img_np[:, :, 1]
        b = img_np[:, :, 2]
        
        skin_mask = (r > 95) & (g > 40) & (b > 20) & ((r - g) > 15) & (r > g) & (r > b)
        skin_vector = np.where(skin_mask, 1.0, 0.0).flatten()
        
        # 2. Aydınlık / Gölge Haritası
        gray_img = img_resized.convert('L')
        gray_np = np.array(gray_img, dtype=np.float32) / 255.0
        shadow_vector = gray_np.flatten()
        
        biyometric_identity = np.concatenate([skin_vector, shadow_vector])
        return biyometric_identity
    except:
        return None

def compare_biyometric_vectors(vector1, vector2):
    if vector1 is None or vector2 is None:
        return 1.0
    
    dot_product = np.dot(vector1, vector2)
    norm_a = np.linalg.norm(vector1)
    norm_b = np.linalg.norm(vector2)
    
    if norm_a == 0 or norm_b == 0:
        return 1.0
        
    similarity = dot_product / (norm_a * norm_b)
    return 1.0 - similarity

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
                        
                        # 🌟 Google Drive'daki ortak global veritabanını canlı olarak indiriyoruz
                        global_db = download_global_db(drive_service)
                        
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
                            
                            # Biyometrik vektörleri anında hesaplayıp kaydediyoruz
                            biyometric_identity = extract_pure_biyometric_vector(file_bytes)
                            identity_list = biyometric_identity.tolist() if biyometric_identity is not None else None
                            
                            # 2. GLOBAL VERİTABANINA ekliyoruz (Görsel byte'larını Drive'da yer kaplamaması için buraya gömmüyoruz, sadece ID'sini tutuyoruz!)
                            new_record = {
                                "name": file_name,
                                "drive_id": uploaded_drive_file.get('id'),
                                "biyometric_identity": identity_list,
                                "uploaded_by": st.session_state.user_name,
                                "timestamp": datetime.datetime.now()
                            }
                            global_db.append(new_record)
                            success_count += 1
                        
                        # 🌟 Ortak güncel veritabanını Google Drive'a geri yüklüyoruz
                        upload_global_db(drive_service, global_db)
                        
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

    # 🔍 YAPAY ZEKA FOTOĞRAP ARAMA MOTORU (ORTAK BULUT VERİTABANI SÜRÜMÜ)
    elif st.session_state.active_page == "find_me":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="card-title">🔍 Yapay Zeka ile Kendini Bul</h3>', unsafe_allow_html=True)
        
        st.markdown('<div style="margin-top: 10px; margin-bottom: 10px;">', unsafe_allow_html=True)
        camera_img = st.camera_input("Yüzünüzü Taramak İçin Poz Verin:", key="biyometric_selfie_camera")
        
        if camera_img:
            selfie_bytes = camera_img.read()
            drive_service = get_drive_service()
            
            if drive_service is not None:
                with st.spinner("Bulut veritabanı eşitleniyor ve akıllı yüz analizi yapılıyor... ⏳"):
                    try:
                        # 1. GOOGLE DRIVE'DAKI GÜNCEL RESİMLERİN ADLARINI ALALIM
                        results = drive_service.files().list(
                            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false and mimeType = 'image/jpeg'",
                            fields="files(id, name)"
                        ).execute()
                        drive_files = results.get('files', [])
                        
                        # Güncel dosya isimlerini ve drive id'lerini eşliyoruz
                        drive_file_names = {file['name'] for file in drive_files}
                        drive_id_map = {file['name']: file['id'] for file in drive_files}
                        
                        # 🌟 Canlı olarak Google Drive'daki ORTAK veritabanını (database.pkl) indiriyoruz
                        global_db = download_global_db(drive_service)
                        
                        # Canlı Silme Koruması: Drive'dan el ile silinen dosyaları global veritabanından da eliyoruz
                        synced_db = [
                            item for item in global_db 
                            if isinstance(item, dict) and item.get("name") in drive_file_names
                        ]
                        
                        # Eğer veritabanında silinen olmuşsa, güncel halini Google Drive'a geri yazıyoruz
                        if len(synced_db) != len(global_db):
                            global_db = synced_db
                            upload_global_db(drive_service, global_db)
                        
                        # 2. BİYOMETRİK ÖZNİTELİK KARŞILAŞTIRMASI (Hızlıca bellek üzerinden çalışır!)
                        selfie_identity = extract_pure_biyometric_vector(selfie_bytes)
                        
                        if selfie_identity is not None:
                            matched_records = []
                            
                            for item in global_db:
                                if not isinstance(item, dict) or "biyometric_identity" not in item:
                                    continue
                                    
                                # Eğer bu kaydın drive_id'si eksik kalmışsa canlandırma yapıyoruz
                                if "drive_id" not in item or not item["drive_id"]:
                                    item["drive_id"] = drive_id_map.get(item["name"])
                                
                                if item["biyometric_identity"] is not None:
                                    saved_ident_array = np.array(item["biyometric_identity"])
                                    distance = compare_biyometric_vectors(selfie_identity, saved_ident_array)
                                    
                                    # Cosine distance tolerans eşiği (0.28 düğün ortamı ışığı için en isabetlisidir)
                                    if distance < 0.28:
                                        matched_records.append(item)
                            
                            # 3. YALNIZCA EŞLEŞEN GÖRSELLERİ DOĞRUDAN GOOGLE DRIVE'DAN İNDİRİP GÖSTERİYORUZ
                            if matched_records:
                                st.success(f"🎉 Sizin olduğunuz {len(matched_records)} fotoğraf bulut albümünden yakalandı!")
                                
                                for idx, item in enumerate(matched_records):
                                    file_id = item.get("drive_id")
                                    
                                    # Canlı ve tekil olarak indiriyoruz (Sadece eşleşenleri indirdiğimiz için asla bağlantı kopmaz!)
                                    request = drive_service.files().get_media(fileId=file_id)
                                    file_io = io.BytesIO()
                                    downloader = MediaIoBaseDownload(file_io, request)
                                    done = False
                                    while not done:
                                        status, done = downloader.next_chunk()
                                    photo_bytes = file_io.getvalue()
                                        
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
                                st.info("Düğün albümünde size ait bir fotoğraf bulunamadı. Başka bir açıyla tekrar poz vermeyi deneyebilirsiniz!")
                        else:
                            st.warning("⚠️ Biyometrik analiz başarısız oldu. Lütfen daha aydınlık bir ortamda tekrar poz verin.")
                            
                    except Exception as e:
                        st.error(f"Eşitleme/Arama hatası: {e}")
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
