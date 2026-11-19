# Rollout: Seminer Makalesi (Scientific Research, Ethics & Seminar)

**Branch:** `seminar-paper` (base: `main` @ `8ea6f2e`)
**Konu:** Virtual Network Function Placement Using Knowledge-Defined Networking
**Danışman:** Tuğçe Bilen
**Çıktı:** IEEE conference formatında (IEEEtran, `a4paper`) LaTeX makale + tekrar üretilebilir kod/deney

---

## 0. Bağlam

Bu repo, *Computer Networks: Basic Protocols* dersinde dönem projesi olarak yapıldı ve 4 sayfalık
IEEE raporu (`report.pdf`) teslim edildi. Seminer dersi için aynı proje üzerinde **iyileştirilmiş
ve dürüstçe yeniden değerlendirilmiş** bir makale çıkarılacak.

Ödevin istediği başlıklar: Title, Abstract, Introduction (Related Work), Material and Methods,
Experimental Results, Conclusion (Future Work), Discussion, Acknowledgements, References.

---

## 1. Eleştiri (2026-11-19 incelemesi)

### 1.1 Ön deney: rapor tekrar üretilebiliyor mu?

`main@8ea6f2e` kodunun bir kopyası `/tmp`'de, ayrı bir venv içinde çalıştırıldı (data generator
seed=2025, modeller `train_models()` ile eğitildi, değerlendirme aynı 5 seed ile yapıldı).

| Algoritma | Rapor (Tablo III) | Tekrar üretim | Not |
|---|---|---|---|
| Greedy | 54.62 % / 20.52 ms | 54.62 % / 20.52 ms | birebir aynı |
| Smart | 53.39 % / 8.56 ms | 53.39 % / 8.56 ms | birebir aynı |
| XGBoost | 54.08 % / 12.72 ms | 54.44 % / 12.68 ms | veri üretimi seed'siz olduğu için küçük fark var |
| Sınıflandırıcı doğruluğu | 93.5 % | 93.5 % | |

**Sonuç:** Sayılar uydurma değil, kod gerçekten bu sayıları üretiyor. Ancak **HEAD'deki
`evaluate_models.py` çalışmıyor** (bkz. 1.3), yani bu sayılar şu anki repodan doğrudan üretilemez.

### 1.2 Ablasyon: kazanç nereden geliyor? (raporda yok)

λ=0.2, end_time=1000. Tabloda 30 seed var (1..30); raporun 5 seed'iyle de aynı sıralama çıktı.
Gecikme yalnızca kabul edilen SFC'ler üzerinden hesaplandı.

| Varyant | Kabul (%) | Gecikme (ms) | Açıklama |
|---|---|---|---|
| **Smart** | 49.7 ± 3.8 | **8.6 ± 1.9** | tek parametreli heuristic |
| Cands+Oracle | 49.7 ± 4.3 | 13.2 ± 2.7 | XGB ile aynı 5 aday, **gerçek** gecikmesi en düşük olan seçiliyor (ML yok) |
| **XGB (full)** | 49.9 ± 4.1 | 13.9 ± 3.1 | raporun yöntemi |
| XGB (no-gate) | 48.9 ± 4.0 | 14.0 ± 3.1 | gatekeeper kapalı |
| Cand0-only | 48.7 ± 4.2 | 15.7 ± 3.2 | yalnızca co-location adayı (ML yok) |
| Greedy | 50.2 ± 4.4 | 20.3 ± 3.7 | |
| Cands+RandPick | 50.5 ± 4.2 | 35.3 ± 6.2 | 5 adaydan rastgele seçim |
| Random | 50.9 ± 4.1 | 37.0 ± 5.3 | |

Eşleştirilmiş Wilcoxon testi (30 seed):
- XGB < Greedy: p ≈ 2e-9. Fark gerçek.
- XGB vs Oracle: fark +0.75 ms, p = 0.11. Regressor, zaten bilinen değeri tahmin ederek oracle'a yaklaşıyor ama onu geçemez.
- XGB > Smart: fark +5.3 ms, p ≈ 2e-9. **Smart, XGB'den açıkça daha iyi** ve kabul oranı aynı.
- Gatekeeper kabul oranını yaklaşık +1 puan artırıyor; bu ilginç bir yan bulgu (bkz. 1.4-e).

### 1.3 Uygulama hataları (kod)

