import streamlit as st
import pandas as pd
import datetime
import os

# --- SAYFA VE SEKME AYARLARI ---
st.set_page_config(page_title="Kurumsal Üretim & Sevkiyat Portalı", page_icon="⚙️", layout="wide")

# --- 1. TÜRKÇE ONDALIK VE VİRGÜL DÜZELTİCİ ---
def sayiya_cevir(val):
    if pd.isna(val) or val == "" or val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip().replace(" ", "")
    if "." in val_str and "," in val_str: val_str = val_str.replace(".", "").replace(",", ".")
    else: val_str = val_str.replace(",", ".")
    try: return float(val_str)
    except: return 0.0

# --- 2. KALICI DOSYA KAYIT MOTORU ---
DOSYA_STOK = "veri_stoklar.json"
DOSYA_URETIM_ZAMAN = "veri_uretim_zaman_log.json"
DOSYA_PERSONEL = "veri_personeller.json"
DOSYA_OPERASYON = "veri_operasyonlar.json"
DOSYA_AKTIF = "veri_aktif_islemler.json"

def stoklari_yukle():
    if os.path.exists(DOSYA_STOK):
        try:
            df = pd.read_json(DOSYA_STOK)
            # Sütun isimlerini normalize et
            if "Stok Kodu" not in df.columns and "Stok Kod" in df.columns:
                df.rename(columns={"Stok Kod": "Stok Kodu"}, inplace=True)
            df["Stok Kodu"] = df["Stok Kodu"].astype(str).str.strip()
            return df
        except: pass
    return pd.DataFrame(columns=["Stok Kodu", "Stok Adı", "Birim"])

def uretim_zaman_yukle():
    if os.path.exists(DOSYA_URETIM_ZAMAN):
        try: 
            df = pd.read_json(DOSYA_URETIM_ZAMAN)
            if not df.empty:
                if "Stok Adı" not in df.columns: df["Stok Adı"] = ""
                if "Birim" not in df.columns: df["Birim"] = "ADET"
            return df
        except: pass
    return pd.DataFrame(columns=["Tarih", "Modül", "Operasyon", "Personel", "Stok Kodu", "Stok Adı", "Birim", "Başlangıç", "Bitiş", "Toplam Süre (Dk)", "Üretilen Adet", "Birim Süre (Dk/Adet)"])

def personelleri_yukle():
    if os.path.exists(DOSYA_PERSONEL):
        try: return pd.read_json(DOSYA_PERSONEL)
        except: pass
    varsayilan_personeller = []
    for i in range(1, 11): varsayilan_personeller.append({"Ad Soyad": f"Kaynak Ustası {i}", "Bölüm": "Kaynak"})
    for i in range(1, 11): varsayilan_personeller.append({"Ad Soyad": f"Montaj Ustası {i}", "Bölüm": "Montaj"})
    return pd.DataFrame(varsayilan_personeller)

def operasyonlari_yukle():
    if os.path.exists(DOSYA_OPERASYON):
        try: return pd.read_json(DOSYA_OPERASYON)
        except: pass
    return pd.DataFrame([
        {"Operasyon Adı": "Gazaltı Kaynak", "Bölüm": "Kaynak"},
        {"Operasyon Adı": "Punta Kaynak", "Bölüm": "Kaynak"},
        {"Operasyon Adı": "Gövde Montajı", "Bölüm": "Montaj"}
    ])

def aktif_islemleri_yukle():
    if os.path.exists(DOSYA_AKTIF):
        try: 
            df = pd.read_json(DOSYA_AKTIF)
            if not df.empty:
                if "Stok Adı" not in df.columns: df["Stok Adı"] = ""
                if "Birim" not in df.columns: df["Birim"] = "ADET"
            return df
        except: pass
    return pd.DataFrame(columns=["Modül", "Operasyon", "Personel", "Stok Kodu", "Stok Adı", "Birim", "Başlangıç"])

def veri_kaydet(df, dosya_adi):
    df.to_json(dosya_adi, orient="records", force_ascii=False)

@st.cache_data
def buyuk_recete_yukle():
    if os.path.exists("veri_dev_receteler.csv"):
        try: return pd.read_csv("veri_dev_receteler.csv", low_memory=False)
        except: pass
    return pd.DataFrame(columns=["Ana Mamül", "Malzeme Kodu", "Malzeme Adı", "Miktar"])

