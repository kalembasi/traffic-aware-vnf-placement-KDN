"""Self-contained HTML progress report (pre-paper draft) built from committed results and figures.

Usage: python -m scripts.make_figures && python -m scripts.build_report  -> docs/progress_report.html
"""
import base64
import json
import os
import subprocess

import pandas as pd

OUT = 'docs/progress_report.html'


def img(name, alt):
    with open(f'figures/{name}.png', 'rb') as f:
        b = base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{b}" alt="{alt}">'


def git(*args):
    try:
        return subprocess.check_output(['git', *args], text=True).strip()
    except Exception:
        return '?'


def fmt_table(df, floatfmt='{:.2f}'):
    return df.to_html(index=False, border=0, classes='t', float_format=lambda v: floatfmt.format(v), na_rep='–')


def pivot(path, metric, algos, names):
    s = pd.read_csv(path)
    p = s.pivot(index='algorithm', columns='lambda', values=metric).loc[algos]
    p.index = [names.get(a, a) for a in p.index]
    p.columns = [f'λ={c:g}' for c in p.columns]
    return p.reset_index().rename(columns={'index': 'Politika'})


NAMES = {'greedy': 'Greedy', 'random': 'Random', 'smart': 'Smart(-v2)', 'smart-load': 'Smart-load (α* ayarlı)',
         'kdn': 'KDN (v1)', 'kdn2': 'KDN-v2', 'kdn2-gate': 'KDN-v2 + gatekeeper', 'oracle': 'Oracle',
         'cands-oracle': 'Adaylar + oracle', 'cands-first': 'Sadece co-location adayı', 'kdn-nogate': 'KDN (v1) gatekeeper yok',
         'cands-random': 'Adaylar + rastgele', 'cands-prop': 'Adaylar + sadece yayılım *', 'smart-nowake': 'Smart, uyandırma cezasız *',
         'smart-nowake-load': 'Smart, cezasız + α *'}


def hyp_table():
    h = pd.read_csv('results/v2/main/hypotheses.csv')
    h = h[h.hypothesis.isin(['H1', 'H2', 'H3', 'gap']) & ((h.hypothesis != 'gap') | (h.metric == 'lat_mean'))]

    def verdict(r):
        if r.hypothesis == 'gap':
            return 'fark yok' if r.ci95_lo < 0 < r.ci95_hi else 'fark var'
        if r.hypothesis == 'H2':
            if r.p_holm >= 0.05:
                return 'anlamlı fark yok'
            return 'KDN-v2 daha iyi' if r.mean_diff < 0 else 'KDN-v2 daha kötü'
        return '✅ destekleniyor' if r.supported else '❌ desteklenmiyor'
    out = pd.DataFrame({
        'Hipotez': h.hypothesis.map({'H1': 'H1: KDN-v2 < Smart', 'H2': 'H2: KDN-v2 vs Smart-load', 'H3': 'H3: CPU-kabul kaybı ≤ 1 pp',
                                     'gap': 'KDN-v2 − Oracle'}),
        'λ': h['lambda'].map('{:g}'.format), 'Ortalama fark': h.mean_diff.map('{:+.2f}'.format),
        '%95 GA': [f'[{a:+.2f}, {b:+.2f}]' for a, b in zip(h.ci95_lo, h.ci95_hi)],
        'p (Holm)': h.p_holm.map(lambda v: '–' if pd.isna(v) else ('<0.001' if v < 0.001 else f'{v:.3f}')),
        'Sonuç': [verdict(r) for r in h.itertuples()]})
    return out.to_html(index=False, border=0, classes='t')


