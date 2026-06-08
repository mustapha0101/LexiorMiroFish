<template>
  <div class="main-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <button class="back-history-btn" @click="router.push('/')" title="Retour à l'historique">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <div class="brand" @click="router.push('/')">
          <img src="/logo.png" class="brand-logo" alt="Lexior" />
          <span class="brand-name">{{ $t('common.brandFirst') }} <span class="brand-sub">{{ $t('common.brandSecond') }}</span></span>
        </div>
      </div>
      
      <div class="header-center">
        <div class="view-switcher">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: $t('main.layoutGraph'), split: $t('main.layoutSplit'), workbench: $t('main.layoutWorkbench') }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <LanguageSwitcher />
        <div class="step-divider"></div>
        <div class="workflow-step">
          <span class="step-num">Step 5/5</span>
          <span class="step-name">{{ $tm('main.stepNames')[4] }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel 
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="5"
          :isSimulating="false"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step5 深度互动 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step5Interaction
          :reportId="currentReportId"
          :simulationId="simulationId"
          :systemLogs="systemLogs"
          :projectData="projectData"
          @add-log="addLog"
          @update-status="updateStatus"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GraphPanel from '../components/GraphPanel.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

// Props
const props = defineProps({
  reportId: String
})

// Layout State - 默认切换到工作台视角
const viewMode = ref('workbench')

// Data State
const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const projectData = ref(null)
const simGraphId = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('ready') // ready | processing | completed | error

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  return currentStatus.value
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Completed'
  if (currentStatus.value === 'processing') return 'Processing'
  return 'Ready'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

// --- Data Logic ---
const loadReportData = async () => {
  try {
    addLog(t('log.loadReportData', { id: currentReportId.value }))

    // 获取 report 信息以获取 simulation_id
    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      const reportData = reportRes.data
      simulationId.value = reportData.simulation_id

      if (simulationId.value) {
        // 获取 simulation 信息
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data) {
          const simData = simRes.data

          // 保存 simulation graph_id
          if (simData.graph_id) {
            simGraphId.value = simData.graph_id
          }

          // 获取 project 信息
          if (simData.project_id) {
            const projRes = await getProject(simData.project_id)
            if (projRes.success && projRes.data) {
              projectData.value = projRes.data
              addLog(t('log.projectLoadSuccess', { id: projRes.data.project_id }))
            }
          }

          // 获取 graph 数据 (优先使用 simulation graph_id, 备用 project graph_id)
          const targetGraphId = simGraphId.value || projectData.value?.graph_id
          if (targetGraphId) {
            await loadGraph(targetGraphId)
          } else {
            addLog(t('log.noGraphIdFound') || 'Aucun identifiant de graphe trouvé.')
          }
        }
      }
    } else {
      addLog(t('log.getReportInfoFailed', { error: reportRes.error || t('common.unknownError') }))
    }
  } catch (err) {
    addLog(t('log.loadException', { error: err.message }))
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog(t('log.graphDataLoadSuccess'))
    }
  } catch (err) {
    addLog(t('log.graphLoadFailed', { error: err.message }))
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  const targetGraphId = simGraphId.value || projectData.value?.graph_id
  if (targetGraphId) {
    loadGraph(targetGraphId)
  }
}

// Watch route params
watch(() => route.params.reportId, (newId) => {
  if (newId && newId !== currentReportId.value) {
    currentReportId.value = newId
    loadReportData()
  }
}, { immediate: true })

onMounted(() => {
  addLog(t('log.interactionViewInit'))
  loadReportData()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 1px solid #1A2333;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #0B1220;
  z-index: 100;
  position: relative;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.header-left {
  display: flex;
  align-items: center;
}

.back-history-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: #0F1E36;
  border: 1px solid #1E293B;
  border-radius: 6px;
  color: #94A3B8;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-right: 12px;
}

.back-history-btn:hover {
  background: #C5A880;
  color: #0B1220;
  border-color: #C5A880;
}

.brand {
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
  font-family: 'Playfair Display', Georgia, serif;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.5px;
  color: #FFFFFF;
}

.brand-sub {
  color: #C5A880;
  font-weight: 500;
}

.view-switcher {
  display: flex;
  background: #0F1E36;
  padding: 4px;
  border-radius: 6px;
  gap: 4px;
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #94A3B8;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn.active {
  background: #C5A880;
  color: #0B1220;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: #94A3B8;
}

.step-name {
  font-weight: 700;
  color: #FFFFFF;
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: #1E293B;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94A3B8;
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #CCC;
}

.status-indicator.ready .dot { background: #4CAF50; }
.status-indicator.processing .dot { background: #FF9800; animation: pulse 1s infinite; }
.status-indicator.completed .dot { background: #4CAF50; }
.status-indicator.error .dot { background: #F44336; }

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.3s ease, transform 0.3s ease;
  will-change: width, opacity, transform;
}

.panel-wrapper.left {
  border-right: 1px solid #EAEAEA;
}
</style>

<style>
@media print {
  /* Print overrides when printing-chat class is active on body */
  body.printing-chat {
    background: #FFFFFF !important;
    color: #000000 !important;
  }

  body.printing-chat .app-header,
  body.printing-chat .panel-wrapper.left,
  body.printing-chat .left-panel,
  body.printing-chat .action-bar,
  body.printing-chat .report-agent-tools-card,
  body.printing-chat .agent-profile-card,
  body.printing-chat .chat-input-area,
  body.printing-chat .chat-export-bar {
    display: none !important;
  }

  body.printing-chat,
  body.printing-chat .main-view,
  body.printing-chat .content-area,
  body.printing-chat .panel-wrapper.right,
  body.printing-chat .interaction-panel,
  body.printing-chat .main-split-layout,
  body.printing-chat .right-panel,
  body.printing-chat .chat-container,
  body.printing-chat .chat-messages {
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow: visible !important;
    position: static !important;
    display: block !important;
    width: 100% !important;
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
  }

  /* Make printed chat layout look gorgeous */
  body.printing-chat .chat-messages {
    display: flex !important;
    flex-direction: column !important;
    gap: 16px !important;
    padding: 20px !important;
  }

  body.printing-chat .chat-message {
    display: flex !important;
    flex-direction: row !important; /* Force standard left-to-right flow for readability */
    align-items: flex-start !important;
    gap: 16px !important;
    page-break-inside: avoid;
    break-inside: avoid;
    background: #F9FAFB !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 8px !important;
    padding: 16px !important;
  }

  body.printing-chat .chat-message.user {
    background: #F0FDF4 !important; /* Light green tint for user messages to look distinct and stylish */
    border-color: #DCFCE7 !important;
  }

  body.printing-chat .message-avatar {
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    background: #E5E7EB !important;
    color: #374151 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: bold !important;
  }

  body.printing-chat .chat-message.user .message-avatar {
    background: #10B981 !important;
    color: #FFFFFF !important;
  }

  body.printing-chat .message-content {
    max-width: 100% !important;
    width: calc(100% - 52px) !important;
    align-items: flex-start !important; /* Standard align start for readable printing */
  }

  body.printing-chat .message-header {
    display: flex !important;
    justify-content: space-between !important;
    width: 100% !important;
    border-bottom: 1px solid #E5E7EB !important;
    padding-bottom: 4px !important;
    margin-bottom: 6px !important;
  }

  body.printing-chat .sender-name {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: #1F2937 !important;
  }

  body.printing-chat .message-time {
    font-size: 11px !important;
    color: #6B7280 !important;
  }

  body.printing-chat .message-text {
    padding: 0 !important;
    background: transparent !important;
    color: #374151 !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
  }
}
</style>