# =========================================================
# 3. OTURUM VE HAFIZA YÖNETİMİ
# =========================================================
if "giriş_yapildi" not in st.session_state: st.session_state["giriş_yapildi"] = False
if "secilen_sirket" not in st.session_state: st.session_state["secilen_sirket"] = None

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

if "stok_df" not in st.session_state: st.session_state["stok_df"] = stoklari_yukle()
if "uretim_zaman_df" not in st.session_state: st.session_state["uretim_zaman_df"] = uretim_zaman_yukle()
if "personel_df" not in st.session_state: st.session_state["personel_df"] = personelleri_yukle()
if "operasyon_df" not in st.session_state: st.session_state["operasyon_df"] = operasyonlari_yukle()
if "aktif_df" not in st.session_state: st.session_state["aktif_df"] = aktif_islemleri_yukle()

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
    menu = st.sidebar.radio("📌 Menü", ["📊 Dashboard & Simülasyon", "📦 Stoklar", "🚚 Sevkiyat"])
else:
    menu = st.sidebar.radio("📌 Menü Seçimi", [
        "📊 Canlı Üretim Dashboard", 
        "📦 Stoklar (Ürün Yönetimi)", # YENİ EKLENDİ
        "📑 Sabit Reçeteler (BOM)", 
        "⚙️ Tanımlamalar (Personel & Operasyon)",
        "⏱️ Üretim Takip (Kaynak)", 
        "⏱️ Üretim Takip (Montaj)", 
        "📋 Üretim (Zaman) Kayıtları"
    ])

# =========================================================
# İLGİ TARIM BÖLÜMLERİ
# =========================================================

