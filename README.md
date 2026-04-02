# Excel'den Web Dizini Oluşturucu

Google Sheets üzerindeki bir Excel dosyasını veri kaynağı olarak kullanarak
kategorize edilmiş, statik bir link dizini sitesi üreten Python betiği.

## Ne Yapar?

1. Google Sheets'ten Excel dosyasını indirir
2. Linkleri ve kategorileri okur
3. Hiyerarşik kategori yapısı oluşturur
4. Her kategori ve link için statik HTML sayfaları üretir
5. Sitemap ve JSON API çıktısı oluşturur

Çıktı olarak `docs/` klasörüne tamamen statik bir site üretir. Herhangi bir
sunucuya, veritabanına veya backend'e ihtiyaç duymaz. GitHub Pages, Netlify
veya herhangi bir statik hosting servisiyle çalışır.

## Hızlı Başlangıç

```bash
# 1. Bağımlılıkları kur
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Ayarları yapılandır
cp .env.example .env
# .env dosyasını kendi spreadsheet URL'inle düzenle

# 3. Siteyi oluştur
python rebuild.py
```

Çıktı `docs/` klasörüne yazılır. `docs/index.html` dosyasını tarayıcınızla
açarak sonucu görebilirsiniz.

## Spreadsheet Formatı

Google Sheets dosyanızda iki sayfa olmalı:

### Links Sayfası

| Başlık | URL | Açıklama | Kategori | Tür | Dil | Gönderen | Kaynak | Tarih |
|--------|-----|----------|----------|-----|-----|----------|--------|-------|
| Google | https://google.com | Arama motoru | İnternet > Arama Motorları | website | Türkçe | ali | reddit | 2024-01-01 |

- **Kategori** alanında `>` işareti ile hiyerarşi belirtilir (ör: `Teknoloji > Yazılım > Python`)
- **Tür**: website, makale, uygulama, liste vb.
- **Dil**: İçeriğin dili

### Categories Sayfası (opsiyonel)

| Kategori ID | Özel Başlık | Açıklama |
|-------------|-------------|----------|
| Teknoloji > Yazılım | Yazılım Dünyası | Yazılım geliştirme kaynakları |

Bu sayfa ile kategori başlıklarını ve açıklamalarını özelleştirebilirsiniz.

## Yapılandırma

`.env` dosyasındaki ayarlar:

| Ayar | Açıklama |
|------|----------|
| `SPREADSHEET_URL` | Google Sheets Excel export URL'i |
| `SPREADSHEET_LINKS_PAGE_NAME` | Linkler sayfasının adı |
| `SPREADSHEET_CATEGORIES_PAGE_NAME` | Kategoriler sayfasının adı |
| `SPREADSHEET_CATEGORY_SEPARATOR` | Kategori ayırıcı karakter (varsayılan: `>`) |
| `SITE_TITLE` | Site başlığı |
| `SITE_URL` | Site adresi |
| `SITE_DESC` | Site açıklaması |
| `TIMEZONE_HOURS` | Saat dilimi farkı (UTC'den) |
| `MINIMIZE_CSS` | CSS sıkıştırma (True/False) |
| `MINIMIZE_HTML` | HTML sıkıştırma (True/False) |

## Temalar

`assets/themes/` klasöründe hazır CSS temaları bulunur. Varsayılan tema
"Retro Dark"tır. Kendi temanızı oluşturup aynı klasöre ekleyebilirsiniz.

## Çıktılar

- `docs/index.html` - Ana sayfa (son eklenen 50 link)
- `docs/<kategori>/index.html` - Kategori sayfaları
- `docs/<kategori>/<link>.html` - Link detay sayfaları
- `docs/sitemap.xml` - XML sitemap
- `docs/data.json` - Tüm veriyi içeren JSON API

## Tasarım Felsefesi

- **Basitlik**: Tek bir Python betiği, veritabanı yok, sunucu yok
- **Statik**: Çıktı tamamen statik HTML/CSS, her yerde host edilebilir
- **Veri kaynağı olarak spreadsheet**: Herkes Google Sheets kullanabilir
- **Özelleştirilebilir**: Jinja2 template'leri ve CSS temaları ile
