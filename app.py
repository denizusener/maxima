import streamlit as st
import pandas as pd
import datetime
import os
import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- SAYFA VE SEKME AYARLARI ---
st.set_page_config(page_title="AGB Üretim & Sevkiyat Yönetim Sistemi", page_icon="⚙️", layout="wide")

# --- 1. OTURUM VE HAFIZA YÖNETİMİ (INITIAL STATE) ---
if "giriş_yapildi" not in st.session_state:
    st.session_state["giriş_yapildi"] = False

if not st.session_state["giriş_yapildi"]:
    st.markdown("## 🔒 AGB Üretim ve Sevkiyat Yönetim Sistemi")
    kullanici = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    
    if st.button("Sisteme Giriş Yap", type="primary"):
        if (kullanici == "admin" and sifre == "1234") or (kullanici == "patron" and sifre == "agb2026"):
            st.session_state["giriş_yapildi"] = True
            st.session_state["kullanici"] = kullanici
            st.rerun()
        else:
            st.error("❌ Hatalı Kullanıcı Adı veya Şifre!")
    st.stop()

# --- HAFIZADAKİ TABLOLAR (STOKLAR, REÇETE, MAMULLER, EKSİKLER, SEVK LOG) ---
if "stok_df" not in st.session_state:
    st.session_state["stok_df"] = pd.DataFrame([
        {"Stok Kod": "1.ATD.20.46.Ç", "Stok Adı": "ATD ÜÇ NOKTA ASKI KOMPLE", "Depo Miktar": 10.0, "Birim": "ADET"},
        {"Stok Kod": "2.ATD.000.01.000.0", "Stok Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Depo Miktar": 2.0, "Birim": "ADET"},
        {"Stok Kod": "7.1.3.1001", "Stok Adı": "LAMA 40 X 10 HAMMADDE", "Depo Miktar": 50.0, "Birim": "METRE"},
        {"Stok Kod": "7.2.2.ATD.0014", "Stok Adı": "ATD ÜÇ NOKTA ASKI SACI SAĞ", "Depo Miktar": 20.0, "Birim": "ADET"}
    ])

if "recete_df" not in st.session_state:
    st.session_state["recete_df"] = pd.DataFrame([
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "1.ATD.20.46.Ç", "Malzeme Kodu": "2.ATD.000.01.000.0", "Malzeme Adı": "ATD ÜÇ NOKTA ASKI YEDEK PARÇA", "Miktar": 1.0, "Seviye": 1, "Path": "1.ATD...>2.ATD..."},
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "2.ATD.000.01.000.0", "Malzeme Kodu": "7.1.3.1001", "Malzeme Adı": "LAMA 40 X 10 HAMMADDE", "Miktar": 4.0, "Seviye": 2, "Path": "1.ATD...>2.ATD...>7.1.3..."},
        {"Mamul": "1.ATD.20.46.Ç", "Ust_Kod": "2.ATD.000.01.000.0", "Malzeme Kodu": "7.2.2.ATD.0014", "Malzeme Adı": "ATD ÜÇ NOKTA ASKI SACI SAĞ", "Miktar": 1.0, "Seviye": 2, "Path": "1.ATD...>2.ATD...>7.2.2..."}
    ])

if "mamuller_df" not in st.session_state:
    st.session_state["mamuller_df"] = pd.DataFrame(columns=["Tarih", "Mamul Kod", "Mamul Adı", "Üretilen Adet", "Durum"])

if "eksik_df" not in st.session_state:
    st.session_state["eksik_df"] = pd.DataFrame(columns=["Tarih", "Ana Mamül", "Eksik Malzeme Kodu", "Malzeme Adı", "Eksik Miktar", "Darboğaz PATH / Yolu"])

if "sevk_log_df" not in st.session_state:
    st.session_state["sevk_log_df"] = pd.DataFrame(columns=["Tarih", "Evrak No", "Firma", "Sevk Eden", "Mamül Kodu", "Sevk Adedi"])

# --- ÖZYİNELEMELİ (RECURSIVE) VE YÜRÜYEN BAKİYELİ ÜRETİM MOTORU ---
def uretimi_simule_et(mamul_kod, parent_kod, miktar, seviye, islem_kaynagi, ust_path, dict_stok, dict_ad, recete_df, log_rows, eksik_rows):
    children = recete_df[(recete_df["Mamul"] == mamul_kod) & (recete_df["Ust_Kod"] == parent_kod)]
    for _, row in children.iterrows():
        child_kod = str(row["Malzeme Kodu"]).strip()
        child_ad = str(row["Malzeme Adı"]).strip()
        birim_miktar = float(row["Miktar"])
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
                eksik_rows.append({
                    "Tarih": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "Ana Mamül": mamul_kod,
                    "Eksik Malzeme Kodu": child_kod,
                    "Malzeme Adı": child_ad,
                    "Eksik Miktar": eksik_miktar,
                    "Darboğaz PATH / Yolu": path_bilgisi
                })
        
        kalan_stok = round(dict_stok.get(child_kod, 0.0), 4)
        log_rows.append({
            "Seviye": f"Seviye {seviye}",
            "İşlem Kaynağı": islem_kaynagi,
            "Bileşen Kodu": child_kod,
            "Bileşen Adı": child_ad,
            "Gereksinim": gereksinim,
            "Önceki Stok": mevcut_stok,
            "Tüketilen": tuketilen,
            "Alt Üretim": alt_uretim,
            "Kalan Stok": kalan_stok,
            "PATH / Kırılım Yolu": path_bilgisi,
            "Durum": durum_mesaji
        })

