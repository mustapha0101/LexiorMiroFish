<template>
  <div class="simulation-panel">
    <!-- Top Control Bar -->
    <div class="control-bar">
      <div class="status-group">
        <template v-if="props.projectData?.simulation_mode === 'legal' && props.runMode === 'courtroom'">
          <!-- Legal Courtroom Trial Status Card -->
          <div class="platform-status legal-courtroom active">
            <div class="platform-header">
              <svg class="platform-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <span class="platform-name">{{ isCivil ? 'Procès Civil (Monte-Carlo)' : 'Procès Criminel (Monte-Carlo)' }}</span>
            </div>
            <div class="platform-stats">
              <span class="stat">
                <span class="stat-label">PROCÈS SIMULÉS</span>
                <span class="stat-value mono">{{ runStatus.current_round || 0 }}<span class="stat-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
              </span>
              <span class="stat">
                <span class="stat-label">{{ acquittalRateLabel }}</span>
                <span class="stat-value mono">{{ acquittalRate !== null ? `${acquittalRate}%` : '--%' }}</span>
              </span>
              <span class="stat">
                <span class="stat-label">DERNIER VERDICT</span>
                <span class="stat-value mono text-truncate" style="max-width: 250px;" :title="lastVerdict || ''">{{ lastVerdict || 'Débats en cours...' }}</span>
              </span>
            </div>
          </div>
        </template>
        <template v-else>
          <!-- Twitter 平台进度 -->
          <div class="platform-status twitter" :class="{ active: runStatus.twitter_running, completed: runStatus.twitter_completed }">
            <div class="platform-header">
              <svg class="platform-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              <span class="platform-name">{{ props.runMode === 'oasis' ? 'Twitter' : 'Info Plaza' }}</span>
              <span v-if="runStatus.twitter_completed" class="status-badge">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </span>
            </div>
            <div class="platform-stats">
              <span class="stat">
                <span class="stat-label">ROUND</span>
                <span class="stat-value mono">{{ runStatus.twitter_current_round || 0 }}<span class="stat-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
              </span>
              <span class="stat">
                <span class="stat-label">TIME</span>
                <span class="stat-value mono">{{ twitterElapsedTime }}</span>
              </span>
              <span class="stat">
                <span class="stat-label">ACTS</span>
                <span class="stat-value mono">{{ runStatus.twitter_actions_count || 0 }}</span>
              </span>
            </div>
            <!-- 可用动作提示 -->
            <div class="actions-tooltip">
              <div class="tooltip-title">Actions Disponibles</div>
              <div class="tooltip-actions">
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Déposer Avis' : 'POST' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Soutenir la Thèse' : 'LIKE' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Partager' : 'REPOST' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Citer' : 'QUOTE' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Suivre' : 'FOLLOW' }}</span>
                <span class="tooltip-action">IDLE</span>
              </div>
            </div>
          </div>
          
          <!-- Reddit 平台进度 -->
          <div class="platform-status reddit" :class="{ active: runStatus.reddit_running, completed: runStatus.reddit_completed }">
            <div class="platform-header">
              <svg class="platform-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
              </svg>
              <span class="platform-name">{{ props.runMode === 'oasis' ? 'Reddit' : 'Topic Community' }}</span>
              <span v-if="runStatus.reddit_completed" class="status-badge">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </span>
            </div>
            <div class="platform-stats">
              <span class="stat">
                <span class="stat-label">ROUND</span>
                <span class="stat-value mono">{{ runStatus.reddit_current_round || 0 }}<span class="stat-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
              </span>
              <span class="stat">
                <span class="stat-label">TIME</span>
                <span class="stat-value mono">{{ redditElapsedTime }}</span>
              </span>
              <span class="stat">
                <span class="stat-label">ACTS</span>
                <span class="stat-value mono">{{ runStatus.reddit_actions_count || 0 }}</span>
              </span>
            </div>
            <!-- 可用动作提示 -->
            <div class="actions-tooltip">
              <div class="tooltip-title">Actions Disponibles</div>
              <div class="tooltip-actions">
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Déposer Avis' : 'POST' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Déposer Argument' : 'COMMENT' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Soutenir la Thèse' : 'LIKE' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Contredire' : 'DISLIKE' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Rechercher' : 'SEARCH' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Tendances' : 'TREND' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Suivre' : 'FOLLOW' }}</span>
                <span class="tooltip-action">{{ props.runMode === 'oasis' ? 'Muet' : 'MUTE' }}</span>
                <span class="tooltip-action">IDLE</span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div class="action-controls" style="display: flex; gap: 12px; justify-content: flex-end;">
        <button 
          v-if="phase === 1"
          class="action-btn secondary stop-btn"
          :disabled="isStopping"
          @click="handleStopSimulation"
          style="background-color: #DC3545; color: white; border-color: #DC3545;"
        >
          <span v-if="isStopping" class="loading-spinner-small"></span>
          {{ isStopping ? 'Arrêt en cours...' : 'Arrêter et passer au rapport' }}
        </button>
        
        <button 
          v-if="phase === 2"
          class="action-btn secondary export-pdf-btn"
          @click="exportSimulationToPDF"
          style="background-color: #0F1E36; color: #C5A880; border-color: #C5A880; display: flex; align-items: center; gap: 6px;"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span>Exporter la simulation (PDF)</span>
        </button>

        <button 
          class="action-btn primary"
          :disabled="phase !== 2 || isGeneratingReport"
          @click="handleNextStep"
        >
          <span v-if="isGeneratingReport" class="loading-spinner-small"></span>
          {{ props.projectData?.simulation_mode === 'legal' ? (isGeneratingReport ? 'Génération...' : 'Générer le rapport du Greffier') : (isGeneratingReport ? $t('step3.generatingReportBtn') : $t('step3.startGenerateReportBtn')) }}
          <span v-if="!isGeneratingReport" class="arrow-icon">→</span>
        </button>
      </div>
    </div>

    <!-- Tab Selector -->
    <div class="tab-selector-bar">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'timeline' }"
        @click="activeTab = 'timeline'"
      >
        Event Timeline
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'cognitive' }"
        @click="activeTab = 'cognitive'"
      >
        Cognitive States (PIE)
      </button>
      <button 
        v-if="props.runMode === 'courtroom'"
        class="tab-btn" 
        :class="{ active: activeTab === 'negotiation' }"
        @click="activeTab = 'negotiation'"
      >
        {{ $t('history.liveChatTitle') }}
      </button>
    </div>

    <!-- Main Content: Dual Timeline or Cognitive States -->
    <div 
      class="main-content-area" 
      :class="{ 'chat-mode': activeTab === 'negotiation' || activeTab === 'cognitive' }" 
      ref="scrollContainer"
    >
      <template v-if="activeTab === 'timeline'">
        <!-- Timeline Header -->
        <div class="timeline-header" v-if="allActions.length > 0">
          <div class="timeline-stats">
            <span class="total-count">TOTAL EVENTS: <span class="mono">{{ allActions.length }}</span></span>
            <span class="platform-breakdown">
              <span class="breakdown-item twitter">
                <svg class="mini-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                <span class="mono">{{ twitterActionsCount }}</span>
              </span>
              <span class="breakdown-divider">/</span>
              <span class="breakdown-item reddit">
                <svg class="mini-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                <span class="mono">{{ redditActionsCount }}</span>
              </span>
            </span>
          </div>
        </div>
        
        <!-- Console d'injection de Stimuli (uniquement en cours de simulation active et pour runMode oasis/courtroom) -->
        <div v-if="phase === 1 && props.projectData?.simulation_mode === 'legal'" class="stimulus-injection-card">
          <div class="card-header-premium">
            <span class="card-title-premium">⚡ CONSOLE D'INJECTION DE STIMULI EN DIRECT</span>
            <span class="card-subtitle-premium">{{ props.runMode === 'oasis' ? 'Injectez des communiqués de presse, des arguments ou des réactions pour influencer l\'opinion publique en temps réel.' : 'Injectez des événements, témoignages surprises ou pièces à conviction pour influencer la simulation en temps réel.' }}</span>
          </div>
          <div class="injection-form">
            <input 
              v-model="stimulusText" 
              type="text" 
              :placeholder="props.runMode === 'oasis' ? 'Ex: Communiqué de presse de la direction démentant toute fuite de données...' : 'Ex: Témoignage surprise : l\'accusé a été vu sur les lieux avec une arme...'" 
              class="stimulus-input" 
              @keyup.enter="handleInjectStimulus"
              :disabled="isInjecting"
            />
            <button 
              class="inject-btn" 
              @click="handleInjectStimulus" 
              :disabled="isInjecting || !stimulusText.trim()"
            >
              <span v-if="isInjecting" class="loading-spinner-small"></span>
              {{ isInjecting ? 'Injection...' : 'Injecter' }}
            </button>
          </div>
          <div v-if="injectionSuccess" class="injection-feedback success">
            ✓ Stimulus injecté avec succès ! Influence en cours.
          </div>
          <div v-if="injectionError" class="injection-feedback error">
            ✗ Erreur : {{ injectionError }}
          </div>
        </div>

        <!-- Timeline Feed -->
        <div class="timeline-feed">
          <div class="timeline-axis"></div>
          
          <TransitionGroup name="timeline-item">
            <div 
              v-for="action in chronologicalActions" 
              :key="action._uniqueId || action.id || `${action.timestamp}-${action.agent_id}`" 
              class="timeline-item"
              :class="action.platform"
            >
              <div class="timeline-marker">
                <div class="marker-dot"></div>
              </div>
              
              <div class="timeline-card">
                <div class="card-header">
                  <div class="agent-info">
                    <div class="avatar-placeholder">{{ (action.agent_name || 'A')[0] }}</div>
                    <span class="agent-name">{{ action.agent_name }}</span>
                    <!-- Cognitive State Hover Button -->
                    <div class="cognitive-trigger-wrapper" @mouseenter="hoverAgent(action)" @mouseleave="clearHover">
                      <span class="brain-icon-trigger">🧠</span>
                      <!-- Elegant glassmorphism hover card -->
                      <div v-if="isActionAgentHovered(action)" class="cognitive-hover-card">
                        <div class="hover-card-header">
                          <span class="hover-card-title">Narrative State: {{ hoveredAgentState.name }}</span>
                        </div>
                        <div class="hover-card-body">
                          <p class="hover-narrative">" {{ hoveredAgentState.meta_narrative }} "</p>
                          
                          <div class="hover-section-title">Cognitive Tensions</div>
                          <div class="hover-tensions-list">
                            <div v-for="tension in getTensionsForAgent(hoveredAgentState)" :key="tension.left" class="hover-tension-item">
                              <div class="hover-tension-labels">
                                <span class="pole-label">{{ tension.left }}</span>
                                <span class="pole-label">{{ tension.right }}</span>
                              </div>
                              <div class="hover-tension-bar-container">
                                <div class="hover-tension-bar-fill" :style="{ width: (tension.value * 100) + '%' }"></div>
                                <div class="hover-tension-marker" :style="{ left: (tension.value * 100) + '%' }"></div>
                              </div>
                              <div class="hover-tension-value mono">
                                Ratio : {{ tension.value.toFixed(2) }}
                              </div>
                            </div>
                          </div>

                          <div v-if="Object.keys(hoveredAgentState.beliefs || {}).length > 0" class="hover-beliefs-section">
                            <div class="hover-section-title">Beliefs</div>
                            <div v-for="(dist, issue) in hoveredAgentState.beliefs" :key="issue" class="hover-belief-item">
                              <div class="hover-belief-issue">{{ issue.replace(/_/g, ' ').toUpperCase() }}</div>
                              <div class="hover-prob-container">
                                <div v-for="(prob, state) in dist" :key="state" class="hover-prob-row">
                                  <span class="hover-prob-state-name">{{ state }}</span>
                                  <span class="hover-prob-val mono">{{ (prob * 100).toFixed(0) }}%</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Audio TTS Button -->
                    <button 
                      v-if="action.action_args?.content || action.result"
                      class="tts-play-btn" 
                      @click="playBubbleTTS(action)" 
                      :title="currentlyPlayingId === (action._uniqueId || action.id || action.timestamp) ? 'Arrêter' : (currentlyLoadingId === (action._uniqueId || action.id || action.timestamp) ? 'Génération...' : 'Lire à voix haute')"
                      :class="{ playing: currentlyPlayingId === (action._uniqueId || action.id || action.timestamp), loading: currentlyLoadingId === (action._uniqueId || action.id || action.timestamp) }"
                    >
                      <span v-if="currentlyLoadingId === (action._uniqueId || action.id || action.timestamp)" class="tts-spinner"></span>
                      <span v-else-if="currentlyPlayingId === (action._uniqueId || action.id || action.timestamp)">⏸️</span>
                      <span v-else>🔊</span>
                    </button>
                  </div>
                  
                  <div class="header-meta">
                    <div class="platform-indicator">
                      <svg v-if="action.platform === 'twitter'" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                      <svg v-else viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                    </div>
                    <div class="action-badge" :class="getActionTypeClass(action.action_type)">
                      {{ getActionTypeLabel(action.action_type) }}
                    </div>
                  </div>
                </div>
                
                <div class="card-body">
                  <!-- Legal courtroom action blocks -->
                  <template v-if="props.projectData?.simulation_mode === 'legal'">
                    <div v-if="action.action_type === 'SPEECH_PROSECUTOR'" class="courtroom-speech prosecutor">
                      <div class="courtroom-speech-header">
                        <span class="actor-label">⚖️ {{ isCivil ? 'Avocat du Demandeur' : 'Ministère Public' }} :</span>
                      </div>
                      <div class="speech-text-content" v-html="renderMarkdown(action.action_args?.content || action.result)"></div>
                    </div>
                    <div v-else-if="action.action_type === 'SPEECH_DEFENSE'" class="courtroom-speech defense">
                      <div class="courtroom-speech-header">
                        <span class="actor-label">🛡️ Avocat de la Défense :</span>
                      </div>
                      <div class="speech-text-content" v-html="renderMarkdown(action.action_args?.content || action.result)"></div>
                    </div>
                    <div v-else-if="action.action_type === 'SPEECH_ACCUSED'" class="courtroom-speech accused">
                      <div class="courtroom-speech-header">
                        <span class="actor-label">👤 {{ isCivil ? 'Défendeur' : 'Prévenu (Accusé)' }} :</span>
                      </div>
                      <div class="speech-text-content" v-html="renderMarkdown(action.action_args?.content || action.result)"></div>
                    </div>
                    <div v-else-if="action.action_type === 'VERDICT' || action.action_type === 'DECISION'" class="courtroom-speech verdict">
                      <div class="courtroom-speech-header">
                        <span class="actor-label">🏛️ Verdict du Juge :</span>
                      </div>
                      <div class="speech-text-content" v-html="renderMarkdown(action.action_args?.content || action.result)"></div>
                    </div>
                    <div v-else-if="action.action_type === 'CLERK_ANALYSIS'" class="courtroom-speech clerk">
                      <div class="courtroom-speech-header">
                        <span class="actor-label">📝 Greffier (Analyse) :</span>
                      </div>
                      <div class="speech-text-content" v-html="renderMarkdown(action.action_args?.content || action.result)"></div>
                    </div>
                    <div v-else-if="action.action_type === 'STIMULUS'" class="courtroom-speech stimulus">
                      <div class="courtroom-speech-header">
                        <span class="actor-label">⚡ STIMULUS INJECTÉ :</span>
                      </div>
                      <div class="speech-text-content" v-html="renderMarkdown(action.action_args?.content || action.result)"></div>
                    </div>
                    <div v-else class="content-text" v-html="renderMarkdown(action.action_args?.content || action.result)">
                    </div>
                  </template>
                  <template v-else>
                    <!-- CREATE_POST: 发布帖子 -->
                    <div v-if="action.action_type === 'CREATE_POST' && action.action_args?.content" class="content-text main-text" v-html="renderMarkdown(action.action_args.content)">
                    </div>

                    <!-- QUOTE_POST: 引用帖子 -->
                    <template v-if="action.action_type === 'QUOTE_POST'">
                      <div v-if="action.action_args?.quote_content" class="content-text" v-html="renderMarkdown(action.action_args.quote_content)">
                      </div>
                      <div v-if="action.action_args?.original_content" class="quoted-block" v-html="renderMarkdown(action.action_args.original_content)">
                      </div>
                    </template>

                    <!-- REPOST: 转发帖子 -->
                    <template v-if="action.action_type === 'REPOST'">
                      <div class="repost-info">
                        <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>
                        <span class="repost-label">{{ props.runMode === 'oasis' ? 'Thèse de référence partagée par' : 'Reposted from' }} @{{ action.action_args?.original_author_name || 'User' }}</span>
                      </div>
                      <div v-if="action.action_args?.original_content" class="repost-content" v-html="renderMarkdown(action.action_args.original_content)">
                      </div>
                    </template>

                    <!-- LIKE_POST: 点赞帖子 -->
                    <template v-if="action.action_type === 'LIKE_POST'">
                      <div class="like-info">
                        <svg class="icon-small filled" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                        <span class="like-label">{{ props.runMode === 'oasis' ? 'Soutien apporté à la thèse de' : 'Liked' }} @{{ action.action_args?.post_author_name || 'User' }}{{ props.runMode === 'oasis' ? '' : "'s post" }}</span>
                      </div>
                      <div v-if="action.action_args?.post_content" class="liked-content" v-html="renderMarkdown(action.action_args.post_content)">
                      </div>
                    </template>

                    <!-- CREATE_COMMENT: 发表评论 -->
                    <template v-if="action.action_type === 'CREATE_COMMENT'">
                      <div v-if="action.action_args?.content" class="content-text" v-html="renderMarkdown(action.action_args.content)">
                      </div>
                      <div v-if="action.action_args?.post_id" class="comment-context">
                        <svg class="icon-small" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                        <span>{{ props.runMode === 'oasis' ? 'Argumentation sur l\'avis' : 'Reply to post' }} #{{ action.action_args.post_id }}</span>
                      </div>
                    </template>

                    <!-- SEARCH_POSTS: 搜索帖子 -->
                    <template v-if="action.action_type === 'SEARCH_POSTS'">
                      <div class="search-info">
                        <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        <span class="search-label">{{ props.runMode === 'oasis' ? 'Recherche de pièces :' : 'Search Query:' }}</span>
                        <span class="search-query">"{{ action.action_args?.query || '' }}"</span>
                      </div>
                    </template>

                    <!-- FOLLOW: 关注用户 -->
                    <template v-if="action.action_type === 'FOLLOW'">
                      <div class="follow-info">
                        <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
                        <span class="follow-label">{{ props.runMode === 'oasis' ? 'Acteur suivi :' : 'Followed' }} @{{ action.action_args?.target_user || action.action_args?.user_id || 'User' }}</span>
                      </div>
                    </template>

                    <!-- UPVOTE / DOWNVOTE -->
                    <template v-if="action.action_type === 'UPVOTE_POST' || action.action_type === 'DOWNVOTE_POST'">
                      <div class="vote-info">
                        <svg v-if="action.action_type === 'UPVOTE_POST'" class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
                        <svg v-else class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                        <span class="vote-label">{{ props.runMode === 'oasis' ? (action.action_type === 'UPVOTE_POST' ? 'Thèse soutenue' : 'Thèse contredite') : (action.action_type === 'UPVOTE_POST' ? 'Upvoted' : 'Downvoted') }} Post</span>
                      </div>
                      <div v-if="action.action_args?.post_content" class="voted-content" v-html="renderMarkdown(action.action_args.post_content)">
                      </div>
                    </template>

                    <!-- DO_NOTHING: 无操作 -->
                    <template v-if="action.action_type === 'DO_NOTHING'">
                      <div class="idle-info">
                        <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                        <span class="idle-label">{{ props.runMode === 'oasis' ? 'Délibération individuelle' : 'Action Skipped' }}</span>
                      </div>
                    </template>

                    <!-- 通用回退 -->
                    <div v-if="!['CREATE_POST', 'QUOTE_POST', 'REPOST', 'LIKE_POST', 'CREATE_COMMENT', 'SEARCH_POSTS', 'FOLLOW', 'UPVOTE_POST', 'DOWNVOTE_POST', 'DO_NOTHING'].includes(action.action_type) && action.action_args?.content" class="content-text" v-html="renderMarkdown(action.action_args.content)">
                    </div>
                  </template>
                </div>

                <div class="card-footer">
                  <span class="time-tag">R{{ action.round_num }} • {{ formatActionTime(action.timestamp) }}</span>
                </div>
              </div>
            </div>
          </TransitionGroup>

          <div v-if="allActions.length === 0" class="waiting-state">
            <div class="pulse-ring"></div>
            <span>Waiting for agent actions...</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'cognitive'">
        <CognitiveStateVisualizer 
          :simulationId="simulationId" 
          :active="activeTab === 'cognitive'" 
          :isLegal="props.projectData?.simulation_mode === 'legal' && props.runMode === 'courtroom'" 
          :cognitiveHistory="runStatus.cognitive_history"
        />
      </template>

      <template v-else-if="activeTab === 'negotiation'">
        <div class="negotiation-chat-panel">
          <!-- Target Selector -->
          <div class="chat-target-selector">
            <span class="selector-label">{{ $t('history.liveChatTarget') }}</span>
            <div class="selector-options">
              <button 
                class="target-option"
                :class="{ active: chatTarget === 'advocate' }"
                @click="chatTarget = 'advocate'"
              >
                <span class="option-bullet advocate"></span>
                {{ $t('history.chatTargetAdvocate') }}
              </button>
              <button 
                class="target-option"
                :class="{ active: chatTarget === 'adversary' }"
                @click="chatTarget = 'adversary'"
              >
                <span class="option-bullet adversary"></span>
                {{ chatTargetAdversaryOptionLabel }}
              </button>
            </div>
          </div>

          <!-- Character Info Card -->
          <div v-if="chatTarget === 'advocate'" class="character-info-card advocate">
            <div class="info-card-header">
              <div class="info-card-avatar advocate-avatar">💼</div>
              <div class="info-card-info">
                <div class="info-card-name">Avocat de la Défense</div>
                <div class="info-card-subtitle">Discussion stratégique & Ligne de défense</div>
              </div>
            </div>
            <div class="info-card-body">
              <p>Ajustez votre ligne de défense pour les prochains rounds. Suggérez de nouveaux arguments juridiques ou techniques {{ isCivil ? 'face aux demandes du Demandeur' : 'face aux accusations du Procureur' }}.</p>
            </div>
          </div>

          <div v-else class="character-info-card adversary">
            <div class="info-card-header">
              <div class="info-card-avatar adversary-avatar">⚖️</div>
              <div class="info-card-info">
                <div class="info-card-name">{{ cabinetAdverseLabel }}</div>
                <div class="info-card-subtitle">Médiation "à chaud" & Offres d'accord</div>
              </div>
            </div>
            <div class="info-card-body">
              <p>Testez des offres de médiation de crise pour faire craquer l'avocat adverse virtuel : menaces réputationnelles, offres de rachat financier, ou concessions sur la Loi 25.</p>
              <div class="negotiation-badge-row">
                <span class="neg-badge neg-badge--finance">💰 Financier</span>
                <span class="neg-badge neg-badge--reputation">📣 Réputation</span>
                <span class="neg-badge neg-badge--law25">🔒 Loi 25</span>
              </div>
            </div>
          </div>

          <!-- Chat Messages Area -->
          <div class="chat-messages" ref="chatThreadContainer">
            <div v-if="chatMessagesFiltered.length === 0" class="chat-empty">
              <div class="empty-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <p class="empty-text">
                {{ chatTarget === 'advocate' 
                  ? "Suggérez une stratégie à votre avocat. Par exemple, insistez sur un argument financier ou technique pour le prochain round." 
                  : "Le procès s'annonce mal ? Proposez une offre de médiation de rachat, menacez d'exposer publiquement l'affaire ou suggérez des concessions réglementaires." }}
              </p>
            </div>
            
            <div 
              v-else 
              v-for="(msg, index) in chatMessagesFiltered" 
              :key="index" 
              class="chat-message"
              :class="msg.role === 'user' ? 'user' : 'assistant'"
            >
              <div class="message-avatar">
                <span v-if="msg.role === 'user'">U</span>
                <span v-else>{{ msg.target === 'advocate' ? 'Av' : (isCivil ? 'Dm' : 'Pr') }}</span>
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="sender-name">
                    {{ msg.role === 'user' ? 'Vous' : (msg.target === 'advocate' ? 'Avocat de la Défense' : adversaryLabel) }}
                  </span>
                  <span class="message-time">{{ msg.time }}</span>
                </div>
                <div class="message-text">
                  {{ msg.content }}
                </div>
              </div>
            </div>
            
            <!-- Typing Indicator -->
            <div v-if="chatSending" class="chat-message assistant">
              <div class="message-avatar">
                <span>{{ chatTarget === 'advocate' ? 'Av' : (isCivil ? 'Dm' : 'Pr') }}</span>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat Input -->
          <div class="chat-input-area" style="flex-direction: column; align-items: stretch; gap: 8px;">
            <div class="chat-input-options" style="display: flex; align-items: center; padding-left: 2px;">
              <label class="stimulus-toggle-label" style="display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;">
                <input type="checkbox" v-model="injectAsStimulus" class="stimulus-checkbox" style="accent-color: #00F2FE; width: 14px; height: 14px; cursor: pointer;" />
                <span class="stimulus-toggle-text" style="font-size: 11px; color: #64748B; font-weight: 500;">{{ props.runMode === 'oasis' ? 'Influer sur l\'opinion (Injecter comme stimulus)' : 'Influer sur le procès (Injecter comme stimulus)' }}</span>
              </label>
            </div>
            <div style="display: flex; gap: 12px; align-items: flex-end;">
              <textarea 
                v-model="chatInputMessage"
                class="chat-input"
                :placeholder="chatTarget === 'advocate' ? 'Suggérer une stratégie à votre avocat...' : 'Proposer un compromis, formuler une menace...'"
                @keydown.enter.exact.prevent="sendLiveChatMessage"
                :disabled="chatSending"
                rows="1"
              ></textarea>
              <button 
                class="send-btn"
                @click="sendLiveChatMessage"
                :disabled="!chatInputMessage.trim() || chatSending"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs" :class="{ minimized: consoleMinimized }">
      <div class="log-header" @click="consoleMinimized = !consoleMinimized" style="cursor: pointer; user-select: none;">
        <span class="log-title" style="display: flex; align-items: center; gap: 8px;">
          <span>SIMULATION MONITOR</span>
          <span style="font-size: 8px; font-weight: normal; padding: 2px 6px; border-radius: 4px; background: #1a1a1a; color: #888; border: 1px solid #333;">
            {{ consoleMinimized ? 'CLIQUEZ POUR EXPAND' : 'CLIQUEZ POUR RÉDUIRE' }}
          </span>
        </span>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="log-id">{{ simulationId || 'NO_SIMULATION' }}</span>
          <button 
            class="console-toggle-btn"
            @click.stop="consoleMinimized = !consoleMinimized"
            :title="consoleMinimized ? 'Agrandir la console' : 'Réduire la console'"
            style="background: #1e293b; border: 1px solid #334155; color: #94a3b8; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px; transition: all 0.2s ease;"
          >
            <span>{{ consoleMinimized ? '▲ AGRANDIR' : '▼ RÉDUIRE' }}</span>
          </button>
        </div>
      </div>
      <div v-show="!consoleMinimized" class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  startSimulation,
  stopSimulation,
  getRunStatus,
  getRunStatusDetail,
  getSimulationCognitiveStates,
  injectStimulus,
  liveChatWithCharacter,
  getSimulationConfig
} from '../api/simulation'
import { generateReport } from '../api/report'
import CognitiveStateVisualizer from './CognitiveStateVisualizer.vue'
import { supabase } from '../utils/supabase'

