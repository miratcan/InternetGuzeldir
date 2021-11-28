# Hakkında 

Bana son yıllarda İnternet kocaman bir AVM içerisinde gezmek gibi geliyor. Büyük, parlak, dev gibi resimlerle, yuvarlak köşelerle, bootstrap denen zımbırtının ürettiği birbirinin aynısı iskeletler üzerine yükselen bir yapı.

Görüntüsü güzel, ancak içeriği karın doyurmuyor. Algoritmaların sadece o adres üzerinde daha çok zaman geçirmemiz için seçtiği bomboş içerikler denizi içinde yüzüyoruz. Her gün kendimi dalgın gözlerle instagram ana sayfasını dakikalarca aşağıya kaydırırken buluyorum.

Bu siteyi (eğer varsa) benim gibi hisseden insanlar için yaptım. İçerisinde sadece kendi seçtiğim kategorize edilmiş bağlantıklar var. Çakma DMOZ yapmışsın deseniz alınmam.

Bu linkler çeşitli türlerde olabiliyor: web siteleri, makaleler, online web uygulamaları, online listeler vs gibi. Dil olarak ise Türkçe ve İngilizce içeriklere yer veriyorum.

Her hafta mutlaka bir şeyler ekleniyor. Bookmarklayıp arada bir ziyaret etmenizi tavsiye ederim.

# Sitenin Üretildiği Excell Dosyası

https://docs.google.com/spreadsheets/d/1mK5BycfvwvuPcekTKIMhPKtsRa0EXe-dGeQsvok5wz4/edit?usp=sharing

# Örnek .env Dosyası

```
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXBGnECx6IhFmmeTt6QKLvy3rOvtvmUVaHq_Ubo1mPzWaJu_AfykRrJlurwrd9Ade9S5t7N4Zo2Qpa/pub?output=xlsx"
SPREADSHEET_LINKS_PAGE_NAME = "Bağlantılar"
SPREADSHEET_CATEGORIES_PAGE_NAME = "Kategoriler"
SPREADSHEET_CATEGORY_SEPARATOR = ">"
SPREADSHEET_CATEGORY_COLUMN = 3

SITE_TITLE = "İnternet Güzeldir"
SITE_URL = "https://internetguzeldir.com/"
SITE_DESC = "İnternet'in ne kadar güzel olduğunu hatırlamanızı sağlayacak link dizini"
TWITTER_USERNAME = "internetguzel"
```

# Kurulum

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fetch .env
python3 rebuild.py
```