# --- 0. CANLI DASHBOARD ---
if menu == "📊 Canlı Üretim Dashboard":
    st.title("📊 Sahadaki Canlı Üretim Durumu")
    col1, col2 = st.columns([4, 1])
    with col1: st.write("Şu anda hatlarda çalışmaya devam eden personeller ve operasyon süreleri.")
    with col2:
        if st.button("🔄 Süreleri Güncelle", type="primary"): st.rerun()

    aktif_df = st.session_state["aktif_df"].copy()
    
    if aktif_df.empty:
        st.info("🎉 Şu anda sahada devam eden aktif bir üretim işlemi bulunmuyor.")
    else:
        simdi = datetime.datetime.now()
        def sure_hesapla(baslangic_str):
            try:
                bas = datetime.datetime.strptime(baslangic_str, "%Y-%m-%d %H:%M:%S")
                fark = simdi - bas
                toplam_dk = int(fark.total_seconds() // 60)
                saat = toplam_dk // 60
                dakika = toplam_dk % 60
                if saat > 0: return f"{saat} saat, {dakika} dk"
                return f"{dakika} dk"
            except: return "Hesaplanamıyor"
                
        aktif_df["Geçen Süre"] = aktif_df["Başlangıç"].apply(sure_hesapla)
        c_kay, c_mon = st.columns(2)
        with c_kay:
            st.markdown("<h3 style='color: #E65100;'>🔥 Aktif Kaynak İşlemleri</h3>", unsafe_allow_html=True)
            kay_df = aktif_df[aktif_df["Modül"] == "Kaynak"][["Personel", "Operasyon", "Stok Kodu", "Stok Adı", "Geçen Süre"]]
            if kay_df.empty: st.success("Kaynak bölümünde aktif işlem yok.")
            else: st.dataframe(kay_df, hide_index=True, use_container_width=True)
        with c_mon:
            st.markdown("<h3 style='color: #0277BD;'>🔧 Aktif Montaj İşlemleri</h3>", unsafe_allow_html=True)
            mon_df = aktif_df[aktif_df["Modül"] == "Montaj"][["Personel", "Operasyon", "Stok Kodu", "Stok Adı", "Geçen Süre"]]
            if mon_df.empty: st.success("Montaj bölümünde aktif işlem yok.")
            else: st.dataframe(mon_df, hide_index=True, use_container_width=True)


# --- YENİ EKLENEN: STOKLAR MODÜLÜ ---
elif menu == "📦 Stoklar (Ürün Yönetimi)":
    st.title("📦 İLGİ TARIM - Stok Kartları Arşivi")
    st.write("Sistemde üretimi yapılacak ürünlerin kod, isim ve birim bilgilerini buradan yönetebilirsiniz.")
    
    with st.expander("📥 Yeni Stok Listesi Yükle / Güncelle (Excel veya CSV)"):
        st.info("💡 Yükleyeceğiniz dosyada sütun isimlerinin şu şekilde olduğundan emin olun: **Stok Kodu | Stok Adı | Birim**")
        yuklenen_dosya = st.file_uploader("Güncel Stok Dosyanızı Seçin", type=["xlsx", "xls", "csv"], key="stok_up")
        if yuklenen_dosya is not None:
            if st.button("💾 Stokları Sisteme Kaydet", type="primary"):
                with st.spinner("Stoklar sisteme aktarılıyor..."):
                    if yuklenen_dosya.name.endswith('.csv'): df_yeni = pd.read_csv(yuklenen_dosya)
                    else: df_yeni = pd.read_excel(yuklenen_dosya)
                    
                    # Olası sütun ismi farklılıklarını düzelt
                    cols = df_yeni.columns.tolist()
                    if "Stok Kodu" not in cols and len(cols) > 0: df_yeni.rename(columns={cols[0]: "Stok Kodu"}, inplace=True)
                    if "Stok Adı" not in cols and len(cols) > 1: df_yeni.rename(columns={cols[1]: "Stok Adı"}, inplace=True)
                    if "Birim" not in cols and len(cols) > 2: df_yeni.rename(columns={cols[2]: "Birim"}, inplace=True)
                    
                    # Boş olanları temizle ve string formatına çevir
                    df_yeni = df_yeni.dropna(subset=["Stok Kodu"])
                    df_yeni["Stok Kodu"] = df_yeni["Stok Kodu"].astype(str).str.strip()
                    if "Stok Adı" not in df_yeni.columns: df_yeni["Stok Adı"] = ""
                    if "Birim" not in df_yeni.columns: df_yeni["Birim"] = "ADET"
                    
                    st.session_state["stok_df"] = df_yeni
                    veri_kaydet(df_yeni, DOSYA_STOK)
                    st.success("✅ Stok arşivi başarıyla güncellendi!")
                    st.rerun()

    st.markdown("---")
    st.write("### Mevcut Stok Listesi (Düzenlenebilir)")
    guncel_stok = st.data_editor(st.session_state["stok_df"], num_rows="dynamic", use_container_width=True)
    if st.button("💾 Tablodaki Değişiklikleri Kaydet"):
        st.session_state["stok_df"] = guncel_stok
        veri_kaydet(guncel_stok, DOSYA_STOK)
        st.success("Değişiklikler kaydedildi!")
        st.rerun()


elif menu == "📑 Sabit Reçeteler (BOM)":
    st.title("📑 İLGİ TARIM - Sabit Üretim Reçeteleri Arşivi")
    with st.expander("📥 Yeni Reçete Dosyası Yükle / Güncelle (Excel veya CSV)"):
        yuklenen_dosya = st.file_uploader("Güncel Reçete Dosyanızı Seçin", type=["xlsx", "xls", "csv"])
        if yuklenen_dosya is not None:
            if st.button("💾 Yüklenen Dosyayı Sisteme Kaydet", type="primary"):
                with st.spinner("Dosya işleniyor..."):
                    if yuklenen_dosya.name.endswith('.csv'): df_yeni = pd.read_csv(yuklenen_dosya)
                    else: df_yeni = pd.read_excel(yuklenen_dosya)
                    df_yeni.to_csv("veri_dev_receteler.csv", index=False)
                    st.cache_data.clear()
                    st.success("Arşiv güncellendi!")
                    st.rerun()

    dev_recete_df = buyuk_recete_yukle()
    if dev_recete_df.empty:
        st.warning("Sistemde henüz reçete bulunmuyor. Lütfen Excel veya CSV dosyanızı yükleyin.")
    else:
        c1, c2 = st.columns([3, 1])
        with c1: aranan_kelime = st.text_input("🔍 Aranacak Ana Mamül veya Malzeme Kodunu Giriniz:")
        with c2: 
            st.write(""); st.write("")
            hepsini_goster = st.checkbox("İlk 1000 satırı göster")

        if aranan_kelime.strip():
            mask = dev_recete_df.astype(str).apply(lambda x: x.str.contains(aranan_kelime, case=False, na=False)).any(axis=1)
            st.dataframe(dev_recete_df[mask], use_container_width=True)
        elif hepsini_goster:
            st.dataframe(dev_recete_df.head(1000), use_container_width=True)


elif menu == "⚙️ Tanımlamalar (Personel & Operasyon)":
    st.title("⚙️ Sistem Tanımlamaları")
    t_per, t_kay, t_mon = st.tabs(["👥 Personel Tanımları", "🔥 Kaynak Operasyonları", "🔧 Montaj Operasyonları"])
    with t_per:
        guncel_per = st.data_editor(st.session_state["personel_df"], num_rows="dynamic", use_container_width=True)
        if st.button("💾 Kaydet", key="btn_per"):
            st.session_state["personel_df"] = guncel_per
            veri_kaydet(guncel_per, DOSYA_PERSONEL)
            st.rerun()
    with t_kay:
        df_kay_op = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Kaynak"].reset_index(drop=True)
        g_kay_op = st.data_editor(df_kay_op, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Kaydet", key="btn_kay"):
            df_diger = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Montaj"]
            st.session_state["operasyon_df"] = pd.concat([df_diger, g_kay_op], ignore_index=True)
            veri_kaydet(st.session_state["operasyon_df"], DOSYA_OPERASYON)
            st.rerun()
    with t_mon:
        df_mon_op = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Montaj"].reset_index(drop=True)
        g_mon_op = st.data_editor(df_mon_op, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Kaydet", key="btn_mon"):
            df_diger = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == "Kaynak"]
            st.session_state["operasyon_df"] = pd.concat([df_diger, g_mon_op], ignore_index=True)
            veri_kaydet(st.session_state["operasyon_df"], DOSYA_OPERASYON)
            st.rerun()


# --- 3. ÜRETİM TAKİP (GÜNCELLENMİŞ STOK SEÇİMİ İLE) ---
elif menu in ["⏱️ Üretim Takip (Kaynak)", "⏱️ Üretim Takip (Montaj)"]:
    islem_tipi = "Kaynak" if "Kaynak" in menu else "Montaj"
    st.title(f"⏱️ {islem_tipi} Üretimi & Zaman Etüdü")
    st.markdown("---")
    
    # 1. BÖLÜM: HALİHAZIRDA ÇALIŞAN (AKTİF) PERSONELLERİ GÖSTER VE BİTİR FORMU
    aktif_modul_df = st.session_state["aktif_df"][st.session_state["aktif_df"]["Modül"] == islem_tipi]
    
    if not aktif_modul_df.empty:
        st.subheader(f"🔄 Devam Eden {islem_tipi} İşlemleri")
        
        for idx, row in aktif_modul_df.iterrows():
            personel = row["Personel"]
            
            with st.container():
                baslama = datetime.datetime.strptime(row["Başlangıç"], "%Y-%m-%d %H:%M:%S")
                gecen_sure = datetime.datetime.now() - baslama
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Çalışan Personel", personel)
                k2.metric("Operasyon", row["Operasyon"])
                k3.metric("İşlenen Ürün", f"{row['Stok Kodu']} - {row['Stok Adı']}")
                k4.metric("Geçen Süre (Dk)", round(gecen_sure.total_seconds() / 60.0, 1))
                
                c_adet, c_btn1, c_btn2 = st.columns([2, 1, 1])
                birim_isim = row.get("Birim", "ADET")
                with c_adet:
                    uretilen_adet = st.number_input(f"Üretilen Miktar ({birim_isim})", min_value=1.0, value=1.0, step=1.0, key=f"adet_{personel}")
                with c_btn1:
                    st.write(""); st.write("")
                    if st.button("⏹️ BİTİR VE KAYDET", key=f"bitir_{personel}", type="primary", use_container_width=True):
                        toplam_dk = round(gecen_sure.total_seconds() / 60.0, 2)
                        birim_dk = round(toplam_dk / uretilen_adet, 2)
                        
                        yeni_arsiv = pd.DataFrame([{
                            "Tarih": datetime.datetime.now().strftime("%d.%m.%Y"),
                            "Modül": islem_tipi,
                            "Operasyon": row["Operasyon"],
                            "Personel": personel,
                            "Stok Kodu": row["Stok Kodu"],
                            "Stok Adı": row["Stok Adı"],
                            "Birim": row["Birim"],
                            "Başlangıç": baslama.strftime("%H:%M:%S"),
                            "Bitiş": datetime.datetime.now().strftime("%H:%M:%S"),
                            "Toplam Süre (Dk)": toplam_dk,
                            "Üretilen Adet": uretilen_adet,
                            "Birim Süre (Dk/Adet)": birim_dk
                        }])
                        
                        st.session_state["uretim_zaman_df"] = pd.concat([st.session_state["uretim_zaman_df"], yeni_arsiv], ignore_index=True)
                        veri_kaydet(st.session_state["uretim_zaman_df"], DOSYA_URETIM_ZAMAN)
                        
                        st.session_state["aktif_df"] = st.session_state["aktif_df"][st.session_state["aktif_df"]["Personel"] != personel]
                        veri_kaydet(st.session_state["aktif_df"], DOSYA_AKTIF)
                        st.rerun()
                with c_btn2:
                    st.write(""); st.write("")
                    if st.button("❌ İptal (Sil)", key=f"sil_{personel}", use_container_width=True):
                        st.session_state["aktif_df"] = st.session_state["aktif_df"][st.session_state["aktif_df"]["Personel"] != personel]
                        veri_kaydet(st.session_state["aktif_df"], DOSYA_AKTIF)
                        st.rerun()
                st.divider()

    # 2. BÖLÜM: YENİ İŞLEM BAŞLATMA EKRANI
    st.subheader("▶️ Yeni İşlem Başlat")
    
    tum_personeller = st.session_state["personel_df"][st.session_state["personel_df"]["Bölüm"] == islem_tipi]["Ad Soyad"].tolist()
    calisan_personeller = st.session_state["aktif_df"]["Personel"].tolist()
    musait_personeller = [p for p in tum_personeller if p not in calisan_personeller]
    
    if not musait_personeller:
        st.info(f"Şu anda {islem_tipi} bölümündeki tüm personeller üretimde.")
    else:
        c1, c2, c3 = st.columns(3)
        ilgili_operasyonlar = st.session_state["operasyon_df"][st.session_state["operasyon_df"]["Bölüm"] == islem_tipi]["Operasyon Adı"].tolist()
        
        # Stokları okunaklı formatta getirme fonksiyonu
        stok_kodlari = st.session_state["stok_df"]["Stok Kodu"].astype(str).tolist()
        def stok_goster(kod):
            if kod == "": return "Seçim Yapınız..."
            satir = st.session_state["stok_df"][st.session_state["stok_df"]["Stok Kodu"] == kod]
            if not satir.empty:
                ad = satir.iloc[0].get("Stok Adı", "")
                return f"{kod} | {ad}"
            return kod

        with c1: secilen_personel = st.selectbox("1. Müsait Personel Seçimi", [""] + musait_personeller)
        with c2: secilen_operasyon = st.selectbox("2. Operasyon Seçimi", [""] + ilgili_operasyonlar)
        with c3: secilen_stok_kodu = st.selectbox("3. Ürün / Stok Seçimi", [""] + stok_kodlari, format_func=stok_goster)
        
        if st.button("BAŞLAT", type="primary", use_container_width=True):
            if secilen_personel == "" or secilen_operasyon == "" or secilen_stok_kodu == "":
                st.error("Lütfen Personel, Operasyon ve Stok seçimlerini eksiksiz yapınız!")
            else:
                # Seçilen stok bilgilerini çek
                secilen_satir = st.session_state["stok_df"][st.session_state["stok_df"]["Stok Kodu"] == secilen_stok_kodu].iloc[0]
                secilen_stok_adi = secilen_satir.get("Stok Adı", "")
                secilen_stok_birim = secilen_satir.get("Birim", "ADET")
                
                yeni_aktif = pd.DataFrame([{
                    "Modül": islem_tipi,
                    "Operasyon": secilen_operasyon,
                    "Personel": secilen_personel,
                    "Stok Kodu": secilen_stok_kodu,
                    "Stok Adı": secilen_stok_adi,
                    "Birim": secilen_stok_birim,
                    "Başlangıç": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                st.session_state["aktif_df"] = pd.concat([st.session_state["aktif_df"], yeni_aktif], ignore_index=True)
                veri_kaydet(st.session_state["aktif_df"], DOSYA_AKTIF)
                st.success("✅ İşlem başarıyla başlatıldı!")
                st.rerun()


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