const { t } = useI18n()

const props = defineProps({
  simulationId: String,
  maxRounds: Number, // 从Step2传入的最大轮数
  isResume: {
    type: Boolean,
    default: false
  },
  runMode: {
    type: String,
    default: 'courtroom'
  },
  minutesPerRound: {
    type: Number,
    default: 30 // 默认每轮30分钟
  },
  clientSide: {
    type: String,
    default: 'defense'
  },
  selectedDraft: String,
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

const litigationType = ref('civil')

const isCivil = computed(() => {
  if (props.projectData?.simulation_mode !== 'legal') return false
  return litigationType.value === 'civil'
})

const procureurLabel = computed(() => {
  return isCivil.value ? 'Avocat du Demandeur' : 'Le Procureur'
})

const adversaryLabel = computed(() => {
  if (props.clientSide === 'plaintiff') {
    return 'Avocat de la Défense'
  }
  return isCivil.value ? 'Avocat du Demandeur' : 'Procureur Adverse'
})

const cabinetAdverseLabel = computed(() => {
  if (props.clientSide === 'plaintiff') {
    return 'Avocat de la Défense'
  }
  return isCivil.value ? 'Avocat du Demandeur' : 'Cabinet Adverse & Procureur'
})

const acquittalRateLabel = computed(() => {
  if (props.clientSide === 'plaintiff') {
    return isCivil.value ? "TAUX DE SUCCÈS (DEMANDE)" : "TAUX DE CONDAMNATION"
  }
  return isCivil.value ? "TAUX DE REJET" : "TAUX DE RELAXE"
})

const chatTargetAdversaryOptionLabel = computed(() => {
  if (props.projectData?.simulation_mode === 'legal') {
    return isCivil.value ? t('history.chatTargetAdversaryCivil') : t('history.chatTargetAdversary')
  }
  return t('history.chatTargetAdversary')
})

// Stimulus injection state
const stimulusText = ref('')
const isInjecting = ref(false)
const injectionSuccess = ref(false)
const injectionError = ref(null)

// Live Audio bubble player
const currentlyPlayingId = ref(null)
const currentlyLoadingId = ref(null)
let activeAudio = null

const playBubbleTTS = async (action) => {
  const bubbleId = action._uniqueId || action.id || action.timestamp
  
  // 1. Create and unlock the audio element synchronously in the user click frame
  // This bypasses browser autoplay policies that block dynamic audio playback after await calls.
  const localAudio = new Audio()
  try {
    localAudio.play().catch(() => {})
    localAudio.pause()
  } catch (e) {}

  // If clicked while currently loading, cancel loading
  if (currentlyLoadingId.value === bubbleId) {
    currentlyLoadingId.value = null
    return
  }
  
  // If clicked while playing, pause/stop it
  if (currentlyPlayingId.value === bubbleId) {
    if (activeAudio) {
      activeAudio.pause()
      currentlyPlayingId.value = null
    }
    return
  }
  
  // Stop any other active playback or loading
  if (activeAudio) {
    activeAudio.pause()
    activeAudio = null
  }
  currentlyPlayingId.value = null
  currentlyLoadingId.value = null
  
  const text = action.action_args?.content || action.result || ''
  if (!text) return
  
  // Choose voice based on actor type
  let voice = 'fr-FR-HenriNeural' // Henri (France)
  if (action.action_type === 'SPEECH_PROSECUTOR' && isCivil.value) {
    voice = 'fr-CA-SylvieNeural'
  } else if (action.action_type === 'SPEECH_DEFENSE') {
    voice = 'fr-FR-HenriNeural'
  } else if (action.action_type === 'SPEECH_ACCUSED') {
    voice = 'fr-CA-SylvieNeural'
  } else if (action.action_type === 'VERDICT' || action.action_type === 'DECISION') {
    voice = 'fr-FR-HenriNeural'
  } else if (action.action_type === 'CLERK_ANALYSIS') {
    voice = 'fr-CA-SylvieNeural'
  }
  
  currentlyLoadingId.value = bubbleId
  
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5001'}/api/simulation/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, voice }),
    })
    
    if (!response.ok) {
      throw new Error('TTS generation failed')
    }
    
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    
    // Check if user cancelled while it was loading
    if (currentlyLoadingId.value !== bubbleId) {
      return
    }
    
    currentlyLoadingId.value = null
    currentlyPlayingId.value = bubbleId
    
    // Assign source to the already unlocked audio object
    localAudio.src = url
    activeAudio = localAudio
    
    const playPromise = activeAudio.play()
    if (playPromise !== undefined) {
      playPromise.catch(error => {
        console.error('Playback was prevented or failed:', error)
      })
    }
    
    activeAudio.onended = () => {
      if (currentlyPlayingId.value === bubbleId) {
        currentlyPlayingId.value = null
      }
      activeAudio = null
    }
  } catch (err) {
    console.error('Failed to play TTS:', err)
    if (currentlyLoadingId.value === bubbleId) {
      currentlyLoadingId.value = null
    }
    if (currentlyPlayingId.value === bubbleId) {
      currentlyPlayingId.value = null
    }
  }
}

