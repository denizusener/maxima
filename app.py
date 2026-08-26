import streamlit as st
import pandas as pd
import datetime
import os

# ReportLab PDF Kütüphaneleri (Sevkiyat Modülü için - Maxima)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# --- SAYFA VE SEKME AYARLARI ---
st.set_page_config(page_title="Kurumsal Üretim & Sevkiyat Portalı", page_icon="⚙️", layout="wide")

# --- 1. TÜRKÇE ONDALIK VE VİRGÜL DÜZELTİCİ ---
def sayiya_cevir(val):
    if pd.isna(val) or val == "" or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(" ", "")
    if "." in val_str and "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    else:
        val_str = val_str.replace(",", ".")
    try:
        return float(val_str)
    except:
        return 0.0

# --- 2. KALICI DOSYA KAYIT VE YÜKLEME MOTORU (PERSISTENCE) ---
DOSYA_STOK = "veri_stoklar.json"
DOSYA_RECETE = "veri_receteler.json"
DOSYA_MAMUL = "veri_mamuller.json"
DOSYA_SEVK = "veri_sevk_log.json"
DOSYA_URETIM_ZAMAN = "veri_uretim_zaman_log.json"
DOSYA_PERSONEL = "veri_personeller.json"
DOSYA_OPERASYON = "veri_operasyonlar.json" # YENİ: Operasyon veritabanı

def stoklari_yukle():
    if os.path.exists(DOSYA_STOK):
        try:
            df = pd.read_json(DOSYA_STOK)
            if not df.empty:
                df["Stok Kod"] = df["Stok Kod"].astype(str).str.strip()
                df["Depo Miktar"] = df["Depo Miktar"].apply(sayiya_cevir)
                return df
        except:
            pass
    return pd.DataFrame([
        {"Stok Kod": "1.ATD.20.46.Ç", "Stok Adı": "ATD ÜÇ NOKTA ASKI KOMPLE", "Depo Miktar": 15.0, "Birim": "ADET"},
        {"Stok Kod": "7.1.3.1001", "Stok Adı": "LAMA 40 X 10 HAMMADDE", "Depo Miktar": 50.0, "Birim": "METRE"}
    ])

def receteleri_yukle():
    if os.path.exists(DOSYA_RECETE):
        try:
            df = pd.read_json(DOSYA_RECETE)
            if not df.empty:
                for col in ["Mamul", "Ust_Kod", "Malzeme Kodu"]:
                    df[col] = df[col].astype(str).str.strip()
                df["Miktar"] = df["Miktar"].apply(sayiya_cevir)
                return df
        except:
            pass
    return pd.DataFrame([
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "1.ATD.20.46.Ç", "Malzeme Kodu": "2.ATD.000.01.000.0", "Malzeme Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Miktar": 1.0, "Seviye": 1, "Path": "1.ATD...>2.ATD..."}
    ])

def mamulleri_yukle():
    if os.path.exists(DOSYA_MAMUL):
        try: return pd.read_json(DOSYA_MAMUL)
        except: pass
    return pd.DataFrame(columns=["Tarih", "Mamul Kod", "Mamul Adı", "Üretilen Adet", "Durum"])

def sevk_log_yukle():
    if os.path.exists(DOSYA_SEVK):
        try: return pd.read_json(DOSYA_SEVK)
        except: pass
    return pd.DataFrame(columns=["Tarih", "Evrak No", "Firma", "Araç Plaka", "Mamül Kodu", "Sevk Adedi"])

def uretim_zaman_yukle():
    if os.path.exists(DOSYA_URETIM_ZAMAN):
        try: return pd.read_json(DOSYA_URETIM_ZAMAN)
        except: pass
    # YENİ: Sütunlara "Operasyon" eklendi
    return pd.DataFrame(columns=["Tarih", "Modül", "Operasyon", "Personel", "Stok Kodu", "Başlangıç", "Bitiş", "Toplam Süre (Dk)", "Üretilen Adet", "Birim Süre (Dk/Adet)"])

