<template>
  <div class="cognitive-visualizer-container" :class="{ 'legal-mode': isLegal }">
    <div class="visualizer-header">
      <div class="title-group">
        <span class="pulse-dot" :class="{ 'legal-pulse': isLegal, 'history-pulse': selectedRound !== 'live' }"></span>
        <h3 class="panel-title">
          {{ isLegal ? 'Procès Judiciaire - Intelligence Cognitive' : 'Réseau Social Public - Intelligence Cognitive' }}
          <span v-if="selectedRound !== 'live'" class="history-banner-badge">ROUND {{ selectedRound }}</span>
        </h3>
      </div>
      
      <div class="agent-selector-wrapper" style="display: flex; gap: 10px; align-items: center;">
        <!-- Sélecteur de Round -->
        <select v-model="selectedRound" class="agent-select">
          <option value="live">⚡ Temps Réel</option>
          <option v-for="r in availableRounds" :key="r" :value="r">
            Round {{ r }}
          </option>
        </select>

        <select v-model="selectedAgentId" class="agent-select">
          <option value="" disabled>-- Sélectionner un Acteur --</option>
          <option v-for="state in states" :key="state.agent_id" :value="state.agent_id">
            {{ state.name }} (ID: {{ state.agent_id }})
          </option>
        </select>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="states.length === 0" class="empty-state">
      <div class="empty-icon">{{ isLegal ? '⚖️' : '💬' }}</div>
      <p>{{ isLegal ? 'Aucun état cognitif détecté pour l\'instant. Les états apparaîtront au lancement du procès.' : 'Aucun état cognitif détecté pour l\'instant. Les états apparaîtront au lancement de la simulation.' }}</p>
    </div>

    <!-- Active State Details -->
    <div v-else class="cognitive-dashboard">
      
      <!-- CONTROLS & CHARTS FOR LEGAL MODE -->
      <div v-if="isLegal" class="charts-row">
        <!-- Card 1: Entropie Narrative (Chaos factor) -->
        <div class="card chart-card">
          <div class="card-title-with-value">
            <span class="card-title">Score d'Entropie Narrative (Shannon)</span>
            <span class="value-badge entropy-badge mono" v-if="currentEntropy !== null">
              {{ currentEntropy.toFixed(3) }}
            </span>
          </div>
          <p class="chart-desc">Mesure du chaos narratif de l'audience (objections, surprises, incertitude du Juge).</p>
          
          <div class="svg-container">
            <svg viewBox="0 0 450 150" class="sparkline-svg">
              <defs>
                <linearGradient id="entropyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#A855F7" stop-opacity="0.4"/>
                  <stop offset="100%" stop-color="#A855F7" stop-opacity="0.0"/>
                </linearGradient>
              </defs>
              <!-- Grid Lines -->
              <line x1="40" y1="15" x2="435" y2="15" class="grid-line" stroke-dasharray="2,4" />
              <line x1="40" y1="70" x2="435" y2="70" class="grid-line" stroke-dasharray="2,4" />
              <line x1="40" y1="125" x2="435" y2="125" class="grid-line" />
              
              <!-- Y Axis Labels -->
              <text x="32" y="20" class="axis-label" text-anchor="end">{{ entropyMaxScale.toFixed(1) }}</text>
              <text x="32" y="75" class="axis-label" text-anchor="end">{{ (entropyMaxScale / 2).toFixed(1) }}</text>
              <text x="32" y="130" class="axis-label" text-anchor="end">0.0</text>

              <!-- Line & Area Paths -->
              <path v-if="entropyChartData.areaPath" :d="entropyChartData.areaPath" fill="url(#entropyGrad)" />
              <path v-if="entropyChartData.linePath" :d="entropyChartData.linePath" class="chart-line entropy-line" />
              
              <!-- Interactive Points -->
              <circle v-for="pt in entropyChartData.points" 
                      :key="pt.round" 
                      :cx="pt.x" 
                      :cy="pt.y" 
                      r="4" 
                      class="chart-dot entropy-dot"
                      :class="{ 'active-dot': String(selectedRound) === String(pt.round) }"
                      @click="selectedRound = pt.round"
                      style="cursor: pointer;" />
                      
              <!-- X Axis Labels -->
              <text v-for="pt in entropyChartData.points"
                    :key="'lbl-' + pt.round"
                    :x="pt.x"
                    y="144"
                    class="axis-label text-center clickable-label"
                    :class="{ 'active-label': String(selectedRound) === String(pt.round) }"
                    text-anchor="middle"
                    @click="selectedRound = pt.round"
                    style="cursor: pointer;">
                R{{ pt.round }}
              </text>
            </svg>
            <div v-if="!entropyChartData.points.length" class="chart-empty-placeholder">
              Attente des données du Round 1...
            </div>
          </div>
        </div>

        <!-- Card 2: Trajectoires de Tensions de l'Acteur -->
        <div class="card chart-card">
          <div class="card-title-with-value">
            <span class="card-title">Trajectoire des Tensions (Hystérésis)</span>
            <span class="value-badge actor-badge" v-if="selectedAgent">
              {{ selectedAgent.name }}
            </span>
          </div>
          <p class="chart-desc">Évolution des 3 curseurs cognitifs de l'acteur sélectionné au fil des rounds.</p>
          
          <div class="svg-container">
            <svg viewBox="0 0 450 150" class="sparkline-svg">
              <!-- Grid Lines -->
              <line x1="40" y1="15" x2="435" y2="15" class="grid-line" stroke-dasharray="2,4" />
              <line x1="40" y1="70" x2="435" y2="70" class="grid-line" stroke-dasharray="2,4" />
              <line x1="40" y1="125" x2="435" y2="125" class="grid-line" />
              
              <!-- Y Axis Labels -->
              <text x="32" y="20" class="axis-label" text-anchor="end">1.0</text>
              <text x="32" y="75" class="axis-label" text-anchor="end">0.5</text>
              <text x="32" y="130" class="axis-label" text-anchor="end">0.0</text>

              <!-- Line Paths -->
              <path v-if="tensionsChartData.path_p" :d="tensionsChartData.path_p" class="chart-line tension-p-line" />
              <path v-if="tensionsChartData.path_o" :d="tensionsChartData.path_o" class="chart-line tension-o-line" />
              <path v-if="tensionsChartData.path_r" :d="tensionsChartData.path_r" class="chart-line tension-r-line" />
              
              <!-- Interactive Points -->
              <!-- Theta P -->
              <circle v-for="pt in tensionsChartData.points_p" 
                      :key="'p-'+pt.round" 
                      :cx="pt.x" 
                      :cy="pt.y" 
                      r="3.5" 
                      class="chart-dot tension-p-dot"
                      :class="{ 'active-dot': String(selectedRound) === String(pt.round) }"
                      @click="selectedRound = pt.round"
                      style="cursor: pointer;" />
              <!-- Theta O -->
              <circle v-for="pt in tensionsChartData.points_o" 
                      :key="'o-'+pt.round" 
                      :cx="pt.x" 
                      :cy="pt.y" 
                      r="3.5" 
                      class="chart-dot tension-o-dot"
                      :class="{ 'active-dot': String(selectedRound) === String(pt.round) }"
                      @click="selectedRound = pt.round"
                      style="cursor: pointer;" />
              <!-- Theta R -->
              <circle v-for="pt in tensionsChartData.points_r" 
                      :key="'r-'+pt.round" 
                      :cx="pt.x" 
                      :cy="pt.y" 
                      r="3.5" 
                      class="chart-dot tension-r-dot"
                      :class="{ 'active-dot': String(selectedRound) === String(pt.round) }"
                      @click="selectedRound = pt.round"
                      style="cursor: pointer;" />

              <!-- X Axis Labels -->
              <text v-for="pt in tensionsChartData.points_p"
                    :key="'lbl-p-' + pt.round"
                    :x="pt.x"
                    y="144"
                    class="axis-label clickable-label"
                    :class="{ 'active-label': String(selectedRound) === String(pt.round) }"
                    text-anchor="middle"
                    @click="selectedRound = pt.round"
                    style="cursor: pointer;">
                R{{ pt.round }}
              </text>
            </svg>
            <div v-if="!tensionsChartData.points_p.length" class="chart-empty-placeholder">
              Attente des données du Round 1...
            </div>
          </div>
          
          <!-- Legend -->
          <div class="chart-legend" v-if="tensionsChartData.points_p.length">
            <span class="legend-item"><span class="legend-color p-color"></span>&theta;<sub>p</sub>: Procédure / Équité</span>
            <span class="legend-item"><span class="legend-color o-color"></span>&theta;<sub>o</sub>: Offensive / Négoc.</span>
            <span class="legend-item"><span class="legend-color r-color"></span>&theta;<sub>r</sub>: Prudence / Rapidité</span>
          </div>
        </div>
      </div>

      <!-- Selected Agent Main View -->
      <div v-if="selectedAgent" class="dashboard-details-row">
        <!-- Section Métacognition -->
        <div class="card meta-card">
          <div class="card-label" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <span>Continuité Subjective (Auto-Narration)</span>
            <span v-if="selectedAgent.personality" class="value-badge personality-badge" style="background: rgba(212, 175, 55, 0.15); color: #D4AF37; border: 1px solid rgba(212, 175, 55, 0.3); font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
              Profil : {{ selectedAgent.personality }}
            </span>
          </div>
          <p class="meta-narrative">" {{ selectedAgent.meta_narrative }} "</p>
          <div class="recent-reflection">
            <span class="reflection-label">Dernière introspection :</span>
            <span class="reflection-text">{{ selectedAgent.recent_reflection || 'Aucune réflexion récente.' }}</span>
          </div>
        </div>

        <!-- Section Tensions & Croyances -->
        <div class="tensions-grid">
          <div class="card tension-card">
            <div class="card-title">Équilibre des Tensions Cognitives</div>
            
            <div class="tension-bars-list">
              <div v-for="tension in tensionsToDisplay" :key="tension.key" class="tension-item">
                <div class="tension-labels">
                  <span class="pole-label">{{ tension.leftLabel }}</span>
                  <span class="pole-label">{{ tension.rightLabel }}</span>
                </div>
                <div class="tension-bar-container">
                  <div class="tension-bar-fill" :class="tension.leftClass" :style="{ width: (tension.value * 100) + '%' }"></div>
                  <div class="tension-bar-fill" :class="tension.rightClass" :style="{ width: ((1 - tension.value) * 100) + '%' }"></div>
                  <div class="tension-marker" :style="{ left: (tension.value * 100) + '%' }"></div>
                </div>
                <div class="tension-value mono">
                  Ratio : {{ tension.value.toFixed(2) }}
                </div>
              </div>
            </div>
          </div>

          <!-- Section Croyances (Superpositions) -->
          <div class="card beliefs-card">
            <div class="card-title">{{ isLegal ? (isCivil ? 'Probabilité Subjective de Responsabilité' : 'Probabilité Subjective de Culpabilité') : 'Superpositions des Croyances' }}</div>
            
            <div class="beliefs-list">
              <template v-for="(distribution, issue) in selectedAgent.beliefs" :key="issue">
                <div v-if="!(isLegal && issue === 'general_trust')" class="belief-issue-item">
                  <div class="issue-name">{{ formatIssueName(issue) }}</div>
                  
                  <div class="probabilities-container">
                    <div v-for="(prob, state) in distribution" :key="state" class="prob-row">
                      <div class="prob-meta">
                        <span class="prob-state-name">{{ formatStateName(state) }}</span>
                        <span class="prob-val mono">{{ (prob * 100).toFixed(0) }}%</span>
                      </div>
                      <div class="prob-progress-bg">
                        <div class="prob-progress-fill" :style="{ width: (prob * 100) + '%' }"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getSimulationCognitiveStates } from '../api/simulation'

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  },
  active: {
    type: Boolean,
    default: true
  },
  isLegal: {
    type: Boolean,
    default: false
  },
  cognitiveHistory: {
    type: Array,
    default: () => []
  }
})

