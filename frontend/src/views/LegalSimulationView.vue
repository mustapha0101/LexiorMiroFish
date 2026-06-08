<template>
  <div class="legal-sim-container">
    <div class="backdrop"></div>
    
    <header class="legal-header">
      <div class="brand" @click="goHome">
        <img src="/logo.png" class="brand-logo" alt="Lexior" />
        <span class="brand-name">{{ $t('common.brandFirst') }} <span class="brand-sub">{{ $t('common.brandSecond') }}</span></span>
      </div>
      <div class="header-title">Laboratoire Juridique • Monte-Carlo</div>
      <div class="header-right">
        <button class="back-btn" @click="goHome">Retour</button>
      </div>
    </header>

    <main class="legal-main" :class="{ 'full-width': status === 'completed' }">
      <!-- Panneau de configuration -->
      <div class="glass-panel input-panel" v-if="status !== 'completed'" :class="{ 'is-loading': status === 'loading' }">
        <h1 class="panel-title">Configuration du Procès</h1>
        <p class="panel-desc">Saisissez les faits de la cause. Les agents (Procureur et Avocat) s'affronteront en se basant sur la jurisprudence réelle.</p>

        <div class="form-group">
          <label>Contexte de l'Affaire / Décision de Justice</label>
          <textarea 
            v-model="contextText" 
            placeholder="Saisissez les faits détaillés... Ex: Le prévenu est poursuivi pour vol qualifié avec arme factice dans une banque. Il invoque la contrainte et l'état de nécessité sous la menace de complices..."
            rows="8"
            :disabled="status === 'loading'"
          ></textarea>
        </div>

        <div class="form-group">
          <label>Nombre de simulations de procès (Monte-Carlo)</label>
          <div class="slider-group">
            <input 
              type="range" 
              v-model="iterations" 
              min="1" 
              max="50" 
              step="1"
              :disabled="status === 'loading'"
            >
            <span class="value-display">{{ iterations }}</span>
          </div>
          <span class="helper-text">Plus le nombre est élevé, plus l'analyse statistique des chances d'acquittement est précise.</span>
        </div>

        <button 
          class="run-btn" 
          @click="startSimulation" 
          :disabled="!contextText || status === 'loading'"
        >
          <span v-if="status === 'idle'">Lancer la simulation</span>
          <span v-else class="loader-text">Délibération en cours...</span>
        </button>
      </div>

      <!-- Panneau de résultats et chargement -->
      <div class="glass-panel result-panel" v-if="status === 'loading' || status === 'completed'" :class="{ 'has-results': status === 'completed' }">
        
        <!-- ÉTAT : CHARGEMENT -->
        <div v-if="status === 'loading'" class="loading-state">
          <div class="spinner"></div>
          <div class="loading-status">{{ taskMessage }}</div>
          <div class="progress-bar-container">
            <div class="progress-bar-fill" :style="{ width: taskProgress + '%' }"></div>
          </div>
          <div class="progress-text">{{ taskProgress }}%</div>
        </div>

        <!-- ÉTAT : COMPLÉTÉ -->
        <div v-else-if="status === 'completed'" class="completed-state-container">
          <!-- Entête des résultats -->
          <div class="results-header">
            <h2>Analyse Prédictive Juridique</h2>
            <button class="new-sim-btn" @click="resetSimulation">Nouveau Procès</button>
          </div>

          <div class="stats-and-summary">
            <!-- Graphique de taux d'acquittement -->
            <div class="win-dashboard">
              <div class="win-circle" :style="winStyle">
                <span class="win-rate">{{ winRate }}%</span>
                <span class="win-label">{{ isCivil ? 'Chances de Rejet' : 'Chances de Relaxe' }}</span>
              </div>
              <div class="win-stats-details">
                <div class="stat-detail-item">
                  <span class="stat-number text-win">{{ simResults ? simResults.defense_wins : 0 }}</span>
                  <span class="stat-label">{{ isCivil ? 'Rejets de la Demande' : 'Relaxes / Acquittements' }}</span>
                </div>
                <div class="stat-detail-item">
                  <span class="stat-number text-loss">{{ simResults ? (simResults.iterations - simResults.defense_wins) : 0 }}</span>
                  <span class="stat-label">{{ isCivil ? 'Responsabilités' : 'Condamnations' }}</span>
                </div>
                <div class="stat-detail-item">
                  <span class="stat-number text-gold">{{ simResults ? simResults.iterations : 0 }}</span>
                  <span class="stat-label">Procès simulés</span>
                </div>
              </div>
            </div>
            
            <!-- Synthèse du greffier -->
            <div class="summary-box">
              <h3>Synthèse de l'IA Greffier</h3>
              <p>{{ clerkSummary }}</p>
            </div>
          </div>

          <!-- Section Détail des Procès -->
          <div class="trials-details-section">
            <div class="trials-section-header">
              <h3>Détails des Itérations (Monte-Carlo)</h3>
              <p class="trials-desc">Chaque itération simule un procès complet devant un juge ayant une personnalité unique.</p>
            </div>
            
            <div class="trials-layout">
              <!-- Liste des procès (Gauche) -->
              <div class="trials-list">
                <div 
                  v-for="trial in (simResults ? simResults.details : [])" 
                  :key="trial.iteration"
                  class="trial-list-item"
                  :class="{ 'is-selected': selectedIteration && selectedIteration.iteration === trial.iteration, 'win': trial.is_defense_win, 'loss': !trial.is_defense_win }"
                  @click="selectedIteration = trial"
                >
                  <div class="trial-meta">
                    <span class="trial-number">Procès #{{ trial.iteration }}</span>
                    <span class="trial-judge-personality-short">{{ getJudgePersonalityShort(trial.judge_personality) }}</span>
                  </div>
                  <span class="verdict-badge" :class="trial.is_defense_win ? 'badge-win' : 'badge-loss'">
                    {{ trial.is_defense_win ? (isCivil ? 'REJET' : 'RELAXE') : (isCivil ? 'RESPONSABLE' : 'CONDAMNÉ') }}
                  </span>
                </div>
              </div>

              <!-- Transcriptions du procès sélectionné (Droite) -->
              <div class="trial-transcript-panel">
                <div v-if="selectedIteration" class="transcript-container">
                  <div class="transcript-header">
                    <h4>Retranscription du Procès #{{ selectedIteration.iteration }}</h4>
                    <div class="judge-profile-card">
                      <span class="badge">Juge affecté</span>
                      <span class="judge-personality-desc">{{ selectedIteration.judge_personality }}</span>
                    </div>
                  </div>
                  
                  <!-- Déroulé des messages -->
                  <div class="transcript-messages">
                    <div 
                      v-for="(msg, idx) in selectedIteration.transcript" 
                      :key="idx"
                      class="speech-bubble-wrapper"
                      :class="getSpeechRole(msg)"
                    >
                      <div class="speech-sender-badge">
                        {{ getSpeechSenderLabel(msg) }}
                      </div>
                      <div class="speech-bubble">
                        <p v-html="formatSpeechText(msg)"></p>
                      </div>
                    </div>
                  </div>

                  <!-- Analyse spécifique de cette itération par le greffier -->
                  <div class="clerk-verdict-analysis">
                    <h5>Décryptage rhétorique du Greffier</h5>
                    <p>{{ selectedIteration.clerk_analysis }}</p>
                  </div>
                </div>

                <!-- État vide (Aucun procès sélectionné) -->
                <div v-else class="transcript-empty-state">
                  <div class="gavel-icon">⚖</div>
                  <p v-if="isCivil">Sélectionnez une itération de procès dans la liste de gauche pour analyser les plaidoiries de l'Avocat du Demandeur, la plaidoirie de la Défense et le jugement motivé rendu par le Juge.</p>
                  <p v-else>Sélectionnez une itération de procès dans la liste de gauche pour analyser le réquisitoire du Procureur, la plaidoirie de la Défense et le verdict motivé rendu par le Juge.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const contextText = ref('')
