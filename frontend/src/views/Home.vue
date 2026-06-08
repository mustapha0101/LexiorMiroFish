<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand" @click="router.push('/')">
        <img src="/logo.png" class="brand-logo" alt="Lexior" />
        <span class="brand-name">LEXIOR <span class="brand-sub">SIMULATOR</span></span>
      </div>
      <div class="nav-links">
        <button class="legal-sandbox-btn" @click="$router.push('/legal-simulator')">
          ⚖️ Laboratoire Juridique
        </button>
        <LanguageSwitcher />
        <a href="https://github.com/666ghj/MiroFish" target="_blank" class="github-link">
          {{ $t('nav.visitGithub') }} <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
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
      <section class="dashboard-section">
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
              <div class="metric-value">{{ $t('home.metricLowCost') }}</div>
              <div class="metric-label">{{ $t('home.metricLowCostDesc') }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ $t('home.metricHighAvail') }}</div>
              <div class="metric-label">{{ $t('home.metricHighAvailDesc') }}</div>
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
                  <p class="mode-desc">Simulation d'opinion publique et propagation d'impact sur les réseaux sociaux (Twitter / Reddit) avec l'intégration du moteur d'intégrité cognitive PIE.</p>
                </div>

                <div 
                  class="mode-card" 
                  :class="{ active: formData.simulationMode === 'legal' }"
                  @click="formData.simulationMode = 'legal'"
                >
                  <div class="mode-card-header">
                    <span class="mode-icon">⚖️</span>
                    <span class="mode-title">{{ $t('home.modeLegal') }}</span>
                  </div>
                  <p class="mode-desc">Simulation de procès contradictoire devant le Juge sur les faits du document.</p>
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

      <!-- Section Preuves en Direct -->
      <section class="live-proofs-section">
        <div class="section-header-centered">
          <span class="header-icon-gold">⚖️</span>
          <h2 class="section-title-large">Banc d'Essai Scientifique (PIE Engine)</h2>
          <p class="section-subtitle">Démonstration quantitative en temps réel des innovations théoriques de l'architecture cognitive Lexior.</p>
        </div>

        <div class="proofs-grid">
          <!-- Preuve 1 : Hystérésis & Négociation Contractuelle -->
          <div class="proof-card">
            <div class="proof-card-header">
              <span class="proof-num">PREUVE 1</span>
              <h3 class="proof-title">Asymétrie Émotionnelle & Hystérésis de Négociation</h3>
            </div>
            <p class="proof-desc">
              Démontre l'asymétrie de la confiance lors d'une négociation contractuelle. Une seule clause abusive suffit à rendre l'avocat méfiant, tandis qu'il faut 5 concessions consécutives pour restaurer la coopération.
            </p>
            <div class="proof-body">
              <button 
                class="proof-btn" 
                @click="startHysteresisProof" 
                :disabled="runningHysteresis"
              >
                <span v-if="runningHysteresis" class="loading-spinner-small"></span>
                {{ runningHysteresis ? 'Simulation en cours...' : 'Exécuter en direct' }}
              </button>

              <div v-if="hysteresisSteps.length > 0" class="live-timeline">
                <div 
                  v-for="(step, idx) in hysteresisSteps" 
                  :key="idx" 
                  class="timeline-step-item"
                  :class="{ active: currentHysteresisStepIndex === idx }"
                >
                  <span class="step-round-badge">R{{ step.round }}</span>
                  <div class="step-details">
                    <div class="step-action-received">
                      Action : <span class="mono">{{ step.action }}</span>
                    </div>
                    <div class="step-desc-text">{{ step.description }}</div>
                    <div class="step-mood-status">
                      Humeur : 
                      <span class="mood-pill" :class="step.mood.toLowerCase()">
                        {{ step.mood }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div v-if="hysteresisConclusion" class="proof-conclusion">
                <strong>Conclusion :</strong> {{ hysteresisConclusion }}
              </div>
            </div>
          </div>

          <!-- Preuve 2 : Inertie Identitaire & Décision Judiciaire -->
          <div class="proof-card">
            <div class="proof-card-header">
              <span class="proof-num">PREUVE 2</span>
              <h3 class="proof-title">Stabilité Décisionnelle Judiciaire sous Bruit (Inertie PIE)</h3>
            </div>
            <p class="proof-desc">
              Compare la stabilité de conviction d'un juge (Acquittement vs Condamnation) face aux témoignages contradictoires. L'inertie jurisprudentielle PIE stabilise sa décision, tandis qu'un juge sans régulation dévie de façon instable.
            </p>
            <div class="proof-body">
              <button 
                class="proof-btn" 
                @click="startInertiaProof" 
                :disabled="runningInertia"
              >
                <span v-if="runningInertia" class="loading-spinner-small"></span>
                {{ runningInertia ? 'Simulation en cours...' : 'Exécuter en direct' }}
              </button>

              <div v-if="inertiaHistory.length > 0" class="live-chart-container">
                <table class="inertia-table">
                  <thead>
                    <tr>
                      <th>Étape</th>
                      <th>Stimulus</th>
                      <th>Contrôle</th>
                      <th>PIE (Inertie)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="(h, idx) in inertiaHistory" 
                      :key="idx"
                      :class="{ active: currentInertiaStepIndex === idx }"
                    >
                      <td class="mono">S{{ h.step }}</td>
                      <td class="mono" :class="h.stimulus > 0 ? 'text-pos' : 'text-neg'">
                        {{ h.stimulus > 0 ? '+' : '' }}{{ h.stimulus }}
                      </td>
                      <td>
                        <div class="bar-wrapper">
                          <span class="mono val">{{ h.tension_control.toFixed(3) }}</span>
                          <div class="bar-bg">
                            <div class="bar-fill control" :style="{ width: (h.tension_control * 100) + '%' }"></div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div class="bar-wrapper">
                          <span class="mono val">{{ h.tension_pie.toFixed(3) }}</span>
                          <div class="bar-bg">
                            <div class="bar-fill pie" :style="{ width: (h.tension_pie * 100) + '%' }"></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="inertiaConclusion" class="variance-comparison">
                <div class="variance-item">
                  <span class="label">Variance Contrôle (Bruit) :</span>
                  <span class="value mono text-neg">{{ inertiaVarianceControl.toFixed(6) }}</span>
                </div>
                <div class="variance-item">
                  <span class="label">Variance PIE (Stabilité) :</span>
                  <span class="value mono text-pos">{{ inertiaVariancePie.toFixed(6) }}</span>
                </div>
              </div>
              
              <div v-if="inertiaConclusion" class="proof-conclusion">
                <strong>Conclusion :</strong> {{ inertiaConclusion }}
              </div>
            </div>
          </div>

          <!-- Preuve 3 : Budget Attentionnel -->
          <div class="proof-card">
            <div class="proof-card-header">
              <span class="proof-num">PREUVE 3</span>
              <h3 class="proof-title">Filtre Attentionnel de Dossier sous Contrainte</h3>
            </div>
            <p class="proof-desc">
              Démontre comment un budget d'attention restreint (10%) force l'avocate à élaguer les détails procéduraux secondaires pour focaliser ses ressources sur les précédents fondamentaux de la Cour Suprême.
            </p>
            <div class="proof-body">
              <button 
                class="proof-btn" 
                @click="startAttentionProof" 
                :disabled="runningAttention"
              >
                <span v-if="runningAttention" class="loading-spinner-small"></span>
                {{ runningAttention ? 'Analyse du contexte...' : 'Exécuter en direct' }}
              </button>

              <div v-if="attentionResult" class="attention-results">
                <div class="memories-pool">
                  <h4>Éléments dans le dossier :</h4>
                  <ul>
                    <li v-for="(m, idx) in attentionResult.memories" :key="idx" class="memory-pool-item">
                      <span class="bullet">▪</span>
                      <span class="desc">{{ m.desc }}</span>
                      <span class="importance-badge" :class="m.importance">
                        {{ m.importance }}
                      </span>
                    </li>
                  </ul>
                </div>

                <div class="prompt-comparison">
                  <div class="prompt-box high">
                    <h5>Budget Élevé (50% d'attention)</h5>
                    <div class="prompt-content-view">
                      <div class="prompt-section-header">Éléments Transmis au LLM :</div>
                      <div class="prompt-text">
                        - Erreur de frappe mineure du greffe lors du dépôt...<br>
                        - Arrêt de principe de la Cour Suprême sur la responsabilité...
                      </div>
                      <div class="prompt-section-header">Introspection :</div>
                      <div class="prompt-text-highlight">
                        "J'examine chaque pièce du dossier avec rigueur. Chaque erreur matérielle est notée."
                      </div>
                    </div>
                  </div>

                  <div class="prompt-box low">
                    <h5>Budget Faible (10% d'attention)</h5>
                    <div class="prompt-content-view">
                      <div class="prompt-section-header">Éléments Transmis au LLM :</div>
                      <div class="prompt-text">
                        <span class="text-filtered">[FILTRÉ - Élagage d'attention]</span><br>
                        - Arrêt de principe de la Cour Suprême sur la responsabilité...
                      </div>
                      <div class="prompt-section-header">Introspection :</div>
                      <div class="prompt-text-highlight text-neg">
                        "L'introspection et l'analyse des erreurs de forme sont désactivées pour préserver l'attention sur les précédents."
                      </div>
                    </div>
                  </div>
                </div>

                <div class="proof-conclusion">
                  <strong>Conclusion :</strong> {{ attentionResult.conclusion }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 历史项目数据库 -->
      <HistoryDatabase />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const router = useRouter()

const triggerVirtualUpload = (type, requirement) => {
  const fileContent = `Benchmark case for ${type}. Context and details about the legal case.`
  const file = new File([fileContent], `proof_${type}.txt`, { type: 'text/plain' })
  
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload([file], requirement)
    
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}

const runningHysteresis = ref(false)
const hysteresisSteps = ref([])
const currentHysteresisStepIndex = ref(-1)
const hysteresisConclusion = ref('')

const startHysteresisProof = () => {
  triggerVirtualUpload('hysteresis', "Démonstration quantitative de l'hystérésis d'humeur lors de négociations contractuelles tendues face à des clauses abusives répétées.")
}

// Inertia proof state
const runningInertia = ref(false)
const inertiaHistory = ref([])
const currentInertiaStepIndex = ref(-1)
const inertiaVarianceControl = ref(0)
const inertiaVariancePie = ref(0)
const inertiaConclusion = ref('')

const startInertiaProof = () => {
  triggerVirtualUpload('inertia', "Comparaison de la stabilité décisionnelle d'un magistrat face aux contradictions des témoignages : Juge standard vs Juge régulé par les précédents judiciaires (PIE).")
}

// Attention proof state
const runningAttention = ref(false)
const attentionResult = ref(null)

const startAttentionProof = () => {
  triggerVirtualUpload('attention', "Modélisation de la focalisation de l'attention de l'avocat et de l'élagage des détails procéduraux mineurs sous contrainte de temps strict (10% de budget attentionnel).")
}

// 表单数据
const formData = ref({
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
    setPendingUpload(files.value, formData.value.simulationRequirement, formData.value.simulationMode)
    
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
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --gray-light: #F5F5F5;
  --gray-text: #666666;
  --border: #E5E5E5;
  /* 
    Utilisation de Playfair Display pour les titres (juridique chic) et Inter pour le texte courant.
  */
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  --font-serif: 'Playfair Display', 'Lora', Georgia, serif;
  --font-cn: 'Noto Sans SC', system-ui, sans-serif;
}

.home-container {
  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-sans);
  color: var(--black);
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
  font-size: 4.5rem;
  line-height: 1.2;
  font-weight: 500;
  margin: 0 0 40px 0;
  letter-spacing: -1px;
  color: var(--black);
}

.gradient-text {
  background: linear-gradient(90deg, #000000 0%, #444444 100%);
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
  font-weight: 520;
  color: var(--black);
  letter-spacing: 1px;
  border-left: 3px solid var(--orange);
  padding-left: 15px;
  margin-top: 20px;
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
  border: 1px solid #CCC; /* 外部实线 */
  padding: 8px; /* 内边距形成双重边框感 */
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
  color: #666;
}

.upload-zone {
  border: 1px dashed #CCC;
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #FAFAFA;
}

.upload-zone.has-files {
  align-items: flex-start;
}

.upload-zone:hover {
  background: #F0F0F0;
  border-color: #999;
}

.upload-placeholder {
  text-align: center;
}

.upload-icon {
  width: 40px;
  height: 40px;
  border: 1px solid #DDD;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  color: #999;
}

.upload-title {
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.upload-hint {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #999;
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
  background: var(--white);
  padding: 8px 12px;
  border: 1px solid #EEE;
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.file-name {
  flex: 1;
  margin: 0 10px;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: #999;
}

.console-divider {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #EEE;
}

.console-divider span {
  padding: 0 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #BBB;
  letter-spacing: 1px;
}

.input-wrapper {
  position: relative;
  border: 1px solid #DDD;
  background: #FAFAFA;
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
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #AAA;
}

.start-engine-btn {
  width: 100%;
  background: var(--black);
  color: var(--white);
  border: none;
  padding: 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
}

/* 可点击状态（非禁用） */
.start-engine-btn:not(:disabled) {
  background: var(--black);
  border: 1px solid var(--black);
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: var(--orange);
  border-color: var(--orange);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: #E5E5E5;
  color: #999;
  cursor: not-allowed;
  transform: none;
  border: 1px solid #E5E5E5;
}

/* 引导动画：微妙的边框脉冲 */
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.2); }
  70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

/* 响应式适配 */
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

/* Preuves en Direct Styles */
.live-proofs-section {
  padding: 80px 40px;
  background: #F8FAFC;
  border-top: 1px solid #E2E8F0;
  border-bottom: 1px solid #E2E8F0;
}

.section-header-centered {
  text-align: center;
  margin-bottom: 50px;
}

.header-icon-gold {
  font-size: 2.5rem;
  margin-bottom: 16px;
  display: block;
}

.section-title-large {
  font-family: var(--font-serif);
  font-size: 2.2rem;
  font-weight: 700;
  color: #0B1220;
  margin-bottom: 12px;
}

.section-subtitle {
  font-size: 1.1rem;
  color: #64748B;
  max-width: 700px;
  margin: 0 auto;
}

.proofs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 30px;
  max-width: 1300px;
  margin: 0 auto;
}

.proof-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.025);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.proof-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 20px -3px rgba(11,18,32,0.08);
  border-color: #C5A880;
}

.proof-card-header {
  margin-bottom: 16px;
}

.proof-num {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: #C5A880;
  letter-spacing: 1px;
}

.proof-title {
  font-family: var(--font-serif);
  font-size: 1.35rem;
  font-weight: 700;
  color: #0B1220;
  margin-top: 4px;
}

.proof-desc {
  font-size: 0.9rem;
  color: #64748B;
  line-height: 1.5;
  margin-bottom: 24px;
  flex-grow: 1;
}

.proof-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.proof-btn {
  background: #0B1220;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  padding: 12px 20px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.proof-btn:hover {
  background: #0F1E36;
  box-shadow: 0 4px 12px rgba(11,18,32,0.15);
}

.proof-btn:disabled {
  background: #94A3B8;
  cursor: not-allowed;
}

/* Timeline live style */
.live-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #0B1220;
  border-radius: 8px;
  padding: 16px;
  max-height: 300px;
  overflow-y: auto;
  animation: fadeIn 0.4s ease-out;
}

.timeline-step-item {
  display: flex;
  gap: 12px;
  padding: 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  border-left: 3px solid transparent;
  transition: all 0.3s;
}

.timeline-step-item.active {
  background: rgba(255, 255, 255, 0.08);
  border-left-color: #C5A880;
}

.step-round-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  background: #1E293B;
  color: #C5A880;
  height: 24px;
  padding: 0 6px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-grow: 1;
}

.step-action-received {
  font-size: 0.75rem;
  color: #94A3B8;
}

.step-desc-text {
  font-size: 0.85rem;
  color: #E2E8F0;
}

.step-mood-status {
  font-size: 0.75rem;
  color: #94A3B8;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mood-pill {
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.mood-pill.neutre {
  background: #475569;
  color: #E2E8F0;
}

.mood-pill.méfiance {
  background: #B45309;
  color: #FEF3C7;
}

.mood-pill.isolé {
  background: #B91C1C;
  color: #FEE2E2;
}

.mood-pill.coopératif {
  background: #15803D;
  color: #DCFCE7;
}

.proof-conclusion {
  background: #FFFBEB;
  border-left: 3px solid #F59E0B;
  padding: 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #B45309;
  line-height: 1.4;
  margin-top: 10px;
}

/* Inertia table styling */
.live-chart-container {
  background: #0B1220;
  border-radius: 8px;
  padding: 12px;
  max-height: 320px;
  overflow-y: auto;
  animation: fadeIn 0.4s ease-out;
}

.inertia-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  color: #E2E8F0;
}

.inertia-table th {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid #1E293B;
  color: #94A3B8;
}

.inertia-table td {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.inertia-table tr.active {
  background: rgba(255, 255, 255, 0.05);
}

.text-pos {
  color: #10B981;
}

.text-neg {
  color: #EF4444;
}

.bar-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bar-wrapper .val {
  min-width: 32px;
}

.bar-bg {
  flex-grow: 1;
  height: 6px;
  background: #1E293B;
  border-radius: 3px;
  position: relative;
  overflow: hidden;
  width: 60px;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.bar-fill.control {
  background: #EF4444;
}

.bar-fill.pie {
  background: #10B981;
}

.variance-comparison {
  display: flex;
  justify-content: space-between;
  background: #0F1E36;
  padding: 12px;
  border-radius: 6px;
}

.variance-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.variance-item .label {
  font-size: 0.75rem;
  color: #94A3B8;
}

.variance-item .value {
  font-size: 0.95rem;
  font-weight: 700;
}

/* Attention results styling */
.attention-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: fadeIn 0.5s ease-out;
}

.memories-pool {
  background: #F1F5F9;
  border-radius: 8px;
  padding: 16px;
}

.memories-pool h4 {
  font-size: 0.85rem;
  font-weight: 700;
  color: #1E293B;
  margin-top: 0;
  margin-bottom: 8px;
}

.memories-pool ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.memory-pool-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #334155;
}

.memory-pool-item .bullet {
  color: #64748B;
}

.importance-badge {
  font-size: 0.65rem;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  text-transform: uppercase;
}

.importance-badge.faible {
  background: #E2E8F0;
  color: #475569;
}

.importance-badge.très\ forte {
  background: #FEE2E2;
  color: #991B1B;
}

.prompt-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.prompt-box {
  background: #0B1220;
  border-radius: 8px;
  padding: 16px;
  color: #E2E8F0;
  border-top: 3px solid;
}

.prompt-box.high {
  border-top-color: #10B981;
}

.prompt-box.low {
  border-top-color: #EF4444;
}

.prompt-box h5 {
  font-size: 0.8rem;
  font-weight: 700;
  margin-top: 0;
  margin-bottom: 12px;
  color: #FFFFFF;
}

.prompt-content-view {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.prompt-section-header {
  font-size: 0.7rem;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.prompt-text {
  font-size: 0.75rem;
  color: #CBD5E1;
  line-height: 1.4;
  background: rgba(255,255,255,0.03);
  padding: 6px;
  border-radius: 4px;
}

.text-filtered {
  color: #64748B;
  font-style: italic;
}

.prompt-text-highlight {
  font-size: 0.75rem;
  color: #10B981;
  font-style: italic;
  line-height: 1.4;
  background: rgba(16, 185, 129, 0.05);
  padding: 6px;
  border-radius: 4px;
}

.prompt-text-highlight.text-neg {
  color: #EF4444;
  background: rgba(239, 68, 68, 0.05);
}

/* Mode Selector Grid & Card Styles */
.mode-selector-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-top: 8px;
}

.mode-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  user-select: none;
}

.mode-card:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.15);
}

.mode-card.active {
  background: rgba(212, 175, 55, 0.06);
  border-color: #D4AF37;
  box-shadow: 0 0 15px rgba(212, 175, 55, 0.08);
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
  color: #FFFFFF;
  letter-spacing: 0.3px;
  transition: color 0.2s;
}

.mode-card.active .mode-title {
  color: #D4AF37;
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
</style>
