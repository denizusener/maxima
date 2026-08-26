import streamlit as st
import pandas as pd
import datetime
import os
import json
import smtplib
from email.message import EmailMessage

# ReportLab PDF Kütüphaneleri
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

# --- 2. STREAMLIT CLOUD PDF HARF KORUMASI ---
def pdf_text(metin):
    if not isinstance(metin, str):
        metin = str(metin)
    degisim = {
        "Ğ": "G", "ğ": "g", "Ş": "S", "ş": "s", "İ": "I", "ı": "i",
        "Ç": "C", "ç": "c", "Ö": "O", "ö": "o", "Ü": "U", "ü": "u"
    }
    for tr, en in degisim.items():
        metin = metin.replace(tr, en)
    return metin

# =========================================================
# 3. KALICI DOSYA KAYIT VE YÜKLEME MOTORU (PERSISTENCE)
# =========================================================
DOSYA_STOK = "veri_stoklar.json"
DOSYA_RECETE = "veri_receteler.json"
DOSYA_MAMUL = "veri_mamuller.json"
DOSYA_SEVK = "veri_sevk_log.json"
DOSYA_URETIM_ZAMAN = "veri_uretim_zaman_log.json" # YENİ EKLENEN İLGİ TARIM DOSYASI

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
        {"Stok Kod": "1.AGB.100.04.000.0", "Stok Adı": "AGB DİNGİL PİSTONU KOMPLE", "Depo Miktar": 8.0, "Birim": "ADET"},
        {"Stok Kod": "2.ATD.000.01.000.0", "Stok Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Depo Miktar": 2.0, "Birim": "ADET"},
        {"Stok Kod": "7.1.3.1001", "Stok Adı": "LAMA 40 X 10 HAMMADDE", "Depo Miktar": 50.0, "Birim": "METRE"},
        {"Stok Kod": "7.1.7.1076", "Stok Adı": "BORU DİKİŞLİ Ø88,9(3'')x2", "Depo Miktar": 100.0, "Birim": "METRE"}
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
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "1.ATD.20.46.Ç", "Malzeme Kodu": "2.ATD.000.01.000.0", "Malzeme Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Miktar": 1.0, "Seviye": 1, "Path": "1.ATD...>2.ATD..."},
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "2.ATD.000.01.000.0", "Malzeme Kodu": "7.1.3.1001", "Malzeme Adı": "LAMA 40 X 10 HAMMADDE", "Miktar": 4.0, "Seviye": 2, "Path": "1.ATD...>2.ATD...>7.1.3..."},
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "2.ATD.000.01.000.0", "Malzeme Kodu": "7.1.7.1076", "Malzeme Adı": "BORU DİKİŞLİ Ø88,9(3'')x2", "Miktar": 0.164, "Seviye": 2, "Path": "1.ATD...>2.ATD...>7.1.7..."}
    ])

def mamulleri_yukle():
    if os.path.exists(DOSYA_MAMUL):
        try:
            return pd.read_json(DOSYA_MAMUL)
        except:
            pass
    return pd.DataFrame(columns=["Tarih", "Mamul Kod", "Mamul Adı", "Üretilen Adet", "Durum"])

def sevk_log_yukle():
    if os.path.exists(DOSYA_SEVK):
        try:
            return pd.read_json(DOSYA_SEVK)
        except:
            pass
    return pd.DataFrame(columns=["Tarih", "Evrak No", "Firma", "Araç Plaka", "Mamül Kodu", "Sevk Adedi"])

def uretim_zaman_yukle():
    if os.path.exists(DOSYA_URETIM_ZAMAN):
        try:
            return pd.read_json(DOSYA_URETIM_ZAMAN)
        except:
            pass
    return pd.DataFrame(columns=["Tarih", "Modül", "Personel", "Stok Kodu", "Başlangıç", "Bitiş", "Toplam Süre (Dk)", "Üretilen Adet", "Birim Süre (Dk/Adet)"])

def veri_kaydet(df, dosya_adi):
    df.to_json(dosya_adi, orient="records", force_ascii=False)

# =========================================================
# 4. OTURUM, ŞİRKET SEÇİMİ VE HAFIZA YÖNETİMİ
# =========================================================
if "giriş_yapildi" not in st.session_state:
    st.session_state["giriş_yapildi"] = False
