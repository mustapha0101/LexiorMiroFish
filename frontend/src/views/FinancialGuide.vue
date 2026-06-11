<template>
  <div class="guide-container">
    <!-- Navigation Bar -->
    <nav class="navbar">
      <div class="nav-brand" @click="router.push('/')">
        <img src="/logo.png" class="brand-logo" alt="Lexior" />
        <span class="brand-name">{{ $t('common.brandFirst') }} <span class="brand-sub">{{ $t('common.brandSecond') }}</span></span>
      </div>
      <div class="nav-links">
        <button class="back-btn" @click="router.push('/')">
          ← {{ $t('common.back') || 'Retour' }}
        </button>
        <LanguageSwitcher />
      </div>
    </nav>

    <!-- Main Grid Content -->
    <div class="guide-grid">
      <!-- Sidebar Index -->
      <aside class="sidebar-index">
        <div class="sidebar-title">TABLE DES MATIÈRES</div>
        <ul class="index-list">
          <li v-for="(sec, idx) in sections" :key="idx" :class="{ active: activeSection === sec.id }" @click="scrollToSection(sec.id)">
            <span class="sec-num">0{{ idx + 1 }}</span>
            <span class="sec-name">{{ sec.title }}</span>
          </li>
        </ul>
      </aside>

      <!-- Main Body -->
      <main class="scientific-body">
        <header class="paper-header">
          <div class="rd-tag">GUIDE OFFICIEL</div>
          <h1 class="paper-title">
            Guide d'Interprétation Financière & Évaluation d'Aléa Judiciaire
          </h1>
          <div class="paper-subtitle">
            Cadre de calcul des dépens, honoraires extrajudiciaires et arbitrage Monte-Carlo
          </div>
          <div class="paper-meta">
            <span><strong>Version :</strong> 2026.1</span>
            <span><strong>Système :</strong> Lexior PIE Engine</span>
            <span><strong>Juridictions :</strong> Québec (C.p.c.) / Canada</span>
          </div>
        </header>

        <!-- Section 1 -->
        <section id="section1" class="paper-section">
          <h2><span>01.</span> Introduction à l'Aléa Judiciaire</h2>
          <p>
            Pour le C-Suite et les Conseils d'Administration, un litige juridique n'est pas seulement un débat sur le droit positif, c'est avant tout un <strong>risque de bilan</strong> (bilan passif / provision pour risques et charges). Les avocats parlent le langage de la procédure, mais les dirigeants d'entreprise parlent le langage des chiffres et des probabilités.
          </p>
          <p>
            <strong>Lexior Simulator</strong> comble cette rupture de communication en traduisant une probabilité d'issue juridique (issue de nos simulations de Monte-Carlo face à des jumeaux de juges) en une exposition financière nette projetée dans le temps.
          </p>
        </section>

        <!-- Section 2 -->
        <section id="section2" class="paper-section">
          <h2><span>02.</span> Évaluation des Coûts : Le Cadre du Québec (C.p.c.)</h2>
          <p>
            Au Québec, les coûts d'un procès sont régis par le <em>Code de procédure civile</em> (C.p.c.) et se divisent en deux catégories strictes :
          </p>
          
          <h3>2.1 Les Dépens (Frais de Justice)</h3>
          <p>
            Selon l'article 339 C.p.c., la partie perdante assume les dépens de la partie gagnante. Lexior calcule automatiquement ces dépens selon le **Tarif des frais judiciaires en matière civile** en fonction de la classe du litige :
          </p>
          <ul>
            <li><strong>Classe I (0,01 $ à 15 000 $)</strong> : Droits de greffe de 112 $ (personne physique) ou 186 $ (morale).</li>
            <li><strong>Classe II (15 000,01 $ à 85 000 $)</strong> : Droits de greffe de 224 $ (physique) ou 345 $ (morale).</li>
            <li><strong>Classe III (85 000,01 $ à 300 000 $)</strong> : Droits de greffe de 336 $ (physique) ou 485 $ (morale).</li>
            <li><strong>Classe IV (300 000,01 $ et plus)</strong> : Droits de greffe de 520 $ (physique) ou 750 $ (morale).</li>
          </ul>

          <h3>2.2 Les Honoraires Extrajudiciaires</h3>
          <p>
            Au Québec, chacun assume ses honoraires d'avocat, peu importe l'issue du litige. L'exception unique réside dans l'<strong>abus de procédure</strong> (art. 51 et 342 C.p.c.), où le juge condamne le perdant au remboursement intégral des honoraires d'avocat de l'autre partie. Lexior estime cette probabilité selon le profil d'agressivité de la partie adverse.
          </p>
        </section>

        <!-- Section 3 -->
        <section id="section3" class="paper-section">
          <h2><span>03.</span> Évaluation des Coûts : Provinces de Common Law</h2>
          <p>
            Dans les autres provinces canadiennes (Ontario, Colombie-Britannique), le régime de transfert des coûts (fee-shifting) s'applique selon trois échelles d'indemnisation :
          </p>
          <div class="verrous-list">
            <div class="verrou-card">
              <div class="verrou-icon">⚖️</div>
              <h4>Indemnité Partielle</h4>
              <p>Le perdant rembourse environ 60% des frais d'avocat du gagnant. C'est le tarif standard appliqué par les tribunaux.</p>
            </div>
            <div class="verrou-card">
              <div class="verrou-icon">⚡</div>
              <h4>Indemnité Substantielle</h4>
              <p>Remboursement à hauteur d'environ 80%. Déclenché si une offre de règlement (Rule 49) a été indûment rejetée.</p>
            </div>
            <div class="verrou-card">
              <div class="verrou-icon">🔥</div>
              <h4>Indemnité Totale</h4>
              <p>Remboursement à 100% des honoraires de l'adversaire. Réservé aux comportements malicieux ou de mauvaise foi.</p>
            </div>
          </div>
        </section>

        <!-- Section 4 -->
        <section id="section4" class="paper-section">
          <h2><span>04.</span> Modélisation de l'Espérance Mathématique (EV)</h2>
          <p>
            Le simulator utilise la méthode de Monte-Carlo pour intégrer le risque de perte et calculer l'<strong>Espérance Mathématique de Gain (Expected Value - EV)</strong> :
          </p>
          <div class="formula-box">
            EV = ( P<sub>win</sub> &times; Gain_Net<sub>Win</sub> ) + ( P<sub>loss</sub> &times; Perte_Nette<sub>Loss</sub> )
          </div>
          <p>Où :</p>
          <ul>
            <li><strong>Gain_Net<sub>Win</sub></strong> : Montant réclamé $-$ Nos honoraires d'avocat $+$ Remboursement des dépens/frais par l'adversaire.</li>
            <li><strong>Perte_Nette<sub>Loss</sub></strong> : $0$ $-$ Nos honoraires d'avocat $-$ Honoraires ou dépens à rembourser à l'adversaire.</li>
          </ul>
        </section>

        <!-- Section 5 -->
        <section id="section5" class="paper-section">
          <h2><span>05.</span> Comment Interpréter le Quadrant de Risque</h2>
          <p>
            La <strong>Matrice des Risques Judiciaires</strong> à bulles classe les risques selon deux facteurs : leur probabilité de survenance et leur impact financier.
          </p>
          <div class="concept-vulgarization">
            <div class="vulgarization-title">💡 Lecture de la Matrice des Risques</div>
            <p class="vulgarization-text">
              <strong>1. Quadrant Éviter (Haut-Droite)</strong> : Risque majeur. Forte probabilité et fort coût. Indique une urgence critique à transiger (règlement amiable immédiat).<br>
              <strong>2. Quadrant Atténuer (Haut-Gauche)</strong> : Impact élevé mais faible probabilité. Demande une préparation minutieuse des éléments de preuve.<br>
              <strong>3. Quadrant Transférer (Bas-Droite)</strong> : Probabilité élevée mais impact financier faible. Souvent couvert par des assurances ou géré à faible coût.<br>
              <strong>4. Quadrant Accepter (Bas-Gauche)</strong> : Risque faible et impact minime. Aucune action stratégique requise.
            </p>
          </div>
        </section>

        <!-- Section 6 -->
        <section id="section6" class="paper-section">
          <h2><span>06.</span> Méthodologie d'Arbitrage et de Règlement</h2>
          <p>
            La justification d'un règlement amiable repose sur une preuve mathématique simple : si la valeur actuelle nette d'une offre amiable d'un montant de $X$ (déduction faite des frais d'avocat déjà engagés) est supérieure à l'EV du procès, la transaction est mathématiquement supérieure.
          </p>
          <p>
            Cela permet aux associés de cabinets de présenter une recommandation dénuée d'émotion à leurs clients, fondée sur des certitudes statistiques calculées sur plus de 100 simulations de juges différents.
          </p>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const router = useRouter()
