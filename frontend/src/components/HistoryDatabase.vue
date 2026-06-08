<template>
  <div 
    class="history-database-premium"
    :class="{ 'no-projects': filteredProjects.length === 0 && !loading }"
    ref="historyContainer"
  >
    <!-- Background grid decoration -->
    <div class="tech-grid-bg">
      <div class="grid-pattern"></div>
      <div class="gradient-overlay"></div>
    </div>

    <!-- Title Header -->
    <div class="section-header">
      <div class="section-line"></div>
      <span class="section-title">{{ $t('history.title') }}</span>
      <div class="section-line"></div>
    </div>

    <!-- Search & Filter Controls Panel -->
    <div class="search-filter-panel">
      <!-- Search Input -->
      <div class="search-wrapper">
        <span class="search-icon">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </span>
        <input 
          type="text" 
          v-model="searchQuery" 
          :placeholder="$t('history.searchPlaceholder')"
          class="search-input"
        />
        <button v-if="searchQuery" @click="searchQuery = ''" class="clear-search-btn">×</button>
      </div>

      <!-- Filters Section -->
      <div class="filters-row">
        <!-- Status Filters -->
        <div class="filter-group">
          <span class="filter-label">{{ $t('history.filterStatus') }}</span>
          <div class="filter-options">
            <button 
              v-for="statusOpt in statusOptions" 
              :key="statusOpt.value"
              class="filter-tab-btn"
              :class="{ active: currentStatusFilter === statusOpt.value }"
              @click="currentStatusFilter = statusOpt.value"
            >
              {{ statusOpt.label }}
            </button>
          </div>
        </div>

        <!-- Mode Filters -->
        <div class="filter-group">
          <span class="filter-label">{{ $t('history.filterMode') }}</span>
          <div class="filter-options">
            <button 
              v-for="modeOpt in modeOptions" 
              :key="modeOpt.value"
              class="filter-tab-btn"
              :class="{ active: currentModeFilter === modeOpt.value }"
              @click="currentModeFilter = modeOpt.value"
            >
              {{ modeOpt.label }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Grid Container -->
    <div v-if="filteredProjects.length > 0" class="premium-cards-grid">
      <div 
        v-for="project in filteredProjects" 
        :key="project.simulation_id"
        class="premium-project-card"
        @click="navigateToProject(project)"
      >
        <!-- Card Header -->
        <div class="premium-card-header">
          <span class="premium-card-id">{{ formatSimulationId(project.simulation_id) }}</span>
          
          <div class="badges-group">
            <!-- Mode badge -->
            <span class="mode-tag" :class="project.run_mode || 'courtroom'">
              {{ getModeLabel(project) }}
            </span>
            <!-- Status dot badge -->
            <span class="progress-tag" :class="getProgressClass(project)">
              <span class="status-dot">●</span> {{ getStatusLabel(project) }}
            </span>
          </div>
        </div>

        <!-- Files indicator -->
        <div class="premium-files-strip" v-if="project.files && project.files.length > 0">
          <div 
            v-for="(file, fileIndex) in project.files.slice(0, 3)" 
            :key="fileIndex"
            class="premium-file-pill"
            :title="file.filename"
          >
            <span class="file-pill-tag" :class="getFileType(file.filename)">{{ getFileTypeLabel(file.filename) }}</span>
            <span class="file-pill-name">{{ truncateFilename(file.filename, 14) }}</span>
          </div>
          <div v-if="project.files.length > 3" class="premium-file-pill-more">
            +{{ project.files.length - 3 }}
          </div>
        </div>

        <!-- Content Area -->
        <div class="premium-card-body">
          <h3 class="premium-card-title">{{ getSimulationTitle(project.simulation_requirement) }}</h3>
          <p class="premium-card-desc">{{ project.simulation_requirement }}</p>
        </div>

        <!-- Divider line -->
        <div class="premium-card-divider"></div>

        <!-- Card Footer -->
        <div class="premium-card-footer">
          <!-- Left side info -->
          <div class="footer-meta">
            <span class="rounds-text">{{ formatRounds(project) }}</span>
            <span class="date-text" v-if="project.created_at">{{ formatDate(project.created_at) }}</span>
          </div>

          <!-- Direct action buttons -->
          <div class="footer-actions">
            <!-- Resume Action -->
            <button 
              v-if="canResume(project)"
              class="action-icon-btn resume"
              @click.stop="promptResume(project)"
              :title="$t('history.btnResume')"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
            </button>

            <!-- Rerun Action -->
            <button 
              v-if="canRerun(project)"
              class="action-icon-btn rerun"
              @click.stop="promptRerun(project)"
              :title="$t('history.btnRerun')"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
              </svg>
            </button>

            <!-- View active simulation running -->
            <button 
              v-if="isRunning(project)"
              class="action-icon-btn follow"
              @click.stop="goToActiveSimulation(project)"
              title="Suivre la simulation"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            </button>

            <!-- Report Action -->
            <button 
              v-if="project.report_id"
              class="action-icon-btn report"
              @click.stop="goToReportDirect(project.report_id)"
              :title="$t('history.analysisReport')"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
            </button>

            <span class="action-separator"></span>

            <!-- Delete Action -->
            <button 
              class="action-icon-btn delete"
              @click.stop="promptDelete(project)"
              :title="$t('history.btnDelete')"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading" class="empty-state">
      <span class="empty-icon">◇</span>
      <span>Aucune simulation trouvée</span>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
      <span class="loading-text">{{ $t('history.loadingText') }}</span>
    </div>

    <!-- History Replay Details Modal (keeps the exact same view logic) -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedProject" class="modal-overlay" @click.self="closeModal">
          <div class="modal-content">
            <!-- Modal Header -->
            <div class="modal-header">
              <div class="modal-title-section">
                <span class="modal-id">{{ formatSimulationId(selectedProject.simulation_id) }}</span>
                <span class="modal-progress" :class="getProgressClass(selectedProject)">
                  <span class="status-dot">●</span> {{ formatRounds(selectedProject) }}
                </span>
                <span class="modal-create-time">{{ formatDate(selectedProject.created_at) }} {{ formatTime(selectedProject.created_at) }}</span>
              </div>
              <button class="modal-close" @click="closeModal">×</button>
            </div>

            <!-- Modal Body -->
            <div class="modal-body">
              <!-- Requirement -->
              <div class="modal-section">
                <div class="modal-label">{{ $t('history.simRequirement') }}</div>
                <div class="modal-requirement">{{ selectedProject.simulation_requirement || $t('common.none') }}</div>
              </div>

              <!-- Files -->
              <div class="modal-section">
                <div class="modal-label">{{ $t('history.relatedFiles') }}</div>
                <div class="modal-files" v-if="selectedProject.files && selectedProject.files.length > 0">
                  <div v-for="(file, index) in selectedProject.files" :key="index" class="modal-file-item">
                    <span class="file-tag" :class="getFileType(file.filename)">{{ getFileTypeLabel(file.filename) }}</span>
                    <span class="modal-file-name">{{ file.filename }}</span>
                  </div>
                </div>
                <div class="modal-empty" v-else>{{ $t('history.noRelatedFiles') }}</div>
              </div>
            </div>

            <!-- Replay Section Divider -->
            <div class="modal-divider">
              <span class="divider-line"></span>
              <span class="divider-text">{{ $t('history.replayTitle') }}</span>
              <span class="divider-line"></span>
            </div>

            <!-- Navigation Actions -->
            <div class="modal-actions">
              <button 
                class="modal-btn btn-project" 
                @click="goToProject"
                :disabled="!selectedProject.project_id"
              >
                <span class="btn-step">Step1</span>
                <span class="btn-icon">◇</span>
                <span class="btn-text">{{ $t('history.step1Button') }}</span>
              </button>
              <button 
                class="modal-btn btn-simulation" 
                @click="goToSimulation"
              >
                <span class="btn-step">Step2</span>
                <span class="btn-icon">◈</span>
                <span class="btn-text">{{ $t('history.step2Button') }}</span>
              </button>
              <button 
                class="modal-btn btn-report" 
                @click="goToReport"
                :disabled="!selectedProject.report_id"
              >
                <span class="btn-step">Step4</span>
                <span class="btn-icon">◆</span>
                <span class="btn-text">{{ $t('history.step4Button') }}</span>
              </button>
            </div>
            <!-- Playback hint -->
            <div class="modal-playback-hint">
              <span class="hint-text">{{ $t('history.replayHint') }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Custom Confirmation Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="confirmDialog.show" class="modal-overlay" @click.self="closeConfirm">
          <div class="confirm-modal-content">
            <h4 class="confirm-title">{{ confirmDialog.title }}</h4>
            <p class="confirm-desc">{{ confirmDialog.message }}</p>
            <div class="confirm-actions">
              <button class="confirm-btn cancel" @click="closeConfirm">{{ $t('common.cancel') }}</button>
              <button class="confirm-btn confirm" :class="confirmDialog.type" @click="handleConfirm">
                {{ $t('common.confirm') }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getSimulationHistory, deleteSimulation } from '../api/simulation'

const router = useRouter()
const { t } = useI18n()

// Data states
const projects = ref([])
const loading = ref(true)
const selectedProject = ref(null)

// Search & Filter states
const searchQuery = ref('')
const currentStatusFilter = ref('all')
const currentModeFilter = ref('all')

// Confirmation Dialog State
const confirmDialog = ref({
  show: false,
  title: '',
  message: '',
  type: '', // 'delete' | 'rerun'
  project: null
})

// Translation helpers
const statusOptions = computed(() => [
  { value: 'all', label: t('history.all') },
  { value: 'running', label: t('common.running') },
  { value: 'paused', label: 'En pause' },
  { value: 'completed', label: t('common.completed') },
  { value: 'failed', label: t('common.failed') }
])

const modeOptions = computed(() => [
  { value: 'all', label: t('history.all') },
  { value: 'courtroom', label: 'Judiciaire' },
  { value: 'social', label: 'Réseau Social' },
  { value: 'benchmark', label: "Banc d'Essai" }
])

// Load historical items
const loadHistory = async () => {
  try {
    loading.value = true
    const response = await getSimulationHistory(30)
    if (response.success) {
      projects.value = response.data || []
    }
  } catch (error) {
    console.error('Failed to load history:', error)
    projects.value = []
  } finally {
    loading.value = false
  }
}

// Watch filters to reload if needed, or simply filter client-side
const filteredProjects = computed(() => {
  return projects.value.filter(project => {
    // 1. Text Search
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const matchesId = project.simulation_id.toLowerCase().includes(q)
      const matchesRequirement = (project.simulation_requirement || '').toLowerCase().includes(q)
      if (!matchesId && !matchesRequirement) return false
    }

    // 2. Status Filter
    if (currentStatusFilter.value !== 'all') {
      const status = (project.runner_status || project.status || '').toLowerCase()
      if (currentStatusFilter.value === 'running') {
        if (status !== 'running' && status !== 'starting') return false
      } else if (currentStatusFilter.value === 'paused') {
        if (status !== 'paused') return false
      } else if (currentStatusFilter.value === 'completed') {
        if (status !== 'completed') return false
      } else if (currentStatusFilter.value === 'failed') {
        if (status !== 'failed' && status !== 'stopped') return false
      }
    }

    // 3. Mode Filter
    if (currentModeFilter.value !== 'all') {
      const isBenchmark = project.simulation_id.startsWith('sim_proof_')
      if (currentModeFilter.value === 'benchmark') {
        if (!isBenchmark) return false
      } else if (currentModeFilter.value === 'courtroom') {
        if (isBenchmark || project.run_mode !== 'courtroom') return false
      } else if (currentModeFilter.value === 'social') {
        if (isBenchmark || (project.run_mode !== 'social' && project.run_mode !== 'oasis')) return false
      }
    }

    return true
  })
})

// Progress class helper
const getProgressClass = (simulation) => {
  const current = simulation.current_round || 0
  const total = simulation.total_rounds || 0
  const status = (simulation.runner_status || simulation.status || '').toLowerCase()
  
  if (status === 'running' || status === 'starting') {
    return 'in-progress'
  } else if (status === 'paused') {
    return 'paused'
  } else if (status === 'completed' || current >= total && total > 0) {
    return 'completed'
  } else if (status === 'failed' || status === 'stopped') {
    return 'failed'
  }
  return 'not-started'
}

// Get status label helper
const getStatusLabel = (project) => {
  const status = (project.runner_status || project.status || '').toLowerCase()
  if (status === 'running' || status === 'starting') return t('common.running')
  if (status === 'paused') return 'En pause'
  if (status === 'completed') return t('common.completed')
  if (status === 'failed') return t('common.failed')
  if (status === 'stopped') return 'Arrêté'
  return t('common.pending')
}

// Get mode label helper
const getModeLabel = (project) => {
  if (project.simulation_id.startsWith('sim_proof_')) return "Banc d'Essai"
  if (project.run_mode === 'social' || project.run_mode === 'oasis') return "Réseau Social"
  return "Judiciaire"
}

// Helpers for direct action conditions
const canResume = (project) => {
  const status = (project.runner_status || project.status || '').toLowerCase()
  return (status === 'paused' || status === 'stopped' || status === 'failed')
}

const canRerun = (project) => {
  const status = (project.runner_status || project.status || '').toLowerCase()
  return (status === 'completed' || status === 'stopped' || status === 'failed' || status === 'paused' || status === 'idle')
}

const isRunning = (project) => {
  const status = (project.runner_status || project.status || '').toLowerCase()
  return (status === 'running' || status === 'starting')
}

// Actions handlers
const promptResume = (project) => {
  goToActiveSimulation(project, true)
}

const promptRerun = (project) => {
  confirmDialog.value = {
    show: true,
    title: t('history.confirmTitle'),
    message: t('history.confirmRerun'),
    type: 'rerun',
    project
  }
}

const promptDelete = (project) => {
  confirmDialog.value = {
    show: true,
    title: t('history.confirmTitle'),
    message: t('history.confirmDelete'),
    type: 'delete',
    project
  }
}

const closeConfirm = () => {
  confirmDialog.value.show = false
  confirmDialog.value.project = null
}

const handleConfirm = async () => {
  const project = confirmDialog.value.project
  const type = confirmDialog.value.type
  closeConfirm()
  
  if (!project) return
  
  if (type === 'delete') {
    try {
      loading.value = true
      const res = await deleteSimulation({ simulation_id: project.simulation_id })
      if (res.success) {
        await loadHistory()
      } else {
        alert(res.error || t('history.deleteError'))
      }
    } catch (err) {
      console.error(err)
      alert(t('history.deleteError'))
    } finally {
      loading.value = false
    }
  } else if (type === 'rerun') {
    // Navigate to step 3 in rerun mode
    router.push({
      name: 'SimulationRun',
      params: { simulationId: project.simulation_id },
      query: { 
        runMode: project.run_mode || 'courtroom',
        maxRounds: project.total_rounds || null,
        force: 'true' 
      }
    })
  }
}

const goToActiveSimulation = (project, resume = false) => {
  router.push({
    name: 'SimulationRun',
    params: { simulationId: project.simulation_id },
    query: { 
      runMode: project.run_mode || 'courtroom',
      maxRounds: project.total_rounds || null,
      resume: resume ? 'true' : 'false'
    }
  })
}

// Navigation methods for detail modal
const navigateToProject = (simulation) => {
  selectedProject.value = simulation
}

const closeModal = () => {
  selectedProject.value = null
}

const goToProject = () => {
  if (selectedProject.value?.project_id) {
    router.push({
      name: 'Process',
      params: { projectId: selectedProject.value.project_id }
    })
    closeModal()
  }
}

const goToSimulation = () => {
  if (selectedProject.value?.simulation_id) {
    router.push({
      name: 'Simulation',
      params: { simulationId: selectedProject.value.simulation_id }
    })
    closeModal()
  }
}

const goToReport = () => {
  if (selectedProject.value?.report_id) {
    router.push({
      name: 'Report',
      params: { reportId: selectedProject.value.report_id }
    })
    closeModal()
  }
}

const goToReportDirect = (reportId) => {
  router.push({
    name: 'Report',
    params: { reportId }
  })
}

// Format utilities
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toISOString().slice(0, 10)
  } catch {
    return dateStr?.slice(0, 10) || ''
  }
}