if "secilen_sirket" not in st.session_state:
    st.session_state["secilen_sirket"] = None
if "aktif_islem" not in st.session_state:
    st.session_state["aktif_islem"] = {"durum": False, "baslangic": None, "personel": "", "stok_kodu": "", "modul": ""}

# --- A) ŞİRKET SEÇİM EKRANI ---
if st.session_state["secilen_sirket"] is None:
    st.markdown("<h1 style='text-align: center; margin-top: 20px;'>🏢 KURUMSAL OPERASYON PORTALI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 18px;'>Lütfen giriş yapmak istediğiniz firmayı seçiniz</p>", unsafe_allow_html=True)
    st.write("---")
    
    col_max, col_ilgi = st.columns(2)
    with col_max:
        st.info("### 🏭 MAXİMA MAKİNE\nÜretim takibi, BOM reçete patlatma, yürüyen bakiye simülasyonu.")
        st.write("")
        if st.button("▶ MAXİMA PORTALINA GİRİŞ YAP", type="primary", use_container_width=True):
            st.session_state["secilen_sirket"] = "MAXİMA MAKİNE"
            st.rerun()
            
    with col_ilgi:
        st.success("### 🚜 İLGİ TARIM MAKİNALARI\nKaynak & Montaj zaman etüdü, reçete yönetimi ve lojistik.")
        st.write("")
        if st.button("▶ İLGİ TARIM PORTALINA GİRİŞ YAP", type="primary", use_container_width=True):
            st.session_state["secilen_sirket"] = "İLGİ TARIM"
            st.rerun()
    st.stop()

# --- B) GİRİŞ EKRANI ---
if not st.session_state["giriş_yapildi"]:
    sirket = st.session_state["secilen_sirket"]
    st.markdown(f"## 🔒 {sirket} - Yetkili Personel Girişi")
    st.write("---")
    kullanici = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    
    c_btn1, c_btn2 = st.columns([1, 2])
    with c_btn1:
        if st.button("⬅️ Şirket Değiştir", use_container_width=True):
            st.session_state["secilen_sirket"] = None
            st.rerun()
    with c_btn2:
        if st.button("Sisteme Giriş Yap", type="primary", use_container_width=True):
            if sirket == "MAXİMA MAKİNE" and ((kullanici == "admin" and sifre == "1234") or (kullanici == "enes" and sifre == "mxm2026")):
                st.session_state["giriş_yapildi"] = True
                st.session_state["kullanici"] = kullanici
                st.rerun()
            elif sirket == "İLGİ TARIM" and ((kullanici == "admin" and sifre == "1234") or (kullanici == "deniz" and sifre == "ilgi2026")):
                st.session_state["giriş_yapildi"] = True
                st.session_state["kullanici"] = kullanici
                st.rerun()
            else:
                st.error(f"❌ '{sirket}' sistemi için hatalı giriş!")
    st.stop()

# --- TABLOLARI YÜKLE ---
if "stok_df" not in st.session_state:
    st.session_state["stok_df"] = stoklari_yukle()
if "recete_df" not in st.session_state:
    st.session_state["recete_df"] = receteleri_yukle()
if "mamuller_df" not in st.session_state:
    st.session_state["mamuller_df"] = mamulleri_yukle()
if "eksik_df" not in st.session_state:
    st.session_state["eksik_df"] = pd.DataFrame(columns=["Tarih", "Ana Mamül", "Eksik Malzeme Kodu", "Malzeme Adı", "Eksik Miktar", "Darboğaz PATH / Yolu"])
if "sevk_log_df" not in st.session_state:
    st.session_state["sevk_log_df"] = sevk_log_yukle()
if "uretim_zaman_df" not in st.session_state:
    st.session_state["uretim_zaman_df"] = uretim_zaman_yukle()
if "irsaliye_sepeti" not in st.session_state:
    st.session_state["irsaliye_sepeti"] = []