# --- PDF İRSALİYE OLUŞTURUCU ---
def pdf_irsaliye_olustur(evrak_no, firma, sevk_eden, mamul_kod, sevk_adet):
    pdf_yolu = f"/tmp/Sevkiyat_{evrak_no}.pdf"
    c = canvas.Canvas(pdf_yolu, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, "AGB HIDROLIK & MAKINA")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 775, f"SEVKIYAT VE IRSALIYE FORMU ({evrak_no})")
    c.line(50, 765, 550, 765)
    
    c.setFont("Helvetica", 11)
    c.drawString(50, 730, f"Firma / Müşteri: {firma}")
    c.drawString(50, 710, f"Sevk Eden Yetkili: {sevk_eden}")
    c.drawString(50, 690, f"Düzenleme Tarihi: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    c.line(50, 670, 550, 670)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 650, "MAMUL KODU")
    c.drawString(300, 650, "SEVK EDILEN ADET")
    c.drawString(450, 650, "BIRIM")
    c.line(50, 640, 550, 640)
    
    c.setFont("Helvetica", 11)
    c.drawString(50, 620, str(mamul_kod))
    c.drawString(300, 620, str(sevk_adet))
    c.drawString(450, 620, "ADET")
    
    c.line(50, 100, 550, 100)
    c.drawString(50, 80, "Teslim Eden İmza: ........................         Teslim Alan İmza: ........................")
    c.save()
    return pdf_yolu

# --- GERÇEK SMTP MAİL GÖNDERİCİ ---
def mail_gonder(alici_mail, evrak_no, firma, pdf_yolu, smtp_user, smtp_pass):
    msg = EmailMessage()
    msg["Subject"] = f"AGB Hidrolik - Sevkiyat İrsaliyesi ({evrak_no})"
    msg["From"] = smtp_user
    msg["To"] = alici_mail
    msg.set_content(f"Sayın {firma} Yetkilisi,\n\n{evrak_no} referans numaralı sevkiyatımıza ait irsaliye belgesi ekte PDF olarak sunulmuştur.\n\nİyi çalışmalar dileriz.")
    
    with open(pdf_yolu, "rb") as f:
        pdf_data = f.read()
    msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=f"Sevkiyat_{evrak_no}.pdf")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)

# =========================================================
# YAN MENÜ VE SAYFA YÖNLENDİRMELERİ
# =========================================================
st.sidebar.markdown(f"👤 **Giriş Yapan:** `{st.session_state['kullanici'].upper()}`")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["giriş_yapildi"] = False
    st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("📌 Menü Seçimi", [
    "📊 Dashboard & Simülasyon",
    "📦 Stoklar (Manuel Kontrol)",
    "📑 Reçeteler (BOM)",
    "🏭 Mamüller (Üretim Arşivi)",
    "⚠️ Eksik Stoklar (Darboğaz)",
    "🚚 Sevkiyat & İrsaliye"
])

