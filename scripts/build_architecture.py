"""Deep-dive architecture & decision document (Turkish) -> docs/architecture.html

Tables are generated from the code/config (src.sfc, src.v2.features, experiments/v2/env_main.json,
docs/worked_example.json) so the document cannot drift from the implementation.
Usage: python -m scripts.make_arch_figures && python -m scripts.worked_example && python -m scripts.build_architecture
"""
import base64
import json
import subprocess

from src.sfc import SFC_BANDWIDTH, SFC_CATALOG, SFC_CODES, VNF_REQUIREMENTS
from src.v2.environment import VNF_FAMILY
from src.v2.features import CANDIDATE_FEATURES, STATE_FEATURES

OUT = 'docs/architecture.html'
ENV = json.load(open('experiments/v2/env_main.json'))
EX = json.load(open('docs/worked_example.json'))
TM = json.load(open('results/v2/main/training_metrics.json'))


def img(name, alt):
    b = base64.b64encode(open(f'figures/{name}.png', 'rb').read()).decode()
    return f'<img src="data:image/png;base64,{b}" alt="{alt}">'


def rows(r):
    return ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in r)


def table(head, body, cls='t'):
    return f'<table class="{cls}"><thead><tr>' + ''.join(f'<th>{h}</th>' for h in head) + f'</tr></thead><tbody>{rows(body)}</tbody></table>'


FEATURE_DOC = {
    'sfc_type_encoded': 'SFC tipi (Video=0, VoIP=1, Web=2)',
    'packets': 'isteğin 20 sn\'lik paket sayısı (ingress\'te ölçülebilir)',
    'flows': 'isteğin akış sayısı (ingress\'te ölçülebilir)',
    'n_hosts': 'adayın kullandığı farklı düğüm sayısı',
    'rho_max_hosts': 'seçilen düğümlerin ölçülen kullanımının (ρ) en büyüğü',
    'rho_mean_hosts': 'seçilen farklı düğümlerin ρ ortalaması',
    'cpu_res_max_host': 'bu SFC\'nin tek bir düğüme koyduğu en büyük CPU rezervasyonu',
    'cpu_res_sum': 'bu SFC\'nin toplam CPU rezervasyonu (tipe göre sabit)',
    'vnf_max_host': 'tek bir düğüme düşen en fazla VNF sayısı',
    'net_rho_mean': 'ağ genelinde ortalama ρ',
    'net_free_cpu': 'ağ genelinde boş CPU (rezervasyona göre)',
    'net_free_cpu ': '',
    'max_node_free_cpu': 'en boş düğümün boş CPU\'su',
    'min_free_bw': 'en dolu linkin boş bant genişliği',
}


def sfc_table():
    body = []
    for t, chain in SFC_CATALOG.items():
        for i, v in enumerate(chain):
            body.append([t if i == 0 else '', SFC_BANDWIDTH[t] if i == 0 else '', SFC_CODES[t] if i == 0 else '', v,
                         VNF_REQUIREMENTS[v]['cpu'], VNF_REQUIREMENTS[v]['ram'], ENV['service_ms'][v], VNF_FAMILY[v]])
    return table(['SFC', 'BW (Mbps)', 'kod', 'VNF (sırayla)', 'CPU rez.', 'RAM rez.', 's<sub>v</sub> (ms)', 'ölçüm ailesi'], body)


def example_table():
    best_true = min(c['true_total'] for c in EX['candidates'])
    best_kdn = min(c['kdn_score'] for c in EX['candidates'])
    best_prop = min(c['prop_ms'] for c in EX['candidates'])
    body = []
    for c in EX['candidates']:
        tags = []
        if c['kdn_score'] == best_kdn: tags.append('<b>KDN-v2 seçer</b>')
        if c['true_total'] == best_true: tags.append('<b>Oracle seçer</b>')
        if c['prop_ms'] == best_prop: tags.append('cands-prop seçer')
        if c['hosts'] == EX['smart_v2_choice']: tags.append('= Smart-v2')
        short = lambda n: n.replace('ng', '')
        body.append([c['generator'], ' → '.join(short(h) for h in c['hosts']), f"{c['prop_ms']:.2f}", f"{c['pred_proc_ms']:.2f}",
                     f"{c['kdn_score']:.2f}", f"{c['true_proc_ms']:.2f}", f"{c['true_total']:.2f}", ', '.join(tags)])
    return table(['üreteç', 'VNF yerleşimi', 'yayılım (bilinen)', 'tahmini işleme', 'KDN skoru', 'gerçek işleme (gizli)',
                  'gerçek toplam', 'kim seçer?'], body)


def svg_pipeline():
    box = lambda x, y, w, h, t, sub='', fill='#ffffff', stroke='#9a9893': (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>'
        f'<text x="{x + w / 2}" y="{y + (22 if sub else h / 2 + 5)}" text-anchor="middle" font-weight="600" font-size="13">{t}</text>'
        + (f'<text x="{x + w / 2}" y="{y + 40}" text-anchor="middle" font-size="11" fill="#52514e">{sub}</text>' if sub else ''))
    arrow = lambda x1, y1, x2, y2, label='': (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#52514e" stroke-width="1.5" marker-end="url(#a)"/>'
        + (f'<text x="{(x1 + x2) / 2 + 4}" y="{(y1 + y2) / 2 - 4}" font-size="10.5" fill="#52514e">{label}</text>' if label else ''))
    s = ['<svg viewBox="0 0 900 445" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,Roboto,Arial">',
         '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>']
    s += [box(10, 10, 200, 52, 'SNDlib Abilene', 'topoloji, koordinat, kapasite', '#f3f2ef'),
          box(10, 80, 200, 52, 'Abilene TM (Zhang 2004)', '48 096 × 5 dk, 12×12 OD', '#f3f2ef'),
          box(10, 150, 200, 52, 'KDN VNF ölçümleri', 'Snort / Firewall / OVS CPU', '#f3f2ef'),
          box(270, 40, 200, 130, 'V2World', ' ', '#eef4fc', '#2a78d6'),
          '<text x="370" y="85" text-anchor="middle" font-size="11" fill="#52514e">graph (gecikme, kapasite)</text>'
          '<text x="370" y="103" text-anchor="middle" font-size="11" fill="#52514e">schedule(split, seed, λ)</text>'
          '<text x="370" y="121" text-anchor="middle" font-size="11" fill="#52514e">gizli r (k-NN), s_v/(1−ρ)</text>'
          '<text x="370" y="139" text-anchor="middle" font-size="11" fill="#52514e">true_latency()</text>',
          box(530, 40, 170, 130, 'V2Simulation', ' ', '#ffffff', '#52514e'),
          '<text x="615" y="85" text-anchor="middle" font-size="11" fill="#52514e">SimPy olay döngüsü</text>'
          '<text x="615" y="103" text-anchor="middle" font-size="11" fill="#52514e">place → commit</text>'
          '<text x="615" y="121" text-anchor="middle" font-size="11" fill="#52514e">yük ekle / süre sonu</text>'
          '<text x="615" y="139" text-anchor="middle" font-size="11" fill="#52514e">release (yük çıkar)</text>',
          box(740, 40, 150, 130, 'Politika', ' ', '#fff6ef', '#eb6834'),
          '<text x="815" y="85" text-anchor="middle" font-size="11" fill="#52514e">place(graph, req)</text>'
          '<text x="815" y="103" text-anchor="middle" font-size="11" fill="#52514e">→ PlacementResult</text>'
          '<text x="815" y="121" text-anchor="middle" font-size="11" fill="#52514e">grafiği DEĞİŞTİRMEZ</text>',
          arrow(210, 36, 268, 70), arrow(210, 106, 268, 106), arrow(210, 176, 268, 140),
          arrow(470, 105, 528, 105), arrow(700, 90, 738, 90, ''), arrow(738, 130, 702, 130, ''),
          box(530, 250, 170, 60, 'Telemetri', 'özellikler + ölçülen gecikme', '#ffffff'),
          box(740, 250, 150, 60, 'XGBoost eğitimi', 'models/v2/kdn2_regressor', '#effaf5', '#1baf7a'),
          box(270, 250, 200, 60, 'RequestRecord', 'kabul, gecikme, karar süresi', '#ffffff'),
          box(270, 370, 200, 60, 'runs.csv / summary', 'seed × λ × politika', '#ffffff'),
          box(530, 370, 170, 60, 'analysis', 'Wilcoxon, Holm, %95 GA', '#ffffff'),
          arrow(640, 172, 640, 248), '<text x="646" y="215" font-size="10.5" fill="#52514e">train: observer</text>',
          '<polyline points="580,172 580,212 370,212 370,246" fill="none" stroke="#52514e" stroke-width="1.5" marker-end="url(#a)"/>',
          '<text x="378" y="206" font-size="10.5" fill="#52514e">test: her istek</text>',
          arrow(700, 280, 738, 280), arrow(815, 248, 815, 172), '<text x="821" y="215" font-size="10.5" fill="#52514e">KDN-v2 yükler</text>',
          arrow(370, 312, 370, 368), arrow(470, 400, 528, 400),
          '<text x="10" y="262" font-size="12" font-weight="600" fill="#2a78d6">Knowledge plane</text>'
          '<text x="10" y="280" font-size="11" fill="#52514e">telemetri → eğitim → model</text>'
          '<text x="10" y="322" font-size="12" font-weight="600" fill="#eb6834">Control plane</text>'
          '<text x="10" y="340" font-size="11" fill="#52514e">politika + simülasyon motoru</text>'
          '<text x="10" y="382" font-size="12" font-weight="600" fill="#52514e">Data plane</text>'
          '<text x="10" y="400" font-size="11" fill="#52514e">graph: CPU/RAM/BW + gerçek yük</text>',
          '</svg>']
    return ''.join(s)