const handleInjectStimulus = async () => {
  if (!stimulusText.value.trim() || !props.simulationId) return
  
  isInjecting.value = true
  injectionError.value = null
  injectionSuccess.value = false
  
  try {
    const res = await injectStimulus(props.simulationId, stimulusText.value.trim())
    if (res.success) {
      addLog(`[STIMULUS INJECTÉ] : "${stimulusText.value.trim()}"`)
      injectionSuccess.value = true
      stimulusText.value = ''
      // Hide success message after 3 seconds
      setTimeout(() => {
        injectionSuccess.value = false
      }, 3000)
    } else {
      injectionError.value = res.error || "Échec de l'injection."
    }
  } catch (err) {
    injectionError.value = err.message || "Erreur réseau."
  } finally {
    isInjecting.value = false
  }
}

const router = useRouter()

// State
const activeTab = ref('timeline')
const isGeneratingReport = ref(false)
const phase = ref(0) // 0: 未开始, 1: 运行中, 2: 已完成

// Live Chat State
const chatTarget = ref('advocate') // 'advocate' | 'adversary'
const chatInputMessage = ref('')
const chatSending = ref(false)
const injectAsStimulus = ref(true)
const consoleMinimized = ref(false)
const chatMessages = ref([]) // array of { role: 'user'|'assistant', content: string, target: 'advocate'|'adversary', time: string }
const chatThreadContainer = ref(null)

