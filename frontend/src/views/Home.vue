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
  justify-content: flex-start;
  margin-top: 25px;
  max-width: 320px;
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
  width: 100%;
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
</style>