const iterations = ref(10)
const status = ref('idle') // idle, loading, completed
const winRate = ref(0)
const clerkSummary = ref('')

const taskId = ref(null)
const taskProgress = ref(0)
const taskMessage = ref('')
const simResults = ref(null)
const selectedIteration = ref(null)
const projectId = ref(route.query.projectId || null)

const isCivil = computed(() => {
  return simResults.value?.litigation_type === 'civil'
})

onMounted(async () => {
  if (projectId.value) {
    status.value = 'loading'
    taskMessage.value = "Chargement du contexte textuel et du graphe de connaissances..."
    try {
      const response = await fetch(`http://localhost:5001/api/graph/project/${projectId.value}/text`)
      const res = await response.json()
      if (res.success && res.data?.text) {
        contextText.value = res.data.text
      } else {
        console.error("Erreur de chargement du texte du projet:", res.error)
      }
    } catch (err) {
      console.error("Exception lors du chargement du texte:", err)
    } finally {
      status.value = 'idle'
      taskMessage.value = ''
    }
  }
})

const winStyle = computed(() => {
  return {
    background: `conic-gradient(#D4AF37 ${winRate.value}%, rgba(255,255,255,0.06) 0)`
  }
})

const goHome = () => {
  router.push('/')
}

const startSimulation = async () => {
  if (!contextText.value) return
  status.value = 'loading'
  taskProgress.value = 0
  taskMessage.value = "Initialisation de la simulation de Monte-Carlo..."
  simResults.value = null
  selectedIteration.value = null
  
  try {
    const response = await fetch('http://localhost:5001/api/simulation/legal/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        context: contextText.value,
        iterations: Number(iterations.value),
        project_id: projectId.value
      })
    })
    const res = await response.json()
    if (res.success && res.data.task_id) {
      taskId.value = res.data.task_id
      pollTask(res.data.task_id)
    } else {
      throw new Error(res.error || 'Erreur inconnue.')
    }
  } catch (err) {
    console.error(err)
    status.value = 'idle'
    alert("Impossible de lancer la simulation : " + err.message)
  }
}