| # | Sorun | Yer |
|---|---|---|
| a | `main()` çağrısı `main` fonksiyonunun içine girintilenmiş ve `if __name__ == '__main__'` yok. Script çalıştırılınca hiçbir şey yapmıyor; çağrılırsa sonsuz özyinelemeye giriyor. | `evaluate_models.py:356` |
| b | Veri üretimi seed'siz, dolayısıyla eğitim verisi ve modeller tekrar üretilemiyor. | `data_generator.py` |
| c | Topolojinin link gecikmeleri her `create_topology` çağrısında rastgele çekiliyor. Eğitimdeki topoloji ile değerlendirmedeki topoloji farklı ve gecikme özelliklerde yok. | `src/topology.py:39` |
| d | En kısa yol hop sayısına göre hesaplanıyor (`weight` yok); gecikmeyi değil hop sayısını minimize ediyor. Bu yüzden "latency-aware" iddiası zayıf. | tüm algoritmalar |
| e | Ağ durumunu çıkaran fonksiyon iki yerde kopyalanmış (train/serve skew riski), `MAX_CPU=100` sabit kodlanmış. | `data_generator.py:14`, `xgboost.py:20`, `smart.py:9` |
| f | Yerleştirme döngüsünün 4 neredeyse aynı kopyası var; `len(res)==2` gibi eski arayüz yamaları duruyor. | `src/algorithms/*`, `engine.py:59` |
| g | `RandomPlacement` var ama değerlendirmede kullanılmıyor. | `evaluate_models.py` |
| h | Notebook'lar `c:\thesis` yoluna `chdir` ediyor ve eski/tek seed'li sonuçları gösteriyor (rapordaki sayılarla tutarsız). | `notebooks/` |
| i | README UTF-16 kodlu ve "Master's Thesis" diyor; hiç test yok. | |

### 1.4 Metodolojik sorunlar (asıl önemli olanlar)

**a. Regressor, zaten bilinen bir değeri tahmin ediyor.** Aday üretimi sırasında her adayın
`total_delay` değeri kesin olarak hesaplanıyor (`xgboost.py:97`). Sonra ML modeli bu değeri
tahmin ediyor ve tahmine göre seçim yapıyor. Doğrudan `min(total_delay)` seçimi tanım gereği eşit
ya da daha iyi sonuç verir; ablasyon da bunu doğruluyor. Mevcut haliyle ML katmanı bilgi katmıyor.

**b. Durum özellikleri adayları ayırt etmiyor.** Aynı istek için 5 adayın 6 durum özelliği
birebir aynı; sıralamayı yalnızca `action_max_path_distance` ve `action_num_unique_nodes`
belirliyor. Rapordaki "network_free_bw en önemli özellik" yorumu (Şekil 5) aday seçimi açısından
anlamsız. Ayrıca XGBoost'un `weight` metriği önem değil, split sayısıdır; `gain` ya da SHAP
kullanılmalı.

