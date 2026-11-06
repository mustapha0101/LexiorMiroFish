<template>
  <div class="home-container" :class="{ 'auth-bg': !session }">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand" @click="router.push('/')">
        <img src="/logo.png" class="brand-logo" alt="Lexior" />
        <span class="brand-name">{{ $t('common.brandFirst') }} <span class="brand-sub">{{ $t('common.brandSecond') }}</span></span>
      </div>
      <div class="nav-links">
        <router-link to="/research" class="nav-item-link">
          📚 {{ $t('nav.researchPaper') }}
        </router-link>
        <router-link to="/financial-guide" class="nav-item-link">
          ⚖️ {{ $t('nav.financialGuide') }}
        </router-link>
        <button 
          v-if="session" 
          class="signout-btn" 
          @click="loginGate?.handleSignOut"
        >
          🔑 {{ $t('auth.signOut') }}
        </button>
        <LanguageSwitcher />
      </div>
    </nav>

    <div class="main-content">
      <LoginGate ref="loginGate" @session-change="handleSessionChange">
        <!-- 上半部分：Hero 区域 -->
        <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag">{{ $t('home.tagline') }}</span>
            <span class="version-text">{{ $t('home.version') }}</span>
          </div>
          
          <h1 class="main-title">
            {{ $t('home.heroTitle1') }}<br>
            <span class="gradient-text">{{ $t('home.heroTitle2') }}</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              <i18n-t keypath="home.heroDesc" tag="span">
                <template #brand><span class="highlight-bold">{{ $t('home.heroDescBrand') }}</span></template>
                <template #agentScale><span class="highlight-orange">{{ $t('home.heroDescAgentScale') }}</span></template>
                <template #optimalSolution><span class="highlight-code">{{ $t('home.heroDescOptimalSolution') }}</span></template>
              </i18n-t>
            </p>
            <p class="slogan-text">
              {{ $t('home.slogan') }}<span class="blinking-cursor">_</span>
            </p>
            <div class="demo-hero-container">
              <button class="demo-load-btn" @click="loadDemoData">
                {{ $t('home.loadDemoBtn') }}
              </button>
              <button class="demo-preview-btn" @click="showDemoPreview = true">
                {{ $t('home.previewDemoBtn') }}
              </button>
            </div>
          </div>
           
          <div class="decoration-square"></div>
        </div>
        
        <div class="hero-right">
          <!-- Logo 区域 -->
          <div class="logo-container">
            <img src="/logo.png" alt="Lexior Logo" class="hero-logo" />
          </div>
          
          <button class="scroll-down-btn" @click="scrollToBottom">
            ↓
          </button>
        </div>
      </section>

      <!-- 下半部分：双栏布局 -->
      <section ref="dashboardSection" class="dashboard-section">
        <!-- 左栏：状态与步骤 -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> {{ $t('home.systemStatus') }}
          </div>
          
          <h2 class="section-title">{{ $t('home.systemReady') }}</h2>
          <p class="section-desc">
            {{ $t('home.systemReadyDesc') }}
          </p>
          
          <!-- 数据指标卡片 -->
          <div class="metrics-row">
            <div class="metric-card">
              <div class="metric-value">{{ stats.totalSimulations }}</div>
              <div class="metric-label">{{ $t('home.metricSimulationsRun') }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ stats.totalActors }}</div>
              <div class="metric-label">{{ $t('home.metricActorsSimulated') }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ stats.totalRounds }}</div>
              <div class="metric-label">{{ $t('home.metricRoundsRun') }}</div>
            </div>
          </div>

          <!-- 项目模拟步骤介绍 (新增区域) -->
          <div class="steps-container">
            <div class="steps-header">
               <span class="diamond-icon">◇</span> {{ $t('home.workflowSequence') }}
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step01Title') }}</div>
                  <div class="step-desc">{{ $t('home.step01Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step02Title') }}</div>
                  <div class="step-desc">{{ $t('home.step02Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step03Title') }}</div>
                  <div class="step-desc">{{ $t('home.step03Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step04Title') }}</div>
                  <div class="step-desc">{{ $t('home.step04Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">05</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step05Title') }}</div>
                  <div class="step-desc">{{ $t('home.step05Desc') }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右栏：交互控制台 -->
        <div class="right-panel">
          <div class="console-box">
            <!-- Exemples Prêts à Simuler en 1 Clic (SAAQ & Cour du Québec) -->
            <div class="console-section preset-cases-section">
              <div class="console-header">
                <span class="console-label">⚡ DOSSIERS PRÊTS À SIMULER EN 1 CLIC (SAAQ / TAQ & COUR DU QUÉBEC)</span>
                <span class="console-meta">L.A.A. / C.C.Q. / C.P.C.</span>
              </div>
              <div class="preset-cases-grid">
                <div
                  v-for="preset in legalPresets"
                  :key="preset.id"
                  class="preset-case-card"
                  :class="{ active: selectedPresetId === preset.id }"
                  @click="selectPresetCase(preset, false)"
                >
                  <div class="preset-card-top">
                    <span class="preset-badge" :class="preset.badgeClass">{{ preset.badge }}</span>
                    <span class="preset-quantum">{{ preset.claimAmount }}</span>
                  </div>
                  <div class="preset-title">{{ preset.title }}</div>
                  <div class="preset-subtitle">{{ preset.subtitle }}</div>
                  <div class="preset-actions" @click.stop>
                    <button class="preset-btn-load" @click="selectPresetCase(preset, false)">
                      📥 Charger
                    </button>
                    <button class="preset-btn-preview" @click="previewPresetCase(preset)">
                      👁️ Lire
                    </button>
                    <button class="preset-btn-run" @click="selectPresetCase(preset, true)">
                      ⚡ Simuler en 1 clic
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 上传区域 -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.realitySeed') }}</span>
                <span class="console-meta">{{ $t('home.supportedFormats') }}</span>
              </div>
              
              <div 
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />
                
                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">↑</div>
                  <div class="upload-title">{{ $t('home.dragToUpload') }}</div>
                  <div class="upload-hint">{{ $t('home.orBrowse') }}</div>
                </div>
                
                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 分割线 -->
            <div class="console-divider">
              <span>{{ $t('home.inputParams') }}</span>
            </div>

            <!-- Nom de la simulation (facultatif) -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.simulationNameLabel') }}</span>
              </div>
              <div class="input-wrapper">
                <input
                  v-model="formData.simulationName"
                  type="text"
                  class="code-input-single"
                  :placeholder="$t('home.simulationNamePlaceholder')"
                  :disabled="loading"
                />
              </div>
            </div>

            <!-- 输入区域 -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.simulationPrompt') }}</span>
              </div>
              <div class="input-wrapper">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  :placeholder="$t('home.promptPlaceholder')"
                  rows="6"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">{{ $t('home.engineBadge') }}</div>
              </div>
            </div>

            <!-- Options de Simulation -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.simulationMode') }}</span>
              </div>
              <div class="mode-selector-grid">
                <div 
                  class="mode-card" 
                  :class="{ active: formData.simulationMode === 'social' }"
                  @click="formData.simulationMode = 'social'"
                >
                  <div class="mode-card-header">
                    <span class="mode-icon">💬</span>
                    <span class="mode-title">{{ $t('home.modeSocial') }}</span>
                  </div>
                  <p class="mode-desc">{{ $t('home.modeSocialDesc') }}</p>
                </div>

                <div 
                  class="mode-card" 
                  :class="{ active: formData.simulationMode === 'legal', 'legal-card-active': formData.simulationMode === 'legal' }"
                  @click="formData.simulationMode = 'legal'"
                >
                  <div class="mode-card-header">
                    <span class="mode-icon">⚖️</span>
                    <span class="mode-title">{{ $t('home.modeLegal') }}</span>
                  </div>
                  <p class="mode-desc">{{ $t('home.modeLegalDesc') }}</p>
                </div>
              </div>
            </div>

            <!-- 启动按钮 -->
            <div class="console-section btn-section">
              <button 
                class="start-engine-btn"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span v-if="!loading">{{ $t('home.startEngine') }}</span>
                <span v-else>{{ $t('home.initializing') }}</span>
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>
      </section>

        <!-- 历史项目数据库 -->
        <HistoryDatabase />
      </LoginGate>
    </div>

    <!-- Modal de prévisualisation du cas de démonstration -->
    <div v-if="showDemoPreview" class="preview-modal-overlay" @click.self="showDemoPreview = false">
      <div class="preview-modal-box">
        <div class="preview-modal-header">
          <h3 class="preview-modal-title">📄 {{ activePreviewTitle }}</h3>
          <button class="preview-modal-close-btn" @click="showDemoPreview = false">×</button>
        </div>
        <div class="preview-modal-body">
          <pre class="preview-modal-text">{{ activePreviewContent }}</pre>
        </div>
        <div class="preview-modal-footer">
          <button class="preview-modal-cancel-btn" @click="showDemoPreview = false">
            {{ $t('common.close') }}
          </button>
          <button class="preview-modal-confirm-btn" @click="loadDemoAndClose">
            ⚡ Charger dans le simulateur
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import LoginGate from '../components/LoginGate.vue'
import { getSimulationHistory } from '../api/simulation'

const router = useRouter()
const loginGate = ref(null)
const session = ref(null)
const { t } = useI18n()

const selectedPresetId = ref('')
const previewPreset = ref(null)

const legalPresets = [
  {
    id: 'saaq_1_irr_taq',
    badge: 'SAAQ / TAQ #1',
    badgeClass: 'badge-saaq',
    claimAmount: '84 600 $',
    title: 'Pelletier c. SAAQ — Fin d\'IRR & État préexistant',
    subtitle: 'Art. 2, 14, 49 et 73 L.a.a. | Arrêt Productions Pram (Décompensation lombaire L4-S1 vs arthrose)',
    fileName: 'dossier_saaq_1_pelletier_irr_etat_preexistant_taq.txt',
    simulationName: 'SAAQ #1 — Pelletier c. SAAQ (Fin IRR & État préexistant - TAQ)',
    requirement: 'Simuler l\'audience contradictoire devant le Tribunal administratif du Québec (TAQ - Section des affaires sociales) dans le recours de Marc-André Pelletier contre la Société de l\'assurance automobile du Québec (SAAQ). Évaluer la demande totale de 84 600,00 $ (65 800 $ d\'arrérages d\'IRR sous l\'art. 14 L.a.a., 14 300 $ de séquelles permanentes classe 3 sous l\'art. 73 L.a.a. et 4 500 $ de frais) face à la défense de la SAAQ fondée sur l\'état dégénératif préexistant (IRM D-3, expertise D-4) et la fin d\'IRR sous l\'art. 49 L.a.a.',
    content: `DOSSIER DE LITIGE ADMINISTRATIF ET MÉDICO-LÉGAL (SAAQ / TAQ - SECTION DES AFFAIRES SOCIALES)
Juridiction : Tribunal administratif du Québec (TAQ) — Révision d'une décision de la Société de l'assurance automobile du Québec (SAAQ)
Nature du recours : Contestation en vertu de l'article 83.34 de la Loi sur l'assurance automobile (RLRQ c. A-25, L.a.a.) et du Code civil du Québec (fardeau de preuve art. 2803 et 2804 C.c.Q.).

PARTIES EN CAUSE :
- Partie Requérante (Demandeur) : Monsieur Marc-André Pelletier, charpentier-menuisier (48 ans).
- Partie Intimée (Défenderesse) : Société de l'assurance automobile du Québec (SAAQ).

1. FAITS ADMIS ET CHRONOLOGIE DE L'ACCIDENT :
- Le 14 janvier 2024 (Pièce P-1 : Rapport d'accident de police), le véhicule de Monsieur Pelletier est percuté à l'arrière à une vitesse estimée à 45 km/h alors qu'il était immobilisé à un feu rouge.
- À l'urgence (Pièce P-2 : Feuille sommaire d'urgence du 14 janvier 2024), le médecin diagnostique une entorse cervico-lombaire de grade II (whiplash) sans fracture visible à la radiographie simple.
- La SAAQ accepte initialement la réclamation en vertu des articles 2 et 14 L.a.a. et verse une indemnité de remplacement du revenu (IRR) de 1 175,00 $ par semaine à compter du 21 janvier 2024.
- Une IRM lombaire réalisée le 18 mai 2024 (Pièce D-3 : Rapport d'imagerie par résonance magnétique) révèle une discopathie dégénérative pluri-étagée L4-L5 et L5-S1 avec arthrose facettaire modérée et protrusion discale L5-S1 sans compression radiculaire franche.
- Le 12 septembre 2024, à la suite de l'expertise du médecin évaluateur de la SAAQ, le Dr Bruno Lavigne, orthopédiste (Pièce D-4), la SAAQ rend une décision en révision (Pièce D-5) mettant fin à l'IRR en vertu de l'article 49 L.a.a., au motif que l'entorse lombaire causée par l'accident est consolidée sans séquelle permanente (0 % SUTT sous l'art. 73 L.a.a.) et que les douleurs persistantes découlent exclusivement de l'état dégénératif préexistant personnel de M. Pelletier.

2. PRÉTENTIONS ET MONTANTS RÉCLAMÉS PAR LE REQUÉRANT (DEMANDE TOTALE : 84 600,00 $) :
- M. Pelletier dépose une contre-expertise du Dr Henri Courchesne, physiatre (Pièce P-6), soutenant que son état dégénératif lombaire était totalement asymptomatique avant l'accident du 14 janvier 2024 (attesté par son dossier CNESST vierge et ses 2 000 heures travaillées en 2023, Pièce P-7) et que l'accident a agi comme facteur déclencheur ayant décompensé de façon permanente sa colonne lombaire (jurisprudence Productions Pram inc. c. Lemay).
- Conclusions chiffrées de la demande devant le TAQ (Total réclamé : 84 600,00 $) :
  a) Rétroactivité et maintien de l'indemnité de remplacement du revenu (IRR, art. 14 L.a.a.) sur 56 semaines (65 800,00 $) ;
  b) Indemnité forfaitaire pour préjudice non pécuniaire / séquelles permanentes de classe 3 au rachis lombaire en vertu de l'article 73 L.a.a. et du Règlement sur le barème des dommages corporels (14 300,00 $) ;
  c) Remboursement intégral des frais d'expertise privée et frais de traitements chiropratiques non autorisés (4 500,00 $).

3. MOYENS DE DÉFENSE DE LA SAAQ (INTIMÉE) :
- La SAAQ soutient que la présomption de simultanéité (post hoc ergo propter hoc) ne suffit pas à établir le lien causal médical requis par l'article 2 L.a.a. et l'article 2803 C.c.Q.
- Selon le rapport biomécanique et orthopédique D-4, une entorse lombaire de grade II se résorbe physiologiquement en 6 à 12 semaines ; l'absence d'oedème osseux traumatique à l'IRM D-3 démontre que la protrusion L5-S1 est d'origine purement dégénérative et évolue pour son propre compte.
- Subsidiairement, même si le Tribunal reconnaissait une aggravation temporaire ou une séquelle résiduelle mineure de classe 1 (douleurs intermittentes, ~3 200 $ sous l'art. 73 L.a.a.), M. Pelletier avait recouvré la capacité d'exercer un emploi convenable léger au plus tard à la date du rapport D-4 (art. 45 et 49 L.a.a.), et les traitements chiropratiques réclamés ne respectent pas les conditions réglementaires de prescription médicale préalable.`
  },
  {
    id: 'saaq_2_emploi_convenable',
    badge: 'SAAQ / TAQ #2',
    badgeClass: 'badge-saaq',
    claimAmount: '69 200 $',
    title: 'Arsenault c. SAAQ — Capacité d\'exercer un emploi convenable',
    subtitle: 'Art. 45 et 49 L.a.a. | Camionneuse lourde réorientée comme commis à la répartition',
    fileName: 'dossier_saaq_2_arsenault_emploi_convenable_art45.txt',
    simulationName: 'SAAQ #2 — Arsenault c. SAAQ (Emploi convenable art. 45 L.a.a.)',
    requirement: 'Simuler l\'audience contradictoire devant le Tribunal administratif du Québec (TAQ) dans le litige opposant Sophie Arsenault à la SAAQ concernant la détermination d\'un emploi convenable de commis à la répartition (art. 45 et 49 L.a.a.). Évaluer la demande totale de 69 200,00 $ (62 400 $ d\'arrérages d\'IRR et 6 800 $ de frais d\'évaluation privée) face à l\'autorité de la chose jugée sur les limitations fonctionnelles reconnues (Pièce P-2).',
    content: `DOSSIER DE LITIGE SAAQ #2 — CAPACITÉ D'EXERCER UN EMPLOI CONVENABLE (ART. 45 ET 49 L.A.A.)
Juridiction : Tribunal administratif du Québec (TAQ - Section des affaires sociales)
Nature du litige : Contestation de la détermination d'un emploi convenable de répartiteur en transport (art. 45 L.a.a.) et de la fin de l'Indemnité de remplacement du revenu (IRR, art. 49 L.a.a.).

PARTIES :
- Requérante (Demanderesse) : Madame Sophie Arsenault, conductrice de camion lourd semi-remorque (54 ans, scolarité de Secondaire IV).
- Intimée (Défenderesse) : Société de l'assurance automobile du Québec (SAAQ).

1. FAITS ET PIÈCES AU DOSSIER :
- Le 3 novembre 2022, Mme Arsenault subit une fracture comminutive de l'épaule droite lors d'une collision frontale sur l'autoroute 20 (Pièce P-1).
- La SAAQ lui reconnaît des séquelles permanentes (SUTT, art. 73 L.a.a.) et des limitations fonctionnelles permanentes interdisant tout soulèvement de charges de plus de 10 kg et tout travail répétitif au-dessus du niveau des épaules (Pièce P-2 : Rapport d'évaluation médicale de la SAAQ), la rendant définitivement incapable de reprendre son emploi de camionneuse lourde (art. 14 L.a.a.).
- Le 15 octobre 2024, à la suite d'un rapport d'évaluation des possibilités professionnelles (Pièce D-1), la SAAQ rend une décision en révision (Pièce D-2) déterminant que Mme Arsenault est capable d'exercer à temps plein l'emploi convenable de « Commis à la répartition et au suivi de flotte » en vertu de l'article 45 L.a.a., mettant ainsi fin à sa pleine IRR au terme du délai d'un an prévu à l'article 49 L.a.a.

2. RÉCLAMATION DE LA REQUÉRANTE (DEMANDE TOTALE : 69 200,00 $) :
- Mme Arsenault dépose un rapport d'ergothérapie et d'orientation professionnelle indépendant (Pièce P-3) concluant qu'elle ne maîtrise pas les logiciels informatiques de logistique exigés par les employeurs modernes et que ses douleurs chroniques cervicales associées limitent sa posture assise prolongée devant un écran.
- Elle réclame l'annulation de la décision D-2 et le rétablissement intégral de son IRR (62 400,00 $ sur 24 mois d'arrérages et maintien futur), ainsi que 6 800,00 $ de frais d'évaluation privée.

3. POSITION DE LA DÉFENSE (SAAQ) :
- La SAAQ fait valoir qu'en vertu de l'article 45 L.a.a., la capacité d'exercer un emploi convenable s'apprécie au regard des limitations fonctionnelles médicalement reconnues (qui ne comportent aucune restriction quant à la posture assise ou au travail à l'ordinateur dans la décision finale P-2, passée en force de chose jugée).
- De plus, Mme Arsenault cumule 22 ans d'expérience dans le secteur du transport routier (connaissance des feuilles de route, des heures de conduite C.s.r. et de la géographie routière), et la SAAQ lui a offert une formation d'appoint en bureautique de 12 semaines qu'elle a refusé de compléter (Pièce D-3).`
  },
  {
    id: 'saaq_3_immunite_civile',
    badge: 'SAAQ / CIVIL #3',
    badgeClass: 'badge-saaq',
    claimAmount: '78 500 $',
    title: 'Benali c. Livraison Boréale & SAAQ — Immunité No-Fault',
    subtitle: 'Art. 1 et 83.57 L.a.a. vs Art. 1457 C.c.Q. | Bris de hayon hydraulique lors du déchargement',
    fileName: 'dossier_saaq_3_benali_immunite_civile_art83_57_laa.txt',
    simulationName: 'SAAQ #3 — Benali c. Livraison Boréale & SAAQ (Immunité art. 83.57 L.a.a.)',
    requirement: 'Simuler l\'audience contradictoire devant la Cour du Québec (Chambre civile) dans l\'action en responsabilité civile de Karim Benali (78 500,00 $ réclamés sous l\'art. 1457 C.c.Q., incluant 15 000 $ sous l\'art. 51 C.p.c.) contre Entreprises de Livraison Boréale inc. et son assureur, avec mise en cause de la SAAQ. Évaluer le moyen d\'irrecevabilité fondé sur l\'immunité civile absolue du régime no-fault de la SAAQ (art. 1 et 83.57 L.a.a., art. 168 C.p.c.).',
    content: `DOSSIER DE LITIGE SAAQ #3 — IMMUNITÉ CIVILE NO-FAULT ET NOTION D'ACCIDENT D'AUTOMOBILE (ART. 1 ET 83.57 L.A.A. / ART. 1457 C.C.Q.)
Juridiction : Cour du Québec (Chambre civile)
Nature du litige : Action en responsabilité civile extracontractuelle (art. 1457 C.c.Q.) et moyen d'irrecevabilité fondé sur l'immunité civile absolue du régime d'assurance automobile (art. 1, 2 et 83.57 L.a.a., art. 168 C.p.c.).

PARTIES :
- Demandeur : Monsieur Karim Benali.
- Défendeurs : Entreprises de Livraison Boréale inc. et son assureur responsabilité civile, Assurances Générales Saint-Laurent inc., avec mise en cause de la Société de l'assurance automobile du Québec (SAAQ).

1. FAITS ET PIÈCES AU DOSSIER :
- Le 22 février 2025, M. Benali aidait le chauffeur d'un camion de livraison appartenant à Entreprises de Livraison Boréale inc. (stationné dans l'entrée glacée de M. Benali, moteur en marche et hayon élévateur hydraulique déployé) à décharger une palette d'électroménagers (Pièce P-1).
- Alors que M. Benali se trouvait sur le hayon élévateur du camion, un bris du câble hydraulique du hayon (dû à un défaut d'entretien documenté dans le carnet mécanique Pièce P-2) a provoqué le basculement brusque de la plateforme, projetant M. Benali au sol et lui causant une fracture du tibia-péroné.
- M. Benali poursuit Entreprises de Livraison Boréale inc. et son assureur devant la Cour du Québec (Chambre civile) en vertu des articles 1457 et 1465 C.c.Q., réclamant un total de 78 500,00 $ :
  a) Perte de revenus nette non compensée : 38 500,00 $ ;
  b) Dommages non pécuniaires (douleurs, souffrances et perte de jouissance de la vie) : 25 000,00 $ ;
  c) Remboursement des honoraires extrajudiciaires d'avocat en vertu de l'article 51 C.p.c. : 15 000,00 $.

2. MOYENS DE LA DÉFENSE ET APPLICATION DE LA LOI SUR L'ASSURANCE AUTOMOBILE (L.A.A.) :
- Les Défendeurs opposent l'irrecevabilité totale du recours civil (art. 168 C.p.c. et art. 83.57 L.a.a.) au motif que le préjudice corporel a été causé par l'usage du camion et de son équipement intégré lors du déchargement (« préjudice causé par une automobile, par son usage ou par son chargement » au sens de l'article 1 L.a.a., tel qu'interprété de façon large et libérale par la Cour suprême du Canada dans Amos c. ICBC et Westmount (Ville) c. Rossy).
- Subsidiairement, même si l'exclusion relative à « l'entretien ou la réparation d'une automobile » de l'article 1 L.a.a. était soulevée par le Demandeur, M. Benali n'effectuait lui-même aucune action d'entretien du camion au moment de la chute, de sorte que son seul recours relève exclusivement de la SAAQ. En tout état de cause, la demande de 15 000 $ sous l'art. 51 C.p.c. est infondée, le débat sur le partage de compétence entre la Cour civile et la SAAQ étant sérieux.`
  },
  {
    id: 'paragon_homes_2022qccq10057',
    badge: 'COUR DU QUÉBEC',
    badgeClass: 'badge-civil',
    claimAmount: '71 928 $',
    title: 'Robertson c. Maisons Paragon Homes (2022 QCCQ 10057)',
    subtitle: 'Dol (art. 1401 C.c.Q.), marge cachée de 15 % sur kit préfabriqué & rejet art. 51 C.p.c.',
    fileName: 'dossier_robertson_c_murray_paragon_homes_2022qccq10057.txt',
    simulationName: 'Robertson c. Maisons Paragon Homes inc. (2022 QCCQ 10057)',
    requirement: 'Simuler l\'audience contradictoire devant la Cour du Québec (Chambre civile) dans le litige opposant Scott Robertson et Josée Charbonneau à Nicole Murray, François Murray et Maisons Paragon Homes inc. Évaluer la demande principale de 71 928,15 $ (restitution de 41 117,15 $, troubles et inconvénients de 5 000 $, honoraires extrajudiciaires de 25 811 $ sous l\'art. 51 C.p.c.), la responsabilité in solidum (art. 1457 et 1526 C.c.Q.) et la demande reconventionnelle de 51 646,53 $.',
    content: `DOSSIER DE LITIGE CIVIL ET COMMERCIAL — COUR DU QUÉBEC (CHAMBRE CIVILE)
Référence de test : Robertson et Charbonneau c. Murray et Maisons Paragon Homes inc.
Nature : Action en réduction d'obligation / restitution pour dol (art. 1399, 1401, 1407 C.c.Q.), responsabilité extracontractuelle in solidum (art. 1457, 1526 C.c.Q.), abus de procédure (art. 51 C.p.c.) et demande reconventionnelle (51 646,53 $).

1. FAITS ET PIÈCES DU DOSSIER :
- Les demandeurs Scott Robertson et Josée Charbonneau concluent un contrat à coût majoré (cost-plus 15 %) avec Nicole Murray pour l'autoconstruction de leur résidence à partir d'un « Kit Paragon » vendu par Maisons Paragon Homes inc. (dirigée par François Murray).
- La brochure promotionnelle remise aux demandeurs (Pièce P-3 : « Comprendre votre Contrat ») affirme expressément qu'aucune marge de profit de 15 % n'est prélevée sur le Kit Paragon lui-même, le profit étant déjà inclus dans le prix du kit (223 223,00 $).
- Or, les demandeurs découvrent en cours de chantier (Pièce P-7 : contrat de design et courriel D-4.2 de François Murray) qu'une commission/marge occulte de 41 117,15 $ a été facturée et partagée entre Maisons Paragon Homes inc. et Nicole Murray sur le Kit Paragon.
- Les demandeurs suspendent le paiement des dernières factures et réclament un total de 71 928,15 $ :
  a) 41 117,15 $ en restitution de la marge occulte (art. 1401 et 1407 C.c.Q.) ;
  b) 5 000,00 $ pour troubles, stress et inconvénients ;
  c) 25 811,00 $ en remboursement d'honoraires extrajudiciaires d'avocats pour abus (art. 51 C.p.c.).
- Les défendeurs déposent une demande reconventionnelle de 51 646,53 $ pour factures impayées et perte de profit sur la fin du chantier.`
  }
]

const activePreviewTitle = computed(() => {
  if (previewPreset.value) return previewPreset.value.fileName
  return t('home.demoFileName')
})

const activePreviewContent = computed(() => {
  if (previewPreset.value) return previewPreset.value.content
  return t('home.demoFileContent')
})

const selectPresetCase = (preset, autoStart = false) => {
  selectedPresetId.value = preset.id
  previewPreset.value = preset
  const blob = new Blob([preset.content], { type: 'text/plain' })
  const presetFile = new File([blob], preset.fileName, { type: 'text/plain' })
  files.value = [presetFile]
  formData.value.simulationName = preset.simulationName
  formData.value.simulationRequirement = preset.requirement
  formData.value.simulationMode = 'legal'

  if (autoStart) {
    startSimulation()
  } else if (dashboardSection.value) {
    dashboardSection.value.scrollIntoView({ behavior: 'smooth' })
  }
}

const previewPresetCase = (preset) => {
  previewPreset.value = preset
  showDemoPreview.value = true
}

const stats = ref({
  totalSimulations: 0,
  totalActors: 0,
  totalRounds: 0
})

const loadRealStats = async () => {
  try {
    const res = await getSimulationHistory(100)
    if (res.success && res.data) {
      stats.value.totalSimulations = res.data.length
      stats.value.totalActors = res.data.reduce((acc, curr) => acc + (curr.entities_count || curr.profiles_count || 5), 0)
      stats.value.totalRounds = res.data.reduce((acc, curr) => acc + (curr.current_round || 0), 0)
    }
  } catch (err) {
    console.error('Failed to load real stats:', err)
  }
}

onMounted(() => {
  loadRealStats()
})

const handleSessionChange = (newSession) => {
  session.value = newSession
}

const dashboardSection = ref(null)

const loadDemoData = () => {
  const demoFileName = t('home.demoFileName')
  const demoFileContent = t('home.demoFileContent')
  const demoRequirement = t('home.demoRequirement')

  const blob = new Blob([demoFileContent], { type: 'text/plain' })
  const demoFile = new File([blob], demoFileName, { type: 'text/plain' })
  
  files.value = [demoFile]
  formData.value.simulationRequirement = demoRequirement
  
  if (dashboardSection.value) {
    dashboardSection.value.scrollIntoView({ behavior: 'smooth' })
  }
}

const showDemoPreview = ref(false)

const loadDemoAndClose = () => {
  showDemoPreview.value = false
  if (previewPreset.value) {
    selectPresetCase(previewPreset.value, false)
  } else {
    loadDemoData()
  }
}

// 表单数据
const formData = ref({
  simulationName: '',
  simulationRequirement: '',
  simulationMode: 'social'
})

// 文件列表
const files = ref([])

// 状态
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)