def personelleri_yukle():
    if os.path.exists(DOSYA_PERSONEL):
        try: return pd.read_json(DOSYA_PERSONEL)
        except: pass
    varsayilan_personeller = []
    for i in range(1, 11): varsayilan_personeller.append({"Ad Soyad": f"Kaynak Ustası {i}", "Bölüm": "Kaynak"})
    for i in range(1, 11): varsayilan_personeller.append({"Ad Soyad": f"Montaj Ustası {i}", "Bölüm": "Montaj"})
    return pd.DataFrame(varsayilan_personeller)

# YENİ: Operasyon Yükleyici
def operasyonlari_yukle():
    if os.path.exists(DOSYA_OPERASYON):
        try: return pd.read_json(DOSYA_OPERASYON)
        except: pass
    # Varsayılan operasyonlar
    varsayilan_operasyonlar = [
        {"Operasyon Adı": "Gazaltı Kaynak", "Bölüm": "Kaynak"},
        {"Operasyon Adı": "Punta Kaynak", "Bölüm": "Kaynak"},
        {"Operasyon Adı": "Argon Kaynak", "Bölüm": "Kaynak"},
        {"Operasyon Adı": "Gövde Montajı", "Bölüm": "Montaj"},
        {"Operasyon Adı": "Rulman Çakma", "Bölüm": "Montaj"},
        {"Operasyon Adı": "Son Kontrol ve Paketleme", "Bölüm": "Montaj"}
    ]
    return pd.DataFrame(varsayilan_operasyonlar)

def veri_kaydet(df, dosya_adi):
    df.to_json(dosya_adi, orient="records", force_ascii=False)

# =========================================================
# 3. OTURUM VE HAFIZA YÖNETİMİ
# =========================================================
if "giriş_yapildi" not in st.session_state: st.session_state["giriş_yapildi"] = False
if "secilen_sirket" not in st.session_state: st.session_state["secilen_sirket"] = None
# YENİ: aktif_islem state'ine "operasyon" eklendi
if "aktif_islem" not in st.session_state: st.session_state["aktif_islem"] = {"durum": False, "baslangic": None, "personel": "", "operasyon": "", "stok_kodu": "", "modul": ""}

# --- ŞİRKET SEÇİM EKRANI ---
if st.session_state["secilen_sirket"] is None:
    st.markdown("<h1 style='text-align: center; margin-top: 20px;'>🏢 KURUMSAL OPERASYON PORTALI</h1>", unsafe_allow_html=True)
    st.write("---")
    c_m, c_i = st.columns(2)
    with c_m:
        st.info("### 🏭 MAXİMA MAKİNE\nÜretim, BOM reçete patlatma ve sevkiyat.")
        if st.button("▶ MAXİMA PORTALINA GİRİŞ YAP", type="primary", use_container_width=True):
            st.session_state["secilen_sirket"] = "MAXİMA MAKİNE"
            st.rerun()
    with c_i:
        st.success("### 🚜 İLGİ TARIM MAKİNALARI\nKaynak & Montaj zaman etüdü, operasyon yönetimi.")
        if st.button("▶ İLGİ TARIM PORTALINA GİRİŞ YAP", type="primary", use_container_width=True):
            st.session_state["secilen_sirket"] = "İLGİ TARIM"
            st.rerun()
    st.stop()

# --- GİRİŞ EKRANI ---
if not st.session_state["giriş_yapildi"]:
    sirket = st.session_state["secilen_sirket"]
    st.markdown(f"## 🔒 {sirket} - Yetkili Personel Girişi")
    kullanici = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    
    cb1, cb2 = st.columns([1, 2])
    with cb1:
        if st.button("⬅️ Şirket Değiştir", use_container_width=True):
            st.session_state["secilen_sirket"] = None
            st.rerun()
    with cb2:
        if st.button("Sisteme Giriş Yap", type="primary", use_container_width=True):
            if ((sirket == "MAXİMA MAKİNE" and kullanici == "admin" and sifre == "1234") or 
                (sirket == "İLGİ TARIM" and kullanici == "admin" and sifre == "1234")):
                st.session_state["giriş_yapildi"] = True
                st.session_state["kullanici"] = kullanici
                st.rerun()
            else:
                st.error("❌ Hatalı giriş!")
    st.stop()