# =========================================================
# 1. EKRAN: DASHBOARD & SİMÜLASYON (TAM ÇEKİRDEK KONTROL)
# =========================================================
if menu == "📊 Dashboard & Simülasyon":
    st.title("📊 Çok Seviyeli Üretim Simülasyonu & Yürüyen Bakiye")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        mamul_kod = st.text_input("Üretilecek Mamül Kodu", "1.ATD.20.46.Ç")
    with col2:
        hedef_adet = st.number_input("Hedef Adet", min_value=1.0, value=5.0, step=1.0)
        
    if st.button("▶ SİMÜLASYONU BAŞLAT VE REÇETEYİ PATLAT", type="primary", use_container_width=True):
        stok_dict = dict(zip(st.session_state["stok_df"]["Stok Kod"], st.session_state["stok_df"]["Depo Miktar"]))
        ad_dict = dict(zip(st.session_state["stok_df"]["Stok Kod"], st.session_state["stok_df"]["Stok Adı"]))
        
        # Hafızada test etmek için kopyasını oluştur (Ya Hep Ya Hiç Koruması)
        test_stok_dict = stok_dict.copy()
        log_rows = []
        eksik_rows = []
        
        uretimi_simule_et(mamul_kod, mamul_kod, hedef_adet, 1, "ANA ÜRETİM EMRİ", "", test_stok_dict, ad_dict, st.session_state["recete_df"], log_rows, eksik_rows)
        
        st.divider()
        toplam_islem = len(log_rows)
        ym_uretim = sum(1 for row in log_rows if "⚙️" in row["Durum"])
        eksik_sayisi = len(eksik_rows)
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Toplam İşlem Gören Kalem", f"{toplam_islem} Adet")
        k2.metric("Üretilen Yarı Mamül (2.xxx)", f"{ym_uretim} Adet")
        k3.metric("Darboğaz / Eksik Malzeme", f"{eksik_sayisi} Adet")
        
        if eksik_sayisi > 0:
            st.error("❌ DİKKAT: Üretim için yetersiz stok / darboğaz tespit edildi!")
            st.warning("🛡️ 'Ya Hep Ya Hiç' Koruması Devrede: STOKLAR sayfasından hiçbir miktar düşülmedi ve üretime onay verilmedi. Eksikleri tamamlayıp tekrar deneyin.")
            
            # Eksik listesini sekmeye kaydet
            st.session_state["eksik_df"] = pd.DataFrame(eksik_rows)
            st.dataframe(st.session_state["eksik_df"], use_container_width=True)
        else:
            # Hiç eksik yoksa gerçek stok tablosunu güncelle
            for i, row in st.session_state["stok_df"].iterrows():
                kod = row["Stok Kod"]
                if kod in test_stok_dict:
                    st.session_state["stok_df"].at[i, "Depo Miktar"] = test_stok_dict[kod]
            
            # Mamüller sayfasına üretim kaydı at
            yeni_mamul = pd.DataFrame([{
                "Tarih": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Mamul Kod": mamul_kod,
                "Mamul Adı": ad_dict.get(mamul_kod, mamul_kod),
                "Üretilen Adet": hedef_adet,
                "Durum": "Üretildi (Tamamlandı)"
            }])
            st.session_state["mamuller_df"] = pd.concat([st.session_state["mamuller_df"], yeni_mamul], ignore_index=True)
            st.session_state["eksik_df"] = pd.DataFrame(columns=["Tarih", "Ana Mamül", "Eksik Malzeme Kodu", "Malzeme Adı", "Eksik Miktar", "Darboğaz PATH / Yolu"])
            
            st.success("✅ BAŞARILI: Hiçbir darboğazla karşılaşılmadı! Stoklar kalıcı olarak düşüldü ve MAMÜLLER sayfasına eklendi.")
            st.dataframe(pd.DataFrame(log_rows), use_container_width=True)

# =========================================================
# 2. EKRAN: STOKLAR (ELLE MANUEL KONTROL VE DEĞİŞİKLİK)
# =========================================================
elif menu == "📦 Stoklar (Manuel Kontrol)":
    st.title("📦 Mevcut Stok Yönetimi")
    st.info("💡 Tablodaki hücrelere çift tıklayarak stokları manuel güncelleyebilirsiniz.")
    guncel_stok = st.data_editor(st.session_state["stok_df"], num_rows="dynamic", use_container_width=True)
    if st.button("💾 Değişiklikleri Kaydet", type="primary"):
        st.session_state["stok_df"] = guncel_stok
        st.success("✅ Stoklar güncellendi!")

# =========================================================
# 3. EKRAN: REÇETELER (BOM LİSTESİ)
# =========================================================
elif menu == "📑 Reçeteler (BOM)":
    st.title("📑 Üretim Reçeteleri (BOM Listesi)")
    guncel_recete = st.data_editor(st.session_state["recete_df"], num_rows="dynamic", use_container_width=True)
    if st.button("💾 Reçeteyi Kaydet", type="primary"):
        st.session_state["recete_df"] = guncel_recete
        st.success("✅ Reçete listesi güncellendi!")

# =========================================================
# 4. EKRAN: MAMÜLLER (ÜRETİM ARŞİVİ)
# =========================================================
elif menu == "🏭 Mamüller (Üretim Arşivi)":
    st.title("🏭 Başarıyla Üretilen Mamüller Listesi")
    st.dataframe(st.session_state["mamuller_df"], use_container_width=True)

# =========================================================
# 5. EKRAN: EKSİK STOKLAR (DARBOĞAZ KONTROLÜ)
# =========================================================
elif menu == "⚠️ Eksik Stoklar (Darboğaz)":
    st.title("⚠️ Üretim Darboğazı & Eksik Stoklar")
    if st.session_state["eksik_df"].empty:
        st.success("🎉 Harika! Şu an hiçbir üretimde eksik stok darboğazı bulunmuyor.")
    else:
        st.error("❌ Aşağıdaki malzemeler yetersiz olduğu için üretimler durdurulmuştur:")
        st.dataframe(st.session_state["eksik_df"], use_container_width=True)