const formatTime = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  } catch {
    return ''
  }
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.slice(0, maxLength) + '...' : text
}

const getSimulationTitle = (requirement) => {
  if (!requirement) return t('history.untitledSimulation')
  const title = requirement.slice(0, 32)
  return requirement.length > 32 ? title + '...' : title
}

const formatSimulationId = (simulationId) => {
  if (!simulationId) return 'SIM_UNKNOWN'
  if (simulationId.startsWith('sim_proof_')) {
    const parts = simulationId.split('_')
    const type = parts[2] || 'proof'
    return `PIE_${type.toUpperCase()}`
  }
  const prefix = simulationId.replace('sim_', '').slice(0, 6)
  return `SIM_${prefix.toUpperCase()}`
}

const formatRounds = (simulation) => {
  const current = simulation.current_round || 0
  const total = simulation.total_rounds || 0
  if (total === 0) return t('history.notStarted')
  return t('history.roundsProgress', { current, total })
}

const getFileType = (filename) => {
  if (!filename) return 'other'
  const ext = filename.split('.').pop()?.toLowerCase()
  const typeMap = {
    'pdf': 'pdf',
    'doc': 'doc', 'docx': 'doc',
    'xls': 'xls', 'xlsx': 'xls', 'csv': 'xls',
    'ppt': 'ppt', 'pptx': 'ppt',
    'txt': 'txt', 'md': 'txt', 'json': 'code',
    'jpg': 'img', 'jpeg': 'img', 'png': 'img', 'gif': 'img',
    'zip': 'zip', 'rar': 'zip', '7z': 'zip'
  }
  return typeMap[ext] || 'other'
}