# --- TABLOLARI YÜKLE ---
if "stok_df" not in st.session_state: st.session_state["stok_df"] = stoklari_yukle()
if "recete_df" not in st.session_state: st.session_state["recete_df"] = receteleri_yukle()
if "uretim_zaman_df" not in st.session_state: st.session_state["uretim_zaman_df"] = uretim_zaman_yukle()
if "personel_df" not in st.session_state: st.session_state["personel_df"] = personelleri_yukle()
if "operasyon_df" not in st.session_state: st.session_state["operasyon_df"] = operasyonlari_yukle()

# =========================================================
# YAN MENÜ DİNAMİK YAPISI
# =========================================================
st.sidebar.markdown(f"🏢 **Firma:** `{st.session_state['secilen_sirket']}`")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["giriş_yapildi"] = False
    st.session_state["secilen_sirket"] = None
    st.rerun()
st.sidebar.divider()

if st.session_state["secilen_sirket"] == "MAXİMA MAKİNE":
    menu = st.sidebar.radio("📌 Menü", ["📊 Dashboard & Simülasyon", "📦 Stoklar", "📑 Reçeteler", "🚚 Sevkiyat"])
else: # İLGİ TARIM
    menu = st.sidebar.radio("📌 Menü Seçimi", [
        "📑 Sabit Reçeteler (BOM)", 
        "⚙️ Tanımlamalar (Personel & Operasyon)",
        "⏱️ Üretim Takip (Kaynak)", 
        "⏱️ Üretim Takip (Montaj)", 
        "📋 Üretim (Zaman) Kayıtları"
    ])

# =========================================================
# İLGİ TARIM BÖLÜMLERİ
# =========================================================

# --- 1. DOSYAYI SADECE 1 KERE OKUMAK İÇİN CACHE EKLİYORUZ ---
@st.cache_data
def buyuk_recete_excel_yukle():
    try:
        # 500.000 satırlık Excel dosyanızın yolunu buraya yazın
        # Örneğin: df = pd.read_excel("ilgi_tarim_receteler.xlsx")
        
        # Şimdilik örnek veri döndürüyoruz (Siz read_excel yapacaksınız)
        df = pd.DataFrame(columns=["Ana Mamül", "Malzeme Kodu", "Malzeme Adı", "Miktar"])
        return df
    except:
        return pd.DataFrame()

# --- 2. İLGİ TARIM REÇETELER MODÜLÜ ARKA PLANI ---
elif menu in ["📑 Sabit Reçeteler (BOM)"]:
    st.title("📑 İLGİ TARIM - Sabit Üretim Reçeteleri Arşivi")
    st.write("Veritabanında **500.000+** kayıt bulunmaktadır. Sistemi yormamak için arama yapınız.")
    
    # Veriyi RAM'den (Cache) çağır
    dev_recete_df = buyuk_recete_excel_yukle()
    
    st.markdown("---")
    
    # Arama motoru yapısı
    c1, c2 = st.columns([3, 1])
    with c1:
        aranan_kelime = st.text_input("🔍 Aranacak Ana Mamül veya Malzeme Kodunu Giriniz:")
    
    with c2:
        st.write("")
        st.write("")
        hepsini_goster = st.checkbox("Yine de ilk 1000 satırı göster")

    # Arama kelimesi girildiyse filtrele ve göster
    if aranan_kelime.strip():
        # Hem Ana Mamül sütununda hem Malzeme Kodu sütununda arama yapar
        filtrelenmis_df = dev_recete_df[
            dev_recete_df["Ana Mamül"].astype(str).str.contains(aranan_kelime, case=False, na=False) |
            dev_recete_df["Malzeme Kodu"].astype(str).str.contains(aranan_kelime, case=False, na=False)
        ]
        
        st.success(f"✅ Arama sonucunda {len(filtrelenmis_df)} kayıt bulundu.")
        st.dataframe(filtrelenmis_df, use_container_width=True)
        
    elif hepsini_goster:
        st.warning("⚠️ Tarayıcı performansını korumak için sadece ilk 1000 satır gösteriliyor.")
        st.dataframe(dev_recete_df.head(1000), use_container_width=True)
        
    else:
        st.info("👆 Reçete detaylarını görmek için lütfen yukarıdaki arama kutusuna bir stok kodu yazınız.")