// States
const states = ref([])
const selectedAgentId = ref('')
const selectedRound = ref('live')
let pollTimer = null

const isCivil = computed(() => {
  if (!props.isLegal) return false
  return states.value.some(s => s.name && (s.name.toLowerCase().includes("demandeur") || s.name.toLowerCase().includes("défendeur")))
})

const availableRounds = computed(() => {
  if (!props.cognitiveHistory || props.cognitiveHistory.length === 0) return []
  return props.cognitiveHistory.map(h => h.round)
})

// Watch props.cognitiveHistory to populate agents list when states is empty
watch(() => props.cognitiveHistory, (newHistory) => {
  if (newHistory && newHistory.length > 0 && states.value.length === 0) {
    const lastEntry = newHistory[newHistory.length - 1]
    if (lastEntry && lastEntry.agents) {
      const tempStates = []
      Object.entries(lastEntry.agents).forEach(([id, agent]) => {
        tempStates.push({
          agent_id: id,
          name: agent.name,
          tensions: {
            procedure_vs_equite: agent.procedure_vs_equite,
            offensive_vs_negociation: agent.offensive_vs_negociation,
            prudence_vs_rapidite: agent.prudence_vs_rapidite
          },
          beliefs: {
            culpabilite_accuse: {
              coupable: agent.belief_coupable,
              innocent: 1 - agent.belief_coupable
            }
          },
          meta_narrative: "Analyse en cours...",
          recent_reflection: ""
        })
      })
      states.value = tempStates
      if (!selectedAgentId.value && tempStates.length > 0) {
        selectedAgentId.value = tempStates[0].agent_id
      }
    }
  }
}, { immediate: true, deep: true })