// 文件输入引用
const fileInput = ref(null)

// 计算属性:是否可以提交
const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

// 触发文件选择
const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

// 处理文件选择
const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

// 处理拖拽相关
const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (e) => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

// 添加文件
const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
}

// 移除文件
const removeFile = (index) => {
  files.value.splice(index, 1)
}

// 滚动到底部
const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

// 开始模拟 - 立即跳转，API调用在Process页面进行
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  
  // 存储待上传的数据
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, formData.value.simulationMode, formData.value.simulationName)
    
    // 立即跳转到Process页面（使用特殊标识表示新建项目）
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
/* 全局变量与重置 */
.home-container {
  --black: #0B1220;
  --white: #FFFFFF;
  --orange: #C5A880;
  --gray-light: #F8FAFC;
  --gray-text: #475569;
  --border: #E2E8F0;
  /* 
    Utilisation de Playfair Display pour les titres (juridique chic) et Inter pour le texte courant.
  */
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  --font-serif: 'Playfair Display', 'Lora', Georgia, serif;
  --font-cn: 'Noto Sans SC', system-ui, sans-serif;

  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-sans);
  color: var(--black);
}

.home-container.auth-bg {
  background: #F8FAFC;
}

.home-container.auth-bg .main-content {
  max-width: 100%;
  padding: 0;
  margin: 0;
  background: #F8FAFC;
}