const getFileTypeLabel = (filename) => {
  if (!filename) return 'FILE'
  const ext = filename.split('.').pop()?.toUpperCase()
  return ext || 'FILE'
}

const truncateFilename = (filename, maxLength) => {
  if (!filename) return t('history.unknownFile')
  if (filename.length <= maxLength) return filename
  
  const ext = filename.includes('.') ? '.' + filename.split('.').pop() : ''
  const nameWithoutExt = filename.slice(0, filename.length - ext.length)
  const truncatedName = nameWithoutExt.slice(0, maxLength - ext.length - 3) + '...'
  return truncatedName + ext
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
/* Main Container styling (Light Slate premium theme - Less dark) */
.history-database-premium {
  position: relative;
  width: 100%;
  min-height: 380px;
  margin-top: 50px;
  padding: 40px 24px 60px;
  background: radial-gradient(circle at top, #F8FAFC 0%, #E2E8F0 100%);
  border: 1px solid #CBD5E1;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  overflow: visible;
  z-index: 10;
}

/* Background overlay lines */
.tech-grid-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
  border-radius: 12px;
}

.grid-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(15, 23, 42, 0.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15, 23, 42, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  background-position: top left;
}

.gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    linear-gradient(to bottom, rgba(248, 250, 252, 0.1) 0%, rgba(226, 232, 240, 0.6) 100%);
}