// Computed
const selectedAgent = computed(() => {
  if (!selectedAgentId.value) return null
  
  if (selectedRound.value === 'live') {
    return states.value.find(s => String(s.agent_id) === String(selectedAgentId.value)) || null
  } else {
    // Look up in history
    const historyEntry = props.cognitiveHistory.find(h => String(h.round) === String(selectedRound.value))
    if (!historyEntry) return null
    
    const agentHist = historyEntry.agents?.[selectedAgentId.value] || historyEntry.agents?.[String(selectedAgentId.value)]
    if (!agentHist) return null
    
    // Find the live agent name as a fallback
    const liveAgent = states.value.find(s => String(s.agent_id) === String(selectedAgentId.value))
    const name = agentHist.name || (liveAgent ? liveAgent.name : `Acteur ${selectedAgentId.value}`)
    
    // Fallback texts for courtroom simulation (Round 0 baseline)
    let defaultMeta = "Aucune continuité subjective enregistrée pour ce round."
    let defaultRefl = "Aucune réflexion enregistrée pour ce round."
    
    if (String(selectedRound.value) === '0' || !agentHist.meta_narrative) {
      if (String(selectedAgentId.value) === '0') {
        defaultMeta = "Je préside cette audience de manière impartiale. Mon devoir est d'écouter les deux parties avant de me forger une intime conviction."
        defaultRefl = "Les débats commencent à peine, l'impartialité est requise."
      } else if (String(selectedAgentId.value) === '1') {
        if (isCivil.value) {
          defaultMeta = "Ma mission est de démontrer la responsabilité civile du défendeur et d'obtenir réparation pour le préjudice subi par mon client. Le vice caché ou le manquement contractuel est caractérisé."
          defaultRefl = "Le dossier technique et les preuves de défaillance démontrent clairement le bien-fondé de notre demande."
        } else {
          defaultMeta = "Ma mission est de défendre l'ordre public et de faire appliquer strictement la loi. La culpabilité du prévenu ne fait aucun doute."
          defaultRefl = "Le dossier présente des charges sérieuses qui justifient une répression ferme."
        }
      } else if (String(selectedAgentId.value) === '2') {
        if (isCivil.value) {
          defaultMeta = "Je me bats pour libérer mon client de toute responsabilité. La diligence raisonnable a été exercée et les prétentions adverses sont disproportionnées."
          defaultRefl = "L'acquéreur était pleinement conscient des risques, il n'y a aucun vice caché au sens de la loi."
        } else {
          defaultMeta = "Je me bats pour protéger les droits fondamentaux de mon client. L'équité naturelle doit prévaloir sur le formalisme aveugle."
          defaultRefl = "Les pièces fournies par l'accusation sont insuffisantes et truffées d'incertitudes."
        }
      }
    }
    
    return {
      agent_id: selectedAgentId.value,
      name: name,
      personality: agentHist.personality || (liveAgent ? liveAgent.personality : ''),
      tensions: {
        procedure_vs_equite: agentHist.procedure_vs_equite ?? 0.5,
        offensive_vs_negociation: agentHist.offensive_vs_negociation ?? 0.5,
        prudence_vs_rapidite: agentHist.prudence_vs_rapidite ?? 0.5,
        exploration_vs_security: agentHist.exploration_vs_security ?? 0.5,
        cooperation_vs_domination: agentHist.cooperation_vs_domination ?? 0.5,
        truth_vs_social_survival: agentHist.truth_vs_social_survival ?? 0.5
      },
      beliefs: {
        culpabilite_accuse: {
          coupable: agentHist.belief_coupable ?? 0.5,
          innocent: 1 - (agentHist.belief_coupable ?? 0.5)
        }
      },
      meta_narrative: agentHist.meta_narrative || defaultMeta,
      recent_reflection: agentHist.recent_reflection || defaultRefl
    }
  }
})

