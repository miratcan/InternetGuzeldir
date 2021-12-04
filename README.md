Merhaba Yolcu...

Bu ulaştığın sayfa https://internetguzeldir.com'un kaynak kodudur. Basitçe Google Drive üzerinde duran bir Excell dosyasını veri kaynağı olarak kullanarak kategorize edilmiş linkler sitesi üreten bir Python betiğidir. Site geliştirilirken çeşitli prensiplere bağlı kalınmaya çalışılmaktadır:

### Ürün Market Uyumu ya da Gelir Modeli Umursanmamaktadır ###

Geliştirirken keyif alınması, ve insanlara faydalı olması temennisiyle geliştirilen bir projedir. Motivasyonu DM'den atılan teşekkür, "oha ne güzel siteymiş lan" diye atılan tivit ya da "şurayı da ben düzelteyim" diye açılmış Pull Requestlerdir.

### Web 2.0 umursanmamaktadır ###

Kayıt süreçleri, ünlü olma çabaları, puanlamalar, eposta validasyonları gibi şeyle yoktur. Linkler siteye admin tarafından seçilerek konulmakta, kullanıcılar ise bir Google Form üzerinden sadece tavsiye verebilmektedir. Siteyi kullanan kişiler için bu kadar katılımcılık yeterlidir, daha fazlası eklenmeyecektir.

###  Mümkün Olan En Basit Yazılım Teknolojileri Kullanılmaktadır ###

Önyüz düz HTML ve CSS dosyalarından oluşur. Backend tarafında bir sunucu yoktur. Site sadece statik sayfaları inşa eden bir Python betiğinin çıktısıdır. "Abi Couchdb takalım buna" şeklinde açılan PR'ların sahipleri bulunup hızla ve 
yerinde dövülür.

# Yardım ve Yataklık # 

Eğer canınız istiyorsa bu sitenin yapımında faydalı olabileceğiniz bir çok konu mevcut:

 - Var olan, problemli linkleri, imla hatalarını, seo dostu olmayan açıklama metinlerini link detay sayfalarındaki yorum alanını raporlayabilirsiniz. (Örnek)
 - Yukarıdaki türde olmayan herhangi bir hata ya da iyileştirme önerisi görürseniz issues sayfasından paylaşabilirsiniz.
 - Siteden bahsedebilir, forumlarda, blogunuzda, Facebook sayfalarında paylaşabilirsiniz. 
 - HTML/CSS/Tasarım bilginiz varsa site için userspots.com adresi üzerinde çeşitli temalar hazırlayabilirsiniz. (*)
 - Tavsiye formunu kullanarak eklenmesi gerektiğini düşündüğünüz linkleri bildirebilirsiniz.
 - HTML/CSS/Python bilginiz varsa issues bölümüne gidip yapılmayı bekleyen işeri yapıp pull request açabilirsiniz. (Projenin nasıl çalıştırılacağı aşağıda anlatılacaktır)

\*: Kimileri açık renkler istiyor, kimisi daha modern bir tasarım istiyor, kimisi daha büyük fontlar istiyor. Herkesi memnun edebildiğim bir formül çıkamadı. Userspots üzerinde hazırlanacak temalar bu işi çözer diye düşünüyorum.

# Projenin Çalıştırılması #

## Bağımlılıkların Kurulması ##

Proje aslında rebuild.py'nin çalıştırılmasından ibarettir. Bu dosya Python 3.9 ile çalışabilmekte ve çeşitli harici kütüphanelere ihtiyaç duymaktadır. Proje dizinine gidip venv adında bir virtual environment oluşturup requirements.txt dosyası içerisindeki bağımlılıkları yükleyebilirsiniz.

    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt

> Eğer virtual environment nedir bilmiyorsanız ağlayarak günlüğünüze yazabilir, musluğu açıp suya anlatabilir ya da [kısa bir araştırma yaparak](https://letmegooglethat.com/?q=python+virtual+environment+nedir) konuyu öğrenebilirsiniz)

> Eğer Windows kullanıcısı iseniz rcssmin kütüphanesinin kurulamadığını görmeniz muhtemel. Bu kütüphane CSS dosyalarının minify edilmesi için kullanılmakta ve aslında opsiyonel bir kütüphane. Kurulamamış olması bir sorun olacağı anlamına gelmiyor.

## Ayarlar Dosyasinin Yazılması ## 

İnşa edici betiğin çalıştırılabilmesi için proje klasörü içerisinde bir .env dosyasının bulunması gerekmekte. Bu dosyayı aşağıdaki komutu uygulayarak elde edebilirsiniz:

    $ cp .env.example .env

## İnşa Edici Betiğin Çalıştırılması ## 

Yukarıdaki işlemleri başarıyla uygulayabildi iseniz aşağıdaki komutu çalıştırabilmeniz gerekli:

    $ python3 rebuild.py

Bu betik çıktı olarak aşağıdaki gibi bir sonuç gösterecek, ve docs klasörü altına siteyi inşa edecektir:

    $ python rebuild.py
    2021-12-04 19:08:00,197 INFO - Building category information.
    2021-12-04 19:08:00,213 INFO - Building json output.
    2021-12-04 19:08:00,218 INFO - Building assets.
    2021-12-04 19:08:00,226 INFO - Rendering categories.
    2021-12-04 19:08:00,310 INFO - Rendering links.
    2021-12-04 19:08:00,560 INFO - Rendering homepage.
    2021-12-04 19:08:00,572 INFO - Rendering sitemap.
    2021-12-04 19:08:00,595 INFO - Rendering feed outputs.
    $ 

docs klasörü altındaki index.html dosyasını internet tarayıcınız ile açtığınızda çıktı olarak internetgüzelir.com'un bir kopyasını görüyor olacaksınız.

## Ortaya Çıkış Hikayesi ## 

Aşağıda siteyi internet ortamlarına fırlattığım ilk gün yazdığım gereksiz duygusal tonda bir yazı var. Direkt okubeni dosyasında olması gereken bir şey değil fakat yine de hikayeyi aşağı yukarı anlatıyor:

----

Bana son yıllarda İnternet kocaman bir AVM içerisinde gezmek gibi geliyor. Büyük, parlak, dev gibi resimlerle, yuvarlak köşelerle, bootstrap denen zımbırtının ürettiği birbirinin aynısı iskeletler üzerine yükselen bir yapı.

Görüntüsü güzel, ancak içeriği karın doyurmuyor. Algoritmaların sadece o adres üzerinde daha çok zaman geçirmemiz için seçtiği bomboş içerikler denizi içinde yüzüyoruz. Her gün kendimi dalgın gözlerle instagram ana sayfasını dakikalarca aşağıya kaydırırken buluyorum.

Bu siteyi (eğer varsa) benim gibi hisseden insanlar için yaptım. İçerisinde sadece kendi seçtiğim kategorize edilmiş bağlantıklar var. Çakma DMOZ yapmışsın deseniz alınmam.

Bu linkler çeşitli türlerde olabiliyor: web siteleri, makaleler, online web uygulamaları, online listeler vs gibi. Dil olarak ise Türkçe ve İngilizce içeriklere yer veriyorum.

Her hafta mutlaka bir şeyler ekleniyor. Bookmarklayıp arada bir ziyaret etmenizi tavsiye ederim.