/* 顶部导航 */
.navbar {
  height: 60px;
  background: #0B1220;
  color: var(--white);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  border-bottom: 1px solid #1A2333;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.brand-logo {
  height: 24px;
  width: auto;
}

.brand-name {
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: 0.5px;
  color: #FFFFFF;
}

.brand-sub {
  color: #C5A880;
  font-weight: 500;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-item-link {
  color: var(--white);
  text-decoration: none;
  font-family: var(--font-sans);
  font-size: 0.9rem;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-item-link:hover {
  color: #C5A880;
  background: rgba(197, 168, 128, 0.08);
}

.github-link {
  color: var(--white);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.2s;
}

.github-link:hover {
  opacity: 0.8;
}

.legal-sandbox-btn {
  background: transparent;
  border: 1px solid #C5A880;
  color: #C5A880;
  padding: 6px 12px;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.legal-sandbox-btn:hover {
  background: var(--orange);
  color: var(--white);
}

.signout-btn {
  background: transparent;
  border: 1px solid #E2E8F0;
  color: #64748B;
  padding: 6px 12px;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.signout-btn:hover {
  background: #FEF2F2;
  color: #EF4444;
  border-color: #FEE2E2;
}

.arrow {
  font-family: sans-serif;
}

/* 主要内容区 */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Hero 区域 */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.75rem;
}

.version-text {
  color: #999;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.main-title {
  font-family: var(--font-serif);
  font-size: 4.2rem;
  line-height: 1.15;
  font-weight: 700;
  margin: 0 0 30px 0;
  letter-spacing: -1.5px;
  color: #0B1220;
}

.gradient-text {
  background: linear-gradient(135deg, #AA7C11 0%, #D4AF37 50%, #8A6D3B 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--gray-text);
  max-width: 640px;
  margin-bottom: 50px;
  font-weight: 400;
  text-align: justify;
}

.hero-desc p {
  margin-bottom: 1.5rem;
}

.highlight-bold {
  color: var(--black);
  font-weight: 700;
}

.highlight-orange {
  color: var(--orange);
  font-weight: 700;
  font-family: var(--font-mono);
}

.highlight-code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--black);
  font-weight: 600;
}

.slogan-text {
  font-size: 1.2rem;
  font-weight: 600;
  color: #0B1220;
  letter-spacing: 0.5px;
  border-left: 4px solid var(--orange);
  padding-left: 15px;
  margin-top: 25px;
}

.blinking-cursor {
  color: var(--orange);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.decoration-square {
  width: 16px;
  height: 16px;
  background: var(--orange);
}

.hero-right {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
}

.logo-container {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  padding-right: 40px;
}

.hero-logo {
  max-width: 500px; /* 调整logo大小 */
  width: 100%;
}

.scroll-down-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--orange);
  font-size: 1.2rem;
  transition: all 0.2s;
}

.scroll-down-btn:hover {
  border-color: var(--orange);
}

/* Dashboard 双栏布局 */
.dashboard-section {
  display: flex;
  gap: 60px;
  border-top: 1px solid var(--border);
  padding-top: 60px;
  align-items: flex-start;
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}

/* 左侧面板 */
.left-panel {
  flex: 0.8;
}

.panel-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  color: var(--orange);
  font-size: 0.8rem;
}