const pollTask = (id) => {
  const timer = setInterval(async () => {
    try {
      const response = await fetch(`http://localhost:5001/api/graph/task/${id}`)
      const res = await response.json()
      if (res.success && res.data) {
        const task = res.data
        taskProgress.value = task.progress || 0
        taskMessage.value = task.message || 'Délibération des agents en cours...'
        
        if (task.status === 'completed') {
          clearInterval(timer)
          fetchResult(id)
        } else if (task.status === 'failed') {
          clearInterval(timer)
          status.value = 'idle'
          alert("La simulation a échoué : " + task.error)
        }
      }
    } catch (err) {
      console.error("Erreur de polling :", err)
    }
  }, 1000)
}

const fetchResult = async (id) => {
  try {
    const response = await fetch(`http://localhost:5001/api/simulation/legal/result/${id}`)
    const res = await response.json()
    if (res.success && res.data) {
      simResults.value = res.data
      winRate.value = Math.round(res.data.win_rate)
      
      const details = res.data.details || []
      if (details.length > 0) {
        clerkSummary.value = details[0].clerk_analysis || "Procès simulés avec succès."
      } else {
        clerkSummary.value = "La simulation est terminée mais aucune donnée n'a été extraite."
      }
      
      status.value = 'completed'
    } else {
      alert("Erreur de récupération des résultats.")
      status.value = 'idle'
    }
  } catch (err) {
    console.error(err)
    status.value = 'idle'
  }
}

const resetSimulation = () => {
  status.value = 'idle'
  taskId.value = null
  taskProgress.value = 0
  taskMessage.value = ''
  simResults.value = null
  selectedIteration.value = null
}

const getSpeechRole = (msg) => {
  if (msg.startsWith("PROCUREUR:")) return "prosecutor"
  if (msg.startsWith("DEFENSE:")) return "defense"
  if (msg.startsWith("JUGE:")) return "judge"
  return "narrator"
}

const getSpeechSenderLabel = (msg) => {
  if (msg.startsWith("PROCUREUR:")) return isCivil.value ? "Avocat du Demandeur" : "Le Procureur (Accusation)"
  if (msg.startsWith("DEFENSE:")) return "L'Avocat (Défense)"
  if (msg.startsWith("JUGE:")) return "Le Juge (Verdict)"
  return "Rapport d'audience"
}