const tensionsToDisplay = computed(() => {
  if (!selectedAgent.value) return []
  
  if (props.isLegal) {
    return [
      {
        key: 'procedure_vs_equite',
        leftLabel: 'PROCÉDURE',
        rightLabel: 'ÉQUITÉ',
        value: selectedAgent.value.tensions?.procedure_vs_equite ?? 0.5,
        leftClass: 'exploration',
        rightClass: 'security'
      },
      {
        key: 'offensive_vs_negociation',
        leftLabel: 'OFFENSIVE',
        rightLabel: 'NÉGOCIATION',
        value: selectedAgent.value.tensions?.offensive_vs_negociation ?? 0.5,
        leftClass: 'cooperation',
        rightClass: 'domination'
      },
      {
        key: 'prudence_vs_rapidite',
        leftLabel: 'PRUDENCE',
        rightLabel: 'RAPIDITÉ',
        value: selectedAgent.value.tensions?.prudence_vs_rapidite ?? 0.5,
        leftClass: 'truth',
        rightClass: 'survival'
      }
    ]
  } else {
    return [
      {
        key: 'exploration_vs_security',
        leftLabel: 'EXPLORATION',
        rightLabel: 'SECURITY',
        value: selectedAgent.value.tensions?.exploration_vs_security ?? 0.5,
        leftClass: 'exploration',
        rightClass: 'security'
      },
      {
        key: 'cooperation_vs_domination',
        leftLabel: 'COOPERATION',
        rightLabel: 'DOMINATION',
        value: selectedAgent.value.tensions?.cooperation_vs_domination ?? 0.5,
        leftClass: 'cooperation',
        rightClass: 'domination'
      },
      {
        key: 'truth_vs_social_survival',
        leftLabel: 'TRUTH',
        rightLabel: 'SOCIAL SURVIVAL',
        value: selectedAgent.value.tensions?.truth_vs_social_survival ?? 0.5,
        leftClass: 'truth',
        rightClass: 'survival'
      }
    ]
  }
})