/* Section Header */
.section-header {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 30px;
  font-family: 'JetBrains Mono', monospace;
}

.section-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(197, 168, 128, 0.4), transparent);
  max-width: 250px;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #8C6D3B; /* Bronze/gold */
  letter-spacing: 4px;
  text-transform: uppercase;
  text-shadow: 0 0 10px rgba(197, 168, 128, 0.1);
}

/* Search & Filter Controls Panel styling */
.search-filter-panel {
  position: relative;
  z-index: 5;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 35px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
}

.search-wrapper {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 14px;
  color: #64748B;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 12px 16px 12px 42px;
  background: #FFFFFF;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  color: #0F172A;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #C5A880;
  background: #FFFFFF;
  box-shadow: 0 0 0 3px rgba(197, 168, 128, 0.15);
}

.clear-search-btn {
  position: absolute;
  right: 14px;
  background: transparent;
  border: none;
  color: #94A3B8;
  font-size: 1.2rem;
  cursor: pointer;
}

.clear-search-btn:hover {
  color: #0F172A;
}

/* Filters Row */
.filters-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-grow: 1;
}

.filter-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #8C6D3B;
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
}

.filter-options {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-tab-btn {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid #E2E8F0;
  border-radius: 4px;
  color: #475569;
  padding: 6px 12px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-tab-btn:hover {
  background: #FFFFFF;
  color: #0F172A;
  border-color: #CBD5E1;
}

.filter-tab-btn.active {
  background: #9A7B56;
  border-color: #9A7B56;
  color: #FFFFFF;
  font-weight: 600;
}

/* Premium Responsive Grid */
.premium-cards-grid {
  position: relative;
  z-index: 5;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

/* Premium Project Card (Sleek light premium card) */
.premium-project-card {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04);
  position: relative;
}

.premium-project-card:hover {
  transform: translateY(-4px);
  background: #FFFFFF;
  border-color: rgba(197, 168, 128, 0.6);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

/* Card Header */
.premium-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.premium-card-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 700;
  color: #8C6D3B;
}

.badges-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}

.mode-tag.courtroom {
  background: rgba(59, 130, 246, 0.1);
  color: #2563EB;
}

.mode-tag.social, .mode-tag.oasis {
  background: rgba(139, 92, 246, 0.1);
  color: #7C3AED;
}

.mode-tag.benchmark {
  background: rgba(236, 72, 153, 0.1);
  color: #DB2777;
}

.progress-tag {
  font-family: 'Inter', sans-serif;
  font-size: 0.65rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.progress-tag .status-dot {
  font-size: 0.5rem;
}

.progress-tag.completed { color: #059669; }
.progress-tag.in-progress { color: #D97706; }
.progress-tag.paused { color: #2563EB; }
.progress-tag.failed { color: #DC2626; }
.progress-tag.not-started { color: #475569; }

/* Files Pill Strip */
.premium-files-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
  padding: 6px 8px;
  background: #F1F5F9;
  border-radius: 4px;
  border: 1px solid #E2E8F0;
}

.premium-file-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  padding: 3px 6px;
  border-radius: 3px;
  font-size: 0.65rem;
  color: #475569;
  max-width: 140px;
}

.file-pill-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  font-weight: 700;
  padding: 1px 3px;
  border-radius: 2px;
  line-height: 1;
}

.file-pill-tag.pdf { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
.file-pill-tag.doc { background: rgba(59, 130, 246, 0.1); color: #3B82F6; }
.file-pill-tag.xls { background: rgba(16, 185, 129, 0.1); color: #10B981; }
.file-pill-tag.txt { background: rgba(107, 114, 128, 0.1); color: #6B7280; }
.file-pill-tag.other { background: rgba(107, 114, 128, 0.05); color: #6B7280; }

.file-pill-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.premium-file-pill-more {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #64748B;
  display: flex;
  align-items: center;
  padding: 0 4px;
}

/* Card Body */
.premium-card-body {
  flex-grow: 1;
  margin-bottom: 16px;
}

.premium-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #0F172A;
  margin: 0 0 6px 0;
  line-height: 1.4;
}

.premium-card-desc {
  font-size: 0.75rem;
  color: #475569;
  margin: 0;
  line-height: 1.5;
  height: 45px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.premium-card-divider {
  height: 1px;
  background: #E2E8F0;
  margin-bottom: 14px;
}

/* Card Footer */
.premium-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rounds-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  color: #8C6D3B;
}

.date-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #64748B;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 5px;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-icon-btn:hover {
  background: #E2E8F0;
  color: #0F172A;
}

.action-icon-btn.resume {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.3);
  color: #059669;
}

.action-icon-btn.resume:hover {
  background: #10B981;
  color: #FFFFFF;
  border-color: #10B981;
}

.action-icon-btn.rerun {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  color: #D97706;
}

.action-icon-btn.rerun:hover {
  background: #F59E0B;
  color: #FFFFFF;
  border-color: #F59E0B;
}

.action-icon-btn.follow {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: #2563EB;
  animation: pulse-border 1.5s infinite;
}

.action-icon-btn.follow:hover {
  background: #3B82F6;
  color: #FFFFFF;
  border-color: #3B82F6;
}

.action-icon-btn.report {
  background: rgba(197, 168, 128, 0.15);
  border-color: rgba(197, 168, 128, 0.3);
  color: #8C6D3B;
}

.action-icon-btn.report:hover {
  background: #C5A880;
  color: #FFFFFF;
  border-color: #C5A880;
}

.action-separator {
  width: 1px;
  height: 16px;
  background: #E2E8F0;
}

.action-icon-btn.delete {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.2);
  color: #EF4444;
}

.action-icon-btn.delete:hover {
  background: #EF4444;
  color: #FFFFFF;
  border-color: #EF4444;
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); }
  100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}

/* Empty/Loading States */
.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 60px 40px;
  color: #64748B;
  position: relative;
  z-index: 5;
}

.empty-icon {
  font-size: 2rem;
  color: #8C6D3B;
  opacity: 0.8;
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 2px solid rgba(15, 23, 42, 0.05);
  border-top-color: #C5A880;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Modal details overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-content {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  width: 560px;
  max-width: 90vw;
  border-radius: 8px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15);
  overflow-y: auto;
  max-height: 85vh;
}

/* Modal details header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #E2E8F0;
  background: #F8FAFC;
}

.modal-title-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.95rem;
  font-weight: 700;
  color: #8C6D3B;
}

.modal-progress {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.modal-progress.completed { background: rgba(16, 185, 129, 0.15); color: #059669; }
.modal-progress.in-progress { background: rgba(245, 158, 11, 0.15); color: #D97706; }
.modal-progress.paused { background: rgba(59, 130, 246, 0.15); color: #2563EB; }
.modal-progress.failed { background: rgba(239, 68, 68, 0.15); color: #DC2626; }
.modal-progress.not-started { background: rgba(148, 163, 184, 0.1); color: #475569; }

.modal-create-time {
  font-size: 0.7rem;
  color: #64748B;
  font-family: 'JetBrains Mono', monospace;
}

.modal-close {
  background: transparent;
  border: none;
  color: #94A3B8;
  font-size: 1.5rem;
  cursor: pointer;
}

.modal-close:hover {
  color: #0F172A;
}

/* Modal Body */
.modal-body {
  padding: 20px 24px;
}

.modal-section {
  margin-bottom: 20px;
}

.modal-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #8C6D3B;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.modal-requirement {
  font-size: 0.85rem;
  color: #1E293B;
  line-height: 1.6;
  background: #F8FAFC;
  padding: 12px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
}