DECISIONS = [
    # (alan, karar, neden, alternatif / risk)
    ('Simülasyon', 'SimPy ile ayrık olay simülasyonu', 'SFC\'ler gelir, süre boyunca kaynak tutar, bırakır. Bu doğal olarak olay tabanlı; zamanı adım adım ilerletmek gereksiz.', 'Emülasyon (Mininet) gerçekçi ama yavaş; seed × λ gridi için uygun değil.'),
    ('Simülasyon', 'Trafik önceden üretilir (schedule), her politika aynı istek dizisini görür', 'Common random numbers: farklar politikadan gelir, şanstan değil. Seed başına eşleştirilmiş test yapmayı mümkün kılar.', 'Canlı örnekleme varyansı artırır, karşılaştırmayı zayıflatır.'),
    ('Simülasyon', 'Politikalar grafiği değiştirmez; commit ve release motorda', 'v1\'de her algoritma kendi rollback\'ini yazıyordu (4 kopya). Tek yerde kaynak muhasebesi hata riskini azaltır; testlerle korunuyor.', '—'),
    ('Simülasyon', 'Aday denemesi için kopyasız ResourceState overlay', 'Aday başına grafiği kopyalamak yavaş; overlay sadece geçici rezervasyonları tutar.', '—'),
    ('Protokol', 'Ufuk 10 000 t.u., warm-up 1 200 t.u. atılır', 'Maks. SFC süresi 600 t.u.; 2×600 sonra sistem durağan rejime yaklaşır. v1\'de 1000 t.u. çok kısaydı.', 'Daha uzun ufuk istatistiği iyileştirir ama gereksiz.'),
    ('Protokol', 'λ ∈ {0.02, 0.05, 0.1, 0.2, 0.4}', 'Kabul oranı ~%100\'den ~%27\'ye kadar tüm rejimleri kapsar; v1 sadece aşırı yükte (λ=0.2) bakıyordu.', '—'),
    ('Protokol', '30 seed, eşleştirilmiş Wilcoxon, Holm düzeltmesi, %95 t-GA', 'Dağılım normal varsayılamaz; aynı trafik üzerinde fark testi güçlü. 5 λ için çoklu test düzeltmesi gerekli.', 'Paired t-test de verilebilir; sonuç değişmez.'),
    ('Metrik', 'CPU ağırlıklı kabul (istek sayısının yanında)', 'v1\'de gatekeeper büyük Video\'ları reddederek sayıyı artırıyordu; taşınan yükü ölçmek için.', 'Gelir ağırlıklı (revenue) kabul de olabilirdi.'),
    ('Metrik', 'Gecikme sadece kabul edilenler üzerinden; kurulum anında ölçülür', 'Reddedilen isteğin gecikmesi yok; kurulum anı karar anına bağlı tek tanımlı büyüklük.', 'Survivor bias: daha az kabul eden daha düşük gecikme gösterebilir. Bu yüzden kabul de birlikte raporlanıyor.'),
    ('Topoloji', 'SNDlib Abilene (v1\'in elle kurulmuş topolojisi yerine)', 'Literatürde kabul görmüş ve atıf yapılabilir; trafik matrisleriyle aynı düğüm adları.', '—'),
    ('Topoloji', 'Gecikme = coğrafi mesafe × 5 µs/km; rota şişirme yok', 'Işık fiberde ~2×10⁸ m/s. Basit ve savunulabilir; v1\'deki rastgele 2–10 ms gecikmenin yerine.', 'Gerçek fiber yolu daha uzun; mutlak değerler alt sınır.'),
    ('Topoloji', 'Link kapasitesi SNDlib / 9.92 (9920→1000, 2480→250 Mbps)', 'v1\'in 10/20/50 Mbps SFC talepleriyle linkler doygunluğa ulaşabilsin, oranlar korunsun.', 'Ölçek bir seçim; asıl darboğaz zaten CPU.'),
    ('Topoloji', 'Düğüm başına 100 CPU / 100 RAM (v1 ile aynı)', 'SNDlib\'de hesaplama kapasitesi verisi yok.', 'Heterojen düğümler daha ilginç olurdu (gelecek iş).'),
    ('Yönlendirme', 'Gecikme ağırlıklı en kısa yol, önceden hesaplanmış; BW sadece o yolda kontrol', 'Hızlı (tüm çiftler bir kez); v1\'deki hop-sayısı yönlendirmesi "gecikme farkında" değildi.', 'BW-farkında alternatif yol aranmıyor (k-shortest gelecek iş).'),
    ('Trafik', '1 TM aralığı (5 dk) = 30 t.u.; 10 000 t.u. ≈ 28 saat', 'Bir koşu günlük döngüyü (diurnal) kapsasın. SFC süreleri (10–600 t.u.) ile uyumlu.', 'Zaman sıkıştırması gerçek süre değil; t.u. soyut birim.'),
    ('Trafik', 'Homojen olmayan Poisson, thinning ile', 'Varış oranı gerçek toplam hacmi izler; thinning, değişken oranlı Poisson için standart ve tam yöntem.', '—'),
    ('Trafik', 'Ingress/egress ∝ o anki OD hacmi', 'Gerçek trafik dengesiz (en yoğun çift %5.5); uç noktaların yeri yerleşimi etkiler.', '—'),
    ('Trafik', 'Train = Mart–Haziran, test = Temmuz–Eylül', 'Zamansal ayrım: model gelecekteki trafiğe genelleşmeli; rastgele bölme sızıntı yaratır (v1\'de gördük).', '—'),
    ('Gizli model', 'VNF yükü KDN ölçümlerinden k-NN (k=5) ile, aile medyanına bölünmüş', 'Parametrik form dayatmadan ölçülen doğrusal olmama ve gürültüyü korur. CPU birimi belirtilmediği için medyana göre normalize.', 'Paket sayıları dar aralıkta toplandığı için r ≈ 1 (0.87–1.15). Bu zayıflık aşağıda tartışılıyor.'),
    ('Gizli model', 'VNF → ölçüm ailesi eşlemesi (tabloda)', 'Sadece üç ölçülmüş VNF var; işlevce en yakın olan seçildi.', 'Transcoder/SBC için gerçek ölçüm yok; yaklaşık.'),
    ('Gizli model', 'Paket tercile göre SFC tipi (Web düşük, Video yüksek)', 'Video\'nun daha yoğun trafik taşıması mantıklı; tip ile yük arasında ilişki kurar.', '—'),
    ('Gizli model', 'Yük = u0 · CPU rezervasyonu · r, u0 = 0.6', 'Gerçek kullanım rezervasyondan farklıdır (overprovisioning); u0 bunu temsil eder.', 'u0 seçim → duyarlılıkta 0.4 ve 0.8 denendi.'),
    ('Gizli model', 'İşleme gecikmesi s_v / (1 − min(ρ, 0.95))', 'M/M/1 kuyruk modelinin şekli: yük arttıkça doğrusal olmayan artış. 0.95 sınırı sonsuzluğu önler.', 'Form seçim → duyarlılıkta doğrusal fonksiyon denendi.'),
    ('Gizli model', 'Kabul kararı rezervasyona göre (gerçek yüke göre değil)', 'Gerçek orkestratörler (ör. OpenStack/K8s) rezervasyonla kabul eder; gerçek yük telemetriyle görünür.', 'Bu yüzden ρ ≤ ~0.6 kalıyor. Kuyruk gecikmesi patlamıyor.'),
    ('Politika', 'Aday kümesi: Smart(α=0,2,10,50), least-util, colocate, 2 rastgele', 'v1 dersi: seçici, kümede olmayanı bulamaz. Güçlü ve çeşitli adaylar, KDN\'e en az heuristic kadar iyi olma şansı verir.', 'Küme hâlâ el yapımı; daha zengin üretim (ör. arama) gelecek iş.'),
    ('Öğrenme', 'Regressor sadece işleme gecikmesini öğrenir; yayılım bilinen olarak eklenir', 'v1\'in temel hatasını düzeltir: bilineni öğrenmeye çalışmamak (residual learning).', '—'),
    ('Öğrenme', 'Özellikler sadece gözlenebilir büyüklükler; fonksiyon formu kodlanmaz', '1/(1−ρ) gibi bir özellik eklemek gizli modeli sızdırmak olurdu.', 'Özet özellikler aynı özetli iki adayı ayırt edemez (örnekte görülüyor).'),
    ('Öğrenme', 'Veri davranış politikasıyla: adaylar arasından rastgele seçim', 'Kapsam: her aday türü için örnek. v1\'de sadece Greedy verisi vardı (bias).', 'Dağıtılan politika farklı dağılım görür (kapalı döngü = 4B).'),
    ('Öğrenme', 'XGBoost, v1 ile aynı hiperparametreler, ayar yok', 'Tablo verisi için güçlü ve hızlı. Hiperparametre ayarı yapmamak test sızıntısını önler ve v1 ile karşılaştırılabilir kılar.', 'GNN/RouteNet topolojiden bağımsız olurdu (gelecek iş).'),
    ('Baseline', 'Smart-load(α): α train\'de grid ile ayarlandı (α* = 10)', '"Elle ayar gerektirmeyen" iddiasının dürüst sınavı: eşit bütçeyle ayarlanmış heuristic.', '—'),
    ('Baseline', 'Oracle = aynı adaylar arasında gerçek gecikmesi en düşük olan', 'Seçici için üst sınır; öğrenme hatasını yerleşim hatasından ayırır.', 'Global optimum değil, o da miyop.'),
    ('Etik', 'Ön kayıt + sapma listesi + keşif etiketi', 'v2 tasarımı v1 sonuçları görüldükten sonra yapıldı; seçici raporlamayı önlemek için.', '—'),
]