// Legal Charts computations
const currentEntropy = computed(() => {
  if (!props.cognitiveHistory || props.cognitiveHistory.length === 0) return null
  const lastEntry = props.cognitiveHistory[props.cognitiveHistory.length - 1]
  return lastEntry.entropy ?? 0
})

const entropyMaxScale = computed(() => {
  if (!props.cognitiveHistory || props.cognitiveHistory.length === 0) return 1.5
  const maxVal = Math.max(...props.cognitiveHistory.map(h => h.entropy ?? 0))
  return Math.max(1.5, maxVal * 1.1)
})

const entropyChartData = computed(() => {
  const history = props.cognitiveHistory || []
  if (history.length === 0) {
    return { linePath: '', areaPath: '', points: [] }
  }
  
  const width = 450
  const height = 150
  const margin = { left: 40, right: 15, top: 15, bottom: 25 }
  const chartWidth = width - margin.left - margin.right
  const chartHeight = height - margin.top - margin.bottom
  
  const maxVal = entropyMaxScale.value
  
  const points = history.map((entry, idx) => {
    const x = margin.left + (history.length > 1 ? (idx / (history.length - 1)) * chartWidth : chartWidth / 2)
    const val = entry.entropy ?? 0
    const y = height - margin.bottom - (val / maxVal) * chartHeight
    return {
      x,
      y,
      round: entry.round,
      value: val.toFixed(3)
    }
  })
  
  const linePath = points.length > 0 
    ? 'M ' + points.map(p => `${p.x} ${p.y}`).join(' L ')
    : ''
    
  const areaPath = points.length > 0
    ? `${linePath} L ${points[points.length - 1].x} ${height - margin.bottom} L ${points[0].x} ${height - margin.bottom} Z`
    : ''
    
  return { linePath, areaPath, points }
})