const getJudgePersonalityShort = (desc) => {
  if (!desc) return "Juge"
  return desc.split('(')[0].trim()
}

const formatSpeechText = (msg) => {
  let text = msg
  if (msg.startsWith("PROCUREUR:")) text = msg.substring(10).trim()
  else if (msg.startsWith("DEFENSE:")) text = msg.substring(8).trim()
  else if (msg.startsWith("JUGE:")) text = msg.substring(5).trim()
  
  text = text.replace(/(Selon l'arrêt [^,]+,)/gi, '<strong class="highlight-jurisprudence">$1</strong>')
  text = text.replace(/(OBJECTION : .*)/gi, '<span class="objection-alert">$1</span>')
  
  if (isCivil.value) {
    text = text.replace(/(RESPONSABLE)/g, '<strong class="verdict-guilty">$1</strong>')
    text = text.replace(/(NON RESPONSABLE|REJETTE|DEBOUTE|REJET)/g, '<strong class="verdict-acquitted">$1</strong>')
  } else {
    text = text.replace(/(COUPABLE)/g, '<strong class="verdict-guilty">$1</strong>')
    text = text.replace(/(NON COUPABLE|RELAXE|ACQUITTEMENT)/g, '<strong class="verdict-acquitted">$1</strong>')
  }

  return text
}
</script>

<style scoped>
.legal-sim-container {
  min-height: 100vh;
  background: #080B11;
  background-image: radial-gradient(circle at top right, rgba(212, 175, 55, 0.08), transparent 45%),
                    radial-gradient(circle at bottom left, rgba(26, 147, 111, 0.05), transparent 50%);
  color: #E2E8F0;
  font-family: 'Inter', system-ui, sans-serif;
  overflow-x: hidden;
  padding-bottom: 60px;
}

.legal-header {
  height: 70px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(8, 11, 17, 0.8);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.brand-logo {
  height: 26px;
  width: auto;
}

.brand-name {
  font-family: 'Playfair Display', Georgia, serif;
  font-weight: 700;
  font-size: 17px;
  letter-spacing: 0.5px;
  color: #FFFFFF;
}

.brand-sub {
  color: #D4AF37;
  font-weight: 500;
}

.header-title {
  font-weight: 300;
  letter-spacing: 1.5px;
  color: #94A3B8;
  font-size: 14px;
  text-transform: uppercase;
}

.back-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: white;
  padding: 6px 18px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: #D4AF37;
  color: #D4AF37;
}

.legal-main {
  max-width: 1280px;
  margin: 40px auto 0;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 30px;
  padding: 0 25px;
  transition: all 0.5s ease;
}

.legal-main.full-width {
  grid-template-columns: 1fr;
}

.glass-panel {
  background: rgba(15, 20, 30, 0.6);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 35px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  height: fit-content;
}

.input-panel {
  transition: all 0.3s ease;
}

.input-panel.is-loading {
  opacity: 0.5;
  pointer-events: none;
}

.panel-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 26px;
  font-weight: 500;
  color: #D4AF37;
  margin-bottom: 8px;
  margin-top: 0;
}

.panel-desc {
  font-size: 14px;
  color: #94A3B8;
  margin-bottom: 30px;
  line-height: 1.5;
}

.form-group {
  margin-bottom: 28px;
}

.form-group label {
  display: block;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 10px;
  color: #94A3B8;
  font-weight: 600;
}

textarea {
  width: 100%;
  background: rgba(5, 7, 12, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 15px;
  color: white;
  font-family: inherit;
  resize: vertical;
  line-height: 1.6;
  font-size: 14px;
  transition: all 0.3s;
}

textarea:focus {
  outline: none;
  border-color: #D4AF37;
  background: rgba(5, 7, 12, 0.8);
  box-shadow: 0 0 10px rgba(212, 175, 55, 0.15);
}

.slider-group {
  display: flex;
  align-items: center;
  gap: 20px;
}

input[type=range] {
  flex: 1;
  accent-color: #D4AF37;
  height: 5px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
}

.value-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  color: #D4AF37;
  width: 45px;
  text-align: right;
  font-weight: bold;
}

.helper-text {
  display: block;
  font-size: 11px;
  color: #64748B;
  margin-top: 6px;
}

.run-btn {
  width: 100%;
  padding: 16px;
  background: #D4AF37;
  color: #080B11;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1.5px;
}

.run-btn:disabled {
  background: #2D3748;
  color: #718096;
  cursor: not-allowed;
}

.run-btn:not(:disabled):hover {
  background: #E5C354;
  box-shadow: 0 0 25px rgba(212, 175, 55, 0.25);
  transform: translateY(-1px);
}

/* RÉSULTATS & CHARGEMENT */
.result-panel {
  display: flex;
  flex-direction: column;
  min-height: 480px;
  justify-content: center;
}

.result-panel.has-results {
  justify-content: flex-start;
  min-height: auto;
}

.loading-state {
  text-align: center;
  padding: 40px 0;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255, 255, 255, 0.05);
  border-top-color: #D4AF37;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 24px;
}