# =========================================================
# 6. EKRAN: SEVKİYAT, STOK KONTROLÜ VE E-POSTA
# =========================================================
elif menu == "🚚 Sevkiyat & İrsaliye":
    st.title("🚚 Sevkiyat, Stok Kontrolü ve PDF E-Posta")
    
    col1, col2 = st.columns(2)
    with col1:
        firma = st.text_input("Sevk Edilecek Firma", "AGB Hidrolik A.Ş.")
        evrak_no = st.text_input("İrsaliye / Evrak No", "SVK-2026-001")
        mail_adresi = st.text_input("Gönderilecek Müşteri Mail Adresi", "alici@firma.com")
    with col2:
        sevk_kod = st.selectbox("Sevk Edilecek Mamül Kodu", st.session_state["stok_df"]["Stok Kod"].unique())
        sevk_miktar = st.number_input("Sevk Edilecek Adet", min_value=1.0, value=1.0, step=1.0)
        sevk_eden = st.text_input("Sevk Eden Yetkili", st.session_state["kullanici"].upper())
        
    with st.expander("📧 E-Posta SMTP Gönderici Ayarları (Gerçek Mail Atmak İçin)"):
        smtp_user = st.text_input("Gönderici Gmail Adresi", "seninmailin@gmail.com")
        smtp_pass = st.text_input("Gmail Uygulama Şifresi (App Password)", type="password")
        mail_aktif = st.checkbox("Sevkiyatta Müşteriye E-Posta Gönder", value=False)
        
    if st.button("▶ SEVKİYATI ONAYLA, PDF OLUŞTUR VE MAİL AT", type="primary"):
        # 1. STOK KONTROLÜ
        mevcut_satir = st.session_state["stok_df"][st.session_state["stok_df"]["Stok Kod"] == sevk_kod]
        if mevcut_satir.empty:
            st.error("❌ HATA: Seçilen ürün stok listesinde bulunamadı!")
            st.stop()
            
        mevcut_stok = float(mevcut_satir["Depo Miktar"].values[0])
        
        if sevk_miktar > mevcut_stok:
            st.error(f"❌ HATA: Depoda Yeterli Stok Yok! Sevk Edilmek İstenen: {sevk_miktar} | Depodaki Stok: {mevcut_stok}")
            st.stop()
            
        # 2. STOK DÜŞME
        idx = mevcut_satir.index[0]
        st.session_state["stok_df"].at[idx, "Depo Miktar"] = round(mevcut_stok - sevk_miktar, 4)
        
        # 3. LOG KAYDI
        yeni_sevk = pd.DataFrame([{
            "Tarih": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            "Evrak No": evrak_no,
            "Firma": firma,
            "Sevk Eden": sevk_eden,
            "Mamül Kodu": sevk_kod,
            "Sevk Adedi": sevk_miktar
        }])
        st.session_state["sevk_log_df"] = pd.concat([st.session_state["sevk_log_df"], yeni_sevk], ignore_index=True)
        
        # 4. PDF İRSALİYE OLUŞTURMA
        pdf_dosya = pdf_irsaliye_olustur(evrak_no, firma, sevk_eden, sevk_kod, sevk_miktar)
        
        # 5. GERÇEK E-POSTA GÖNDERİMİ (SEÇİLDİYSE)
        mail_basarili = False
        if mail_aktif and smtp_user and smtp_pass:
            try:
                mail_gonder(mail_adresi, evrak_no, firma, pdf_dosya, smtp_user, smtp_pass)
                mail_basarili = True
            except Exception as e:
                st.warning(f"⚠️ Stoklar düştü, PDF oluştu fakat Mail gönderilemedi: {e}")
        
        st.success(f"✅ {sevk_kod} kodlu mamülden {sevk_miktar} adet başarıyla sevk edildi! Güncel Depo Stoku: {st.session_state['stok_df'].at[idx, 'Depo Miktar']}")
        if mail_basarili:
            st.info(f"📧 İrsaliye PDF'i {mail_adresi} adresine başarıyla gönderildi!")
            
        # İndirilebilir PDF Butonu
        with open(pdf_dosya, "rb") as f:
            st.download_button("📥 İRSALİYE PDF'İNİ İNDİR", data=f, file_name=f"Sevkiyat_{evrak_no}.pdf", mime="application/pdf")
            
    if not st.session_state["sevk_log_df"].empty:
        st.write("---")
        st.subheader("📋 Geçmiş Sevkiyat Kayıtları")
        st.dataframe(st.session_state["sevk_log_df"], use_container_width=True)