const tensionsChartData = computed(() => {
  const history = props.cognitiveHistory || []
  const agentId = selectedAgentId.value
  
  if (history.length === 0 || !agentId) {
    return { path_p: '', path_o: '', path_r: '', points_p: [], points_o: [], points_r: [] }
  }
  
  const width = 450
  const height = 150
  const margin = { left: 40, right: 15, top: 15, bottom: 25 }
  const chartWidth = width - margin.left - margin.right
  const chartHeight = height - margin.top - margin.bottom
  
  const points_p = []
  const points_o = []
  const points_r = []
  
  history.forEach((entry, idx) => {
    const x = margin.left + (history.length > 1 ? (idx / (history.length - 1)) * chartWidth : chartWidth / 2)
    const agentData = entry.agents?.[agentId] || entry.agents?.[String(agentId)]
    if (agentData) {
      const val_p = agentData.procedure_vs_equite ?? 0.5
      const val_o = agentData.offensive_vs_negociation ?? 0.5
      const val_r = agentData.prudence_vs_rapidite ?? 0.5
      
      points_p.push({ x, y: height - margin.bottom - val_p * chartHeight, round: entry.round, value: val_p })
      points_o.push({ x, y: height - margin.bottom - val_o * chartHeight, round: entry.round, value: val_o })
      points_r.push({ x, y: height - margin.bottom - val_r * chartHeight, round: entry.round, value: val_r })
    }
  })
  
  const path_p = points_p.length > 0 ? 'M ' + points_p.map(p => `${p.x} ${p.y}`).join(' L ') : ''
  const path_o = points_o.length > 0 ? 'M ' + points_o.map(p => `${p.x} ${p.y}`).join(' L ') : ''
  const path_r = points_r.length > 0 ? 'M ' + points_r.map(p => `${p.x} ${p.y}`).join(' L ') : ''
  
  return {
    path_p,
    path_o,
    path_r,
    points_p,
    points_o,
    points_r
  }
})

// Methods
const formatIssueName = (name) => {
  if (name === 'culpabilite_accuse') {
    return props.isLegal 
      ? (isCivil.value ? 'Responsabilité du défendeur' : 'Culpabilité de l\'accusé') 
      : 'Orientation de l\'opinion publique'
  }
  return name.replace(/_/g, ' ').toUpperCase()
}

const formatStateName = (state) => {
  if (state === 'coupable') {
    return props.isLegal 
      ? (isCivil.value ? 'Responsable' : 'Coupable') 
      : 'Défavorable / Contre'
  }
  if (state === 'innocent') {
    return props.isLegal 
      ? (isCivil.value ? 'Non responsable' : 'Innocent') 
      : 'Favorable / Pour'
  }
  return state
}

const fetchStates = async () => {
  if (!props.simulationId) return
  try {
    const res = await getSimulationCognitiveStates(props.simulationId)
    if (res.success && res.data) {
      states.value = res.data
      
      // Auto-sélectionner le premier agent si aucun n'est sélectionné
      if (states.value.length > 0 && !selectedAgentId.value) {
        selectedAgentId.value = String(states.value[0].agent_id)
      }
    }
  } catch (err) {
    console.warn("Erreur de récupération des états cognitifs:", err)
  }
}

