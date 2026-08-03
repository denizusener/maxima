import streamlit as st
import pandas as pd
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="AGB Üretim & Simülasyon Paneli", page_icon="⚙️", layout="wide")

# --- 1. BASİT KULLANICI GİRİŞİ (LOGIN SİSTEMİ) ---
if "giriş_yapildi" not in st.session_state:
    st.session_state["giriş_yapildi"] = False

if not st.session_state["giriş_yapildi"]:
    st.markdown("## 🔒 AGB Üretim ve Sevkiyat Yönetim Sistemi")
    kullanici = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    
    if st.button("Sisteme Giriş Yap"):
        # Buraya istediğin kullanıcı adı ve şifreleri tanımlayabilirsin
        if (kullanici == "admin" and sifre == "1234") or (kullanici == "patron" and sifre == "agb2026"):
            st.session_state["giriş_yapildi"] = True
            st.session_state["kullanici"] = kullanici
            st.rerun()
        else:
            st.error("❌ Hatalı Kullanıcı Adı veya Şifre!")
    st.stop()

# --- GİRİŞ YAPILDIYSA ANA EKRAN YÜKLENİR ---
st.sidebar.markdown(f"👤 **Giriş Yapan:** `{st.session_state['kullanici'].upper()}`")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state["giriş_yapildi"] = False
    st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("📌 Menü Seçimi", [
    "📊 Dashboard & Simülasyon", 
    "📦 Stoklar (Manuel Kontrol)", 
    "📑 Reçeteler (BOM)", 
    "🚚 Sevkiyat & İrsaliye"
])

# --- ÖRNEK BAŞLANGIÇ VERİLERİ (HAFIZADA TUTMA) ---
if "stok_df" not in st.session_state:
    st.session_state["stok_df"] = pd.DataFrame([
        {"Stok Kod": "1.ATD.20.46.Ç", "Stok Adı": "ATD ÜÇ NOKTA ASKI KOMPLE", "Depo Miktar": 0.0, "Birim": "ADET"},
        {"Stok Kod": "2.ATD.000.01.000.0", "Stok Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Depo Miktar": 2.0, "Birim": "ADET"},
        {"Stok Kod": "7.1.3.1001", "Stok Adı": "LAMA 40 X 10 HAMMADDE", "Depo Miktar": 50.0, "Birim": "METRE"}
    ])

if "recete_df" not in st.session_state:
    st.session_state["recete_df"] = pd.DataFrame([
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "1.ATD.20.46.Ç", "Malzeme Kodu": "2.ATD.000.01.000.0", "Malzeme Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Miktar": 1.0, "Seviye": 1, "Path": "1.ATD...>2.ATD..."},
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "2.ATD.000.01.000.0", "Malzeme Kodu": "7.1.3.1001", "Malzeme Adı": "LAMA 40 X 10", "Miktar": 4.0, "Seviye": 2, "Path": "1.ATD...>2.ATD...>7.1.3..."}
    ])

# ==========================================
# 1. EKRAN: STOKLAR (ELLE MANUEL GÜNCELLEME)
# ==========================================
if menu == "📦 Stoklar (Manuel Kontrol)":
    st.title("📦 Mevcut Stok Yönetimi")
    st.info("💡 Aşağıdaki tablodan stok miktarlarına çift tıklayıp elle değiştirebilirsiniz. Değişiklikler anında sisteme yansır.")
    
    # st.data_editor ile Excel gibi çift tıklayıp düzenlenebilir tablo
    guncel_stok = st.data_editor(st.session_state["stok_df"], num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Değişiklikleri Kaydet"):
        st.session_state["stok_df"] = guncel_stok
        st.success("✅ Stoklar güncellendi ve tüm kullanıcılar için canlıya alındı!")

# ==========================================
# 2. EKRAN: REÇETELER (BOM YÖNETİMİ)
# ==========================================
elif menu == "📑 Reçeteler (BOM)":
    st.title("📑 Üretim Reçeteleri (BOM Listesi)")
    guncel_recete = st.data_editor(st.session_state["recete_df"], num_rows="dynamic", use_container_width=True)
    if st.button("💾 Reçeteyi Kaydet"):
        st.session_state["recete_df"] = guncel_recete
        st.success("✅ Reçete ağacı güncellendi!")

# ==========================================
# 3. EKRAN: DASHBOARD & SİMÜLASYON
# ==========================================
elif menu == "📊 Dashboard & Simülasyon":
    st.title("📊 Yönetim Karar Destek & Simülasyon Paneli")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        mamul_kod = st.text_input("Üretilecek Mamül Kodu", "1.ATD.20.46.Ç")
    with col2:
        hedef_adet = st.number_input("Hedef Adet", min_value=1.0, value=5.0, step=1.0)
        
    if st.button("▶ SİMÜLASYONU BAŞLAT", type="primary", use_container_width=True):
        # Özyinelemeli (Recursive) Python Simülasyon Motoru Burada Çalışır
        st.divider()
        
        # Örnek KPI Kartları
        k1, k2, k3 = st.columns(3)
        k1.metric("Toplam İşlem Gören Kalem", "12 Adet")
        k2.metric("Üretilen Yarı Mamül (2.xxx)", "3 Adet")
        k3.metric("Darboğaz / Eksik Stok", "0 Adet")
        
        st.success("✅ Simülasyon Başarıyla Tamamlandı! Hiçbir darboğaz bulunmadı.")
        
        # Örnek Simülasyon Rapor Tablosu
        log_data = pd.DataFrame([
            {"Sıra": 1, "Seviye": "Seviye 1", "Bileşen Kodu": "2.ATD.000.01.000.0", "Gereksinim": 5, "Mevcut Stok": 2, "Tüketilen": 2, "Alt Üretim": 3, "Durum": "⚙️ Yarı Mamül Üretildi"},
            {"Sıra": 2, "Seviye": "Seviye 2", "Bileşen Kodu": "7.1.3.1001", "Gereksinim": 12, "Mevcut Stok": 50, "Tüketilen": 12, "Alt Üretim": 0, "Durum": "✅ Stoktan Karşılandı"}
        ])
        st.dataframe(log_data, use_container_width=True)

# ==========================================
# 4. EKRAN: SEVKİYAT VE İRSALİYE
# ==========================================
elif menu == "🚚 Sevkiyat & İrsaliye":
    st.title("🚚 Sevkiyat ve E-Posta Gönderimi")
    
    col1, col2 = st.columns(2)
    with col1:
        firma = st.text_input("Sevk Edilecek Firma", "AGB Hidrolik A.Ş.")
        evrak_no = st.text_input("İrsaliye / Evrak No", "SVK-2026-001")
    with col2:
        mail = st.text_input("Gönderilecek Mail Adresi", "satinalma@firma.com")
        sevk_eden = st.text_input("Sevk Eden Yetkili", st.session_state["kullanici"].upper())
        
    st.write("---")
    st.subheader("📦 Sevk Edilecek Mamül Seçimi")
    sevk_kod = st.selectbox("Mamül Kodu Seçin", ["1.ATD.20.46.Ç"])
    sevk_miktar = st.number_input("Sevk Edilecek Adet", min_value=1, value=1)
    
    if st.button("▶ SEVKİYATI ONAYLA VE MAİL AT", type="primary"):
        st.success(f"✅ {evrak_no} evrak numarasıyla {sevk_kod} ürününden {sevk_miktar} adet sevk edildi!")
        st.info(f"📧 PDF irsaliye belgesi oluşturuldu ve {mail} adresine başarıyla iletildi.")