QA = [
    ('Ortamı ML kazansın diye mi kurdunuz?',
     'Riski kabul ediyoruz ve üç önlem aldık. (1) Parametreler public verilerden geliyor: SNDlib, Abilene TM, KDN ölçümleri. (2) Protokol, model eğitilmeden önce commit\'lendi (48e6edb). (3) Ayarlanmış bir heuristic ve oracle ile karşılaştırdık. Sonuç zaten ML lehine "temiz" çıkmadı: ağır yükte heuristic\'ler kazanıyor. Bunu da raporluyoruz.'),
    ('Oracle nedir, neden ağır yükte Smart\'tan kötü?',
     'Oracle, KDN ile aynı aday kümesine bakar ama tahmin yerine gerçek gecikmeyi (gizli r ve gerçek fonksiyon) kullanır; seçici için üst sınırdır. Global optimum değildir: sadece o anki isteğin kurulum gecikmesini minimize eder (miyop). Ağır yükte bu tercih, sonraki isteklerin karşılaşacağı durumu kötüleştiriyor. Smart\'ın tutarlı konsolidasyonu uzun vadede daha iyi.'),
    ('Smart kuralı tam olarak ne?',
     'Her VNF için sırayla, uygun düğümler arasında skoru en düşük olan seçilir. Skor = önceki noktadan yol gecikmesi (ilk VNF için ingress\'ten) + 1000·[düğüm boşta] + α·ρ_düğüm + (son VNF ise) düğümden egress\'e gecikme. 1000\'lik "uyandırma cezası" v1\'den geliyor ve enerji tasarrufu için açık düğümlere konsolide eder (ElasticTree fikri). α=0 Smart-v2, α=10 ayarlanmış Smart-load. Eşitlikte sabit düğüm sırası kazanır.'),
    ('R² 0.994 şüpheli değil mi? Sızıntı var mı?',
     'Doğrulama, eğitimde kullanılmayan seed\'lerde yapıldı; test ise farklı aylarda. Yüksek R²\'nin asıl nedeni "gizli" bileşenin pek gizli olmaması: r ≈ 1 olduğu için yük ≈ 0.6 × rezervasyon, ve rezervasyonlar özelliklerde var. Bu bir sızıntı değil ama ortamın zayıflığı; öğrenmenin katkısının küçük (0.2–0.5 ms) olmasının da sebebi.'),
    ('Öğrenmenin katkısı bu kadar küçükse KDN ne işe yarıyor?',
     'Ölçtüğümüz şey tam olarak bu. Aynı adaylar, sadece bilinen yayılım gecikmesiyle seçildiğinde (cands-prop) KDN\'den 0.2–0.5 ms kötü. Yani öğrenme ölçülebilir ama küçük bir değer katıyor. Büyük kazanç aday kümesinden geliyor. Makalenin dürüst mesajı bu: "KDN gizli davranışı öğrenebiliyor, ama kazancın büyüklüğü ortamın öğrenilecek ne kadar bilgi barındırdığına ve karar hedefine bağlı."'),
    ('Neden RL değil?',
     'RL uzun vadeli hedefle miyopluğu çözebilir. Ama örnek verimliliği, ayar maliyeti ve tekrar üretilebilirliği bu kapsam için ağır. Sonuçlarımız RL\'nin nerede gerekli olduğunu gösteriyor (ağır yük): Future Work\'ün gerekçesi bu.'),
    ('Neden XGBoost, neden GNN değil?',
     'Özellikler tablo biçiminde ve sabit boyutlu; XGBoost hızlı, güçlü ve v1 ile karşılaştırılabilir. GNN topolojiden bağımsız genelleme için gerekli olurdu, ama tek topolojide bu avantaj ölçülemez.'),
    ('2004 trafiği bugün için anlamlı mı?',
     'Mutlak hacimler değil, zamansal profil (günlük döngü) ve OD dengesizliği kullanılıyor; hacim λ ile ölçekleniyor. Abilene TM, yönlendirme ve trafik mühendisliği literatüründe standart bir benchmark.'),
    ('t.u. nedir? 30 t.u. = 5 dakika ne demek?',
     't.u. soyut zaman birimi. SFC süresi 10–600 t.u. ve 5 dakikalık bir TM aralığı 30 t.u.\'ya eşlendi; böylece bir koşu ~28 saatlik gerçek trafik profilini kapsıyor. Saniye değil; ölçek bir modelleme seçimi.'),
    ('Neden gecikme sadece kurulum anında ölçülüyor?',
     'Karar anına bağlı, iyi tanımlı tek büyüklük o. SFC ömrü boyunca ortalama gecikme daha gerçekçi olurdu ama sonraki kararlara bağlı olduğu için atfetmek zorlaşır. Bu bir sınırlama ve Discussion\'da var.'),
    ('Gatekeeper neden v2 ana yönteminde yok?',
     'v1\'de "kazanç" sayım artefaktıydı (CPU ağırlıklı kabulde zararlı). v2\'de ablasyon olarak duruyor: ağır yükte gecikmeyi 0.9–1.5 ms düşürüyor, CPU ağırlıklı kabulü 0.1–0.3 pp azaltıyor. Yani kabul–gecikme ödünleşimi yapıyor, bedava kazanç değil.'),
    ('v1 projesine göre ne değişti?',
     'Kod: test edilebilir tek bir yerleştirme çekirdeği, 39 test, v1\'i birebir koruyan regresyon testi. Yöntem: bilinenin değil gizlinin öğrenilmesi, gerçek topoloji ve trafik, ölçüme dayalı VNF davranışı, ön kayıt, ayarlanmış baseline ve oracle. Değerlendirme: 30 seed × 5 λ, CPU ağırlıklı kabul, eşleştirilmiş testler.'),
    ('Sonuçlar tekrar üretilebilir mi?',
     'Evet: fetch_data.sh (SHA256 doğrulamalı) → run_all.sh → scripts.v2 alt komutları. Tüm seed\'ler sabit; v1 sayıları orijinal kodla seed bazında birebir aynı çıkıyor (regresyon testi).'),
    ('En büyük zayıflığınız ne?',
     'Gizli bileşenin varyansı düşük (r ≈ 1, ρ ≤ 0.6): öğrenme için alan dar. Tek topoloji. VNF-ölçüm eşlemesi yaklaşık. Kurulum anı gecikmesi. Bunların hepsi makalede "threats to validity" altında.'),
]