# --- 2. YENİ: TANIMLAMALAR (PERSONEL VE OPERASYON YÖNETİMİ) ---
elif menu == "⚙️ Tanımlamalar (Personel & Operasyon)":
    st.title("⚙️ Sistem Tanımlamaları")
    st.write("Personel listelerini ve operasyon (işlem) adımlarını buradan yönetebilirsiniz.")
    
    t_per, t_kay, t_mon = st.tabs(["👥 Personel Tanımları", "🔥 Kaynak Operasyonları", "🔧 Montaj Operasyonları"])
    
    with t_per:
        st.subheader("Mevcut Personel Listesi")
        guncel_per = st.data_editor(st.session_state["personel_df"], num_rows="dynamic", use_container_width=True, key="ed_per")
        if st.button("💾 Personel Tablosunu Kaydet"):
            st.session_state["personel_df"] = guncel_per
            veri_kaydet(guncel_per, DOSYA_PERSONEL)
            st.success("Kayıt başarılı!")
            st.rerun()
            
        st.markdown("---")
        with st.form("per_ekle_form"):
            st.write("➕ Hızlı Personel Ekle")
            y_ad = st.text_input("Personel Adı Soyadı")
            y_bolum = st.selectbox("Bölüm", ["Kaynak", "Montaj"])
            if st.form_submit_button("Ekle") and y_ad:
                yeni = pd.DataFrame([{"Ad Soyad": y_ad, "Bölüm": y_bolum}])
                st.session_state["personel_df"] = pd.concat([st.session_state["personel_df"], yeni], ignore_index=True)
                veri_kaydet(st.session_state["personel_df"], DOSYA_PERSONEL)
                st.success("Eklendi!")
                st.rerun()
                
    with t_kay:
        st.subheader("Kaynak Bölümü Operasyonları")
        df_kay_op = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Kaynak"].reset_index(drop=True)
        g_kay_op = st.data_editor(df_kay_op, num_rows="dynamic", use_container_width=True, key="ed_kay")
        if st.button("💾 Kaynak Operasyonlarını Kaydet"):
            # Önce montajı al, üstüne güncellenen kaynağı ekle
            df_diger = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Montaj"]
            st.session_state["operasyon_df"] = pd.concat([df_diger, g_kay_op], ignore_index=True)
            veri_kaydet(st.session_state["operasyon_df"], DOSYA_OPERASYON)
            st.success("Kaydedildi!")
            st.rerun()
            
    with t_mon:
        st.subheader("Montaj Bölümü Operasyonları")
        df_mon_op = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Montaj"].reset_index(drop=True)
        g_mon_op = st.data_editor(df_mon_op, num_rows="dynamic", use_container_width=True, key="ed_mon")
        if st.button("💾 Montaj Operasyonlarını Kaydet"):
            df_diger = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Kaynak"]
            st.session_state["operasyon_df"] = pd.concat([df_diger, g_mon_op], ignore_index=True)
            veri_kaydet(st.session_state["operasyon_df"], DOSYA_OPERASYON)
            st.success("Kaydedildi!")
            st.rerun()