.section-title {
  font-family: var(--font-serif);
  font-size: 2.2rem;
  font-weight: 520;
  margin: 0 0 15px 0;
}

.section-desc {
  color: var(--gray-text);
  margin-bottom: 25px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-card {
  border: 1px solid var(--border);
  padding: 20px 30px;
  min-width: 150px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 520;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 0.85rem;
  color: #999;
}

/* 项目模拟步骤介绍 */
.steps-container {
  border: 1px solid var(--border);
  padding: 30px;
  position: relative;
}

.steps-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon {
  font-size: 1.2rem;
  line-height: 1;
}
.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--black);
  opacity: 0.3;
}

.step-info {
  flex: 1;
}

.step-title {
  font-weight: 520;
  font-size: 1rem;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--gray-text);
}

/* 右侧交互控制台 */
.right-panel {
  flex: 1.2;
}

.console-box {
  background: #0B1220; /* Deep blue background matching navbar & premium dark theme */
  border: 1px solid var(--orange);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(11, 18, 32, 0.3);
}

.console-section {
  padding: 20px;
}

.console-section.btn-section {
  padding-top: 0;
}

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #94A3B8; /* Light gray text for readability */
}

.console-label {
  color: var(--orange);
  font-weight: 600;
}

.console-meta {
  color: #64748B;
}

