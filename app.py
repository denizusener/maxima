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
st.set_page_config(page_title="AGB Üretim & Sevkiyat Yönetim Sistemi", page_icon="⚙️", layout="wide")

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

def veri_kaydet(df, dosya_adi):
    df.to_json(dosya_adi, orient="records", force_ascii=False)

# --- 4. OTURUM VE HAFIZA YÖNETİMİ ---
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

# --- TABLOLARI DOSYADAN YÜKLE ---
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
if "irsaliye_sepeti" not in st.session_state:
    st.session_state["irsaliye_sepeti"] = []

# --- ÖZYİNELEMELİ (RECURSIVE) ÜRETİM MOTORU ---
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

# --- RESMİ SEVK İRSALİYESİ (A4 PDF) OLUŞTURUCU ---
def resmi_irsaliye_pdf_olustur(evrak_no, satici_bilgi, alici_bilgi, sevk_detay, kalemler):
    pdf_yolu = f"/tmp/Sevk_Irsaliyesi_{evrak_no}.pdf"
    doc = SimpleDocTemplate(pdf_yolu, pagesize=A4, leftMargin=35, rightMargin=35, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#1A365D"), alignment=TA_CENTER, spaceAfter=15)
    style_normal = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13)
    style_bold = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=13)
    
    story = []
    story.append(Paragraph(pdf_text("AGB HIDROLIK & MAKINA SAN. TIC. A.S."), style_title))
    story.append(Paragraph(pdf_text(f"SEVK IRSALIYESI - No: {evrak_no}"), style_title))
    story.append(Spacer(1, 10))
    
    satici_txt = f"<b>DÜZENLEYEN (SATICICI):</b><br/>{pdf_text(satici_bilgi['unvan'])}<br/>Adres: {pdf_text(satici_bilgi['adres'])}<br/>V.D. / No: {pdf_text(satici_bilgi['vd'])}"
    alici_txt = f"<b>ALICI (MÜŞTERİ):</b><br/>{pdf_text(alici_bilgi['unvan'])}<br/>Adres: {pdf_text(alici_bilgi['adres'])}<br/>V.D. / No: {pdf_text(alici_bilgi['vd'])}"
    
    t_fatura = Table([[Paragraph(satici_txt, style_normal), Paragraph(alici_txt, style_normal)]], colWidths=[260, 260])
    t_fatura.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#A0AEC0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_fatura)
    story.append(Spacer(1, 12))
    
    detay_txt = f"<b>Düzenleme Tarihi:</b> {sevk_detay['duzenleme_tarih']}   |   <b>Fiili Sevk Tarihi & Saati:</b> {sevk_detay['fiili_sevk']}   |   <b>Araç Plakası:</b> {pdf_text(sevk_detay['plaka'])}   |   <b>Şoför:</b> {pdf_text(sevk_detay['sofor'])}"
    t_detay = Table([[Paragraph(detay_txt, style_normal)]], colWidths=[520])
    t_detay.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EDF2F7")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_detay)
    story.append(Spacer(1, 15))
    
    tablo_veri = [[Paragraph("<b>Sıra</b>", style_bold), Paragraph("<b>Stok / Malzeme Kodu</b>", style_bold), Paragraph("<b>Malın Cinsi / Açıklaması</b>", style_bold), Paragraph("<b>Miktar</b>", style_bold), Paragraph("<b>Birim</b>", style_bold)]]
    for i, item in enumerate(kalemler, start=1):
        tablo_veri.append([Paragraph(str(i), style_normal), Paragraph(pdf_text(item["kod"]), style_normal), Paragraph(pdf_text(item["ad"]), style_normal), Paragraph(str(item["miktar"]), style_normal), Paragraph(pdf_text(item["birim"]), style_normal)])
        
    t_urunler = Table(tablo_veri, colWidths=[35, 120, 235, 65, 65])
    t_urunler.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#718096")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_urunler)
    story.append(Spacer(1, 25))
    
    yasal_not = "<i>İşbu sevk irsaliyesi muhteviyatı mallar yukarıda belirtilen miktar ve niteliklere uygun olarak eksiksiz ve hasarsız bir şekilde teslim edilmiştir/alınmıştır.</i>"
    story.append(Paragraph(pdf_text(yasal_not), style_normal))
    story.append(Spacer(1, 15))
    
    imza_tablo = Table([[
        Paragraph("<b>TESLİM EDEN (SEVK EDEN)</b><br/><br/>İmza / Kaşe:<br/><br/>........................................", style_normal),
        Paragraph("<b>TAŞIYICI / ŞOFÖR</b><br/><br/>İmza:<br/><br/>........................................", style_normal),
        Paragraph("<b>TESLİM ALAN (MÜŞTERİ)</b><br/><br/>İmza / Kaşe:<br/><br/>........................................", style_normal)
    ]], colWidths=[173, 173, 174])
    imza_tablo.setStyle(TableStyle([('TOPPADDING', (0,0), (-1,-1), 10), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(KeepTogether(imza_tablo))
    doc.build(story)
    return pdf_yolu

# --- GERÇEK SMTP MAİL GÖNDERİCİ ---
def mail_gonder(alici_mail, evrak_no, firma, pdf_yolu, smtp_user, smtp_pass):
    msg = EmailMessage()
    msg["Subject"] = f"AGB Hidrolik - Sevk İrsaliyesi ({evrak_no})"
    msg["From"] = smtp_user
    msg["To"] = alici_mail
    msg.set_content(f"Sayın {firma} Yetkilisi,\n\n{evrak_no} seri numaralı sevk irsaliyemize ait resmi evrak ekte PDF olarak sunulmuştur.\n\nMalların eksiksiz teslim alınmasını rica eder, iyi çalışmalar dileriz.\nAGB Hidrolik ve Makina San. Tic. A.Ş.")
    with open(pdf_yolu, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=f"Sevk_Irsaliyesi_{evrak_no}.pdf")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)

# =========================================================
# YAN MENÜ
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
# 1. DASHBOARD & SİMÜLASYON
# =========================================================
if menu == "📊 Dashboard & Simülasyon":
    st.title("📊 Çok Seviyeli Üretim Simülasyonu & Yürüyen Bakiye")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        mamul_kod = st.text_input("Üretilecek Mamül Kodu", "1.ATD.20.46.Ç")
    with col2:
        hedef_adet = st.number_input("Hedef Adet", min_value=1.0, value=5.0, step=1.0)
        
    if st.button("▶ SİMÜLASYONU BAŞLAT VE REÇETEYİ PATLAT", type="primary", use_container_width=True):
        stok_dict = {row["Stok Kod"]: sayiya_cevir(row["Depo Miktar"]) for _, row in st.session_state["stok_df"].iterrows()}
        ad_dict = dict(zip(st.session_state["stok_df"]["Stok Kod"], st.session_state["stok_df"]["Stok Adı"]))
        
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
            st.warning("🛡️ 'Ya Hep Ya Hiç' Koruması Devrede: STOKLAR sayfasından hiçbir miktar düşülmedi ve üretime onay verilmedi.")
            st.session_state["eksik_df"] = pd.DataFrame(eksik_rows)
            st.dataframe(st.session_state["eksik_df"], use_container_width=True)
        else:
            for i, row in st.session_state["stok_df"].iterrows():
                kod = row["Stok Kod"]
                if kod in test_stok_dict:
                    st.session_state["stok_df"].at[i, "Depo Miktar"] = test_stok_dict[kod]
            
            # Üretim sonrası stokları kalıcı olarak dosyaya kaydet
            veri_kaydet(st.session_state["stok_df"], DOSYA_STOK)
            
            yeni_mamul = pd.DataFrame([{
                "Tarih": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Mamul Kod": mamul_kod,
                "Mamul Adı": ad_dict.get(mamul_kod, mamul_kod),
                "Üretilen Adet": hedef_adet,
                "Durum": "Üretildi (Tamamlandı)"
            }])
            st.session_state["mamuller_df"] = pd.concat([st.session_state["mamuller_df"], yeni_mamul], ignore_index=True)
            veri_kaydet(st.session_state["mamuller_df"], DOSYA_MAMUL)
            
            st.session_state["eksik_df"] = pd.DataFrame(columns=["Tarih", "Ana Mamül", "Eksik Malzeme Kodu", "Malzeme Adı", "Eksik Miktar", "Darboğaz PATH / Yolu"])
            st.success("✅ BAŞARILI: Hiçbir darboğazla karşılaşılmadı! Stoklar kalıcı olarak düşüldü ve dosyaya kaydedildi.")
            st.dataframe(pd.DataFrame(log_rows), use_container_width=True)

# =========================================================
# 2. STOKLAR (ELLE MANUEL KONTROL & KALICI DOSYA KAYDI)
# =========================================================
elif menu == "📦 Stoklar (Manuel Kontrol)":
    st.title("📦 Mevcut Stok Yönetimi")
    st.info("💡 Tablodaki hücrelere çift tıklayarak stokları manuel güncelleyebilirsiniz.")
    guncel_stok = st.data_editor(st.session_state["stok_df"], num_rows="dynamic", use_container_width=True, key="editor_stok")
    if st.button("💾 Değişiklikleri Kaydet", type="primary"):
        guncel_stok["Depo Miktar"] = guncel_stok["Depo Miktar"].apply(sayiya_cevir)
        guncel_stok["Stok Kod"] = guncel_stok["Stok Kod"].astype(str).str.strip()
        st.session_state["stok_df"] = guncel_stok
        veri_kaydet(guncel_stok, DOSYA_STOK)
        st.success("✅ Stoklar güncellendi ve kalıcı dosyaya kaydedildi!")
        st.rerun()

# =========================================================
# 3. REÇETELER (KALICI DOSYA KAYDI)
# =========================================================
elif menu == "📑 Reçeteler (BOM)":
    st.title("📑 Üretim Reçeteleri (BOM Listesi)")
    guncel_recete = st.data_editor(st.session_state["recete_df"], num_rows="dynamic", use_container_width=True, key="editor_recete")
    if st.button("💾 Reçeteyi Kaydet", type="primary"):
        guncel_recete["Miktar"] = guncel_recete["Miktar"].apply(sayiya_cevir)
        for col in ["Mamul", "Ust_Kod", "Malzeme Kodu"]:
            guncel_recete[col] = guncel_recete[col].astype(str).str.strip()
        st.session_state["recete_df"] = guncel_recete
        veri_kaydet(guncel_recete, DOSYA_RECETE)
        st.success("✅ Reçete listesi güncellendi ve kalıcı dosyaya yazıldı!")
        st.rerun()

# =========================================================
# 4. MAMÜLLER
# =========================================================
elif menu == "🏭 Mamüller (Üretim Arşivi)":
    st.title("🏭 Başarıyla Üretilen Mamüller Listesi")
    st.dataframe(st.session_state["mamuller_df"], use_container_width=True)

# =========================================================
# 5. EKSİK STOKLAR
# =========================================================
elif menu == "⚠️ Eksik Stoklar (Darboğaz)":
    st.title("⚠️ Üretim Darboğazı & Eksik Stoklar")
    if st.session_state["eksik_df"].empty:
        st.success("🎉 Harika! Şu an hiçbir üretimde eksik stok darboğazı bulunmuyor.")
    else:
        st.error("❌ Aşağıdaki malzemeler yetersiz olduğu için üretimler durdurulmuştur:")
        st.dataframe(st.session_state["eksik_df"], use_container_width=True)

# =========================================================
# 6. RESMİ SEVK İRSALİYESİ & ÇOKLU SEVKİYAT SEPETİ
# =========================================================
elif menu == "🚚 Sevkiyat & İrsaliye":
    st.title("🚚 Resmi Sevk İrsaliyesi Düzenleme & Lojistik")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 Düzenleyen (Bizim Firma)")
        s_unvan = st.text_input("Satıcı Ünvanı", "AGB HİDROLİK VE MAKİNA SAN. TİC. A.Ş.")
        s_adres = st.text_area("Satıcı Adresi", "Organize Sanayi Bölgesi 2. Cadde No:14 Aydın / Türkiye", height=68)
        s_vd = st.text_input("Vergi Dairesi / No", "Aydın V.D. - 0123456789")
    with c2:
        st.subheader("🏬 Alıcı (Müşteri Firma)")
        a_unvan = st.text_input("Alıcı Firma Ünvanı", "ÇUKUROVA TARIM MAKİNALARI LTD. ŞTİ.")
        a_adres = st.text_area("Alıcı Sevk Adresi", "Sanayi Sitesi 4. Blok No:89 Seyhan / Adana", height=68)
        a_vd = st.text_input("Alıcı V.D. / No", "Seyhan V.D. - 9876543210")
        a_mail = st.text_input("Alıcı E-Posta Adresi", "satinalma@cukurova.com")

    st.markdown("---")
    
    st.subheader("🚛 Taşıma & Evrak Detayları")
    c3, c4, c5, c6 = st.columns(4)
    with c3:
        evrak_no = st.text_input("İrsaliye Seri / Sıra No", "AGB-2026-0001")
    with c4:
        fiili_sevk = st.text_input("Fiili Sevk Tarihi & Saati", datetime.datetime.now().strftime("%d.%m.%Y - %H:30"))
    with c5:
        plaka = st.text_input("Taşıyıcı Araç Plakası", "09 AGB 456")
    with c6:
        sofor = st.text_input("Şoför Adı Soyadı", "Ahmet Yılmaz")

    st.markdown("---")
    
    st.subheader("📦 İrsaliyeye Eklenecek Ürün Kalemleri")
    c7, c8, c9 = st.columns([2, 1, 1])
    with c7:
        secilen_kod = st.selectbox("Sevk Edilecek Stok / Mamül Kodu", st.session_state["stok_df"]["Stok Kod"].unique())
    with c8:
        secilen_adet = st.number_input("Sevk Adedi", min_value=1.0, value=1.0, step=1.0)
    with c9:
        st.write("")
        st.write("")
        if st.button("➕ İrsaliyeye Ekle", use_container_width=True):
            satir = st.session_state["stok_df"][st.session_state["stok_df"]["Stok Kod"] == secilen_kod].iloc[0]
            st.session_state["irsaliye_sepeti"].append({
                "kod": secilen_kod,
                "ad": satir["Stok Adı"],
                "miktar": secilen_adet,
                "birim": satir["Birim"]
            })
            st.success(f"{secilen_kod} irsaliye listesine eklendi!")

    if len(st.session_state["irsaliye_sepeti"]) > 0:
        st.write("### 🛒 Hazırlanan İrsaliye Listesi")
        sepet_df = pd.DataFrame(st.session_state["irsaliye_sepeti"])
        st.dataframe(sepet_df, use_container_width=True)
        
        if st.button("🗑️ Sepeti Temizle"):
            st.session_state["irsaliye_sepeti"] = []
            st.rerun()

        st.markdown("---")
        
        with st.expander("📧 E-Posta SMTP Gönderici Ayarları (Gerçek Mail Atmak İçin)"):
            smtp_user = st.text_input("Gönderici Gmail Adresi", "seninmailin@gmail.com")
            smtp_pass = st.text_input("Gmail Uygulama Şifresi (App Password)", type="password")
            mail_aktif = st.checkbox("İrsaliye Onaylandığında Müşteriye E-Posta Gönder", value=False)

        if st.button("▶ RESMİ İRSALİYEYİ ONAYLA, STOKLARDAN DÜŞ VE SEVK ET", type="primary", use_container_width=True):
            yetersizler = []
            for item in st.session_state["irsaliye_sepeti"]:
                m_row = st.session_state["stok_df"][st.session_state["stok_df"]["Stok Kod"] == item["kod"]]
                mevcut_stok_val = sayiya_cevir(m_row["Depo Miktar"].values[0]) if not m_row.empty else 0.0
                if m_row.empty or mevcut_stok_val < item["miktar"]:
                    yetersizler.append(f"• {item['kod']} ( İstenen: {item['miktar']} | Depoda: {mevcut_stok_val} )")
            
            if len(yetersizler) > 0:
                st.error("❌ HATA: Aşağıdaki ürünlerin depodaki stoku yetersiz! Hiçbir düşüm yapılmadı:")
                for y in yetersizler:
                    st.write(y)
                st.stop()
            
            for item in st.session_state["irsaliye_sepeti"]:
                idx = st.session_state["stok_df"][st.session_state["stok_df"]["Stok Kod"] == item["kod"]].index[0]
                mevcut = sayiya_cevir(st.session_state["stok_df"].at[idx, "Depo Miktar"])
                st.session_state["stok_df"].at[idx, "Depo Miktar"] = round(mevcut - item["miktar"], 4)
                
                yeni_log = pd.DataFrame([{
                    "Tarih": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "Evrak No": evrak_no,
                    "Firma": a_unvan,
                    "Araç Plaka": plaka,
                    "Mamül Kodu": item["kod"],
                    "Sevk Adedi": item["miktar"]
                }])
                st.session_state["sevk_log_df"] = pd.concat([st.session_state["sevk_log_df"], yeni_log], ignore_index=True)

            # Sevkiyat sonrası düşülen stokları ve geçmişi kalıcı olarak dosyaya kaydet
            veri_kaydet(st.session_state["stok_df"], DOSYA_STOK)
            veri_kaydet(st.session_state["sevk_log_df"], DOSYA_SEVK)

            satici_info = {"unvan": s_unvan, "adres": s_adres, "vd": s_vd}
            alici_info = {"unvan": a_unvan, "adres": a_adres, "vd": a_vd}
            detay_info = {
                "duzenleme_tarih": datetime.datetime.now().strftime("%d.%m.%Y"),
                "fiili_sevk": fiili_sevk,
                "plaka": plaka,
                "sofor": sofor
            }
            
            pdf_yolu = resmi_irsaliye_pdf_olustur(evrak_no, satici_info, alici_info, detay_info, st.session_state["irsaliye_sepeti"])
            
            mail_msg = ""
            if mail_aktif and smtp_user and smtp_pass:
                try:
                    mail_gonder(a_mail, evrak_no, a_unvan, pdf_yolu, smtp_user, smtp_pass)
                    mail_msg = f" 📧 Resmi sevk irsaliyesi {a_mail} adresine gönderildi!"
                except Exception as e:
                    mail_msg = f" ⚠️ PDF oluştu ancak E-Posta gönderilemedi: {e}"

            st.success(f"✅ {evrak_no} irsaliyesi başarıyla kesildi, stoklardan düşüldü ve kalıcı dosyaya kaydedildi!{mail_msg}")
            
            with open(pdf_yolu, "rb") as f:
                st.download_button(
                    label="📥 RESMİ SEVK İRSALİYESİ PDF'İNİ İNDİR",
                    data=f,
                    file_name=f"Sevk_Irsaliyesi_{evrak_no}.pdf",
                    mime="application/pdf"
                )
            
            st.session_state["irsaliye_sepeti"] = []
    else:
        st.info("💡 İrsaliye oluşturmak için yukarıdan ürün seçip 'İrsaliyeye Ekle' butonuna basınız.")

    if not st.session_state["sevk_log_df"].empty:
        st.write("---")
        st.subheader("📋 Geçmiş Sevkiyat ve İrsaliye Kayıtları")
        st.dataframe(st.session_state["sevk_log_df"], use_container_width=True)