# --- ÖZYİNELEMELİ ÜRETİM MOTORU (MAXİMA İÇİN) ---
def uretimi_simule_et(mamul_kod, parent_kod, miktar, seviye, islem_kaynagi, ust_path, dict_stok, dict_ad, recete_df, log_rows, eksik_rows):
    children = recete_df[(recete_df["Mamul"] == mamul_kod) & (recete_df["Ust_Kod"] == parent_kod)]
    for _, row in children.iterrows():
        child_kod = str(row["Malzeme Kodu"]).strip()
        child_ad = str(row["Malzeme Adı"]).strip()
        birim_miktar = sayiya_cevir(row["Miktar"])
        path_bilgisi = str(row["Path"]).strip()
        gereksinim = round(miktar * birim_miktar, 4)
        mevcut_stok = round(dict_stok.get(child_kod, 0.0), 4)
        eksik_miktar = 0.0
        alt_uretim = 0.0
        
        if mevcut_stok >= gereksinim:
            tuketilen = gereksinim
            dict_stok[child_kod] = round(mevcut_stok - tuketilen, 4)
            durum_mesaji = "✅ Stoktan Karşılandı"
        else:
            tuketilen = mevcut_stok
            eksik_miktar = round(gereksinim - mevcut_stok, 4)
            has_sub_recipe = not recete_df[(recete_df["Mamul"] == mamul_kod) & (recete_df["Ust_Kod"] == child_kod)].empty
            
            if has_sub_recipe or child_kod.startswith("2."):
                uretimi_simule_et(mamul_kod, child_kod, eksik_miktar, seviye + 1, f"{child_kod} ÜRETİMİ", path_bilgisi, dict_stok, dict_ad, recete_df, log_rows, eksik_rows)
                alt_uretim = eksik_miktar
                dict_stok[child_kod] = 0.0
                durum_mesaji = f"⚙️ Yarı Mamül Üretildi ({eksik_miktar} ad.)"
            else:
                dict_stok[child_kod] = 0.0
                durum_mesaji = f"❌ EKSİK STOK ({eksik_miktar} ad. açık)"
                eksik_rows.append({"Tarih": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), "Ana Mamül": mamul_kod, "Eksik Malzeme Kodu": child_kod, "Malzeme Adı": child_ad, "Eksik Miktar": eksik_miktar, "Darboğaz PATH / Yolu": path_bilgisi})
        
        kalan_stok = round(dict_stok.get(child_kod, 0.0), 4)
        log_rows.append({"Seviye": f"Seviye {seviye}", "İşlem Kaynağı": islem_kaynagi, "Bileşen Kodu": child_kod, "Bileşen Adı": child_ad, "Gereksinim": gereksinim, "Önceki Stok": mevcut_stok, "Tüketilen": tuketilen, "Alt Üretim": alt_uretim, "Kalan Stok": kalan_stok, "PATH / Kırılım Yolu": path_bilgisi, "Durum": durum_mesaji})

# --- İRSALİYE FONKSİYONLARI BURADA GİZLENMİŞTİR (AYNI KALDI) ---
def resmi_irsaliye_pdf_olustur(evrak_no, satici_bilgi, alici_bilgi, sevk_detay, kalemler):
    pass # (Uzunluktan tasarruf için gizlendi, önceki kodun aynısıdır)

# =========================================================
# YAN MENÜ DİNAMİK YAPISI
# =========================================================
st.sidebar.markdown(f"🏢 **Firma:** `{st.session_state['secilen_sirket']}`")
st.sidebar.markdown(f"👤 **Giriş Yapan:** `{st.session_state['kullanici'].upper()}`")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["giriş_yapildi"] = False
    st.session_state["secilen_sirket"] = None
    st.rerun()

st.sidebar.divider()

# ŞİRKETE GÖRE MENÜYÜ DEĞİŞTİR
if st.session_state["secilen_sirket"] == "MAXİMA MAKİNE":
    menu_secenekleri = [
        "📊 Dashboard & Simülasyon",
        "📦 Stoklar (Manuel Kontrol)",
        "📑 Reçeteler (BOM)",
        "🏭 Mamüller (Üretim Arşivi)",
        "⚠️ Eksik Stoklar (Darboğaz)",
        "🚚 Sevkiyat & İrsaliye"
    ]
else: # İLGİ TARIM
    menu_secenekleri = [
        "📑 Sabit Reçeteler (BOM)", 
        "⏱️ Üretim Takip (Kaynak)", 
        "⏱️ Üretim Takip (Montaj)", 
        "📋 Üretim (Zaman) Kayıtları",
        "🚚 Sevkiyat & İrsaliye"
    ]

menu = st.sidebar.radio("📌 Menü Seçimi", menu_secenekleri)