def build():
    head = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
    cand_feat = table(['#', 'özellik', 'anlamı'], [[i + 1, f'<code>{f}</code>', FEATURE_DOC.get(f, '')] for i, f in enumerate(CANDIDATE_FEATURES)])
    state_feat = table(['#', 'özellik', 'anlamı'], [[i + 1, f'<code>{f}</code>', FEATURE_DOC.get(f, '')] for i, f in enumerate(STATE_FEATURES)])
    dec = table(['#', 'alan', 'karar', 'neden', 'alternatif / risk'], [[i + 1, a, b, c, d] for i, (a, b, c, d) in enumerate(DECISIONS)])
    qa = ''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in QA)
    ex = EX
    rho_txt = ', '.join(f"{k.replace('ng', '')}={max(v, 0.0):.2f}" for k, v in ex['node_rho'].items())

    html = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mimari ve karar dokümanı: KDN tabanlı VNF yerleştirme</title>
<style>
:root {{ --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --rule:#e4e3df; --blue:#2a78d6; --orange:#eb6834; --aqua:#1baf7a; --violet:#6250d6; }}
body {{ background:var(--surface); color:var(--ink); font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; margin:0; }}
main {{ max-width:1000px; margin:0 auto; padding:32px 24px 80px; }}
h1 {{ font-size:26px; line-height:1.25; margin:0 0 6px; }} h2 {{ font-size:20px; margin:42px 0 10px; padding-top:12px; border-top:1px solid var(--rule); }}
h3 {{ font-size:16px; margin:24px 0 6px; }} .meta {{ color:var(--ink2); font-size:13px; }}
figure {{ margin:16px 0 22px; }} figure img {{ max-width:100%; border:1px solid var(--rule); border-radius:6px; }}
figcaption {{ color:var(--ink2); font-size:13px; margin-top:6px; }}
table.t {{ border-collapse:collapse; font-size:13px; margin:10px 0 18px; width:100%; }}
table.t th, table.t td {{ border-bottom:1px solid var(--rule); padding:5px 8px; text-align:left; vertical-align:top; }}
table.t thead th {{ color:var(--ink2); font-weight:600; }}
.box {{ border-radius:4px; padding:10px 16px; margin:12px 0; }}
.info {{ background:#f3f2ef; border-left:4px solid var(--blue); }} .warn {{ background:#fff6ef; border-left:4px solid var(--orange); }}
.ok {{ background:#effaf5; border-left:4px solid var(--aqua); }}
code {{ background:#f0efec; padding:1px 4px; border-radius:3px; font-size:13px; }}
pre {{ background:#f0efec; padding:10px 14px; border-radius:6px; overflow:auto; font-size:12.5px; line-height:1.45; }}
.eq {{ font-family:Cambria,Georgia,serif; font-size:16px; background:#f7f6f3; padding:8px 14px; border-radius:6px; margin:8px 0; }}
details {{ border-bottom:1px solid var(--rule); padding:8px 0; }} summary {{ cursor:pointer; font-weight:600; }}
nav ol {{ columns:2; font-size:14px; }} .small {{ font-size:13px; color:var(--ink2); }}
</style></head><body><main>
<h1>Mimari ve karar dokümanı: KDN tabanlı VNF yerleştirme</h1>
<div class="meta">Jüriye hazırlık için derinlemesine anlatım · branch <code>faz-4-v2</code> @ <code>{head}</code> · tablolar koddan ve config'ten otomatik üretildi</div>
<nav><ol>
<li><a href="#s1">Tek paragrafta proje</a></li><li><a href="#s2">Genel mimari</a></li><li><a href="#s3">Kod haritası</a></li>
<li><a href="#s4">Simülasyon çekirdeği</a></li><li><a href="#s5">Veri setleri</a></li><li><a href="#s6">SFC/VNF kataloğu</a></li>
<li><a href="#s7">Gizli VNF modeli</a></li><li><a href="#s8">Politikalar (Smart, Oracle, KDN…)</a></li>
<li><a href="#s9">Somut bir karar örneği</a></li><li><a href="#s10">Öğrenme hattı</a></li><li><a href="#s11">Deney protokolü ve istatistik</a></li>
<li><a href="#s12">Karar günlüğü</a></li><li><a href="#s13">Bilinen zayıflıklar</a></li><li><a href="#s14">Jüri soru–cevap</a></li>
<li><a href="#s15">Akademik katkı ve yayın değerlendirmesi</a></li>
</ol></nav>

<h2 id="s1">1. Tek paragrafta proje</h2>
<p>Bir <b>SFC</b> (Service Function Chain), trafiğin sırayla geçmesi gereken sanal ağ fonksiyonlarından (VNF; ör. NAT → DPI → Transcoder) oluşur. <b>Yerleştirme problemi</b>, her VNF için bir sunucu düğümü seçmek ve aralarında yol kurmaktır; CPU/RAM/bant genişliği kısıtları vardır ve problem NP-zordur. <b>Knowledge-Defined Networking (KDN)</b>, SDN'e bir "bilgi düzlemi" ekler: ağdan toplanan telemetriyle ML modeli eğitilir, model kontrol kararlarına girdi olur. Projemizde KDN, VNF'lerin yüke bağlı ve kontrolcünün bilmediği işleme gecikmesini telemetriden öğreniyor ve aday yerleşimler arasından en düşük toplam gecikmeli olanı seçiyor.</p>
{table(['', 'v1 (ders projesi)', 'v2 (seminer, Faz 4A)'], [
    ['Topoloji', 'elle kurulmuş "Abilene benzeri", rastgele 2–10 ms', 'SNDlib Abilene, coğrafi gecikme'],
    ['Trafik', 'Poisson, uniform tip, uç noktası yok', 'Abilene TM 2004: günlük profil + OD\'ye göre ingress/egress'],
    ['Gecikme', 'sadece VNF\'ler arası yayılım (bilinen)', 'ingress→…→egress yayılım + gizli işleme gecikmesi'],
    ['ML ne öğreniyor?', 'zaten hesaplanmış gecikmeyi (gereksiz)', 'gizli işleme gecikmesini (gerekli)'],
    ['Eğitim verisi', 'Greedy kararları', 'aday kümesinden rastgele seçen davranış politikası'],
    ['Değerlendirme', '5 seed, tek yük, istatistik yok', '30 seed × 5 yük, ön kayıt, eşleştirilmiş test, ayarlanmış baseline, oracle'],
])}

<h2 id="s2">2. Genel mimari</h2>
{svg_pipeline()}
<p class="small">Mavi kutu: dünya (veri + gizli gerçeklik). Turuncu: karar veren politika. Yeşil: bilgi düzlemi (model). Politikalar grafiği değiştirmez, sadece önerir; kaynakları simülasyon motoru ayırır ve bırakır. Eğitim verisi sadece train dönemi (Mart–Haziran) koşularından, değerlendirme sadece test döneminden (Temmuz–Eylül) gelir.</p>

<h2 id="s3">3. Kod haritası</h2>
{table(['dosya', 'sorumluluk'], [
    ['<code>src/sfc.py</code>', 'SFC kataloğu, VNF gereksinimleri, <code>SFCRequest</code> (src/dst, gözlenebilir <code>features</code>, gizli <code>hidden</code>)'],
    ['<code>src/placement.py</code>', 'Ortak çekirdek: <code>ResourceState</code> (kopyasız overlay), <code>route</code>, <code>feasible_hosts</code>, <code>build_chain</code>, <code>commit</code>/<code>release</code>'],
    ['<code>src/engine.py</code>', 'SimPy simülasyonu, <code>generate_schedule</code> (v1), <code>RequestRecord</code>, <code>summarize</code> (metrikler)'],
    ['<code>src/algorithms/*</code>', 'v1 politikaları: greedy, smart, random, kdn (+ ablasyonlar, registry)'],
    ['<code>src/v2/data.py</code>', 'SNDlib, TM ve KDN VNF dosyalarının ayrıştırıcıları'],
    ['<code>src/v2/environment.py</code>', '<code>V2World</code> (graf, trafik üretimi, gizli yük, gerçek gecikme), <code>V2Simulation</code>'],
    ['<code>src/v2/policies.py</code>', 'v2 politikaları, aday kümesi, KDN-v2, Oracle, davranış politikası'],
    ['<code>src/v2/features.py</code>', 'Telemetri özellikleri (sadece gözlenebilir büyüklükler)'],
    ['<code>src/v2/experiment.py</code>, <code>analysis.py</code>', 'Koşu gridi, veri üretimi, eğitim; H1–H3, Holm, GA'],
    ['<code>scripts/*</code>', 'CLI: fetch_data, v2 (datagen/train/tune/evaluate/explore), figürler, raporlar'],
    ['<code>experiments/v2_protocol.md</code>', 'Ön kayıt + sapmalar'],
    ['<code>tests/*</code>', '39 test: kaynak/yük korunumu, determinizm, v1 regresyonu, oracle doğruluğu, SNDlib kontrolü'],
])}

<h2 id="s4">4. Simülasyon çekirdeği</h2>
<h3>4.1 Bir isteğin yaşam döngüsü</h3>
<pre>istek gelir (önceden üretilmiş schedule'dan, varışlar arası süre kadar bekle)
  └─ res = politika.place(graph, req)          # grafiği DEĞİŞTİRMEZ, öneri döndürür
       ├─ başarılı:  gerçek_gecikme = yayılım + gizli_işleme(graph, res, req)
       │             commit(graph, res)         # CPU/RAM/BW rezervasyonu düşülür
       │             yük ekle (u0·CPU·r)        # telemetrinin "ölçtüğü" gerçek yük
       │             süre (10–600 t.u.) sonra: release + yükü çıkar
       └─ başarısız: reddedildi ('infeasible' veya 'gate')
  └─ RequestRecord (zaman, tip, kabul, gecikme, karar süresi) kaydedilir</pre>
<h3>4.2 <code>build_chain</code>: bütün politikaların ortak iskeleti</h3>
<pre>prev = ingress (v1'de yok)
her VNF için (zincir sırasıyla):
    adaylar = sıralama(düğümler) içinde, CPU/RAM'i yeten VE prev'den yolu BW'ye yeten düğümler
    hop = seçici(adaylar)                     # politikayı tanımlayan tek şey: sıralama + seçici
    geçici rezervasyon (overlay); yayılım += yol gecikmesi; prev = hop
son VNF'ten egress'e yol (BW kontrolü); yayılım += gecikme</pre>
<p>Bütün politikalar bu iskeletin sıralama ve seçici parametreleri olarak yazıldığı için fizibilite, yönlendirme ve geri alma kodu tek bir yerde ve testli.</p>
<h3>4.3 Metrikler</h3>
<div class="eq">kabul = kabul edilen / toplam istek &nbsp;·&nbsp; CPU-ağırlıklı kabul = Σ<sub>kabul</sub> CPU(SFC) / Σ<sub>tümü</sub> CPU(SFC)</div>
<div class="eq">gecikme = ortalama (ve p95) kurulum gecikmesi, sadece kabul edilenler üzerinden; warm-up (ilk 1200 t.u.) hariç</div>

<h2 id="s5">5. Veri setleri</h2>
<h3>5.1 SNDlib Abilene ağı (<code>abilene.txt</code>, native format)</h3>
<pre>NODES (  ATLAng ( -85.50 34.50 )   …  )                                   # ad (boylam enlem)
LINKS (  ATLAng_HSTNng ( HSTNng ATLAng ) 9920.00 0.00 0.00 0.00 ( 40000.00 1081.00 )  … )
         # link_id ( u v ) kurulu_kapasite_Mbps  …  (modül kapasite/maliyet)</pre>
<p>Kullandığımız alanlar: 12 düğümün koordinatları ve 15 linkin kurulu kapasitesi. Gecikme = haversine mesafesi × 5 µs/km. Sonuç: 0.66–10.96 ms. Not: <code>ATLAM5</code>, Atlanta'da ikinci bir PoP; trafik matrisinde neredeyse hiç trafiği yok.</p>
<h3>5.2 Abilene trafik matrisleri (Zhang, SNDlib'den)</h3>
<pre>demandMatrix-abilene-zhang-5min-20040301-0005.txt     # 48 096 dosya: 2004-03-01 … 2004-09-10, 5 dk
DEMANDS (  ATLAM5_CHINng ( ATLAM5 CHINng ) 1 1.082379 UNLIMITED  … )   # (kaynak hedef) birim değer(Mbps)</pre>
<p>Tek bir <code>float32[48096, 12, 12]</code> dizisine çevrilip <code>data/derived/abilene_tm.npz</code> dosyasında önbellekleniyor (5 sn). 132 OD çiftinin hepsinde trafik var, köşegen sıfır. Train 27 648 aralık, test 20 448 aralık.</p>
<figure>{img('arch_traffic', 'Trafik profili ve OD dağılımı')}<figcaption>Solda varış oranının zaman profili: günlük döngü ±%20 ve ani tepeler. Sağda ingress/egress seçim olasılıkları: CHIN→LOSA ve WASH→NYCM en yoğun çiftler.</figcaption></figure>
<p><b>Trafik üretimi (thinning):</b> λ<sub>max</sub> = pencere içindeki en yüksek oran. Aday varışlar exp(λ<sub>max</sub>) aralıklarla üretilir ve her biri λ(t)/λ<sub>max</sub> olasılıkla kabul edilir; bu, değişken oranlı Poisson sürecini tam olarak üretir. Her istek için sırayla şunlar çekilir:</p>
<ul>
<li>OD çifti (o anki matrise göre)</li>
<li>SFC tipi (uniform)</li>
<li>süre (U{{10…600}})</li>
<li>trafik profili (KDN havuzundan)</li>
<li>gizli r değerleri</li>
</ul>
<p>Rastgele sayı üreteci (seed, λ, split) üçlüsünden türetiliyor; politika ne olursa olsun aynı akış üretiliyor.</p>
<h3>5.3 KDN VNF ölçümleri (Mestres et al. 2017)</h3>
<pre>Snort/features/longIn1_m_0.025_i_20.0.csv   # 20 sn'lik batch başına 86 trafik özelliği (numPackets, flows, ipSrc, …)
Snort/cpu/longIn1.txt                       # aynı batch'lerin ölçülen CPU tüketimi (birim belirtilmemiş)
Snort/loadSnort.m                           # hangi features dosyası hangi cpu dosyasıyla eşleşir (sıra)</pre>
<p>Matlab yükleyicisindeki sıra izlenerek eşleştirildi: Snort 1359, Firewall 755, OVS 1191 örnek (OVS'de 2 dosya eksik, atlandı). Ham trafik izleri gizlilik nedeniyle yayımlanmamış; sadece özellikler ve CPU değerleri var. Kullandığımız alanlar <code>numPackets</code>, <code>flows</code> ve CPU. CPU birimi belirtilmediği için her aile kendi medyanına bölünüyor (Snort 198, Firewall 390, OVS 449).</p>
<figure>{img('arch_vnf_data', 'VNF ölçümleri ve gizli r dağılımı')}<figcaption>Solda CPU, paketle alt-doğrusal (b≈0.63–0.73) ve gürültülü artıyor; KDN makalesinin "ML gerekli" argümanı bu. Sağda simülatörün fiilen çektiği gizli r değerleri: paket sayıları 40–60 bin aralığında yoğunlaştığı için %90'ı 0.87–1.15 arasında.</figcaption></figure>
<h3>5.4 Ürettiğimiz veri setleri</h3>
{table(['veri', 'nerede', 'şema / içerik'], [
    ['v1 telemetrisi', '<code>data/telemetry_v1.csv</code> (25 056 satır)', 'timestamp, sfc_type, 5 ağ durum özelliği, 2 aksiyon özelliği (max hop, farklı düğüm), outcome_accepted, outcome_latency, profile. Etiketler Greedy\'den.'],
    ['v2 telemetrisi', '<code>data/v2/main/telemetry.csv.gz</code> (156 495 satır, %41.4 kabul)', f'seed, lambda, time, sfc_type, accepted, prop_delay, <b>proc_delay (hedef)</b>, generator, 7 durum özelliği <code>s_*</code>, 11 aday özelliği <code>c_*</code>. Train dönemi, seed 1001–1020 × λ {{0.05, 0.1, 0.2, 0.4}}; doğrulama seed\'leri 1017–1020.'],
    ['sonuç tabloları', '<code>results/**/runs.csv</code>', 'politika × seed × λ başına bir satır: kabul, CPU-kabul, gecikme ortalama/p95, aktif düğüm, karar süresi'],
])}

<h2 id="s6">6. SFC/VNF kataloğu</h2>
{sfc_table()}
<p class="small">CPU/RAM rezervasyonları v1'den aynen. s<sub>v</sub> (taban işleme süresi) değerleri göreli ağırlığı yansıtacak şekilde seçildi: transcoder en ağır, monitor en hafif. Bu bir modelleme seçimi; duyarlılık analizi bunu kısmen kapsıyor.</p>

<h2 id="s7">7. Gizli VNF modeli (sadece oracle bilir)</h2>
<div class="eq">r<sub>v</sub> = CPU<sub>k-NN(paket)</sub> / medyan(aile) &nbsp;&nbsp; (k = {ENV['knn']}, rastgele komşu)</div>
<div class="eq">yük<sub>v</sub> = u0 · CPU-rez(v) · r<sub>v</sub>, &nbsp; u0 = {ENV['u0']} &nbsp;&nbsp; ρ<sub>n</sub> = Σ yük / 100</div>
<div class="eq">işleme<sub>v</sub> = s<sub>v</sub> / (1 − min(ρ<sub>n</sub>, {ENV['rho_max']})) &nbsp;&nbsp; gecikme = yayılım(ingress → VNF<sub>1</sub> → … → egress) + Σ<sub>v</sub> işleme<sub>v</sub></div>
<figure>{img('arch_delay_fn', 'Gizli gecikme fonksiyonu')}<figcaption>Seçilen düğümlerin ölçülen kullanımı %99 oranında ≤ 0.60. Eğrinin düz bölgesindeyiz, gecikme çarpanı ≤ 2.5×.</figcaption></figure>
<div class="box warn"><b>Dürüst not:</b> Kabul kararı rezervasyona göre verildiği (Σ CPU-rez ≤ 100) ve r ≈ 1 olduğu için gerçek ρ ≈ 0.6 × (rezerve oran) ≤ 0.6 civarında kalıyor. Sonuç olarak "gizli" bileşenin büyük kısmı rezervasyondan tahmin edilebiliyor. Bu üç şeyi birlikte açıklıyor: R² = {TM['reg_val_r2']:.3f}, öğrenmenin katkısının küçük olması ve u0 değiştiğinde sonucun değişmemesi. Ortam ön kayıtla sabitlendiği için değiştirmedik; makalede sınırlama olarak yazılacak.</div>

<h2 id="s8">8. Politikalar</h2>
<h3>Greedy (first-fit)</h3><p>Her VNF, sabit düğüm sırasında CPU/RAM'i yeten ve yolu BW'ye yeten <b>ilk</b> düğüme konur. Gecikmeyi ve yükü hiç dikkate almaz; alt referans.</p>
<h3>Random</h3><p>Her VNF, uygun düğümler arasından uniform rastgele seçilir; en kötü durum referansı.</p>
<h3>Smart (v1 ve v2): kural tam olarak</h3>
<div class="eq">skor(n) = d(prev → n) + 1000 · [n boşta] + α · ρ<sub>n</sub> + [son VNF] · d(n → egress)</div>
<ul>
<li><b>d(prev → n):</b> önceki VNF'ten (ilk VNF için ingress'ten) n'ye gecikme ağırlıklı yolun gecikmesi.</li>
<li><b>[n boşta]:</b> düğümde hiç rezervasyon yok. 1000'lik ceza neredeyse "zorunlu konsolidasyon" demek: açık bir düğüm varken yeni düğüm açılmaz (enerji tasarrufu, ElasticTree fikri; v1'den geliyor).</li>
<li><b>α · ρ<sub>n</sub>:</b> yük farkındalığı. α=0 → <b>Smart-v2</b> (yükü bilmez), α=α*=10 → <b>Smart-load</b> (train'de grid ile ayarlandı).</li>
<li><b>[son VNF] · d(n → egress):</b> zincirin çıkışa yakın bitmesini sağlar (v2'de eklendi).</li>
<li>Seçim her VNF için ayrı yapılır (açgözlü); eşitlikte sabit düğüm sırası kazanır.</li>
</ul>
<p><b>Keşif amaçlı varyantlar:</b> <code>smart-nowake</code> (ceza = 0, saf gecikme heuristic'i) ve <code>smart-nowake-load</code> (ceza = 0, α = 10). Düşük yükte Smart'ın yavaşlığının nedeninin bu ceza olduğunu bunlarla gösterdik.</p>
<h3>Aday kümesi (KDN-v2, Oracle, cands-prop ve davranış politikası için ortak)</h3>
{table(['üreteç', 'kural'], [
    ['smart-a0', 'Smart-v2 (α=0)'], ['smart-a2 / a10 / a50', 'Smart, sabit α değerleriyle (ayarlanmış değil; küme çeşitliliği için)'],
    ['least-util', 'düğümler ölçülen ρ\'ya göre artan sırada, first-fit'],
    ['colocate', 'düğümler önceki noktaya (ilk VNF için ingress) uzaklığa göre sıralı, first-fit → önce aynı düğüm, sonra en yakın'],
    ['shuffled ×2', 'rastgele düğüm sırası, first-fit (keşif/çeşitlilik)'],
])}
<p>Aynı düğüm dizisini veren adaylar tekilleştirilir (en fazla 8 aday).</p>
<h3>KDN-v2</h3>
<div class="eq">seçim = argmin<sub>c ∈ adaylar</sub> [ yayılım(c) (bilinen) + f̂<sub>XGB</sub>(özellikler(c)) (tahmini işleme) ]</div>
<p>Aday başına 11 özellik:</p>{cand_feat}
<h3>Oracle</h3>
<p>Aynı aday kümesi; seçim gerçek toplam gecikmeye göre yapılır (gizli r ve gerçek fonksiyon). Şunu gösterir: "Model mükemmel olsaydı bu aday kümesiyle ne kadar iyi olurduk?" <b>Global optimum değildir</b>: (1) sadece bu 8 aday arasından seçer, (2) sadece bu isteğin gecikmesine bakar, sonrakileri düşünmez (miyop).</p>
<h3>cands-prop (keşif amaçlı)</h3><p>Aynı adaylar, sadece bilinen yayılım gecikmesine göre seçilir. KDN-v2 ile farkı = <b>öğrenmenin kendi katkısı</b>.</p>
<h3>KDN-v2 + gatekeeper (ablasyon)</h3><p>Önce bir XGBoost sınıflandırıcı, isteğin davranış politikası altında kabul edilip edilmeyeceğini tahmin eder; "hayır" derse istek reddedilir. Durum özellikleri:</p>{state_feat}
<h3>Davranış politikası (sadece veri toplama)</h3><p>Aday kümesinden uniform rastgele seçim. Amaç kapsam: regressor her aday türünün sonucunu görsün.</p>

<h2 id="s9">9. Somut bir karar örneği (test dönemi, seed 3, λ=0.1, t={ex['time']:.0f})</h2>
<p>İstek: <b>{ex['sfc']}</b> ({' → '.join(ex['chain'])}), ingress <b>{ex['src'].replace('ng', '')}</b> → egress <b>{ex['dst'].replace('ng', '')}</b>, paket = {ex['packets']:.0f}, akış = {ex['flows']:.0f}. Gizli r = {', '.join(f'{x:.2f}' for x in ex['hidden_r'])}.<br>
<span class="small">O anki ölçülen ρ: {rho_txt}</span></p>
{example_table()}
<ul>
<li><b>KDN-v2</b>, tahmini toplamı en düşük adayı seçiyor; bu aday gerçekte de en iyisi, yani oracle ile aynı karar. Bu örnekte seçilen yerleşim aynı zamanda Smart-v2'nin kendi yerleşimi.</li>
<li><b>En az kullanılan düğüm adayının</b> işleme gecikmesi en düşük ama yayılımı uzun. Gecikme, yayılım ile işleme arasındaki bir ödünleşim.</li>
<li><b>İki rastgele aday</b> aynı özet özelliklere sahip olduğu için aynı tahmini alıyor, ama gerçek işleme gecikmeleri farklı. Bu, özet özelliklerin ayırt etme sınırını gösteriyor.</li>
</ul>

<h2 id="s10">10. Öğrenme hattı</h2>
{table(['', 'v1', 'v2'], [
    ['Veri', 'Greedy\'nin kararları (4 trafik profili, 25 056 istek)', 'davranış politikası, train dönemi, 80 koşu, 156 495 istek'],
    ['Regressor hedefi', 'toplam gecikme (zaten bilinen)', '<b>işleme gecikmesi</b> (gizli); yayılım sonradan eklenir'],
    ['Doğrulama', 'rastgele %80/20 bölme (ardışık durumlar → hafif sızıntı)', 'ayrı seed\'ler (1017–1020); test ayrı aylarda'],
    ['Model', 'XGBoost 150 ağaç, derinlik 5, lr 0.1', 'aynı (ayar yok)'],
    ['Kalite', 'sınıflandırıcı %93.5; regressor R² ~0.79', f"regressor doğrulama R² {TM['reg_val_r2']:.3f}, RMSE {TM['reg_val_rmse']:.2f} ms (ortalama {TM['reg_val_target_mean']:.2f} ms); gate AUC {TM['clf_val_auc']:.3f}"],
])}

<h2 id="s11">11. Deney protokolü ve istatistik</h2>
<ul>
<li><b>Ön kayıt</b> (<code>experiments/v2_protocol.md</code>, commit <code>48e6edb</code>): ortam, politikalar, hipotezler, analiz planı. Sapmalar dosyanın sonunda; keşif analizleri ayrıca etiketli.</li>
<li><b>Ölçek:</b>
  <ul>
  <li>Test: 30 seed × λ ∈ {{0.02, 0.05, 0.1, 0.2, 0.4}}</li>
  <li>α ayarı: train'de 10 seed × 5 λ, 9 α değeri; hedef λ'lar üzerinden toplam ortalama gecikme</li>
  </ul></li>
<li><b>Hipotezler:</b>
  <ul>
  <li>H1: KDN-v2 &lt; Smart-v2 (tek yönlü Wilcoxon)</li>
  <li>H2: KDN-v2 ile Smart-load arasında fark var mı (iki yönlü)</li>
  <li>H3: CPU ağırlıklı kabulde kayıp en fazla 1 pp (GA alt sınırı &gt; −1)</li>
  </ul>
  H1 ve H2 için 5 λ üzerinden Holm düzeltmesi uygulandı.</li>
<li><b>Duyarlılık:</b> u0 ∈ {{0.4, 0.8}} ve doğrusal gecikme; her varyant için veri, model ve α yeniden üretildi.</li>
<li><b>Neden Wilcoxon?</b> Farklar seed başına eşleşik ve normal dağılım varsayılamaz. İşaretli sıra testi dayanıklı bir seçim.</li>
</ul>

<h2 id="s12">12. Karar günlüğü (her karar, nedeni ve riski)</h2>
{dec}

<h2 id="s13">13. Bilinen zayıflıklar</h2>
<ol>
<li><b>Gizli bileşenin varyansı düşük</b> (r ≈ 1, ρ ≤ 0.6): öğrenme için alan dar. Bu ortam KDN'i değil, ortamın bilgi içeriğini sınırlıyor.</li>
<li><b>Tek topoloji</b> (GÉANT indirildi, koşulmadı).</li>
<li><b>VNF–ölçüm eşlemesi yaklaşık;</b> s<sub>v</sub> değerleri seçim.</li>
<li><b>Gecikme yalnızca kurulum anında ölçülüyor;</b> SFC ömrü boyunca değil.</li>
<li><b>Karar hedefi miyop</b> (istek başına). Ağır yükteki kayıp buradan geliyor.</li>
<li><b>Aday kümesi el yapımı.</b></li>
<li><b>Güncel DRL/GNN yöntemleriyle doğrudan kıyas yok.</b></li>
</ol>

<h2 id="s14">14. Jüri soru–cevap</h2>
{qa}

<h2 id="s15">15. Akademik katkı ve yayın değerlendirmesi</h2>
<h3>Savunulabilir katkılar</h3>
<ol>
<li><b>Ölçüme ve gerçek trafiğe dayalı, tekrar üretilebilir bir değerlendirme ortamı:</b> SNDlib Abilene + 2004 trafik matrisleri + KDN VNF ölçümleri, ön kayıtlı protokol, açık kod ve SHA256 doğrulamalı veri hattı. Bu kombinasyon KDN tabanlı VNF yerleştirme literatüründe yaygın değil.</li>
<li><b>Ampirik bulgu:</b> telemetriden öğrenilen gecikme modeli oracle düzeyinde seçim yapıyor. Ama yerleşim kazancı yük rejimine bağlı: hafif ve orta yükte belirgin, ağır yükte aday kümesi ve miyop hedef nedeniyle sınırlı. "Öğrenme nerede işe yarar?" sorusuna nicel bir cevap.</li>
<li><b>Metodolojik dersler</b> (v1 → v2):
  <ul>
  <li>Hesaplanabilir bir büyüklüğü öğrenmeye çalışmamak.</li>
  <li>İstek sayısına dayalı kabul oranı, büyük SFC'leri reddetmeyi ödüllendirebilir.</li>
  <li>Baseline'lar eşit bütçeyle ayarlanmalı.</li>
  <li>Ablasyon, kazancın çoğunun aday kümesinden geldiğini gösterebilir.</li>
  </ul>
  ML-for-networking değerlendirmelerinde tekrar eden tuzaklar bunlar.</li>
</ol>
<h3>Bir hakem ne der?</h3>
<ul>
<li><b>Artıları:</b> dürüst ve dikkatli değerlendirme, ön kayıt, ablasyonlar, açık artefakt, negatif sonuçların raporlanması.</li>
<li><b>Eksileri:</b>
  <ul>
  <li>Yöntemsel yenilik düşük (XGBoost + heuristic adaylar).</li>
  <li>Tek topoloji.</li>
  <li>Gizli modelin bilgi içeriği zayıf (r ≈ 1).</li>
  <li>Sadece simülasyon.</li>
  <li>DRL/GNN tabanlı güncel yöntemlerle kıyas yok.</li>
  </ul></li>
</ul>
<h3>Kabul şansı (meraktan; kesinlik iddiası yok)</h3>
{table(['hedef', 'görüşüm'], [
    ['Üst düzey konferanslar (SIGCOMM, INFOCOM, CoNEXT, NSDI)', 'Bu haliyle hayır: yenilik ve kapsam yetersiz.'],
    ['Orta düzey IEEE ağ yönetimi konferansları (ör. CNSM, NetSoft, NOMS) ana track', 'Zayıf. Güçlendirmeyle sınırda: ikinci topoloji, daha zengin gizli davranış ve uzun vadeli hedefli (RL veya değer fonksiyonu) bir yöntem.'],
    ['ML-for-networking veya reproducibility/negatif sonuç odaklı workshop\'lar, kısa bildiri', 'Makul. "Öğrenme nerede işe yarar + değerlendirme tuzakları" çerçevesi bu tür mekanlara uygun.'],
    ['Ulusal/bölgesel IEEE konferansları (ör. SIU), öğrenci oturumları', 'Makul ile iyi arası; yöntem ve değerlendirme titizliği bu seviyede güçlü.'],
])}
<p class="small">Yayına hazırlamak için en çok değer katacak üç adım:</p>
<ol class="small">
<li>Gizli davranışı daha bilgi taşıyan hale getirmek: daha geniş r dağılımı ve gerçek kullanımın rezervasyondan sapması.</li>
<li>GÉANT ile genelleme testi.</li>
<li>Miyopluğu hedefleyen bir yöntem (ör. gelecek maliyeti öğrenen bir değer terimi) ve bir DRL baseline'ı.</li>
</ol>
</main></body></html>"""
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('->', OUT)


if __name__ == '__main__':
    build()