**c. "End-to-end latency" gerçekte uçtan uca değil.** SFC'lerin kaynak ve hedef düğümü yok;
işleme veya kuyruk gecikmesi yok. Ölçülen şey sadece VNF'ler arası yayılım gecikmesi. Tüm VNF'ler
aynı düğüme konursa gecikme 0 oluyor (eğitim verisindeki kabullerin %12.6'sı 0 ms). Bu yüzden
"co-location yapan kazanır" ve Smart en iyi sonucu veriyor.

**d. Gecikme yalnızca kabul edilenler üzerinden ortalanıyor (survivor bias).** Daha çok reddeden
bir algoritma daha düşük gecikme gösterebilir. Kabul oranları burada yakın olsa da metrik
tasarımı bunu ayrıca kontrol etmeli (SFC tipine göre kırılım, p95).

**e. Gatekeeper'ın "maliyetli başarısız denemeleri önlediği" iddiası modelde karşılıksız.**
Simülatörde başarısız deneme maliyetsiz (rollback anında yapılıyor). Sınıflandırıcı sadece
"Greedy bu durumda kabul eder miydi?" sorusunu taklit ediyor. Yine de ablasyonda kabul oranını
yaklaşık 1 puan artırdı. Muhtemel sebep, yük altında büyük SFC'leri (Video) reddederek
kapasiteyi küçüklere bırakması (trunk-reservation benzeri bir etki). Bu, makalede düzgün
incelenmeye değer bir bulgu.

**f. Değerlendirme protokolü zayıf.**
- end_time=1000 ve ortalama tutma süresi 305 olduğundan sistem durağan duruma zar zor ulaşıyor (warm-up atılmamış).
- ~200 istek/seed × 5 seed var; istatistiksel test yok, "en düşük varyans → SLA garantisi" iddiası n=5 ile savunulamaz.
- Tek bir yük noktası kullanılmış. Teklif edilen yük kapasitenin yaklaşık 2 katı (yaklaşık 61 eşzamanlı SFC talebi, kapasite ≈ 25), yani hep aşırı yük rejimindeyiz. Yük taraması (λ sweep) yapılmalı.
- "Active nodes" metriği tüm algoritmalarda 11.2–11.5/12; bu rejimde bilgi taşımıyor.

**g. Sınıflandırıcı değerlendirmesinde hafif sızıntı var.** Ardışık durumlar neredeyse aynı;
rastgele bölmede %93.5, kronolojik bölmede %91.6 çıkıyor. Ciddi değil ama düzeltilmeli. Kıyas
için: çoğunluk sınıfı %59.5, 2 derinlikli ağaç (sfc_type, free_cpu) %82.9.

**h. KDN "kapalı döngü" değil.** Model bir kez, Greedy verisiyle offline eğitiliyor; kendi
kararlarının telemetrisiyle yeniden eğitilmiyor. Tablo IV'teki "closed-loop automation" ifadesi
abartılı.

**i. Rapordaki iddialar ve atıflar.**
- "without handcrafted weight tuning": aday üreteci (co-location, 4 shuffle) zaten el yapımı. Tek parametreli Smart hem daha basit hem daha iyi.
- Topoloji "SNDlib Abilene" diye anlatılıyor ama kenar listesi SNDlib dosyasıyla birebir uyuşmuyor gibi görünüyor (DALL düğümü, CHIC–WASH kenarı; INDI–KANS yok). **SNDlib dosyasıyla doğrulanmalı.** Ayrıca [7] numaralı atıf SNDlib değil, Topology Zoo.
- "Lowest variance → production-grade SLA" iddiası çıkarılmalı.
- Related Work yalnızca 7 kaynaktan oluşuyor. Seminer makalesinde güncel VNF/SFC yerleştirme, DRL, GNN ve KDN literatürü gerekli.

### 1.5 Özet hüküm

| Soru | Cevap |
|---|---|
| Yapı kurulabilmiş mi? | **Kısmen.** SimPy olay tabanlı simülatör, kaynak ayırma/serbest bırakma ve iki aşamalı pipeline uçtan uca çalışıyor. KDN döngüsü ise açık (offline, tek seferlik eğitim). Regressor zaten bilinen bir değeri tahmin ettiği için "öğrenilmiş bilgi" katmanı fiilen işlevsiz. |
| Metrikler dürüst mü? | **Sayılar dürüst, yorumlar değil.** Sayılar tekrar üretilebiliyor. Ancak gecikme tanımı dar; "%38 iyileşme"nin kaynağı ML değil, aday üretimi ve seçim. Smart'ın açık üstünlüğü ise geri planda bırakılmış. |
| Deneyler tekrarlanmalı mı? | **Evet, kesinlikle.** HEAD'deki değerlendirme scripti bozuk, veri seed'siz. Ablasyon, yük taraması ve istatistik eksik. |
| Refactor mı, sıfırdan yazım mı? | **Hedefli refactor + model iyileştirmesi.** Kod küçük (~1400 satır) ve simülasyon çekirdeği sağlam. Sıfırdan yazmak gereksiz. Ortak yerleştirme çekirdeği, tek özellik fonksiyonu ve config tabanlı deney koşucusu yeterli. Gerçek iyileştirme ise gecikme modelinin değiştirilmesi (Faz 4). |

---

## 2. Strateji

Bu bir **araştırma etiği** dersi. Önceki raporun abartılı iddialarını tekrarlamak hem riskli hem
gereksiz. Önerilen hikaye:

> *"Bir KDN tabanlı iki aşamalı öğrenen yerleştirme mekanizması; ablasyonla öğrenmenin nerede
> değer kattığını ve nerede katmadığını ayırt eden dürüst bir değerlendirme; ve ML'nin gerçekten
> bilinmeyen bir şeyi (yüke bağlı işleme ve kuyruk gecikmesi) öğrenmesi gereken daha gerçekçi
> bir gecikme modeli."*

- **v1 (ders projesi) sonuçları** baseline ve motivasyon olarak kullanılır. Ablasyon, oracle'ın ML'den iyi olduğunu açıkça gösterir.
- **v2 (seminer)** gecikme modelini KDN'in asıl önermesine uygun hale getirir: kontrolcü ağın davranış fonksiyonunu bilmez, telemetriden öğrenir (RouteNet benzeri motivasyon).
- Sonuç ne çıkarsa çıksın (ML Smart'ı geçse de geçmese de) dürüstçe raporlanır. Danışmana verilen seminer özetindeki "lower latency than baselines" beklentisi tutmazsa, Discussion'da açıkça tartışılır.

**Self-plagiarism notu:** Önceki ders raporu yayımlanmamış küçük bir ödev olduğu için makalede
atıf yapılmayacak (karar: kullanıcı, 2026-11-19). Yine de metin oradan kopyalanmayacak, şekiller
yeniden üretilecek. AI-araç kullanım beyanı ders politikasına göre belirlenecek.

---

## 3. Fazlar ve Subtask'lar

> İş akışı: her faz `seminar-paper`'dan açılan ayrı bir branch'te yapılır, merge öncesi özet onayı alınır. Her faz ayrı commit(ler). Faz sonunda kısa bir "çıktı / kabul kriteri" kontrolü yapılır.

### Faz 0 — Hijyen ve dondurma
- [x] `seminar-paper` branch'ini aç
- [x] `rollout.md` (bu dosya)
- [x] `main@8ea6f2e` için `v1-course-report` tag'i at (ders raporunun kod hali, şimdilik lokal)
- [x] README'yi UTF-8'e çevir, "Master's Thesis" ifadesini düzelt, tekrar üretim talimatlarını ekle
- [x] `.gitignore`: `.venv/`, `data/` ve `models/` yok sayılıyor; `results/` altındaki özet tablolar (csv/md) takip ediliyor, ham loglar edilmiyor. `__pycache__` repodan çıkarıldı. Makale klasörü `manuscript/` olacak (`paper*` deseni yüzünden).
- [x] `report.pdf` repoya alınmayacak; lokal untracked kalacak (tüm fazlardan sonra v1/v2 kıyası için saklanıyor).
- [x] Python 3.14'e uygun pinler (`numpy==2.2.6`'nın 3.14 için wheel'i yok, bu yüzden güncellendi); `seaborn` ve `pytest` eklendi. v1 sonuçları yeni sürümlerle de birebir aynı.

### Faz 1 — v1'i tekrar üretilebilir hale getir (davranış değişikliği yok)
- [x] `evaluate_models.py` giriş noktasını düzelt (1.3-a); `--out-dir` ve `--verbose` eklendi
- [x] `data_generator.py`'a seed parametresi ekle (1.3-b): `--seed`, `--out`, `--stats-out`
- [x] Tek komutla `generate → train → evaluate`: `./run_all.sh` (~20 sn)
- [x] v1 sonuçlarını `results/v1/` altına CSV olarak üret. Greedy 54.62±6.00 % / 20.52±4.73 ms ve Smart 53.39±7.03 % / 8.56±2.02 ms, Tablo III ile birebir aynı. XGB 54.44 % / 12.68 ms (rapor: 54.08 % / 12.72 ms).
- [x] Kabul kriteri: `models/`, `data/` ve `results/v1` silinip yeniden koşulduğunda `evaluation_summary.csv` bit düzeyinde aynı çıkıyor.

### Faz 2 — Refactor (davranışı koruyan) ✅
- [x] `src/placement.py`: kopyasız `ResourceState` overlay, `route`, `feasible_hosts`, `build_chain`, `commit`/`release`, tipli `PlacementResult` (tuple ve `len(res)==2` yamaları kalktı). Algoritmalar grafiği değiştirmiyor; commit ve release motorda.
- [x] Algoritmalar "VNF başına düğüm sıralaması + seçici" olarak aynı çekirdeği kullanıyor: greedy, smart, random, kdn; ablasyonlar `kdn-nogate`, `cands-oracle`, `cands-first`, `cands-random` (`src/algorithms/__init__.py` registry).
- [x] `src/features.py`: tek özellik kaynağı; `MAX_CPU` yerine düğümdeki `cpu_max` kullanılıyor; pickle'lı LabelEncoder yerine sabit `SFC_CODES` (aynı kodlama).
- [ ] ~~Topoloji gecikmeleri / SNDlib doğrulaması~~ → davranış değiştirdiği için **Faz 4'e taşındı** (v2 kurgusu).
- [x] `src/experiment.py` + `scripts/evaluate.py`: JSON ile (algoritma × seed × λ) gridi, paralel koşu (`--jobs`), `runs.csv`, `summary.csv/md` (ortalama, ddof=1 std, %95 t-CI), eşleştirilmiş Wilcoxon (`reference` alanı), istek bazlı kayıt (`save_requests`).
- [x] `src/training.py` + `scripts/train.py`: eğitim notebook'tan betiğe taşındı; precision/recall/confusion kaydediliyor, önem grafiği `gain` ile çiziliyor. Notebook'lar, `main.py`, `evaluate_models.py`, `data_generator.py`, `src/utils` kaldırıldı (hepsi `v1-course-report` tag'inde).
- [x] Testler (`pytest`, 30 test, ~2 sn):
  - [x] kaynak korunumu: tüm SFC'ler bitince kapasiteler başlangıca dönüyor (8 algoritma)
  - [x] negatif kapasite asla oluşmuyor
  - [x] determinizm: aynı seed ile aynı sonuç
  - [x] regresyon: greedy, smart **ve kdn**, orijinal v1 koduyla tohum bazında birebir aynı (`tests/fixtures/v1_course_report_runs.csv`)
- [x] Kabul kriteri: Faz 1 tablosu refactor sonrası değişmeden üretiliyor. Ablasyon varyantları da /tmp'deki ön deneyle birebir aynı.

### Faz 3 — Dürüst değerlendirme protokolü (v1 modeli üzerinde) ✅
Detaylı bulgular (İngilizce, makaleye taşınabilir): [`results/v1_findings.md`](results/v1_findings.md)
- [x] 30 seed, eşleştirilmiş Wilcoxon testi, %95 t-CI, ddof=1 std (`experiments/v1_sweep.json`, 1200 koşu, ~75 sn)
- [x] Ufuk 10000, warm-up 1200 (2×max_duration) atılıyor
- [x] Yük taraması: λ ∈ {0.02, 0.05, 0.1, 0.2, 0.4} → kabul oranı %100 / 99 / 76 / 47 / 27
- [x] Ablasyonlar: random, greedy, smart, cands-random, cands-first, cands-oracle, kdn-nogate, kdn
- [x] Metrikler: sayıya göre kabul, **CPU ağırlıklı kabul** (yeni), SFC tipine göre kabul ve gecikme, gecikme ortalaması ve p95, aktif düğüm, karar süresi
- [x] Sınıflandırıcı: kronolojik bölme, ROC-AUC, trivial baseline'lar (`scripts/analyze_models.py` → `results/v1_models/`)
- [x] Gatekeeper analizi: SFC tipine göre ret oranı, Greedy'ye göre yanlış ret payı
- [x] Özellik katkıları: SHAP (TreeSHAP `pred_contribs`) ve gain
- [x] Karar kalitesi: regressor, gerçek en iyi adayı ne sıklıkla seçiyor ve ortalama kaç ms kaybettiriyor (regret)
- [x] Kabul kriteri: 1.2'deki ön bulgular doğrulandı ve genişletildi:
  - **F1:** KDN her yükte Greedy'yi yeniyor (−4…−11 ms) ama Smart'ı **hiçbir yükte** yenemiyor (+4.6…+7.5 ms, 30/30 seed).
  - **F2:** Darboğaz seçim değil, aday kümesi. Aynı 5 aday içinden gerçek gecikmeye göre seçim (oracle) KDN'den 0.8–1.5 ms iyi, ama o da Smart'tan 3.7–6 ms kötü. Regressor kararların %82.6'sında doğru adayı seçiyor; ortalama kayıp 1.6 ms.
  - **F3:** Gatekeeper'ın kabul "kazancı" sayım artefaktı. Büyük SFC'leri (Video) reddederek sayıyı artırıyor; CPU ağırlıklı kabulde ise gatekeeper'ı kapatmak daha iyi.
  - **F4:** Gatekeeper ile logistic regresyon neredeyse eşit. Regressor'ın kararlarını pratikte iki aksiyon özelliği belirliyor (sadece bunlarla doğrusal model R² 0.76). Rapordaki "network_free_bw en önemli özellik" yorumu `weight` metriğinden kaynaklanan bir yanılgıydı.

### Faz 4 — Yöntem iyileştirmesi (ML'nin gerçekten değer katabileceği kurgu)
Faz 3 çıkarımları (v1_findings "Implications"): (1) ML, kontrolcünün kapalı formda hesaplayamadığı bir şeyi öğrenmeli; (2) aday kümesi güçlü olmalı (Smart'ın kendi yerleşimi dahil); (3) ayarlanmış (tuned) yük-bilinçli bir heuristic baseline olmalı; (4) CPU ağırlıklı kabul raporlanmalı.

**4A: Gerçekçi gecikme modeli ve v2 politikası.**
- [ ] Topoloji: sabit ve coğrafi link gecikmeleri (train ve eval aynı topoloji); SNDlib Abilene kenar listesinin doğrulanması
- [ ] Her SFC isteğine ingress/egress düğümü; gecikme = ingress→VNF1 + VNF'ler arası + VNFn→egress + Σ işleme gecikmesi
- [ ] VNF işleme gecikmesi düğüm yüküne bağlı ve doğrusal olmayan bir fonksiyon (M/M/1 benzeri `base/(1−ρ)` + gürültü); kontrolcü bu fonksiyonu bilmiyor, telemetride sadece ölçülen gecikme görünüyor
- [ ] Yönlendirme gecikme ağırlıklı (`weight='delay'`)
- [ ] Aday üreteci: Smart-v2 (yayılım gecikmesi + wake-up), load-balanced, co-location, k-shortest ve random varyantları
- [ ] Aday bazlı özellikler: yayılım gecikmesi toplamı, hop, seçilen düğümlerin kullanım oranları (max/mean), path bottleneck BW, düğüm başına VNF sayısı
- [ ] Baseline'lar: Greedy, Smart-v2 (yükü bilmiyor), **Smart-load(α)** (kullanım cezası; α grid search ile ayarlanmış, en iyi α raporlanacak), Oracle (gerçek gecikmeyi bilen seçici, üst sınır), KDN-v2
- [ ] Gatekeeper: CPU ağırlıklı kabulle yeniden değerlendirilecek; fayda yoksa v2'den çıkarılıp Discussion'da anlatılacak
- [ ] Değerlendirme: Faz 3 protokolüyle (30 seed, λ taraması, paired test)

**4B (opsiyonel):** kapalı döngü yeniden eğitim (KDN kendi telemetrisiyle, 2–3 iterasyon).

- [ ] Kabul kriteri: v2 sonuçları Faz 3 protokolüyle üretilmiş ve bulgular `results/v2_findings.md` dosyasına yazılmış.

### Faz 5 — Makale (LaTeX, `manuscript/`)
- [ ] `IEEE Conference Template Latex.zip` → `manuscript/` (IEEEtran, `\documentclass[conference,a4paper]{IEEEtran}`). `.docx` kullanılmayacak.
- [ ] Tüm şekiller `scripts/make_figures.py` ile CSV'lerden üretilsin (elle çizim yok); vektör PDF formatında, tek tip renk ve font
- [ ] Bölüm planı (ödev başlıklarıyla eşleşmeli):
  - [ ] **Title.** Yeni başlık (ör. *"Where Does Learning Help? A Knowledge-Defined Networking Approach to Load-Aware VNF Placement"*)
  - [ ] **Abstract.** Sayılar Faz 3/4'ten; abartısız
  - [ ] **I. Introduction (+ Related Work).** Motivasyon, KDN, katkılar; related work: exact/ILP, heuristic, DRL, GNN/RouteNet, KDN uygulamaları
  - [ ] **II. Material and Methods.** Topoloji, SFC kataloğu, gecikme modeli (v1 ve v2), simülatör, veri üretimi, iki aşamalı model, aday üretimi, baseline ve ablasyonlar, değerlendirme protokolü ve istatistik
  - [ ] **III. Experimental Results.** Sınıflandırıcı/regressor kalitesi, ana tablo, λ taraması, ablasyon, gatekeeper analizi, karar süresi
  - [ ] **IV. Conclusion (Future Work)**
  - [ ] **V. Discussion.** v1'in neden ML'den fayda görmediği, oracle argümanı, tehditler (validity threats: tek topoloji, sentetik trafik, basit kuyruk modeli), etik ve tekrar üretilebilirlik notu
  - [ ] **Acknowledgements.** Danışman; önceki ders projesinden türetildiği; (politika uygunsa) AI-araç beyanı
  - [ ] **References.** BibTeX (`refs.bib`), her kaynak tek tek doğrulanacak (DOI ve sayfa)
- [ ] Literatür (doğrulanacak aday listesi; uydurma atıf olmaması için hepsi kontrol edilecek):
  - Mestres et al., *Knowledge-Defined Networking*, ACM SIGCOMM CCR 2017
  - Clark et al., *A Knowledge Plane for the Internet*, SIGCOMM 2003
  - Mijumbi et al., NFV survey, IEEE COMST 2016
  - Herrera & Botero, *Resource Allocation in NFV: A Comprehensive Survey*, IEEE TNSM 2016
  - Laghrissi & Taleb, VNF placement survey, IEEE COMST 2019
  - Moens & De Turck, *VNF-P*, CNSM 2014; Bari et al., *On orchestrating VNFs*, CNSM 2015
  - Pei et al., DRL-based VNF placement (IEEE JSAC 2020); Mao et al., DeepRM (HotNets 2016)
  - Rusek et al., *RouteNet* (SOSR 2019 / IEEE JSAC 2020)
  - Orlowski et al., *SNDlib 1.0*, Networks 2010; Knight et al., *Topology Zoo*, JSAC 2011
  - Chen & Guestrin, *XGBoost*, KDD 2016; Lundberg & Lee, SHAP, NeurIPS 2017
- [ ] Sayfa limiti ve teslim tarihini ödev metninden veya danışmandan teyit et

### Faz 6 — Kalite kontrol ve teslim
- [ ] Temiz klon → `run_all` → `make_figures` → `latexmk` zincirinin hatasız çalıştığını doğrula
- [ ] Makaledeki her sayının bir CSV satırına izlenebilir olduğunu kontrol et
- [ ] Atıf kontrolü (her referansın gerçekten var olduğu ve doğru bilgilerle yazıldığı)
- [ ] `v2-seminar` tag'i; branch'i PR ile `main`'e birleştir (veya ayrı bırak)

---

## 4. Açık Kararlar

| # | Karar | Öneri | Durum |
|---|---|---|---|
| D1 | Teslim tarihi ve sayfa limiti | — | ✅ 24 Kasım 23:00; 4–8 sayfa IEEE conf |
| D2 | Faz 4 kapsamı: 4A mı, 4A+4B mi, yoksa sadece Faz 3 (dürüst yeniden değerlendirme)? | 4A (zaman kalırsa 4B) | ✅ Faz 4 dahil, sonuna kadar; gain çıkmazsa tartışılacak |
| D3 | Topoloji gecikmeleri: sabit seed ile rastgele mi, coğrafi mesafeden mi? | coğrafi (SNDlib koordinatları) | ❓ |
| D4 | İkinci topoloji (GÉANT) eklensin mi? | Faz 4 bitince, zaman kalırsa | ❓ |
| D5 | AI-araç kullanım beyanı ve önceki projeden türetme beyanı | Danışmana sor | ❓ |
| D6 | Danışmana verilen özetteki beklenti tutmazsa nasıl çerçevelenecek? | Discussion'da açıkça; özeti güncellemek için danışmanla konuş | ❓ |

---

## 5. İlerleme Günlüğü

| Tarih | Faz | Not |
|---|---|---|
| 2026-11-19 | 0 | Kod ve rapor incelendi, v1 tekrar üretildi, ablasyon ön deneyi yapıldı, rollout planı yazıldı. |
| 2026-11-19 | 3 | `faz-3-evaluation`: λ taraması, 8 algoritma × 30 seed, model analizi, CPU ağırlıklı kabul; bulgular `results/v1_findings.md`. |
| 2026-11-19 | 2 | `faz-2-refactor`: ortak çekirdek, registry, deney koşucusu, testler; v1 tohum bazında birebir korunuyor. README gerçekten UTF-8'e çevrildi (Faz 1'de kodlama korunmuştu). Push bu ortamdan yapılamadı (GitHub kimlik bilgisi yok), kullanıcı push edecek. |
| 2026-11-19 | 0–1 | `faz-01-reproducibility` branch'i: hijyen, seed ve CLI eklendi, `run_all.sh` yazıldı, v1 sonuçları `results/v1/` altında. Teslim tarihi: **24 Kasım 23:00** (D1); kapsam Faz 4 dahil (D2). |