# =========================================================
# MAXİMA MAKİNE BÖLÜMLERİ (Önceki kodun aynısı)
# =========================================================
if menu == "📊 Dashboard & Simülasyon":
    st.title("📊 Üretim Simülasyonu & Yürüyen Bakiye")
    # ... Maxima Dashboard Kodu ...
    
elif menu == "📦 Stoklar (Manuel Kontrol)":
    st.title("📦 Mevcut Stok Yönetimi")
    # ... Maxima Stok Kodu ...

elif menu == "🏭 Mamüller (Üretim Arşivi)":
    st.title("🏭 Başarıyla Üretilen Mamüller Listesi")
    st.dataframe(st.session_state["mamuller_df"], use_container_width=True)

elif menu == "⚠️ Eksik Stoklar (Darboğaz)":
    st.title("⚠️ Üretim Darboğazı & Eksik Stoklar")
    st.dataframe(st.session_state["eksik_df"], use_container_width=True)

# =========================================================
# ORTAK BÖLÜMLER (REÇETELER VE SEVKİYAT)
# =========================================================
elif menu in ["📑 Reçeteler (BOM)", "📑 Sabit Reçeteler (BOM)"]:
    st.title(f"📑 {st.session_state['secilen_sirket']} - Sabit Üretim Reçeteleri")
    st.info("💡 Miktar sütununa '0,164' veya '0,396' gibi virgüllü değerleri rahatça yazabilirsiniz. Kaydettiğinizde bu yapı kalıcı olarak sabitlenir.")
    
    recete_gosterim = st.session_state["recete_df"].copy()
    recete_gosterim["Miktar"] = recete_gosterim["Miktar"].astype(str)
    
    guncel_recete = st.data_editor(recete_gosterim, num_rows="dynamic", use_container_width=True, key="editor_recete")
    
    if st.button("💾 Reçeteyi Kaydet", type="primary"):
        guncel_recete["Miktar"] = guncel_recete["Miktar"].apply(sayiya_cevir)
        for col in ["Mamul", "Ust_Kod", "Malzeme Kodu"]:
            guncel_recete[col] = guncel_recete[col].astype(str).str.strip()
        st.session_state["recete_df"] = guncel_recete
        veri_kaydet(guncel_recete, DOSYA_RECETE)
        st.success("✅ Sabit Reçete listesi güncellendi ve kalıcı dosyaya yazıldı!")
        st.rerun()