// Polling
const startPolling = () => {
  stopPolling()
  fetchStates()
  pollTimer = setInterval(fetchStates, 4000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(() => props.active, (newVal) => {
  if (newVal) {
    startPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.cognitive-visualizer-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0B0D10;
  color: #E2E8F0;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid #1E293B;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
}

.legal-mode {
  background: #090B0E;
  border-color: #2D3748;
}

.visualizer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #121620;
  border-bottom: 1px solid #1E293B;
}

.legal-mode .visualizer-header {
  background: #11141D;
  border-bottom-color: #2D3748;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #A855F7;
  box-shadow: 0 0 10px #A855F7;
  animation: pulse-animation 2s infinite;
}

.pulse-dot.legal-pulse {
  background: #00F2FE;
  box-shadow: 0 0 10px #00F2FE;
}

@keyframes pulse-animation {
  0% { transform: scale(0.9); opacity: 0.6; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.6; }
}

.panel-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #F8FAFC;
}

.agent-select {
  background: #0F172A;
  color: #F1F5F9;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  outline: none;
  cursor: pointer;
  transition: all 0.3s;
}

.agent-select:hover {
  border-color: #00F2FE;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  color: #64748B;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 16px;
}

.cognitive-dashboard {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  gap: 20px;
  overflow-y: auto;
}

.card {
  background: #121620;
  border: 1px solid #1E293B;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s ease;
}

.legal-mode .card {
  background: #11141D;
  border-color: #2D3748;
}

/* --- Charts CSS --- */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 992px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  position: relative;
  min-height: 230px;
  display: flex;
  flex-direction: column;
}

.card-title-with-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #F8FAFC;
  letter-spacing: 0.5px;
}

.chart-desc {
  font-size: 11px;
  color: #64748B;
  margin: 0 0 14px 0;
  line-height: 1.4;
}

.value-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}

.entropy-badge {
  background: rgba(168, 85, 247, 0.15);
  color: #C084FC;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.actor-badge {
  background: rgba(0, 242, 254, 0.1);
  color: #00F2FE;
  border: 1px solid rgba(0, 242, 254, 0.2);
}

.svg-container {
  position: relative;
  flex: 1;
  min-height: 120px;
}

.sparkline-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.grid-line {
  stroke: #1E293B;
  stroke-width: 1;
}

.legal-mode .grid-line {
  stroke: #2D3748;
}

.axis-label {
  fill: #475569;
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
}