.loading-status {
  color: #94A3B8;
  font-size: 15px;
  font-weight: 400;
}

.progress-bar-container {
  width: 250px;
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  margin: 18px auto 8px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #D4AF37;
  border-radius: 2px;
  transition: width 0.3s ease-out;
}

.progress-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #D4AF37;
}

/* COMPLETED STATE CONTENEUR */
.completed-state-container {
  width: 100%;
  animation: fadeIn 0.6s ease-out;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 20px;
  margin-bottom: 25px;
}

.results-header h2 {
  font-family: 'Playfair Display', Georgia, serif;
  margin: 0;
  font-size: 24px;
  color: #FFFFFF;
}

.new-sim-btn {
  background: rgba(212, 175, 55, 0.1);
  border: 1px solid #D4AF37;
  color: #D4AF37;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.new-sim-btn:hover {
  background: #D4AF37;
  color: #080B11;
  box-shadow: 0 0 15px rgba(212, 175, 55, 0.2);
}

/* STATS ROW */
.stats-and-summary {
  display: flex;
  gap: 30px;
  align-items: flex-start;
  margin-bottom: 40px;
}

.win-dashboard {
  display: flex;
  gap: 25px;
  align-items: center;
  background: rgba(5, 7, 12, 0.4);
  padding: 20px 25px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

.win-circle {
  width: 130px;
  height: 130px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
}

.win-circle::after {
  content: '';
  position: absolute;
  width: 116px;
  height: 116px;
  background: #0E131F;
  border-radius: 50%;
  z-index: 0;
}

.win-rate {
  position: relative;
  z-index: 1;
  font-size: 32px;
  font-weight: 800;
  color: #D4AF37;
  font-family: 'JetBrains Mono', monospace;
}

.win-label {
  position: relative;
  z-index: 1;
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: #94A3B8;
  margin-top: 2px;
}

.win-stats-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-detail-item {
  display: flex;
  flex-direction: column;
}

.stat-number {
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 700;
}

.stat-label {
  font-size: 11px;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 1px;
}

.text-win {
  color: #2ecc71;
}

.text-loss {
  color: #e74c3c;
}

.text-gold {
  color: #D4AF37;
}

.summary-box {
  flex: 1;
  background: rgba(26, 147, 111, 0.05);
  padding: 22px 25px;
  border-radius: 8px;
  border-left: 4px solid #1A936F;
  min-height: 130px;
}

.summary-box h3 {
  color: #1A936F;
  font-size: 13px;
  margin-top: 0;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.summary-box p {
  color: #CBD5E1;
  font-size: 13.5px;
  line-height: 1.6;
  margin: 0;
}

/* SECTION TENTATIVE DETAILS */
.trials-details-section {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 30px;
}

.trials-section-header {
  margin-bottom: 20px;
}

.trials-section-header h3 {
  margin: 0 0 6px 0;
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 20px;
  color: #FFFFFF;
}

.trials-desc {
  font-size: 13px;
  color: #64748B;
  margin: 0;
}

.trials-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 25px;
  margin-top: 25px;
  align-items: stretch;
}

/* LISTE DES PROCES */
.trials-list {
  background: rgba(5, 7, 12, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  height: 480px;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trial-list-item {
  padding: 12px 16px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
}

.trial-list-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateX(2px);
}

.trial-list-item.is-selected {
  background: rgba(212, 175, 55, 0.08);
  border-color: #D4AF37;
}

.trial-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.trial-number {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}

.trial-judge-personality-short {
  font-size: 11px;
  color: #94A3B8;
}

.verdict-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.badge-win {
  background: rgba(26, 147, 111, 0.12);
  color: #2ecc71;
  border: 1px solid rgba(26, 147, 111, 0.3);
}

.badge-loss {
  background: rgba(197, 40, 61, 0.12);
  color: #e74c3c;
  border: 1px solid rgba(197, 40, 61, 0.3);
}

/* TRANSCRIPT PANEL */
.trial-transcript-panel {
  background: rgba(5, 7, 12, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  height: 480px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.transcript-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.transcript-header {
  background: rgba(10, 15, 25, 0.6);
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.transcript-header h4 {
  margin: 0 0 6px 0;
  font-size: 15px;
  color: #FFFFFF;
}

.judge-profile-card {
  display: flex;
  align-items: center;
  gap: 10px;
}

.judge-profile-card .badge {
  background: rgba(212, 175, 55, 0.12);
  color: #D4AF37;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid rgba(212, 175, 55, 0.2);
}

.judge-personality-desc {
  font-size: 12px;
  color: #CBD5E1;
}

.transcript-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: rgba(3, 5, 8, 0.3);
}

.speech-bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.speech-bubble-wrapper.prosecutor {
  align-self: flex-start;
}

.speech-bubble-wrapper.defense {
  align-self: flex-end;
  align-items: flex-end;
}

.speech-bubble-wrapper.judge {
  align-self: center;
  max-width: 90%;
  align-items: center;
}

.speech-sender-badge {
  font-size: 10px;
  font-weight: 600;
  color: #64748B;
  margin-bottom: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.prosecutor .speech-sender-badge {
  color: #e74c3c;
}

.defense .speech-sender-badge {
  color: #3498db;
}

.judge .speech-sender-badge {
  color: #D4AF37;
}

.speech-bubble {
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.prosecutor .speech-bubble {
  background: rgba(197, 40, 61, 0.06);
  border: 1px solid rgba(197, 40, 61, 0.15);
  border-top-left-radius: 0;
  color: #E2E8F0;
}

.defense .speech-bubble {
  background: rgba(52, 152, 219, 0.06);
  border: 1px solid rgba(52, 152, 219, 0.15);
  border-top-right-radius: 0;
  color: #E2E8F0;
}

.judge .speech-bubble {
  background: rgba(212, 175, 55, 0.05);
  border: 1px solid rgba(212, 175, 55, 0.18);
  text-align: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  color: #FFF;
  font-weight: 500;
}

/* CUSTOM HIGHLIGHTS IN SPEECH */
:deep(.highlight-jurisprudence) {
  color: #D4AF37;
  font-weight: 600;
}

:deep(.objection-alert) {
  display: block;
  margin-top: 10px;
  background: rgba(197, 40, 61, 0.15);
  border: 1px solid #C5283D;
  color: #ff7675;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 600;
}

:deep(.verdict-guilty) {
  color: #ff7675;
  font-weight: bold;
}

:deep(.verdict-acquitted) {
  color: #2ecc71;
  font-weight: bold;
}

/* GREFFIER DÉCRYPTAGE (Bas du Transcript) */
.clerk-verdict-analysis {
  background: rgba(15, 23, 42, 0.8);
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.clerk-verdict-analysis h5 {
  margin: 0 0 6px 0;
  font-size: 12px;
  text-transform: uppercase;
  color: #1A936F;
  letter-spacing: 0.5px;
}

.clerk-verdict-analysis p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: #CBD5E1;
}

/* EMPTY STATE TRANSCRIPT */
.transcript-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  text-align: center;
  color: #64748B;
}

.gavel-icon {
  font-size: 48px;
  color: rgba(255, 255, 255, 0.08);
  margin-bottom: 15px;
}

.transcript-empty-state p {
  max-width: 320px;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

/* SCROLLBAR CUSTOMIZATION */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