# =========================================================
# YENİ: İLGİ TARIM - ÜRETİM (KAYNAK / MONTAJ) MODÜLÜ
# =========================================================
elif menu in ["⏱️ Üretim Takip (Kaynak)", "⏱️ Üretim Takip (Montaj)"]:
    islem_tipi = "Kaynak" if "Kaynak" in menu else "Montaj"
    st.title(f"⏱️ {islem_tipi} Üretimi & Zaman Etüdü")
    st.write(f"Bu ekranda **{islem_tipi}** personeline ait üretim işlemlerinin başlangıç ve bitiş süreleri kayıt altına alınır.")
    st.markdown("---")
    
    # 1. EĞER DEVAM EDEN BİR İŞLEM YOKSA (BAŞLAT EKRANI)
    if not st.session_state["aktif_islem"]["durum"]:
        c1, c2 = st.columns(2)
        with c1:
            secilen_personel = st.text_input("Personel Adı Soyadı")
        with c2:
            secilen_stok = st.selectbox("Üzerinde Çalışılacak Stok / Ürün Kodu", st.session_state["stok_df"]["Stok Kod"].unique())
            
        if st.button(f"▶️ {islem_tipi.upper()} İŞLEMİNİ BAŞLAT", type="primary", use_container_width=True):
            if secilen_personel.strip() == "":
                st.error("Lütfen işlemi başlatmadan önce personel adı giriniz!")
            else:
                st.session_state["aktif_islem"] = {
                    "durum": True,
                    "baslangic": datetime.datetime.now(),
                    "personel": secilen_personel,
                    "stok_kodu": secilen_stok,
                    "modul": islem_tipi
                }
                st.rerun()
                
    # 2. EĞER DEVAM EDEN BİR İŞLEM VARSA (BİTİR EKRANI)
    else:
        aktif = st.session_state["aktif_islem"]
        
        # Eğer aktif işlem diğer ekrandaysa kullanıcıyı uyar
        if aktif["modul"] != islem_tipi:
            st.warning(f"⚠️ Şu anda arka planda **{aktif['modul']}** modülünde çalışan bir sayacınız var. Lütfen önce o işlemi sonlandırın.")
            if st.button("Diğer Ekrana Git", type="secondary"):
                st.info("Lütfen sol menüden o sekmeye geçiş yapın.")
        else:
            st.success("🔄 Sayaç arka planda çalışıyor...")
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Çalışan Personel", aktif["personel"])
            k2.metric("İşlenen Ürün Kodu", aktif["stok_kodu"])
            k3.metric("Başlangıç Saati", aktif["baslangic"].strftime("%H:%M:%S"))
            
            st.markdown("---")
            
            c3, c4 = st.columns([1, 2])
            with c3:
                uretilen_adet = st.number_input("Toplam Üretilen / İşlenen Adet", min_value=1.0, value=1.0, step=1.0)
            
            with c4:
                st.write("") 
                st.write("")
                if st.button("⏹️ SAYAÇ BİTİR VE KAYDET", type="primary", use_container_width=True):
                    bitis_zamani = datetime.datetime.now()
                    gecen_sure = bitis_zamani - aktif["baslangic"]
                    
                    toplam_dakika = round(gecen_sure.total_seconds() / 60.0, 2)
                    birim_sure = round(toplam_dakika / uretilen_adet, 2)
                    
                    yeni_zaman_kaydi = pd.DataFrame([{
                        "Tarih": bitis_zamani.strftime("%d.%m.%Y"),
                        "Modül": aktif["modul"],
                        "Personel": aktif["personel"],
                        "Stok Kodu": aktif["stok_kodu"],
                        "Başlangıç": aktif["baslangic"].strftime("%H:%M:%S"),
                        "Bitiş": bitis_zamani.strftime("%H:%M:%S"),
                        "Toplam Süre (Dk)": toplam_dakika,
                        "Üretilen Adet": uretilen_adet,
                        "Birim Süre (Dk/Adet)": birim_sure
                    }])
                    
                    st.session_state["uretim_zaman_df"] = pd.concat([st.session_state["uretim_zaman_df"], yeni_zaman_kaydi], ignore_index=True)
                    veri_kaydet(st.session_state["uretim_zaman_df"], DOSYA_URETIM_ZAMAN)
                    
                    # Sayacı sıfırla
                    st.session_state["aktif_islem"] = {"durum": False, "baslangic": None, "personel": "", "stok_kodu": "", "modul": ""}
                    st.success("✅ Üretim işlemi başarıyla sonlandırıldı ve kayıtlar sayfasına aktarıldı!")
                    st.rerun()
            
            if st.button("❌ İşlemi İptal Et (Kaydetme)", use_container_width=True):
                st.session_state["aktif_islem"] = {"durum": False, "baslangic": None, "personel": "", "stok_kodu": "", "modul": ""}
                st.rerun()

# =========================================================
# YENİ: İLGİ TARIM - ÜRETİM (ZAMAN ETÜDÜ) KAYITLARI
# =========================================================
elif menu == "📋 Üretim (Zaman) Kayıtları":
    st.title("📋 Tamamlanmış Üretim & Zaman Etüdü Arşivi")
    st.write("Kaynak ve Montaj birimlerinde tamamlanan üretimlerin toplam ve parça başı birim sürelerini buradan inceleyebilirsiniz.")
    
    if st.session_state["uretim_zaman_df"].empty:
        st.info("Şu anda kayıtlı bir üretim verisi bulunmuyor.")
    else:
        st.dataframe(st.session_state["uretim_zaman_df"], use_container_width=True)
        
        # Küçük bir analiz tablosu
        st.markdown("### 📈 Personel Bazlı Ortalama Performans (Birim Süre)")
        ozet = st.session_state["uretim_zaman_df"].groupby(["Personel", "Stok Kodu"])["Birim Süre (Dk/Adet)"].mean().reset_index()
        st.dataframe(ozet, use_container_width=True)

# =========================================================
# 6. RESMİ SEVK İRSALİYESİ (Ortak)
# =========================================================
elif menu == "🚚 Sevkiyat & İrsaliye":
    st.title(f"🚚 {st.session_state['secilen_sirket']} - Resmi Sevk İrsaliyesi Düzenleme")
    # ... İrsaliye Kodunun Geri Kalanı (Değişiklik yapılmadı) ...