// Filter messages for current selected target
const chatMessagesFiltered = computed(() => {
  return chatMessages.value.filter(msg => msg.target === chatTarget.value)
})

// Auto scroll chat thread to bottom
watch(chatMessagesFiltered, () => {
  nextTick(() => {
    if (chatThreadContainer.value) {
      chatThreadContainer.value.scrollTop = chatThreadContainer.value.scrollHeight
    }
  })
}, { deep: true })

const sendLiveChatMessage = async () => {
  const msg = chatInputMessage.value.trim()
  if (!msg || chatSending.value || !props.simulationId) return
  
  const target = chatTarget.value
  const currentTime = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  
  // 1. Add user message locally
  chatMessages.value.push({
    role: 'user',
    content: msg,
    target: target,
    time: currentTime
  })
  chatInputMessage.value = ''
  chatSending.value = true
  
  // Form history for the specific target
  const specificHistory = chatMessages.value
    .filter(m => m.target === target)
    .slice(0, -1) // exclude the one we just added
    .map(m => ({
      role: m.role,
      content: m.content
    }))
    
  try {
    const response = await liveChatWithCharacter({
      simulation_id: props.simulationId,
      character: target,
      message: msg,
      chat_history: specificHistory,
      inject_as_stimulus: injectAsStimulus.value
    })
    
    if (response.success && response.data?.response) {
      // 2. Add assistant message
      chatMessages.value.push({
        role: 'assistant',
        content: response.data.response,
        target: target,
        time: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
      })
      
      // Log influence in the console
      if (response.data.injected) {
        const targetLabel = target === 'advocate' ? "l'Avocat" : (props.runMode === 'oasis' ? "la partie adverse" : (isCivil.value ? "le Demandeur" : "le Procureur"))
        addLog(`[INFLUENCE INJECTÉE] Échange de négociation avec ${targetLabel} intégré ${props.runMode === 'oasis' ? 'aux débats' : 'au procès'}.`)
      } else {
        const targetLabel = target === 'advocate' ? "l'Avocat" : (props.runMode === 'oasis' ? "la partie adverse" : (isCivil.value ? "le Demandeur" : "le Procureur"))
        addLog(`[DISCUSSION CHAT] Discussion hors-champ avec ${targetLabel}.`)
      }
    } else {
      addLog(`[ERREUR CHAT] Échec de la communication avec le personnage: ${response.error || 'Erreur inconnue'}`)
    }
  } catch (err) {
    addLog(`[ERREUR CHAT] Exception de communication: ${err.message}`)
  } finally {
    chatSending.value = false
  }
}

const isStarting = ref(false)
const isStopping = ref(false)
const startError = ref(null)
const runStatus = ref({})
const allActions = ref([]) // 所有动作（增量累积）
const actionIds = ref(new Set()) // 用于去重的动作ID集合
const scrollContainer = ref(null)

// Narrative State Intelligence (PIE) State for hover cards
const cognitiveStates = ref([])
const hoveredAgentId = ref(null)
const hoveredAgentName = ref(null)

const hoveredAgentState = computed(() => {
  if (hoveredAgentId.value === null && !hoveredAgentName.value) return null
  return cognitiveStates.value.find(s => {
    if (hoveredAgentId.value !== null) {
      if (String(s.agent_id).trim() === String(hoveredAgentId.value).trim()) {
        return true
      }
    }
    if (hoveredAgentName.value) {
      if (s.name.toLowerCase().trim() === String(hoveredAgentName.value).toLowerCase().trim()) {
        return true
      }
    }
    return false
  }) || null
})

const hoverAgent = (action) => {
  hoveredAgentId.value = (action.agent_id !== undefined && action.agent_id !== null) ? action.agent_id : null
  hoveredAgentName.value = action.agent_name || null
}

const clearHover = () => {
  hoveredAgentId.value = null
  hoveredAgentName.value = null
}

const isActionAgentHovered = (action) => {
  if (hoveredAgentId.value === null && !hoveredAgentName.value) return false
  if (!hoveredAgentState.value) return false
  
  if (hoveredAgentId.value !== null && action.agent_id !== undefined && action.agent_id !== null) {
    if (String(action.agent_id).trim() === String(hoveredAgentId.value).trim()) {
      return true
    }
  }
  if (hoveredAgentName.value && action.agent_name) {
    if (String(action.agent_name).toLowerCase().trim() === String(hoveredAgentName.value).toLowerCase().trim()) {
      return true
    }
  }
  return false
}