const activeSection = ref('section1')

const sections = [
  { id: 'section1', title: '01. Aléa Judiciaire' },
  { id: 'section2', title: '02. Cadre du Québec (C.p.c.)' },
  { id: 'section3', title: '03. Provinces de Common Law' },
  { id: 'section4', title: '04. Espérance Mathématique (EV)' },
  { id: 'section5', title: '05. Quadrant de Risque' },
  { id: 'section6', title: '06. Méthode d\'Arbitrage' }
]

const scrollToSection = (id) => {
  activeSection.value = id
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

onMounted(() => {
  const observerOptions = {
    root: null,
    rootMargin: '-10% 0px -70% 0px',
    threshold: 0
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        activeSection.value = entry.target.id
      }
    })
  }, observerOptions)

  sections.forEach(sec => {
    const el = document.getElementById(sec.id)
    if (el) observer.observe(el)
  })
})
</script>

<style scoped>
.guide-container {
  --obsidian: #05080C;
  --gold: #D4AF37;
  --gold-dim: #A88725;
  --panel-bg: #0C121D;
  --border-color: #1A2333;
  --text-main: #E2E8F0;
  --text-muted: #8A99AD;
  
  min-height: 100vh;
  background: var(--obsidian);
  color: var(--text-main);
  font-family: 'Inter', system-ui, sans-serif;
}