.modal-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 4px;
  padding: 8px 12px;
}

.file-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 2px;
}

.file-tag.pdf { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
.file-tag.doc { background: rgba(59, 130, 246, 0.1); color: #3B82F6; }
.file-tag.xls { background: rgba(16, 185, 129, 0.1); color: #10B981; }
.file-tag.txt { background: rgba(107, 114, 128, 0.15); color: #475569; }

.modal-file-name {
  font-size: 0.8rem;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal-empty {
  font-size: 0.8rem;
  color: #94A3B8;
  font-style: italic;
}

/* Modal Divider */
.modal-divider {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: #E2E8F0;
}

.divider-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #94A3B8;
  letter-spacing: 2px;
  text-transform: uppercase;
}

/* Modal Actions buttons */
.modal-actions {
  display: flex;
  gap: 12px;
  padding: 20px 24px;
}

.modal-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.modal-btn:hover:not(:disabled) {
  border-color: #C5A880;
  background: #FFFFFF;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}

.modal-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-step {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: #64748B;
}

.btn-icon {
  font-size: 1.2rem;
}

.btn-text {
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  color: #1E293B;
}

.modal-btn.btn-project .btn-icon { color: #2563EB; }
.modal-btn.btn-simulation .btn-icon { color: #D97706; }
.modal-btn.btn-report .btn-icon { color: #059669; }

.modal-playback-hint {
  padding: 0 24px 16px;
  text-align: center;
}

.hint-text {
  font-size: 0.65rem;
  color: #64748B;
  line-height: 1.4;
}

/* Custom Confirm Modal styling */
.confirm-modal-content {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 24px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 25px 50px rgba(15, 23, 42, 0.12);
  text-align: center;
  animation: scale-up 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes scale-up {
  0% { transform: scale(0.9); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.confirm-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 12px;
}

.confirm-desc {
  font-size: 0.85rem;
  color: #475569;
  line-height: 1.5;
  margin: 0 0 20px;
}

.confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.confirm-btn {
  padding: 8px 20px;
  border-radius: 5px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.confirm-btn.cancel {
  background: transparent;
  border-color: #CBD5E1;
  color: #475569;
}

.confirm-btn.cancel:hover {
  background: #F1F5F9;
  color: #0F172A;
  border-color: #CBD5E1;
}

.confirm-btn.confirm {
  background: #C5A880;
  color: #FFFFFF;
}

.confirm-btn.confirm:hover {
  background: #D5B890;
}

.confirm-btn.confirm.delete {
  background: #EF4444;
  color: #FFFFFF;
}

.confirm-btn.confirm.delete:hover {
  background: #DC2626;
}

/* Modal Animations */
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content, .modal-enter-active .confirm-modal-content {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-enter-from .modal-content, .modal-enter-from .confirm-modal-content {
  transform: scale(0.95);
  opacity: 0;
}
</style>