def sens_table():
    rows = []
    for v, name in (('main', 'Ana (u0=0.6, M/M/1)'), ('u04', 'S1: u0=0.4'), ('u08', 'S1: u0=0.8'), ('linear', 'S2: doğrusal gecikme')):
        h = pd.read_csv(f'results/v2/{v}/hypotheses.csv'); h = h[h['lambda'] == 0.2]
        g = lambda hyp, m='lat_mean': h[(h.hypothesis == hyp) & (h.metric == m)].mean_diff.iloc[0]
        tm = json.load(open(f'results/v2/{v}/training_metrics.json'))
        a = json.load(open(f'results/v2/{v}/alpha_star.json'))['alpha_star']
        rows.append({'Varyant': name, 'α*': f'{a:g}', 'Doğrulama R²': f"{tm['reg_val_r2']:.3f}",
                     'KDN-v2 − Smart': f"{g('H1'):+.2f}", 'KDN-v2 − Smart-load': f"{g('H2'):+.2f}",
                     'KDN-v2 − Oracle': f"{g('gap'):+.2f}"})
    return pd.DataFrame(rows).to_html(index=False, border=0, classes='t')


def build():
    v1lat = pivot('results/v1_sweep/summary.csv', 'lat_mean_mean',
                  ['smart', 'cands-oracle', 'kdn', 'kdn-nogate', 'cands-first', 'greedy', 'random'], NAMES)
    v2lat = pivot('results/v2/main_exploratory/summary.csv', 'lat_mean_mean',
                  ['greedy', 'smart', 'smart-load', 'kdn2', 'kdn2-gate', 'oracle', 'cands-prop', 'smart-nowake', 'smart-nowake-load', 'random'], NAMES)
    v2acc = pivot('results/v2/main_exploratory/summary.csv', 'cpu_acceptance_mean',
                  ['greedy', 'smart', 'smart-load', 'kdn2', 'kdn2-gate', 'oracle', 'cands-prop', 'smart-nowake', 'smart-nowake-load'], NAMES)
    tm = json.load(open('results/v2/main/training_metrics.json'))
    head, branch = git('rev-parse', '--short', 'HEAD'), git('rev-parse', '--abbrev-ref', 'HEAD')

    html = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KDN tabanlı VNF yerleştirme — ara rapor (Faz 4A sonrası)</title>