/* Navbar */
.navbar {
  height: 60px;
  background: #0B1220;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.brand-logo {
  height: 24px;
}

.brand-name {
  font-family: 'Playfair Display', serif;
  font-weight: 700;
  font-size: 1.25rem;
  color: #FFFFFF;
}

.brand-sub {
  color: var(--gold);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 6px 16px;
  font-size: 0.85rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  border-color: var(--gold);
  color: var(--gold);
}

/* Layout */
.guide-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
  gap: 40px;
}

/* Sidebar Index */
.sidebar-index {
  position: sticky;
  top: 100px;
  height: fit-content;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 24px;
}

.sidebar-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--gold);
  letter-spacing: 2px;
  margin-bottom: 20px;
}

.index-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.index-list li {
  display: flex;
  gap: 12px;
  font-size: 0.9rem;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.2s;
  align-items: flex-start;
}

.index-list li:hover {
  color: var(--text-main);
}

.index-list li.active {
  color: var(--gold);
  font-weight: 600;
}

.sec-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  opacity: 0.6;
}

.index-list li.active .sec-num {
  opacity: 1;
}

/* Scientific Body */
.scientific-body {
  max-width: 900px;
}

.paper-header {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 30px;
  margin-bottom: 40px;
}

.rd-tag {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--gold);
  border: 1px solid var(--gold);
  padding: 3px 8px;
  border-radius: 3px;
  margin-bottom: 16px;
  letter-spacing: 1px;
}

.paper-title {
  font-family: 'Playfair Display', serif;
  font-size: 2.2rem;
  line-height: 1.3;
  color: #FFFFFF;
  margin: 0 0 16px 0;
}

.paper-subtitle {
  font-size: 1.15rem;
  color: var(--text-muted);
  margin-bottom: 24px;
}

.paper-meta {
  display: flex;
  gap: 24px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* Sections */
.paper-section {
  margin-bottom: 50px;
}

.paper-section h2 {
  font-family: 'Playfair Display', serif;
  font-size: 1.5rem;
  color: #FFFFFF;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.paper-section h2 span {
  color: var(--gold);
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
}

.paper-section h3 {
  font-size: 1.15rem;
  color: var(--gold);
  margin: 24px 0 12px 0;
}

.paper-section p {
  font-size: 1.02rem;
  line-height: 1.65;
  color: var(--text-main);
  margin-bottom: 18px;
}

.paper-section ul {
  padding-left: 20px;
  margin-bottom: 20px;
}

.paper-section li {
  font-size: 1rem;
  line-height: 1.6;
  margin-bottom: 8px;
  color: var(--text-main);
}

.formula-box {
  background: #090E16;
  border-left: 3px solid var(--gold);
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  color: #FFFFFF;
  margin: 24px 0;
  border-radius: 0 6px 6px 0;
  text-align: center;
}

.verrous-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin: 24px 0;
}

.verrou-card {
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 20px;
  transition: border-color 0.2s;
}

.verrou-card:hover {
  border-color: var(--gold);
}

.verrou-icon {
  font-size: 1.5rem;
  margin-bottom: 12px;
}

.verrou-card h4 {
  color: #FFFFFF;
  margin: 0 0 8px 0;
  font-size: 1.05rem;
}

.verrou-card p {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin: 0;
  line-height: 1.5;
}

.concept-vulgarization {
  background: rgba(212, 175, 55, 0.03);
  border: 1px dashed rgba(212, 175, 55, 0.25);
  border-radius: 6px;
  padding: 20px;
  margin: 24px 0;
}

.vulgarization-title {
  font-weight: 700;
  color: var(--gold);
  margin-bottom: 10px;
}

.vulgarization-text {
  font-size: 0.95rem;
  color: var(--text-main);
  line-height: 1.5;
  margin: 0;
}
</style>