.upload-zone {
  border: 1.5px dashed rgba(197, 168, 128, 0.4);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 4px;
}

.upload-zone.has-files {
  align-items: flex-start;
}

.upload-zone:hover {
  background: rgba(197, 168, 128, 0.05);
  border-color: var(--orange);
}

.upload-placeholder {
  text-align: center;
}

.upload-icon {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(197, 168, 128, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  color: var(--orange);
  border-radius: 50%;
  font-size: 1.25rem;
  transition: all 0.3s;
}

.upload-zone:hover .upload-icon {
  background: var(--orange);
  color: #0B1220;
}

.upload-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: #FFFFFF;
  margin-bottom: 5px;
}

.upload-hint {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #64748B;
}

.file-list {
  width: 100%;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-item {
  display: flex;
  align-items: center;
  background: rgba(15, 23, 42, 0.8);
  padding: 8px 12px;
  border: 1px solid rgba(197, 168, 128, 0.2);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: #E2E8F0;
  border-radius: 4px;
}

.file-name {
  flex: 1;
  margin: 0 10px;
  color: #E2E8F0;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: #64748B;
  transition: color 0.2s;
}

.remove-btn:hover {
  color: #EF4444;
}

.console-divider {
  display: flex;
  align-items: center;
  margin: 20px 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
}

.console-divider span {
  padding: 0 15px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--orange);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.input-wrapper {
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(15, 23, 42, 0.6);
  border-radius: 4px;
  transition: border-color 0.3s;
}

.input-wrapper:focus-within {
  border-color: var(--orange);
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
  color: #E2E8F0;
}

.code-input-single {
  width: 100%;
  border: none;
  background: transparent;
  padding: 12px 20px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.6;
  outline: none;
  color: #E2E8F0;
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #64748B;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 2px;
}

.start-engine-btn {
  width: 100%;
  background: var(--orange);
  color: #0B1220;
  border: 1px solid var(--orange);
  padding: 16px 20px;
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
  border-radius: 4px;
  text-transform: uppercase;
}

.start-engine-btn:not(:disabled) {
  background: var(--orange);
  border: 1px solid var(--orange);
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: #D4AF37;
  border-color: #D4AF37;
  box-shadow: 0 6px 20px rgba(197, 168, 128, 0.35);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: #1E293B;
  color: #64748B;
  cursor: not-allowed;
  transform: none;
  border: 1px solid #334155;
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(197, 168, 128, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(197, 168, 128, 0); }
  100% { box-shadow: 0 0 0 0 rgba(197, 168, 128, 0); }
}

@media (max-width: 1024px) {
  .dashboard-section {
    flex-direction: column;
  }
  
  .hero-section {
    flex-direction: column;
  }
  
  .hero-left {
    padding-right: 0;
    margin-bottom: 40px;
  }
  
  .hero-logo {
    max-width: 200px;
    margin-bottom: 20px;
  }
}

.mode-selector-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-top: 8px;
}