const getTensionsForAgent = (agentState) => {
  if (!agentState || !agentState.tensions) return []
  const isLegalMode = props.projectData?.simulation_mode === 'legal'
  if (isLegalMode) {
    return [
      { left: 'PROCÉDURE', right: 'ÉQUITÉ', value: agentState.tensions.procedure_vs_equite ?? 0.5 },
      { left: 'OFFENSIVE', right: 'NÉGOCIATION', value: agentState.tensions.offensive_vs_negociation ?? 0.5 },
      { left: 'PRUDENCE', right: 'RAPIDITÉ', value: agentState.tensions.prudence_vs_rapidite ?? 0.5 }
    ]
  } else {
    return [
      { left: 'EXPLORATION', right: 'SECURITY', value: agentState.tensions.exploration_vs_security ?? 0.5 },
      { left: 'COOPERATION', right: 'DOMINATION', value: agentState.tensions.cooperation_vs_domination ?? 0.5 },
      { left: 'TRUTH', right: 'SOCIAL SURVIVAL', value: agentState.tensions.truth_vs_social_survival ?? 0.5 }
    ]
  }
}

const fetchParentCognitiveStates = async () => {
  if (!props.simulationId) return
  try {
    const res = await getSimulationCognitiveStates(props.simulationId)
    if (res.success && res.data) {
      cognitiveStates.value = res.data
    }
  } catch (err) {
    console.warn("Erreur de récupération des états cognitifs dans le parent:", err)
  }
}

let parentPollTimer = null
const startParentPolling = () => {
  if (parentPollTimer) clearInterval(parentPollTimer)
  fetchParentCognitiveStates()
  parentPollTimer = setInterval(fetchParentCognitiveStates, 4000)
}

const stopParentPolling = () => {
  if (parentPollTimer) {
    clearInterval(parentPollTimer)
    parentPollTimer = null
  }
}

// Markdown renderer helper
const renderMarkdown = (content) => {
  if (!content) return ''
  
  let html = content.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
  
  // lists
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-li" data-level="${level}">${text}</li>`
  })
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-oli" data-level="${level}">${text}</li>`
  })
  
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  html = html.replace(/(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g, '<ol class="md-ol">$&</ol>')
  
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">')
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">')
  html = html.replace(/\s+<\/ul>/g, '</ul>')
  html = html.replace(/\s+<\/ol>/g, '</ol>')
  
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')
  html = html.replace(/^---$/gm, '<hr class="md-hr">')
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  return html
}

// Computed
// 按时间顺序显示动作（最新的在最后面，即底部）
const chronologicalActions = computed(() => {
  return allActions.value
})

// 各平台动作计数
const twitterActionsCount = computed(() => {
  return allActions.value.filter(a => a.platform === 'twitter').length
})

const redditActionsCount = computed(() => {
  return allActions.value.filter(a => a.platform === 'reddit').length
})