.chart-line {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.entropy-line {
  stroke: #A855F7;
  filter: drop-shadow(0 0 6px rgba(168, 85, 247, 0.5));
}

.tension-p-line {
  stroke: #00F2FE;
  filter: drop-shadow(0 0 4px rgba(0, 242, 254, 0.4));
}

.tension-o-line {
  stroke: #FF0844;
  filter: drop-shadow(0 0 4px rgba(255, 8, 68, 0.4));
}

.tension-r-line {
  stroke: #00FF87;
  filter: drop-shadow(0 0 4px rgba(0, 255, 135, 0.4));
}

.chart-dot {
  stroke: #121620;
  stroke-width: 1.5;
  r: 4;
  transition: r 0.2s, stroke-width 0.2s;
}

.chart-dot:hover {
  r: 6;
  stroke: #FFFFFF;
  stroke-width: 2;
}

.chart-dot.active-dot {
  r: 7;
  stroke: #FFFFFF;
  stroke-width: 2.5;
}

.clickable-label {
  transition: fill 0.2s, font-weight 0.2s;
}

.clickable-label:hover {
  fill: #FFFFFF;
  font-weight: bold;
}

.active-label {
  fill: #00F2FE;
  font-weight: bold;
}

.history-banner-badge {
  font-size: 10px;
  font-weight: bold;
  background: rgba(234, 179, 8, 0.15);
  color: #EAB308;
  border: 1px solid rgba(234, 179, 8, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 10px;
  text-transform: uppercase;
  display: inline-block;
  vertical-align: middle;
}

.pulse-dot.history-pulse {
  background: #EAB308;
  box-shadow: 0 0 6px #EAB308;
  animation: none;
}

.entropy-dot {
  fill: #A855F7;
}

.tension-p-dot { fill: #00F2FE; }
.tension-o-dot { fill: #FF0844; }
.tension-r-dot { fill: #00FF87; }

.chart-empty-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #475569;
  font-size: 12px;
  pointer-events: none;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 10px;
  font-size: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #94A3B8;
}

.legend-color {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.p-color { background: #00F2FE; box-shadow: 0 0 4px #00F2FE; }
.o-color { background: #FF0844; box-shadow: 0 0 4px #FF0844; }
.r-color { background: #00FF87; box-shadow: 0 0 4px #00FF87; }

/* --- Details CSS --- */
.dashboard-details-row {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.meta-card {
  border-left: 4px solid #A855F7;
  background: linear-gradient(135deg, #121620 0%, #161B29 100%);
}

.legal-mode .meta-card {
  border-left-color: #00F2FE;
  background: linear-gradient(135deg, #11141D 0%, #161A26 100%);
}

.card-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: #A855F7;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.legal-mode .card-label {
  color: #00F2FE;
}

.meta-narrative {
  font-size: 14px;
  font-style: italic;
  line-height: 1.6;
  color: #F1F5F9;
  margin: 0 0 12px 0;
}

.recent-reflection {
  display: flex;
  font-size: 12px;
  gap: 6px;
  border-top: 1px solid #1E293B;
  padding-top: 10px;
}

.legal-mode .recent-reflection {
  border-top-color: #2D3748;
}

.reflection-label {
  font-weight: 600;
  color: #94A3B8;
  white-space: nowrap;
}

.reflection-text {
  color: #CBD5E1;
}

.tensions-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 768px) {
  .tensions-grid {
    grid-template-columns: 1fr;
  }
}

.tension-bars-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 10px;
}

.tension-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tension-labels {
  display: flex;
  justify-content: space-between;
}

.pole-label {
  font-size: 10px;
  font-weight: 700;
  color: #64748B;
  letter-spacing: 0.5px;
}

.tension-bar-container {
  height: 12px;
  border-radius: 6px;
  background: #1E293B;
  position: relative;
  overflow: hidden;
}

.legal-mode .tension-bar-container {
  background: #1A1F2C;
}

.tension-bar-fill {
  height: 100%;
  position: absolute;
  top: 0;
}

.tension-bar-fill.exploration {
  left: 0;
  background: linear-gradient(90deg, #EC4899 0%, #A855F7 100%);
}

.legal-mode .tension-bar-fill.exploration {
  background: linear-gradient(90deg, #00C6FF 0%, #00F2FE 100%);
}

.tension-bar-fill.security {
  right: 0;
  background: #3B82F6;
  opacity: 0.2;
}

.tension-bar-fill.cooperation {
  left: 0;
  background: linear-gradient(90deg, #10B981 0%, #3B82F6 100%);
}

.legal-mode .tension-bar-fill.cooperation {
  background: linear-gradient(90deg, #FF0844 0%, #FFB199 100%);
}

.tension-bar-fill.domination {
  right: 0;
  background: #EF4444;
  opacity: 0.2;
}

.tension-bar-fill.truth {
  left: 0;
  background: linear-gradient(90deg, #EAB308 0%, #EC4899 100%);
}

.legal-mode .tension-bar-fill.truth {
  background: linear-gradient(90deg, #00FF87 0%, #60EFA0 100%);
}

.tension-bar-fill.survival {
  right: 0;
  background: #64748B;
  opacity: 0.2;
}

.tension-marker {
  position: absolute;
  top: 0;
  width: 4px;
  height: 100%;
  background: #FFFFFF;
  box-shadow: 0 0 8px #FFFFFF;
  transform: translateX(-50%);
  z-index: 10;
}

.tension-value {
  font-size: 11px;
  color: #94A3B8;
  align-self: flex-end;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.beliefs-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 10px;
}

.belief-issue-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.issue-name {
  font-size: 11px;
  font-weight: 700;
  color: #F1F5F9;
  letter-spacing: 0.5px;
}

.probabilities-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prob-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.prob-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.prob-state-name {
  color: #94A3B8;
}

.prob-val {
  color: #A855F7;
  font-weight: 600;
}

.legal-mode .prob-val {
  color: #00F2FE;
}

.prob-progress-bg {
  height: 6px;
  border-radius: 3px;
  background: #1E293B;
  overflow: hidden;
}

.legal-mode .prob-progress-bg {
  background: #1A1F2C;
}

.prob-progress-fill {
  height: 100%;
  background: #A855F7;
  border-radius: 3px;
  box-shadow: 0 0 6px rgba(168, 85, 247, 0.5);
}

.legal-mode .prob-progress-fill {
  background: #00F2FE;
  box-shadow: 0 0 6px rgba(0, 242, 254, 0.5);
}
</style>