<style>
:root {{ --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --rule:#e4e3df; --blue:#2a78d6; --orange:#eb6834; --aqua:#1baf7a; --violet:#6250d6; }}
body {{ background:var(--surface); color:var(--ink); font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; margin:0; }}
main {{ max-width:960px; margin:0 auto; padding:32px 24px 80px; }}
h1 {{ font-size:26px; line-height:1.25; margin:0 0 6px; }} h2 {{ font-size:20px; margin:40px 0 10px; padding-top:12px; border-top:1px solid var(--rule); }}
h3 {{ font-size:16px; margin:24px 0 6px; }} .meta {{ color:var(--ink2); font-size:13px; }}
figure {{ margin:18px 0 22px; }} figure img {{ max-width:100%; border:1px solid var(--rule); border-radius:6px; }}
figcaption {{ color:var(--ink2); font-size:13px; margin-top:6px; }}
table.t {{ border-collapse:collapse; font-size:13px; margin:10px 0 18px; width:100%; }}
table.t th, table.t td {{ border-bottom:1px solid var(--rule); padding:5px 8px; text-align:right; }}
table.t th:first-child, table.t td:first-child {{ text-align:left; }} table.t thead th {{ color:var(--ink2); font-weight:600; }}
.tldr {{ background:#f3f2ef; border-left:4px solid var(--blue); padding:12px 18px; border-radius:4px; }}
.warn {{ background:#fff6ef; border-left:4px solid var(--orange); padding:10px 16px; border-radius:4px; }}
.ok {{ background:#effaf5; border-left:4px solid var(--aqua); padding:10px 16px; border-radius:4px; }}
code {{ background:#f0efec; padding:1px 4px; border-radius:3px; font-size:13px; }}
pre {{ background:#f0efec; padding:10px 14px; border-radius:6px; overflow:auto; font-size:12.5px; }}
.k {{ color:var(--blue); font-weight:600; }} .small {{ font-size:13px; color:var(--ink2); }}
nav ol {{ columns:2; font-size:14px; }}
</style></head><body><main>

<h1>Bilinmeyen VNF davranışını öğrenmek: Knowledge-Defined Networking ile VNF yerleştirme</h1>
<div class="meta">Ara rapor ve makale öncesi taslak · Faz 4A sonrası · branch <code>{branch}</code> @ <code>{head}</code> ·
ön kayıt <code>48e6edb</code> · teslim: 24 Kasım 23:00</div>

<nav><ol>
<li><a href="#ozet">Kısa özet</a></li><li><a href="#v1">v1 projesi ve eleştirisi</a></li>
<li><a href="#v1bulgu">v1'in dürüst değerlendirmesi</a></li><li><a href="#v2">v2: veri temelli yeni kurgu</a></li>
<li><a href="#v2sonuc">v2 sonuçları</a></li><li><a href="#mekanizma">Neden böyle? (mekanizma)</a></li>
<li><a href="#tartisma">Tartışma ve geçerlilik tehditleri</a></li><li><a href="#makale">Makale iskeleti</a></li>
<li><a href="#4b">4B kararı için seçenekler</a></li><li><a href="#repro">Tekrar üretim</a></li>
</ol></nav>

<h2 id="ozet">1. Kısa özet</h2>
<div class="tldr">
<ul>
<li><b>v1 (ders projesi) sayıları doğruydu, yorumları değil.</b> KDN Greedy'yi yeniyordu, ama basit Smart heuristic'ini hiçbir yükte yenemiyordu. Regressor zaten bilinen bir değeri tahmin ediyordu. Gatekeeper'ın kabul "kazancı" ise yalnızca istek sayısıyla ölçüldüğü için ortaya çıkan bir artefakttı.</li>
<li><b>v2 tamamen public veriye dayanıyor:</b>
  <ul>
  <li>SNDlib Abilene topolojisi</li>
  <li>2004 Abilene trafik matrisleri (5 dakikalık)</li>
  <li>KDN makalesinin VNF CPU ölçümleri</li>
  </ul>
  Kontrolcünün bilmediği şey, yüke bağlı VNF işleme gecikmesi; KDN bunu telemetriden öğreniyor. Değerlendirme protokolü sonuçlardan önce ön kayıt edildi.</li>
<li><span class="k">Kazanç:</span> hafif ve orta yükte (λ ≤ 0.1) KDN-v2, Smart'tan 0.4–8.3 ms daha hızlı ve CPU ağırlıklı kabul oranı +1–3 pp daha yüksek. Greedy'ye karşı her yükte %27–42 daha düşük gecikme sağlıyor.</li>
<li><span class="k">Sınır:</span> ağır yükte (λ ≥ 0.2) KDN-v2, ayarlanmış heuristic'ten 1.5–1.7 ms yavaş. Bu sonuç duyarlılık analizinde de değişmedi.</li>
<li><span class="k">Model kalitesi:</span> gizli gecikme neredeyse mükemmel öğreniliyor (doğrulama R² = {tm['reg_val_r2']:.3f}) ve seçim oracle ile aynı kalitede.</li>
<li><span class="k">Kazancın kaynağı:</span> öğrenmenin kendi payı küçük (0.2–0.5 ms); kazancın çoğu aday kümesinden geliyor. Ağır yükteki kaybın sebebi model değil, istek başına (miyop) optimizasyon.</li>
</ul></div>

<h2 id="v1">2. v1 projesi ve eleştirisi</h2>
<p>Ders projesinde kurulan sistem:</p>
<ul>
<li>SimPy ile olay tabanlı bir SFC simülatörü</li>
<li>İki aşamalı bir XGBoost yapısı: kabul kararı için bir gatekeeper sınıflandırıcı ve aday puanlamak için bir gecikme regressor'ı</li>
</ul>
<p>Rapordaki iddia: Greedy'ye göre %38 daha düşük gecikme. Kod incelendiğinde şu sorunlar çıktı:</p>
<ul>
<li><b>Regressor zaten bilinen bir değeri tahmin ediyor.</b> Her adayın gecikmesi, aday üretilirken zaten tam olarak hesaplanıyordu; modelin tahmini bilgi eklemiyordu.</li>
<li><b>"Uçtan uca" gecikme dar tanımlanmış.</b> Kaynak/hedef düğümü ve işleme gecikmesi yoktu; ölçülen şey sadece VNF'ler arası yayılım gecikmesiydi.</li>
<li><b>Değerlendirme scripti çalışmıyordu</b> (<code>main()</code> kendi içine girintilenmişti). Veri üretimi seed'sizdi ve link gecikmeleri her koşuda rastgele çekiliyordu.</li>
<li><b>Topoloji gerçek Abilene değildi.</b> DALL düğümü ve CHIC–WASH kenarı SNDlib'de yok (Şekil 1).</li>
</ul>
<figure>{img('fig_topology', 'v1 ve SNDlib Abilene topolojileri')}
<figcaption>Şekil 1. Solda v1'in elle kurulmuş "Abilene benzeri" topolojisi, sağda SNDlib Abilene. Turuncu kenarlar yalnızca o topolojide var. v2 SNDlib'i ve coğrafi gecikmeleri kullanıyor.</figcaption></figure>

<h2 id="v1bulgu">3. v1'in dürüst değerlendirmesi (Faz 3)</h2>
<p>Protokol:</p>
<ul>
<li>30 seed × 5 yük seviyesi</li>
<li>10 000 t.u. ufuk, warm-up atılıyor</li>
<li>Eşleştirilmiş Wilcoxon testi</li>
<li>Ablasyonlar: oracle seçici, gatekeeper'sız varyant ve diğerleri</li>
</ul>
<figure>{img('fig_v1_ablation', 'v1 ablasyon sonuçları')}
<figcaption>Şekil 2. v1, λ=0.2. Aynı 5 aday içinden gerçek gecikmeye göre seçim yapan oracle bile Smart'tan 5.4 ms kötü. Darboğaz seçim değil, aday kümesi.</figcaption></figure>
<figure>{img('fig_v1_gate', 'v1 gatekeeper etkisi')}
<figcaption>Şekil 3. v1 gatekeeper'ı istek sayısına göre kabul oranını artırıyor, CPU ağırlıklı kabulü ise azaltıyor. Büyük SFC'leri (Video) reddedip küçükleri kabul ediyor.</figcaption></figure>
<h3>Tablo: v1 ortalama gecikme (ms), 30 seed</h3>
{fmt_table(v1lat)}

<h2 id="v2">4. v2: veri temelli yeni kurgu (Faz 4A)</h2>
<div class="ok"><b>Ön kayıt:</b> ortam, politikalar, hipotezler ve analiz planı KDN-v2 eğitilmeden önce <code>experiments/v2_protocol.md</code> dosyasında sabitlendi (commit <code>48e6edb</code>). Sonradan yapılan sapmalar aynı dosyanın sonunda listeleniyor. Ön kayıtta olmayan analizler raporda <b>*</b> ile işaretli.</div>

<h3>4.1 Ortam</h3>
<ul>
<li><b>Topoloji:</b> SNDlib Abilene; 12 düğüm, 15 link. Yayılım gecikmesi coğrafi mesafeden (5 µs/km), yönlendirme gecikme ağırlıklı.</li>
<li><b>Trafik:</b> Zhang'ın 2004 Abilene trafik matrisleri.
  <ul>
  <li>Varış oranı gün içi toplam hacmi izliyor.</li>
  <li>İsteklerin giriş/çıkış düğümleri o andaki kaynak–hedef hacmine göre seçiliyor.</li>
  <li>Eğitim Mart–Haziran, test Temmuz–Eylül verisiyle (zamansal ayrım).</li>
  </ul></li>
<li><b>Gizli VNF davranışı:</b> KDN makalesinin ölçümleri (Snort, OVS-firewall, OVS-switch).
  <ul>
  <li>Her VNF'in yükü, isteğin paket sayısına en yakın ölçümlerden (k-NN) alınıyor.</li>
  <li>İşleme gecikmesi s<sub>v</sub>/(1−ρ), ρ düğüm kullanımı.</li>
  <li>Bu fonksiyonu sadece oracle biliyor.</li>
  </ul></li>
<li><b>Kabul kararı:</b> v1'deki gibi CPU/RAM rezervasyonuna göre. Gerçek yük rezervasyondan farklı ve yalnızca telemetriyle görülebiliyor.</li>
</ul>

<h3>4.2 Kim neyi biliyor?</h3>
<table class="t"><thead><tr><th>Bilgi</th><th>Greedy</th><th>Smart</th><th>Smart-load(α)</th><th>KDN-v2</th><th>Oracle</th></tr></thead><tbody>
<tr><td>Topoloji, gecikmeler, rezervasyonlar</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr>
<tr><td>Ölçülen düğüm kullanımı (telemetri)</td><td></td><td></td><td>✓</td><td>✓</td><td>✓</td></tr>
<tr><td>İstek trafik özellikleri (paket, akış)</td><td></td><td></td><td></td><td>✓</td><td>✓</td></tr>
<tr><td>Gizli gecikme fonksiyonu ve VNF yükleri</td><td></td><td></td><td></td><td></td><td>✓</td></tr>
</tbody></table>

<h3>4.3 Politikalar</h3>
<ul>
<li><b>KDN-v2:</b> en fazla 8 heuristic adayın her biri için "bilinen yayılım + tahmin edilen işleme gecikmesi"ni hesaplıyor ve en düşüğünü seçiyor. Eğitim verisi, train döneminde adaylar arasından rastgele seçim yapan bir davranış politikasıyla toplandı (156 bin istek).</li>
<li><b>Smart-load(α):</b> Smart'ın skoruna α·ρ ekliyor. α, train döneminde grid search ile ayarlandı (α* = 10). Bu, "elle ağırlık ayarı gerekmiyor" iddiasının dürüst sınavı.</li>
<li><b>Oracle:</b> aynı adaylar arasından gerçek gecikmeye göre seçim yapıyor; her seçici için üst sınır.</li>
</ul>

<h2 id="v2sonuc">5. v2 sonuçları (test dönemi, 30 seed × 5 λ)</h2>
<figure>{img('fig_v2_latency', 'v2 gecikme ve yük ilişkisi')}
<figcaption>Şekil 4. Ortalama kurulum gecikmesi, %95 güven aralığı bantlarıyla. KDN-v2 hafif ve orta yükte belirgin biçimde önde, ağır yükte Smart varyantlarının biraz gerisinde. Oracle eğrisi KDN-v2 ile çakıştığı için çizilmedi (tabloya bakın).</figcaption></figure>
<h3>Ön kayıtlı hipotezler</h3>
{hyp_table()}
<p class="small">Gecikme farkları ms, kabul farkları yüzde puanı (pp) cinsinden. Eşleştirilmiş Wilcoxon testi, 5 λ üzerinden Holm düzeltmeli. H3 testinde, %95 güven aralığının alt sınırı −1 pp'nin üstündeyse hipotez destekleniyor.</p>
<figure>{img('fig_v2_diff', 'Eşleştirilmiş gecikme farkları')}
<figcaption>Şekil 5. Eşleştirilmiş farklar (aynı seed, aynı trafik). Gri baklavalar öğrenmenin kendi katkısını gösteriyor: aynı adaylar arasında öğrenilmiş seçim ile sadece bilinen yayılım gecikmesine göre seçim arasındaki fark. Bu katkı en fazla 0.5 ms.</figcaption></figure>
<figure>{img('fig_v2_tradeoff', 'Gecikme ve kabul ödünleşimi')}
<figcaption>Şekil 6. λ=0.1'de, KDN-v2'ye göre farklar. Basit heuristic'ler biraz daha hızlı ama ~1 pp daha az CPU yükü kabul ediyor. Tek bir kazanan yok; daha az kabul eden, kısmen daha kolay istekleri tuttuğu için daha düşük gecikme gösteriyor (survivor bias).</figcaption></figure>
<h3>Tablo: ortalama gecikme (ms)</h3>
{fmt_table(v2lat)}
<h3>Tablo: CPU ağırlıklı kabul (%)</h3>
{fmt_table(v2acc)}
<p class="small">* = keşif amaçlı analiz (ön kayıtta yok).</p>
<h3>Duyarlılık (ön kayıtlı, λ = 0.2; her varyant için model yeniden eğitildi, α yeniden ayarlandı)</h3>
{sens_table()}

<h2 id="mekanizma">6. Neden böyle? (mekanizma)</h2>
<figure>{img('fig_v2_decomp', 'Gecikme ayrışımı')}
<figcaption>Şekil 7. Gecikmenin yayılım ve işleme bileşenleri. λ=0.02'de Smart'ı yavaşlatan şey, v1'den kalan enerji amaçlı "boştaki düğümü uyandırma" cezası; bu ceza onu uzak, aktif düğümlere yönlendiriyor. Ceza kaldırılınca KDN-v2 ile aynı seviyeye iniyor. λ=0.4'te KDN-v2 ve oracle'ın hem yayılım hem işleme gecikmesi daha yüksek.</figcaption></figure>
<figure>{img('fig_v2_generators', 'KDN-v2 aday seçimi')}
<figcaption>Şekil 8. KDN-v2'nin seçtiği aday türleri. Düşük yükte co-location ve en az kullanılan düğüm adayları baskın, yük arttıkça Smart'ın kendi yerleşimi.</figcaption></figure>
<ul>
<li><b>Öğrenme işe yarıyor ama alanı dar.</b> İşleme gecikmesi toplam gecikmenin sadece %18–39'u. Rezervasyona dayalı kabul, düğüm kullanımını sınırlı tuttuğu için kuyruk gecikmesi nadiren patlıyor.</li>
<li><b>Ağır yükte kaybın sebebi miyopluk.</b> Her isteğin kendi gecikmesini minimize etmek, sonraki isteklerin karşılaşacağı ağ durumunu kötüleştiriyor. Oracle bile aynı kaybı yaşıyor; yani sorun modelde değil, karar hedefinde.</li>
<li><b>Aday kümesi belirleyici.</b> v1'deki ders burada da geçerli: seçici, kümede olmayan bir yerleşimi bulamaz.</li>
</ul>

<h2 id="tartisma">7. Tartışma ve geçerlilik tehditleri</h2>
<ul>
<li><b>İç geçerlilik:</b> gecikme modelinin şekli ve parametreleri (s<sub>v</sub>, u0) bizim seçimimiz. Bunu ön kayıt ve duyarlılık analizi (u0 0.4/0.8, doğrusal gecikme) ile sınırladık; ana sonuç tüm varyantlarda aynı kaldı.</li>
<li><b>Dış geçerlilik:</b>
  <ul>
  <li>Tek topoloji kullanıldı (GÉANT verisi indirildi ama koşulmadı).</li>
  <li>VNF-ölçüm eşlemesi yaklaşık; örneğin video transcoder için ölçüm yok, OVS ile temsil edildi.</li>
  <li>Gecikme, SFC'nin kurulduğu anda ölçülüyor (ömrü boyunca değil).</li>
  </ul></li>
<li><b>Yapı geçerliliği:</b> istek sayısına göre kabul oranı yanıltıcı olabiliyor (v1'deki gatekeeper artefaktı). Bu yüzden CPU ağırlıklı kabul de raporlanıyor. Gecikmeler yalnızca kabul edilen SFC'ler üzerinden ortalandığı için survivor bias'a açık.</li>
<li><b>Araştırma etiği:</b> v2 tasarımı v1 sonuçları görüldükten sonra yapıldı; bu açıkça belirtiliyor (v1 keşif, v2 doğrulama amaçlı). Ön kayıttan sapmalar listelendi. Ön kayıtta olmayan analizler etiketli. Negatif sonuçlar da raporlanıyor.</li>
</ul>

<h2 id="makale">8. Makale iskeleti (ödev başlıklarıyla)</h2>
<table class="t"><thead><tr><th>Başlık</th><th>İçerik</th><th>Kaynak</th></tr></thead><tbody>
<tr><td>Title</td><td><i>Learning Hidden VNF Behaviour with Knowledge-Defined Networking: Where Does It Pay Off in SFC Placement?</i> (öneri)</td><td>—</td></tr>
<tr><td>Abstract</td><td>Problem → KDN → trace-driven, ön kayıtlı değerlendirme → hafif/orta yükte kazanç, ağır yükte sınır → oracle düzeyinde öğrenme</td><td>§1</td></tr>
<tr><td>Introduction (Related Work)</td><td>NFV/SFC yerleştirme, heuristic/ILP/DRL, KDN, RouteNet benzeri ağ modelleme; katkılar</td><td>literatür (Faz 5)</td></tr>
<tr><td>Material and Methods</td><td>Veri setleri, v2 ortamı, gizli VNF modeli, politikalar, bilgi tablosu, eğitim, protokol ve istatistik</td><td>§4, protokol</td></tr>
<tr><td>Experimental Results</td><td>Şekil 4–6, hipotez tablosu, duyarlılık; kısa bir v1 alt bölümü (Şekil 2–3)</td><td>§5</td></tr>
<tr><td>Conclusion (Future Work)</td><td>Bulgular; uzun vadeli hedef (RL), aday üretimi, kapalı döngü, GÉANT</td><td>§6</td></tr>
<tr><td>Discussion</td><td>Mekanizma (Şekil 7–8), geçerlilik tehditleri, etik ve tekrar üretilebilirlik</td><td>§6–7</td></tr>
<tr><td>Acknowledgements</td><td>Danışman; SNDlib ve KDN veri sağlayıcıları; (politikaya göre) AI-araç beyanı</td><td>—</td></tr>
</tbody></table>

<h2 id="4b">9. 4B kararı için seçenekler</h2>
<div class="warn">Not: Mevcut regressor zaten oracle düzeyinde (fark ≈ 0). Bu yüzden 4B'nin (kapalı döngüde yeniden eğitim) <b>gecikme sonuçlarını iyileştirmesi beklenmiyor</b>. 4B'nin asıl katkısı "KDN döngüsünü kapattık" anlatısı ve davranış politikası ile dağıtılan politika arasındaki dağılım kaymasının ölçülmesi olur.</div>
<table class="t"><thead><tr><th>Seçenek</th><th>Ne kazandırır</th><th>Maliyet</th><th>Risk</th></tr></thead><tbody>
<tr><td><b>A. 4B'yi atla, makaleye geç</b> (önerim)</td><td>Yazıma 4 gün kalır; sonuçlar zaten tutarlı ve tartışmalı</td><td>0</td><td>Düşük</td></tr>
<tr><td>B. 4B: kapalı döngü (2–3 iterasyon)</td><td>KDN döngüsü kapanır; dağılım kayması ölçülür</td><td>~yarım gün</td><td>Sonuç değişmeyecek gibi; düşük getiri</td></tr>
<tr><td>C. v2.1: yüke göre geçiş yapan hibrit (yeni ön kayıtla)</td><td>Ağır yükteki kaybı kapatabilir; tüm yüklerde "en az heuristic kadar iyi" olabilir</td><td>~yarım gün</td><td>Eşik train'de ayarlanmalı; mühendislik çözümü gibi görünebilir</td></tr>
<tr><td>D. Uzun vadeli hedef (gelecek gecikme etkisini öğrenen değer fonksiyonu)</td><td>Miyopluğa asıl çözüm</td><td>1–2 gün</td><td>Takvimi zorlar</td></tr>
</tbody></table>

<h2 id="repro">10. Tekrar üretim</h2>
<pre>./scripts/fetch_data.sh                 # public veri + SHA256 doğrulaması
./run_all.sh                            # v1 tekrar üretimi + testler
python -m scripts.evaluate --exp experiments/v1_sweep.json --out results/v1_sweep --jobs 10
python -m scripts.analyze_models --data data/telemetry_v1.csv --models-dir models/v1 --out results/v1_models
python -m scripts.v2 datagen  --env experiments/v2/env_main.json --out data/v2/main/telemetry.csv.gz
python -m scripts.v2 train    --data data/v2/main/telemetry.csv.gz --models-dir models/v2/main
python -m scripts.v2 tune     --env experiments/v2/env_main.json --out results/v2/main
python -m scripts.v2 evaluate --env experiments/v2/env_main.json --models-dir models/v2/main --out results/v2/main
python -m scripts.make_figures &amp;&amp; python -m scripts.build_report</pre>
<p class="small">Detaylı bulgular: <code>results/v1_findings.md</code>, <code>results/v2_findings.md</code>. Tüm sayılar <code>results/**</code> altındaki CSV dosyalarından üretiliyor.</p>
</main></body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'-> {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB)')


if __name__ == '__main__':
    build()