# --- 3. ÜRETİM TAKİP (KAYNAK / MONTAJ) ---
elif menu in ["⏱️ Üretim Takip (Kaynak)", "⏱️ Üretim Takip (Montaj)"]:
    islem_tipi = "Kaynak" if "Kaynak" in menu else "Montaj"
    st.title(f"⏱️ {islem_tipi} Üretimi & Zaman Etüdü")
    st.markdown("---")
    
    # DEVAM EDEN İŞLEM YOKSA
    if not st.session_state["aktif_islem"]["durum"]:
        c1, c2, c3 = st.columns(3)
        
        ilgili_personeller = st.session_state["personel_df"][st.session_state["personel_df"]["Bölüm"] == islem_tipi]["Ad Soyad"].tolist()
        ilgili_operasyonlar = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == islem_tipi]["Operasyon Adı"].tolist()
        
        with c1: secilen_personel = st.selectbox("1. Personel Seçimi", [""] + ilgili_personeller)
        with c2: secilen_operasyon = st.selectbox("2. Operasyon Seçimi", [""] + ilgili_operasyonlar)
        with c3: secilen_stok = st.selectbox("3. Ürün / Stok Kodu", st.session_state["stok_df"]["Stok Kod"].unique())
            
        if st.button(f"▶️ SAYAÇ BAŞLAT", type="primary", use_container_width=True):
            if secilen_personel == "" or secilen_operasyon == "":
                st.error("⚠️ Lütfen işlemi başlatmadan önce Personel ve Operasyon seçimini yapınız!")
            else:
                st.session_state["aktif_islem"] = {
                    "durum": True,
                    "baslangic": datetime.datetime.now(),
                    "personel": secilen_personel,
                    "operasyon": secilen_operasyon,
                    "stok_kodu": secilen_stok,
                    "modul": islem_tipi
                }
                st.rerun()
                
    # DEVAM EDEN İŞLEM VARSA
    else:
        aktif = st.session_state["aktif_islem"]
        
        if aktif["modul"] != islem_tipi:
            st.warning(f"⚠️ Arka planda **{aktif['modul']}** modülünde çalışan bir sayacınız var.")
        else:
            st.success("🔄 Sayaç arka planda çalışıyor...")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Personel", aktif["personel"])
            k2.metric("Operasyon", aktif["operasyon"])
            k3.metric("Stok Kodu", aktif["stok_kodu"])
            k4.metric("Başlangıç Saati", aktif["baslangic"].strftime("%H:%M:%S"))
            
            st.markdown("---")
            c4, c5 = st.columns([1, 2])
            with c4: uretilen_adet = st.number_input("Üretilen / İşlenen Adet", min_value=1.0, value=1.0, step=1.0)
            with c5:
                st.write(""); st.write("")
                if st.button("⏹️ SAYAÇ BİTİR VE KAYDET", type="primary", use_container_width=True):
                    bitis = datetime.datetime.now()
                    gecen = bitis - aktif["baslangic"]
                    toplam_dk = round(gecen.total_seconds() / 60.0, 2)
                    birim_dk = round(toplam_dk / uretilen_adet, 2)
                    
                    yeni_kayit = pd.DataFrame([{
                        "Tarih": bitis.strftime("%d.%m.%Y"),
                        "Modül": aktif["modul"],
                        "Operasyon": aktif["operasyon"],
                        "Personel": aktif["personel"],
                        "Stok Kodu": aktif["stok_kodu"],
                        "Başlangıç": aktif["baslangic"].strftime("%H:%M:%S"),
                        "Bitiş": bitis.strftime("%H:%M:%S"),
                        "Toplam Süre (Dk)": toplam_dk,
                        "Üretilen Adet": uretilen_adet,
                        "Birim Süre (Dk/Adet)": birim_dk
                    }])
                    
                    st.session_state["uretim_zaman_df"] = pd.concat([st.session_state["uretim_zaman_df"], yeni_kayit], ignore_index=True)
                    veri_kaydet(st.session_state["uretim_zaman_df"], DOSYA_URETIM_ZAMAN)
                    
                    st.session_state["aktif_islem"] = {"durum": False, "baslangic": None, "personel": "", "operasyon": "", "stok_kodu": "", "modul": ""}
                    st.success("✅ Üretim tamamlandı ve arşive kaydedildi!")
                    st.rerun()
            
            if st.button("❌ İşlemi İptal Et (Kaydetme)", use_container_width=True):
                st.session_state["aktif_islem"] = {"durum": False, "baslangic": None, "personel": "", "operasyon": "", "stok_kodu": "", "modul": ""}
                st.rerun()

# --- 4. ÜRETİM KAYITLARI ARŞİVİ ---
elif menu == "📋 Üretim (Zaman) Kayıtları":
    st.title("📋 Üretim Zaman Etüdü Arşivi")
    
    t1, t2 = st.tabs(["🔥 Kaynak Geçmişi", "🔧 Montaj Geçmişi"])
    
    with t1:
        df_kay = st.session_state["uretim_zaman_df"][st.session_state["uretim_zaman_df"]["Modül"] == "Kaynak"]
        if df_kay.empty: st.info("Kayıt yok.")
        else: st.dataframe(df_kay, use_container_width=True)
            
    with t2:
        df_mon = st.session_state["uretim_zaman_df"][st.session_state["uretim_zaman_df"]["Modül"] == "Montaj"]
        if df_mon.empty: st.info("Kayıt yok.")
        else: st.dataframe(df_mon, use_container_width=True)

# (MAXİMA Modülleri kodda var olan haliyle korunmuştur, yer israfı olmaması için kısaltılmıştır)