// 格式化模拟流逝时间（根据轮次和每轮分钟数计算）
const formatElapsedTime = (currentRound) => {
  if (!currentRound || currentRound <= 0) return '0h 0m'
  const totalMinutes = currentRound * props.minutesPerRound
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours}h ${minutes}m`
}

// Twitter平台的模拟流逝时间
const twitterElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.twitter_current_round || 0)
})

// Reddit平台的模拟流逝时间
const redditElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.reddit_current_round || 0)
})

// Taux d'acquittement pour la simulation juridique
const acquittalRate = computed(() => {
  const verdicts = allActions.value.filter(a => a.action_type === 'VERDICT' || a.action_type === 'DECISION')
  if (verdicts.length === 0) return null
  const wins = verdicts.filter(v => {
    const text = (v.action_args?.content || v.result || '').toUpperCase()
    // Check if the defendant is declared guilty or condemned
    const hasGuilty = text.includes('COUPABLE') && !text.includes('NON COUPABLE') && !text.includes('NON-COUPABLE')
    let hasCondemnation = false
    if (text.includes('CONDAMNE') || text.includes('CONDAMNER')) {
      const matchesApex = text.includes('APEX') || text.includes('DÉFENDEUR') || text.includes('DÉFENDERESSE') || text.includes('DEFENDEUR') || text.includes('DEFENDERESSE')
      if (matchesApex) {
        hasCondemnation = true
      }
    }
    
    if (hasGuilty || hasCondemnation) {
      return false
    }
    
    return text.includes('RELAXE') || text.includes('ACQUITTEMENT') || text.includes('NON COUPABLE') || text.includes('NON-COUPABLE') || text.includes('ACQUITTE') || text.includes('REJETTE') || text.includes('REFUSE')
  })
  const baseRate = Math.round((wins.length / verdicts.length) * 100)
  if (props.clientSide === 'plaintiff') {
    return 100 - baseRate
  }
  return baseRate
})

// Dernier verdict rendu
const lastVerdict = computed(() => {
  const verdicts = allActions.value.filter(a => a.action_type === 'VERDICT' || a.action_type === 'DECISION')
  if (verdicts.length === 0) return null
  const lastV = verdicts[0]
  const text = lastV.action_args?.content || lastV.result || ''
  return text.length > 35 ? text.substring(0, 35) + '...' : text
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// 重置所有状态（用于重新启动模拟）
const resetAllState = () => {
  phase.value = 0
  runStatus.value = {}
  allActions.value = []
  actionIds.value = new Set()
  prevTwitterRound.value = 0
  prevRedditRound.value = 0
  startError.value = null
  isStarting.value = false
  isStopping.value = false
  stopPolling()  // 停止之前可能存在的轮询
}

// 启动模拟
const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog(t('log.errorMissingSimId'))
    return
  }

  // 先重置所有状态，确保不会受到上一次模拟的影响
  resetAllState()
  
  isStarting.value = true
  startError.value = null
  if (props.isResume) {
    addLog("[INFO] Reprise de la simulation de procès...")
  } else {
    addLog(t('log.startingDualSim'))
  }
  emit('update-status', 'processing')
  
  try {
    const params = {
      simulation_id: props.simulationId,
      platform: 'parallel',
      force: !props.isResume,
      enable_graph_memory_update: true,  // 开启动态图谱更新
      run_mode: props.runMode,
      client_side: props.clientSide || 'defense'
    }
    
    if (props.selectedDraft) {
      params.initial_stimulus = props.selectedDraft
    }
    
    if (props.maxRounds) {
      params.max_rounds = props.maxRounds
      addLog(t('log.setMaxRounds', { rounds: props.maxRounds }))
    }
    
    addLog(t('log.graphMemoryUpdateEnabled'))
    
    if (props.selectedDraft) {
      addLog(`[Radar Tactique] Projet de requête injecté comme stimulus initial pour la simulation.`)
    }
    
    const res = await startSimulation(params)
    
    if (res.success && res.data) {
      if (res.data.force_restarted) {
        addLog(t('log.oldSimCleared'))
      }
      addLog(t('log.engineStarted'))
      addLog(`  ├─ PID: ${res.data.process_pid || '-'}`)
      
      phase.value = 1
      runStatus.value = res.data
      
      if (props.isResume) {
        // Fetch completed rounds immediately
        await fetchRunStatus()
        await fetchRunStatusDetail()
      }
      
      startStatusPolling()
      startDetailPolling()
    } else {
      startError.value = res.error || '启动失败'
      addLog(t('log.startFailed', { error: res.error || t('common.unknownError') }))
      emit('update-status', 'error')
    }
  } catch (err) {
    startError.value = err.message
    addLog(t('log.startException', { error: err.message }))
    emit('update-status', 'error')
  } finally {
    isStarting.value = false
  }
}

// 停止模拟
const handleStopSimulation = async () => {
  if (!props.simulationId) return
  
  isStopping.value = true
  addLog(t('log.stoppingSim'))
  
  try {
    const res = await stopSimulation({ simulation_id: props.simulationId })
    
    if (res.success) {
      addLog(t('log.simStoppedSuccess'))
      phase.value = 2
      stopPolling()
      emit('update-status', 'completed')
    } else {
      addLog(t('log.stopFailed', { error: res.error || t('common.unknownError') }))
    }
  } catch (err) {
    addLog(t('log.stopException', { error: err.message }))
  } finally {
    isStopping.value = false
  }
}

// 轮询状态
let statusTimer = null
let detailTimer = null

const startStatusPolling = () => {
  statusTimer = setInterval(fetchRunStatus, 2000)
}

const startDetailPolling = () => {
  detailTimer = setInterval(fetchRunStatusDetail, 3000)
}

const stopPolling = () => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (detailTimer) {
    clearInterval(detailTimer)
    detailTimer = null
  }
}

// 追踪各平台的上一次轮次，用于检测变化并输出日志
const prevTwitterRound = ref(0)
const prevRedditRound = ref(0)

const fetchRunStatus = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getRunStatus(props.simulationId)
    
    if (res.success && res.data) {
      const data = res.data
      
      runStatus.value = data
      
      // 分别检测各平台的轮次变化并输出日志
      if (data.twitter_current_round > prevTwitterRound.value) {
        addLog(`[Plaza] R${data.twitter_current_round}/${data.total_rounds} | T:${data.twitter_simulated_hours || 0}h | A:${data.twitter_actions_count}`)
        prevTwitterRound.value = data.twitter_current_round
      }
      
      if (data.reddit_current_round > prevRedditRound.value) {
        addLog(`[Community] R${data.reddit_current_round}/${data.total_rounds} | T:${data.reddit_simulated_hours || 0}h | A:${data.reddit_actions_count}`)
        prevRedditRound.value = data.reddit_current_round
      }
      
      // 检测模拟是否已完成（通过 runner_status 或平台完成状态判断）
      const isCompleted = data.runner_status === 'completed' || data.runner_status === 'stopped'
      
      // 额外检查：如果后端还没来得及更新 runner_status，但平台已经报告完成
      // 通过检测 twitter_completed 和 reddit_completed 状态判断
      const platformsCompleted = checkPlatformsCompleted(data)
      
      if (isCompleted || platformsCompleted) {
        if (platformsCompleted && !isCompleted) {
          addLog(t('log.allPlatformsCompleted'))
        }
        addLog(t('log.simCompleted'))
        phase.value = 2
        await fetchRunStatusDetail()
        stopPolling()
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('获取运行状态失败:', err)
  }
}

// 检查所有启用的平台是否已完成
const checkPlatformsCompleted = (data) => {
  // 如果没有任何平台数据，返回 false
  if (!data) return false
  
  // 检查各平台的完成状态
  const twitterCompleted = data.twitter_completed === true
  const redditCompleted = data.reddit_completed === true
  
  // 如果至少有一个平台完成了，检查是否所有启用的平台都完成了
  // 通过 actions_count 判断平台是否被启用（如果 count > 0 或 running 曾为 true）
  const twitterEnabled = (data.twitter_actions_count > 0) || data.twitter_running || twitterCompleted
  const redditEnabled = (data.reddit_actions_count > 0) || data.reddit_running || redditCompleted
  
  // 如果没有任何平台被启用，返回 false
  if (!twitterEnabled && !redditEnabled) return false
  
  // 检查所有启用的平台是否都已完成
  if (twitterEnabled && !twitterCompleted) return false
  if (redditEnabled && !redditCompleted) return false
  
  return true
}

const fetchRunStatusDetail = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getRunStatusDetail(props.simulationId)
    
    if (res.success && res.data) {
      // 使用 all_actions 获取完整的动作列表
      const serverActions = res.data.all_actions || []
      
      // 增量添加新动作（去重）
      let newActionsAdded = 0
      serverActions.forEach(action => {
        // 生成唯一ID
        const actionId = action.id || `${action.timestamp}-${action.platform}-${action.agent_id}-${action.action_type}`
        
        if (!actionIds.value.has(actionId)) {
          actionIds.value.add(actionId)
          allActions.value.push({
            ...action,
            _uniqueId: actionId
          })
          newActionsAdded++
        }
      })
      
      // 不自动滚动，让用户自由查看时间轴
      // 新动作会在底部追加
    }
  } catch (err) {
    console.warn('获取详细状态失败:', err)
  }
}

// Helpers
const getActionTypeLabel = (type) => {
  if (props.runMode === 'oasis') {
    const oasisLabels = {
      'CREATE_POST': 'Déposer Avis',
      'REPOST': 'Partager',
      'LIKE_POST': 'Soutenir la Thèse',
      'CREATE_COMMENT': 'Déposer Argument',
      'LIKE_COMMENT': 'Soutenir la Thèse',
      'DO_NOTHING': 'Délibération',
      'FOLLOW': 'Suivre',
      'SEARCH_POSTS': 'Rechercher',
      'QUOTE_POST': 'Citer',
      'UPVOTE_POST': 'Soutenir la Thèse',
      'DOWNVOTE_POST': 'Contredire',
      'SPEECH_PROSECUTOR': 'RÉQUISITION',
      'SPEECH_DEFENSE': 'PLAIDOIRIE',
      'SPEECH_ACCUSED': 'DÉPOSITION',
      'VERDICT': 'VERDICT',
      'DECISION': 'VERDICT',
      'CLERK_ANALYSIS': 'ANALYSE'
    }
    return oasisLabels[type] || type || 'UNKNOWN'
  }

  const labels = {
    'CREATE_POST': 'POST',
    'REPOST': 'REPOST',
    'LIKE_POST': 'LIKE',
    'CREATE_COMMENT': 'COMMENT',
    'LIKE_COMMENT': 'LIKE',
    'DO_NOTHING': 'IDLE',
    'FOLLOW': 'FOLLOW',
    'SEARCH_POSTS': 'SEARCH',
    'QUOTE_POST': 'QUOTE',
    'UPVOTE_POST': 'UPVOTE',
    'DOWNVOTE_POST': 'DOWNVOTE',
    'SPEECH_PROSECUTOR': 'RÉQUISITION',
    'SPEECH_DEFENSE': 'PLAIDOIRIE',
    'SPEECH_ACCUSED': 'DÉPOSITION',
    'VERDICT': 'VERDICT',
    'DECISION': 'VERDICT',
    'CLERK_ANALYSIS': 'ANALYSE',
    'STIMULUS': 'STIMULUS'
  }
  return labels[type] || type || 'UNKNOWN'
}


const getActionTypeClass = (type) => {
  const classes = {
    'CREATE_POST': 'badge-post',
    'REPOST': 'badge-action',
    'LIKE_POST': 'badge-action',
    'CREATE_COMMENT': 'badge-comment',
    'LIKE_COMMENT': 'badge-action',
    'QUOTE_POST': 'badge-post',
    'FOLLOW': 'badge-meta',
    'SEARCH_POSTS': 'badge-meta',
    'UPVOTE_POST': 'badge-action',
    'DOWNVOTE_POST': 'badge-action',
    'DO_NOTHING': 'badge-idle',
    'SPEECH_PROSECUTOR': 'badge-prosecutor',
    'SPEECH_DEFENSE': 'badge-defense',
    'SPEECH_ACCUSED': 'badge-accused',
    'VERDICT': 'badge-verdict',
    'DECISION': 'badge-verdict',
    'CLERK_ANALYSIS': 'badge-clerk',
    'STIMULUS': 'badge-stimulus'
  }
  return classes[type] || 'badge-default'
}

const truncateContent = (content, maxLength = 100) => {
  if (!content) return ''
  if (content.length > maxLength) return content.substring(0, maxLength) + '...'
  return content
}

const formatActionTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

const exportSimulationToPDF = async () => {
  if (!props.simulationId) return
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'
  
  let userId = ''
  if (supabase) {
    try {
      const { data } = await supabase.auth.getSession()
      if (data?.session?.user) {
        userId = data.session.user.id
      }
    } catch (err) {
      console.error('Error getting Supabase session for PDF export:', err)
    }
  }
  
  if (!userId) {
    try {
      const storedBypass = localStorage.getItem('lexior_bypass_session')
      if (storedBypass) {
        const bypassSession = JSON.parse(storedBypass)
        if (bypassSession?.user?.id) {
          userId = bypassSession.user.id
        }
      }
    } catch (err) {}
  }
  
  const url = `${baseURL}/api/simulation/${props.simulationId}/export-pdf?userId=${userId}`
  window.open(url, '_blank')
}

const handleNextStep = async () => {
  if (!props.simulationId) {
    addLog(t('log.errorMissingSimId'))
    return
  }

  if (isGeneratingReport.value) {
    addLog(t('log.reportRequestSent'))
    return
  }
  
  isGeneratingReport.value = true
  addLog(t('log.startingReportGen'))
  
  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true
    })
    
    if (res.success && res.data) {
      const reportId = res.data.report_id
      addLog(t('log.reportGenTaskStarted', { reportId }))
      
      // 跳转到报告页面
      router.push({ name: 'Report', params: { reportId } })
    } else {
      addLog(t('log.reportGenFailed', { error: res.error || t('common.unknownError') }))
      isGeneratingReport.value = false
    }
  } catch (err) {
    addLog(t('log.reportGenException', { error: err.message }))
    isGeneratingReport.value = false
  }
}

// Scroll log to bottom
const logContent = ref(null)
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

onMounted(async () => {
  addLog(t('log.step3Init'))
  if (props.simulationId) {
    try {
      const configRes = await getSimulationConfig(props.simulationId)
      if (configRes.success && configRes.data) {
        litigationType.value = configRes.data.litigation_type || 'civil'
      }
    } catch (e) {
      console.warn("Could not fetch simulation config for litigation type:", e)
    }
    doStartSimulation()
    startParentPolling()
  }
})

onUnmounted(() => {
  stopPolling()
  stopParentPolling()
})
</script>

<style scoped>
.simulation-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  overflow: hidden;
}

/* --- Control Bar --- */
.control-bar {
  background: #FFF;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #EAEAEA;
  z-index: 10;
  height: 64px;
}

.status-group {
  display: flex;
  gap: 12px;
}

/* Platform Status Cards */
.platform-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 4px;
  background: #FAFAFA;
  border: 1px solid #EAEAEA;
  opacity: 0.7;
  transition: all 0.3s;
  min-width: 140px;
  position: relative;
  cursor: pointer;
}

.platform-status.active {
  opacity: 1;
  border-color: #333;
  background: #FFF;
}

.platform-status.completed {
  opacity: 1;
  border-color: #1A936F;
  background: #F2FAF6;
}

/* Actions Tooltip */
.actions-tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 8px;
  padding: 10px 14px;
  background: #000;
  color: #FFF;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
  z-index: 100;
  min-width: 180px;
  pointer-events: none;
}

.actions-tooltip::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid #000;
}

.platform-status:hover .actions-tooltip {
  opacity: 1;
  visibility: visible;
}

.tooltip-title {
  font-size: 10px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.tooltip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tooltip-action {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  color: #FFF;
  letter-spacing: 0.03em;
}

.platform-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.platform-name {
  font-size: 11px;
  font-weight: 700;
  color: #000;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.platform-status.twitter .platform-icon { color: #000; }
.platform-status.reddit .platform-icon { color: #000; }

.platform-stats {
  display: flex;
  gap: 10px;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.stat-label {
  font-size: 8px;
  color: #999;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 11px;
  font-weight: 600;
  color: #333;
}

.stat-total, .stat-unit {
  font-size: 9px;
  color: #999;
  font-weight: 400;
}

.status-badge {
  margin-left: auto;
  color: #1A936F;
  display: flex;
  align-items: center;
}

/* Action Button */
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.action-btn.primary {
  background: #000;
  color: #FFF;
}

.action-btn.primary:hover:not(:disabled) {
  background: #333;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* --- Main Content Area --- */
.main-content-area {
  flex: 1;
  overflow-y: auto;
  position: relative;
  background: #FFF;
}

/* Timeline Header */
.timeline-header {
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  padding: 12px 24px;
  border-bottom: 1px solid #EAEAEA;
  z-index: 5;
  display: flex;
  justify-content: center;
}

.timeline-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 11px;
  color: #666;
  background: #F5F5F5;
  padding: 4px 12px;
  border-radius: 20px;
}

.total-count {
  font-weight: 600;
  color: #333;
}

.platform-breakdown {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.breakdown-divider { color: #DDD; }
.breakdown-item.twitter { color: #000; }
.breakdown-item.reddit { color: #000; }

/* --- Timeline Feed --- */
.timeline-feed {
  padding: 24px 0;
  position: relative;
  min-height: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.timeline-axis {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #EAEAEA; /* Cleaner line */
  transform: translateX(-50%);
}

.timeline-item {
  display: flex;
  justify-content: center;
  margin-bottom: 32px;
  position: relative;
  width: 100%;
}

.timeline-marker {
  position: absolute;
  left: 50%;
  top: 24px;
  width: 10px;
  height: 10px;
  background: #FFF;
  border: 1px solid #CCC;
  border-radius: 50%;
  transform: translateX(-50%);
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-dot {
  width: 4px;
  height: 4px;
  background: #CCC;
  border-radius: 50%;
}

.timeline-item.twitter .marker-dot { background: #000; }
.timeline-item.reddit .marker-dot { background: #000; }
.timeline-item.twitter .timeline-marker { border-color: #000; }
.timeline-item.reddit .timeline-marker { border-color: #000; }

/* Card Layout */
.timeline-card {
  width: calc(100% - 48px);
  background: #FFF;
  border-radius: 2px;
  padding: 16px 20px;
  border: 1px solid #EAEAEA;
  box-shadow: 0 2px 10px rgba(0,0,0,0.02);
  position: relative;
  transition: all 0.2s;
}

.timeline-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  border-color: #DDD;
}

/* Left side (Twitter) */
.timeline-item.twitter {
  justify-content: flex-start;
  padding-right: 50%;
}
.timeline-item.twitter .timeline-card {
  margin-left: auto;
  margin-right: 32px; /* Gap from axis */
}

/* Right side (Reddit) */
.timeline-item.reddit {
  justify-content: flex-end;
  padding-left: 50%;
}
.timeline-item.reddit .timeline-card {
  margin-right: auto;
  margin-left: 32px; /* Gap from axis */
}

/* Card Content Styles */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F5F5F5;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-placeholder {
  width: 24px;
  height: 24px;
  background: #000;
  color: #FFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: #000;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-indicator {
  color: #999;
  display: flex;
  align-items: center;
}

.action-badge {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 2px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid transparent;
}

/* Monochromatic Badges */
.badge-post { background: #F0F0F0; color: #333; border-color: #E0E0E0; }
.badge-comment { background: #F0F0F0; color: #666; border-color: #E0E0E0; }
.badge-action { background: #FFF; color: #666; border: 1px solid #E0E0E0; }
.badge-meta { background: #FAFAFA; color: #999; border: 1px dashed #DDD; }
.badge-idle { opacity: 0.5; }

.content-text {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  margin-bottom: 10px;
}

.content-text.main-text {
  font-size: 14px;
  color: #000;
}

/* Info Blocks (Quote, Repost, etc) */
.quoted-block, .repost-content {
  background: #F9F9F9;
  border: 1px solid #EEE;
  padding: 10px 12px;
  border-radius: 2px;
  margin-top: 8px;
  font-size: 12px;
  color: #555;
}

.quote-header, .repost-info, .like-info, .search-info, .follow-info, .vote-info, .idle-info, .comment-context {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 11px;
  color: #666;
}

.icon-small {
  color: #999;
}
.icon-small.filled {
  color: #999; /* Keep icons neutral unless highlighted */
}

.search-query {
  font-family: 'JetBrains Mono', monospace;
  background: #F0F0F0;
  padding: 0 4px;
  border-radius: 2px;
}

.card-footer {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  font-size: 10px;
  color: #BBB;
  font-family: 'JetBrains Mono', monospace;
}

/* Waiting State */
.waiting-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #666;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.pulse-ring {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid #EAEAEA;
  animation: ripple 2s infinite;
}

@keyframes ripple {
  0% { transform: scale(0.8); opacity: 1; border-color: #CCC; }
  100% { transform: scale(2.5); opacity: 0; border-color: #EAEAEA; }
}

/* Animation */
.timeline-item-enter-active,
.timeline-item-leave-active {
  transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.timeline-item-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.timeline-item-leave-to {
  opacity: 0;
}

/* Logs */
.system-logs {
  background: #000;
  color: #DDD;
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid #222;
  flex-shrink: 0;
  transition: padding 0.2s ease;
}

.system-logs.minimized {
  padding: 8px 16px;
}

.system-logs.minimized .log-header {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: #666;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar { width: 4px; }
.log-content::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time { color: #555; min-width: 75px; }
.log-msg { color: #BBB; word-break: break-all; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Loading spinner for button */
.loading-spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}

/* Tab Selector Control Styled */
.tab-selector-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  background: #0B1220; /* Sleek navy dark mode bg */
  padding: 6px;
  margin: 16px 24px;
  border-radius: 8px;
  border: 1px solid #1A2333;
}

.tab-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: #8A9CAE;
  padding: 8px 16px;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: center;
}

.tab-btn:hover {
  color: #FFFFFF;
  background: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  background: #C5A880; /* Premium LEXIOR gold */
  color: #0B1220;
  box-shadow: 0 2px 8px rgba(197, 168, 128, 0.3);
}

/* Courtroom Speech Styling */
.courtroom-speech {
  padding: 14px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: #1E293B; /* Dark slate text for perfect contrast on light theme background */
}
.courtroom-speech.prosecutor {
  background: rgba(220, 53, 69, 0.04);
  border-left: 4px solid #DC3545;
}
.courtroom-speech.prosecutor .actor-label {
  color: #B91C1C; /* Dark red label */
}
.courtroom-speech.defense {
  background: rgba(40, 167, 69, 0.04);
  border-left: 4px solid #28A745;
}
.courtroom-speech.defense .actor-label {
  color: #15803D; /* Dark green label */
}
.courtroom-speech.accused {
  background: rgba(23, 162, 184, 0.04);
  border-left: 4px solid #17A2B8;
}
.courtroom-speech.accused .actor-label {
  color: #0369A1; /* Dark blue label */
}
.courtroom-speech.verdict {
  background: rgba(212, 175, 55, 0.08); /* Gold accent */
  border-left: 4px solid #D4AF37;
  font-weight: 500;
}
.courtroom-speech.verdict .actor-label {
  color: #B58A3D; /* Gold label */
}
.courtroom-speech.clerk {
  background: rgba(108, 117, 125, 0.04);
  border-left: 4px solid #6C757D;
}
.courtroom-speech.clerk .actor-label {
  color: #475569; /* Slate grey label */
}
.actor-label {
  font-weight: 700;
  margin-right: 6px;
}
.badge-prosecutor {
  background-color: #DC3545 !important;
  color: white !important;
}
.badge-defense {
  background-color: #28A745 !important;
  color: white !important;
}
.badge-accused {
  background-color: #17A2B8 !important;
  color: white !important;
}
.badge-verdict {
  background-color: #FFC107 !important;
  color: #000 !important;
}
.badge-clerk {
  background-color: #6C757D !important;
  color: white !important;
}
.badge-stimulus {
  background-color: #6F42C1 !important;
  color: white !important;
}
.courtroom-speech.stimulus {
  border-left: 3px solid #6F42C1;
  padding-left: 8px;
  background-color: rgba(111, 66, 193, 0.05);
}

/* Courtroom speech content custom style */
.speech-text-content {
  margin-top: 6px;
}

/* Markdown formatting styles */
:deep(.md-p) {
  margin: 0 0 8px 0;
}
:deep(.md-p:last-child) {
  margin-bottom: 0;
}
:deep(.md-h2) {
  font-size: 18px;
  font-weight: 700;
  color: #1E293B;
  margin: 16px 0 8px 0;
}
:deep(.md-h3) {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin: 14px 0 6px 0;
}
:deep(.md-h4) {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin: 12px 0 4px 0;
}
:deep(.md-h5) {
  font-size: 12px;
  font-weight: 600;
  color: #64748B;
  margin: 10px 0 2px 0;
}
:deep(.md-quote) {
  margin: 8px 0;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.02);
  border-left: 3px solid #64748B;
  color: #475569;
  font-style: italic;
}
:deep(.md-ul), :deep(.md-ol) {
  margin: 8px 0;
  padding-left: 20px;
}
:deep(.md-li), :deep(.md-oli) {
  margin: 4px 0;
}
:deep(.code-block) {
  margin: 8px 0;
  padding: 8px 12px;
  background: #0F172A;
  border-radius: 4px;
  overflow-x: auto;
}
:deep(.code-block code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #E2E8F0;
}
:deep(.inline-code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
  color: #0F172A;
}
:deep(strong) {
  font-weight: 700;
}
:deep(em) {
  font-style: italic;
}

/* Cognitive State Hover Card and Triggers */
.cognitive-trigger-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  cursor: pointer;
}

.brain-icon-trigger {
  font-size: 13px;
  opacity: 0.65;
  transition: all 0.25s ease;
  padding: 1px 5px;
  background: rgba(168, 85, 247, 0.08);
  border-radius: 4px;
  border: 1px solid rgba(168, 85, 247, 0.15);
  user-select: none;
}

.cognitive-trigger-wrapper:hover .brain-icon-trigger {
  opacity: 1;
  transform: scale(1.1);
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.35);
  background: rgba(168, 85, 247, 0.18);
  border-color: rgba(168, 85, 247, 0.4);
}

.cognitive-hover-card {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 290px;
  background: rgba(13, 15, 18, 0.96);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(168, 85, 247, 0.25);
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.7), 0 0 20px rgba(168, 85, 247, 0.12);
  padding: 14px;
  z-index: 999;
  color: #E2E8F0;
  text-align: left;
  animation: cardFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  cursor: default;
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(-6px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.hover-card-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 6px;
  margin-bottom: 10px;
}

.hover-card-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #A855F7;
  letter-spacing: 0.8px;
}

.hover-narrative {
  font-size: 11px;
  font-style: italic;
  line-height: 1.45;
  color: #CBD5E1;
  margin: 0 0 12px 0;
  background: rgba(255, 255, 255, 0.03);
  padding: 6px 8px;
  border-radius: 4px;
  border-left: 2px solid #A855F7;
}

.hover-section-title {
  font-size: 9px;
  font-weight: 700;
  color: #94A3B8;
  text-transform: uppercase;
  margin-bottom: 8px;
  letter-spacing: 0.8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 2px;
}

.hover-tensions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.hover-tension-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hover-tension-labels {
  display: flex;
  justify-content: space-between;
}

.hover-tension-labels .pole-label {
  font-size: 8px;
  font-weight: 700;
  color: #64748B;
  letter-spacing: 0.5px;
}

.hover-tension-bar-container {
  height: 6px;
  border-radius: 3px;
  background: #1E293B;
  position: relative;
  overflow: hidden;
}

.hover-tension-bar-fill {
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  background: linear-gradient(90deg, #EC4899 0%, #A855F7 100%);
  border-radius: 3px;
}

.hover-tension-marker {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: #FFFFFF;
  box-shadow: 0 0 4px #FFFFFF;
  transform: translateX(-50%);
  z-index: 10;
}

.hover-tension-value {
  font-size: 8px;
  color: #94A3B8;
  text-align: right;
  margin-top: 1px;
}

.hover-beliefs-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 8px;
}

.hover-belief-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hover-belief-issue {
  font-size: 9px;
  font-weight: 700;
  color: #E2E8F0;
  letter-spacing: 0.5px;
}

.hover-prob-container {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hover-prob-row {
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  color: #94A3B8;
}

.hover-prob-state-name {
  color: #64748B;
}

.hover-prob-val {
  color: #A855F7;
  font-weight: 600;
}

/* --- Stimulus Injection Card --- */
.stimulus-injection-card {
  background: #FFFFFF;
  border: 1px solid #EAEAEA;
  border-radius: 12px;
  padding: 20px;
  margin: 16px 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.card-header-premium {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.card-title-premium {
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
  letter-spacing: 0.5px;
}

.card-subtitle-premium {
  font-size: 11px;
  color: #64748B;
}

.injection-form {
  display: flex;
  gap: 12px;
}

.stimulus-input {
  flex: 1;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #1E293B;
  outline: none;
  transition: all 0.3s;
}

.stimulus-input:focus {
  border-color: #3B82F6;
  background: #FFFFFF;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.inject-btn {
  background: #1E293B;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  padding: 0 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.inject-btn:hover:not(:disabled) {
  background: #0F172A;
  transform: translateY(-1px);
}

.inject-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.injection-feedback {
  margin-top: 12px;
  font-size: 11px;
  font-weight: 600;
  padding: 8px 12px;
  border-radius: 6px;
}

.injection-feedback.success {
  background: #F0FDF4;
  color: #166534;
  border: 1px solid #DCFCE7;
}

.injection-feedback.error {
  background: #FEF2F2;
  color: #991B1B;
  border: 1px solid #FEE2E2;
}

.loading-spinner-small {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #FFFFFF;
  animation: spin 1s ease-in-out infinite;
}

/* --- Negotiation Live Chat Tab Styles --- */
.negotiation-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #FFF;
  overflow: hidden;
}

.chat-target-selector {
  padding: 16px 24px;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  gap: 16px;
  background: #F9FAFB;
}

.selector-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.selector-options {
  display: flex;
  gap: 12px;
}

.target-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.target-option:hover {
  border-color: #D1D5DB;
  background: #F9FAFB;
}

.target-option.active {
  background: #1F2937;
  color: #FFFFFF;
  border-color: #1F2937;
}

.option-bullet {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.option-bullet.advocate {
  background: #3B82F6;
}

.option-bullet.adversary {
  background: #EF4444;
}

/* Character Info Card */
.character-info-card {
  border-radius: 8px;
  padding: 16px;
  margin: 16px 24px 0 24px;
}

.character-info-card.advocate {
  background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 100%);
  border: 1px solid #2B3D52;
}

.character-info-card.adversary {
  background: linear-gradient(135deg, #1C0A10 0%, #0D1627 100%);
  border: 1px solid #3B1B25;
}

.info-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.info-card-avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.info-card-avatar.advocate-avatar {
  background: #3B82F6;
  color: #FFF;
}

.info-card-avatar.adversary-avatar {
  background: #E0315C;
  color: #FFF;
}

.info-card-name {
  font-size: 14px;
  font-weight: 700;
  color: #FFF;
}

.info-card-subtitle {
  font-size: 11px;
}

.advocate .info-card-subtitle {
  color: #60A5FA;
}

.adversary .info-card-subtitle {
  color: #E0315C;
}

.info-card-body p {
  font-size: 12px;
  line-height: 1.5;
  color: #94A3B8;
  margin: 0 0 12px 0;
}

.info-card-body p:last-child {
  margin-bottom: 0;
}

.negotiation-badge-row {
  display: flex;
  gap: 8px;
}

.neg-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.neg-badge--finance {
  background: rgba(224, 180, 49, 0.1);
  color: #E0B431;
  border: 1px solid rgba(224, 180, 49, 0.2);
}

.neg-badge--reputation {
  background: rgba(224, 49, 92, 0.1);
  color: #E0315C;
  border: 1px solid rgba(224, 49, 92, 0.2);
}

.neg-badge--law25 {
  background: rgba(49, 140, 224, 0.1);
  color: #318CE0;
  border: 1px solid rgba(49, 140, 224, 0.2);
}

/* Chat Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #9CA3AF;
  padding: 40px 0;
}

.empty-icon {
  opacity: 0.3;
}

.empty-text {
  font-size: 13px;
  text-align: center;
  max-width: 320px;
  line-height: 1.6;
  color: #6B7280;
  margin: 0;
}

.chat-message {
  display: flex;
  gap: 12px;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.chat-message.user .message-avatar {
  background: #1F2937;
  color: #FFFFFF;
}

.chat-message.assistant .message-avatar {
  background: #F3F4F6;
  color: #374151;
}

.message-content {
  max-width: 75%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-message.user .message-content {
  align-items: flex-end;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-message.user .message-header {
  flex-direction: row-reverse;
}

.sender-name {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.message-time {
  font-size: 11px;
  color: #9CA3AF;
}

.message-text {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}

.chat-message.user .message-text {
  background: #1F2937;
  color: #FFFFFF;
  border-bottom-right-radius: 4px;
}

.chat-message.assistant .message-text {
  background: #F3F4F6;
  color: #374151;
  border-bottom-left-radius: 4px;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  background: #F3F4F6;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9CA3AF;
  border-radius: 50%;
  animation: typing-dots 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-dots {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* Chat Input */
.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid #E5E7EB;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #FFFFFF;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  font-size: 13px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.2s ease;
  max-height: 100px;
  background: #F8FAFC;
  color: #1E293B;
}

.chat-input:focus {
  outline: none;
  border-color: #1F2937;
  background: #FFFFFF;
}

.chat-input:disabled {
  background: #F9FAFB;
  cursor: not-allowed;
}

.send-btn {
  width: 44px;
  height: 44px;
  background: #1F2937;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #374151;
}

.send-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

.loading-spinner-small-dark {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #1E293B;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.main-content-area.chat-mode {
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}

.console-toggle-btn:hover {
  background: #334155 !important;
  color: #f8fafc !important;
  border-color: #475569 !important;
}

.courtroom-speech-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.tts-play-btn {
  font-size: 11px;
  opacity: 0.65;
  transition: all 0.25s ease;
  padding: 1px 5px;
  background: rgba(197, 168, 128, 0.08);
  border-radius: 4px;
  border: 1px solid rgba(197, 168, 128, 0.15);
  color: var(--orange);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  height: 20px;
  margin-left: 4px;
}

.tts-play-btn:hover {
  opacity: 1;
  transform: scale(1.08);
  box-shadow: 0 0 10px rgba(197, 168, 128, 0.35);
  background: rgba(197, 168, 128, 0.18);
}

.tts-play-btn.playing {
  opacity: 1;
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #EF4444;
}

.tts-play-btn.playing:hover {
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.2);
}

.tts-play-btn.loading {
  opacity: 1;
  background: rgba(197, 168, 128, 0.1);
  cursor: wait;
}

.tts-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid rgba(197, 168, 128, 0.3);
  border-radius: 50%;
  border-top-color: var(--orange);
  animation: tts-spin 0.8s linear infinite;
}

@keyframes tts-spin {
  to { transform: rotate(360deg); }
}
</style>