.mode-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  user-select: none;
}

.mode-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(197, 168, 128, 0.3);
}

.mode-card.active {
  background: rgba(197, 168, 128, 0.08);
  border-color: var(--orange);
  box-shadow: 0 0 15px rgba(197, 168, 128, 0.1);
}

.mode-card.active.legal-card-active {
  background: linear-gradient(135deg, #B58A3D 0%, #D4AF37 50%, #B58A3D 100%) !important;
  border-color: #D4AF37 !important;
  box-shadow: 0 4px 20px rgba(212, 175, 55, 0.4);
}

.mode-card.active.legal-card-active .mode-title {
  color: #0B1220 !important;
  font-weight: 700;
}

.mode-card.active.legal-card-active .mode-desc {
  color: #0B1220 !important;
  font-weight: 600;
}

.mode-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mode-icon {
  font-size: 1.1rem;
}

.mode-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-weight: 600;
  font-size: 0.85rem;
  color: #E2E8F0;
  letter-spacing: 0.3px;
  transition: color 0.2s;
}

.mode-card.active .mode-title {
  color: var(--orange);
}

.mode-desc {
  font-size: 0.68rem;
  line-height: 1.4;
  color: #94A3B8;
  margin: 0;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

<style>
/* English locale adjustments (unscoped to target html[lang]) */
html[lang="en"] .main-title {
  font-size: 3.5rem;
  font-family: 'Playfair Display', Georgia, serif;
  letter-spacing: -1px;
}

html[lang="en"] .hero-desc {
  text-align: left;
  font-family: 'Inter', -apple-system, sans-serif;
  letter-spacing: 0;
}

html[lang="en"] .slogan-text {
  font-family: 'Inter', -apple-system, sans-serif;
  letter-spacing: 0;
}

html[lang="en"] .tag-row {
  font-family: 'Inter', -apple-system, sans-serif;
}

html[lang="en"] .navbar .nav-links {
  font-family: 'Inter', -apple-system, sans-serif;
}

/* Left pane: system status + workflow */
html[lang="en"] .status-section {
  font-family: 'Inter', -apple-system, sans-serif;
}

html[lang="en"] .status-section .status-ready {
  font-size: 1.6rem;
}

html[lang="en"] .status-section .metric-value {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 1.4rem;
}

html[lang="en"] .workflow-list .step-title {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

html[lang="en"] .workflow-list .step-desc {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  font-size: 0.72rem !important;
  line-height: 1.4 !important;
}

html[lang="en"] .workflow-list {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.demo-hero-container {
  display: flex;
  gap: 12px;
  justify-content: flex-start;
  margin-top: 25px;
  max-width: 500px;
}

.demo-trigger-container {
  display: flex;
  justify-content: center;
  margin-top: 15px;
}

.demo-load-btn {
  background: var(--orange);
  border: 1px solid var(--orange);
  color: #0B1220;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  padding: 12px 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  text-align: center;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(197, 168, 128, 0.15);
}

.demo-load-btn:hover {
  background: rgba(197, 168, 128, 0.05);
  color: var(--orange);
  box-shadow: 0 6px 20px rgba(197, 168, 128, 0.1);
  transform: translateY(-2px);
}

.demo-preview-btn {
  background: transparent;
  border: 1px solid var(--orange);
  color: var(--orange);
  font-family: var(--font-sans);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  padding: 12px 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  text-align: center;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(197, 168, 128, 0.05);
}

.demo-preview-btn:hover {
  background: rgba(197, 168, 128, 0.1);
  box-shadow: 0 6px 20px rgba(197, 168, 128, 0.15);
  transform: translateY(-2px);
}

/* Modal de prévisualisation */
.preview-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(11, 18, 32, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.preview-modal-box {
  background: #0B1220;
  border: 1px solid #1A2333;
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  border-radius: 8px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: fadeInModal 0.3s ease;
}

@keyframes fadeInModal {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.preview-modal-header {
  padding: 20px;
  border-bottom: 1px solid #1A2333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-modal-title {
  font-family: var(--font-serif);
  color: var(--white);
  font-size: 1.25rem;
  margin: 0;
}

.preview-modal-close-btn {
  background: transparent;
  border: none;
  color: #94A3B8;
  font-size: 1.75rem;
  cursor: pointer;
  line-height: 1;
  transition: color 0.2s;
}

.preview-modal-close-btn:hover {
  color: var(--white);
}

.preview-modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
  background: #0D1627;
}

.preview-modal-text {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  line-height: 1.6;
  color: #E2E8F0;
  white-space: pre-wrap;
  margin: 0;
}

.preview-modal-footer {
  padding: 20px;
  border-top: 1px solid #1A2333;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.preview-modal-cancel-btn {
  background: transparent;
  border: 1px solid #334155;
  color: #94A3B8;
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.preview-modal-cancel-btn:hover {
  background: #1E293B;
  color: var(--white);
}

.preview-modal-confirm-btn {
  background: var(--orange);
  border: 1px solid var(--orange);
  color: #0B1220;
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.preview-modal-confirm-btn:hover {
  background: transparent;
  color: var(--orange);
}

/* Exemples Prêts à Simuler en 1 Clic (SAAQ & Cour du Québec) */
.preset-cases-section {
  margin-bottom: 18px;
}

.preset-cases-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

@media (max-width: 900px) {
  .preset-cases-grid {
    grid-template-columns: 1fr;
  }
}

.preset-case-card {
  background: #F8FAFC;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preset-case-card:hover {
  border-color: #0B1220;
  background: #F1F5F9;
  transform: translateY(-1px);
}

.preset-case-card.active {
  border: 2px solid var(--orange);
  background: #FFFBEB;
}

.preset-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preset-badge {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.badge-saaq {
  background: #0B1220;
  color: #38BDF8;
}

.badge-civil {
  background: #065F46;
  color: #ECFDF5;
}

.preset-quantum {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 700;
  color: #0F172A;
}

.preset-title {
  font-size: 0.84rem;
  font-weight: 700;
  color: #0B1220;
  line-height: 1.25;
}

.preset-subtitle {
  font-size: 0.73rem;
  color: #475569;
  line-height: 1.35;
}

.preset-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.preset-btn-load,
.preset-btn-preview,
.preset-btn-run {
  font-size: 0.71rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-btn-load {
  background: #FFFFFF;
  border: 1px solid #94A3B8;
  color: #0F172A;
}

.preset-btn-load:hover {
  background: #E2E8F0;
}

.preset-btn-preview {
  background: #FFFFFF;
  border: 1px solid #CBD5E1;
  color: #334155;
}

.preset-btn-preview:hover {
  background: #F1F5F9;
}

.preset-btn-run {
  background: #0B1220;
  border: 1px solid #0B1220;
  color: var(--orange);
  margin-left: auto;
}

.preset-btn-run:hover {
  background: var(--orange);
  color: #0B1220;
}
</style>
