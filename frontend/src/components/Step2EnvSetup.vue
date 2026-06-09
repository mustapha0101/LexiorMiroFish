<template>
  <div class="env-setup-panel">
    <div class="scroll-container">
      <!-- Step 01: 模拟实例 -->
      <div class="step-card" :class="{ 'active': phase === 0, 'completed': phase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">{{ isOasisOrSocial ? 'Initialisation de la simulation publique' : 'Initialisation du procès judiciaire' }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 0" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else class="badge processing">{{ $t('step2.initializing') }}</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">
            {{ isOasisOrSocial ? 'Création de l\'instance de simulation publique sur les réseaux sociaux.' : (simulationConfig?.litigation_type === 'civil' ? 'Création de l\'instance de procès civil.' : (simulationConfig?.litigation_type === 'criminal' ? 'Création de l\'instance de procès criminel.' : 'Création de l\'instance de procès.')) }}
          </p>

          <div v-if="simulationId" class="info-card">
            <div class="info-row">
              <span class="info-label">Project ID</span>
              <span class="info-value mono">{{ projectData?.project_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Graph ID</span>
              <span class="info-value mono">{{ projectData?.graph_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Simulation ID</span>
              <span class="info-value mono">{{ simulationId }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Task ID</span>
              <span class="info-value mono">{{ taskId || $t('step2.asyncTaskDone') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: 生成 Agent 人设 -->
      <div class="step-card" :class="{ 'active': phase === 1, 'completed': phase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">{{ isOasisOrSocial ? 'Génération des personas d\'opinion publique' : 'Génération des acteurs clés' }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 1" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else-if="phase === 1" class="badge processing">{{ prepareProgress }}%</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ isOasisOrSocial ? 'Initialisation des acteurs et segments d\'opinion publique (Lanceur d\'alerte, Journaliste, Porte-parole, Expert, Citoyen moyen, Citoyen indigné, Sceptique, Consommateur) basés sur le dossier.' : (simulationConfig?.litigation_type === 'civil' ? 'Initialisation des acteurs clés du procès (Juge, Avocat du Demandeur, Avocat de la Défense, Défendeur, Greffier) basés sur le dossier.' : (simulationConfig?.litigation_type === 'criminal' ? 'Initialisation des acteurs clés du procès (Juge, Le Procureur, Avocat de la Défense, Le Prévenu, Greffier) basés sur le dossier.' : 'Initialisation des acteurs clés du procès basés sur le dossier.')) }}
          </p>

          <!-- Profiles Stats -->
          <div v-if="profiles.length > 0" class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ profiles.length }}</span>
              <span class="stat-label">{{ isOasisOrSocial ? 'Personas générés' : 'Acteurs générés' }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ expectedTotal || '-' }}</span>
              <span class="stat-label">{{ isOasisOrSocial ? 'Personas attendus' : 'Acteurs attendus' }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ totalTopicsCount }}</span>
              <span class="stat-label">{{ isOasisOrSocial ? 'Sujets d\'intérêt' : $t('step2.relatedTopicsCount') }}</span>
            </div>
          </div>

          <!-- Profiles List Preview -->
          <div v-if="profiles.length > 0" class="profiles-preview">
            <div class="preview-header">
              <span class="preview-title">{{ isOasisOrSocial ? 'Personas d\'opinion publique initialisés' : 'Acteurs du tribunal initialisés' }}</span>
            </div>
            <div class="profiles-list">
              <div 
                v-for="(profile, idx) in profiles" 
                :key="idx" 
                class="profile-card"
                @click="selectProfile(profile)"
              >
                <div class="profile-header">
                  <span class="profile-realname">{{ profile.username || 'Unknown' }}</span>
                  <span class="profile-username">@{{ profile.name || `agent_${idx}` }}</span>
                </div>
                <div class="profile-meta">
                  <span class="profile-profession">{{ profile.profession || $t('step2.unknownProfession') }}</span>
                </div>
                <p class="profile-bio">{{ profile.bio || $t('step2.noBio') }}</p>
                <div v-if="profile.interested_topics?.length" class="profile-topics">
                  <span 
                    v-for="topic in profile.interested_topics.slice(0, 3)" 
                    :key="topic" 
                    class="topic-tag"
                  >{{ topic }}</span>
                  <span v-if="profile.interested_topics.length > 3" class="topic-more">
                    +{{ profile.interested_topics.length - 3 }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: 生成双平台模拟配置 -->
      <div v-if="props.projectData?.simulation_mode !== 'legal'" class="step-card" :class="{ 'active': phase === 2, 'completed': phase > 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">{{ $t('step2.dualPlatformConfig') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 2" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else-if="phase === 2" class="badge processing">{{ $t('step2.generating') }}</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('step2.dualPlatformConfigDesc') }}
          </p>
          
          <!-- Config Preview -->
          <div v-if="simulationConfig" class="config-detail-panel">
            <!-- 时间配置 -->
            <div class="config-block">
              <div class="config-grid">
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.simulationDuration') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.total_simulation_hours || '-' }} {{ $t('common.hours') }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.roundDuration') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.minutes_per_round || '-' }} {{ $t('common.minutes') }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.totalRounds') }}</span>
                  <span class="config-item-value">{{ Math.floor((simulationConfig.time_config?.total_simulation_hours * 60 / simulationConfig.time_config?.minutes_per_round)) || '-' }} {{ $t('common.rounds') }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">{{ $t('step2.activePerHour') }}</span>
                  <span class="config-item-value">{{ simulationConfig.time_config?.agents_per_hour_min }}-{{ simulationConfig.time_config?.agents_per_hour_max }}</span>
                </div>
              </div>
              <div class="time-periods">
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.peakHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.peak_hours?.join(':00, ') }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.peak_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.workHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.work_hours?.[0] }}:00-{{ simulationConfig.time_config?.work_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.work_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.morningHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.morning_hours?.[0] }}:00-{{ simulationConfig.time_config?.morning_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.morning_activity_multiplier }}</span>
                </div>
                <div class="period-item">
                  <span class="period-label">{{ $t('step2.offPeakHours') }}</span>
                  <span class="period-hours">{{ simulationConfig.time_config?.off_peak_hours?.[0] }}:00-{{ simulationConfig.time_config?.off_peak_hours?.slice(-1)[0] }}:00</span>
                  <span class="period-multiplier">×{{ simulationConfig.time_config?.off_peak_activity_multiplier }}</span>
                </div>
              </div>
            </div>

            <!-- Agent 配置 -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('step2.agentConfig') }}</span>
                <span class="config-block-badge">{{ simulationConfig.agent_configs?.length || 0 }} {{ $t('common.items') }}</span>
              </div>
              <div class="agents-cards">
                <div 
                  v-for="agent in simulationConfig.agent_configs" 
                  :key="agent.agent_id" 
                  class="agent-card"
                >
                  <!-- 卡片头部 -->
                  <div class="agent-card-header">
                    <div class="agent-identity">
                      <span class="agent-id">Agent {{ agent.agent_id }}</span>
                      <span class="agent-name">{{ agent.entity_name }}</span>
                    </div>
                    <div class="agent-tags">
                      <span class="agent-type">{{ agent.entity_type }}</span>
                      <span class="agent-stance" :class="'stance-' + agent.stance">{{ agent.stance }}</span>
                    </div>
                  </div>
                  
                  <!-- 活跃时间轴 -->
                  <div class="agent-timeline">
                    <span class="timeline-label">{{ $t('step2.activeTimePeriod') }}</span>
                    <div class="mini-timeline">
                      <div 
                        v-for="hour in 24" 
                        :key="hour - 1" 
                        class="timeline-hour"
                        :class="{ 'active': agent.active_hours?.includes(hour - 1) }"
                        :title="`${hour - 1}:00`"
                      ></div>
                    </div>
                    <div class="timeline-marks">
                      <span>0</span>
                      <span>6</span>
                      <span>12</span>
                      <span>18</span>
                      <span>24</span>
                    </div>
                  </div>

                  <!-- 行为参数 -->
                  <div class="agent-params">
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.postsPerHour') }}</span>
                        <span class="param-value">{{ agent.posts_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.commentsPerHour') }}</span>
                        <span class="param-value">{{ agent.comments_per_hour }}</span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.responseDelay') }}</span>
                        <span class="param-value">{{ agent.response_delay_min }}-{{ agent.response_delay_max }}min</span>
                      </div>
                    </div>
                    <div class="param-group">
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.activityLevel') }}</span>
                        <span class="param-value with-bar">
                          <span class="mini-bar" :style="{ width: (agent.activity_level * 100) + '%' }"></span>
                          {{ (agent.activity_level * 100).toFixed(0) }}%
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.sentimentBias') }}</span>
                        <span class="param-value" :class="agent.sentiment_bias > 0 ? 'positive' : agent.sentiment_bias < 0 ? 'negative' : 'neutral'">
                          {{ agent.sentiment_bias > 0 ? '+' : '' }}{{ agent.sentiment_bias?.toFixed(1) }}
                        </span>
                      </div>
                      <div class="param-item">
                        <span class="param-label">{{ $t('step2.influenceWeight') }}</span>
                        <span class="param-value highlight">{{ agent.influence_weight?.toFixed(1) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 平台配置 -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('step2.recommendAlgoConfig') }}</span>
              </div>
              <div class="platforms-grid">
                <div v-if="simulationConfig.twitter_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">{{ $t('step2.platform1Name') }}</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.recencyWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.popularityWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.relevanceWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.viralThreshold') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.echoChamberStrength') }}</span>
                      <span class="param-value">{{ simulationConfig.twitter_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="simulationConfig.reddit_config" class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">{{ $t('step2.platform2Name') }}</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.recencyWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.recency_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.popularityWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.popularity_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.relevanceWeight') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.relevance_weight }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.viralThreshold') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.viral_threshold }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">{{ $t('step2.echoChamberStrength') }}</span>
                      <span class="param-value">{{ simulationConfig.reddit_config.echo_chamber_strength }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- LLM 配置推理 -->
            <div v-if="simulationConfig.generation_reasoning" class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">{{ $t('step2.llmConfigReasoning') }}</span>
              </div>
              <div class="reasoning-content">
                <div 
                  v-for="(reason, idx) in simulationConfig.generation_reasoning.split('|').slice(0, 2)" 
                  :key="idx" 
                  class="reasoning-item"
                >
                  <p class="reasoning-text">{{ reason.trim() }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 04: 初始激活编排 -->
      <div v-if="props.projectData?.simulation_mode !== 'legal'" class="step-card" :class="{ 'active': phase === 3, 'completed': phase > 3 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">04</span>
            <span class="step-title">{{ $t('step2.initialActivation') }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 3" class="badge success">{{ $t('common.completed') }}</span>
            <span v-else-if="phase === 3" class="badge processing">{{ $t('step2.orchestrating') }}</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/prepare</p>
          <p class="description">
            {{ $t('step2.initialActivationDesc') }}
          </p>

          <div v-if="simulationConfig?.event_config" class="orchestration-content">
            <!-- 叙事方向 -->
            <div class="narrative-box">
              <span class="box-label narrative-label">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="special-icon">
                  <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M16.24 7.76L14.12 14.12L7.76 16.24L9.88 9.88L16.24 7.76Z" fill="url(#paint0_linear)" stroke="url(#paint0_linear)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <defs>
                    <linearGradient id="paint0_linear" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#FF5722"/>
                      <stop offset="1" stop-color="#FF9800"/>
                    </linearGradient>
                  </defs>
                </svg>
                {{ $t('step2.narrativeDirection') }}
              </span>
              <p class="narrative-text">{{ simulationConfig.event_config.narrative_direction }}</p>
            </div>

            <!-- 热点话题 -->
            <div class="topics-section">
              <span class="box-label">{{ $t('step2.initialHotTopics') }}</span>
              <div class="hot-topics-grid">
                <span v-for="topic in simulationConfig.event_config.hot_topics" :key="topic" class="hot-topic-tag">
                  # {{ topic }}
                </span>
              </div>
            </div>

            <!-- 初始帖子流 -->
            <div class="initial-posts-section">
              <span class="box-label">{{ $t('step2.initialActivationSeq', { count: simulationConfig.event_config.initial_posts.length }) }}</span>
              <div class="posts-timeline">
                <div v-for="(post, idx) in simulationConfig.event_config.initial_posts" :key="idx" class="timeline-item">
                  <div class="timeline-marker"></div>
                  <div class="timeline-content">
                    <div class="post-header">
                      <span class="post-role">{{ post.poster_type }}</span>
                      <span class="post-agent-info">
                        <span class="post-id">Agent {{ post.poster_agent_id }}</span>
                        <span class="post-username">@{{ getAgentUsername(post.poster_agent_id) }}</span>
                      </span>
                    </div>
                    <p class="post-text">{{ post.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 05: 准备完成 -->
      <div class="step-card" :class="{ 'active': phase === 4 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">05</span>
            <span class="step-title">{{ isOasisOrSocial ? 'Configuration de la simulation prête' : 'Configuration de l\'Audience prête' }}</span>
          </div>
          <div class="step-status">
            <span v-if="phase >= 4" class="badge processing">{{ $t('step1.inProgress') }}</span>
            <span v-else class="badge pending">{{ $t('common.pending') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/simulation/start</p>
          <p class="description">{{ isOasisOrSocial ? 'Configurez l\'environnement d\'exécution et le nombre de rounds pour la simulation.' : 'Configurez l\'environnement d\'exécution et le nombre d\'itérations pour la simulation.' }}</p>
          
          <!-- Choix de la Partie Représentée (uniquement pour les projets judiciaires) -->
          <div v-if="props.projectData?.simulation_mode === 'legal' && runMode === 'courtroom'" class="side-select-section">
            <span class="section-title">Choix de la Partie Représentée</span>
            <span class="section-desc">Sélectionnez le camp que vous souhaitez incarner pour évaluer vos options et adapter les conseils tactiques.</span>
            
            <div class="side-cards-grid">
              <div 
                class="side-select-card" 
                :class="{ active: clientSide === 'defense' }" 
                @click="clientSide = 'defense'"
              >
                <div class="side-icon">🛡️</div>
                <div class="side-details">
                  <span class="side-name">La Défense</span>
                  <span class="side-description">Représenter la partie défenderesse ou le prévenu. Analyser les failles de l'accusation et maximiser les chances d'acquittement ou de rejet.</span>
                </div>
              </div>
              
              <div 
                class="side-select-card" 
                :class="{ active: clientSide === 'plaintiff' }" 
                @click="clientSide = 'plaintiff'"
              >
                <div class="side-icon">⚖️</div>
                <div class="side-details">
                  <span class="side-name">{{ isCivil ? 'Le Demandeur' : 'La Poursuite' }}</span>
                  <span class="side-description">Représenter la partie demanderesse ou poursuivante. Consolider les faits et maximiser les chances de condamnation.</span>
                </div>
              </div>
              </div>
            </div>

          <!-- Radar d'Anticipation Tactique (Détecteur de Failles / Lignes de Force) -->
          <div v-if="props.projectData?.simulation_mode === 'legal' && runMode === 'courtroom'" class="radar-tactique-section">
            <div class="radar-header-inline">
              <div class="radar-header-text">
                <span class="section-title">Radar d'Anticipation Tactique (Détecteur de Failles)</span>
                <span class="section-desc">Analysez la structure sémantique et la centralité du dossier pour détecter les failles critiques et générer des requêtes sur mesure.</span>
              </div>
              <button 
                class="radar-trigger-btn" 
                :class="{ 'loading': radarLoading }" 
                :disabled="radarLoading"
                @click="triggerRadarAnalysis"
              >
                <span v-if="radarLoading" class="spinner-icon">⏳</span>
                <span v-else>🔍</span>
                {{ radarLoading ? 'Analyse du dossier...' : 'Activer le Radar' }}
              </button>
            </div>

            <!-- Strategic Opportunities Matrix -->
            <div v-if="radarResults" class="radar-results-card">
              <div class="matrix-title-row">
                <div class="matrix-title-info">
                  <span class="matrix-title">Matrice d'Anticipation Stratégique ({{ clientSide === 'defense' ? 'Défense' : 'Poursuite' }})</span>
                  <span class="matrix-subtitle">Opportunités tactiques classées par impact sémantique potentiel</span>
                </div>
                <button class="expand-matrix-btn" @click="showExpandedMatrix = true" title="Agrandir la matrice dans une grande fenêtre">
                  🖥️ Agrandir la matrice
                </button>
              </div>
              
              <div class="table-container">
                <table class="radar-table">
                  <thead>
                    <tr>
                      <th>Élément Clé</th>
                      <th>Ligne de Force / Faille</th>
                      <th>Impact Prédit</th>
                      <th>Feuille de Route</th>
                      <th class="actions-col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, idx) in radarResults" :key="idx" :class="{ 'row-selected': selectedDraft && selectedDraft.node_name === item.node_name && selectedDraft.vector_name === item.vector_name }">
                      <td class="node-cell"><strong>{{ item.node_name }}</strong></td>
                      <td class="vector-cell"><span class="vector-badge">{{ item.vector_name }}</span></td>
                      <td class="impact-cell">
                        <div class="impact-value-wrapper">
                          <span class="impact-text">{{ item.impact }}</span>
                          <div class="progress-bar-container">
                            <div class="progress-bar-fill" :style="{ width: (item.impact_value || 0) + '%' }"></div>
                          </div>
                        </div>
                      </td>
                      <td class="plan-cell plan-cell-clamp">{{ item.match_plan }}</td>
                      <td class="action-cell">
                        <button class="detail-btn" @click="openOpportunityDetail(item)" title="Voir les détails">
                          🔍 Détails
                        </button>
                        <button class="draft-btn" @click="triggerDraftRequest(item)">
                          📄 Requête
                        </button>
                        <span v-if="selectedDraft && selectedDraft.node_name === item.node_name && selectedDraft.vector_name === item.vector_name" class="badge success select-badge-animate">
                          Sélectionné
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Sélecteur de Mode d'Exécution (uniquement pour les projets judiciaires) -->
          <div v-if="props.projectData?.simulation_mode === 'legal'" class="run-mode-section">
            <span class="section-title">Mode d'Exécution Judiciaire</span>
            <span class="section-desc">Choisissez l'environnement dans lequel faire tourner la simulation de ce dossier.</span>
            
            <div class="mode-cards-grid">
              <div 
                class="mode-select-card" 
                :class="{ active: runMode === 'courtroom', 'legal-card-active': runMode === 'courtroom' }" 
                @click="runMode = 'courtroom'"
              >
                <div class="mode-icon">⚖️</div>
                <div class="mode-details">
                  <span class="mode-name">{{ $t('home.modeLegal') }}</span>
                  <span class="mode-description">Simulation itérative fermée (Monte-Carlo) entre {{ isCivil ? 'l\'Avocat du Demandeur, l\'Avocat de la Défense et le Juge pour déterminer le taux de rejet' : 'le Procureur, l\'Avocat de la Défense et le Juge pour déterminer le taux d\'acquittement' }}.</span>
                </div>
              </div>
              
              <div 
                class="mode-select-card" 
                :class="{ active: runMode === 'oasis' }" 
                @click="runMode = 'oasis'"
              >
                <div class="mode-icon">💬</div>
                <div class="mode-details">
                  <span class="mode-name">{{ $t('home.modeSocial') }}</span>
                  <span class="mode-description">Plateforme de débat public ouverte (Twitter, Reddit) avec possibilité d'injecter des communiqués ou des arguments en direct.</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 模拟轮数配置 - 只有 en cours / prête -->
          <div v-if="simulationConfig && (autoGeneratedRounds || isOasisOrSocial || !isOasisOrSocial)" class="rounds-config-section">
            <div class="rounds-header">
              <div class="header-left">
                <span class="section-title">{{ isOasisOrSocial ? 'Nombre de rounds' : 'Nombre d\'itérations' }}</span>
                <span class="section-desc">
                  {{ isOasisOrSocial 
                    ? 'Déterminez le nombre de rounds de débats pour observer la propagation de l\'opinion et les arguments.' 
                    : 'Déterminez le nombre de procès indépendants à simuler pour calculer le taux d\'acquittement ou de rejet.' }}
                </span>
              </div>
              <label class="switch-control">
                <input type="checkbox" v-model="useCustomRounds">
                <span class="switch-track"></span>
                <span class="switch-label">Personnaliser</span>
              </label>
            </div>
            
            <Transition name="fade" mode="out-in">
              <div v-if="useCustomRounds" class="rounds-content custom" key="custom">
                <div class="slider-display">
                  <div class="slider-main-value">
                    <span class="val-num">{{ customMaxRounds }}</span>
                    <span class="val-unit">{{ isOasisOrSocial ? 'rounds' : 'simulations' }}</span>
                  </div>
                  <div class="slider-meta-info" style="display: flex; flex-direction: column; gap: 6px; align-items: center;">
                    <span style="color: #1E293B; font-weight: 600;">
                      {{ isOasisOrSocial 
                        ? `Estimation : ${customMaxRounds} rounds` 
                        : `Estimation : ${customMaxRounds} simulations` }}
                    </span>
                    <span class="cost-badge" style="font-size: 11px; color: #334155; background: rgba(2, 132, 199, 0.08); border: 1px solid rgba(2, 132, 199, 0.25); padding: 2px 8px; border-radius: 4px; display: inline-flex; align-items: center; gap: 6px; width: fit-content; margin-top: 4px; font-weight: 500;">
                      💰 Coût estimé LLM ({{ simulationConfig?.llm_model || 'gpt-4o-mini' }}) : 
                      <strong style="color: #0284C7; font-weight: 700;">{{ estimatedCost === 0 ? 'Gratuit (Local)' : `${estimatedCost.toFixed(3)} USD` }}</strong>
                    </span>
                  </div>
                </div>

                <div class="range-wrapper">
                  <input 
                    type="range" 
                    v-model.number="customMaxRounds" 
                    :min="isOasisOrSocial ? 5 : 1" 
                    :max="isOasisOrSocial ? 25 : 50"
                    :step="1"
                    class="minimal-slider"
                    :style="{ '--percent': ((customMaxRounds - (isOasisOrSocial ? 5 : 1)) / ((isOasisOrSocial ? 25 : 50) - (isOasisOrSocial ? 5 : 1))) * 100 + '%' }"
                  />
                  <div class="range-marks">
                    <span>{{ isOasisOrSocial ? 5 : 1 }}</span>
                    <span 
                      v-if="!isOasisOrSocial"
                      class="mark-recommend" 
                      :class="{ active: customMaxRounds === recommendedRounds }"
                      @click="customMaxRounds = recommendedRounds"
                      :style="{ position: 'absolute', left: `calc(${(recommendedRounds - 1) / 49 * 100}% - 30px)` }"
                    >{{ `${recommendedRounds} itér. (Recommandé)` }}</span>
                    <span 
                      v-else
                      class="mark-recommend" 
                      :class="{ active: customMaxRounds === 10 }"
                      @click="customMaxRounds = 10"
                      :style="{ position: 'absolute', left: `calc(${(10 - 5) / 20 * 100}% - 30px)` }"
                    >10 rounds (Recommandé)</span>
                    <span>{{ isOasisOrSocial ? 25 : 50 }}</span>
                  </div>
                </div>
              </div>
              
              <div v-else class="rounds-content auto" key="auto">
                <div class="auto-info-card">
                  <div class="auto-value">
                    <span class="val-num">{{ isOasisOrSocial ? 10 : recommendedRounds }}</span>
                    <span class="val-unit">{{ isOasisOrSocial ? 'rounds' : 'simulations' }}</span>
                  </div>
                  <div class="auto-content">
                    <div class="auto-meta-row" style="display: flex; flex-direction: column; gap: 6px; align-items: flex-start;">
                      <span class="duration-badge">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        {{ isOasisOrSocial 
                          ? 'Recommandation : 10 rounds de débats' 
                          : `Recommandation selon le cas : ${recommendedRounds} simulations` }}
                      </span>
                      <span class="cost-badge" style="font-size: 11px; color: #334155; background: rgba(2, 132, 199, 0.08); border: 1px solid rgba(2, 132, 199, 0.25); padding: 2px 8px; border-radius: 4px; display: inline-flex; align-items: center; gap: 6px; font-weight: 500;">
                        💰 Coût estimé LLM ({{ simulationConfig?.llm_model || 'gpt-4o-mini' }}) : 
                        <strong style="color: #0284C7; font-weight: 700;">{{ estimatedCost === 0 ? 'Gratuit (Local)' : `${estimatedCost.toFixed(3)} USD` }}</strong>
                      </span>
                    </div>
                    <div class="auto-desc">
                      <p class="highlight-tip" @click="useCustomRounds = true">Personnaliser les paramètres ➝</p>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <div class="action-group dual">
            <button 
              class="action-btn secondary"
              @click="$emit('go-back')"
            >
              ← {{ $t('step2.backToGraphBuild') }}
            </button>
            <button 
              class="action-btn primary"
              :disabled="phase < 4"
              @click="handleStartSimulation"
            >
              {{ isOasisOrSocial ? 'Lancer la simulation' : 'Lancer le procès' }} ➝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Detail Modal -->
    <Transition name="modal">
      <div v-if="selectedProfile" class="profile-modal-overlay" @click.self="selectedProfile = null">
        <div class="profile-modal">
          <div class="modal-header">
            <div class="modal-header-info">
              <div class="modal-name-row" v-if="!isEditing">
                <span class="modal-realname">{{ selectedProfile.username }}</span>
                <span class="modal-username">@{{ selectedProfile.name }}</span>
              </div>
              <div class="modal-name-row-edit" v-else>
                <input class="edit-input name-edit" v-model="editForm.username" placeholder="Nom d'affichage">
                <input class="edit-input name-edit-handle" v-model="editForm.name" placeholder="Handle / ID">
              </div>
              <span class="modal-profession" v-if="!isEditing">{{ selectedProfile.profession }}</span>
              <input class="edit-input profession-edit" v-else v-model="editForm.profession" placeholder="Profession">
            </div>
            <div class="modal-header-actions">
              <button v-if="!isEditing" class="edit-mode-btn" @click="startEditing">
                ✏️ Modifier
              </button>
              <template v-else>
                <button class="save-profile-btn" :disabled="isSaving" @click="handleSaveProfile">
                  {{ isSaving ? 'Enregistrement...' : '✓ Enregistrer' }}
                </button>
                <button class="cancel-profile-btn" @click="cancelEditing">
                  ✕ Annuler
                </button>
              </template>
              <button class="close-btn" @click="selectedProfile = null">×</button>
            </div>
          </div>
          
          <div class="modal-body">
            <!-- Mode Édition -->
            <div v-if="isEditing" class="edit-profile-form">
              <!-- Informations de base -->
              <div class="form-grid">
                <div class="form-item">
                  <label class="form-label">Âge</label>
                  <input type="number" class="edit-input" v-model.number="editForm.age">
                </div>
                <div class="form-item">
                  <label class="form-label">Genre</label>
                  <select class="edit-select" v-model="editForm.gender">
                    <option value="male">Homme (male)</option>
                    <option value="female">Femme (female)</option>
                    <option value="other">Autre (other)</option>
                  </select>
                </div>
                <div class="form-item">
                  <label class="form-label">Pays</label>
                  <input type="text" class="edit-input" v-model="editForm.country">
                </div>
                <div class="form-item">
                  <label class="form-label">MBTI</label>
                  <input type="text" class="edit-input" v-model="editForm.mbti">
                </div>
              </div>

              <!-- Biographie & Persona -->
              <div class="form-section">
                <label class="form-label">Biographie (bio)</label>
                <textarea class="edit-textarea bio-textarea" v-model="editForm.bio" placeholder="Biographie..."></textarea>
              </div>

              <div class="form-section">
                <label class="form-label">Persona (Profil cognitif détaillé)</label>
                <textarea class="edit-textarea persona-textarea" v-model="editForm.persona" placeholder="Persona..."></textarea>
              </div>

              <!-- Intérêts -->
              <div class="form-section">
                <label class="form-label">Sujets d'intérêt (séparés par des virgules)</label>
                <input type="text" class="edit-input" :value="editForm.interested_topics.join(', ')" @input="editForm.interested_topics = $event.target.value.split(',').map(s => s.trim()).filter(Boolean)">
              </div>

              <!-- Paramètres Comportementaux (si configuration disponible) -->
              <div v-if="simulationConfig?.agent_configs?.some(a => a.agent_id === selectedProfile.user_id)" class="behavioral-parameters-section">
                <span class="section-label">Paramètres Comportementaux de Simulation</span>
                
                <div class="form-grid behavior-grid">
                  <div class="form-item">
                    <label class="form-label">Stance (Attitude)</label>
                    <select class="edit-select" v-model="editForm.stance">
                      <option value="supportive">Soutien (supportive)</option>
                      <option value="opposing">Opposant (opposing)</option>
                      <option value="neutral">Neutre (neutral)</option>
                      <option value="observer">Observateur (observer)</option>
                    </select>
                  </div>
                  <div class="form-item">
                    <label class="form-label">Poids d'influence</label>
                    <input type="number" step="0.1" class="edit-input" v-model.number="editForm.influence_weight">
                  </div>
                  <div class="form-item">
                    <label class="form-label">Niveau d'activité (0-1)</label>
                    <input type="number" step="0.05" min="0" max="1" class="edit-input" v-model.number="editForm.activity_level">
                  </div>
                  <div class="form-item">
                    <label class="form-label">Biais d'opinion (-1 à 1)</label>
                    <input type="number" step="0.1" min="-1" max="1" class="edit-input" v-model.number="editForm.sentiment_bias">
                  </div>
                  <div class="form-item">
                    <label class="form-label">Posts / heure</label>
                    <input type="number" step="0.1" min="0" class="edit-input" v-model.number="editForm.posts_per_hour">
                  </div>
                  <div class="form-item">
                    <label class="form-label">Comments / heure</label>
                    <input type="number" step="0.1" min="0" class="edit-input" v-model.number="editForm.comments_per_hour">
                  </div>
                </div>
              </div>
            </div>

            <!-- Mode Lecture Seule (Original) -->
            <div v-else>
              <!-- 基本信息 -->
              <div class="modal-info-grid">
                <div class="info-item">
                  <span class="info-label">{{ $t('step2.profileModalAge') }}</span>
                  <span class="info-value">{{ selectedProfile.age || '-' }} {{ $t('step2.yearsOld') }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">{{ $t('step2.profileModalGender') }}</span>
                  <span class="info-value">{{ { male: $t('step2.genderMale'), female: $t('step2.genderFemale'), other: $t('step2.genderOther') }[selectedProfile.gender] || selectedProfile.gender }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">{{ $t('step2.profileModalCountry') }}</span>
                  <span class="info-value">{{ selectedProfile.country || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">
                    {{ $t('step2.profileModalMbti') }}
                    <span class="info-tooltip-container">
                      <span class="info-trigger-i">ⓘ</span>
                      <span class="info-tooltip-bubble">
                        <strong>MBTI apparent :</strong> Décrit le style cognitif et comportemental du jumeau numérique dans la simulation.<br><br>
                        <strong>Lettres clés :</strong><br>
                        • <strong>I / E</strong> : Introversion (calme, réfléchi) / Extraversion (dynamique, expressif)<br>
                        • <strong>S / N</strong> : Sensation (axé sur les faits et preuves) / Intuition (axé sur les théories et visions)<br>
                        • <strong>T / F</strong> : Pensée (logique objective, règles) / Sentiment (empathie, valeurs)<br>
                        • <strong>J / P</strong> : Jugement (méthodique, structuré) / Perception (adaptable, flexible)<br><br>
                        <strong>Profils typiques :</strong><br>
                        • <strong>ISTJ</strong> (Le Juge/Inspecteur) : Strict, factuel, respecte la procédure et la lettre du contrat.<br>
                        • <strong>ENTJ</strong> (L'Avocat Déterminé) : Stratège, logique, fonceur, axé sur la persuasion.
                      </span>
                    </span>
                  </span>
                  <span class="info-value mbti">{{ selectedProfile.mbti || '-' }}</span>
                </div>
              </div>

              <!-- 简介 -->
              <div class="modal-section">
                <span class="section-label">{{ $t('step2.profileModalBio') }}</span>
                <p class="section-bio">{{ selectedProfile.bio || $t('step2.noBio') }}</p>
              </div>

              <!-- 关注话题 -->
              <div class="modal-section" v-if="selectedProfile.interested_topics?.length">
                <span class="section-label">{{ $t('step2.profileModalTopics') }}</span>
                <div class="topics-grid">
                  <span 
                    v-for="topic in selectedProfile.interested_topics" 
                    :key="topic" 
                    class="topic-item"
                  >{{ topic }}</span>
                </div>
              </div>

              <!-- 详细人设 -->
              <div class="modal-section" v-if="selectedProfile.persona">
                <span class="section-label">{{ $t('step2.profileModalPersona') }}</span>
                
                <!-- 人设维度概览 -->
                <div class="persona-dimensions">
                  <div class="dimension-card">
                    <span class="dim-title">{{ $t('step2.personaDimExperience') }}</span>
                    <span class="dim-desc">{{ $t('step2.personaDimExperienceDesc') }}</span>
                  </div>
                  <div class="dimension-card">
                    <span class="dim-title">{{ $t('step2.personaDimBehavior') }}</span>
                    <span class="dim-desc">{{ $t('step2.personaDimBehaviorDesc') }}</span>
                  </div>
                  <div class="dimension-card">
                    <span class="dim-title">{{ $t('step2.personaDimMemory') }}</span>
                    <span class="dim-desc">{{ $t('step2.personaDimMemoryDesc') }}</span>
                  </div>
                  <div class="dimension-card">
                    <span class="dim-title">{{ $t('step2.personaDimSocial') }}</span>
                    <span class="dim-desc">{{ $t('step2.personaDimSocialDesc') }}</span>
                  </div>
                </div>

                <div class="persona-content">
                  <p class="section-persona">{{ selectedProfile.persona }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Typewriter Draft Modal -->
    <Transition name="modal">
      <div v-if="showDraftModal" class="legal-draft-modal-overlay" @click.self="showDraftModal = false">
        <div class="legal-draft-modal">
          <div class="modal-header">
            <div class="modal-header-info">
              <span class="modal-realname">Projet de document juridique</span>
              <span class="modal-username">{{ selectedVector?.vector_name }}</span>
            </div>
            <div class="modal-header-actions">
              <button 
                v-if="draftText && !draftLoading" 
                class="save-profile-btn" 
                @click="selectDraftForSimulation"
                style="background-color: #16A34A;"
              >
                {{ selectedDraft?.text === draftText ? '✓ Sélectionné' : '✓ Sélectionner pour le procès' }}
              </button>
              <button class="save-profile-btn" @click="copyDraftText" :disabled="draftLoading">
                📋 Copier
              </button>
              <button class="cancel-profile-btn" @click="showDraftModal = false">
                Fermer
              </button>
            </div>
          </div>
          <div class="modal-body draft-body">
            <div v-if="draftLoading && !draftText" class="draft-loader">
              <span class="spinner-icon">⏳</span>
              <p>Rédaction du document juridique en cours...</p>
            </div>
            <pre v-else class="typewriter-content">{{ draftText }}<span v-if="draftLoading" class="cursor">|</span></pre>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Expanded Matrix Modal -->
    <Transition name="modal">
      <div v-if="showExpandedMatrix" class="large-modal-overlay" @click.self="showExpandedMatrix = false">
        <div class="large-modal glassmorphic-modal">
          <div class="modal-header gold-border-bottom">
            <div class="modal-header-info">
              <span class="modal-realname font-serif-gold">Matrice d'Anticipation Stratégique</span>
              <span class="modal-username">Vue élargie pour le camp : {{ clientSide === 'defense' ? 'Défense' : 'Poursuite / Demandeur' }}</span>
            </div>
            <div class="modal-header-actions">
              <button class="cancel-profile-btn gold-border-btn" @click="showExpandedMatrix = false">
                ✕ Fermer la vue
              </button>
              <button class="close-btn" @click="showExpandedMatrix = false">×</button>
            </div>
          </div>
          <div class="modal-body large-body">
            <p class="matrix-description-text">
              Cette vue panoramique vous permet d'analyser en détail les lignes de force et les failles du dossier. Utilisez les boutons d'actions pour étudier chaque élément ou générer des projets de requêtes.
            </p>
            <div class="table-container large-table-container">
              <table class="radar-table large-radar-table">
                <thead>
                  <tr>
                    <th style="width: 15%">Élément Clé</th>
                    <th style="width: 20%">Ligne de Force / Faille</th>
                    <th style="width: 15%">Impact Prédit</th>
                    <th style="width: 35%">Feuille de Route (Plan de match)</th>
                    <th style="width: 15%" class="actions-col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in radarResults" :key="idx" :class="{ 'row-selected': selectedDraft && selectedDraft.node_name === item.node_name && selectedDraft.vector_name === item.vector_name }">
                    <td class="node-cell"><strong>{{ item.node_name }}</strong></td>
                    <td class="vector-cell"><span class="vector-badge">{{ item.vector_name }}</span></td>
                    <td class="impact-cell">
                      <div class="impact-value-wrapper">
                        <span class="impact-text">{{ item.impact }}</span>
                        <div class="progress-bar-container">
                          <div class="progress-bar-fill" :style="{ width: (item.impact_value || 0) + '%' }"></div>
                        </div>
                      </div>
                    </td>
                    <td class="plan-cell plan-cell-expanded">{{ item.match_plan }}</td>
                    <td class="action-cell">
                      <button class="detail-btn" @click="openOpportunityDetail(item)" title="Voir la fiche détaillée">
                        🔍 Détails
                      </button>
                      <button class="draft-btn" @click="triggerDraftRequest(item)">
                        📄 Requête
                      </button>
                      <span v-if="selectedDraft && selectedDraft.node_name === item.node_name && selectedDraft.vector_name === item.vector_name" class="badge success select-badge-animate">
                        Sélectionné
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Opportunity Detail Modal -->
    <Transition name="modal">
      <div v-if="selectedOpportunity" class="detail-modal-overlay" @click.self="selectedOpportunity = null">
        <div class="detail-modal glassmorphic-modal">
          <div class="modal-header gold-border-bottom">
            <div class="modal-header-info">
              <span class="modal-realname font-serif-gold">Fiche d'Opportunité Tactique</span>
              <span class="modal-username">Analyse sémantique approfondie</span>
            </div>
            <div class="modal-header-actions">
              <button class="close-btn" @click="selectedOpportunity = null">×</button>
            </div>
          </div>
          <div class="modal-body detail-body-content">
            <!-- Header Card for Node & Vector -->
            <div class="detail-card-header-pane">
              <div class="detail-meta-group">
                <span class="detail-label-tag">ÉLÉMENT CLÉ</span>
                <span class="detail-value-highlight">{{ selectedOpportunity.node_name }}</span>
              </div>
              <div class="detail-meta-group">
                <span class="detail-label-tag">VECTEUR ANALYSÉ</span>
                <span class="vector-badge large-vector-badge">{{ selectedOpportunity.vector_name }}</span>
              </div>
            </div>

            <!-- Impact Section -->
            <div class="detail-impact-card">
              <div class="impact-radial-indicator">
                <span class="impact-radial-text">{{ selectedOpportunity.impact }}</span>
                <div class="detail-progress-container">
                  <div class="detail-progress-fill" :style="{ width: (selectedOpportunity.impact_value || 0) + '%' }"></div>
                </div>
              </div>
              <div class="impact-explanation">
                <span class="detail-section-title">Impact Prédit sur le Procès</span>
                <p class="detail-section-desc">Cette estimation mesure le déplacement de probabilité de gain ou d'acquittement si l'argument est correctement articulé devant le tribunal.</p>
              </div>
            </div>

            <!-- Match Plan (Feuille de Route) -->
            <div class="detail-plan-section">
              <span class="detail-section-label-gold">Feuille de Route Tactique (Plan de match)</span>
              <div class="detail-plan-card-body">
                <p class="detail-plan-text">{{ selectedOpportunity.match_plan }}</p>
              </div>
            </div>

            <!-- Selection Status Info -->
            <div class="detail-status-section">
              <div v-if="selectedDraft && selectedDraft.node_name === selectedOpportunity.node_name && selectedDraft.vector_name === selectedOpportunity.vector_name" class="status-active-badge">
                <span class="status-icon">✓</span>
                <div class="status-text-wrapper">
                  <span class="status-title">Stimulus Actif</span>
                  <span class="status-desc">Ce plan de match est actuellement sélectionné et sera injecté au démarrage du procès.</span>
                </div>
              </div>
              <div v-else class="status-inactive-badge">
                <span class="status-icon">ℹ️</span>
                <div class="status-text-wrapper">
                  <span class="status-title">Non Sélectionné</span>
                  <span class="status-desc">Pour activer cette tactique, générez la requête ci-dessous et validez sa sélection.</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom Actions Bar -->
          <div class="modal-footer-actions gold-border-top">
            <button class="cancel-profile-btn" @click="selectedOpportunity = null">
              Fermer
            </button>
            
            <button 
              v-if="selectedDraft && selectedDraft.node_name === selectedOpportunity.node_name && selectedDraft.vector_name === selectedOpportunity.vector_name"
              class="draft-btn-view"
              @click="triggerDraftRequest(selectedOpportunity)"
            >
              📄 Consulter la Requête
            </button>
            <button 
              v-else
              class="draft-btn-generate pulsing-gold-btn" 
              @click="triggerDraftRequest(selectedOpportunity)"
            >
              ✨ Rédiger la Requête & Sélectionner
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{ simulationId || 'NO_SIMULATION' }}</span>
      </div>
      <div class="log-content" ref="logContent">
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
import { useI18n } from 'vue-i18n'
import {
  prepareSimulation,
  getPrepareStatus,
  getSimulationProfilesRealtime,
  getSimulationConfig,
  getSimulationConfigRealtime,
  updateSimulationProfile,
  runSensitivityAnalysis,
  generateLegalRequest,
  selectDraft,
  getRadarAnalysis
} from '../api/simulation'

const { t } = useI18n()

const props = defineProps({
  simulationId: String,  // 从父组件传入
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

// State
const phase = ref(0) // 0: 初始化, 1: 生成人设, 2: 生成配置, 3: 完成
const runMode = ref('courtroom') // courtroom or oasis
const clientSide = ref(props.projectData?.client_side || 'defense')

watch(() => props.projectData?.client_side, (newVal) => {
  if (newVal) {
    clientSide.value = newVal
  }
})
const taskId = ref(null)
const prepareProgress = ref(0)
const currentStage = ref('')
const progressMessage = ref('')
const profiles = ref([])
const entityTypes = ref([])
const expectedTotal = ref(null)
const simulationConfig = ref(null)

const isCivil = computed(() => {
  if (props.projectData?.simulation_mode !== 'legal') return false
  if (simulationConfig.value?.litigation_type === 'civil') return true
  if (simulationConfig.value?.litigation_type === 'criminal') return false
  return profiles.value.some(p => p.username && (p.username.toLowerCase().includes("demandeur") || p.username.toLowerCase().includes("défendeur")))
})

const isOasisOrSocial = computed(() => {
  return runMode.value === 'oasis' || props.projectData?.simulation_mode === 'social'
})

const selectedProfile = ref(null)
const showProfilesDetail = ref(true)

// Editing Profile States
const isEditing = ref(false)
const isSaving = ref(false)
const editForm = ref({
  name: '',
  username: '',
  profession: '',
  age: 30,
  gender: 'male',
  mbti: '',
  country: '',
  bio: '',
  persona: '',
  interested_topics: [],
  stance: 'neutral',
  influence_weight: 1.0,
  activity_level: 0.5,
  posts_per_hour: 1.0,
  comments_per_hour: 2.0,
  sentiment_bias: 0.0
})

// Tactical Radar State
const radarResults = ref(null)
const radarLoading = ref(false)
const draftText = ref('')
const draftLoading = ref(false)
const showDraftModal = ref(false)
const selectedVector = ref(null)
const selectedDraft = ref(null)

// State for Expanded Matrix and Opportunity Details
const showExpandedMatrix = ref(false)
const selectedOpportunity = ref(null)

const openOpportunityDetail = (opportunity) => {
  selectedOpportunity.value = opportunity
}

const triggerRadarAnalysis = async () => {
  if (radarLoading.value) return
  radarLoading.value = true
  radarResults.value = null
  try {
    const res = await runSensitivityAnalysis({
      project_id: props.projectData?.project_id,
      client_side: clientSide.value,
      simulation_id: props.simulationId
    })
    if (res.data?.success) {
      radarResults.value = res.data.data
    } else if (res.success) {
      radarResults.value = res.data
    } else {
      radarResults.value = res.data || []
    }
    addLog(`[Radar Tactique] Analyse de sensibilité terminée pour le camp : ${clientSide.value === 'defense' ? 'Défense' : 'Poursuite/Demandeur'}.`)
  } catch (err) {
    console.error(err)
    addLog(`[Radar Tactique] Erreur lors de l'analyse : ${err.message || err}`)
  } finally {
    radarLoading.value = false
  }
}

const triggerDraftRequest = async (opportunity) => {
  if (draftLoading.value) return
  selectedVector.value = opportunity
  draftLoading.value = true
  draftText.value = ""
  showDraftModal.value = true
  
  try {
    const res = await generateLegalRequest({
      project_id: props.projectData?.project_id,
      client_side: clientSide.value,
      node_name: opportunity.node_name,
      vector_name: opportunity.vector_name,
      request_type: opportunity.request_type || 'requete',
      simulation_id: props.simulationId
    })
    
    const generated = res.data?.draft || res.data?.data?.draft || res.draft || ""
    
    let i = 0
    const speed = 4
    const typeWriter = () => {
      if (i < generated.length) {
        draftText.value += generated.charAt(i)
        i++
        setTimeout(typeWriter, speed)
      } else {
        draftLoading.value = false
      }
    }
    typeWriter()
    
    addLog(`[Radar Tactique] Projet de document juridique généré pour '${opportunity.node_name}'.`)
  } catch (err) {
    console.error(err)
    draftText.value = "Erreur lors de la génération du document : " + (err.message || err)
    draftLoading.value = false
    addLog(`[Radar Tactique] Erreur lors de la génération du projet de requête : ${err.message || err}`)
  }
}

const copyDraftText = () => {
  navigator.clipboard.writeText(draftText.value)
  alert("Projet de requête copié dans le presse-papiers.")
}

const loadSavedRadarAnalysis = async () => {
  if (!props.simulationId) return
  try {
    const res = await getRadarAnalysis(props.simulationId)
    if (res.data?.success || res.success) {
      const savedData = res.data?.data || res.data
      if (savedData && savedData.selected_draft) {
        selectedDraft.value = savedData.selected_draft
      }
      
      const currentSideResults = savedData ? savedData[clientSide.value] : null
      if (currentSideResults && currentSideResults.length > 0) {
        radarResults.value = currentSideResults
      } else {
        radarResults.value = null
      }
    }
  } catch (err) {
    console.error("Failed to load saved radar analysis:", err)
  }
}

watch(clientSide, async () => {
  radarResults.value = null
  if (selectedDraft.value && selectedDraft.value.client_side !== clientSide.value) {
    selectedDraft.value = null
  }
  await loadSavedRadarAnalysis()
})

const selectDraftForSimulation = async () => {
  if (!draftText.value) return
  const draftObj = {
    node_name: selectedVector.value.node_name,
    vector_name: selectedVector.value.vector_name,
    text: draftText.value,
    client_side: clientSide.value
  }
  selectedDraft.value = draftObj
  
  if (props.simulationId) {
    try {
      await selectDraft(props.simulationId, draftObj)
      addLog(`[Radar Tactique] Sélection enregistrée dans le dossier de simulation.`)
    } catch (err) {
      console.error("Failed to save draft selection:", err)
      addLog(`[Radar Tactique] Avertissement : Impossible d'enregistrer la sélection sur le serveur.`)
    }
  }

  addLog(`[Radar Tactique] Requête pour '${selectedVector.value.node_name}' sélectionnée et intégrée comme stimulus initial pour la simulation.`)
  showDraftModal.value = false
  if (selectedOpportunity.value) {
    selectedOpportunity.value = null
  }
}

// 日志去重：记录上一次输出的关键信息
let lastLoggedMessage = ''
let lastLoggedProfileCount = 0
let lastLoggedConfigStage = ''

// 模拟轮数配置
const useCustomRounds = ref(false) // 默认使用自动配置轮数
const customMaxRounds = ref(40)   // 默认推荐40轮

// Recommandation d'itérations basée sur la complexité du cas (GraphRAG ou description)
const recommendedRounds = computed(() => {
  if (props.projectData?.simulation_mode !== 'legal') return 40;
  
  // Utiliser la complexité du graphe de connaissances si disponible
  const nodeCount = props.graphData?.nodes?.length || 0;
  if (nodeCount > 0) {
    if (nodeCount >= 15) return 45;
    if (nodeCount >= 10) return 35;
    if (nodeCount >= 5) return 25;
    return 15;
  }
  
  // Alternative : se baser sur la longueur du scénario de l'affaire
  const reqLength = props.projectData?.simulation_requirement?.length || 0;
  if (reqLength > 500) return 40;
  if (reqLength > 250) return 30;
  return 20;
})

// Mettre à jour la valeur par défaut lors du chargement
watch(recommendedRounds, (newVal) => {
  if (newVal && runMode.value === 'courtroom') {
    customMaxRounds.value = newVal
  }
}, { immediate: true })

watch(runMode, (newVal) => {
  if (props.projectData?.simulation_mode === 'legal') {
    if (newVal === 'courtroom') {
      customMaxRounds.value = recommendedRounds.value
    } else {
      customMaxRounds.value = 10
    }
  }
})

// Watch stage to update phase
watch(currentStage, (newStage) => {
  if (newStage === '生成Agent人设' || newStage === 'generating_profiles') {
    phase.value = 1
  } else if (newStage === '生成模拟配置' || newStage === 'generating_config') {
    phase.value = 2
    // 进入配置生成阶段，开始轮询配置
    if (!configTimer) {
      addLog(t('log.startGeneratingConfig'))
      startConfigPolling()
    }
  } else if (newStage === '准备模拟脚本' || newStage === 'copying_scripts') {
    phase.value = 2 // 仍属于配置阶段
  }
})

// 从配置中计算自动生成的轮数（不使用硬编码默认值）
const autoGeneratedRounds = computed(() => {
  if (!simulationConfig.value?.time_config) {
    return null // 配置未生成时返回 null
  }
  const totalHours = simulationConfig.value.time_config.total_simulation_hours
  const minutesPerRound = simulationConfig.value.time_config.minutes_per_round
  if (!totalHours || !minutesPerRound) {
    return null // 配置数据不完整时返回 null
  }
  const calculatedRounds = Math.floor((totalHours * 60) / minutesPerRound)
  // 确保最大轮数不小于40（推荐值），避免滑动条范围异常
  return Math.max(calculatedRounds, 40)
})

const MODEL_PRICES = {
  "gpt-4o-mini": { input: 0.15 / 1000000, output: 0.60 / 1000000 },
  "gpt-4o": { input: 2.50 / 1000000, output: 10.00 / 1000000 },
  "gpt-4-turbo": { input: 10.00 / 1000000, output: 30.00 / 1000000 },
  "gpt-3.5-turbo": { input: 0.50 / 1000000, output: 1.50 / 1000000 },
  "claude-3-5-sonnet": { input: 3.00 / 1000000, output: 15.00 / 1000000 },
  "claude-3-haiku": { input: 0.25 / 1000000, output: 1.25 / 1000000 },
  "gemini-1.5-flash": { input: 0.075 / 1000000, output: 0.30 / 1000000 },
  "gemini-1.5-pro": { input: 1.25 / 1000000, output: 5.00 / 1000000 },
}

const estimatedCost = computed(() => {
  if (!simulationConfig.value) return 0
  
  const modelName = simulationConfig.value.llm_model || 'gpt-4o-mini'
  const baseUrl = simulationConfig.value.llm_base_url || ''
  
  // Check if it is a local model
  const isLocal = baseUrl.includes('localhost') || baseUrl.includes('127.0.0.1') || baseUrl.toLowerCase().includes('local')
  if (isLocal) return 0
  
  // Find prices
  let rates = { input: 0.15 / 1000000, output: 0.60 / 1000000 } // gpt-4o-mini default
  const modelLower = modelName.toLowerCase()
  for (const [key, val] of Object.entries(MODEL_PRICES)) {
    if (modelLower.includes(key.toLowerCase())) {
      rates = val
      break
    }
  }
  
  const rounds = useCustomRounds.value ? customMaxRounds.value : (props.projectData?.simulation_mode === 'legal' && runMode.value === 'courtroom' ? recommendedRounds.value : (autoGeneratedRounds.value || 10))
  
  if (props.projectData?.simulation_mode === 'legal' && runMode.value === 'courtroom') {
    // Courtroom mode: 1 simulation = ~18,000 input tokens, ~2,400 output tokens
    const totalInput = rounds * 18000
    const totalOutput = rounds * 2400
    return (totalInput * rates.input) + (totalOutput * rates.output)
  } else {
    // Oasis/Parallel mode: 1 round = ~30,000 input tokens, ~4,500 output tokens
    const totalInput = rounds * 30000
    const totalOutput = rounds * 4500
    return (totalInput * rates.input) + (totalOutput * rates.output)
  }
})

// Polling timer
let pollTimer = null
let profilesTimer = null
let configTimer = null

// Computed
const displayProfiles = computed(() => {
  if (showProfilesDetail.value) {
    return profiles.value
  }
  return profiles.value.slice(0, 6)
})

// 根据agent_id获取对应的username
const getAgentUsername = (agentId) => {
  if (profiles.value && profiles.value.length > agentId && agentId >= 0) {
    const profile = profiles.value[agentId]
    return profile?.username || `agent_${agentId}`
  }
  return `agent_${agentId}`
}

// 计算所有人设的关联话题总数
const totalTopicsCount = computed(() => {
  return profiles.value.reduce((sum, p) => {
    return sum + (p.interested_topics?.length || 0)
  }, 0)
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// 处理开始模拟按钮点击
const handleStartSimulation = () => {
  // 构建传递给父组件 der param
  const params = {
    runMode: runMode.value,
    selectedDraft: selectedDraft.value ? selectedDraft.value.text : null
  }
  
  if (props.projectData?.simulation_mode === 'legal') {
    params.clientSide = clientSide.value
    if (runMode.value === 'courtroom') {
      params.maxRounds = useCustomRounds.value ? customMaxRounds.value : recommendedRounds.value
      addLog(`Démarrage du procès d'audience avec ${params.maxRounds} simulations (Monte-Carlo).`)
    } else {
      params.maxRounds = useCustomRounds.value ? customMaxRounds.value : 10
      addLog(`Démarrage de la Simulation Publique Interactive avec ${params.maxRounds} rounds de débat public.`)
    }
  } else {
    params.runMode = 'oasis'
    if (useCustomRounds.value) {
      // 用户自定义轮数，传递 max_rounds 参数
      params.maxRounds = customMaxRounds.value
      addLog(t('log.startSimCustomRounds', { rounds: customMaxRounds.value }))
    } else {
      // 用户选择保持自动生成的轮数，不传递 max_rounds 参数
      addLog(t('log.startSimAutoRounds', { rounds: autoGeneratedRounds.value || 10 }))
    }
  }
  
  emit('next-step', params)
}

const truncateBio = (bio) => {
  if (bio.length > 80) {
    return bio.substring(0, 80) + '...'
  }
  return bio
}

const selectProfile = (profile) => {
  selectedProfile.value = profile
  isEditing.value = false
}

const startEditing = () => {
  const profile = selectedProfile.value
  if (!profile) return
  
  // Find associated agent config in simulationConfig
  const agentConfig = simulationConfig.value?.agent_configs?.find(
    a => a.agent_id === profile.user_id
  )
  
  editForm.value = {
    name: profile.name || '',
    username: profile.username || '',
    profession: profile.profession || '',
    age: profile.age || 30,
    gender: profile.gender || 'male',
    mbti: profile.mbti || '',
    country: profile.country || '',
    bio: profile.bio || '',
    persona: profile.persona || '',
    interested_topics: profile.interested_topics ? [...profile.interested_topics] : [],
    // Simulation Parameters:
    stance: agentConfig?.stance || 'neutral',
    influence_weight: agentConfig?.influence_weight || 1.0,
    activity_level: agentConfig?.activity_level || 0.5,
    posts_per_hour: agentConfig?.posts_per_hour || 1.0,
    comments_per_hour: agentConfig?.comments_per_hour || 2.0,
    sentiment_bias: agentConfig?.sentiment_bias || 0.0
  }
  
  isEditing.value = true
}

const cancelEditing = () => {
  isEditing.value = false
}

const handleSaveProfile = async () => {
  if (!props.simulationId || !selectedProfile.value) return
  
  isSaving.value = true
  try {
    const payload = {
      user_id: selectedProfile.value.user_id,
      ...editForm.value
    }
    
    const res = await updateSimulationProfile(props.simulationId, payload)
    if (res.success) {
      addLog(`Profil de l'acteur @${editForm.value.username} mis à jour avec succès.`)
      
      // Update local profiles list
      const idx = profiles.value.findIndex(p => p.user_id === selectedProfile.value.user_id)
      if (idx !== -1) {
        profiles.value[idx] = {
          ...profiles.value[idx],
          name: editForm.value.name,
          username: editForm.value.username,
          profession: editForm.value.profession,
          age: editForm.value.age,
          gender: editForm.value.gender,
          mbti: editForm.value.mbti,
          country: editForm.value.country,
          bio: editForm.value.bio,
          persona: editForm.value.persona,
          interested_topics: editForm.value.interested_topics
        }
        
        // Update selectedProfile to reflect changes
        selectedProfile.value = profiles.value[idx]
      }
      
      // Update local simulationConfig agent configs
      if (simulationConfig.value && simulationConfig.value.agent_configs) {
        const aIdx = simulationConfig.value.agent_configs.findIndex(
          a => a.agent_id === selectedProfile.value.user_id
        )
        if (aIdx !== -1) {
          const agent = simulationConfig.value.agent_configs[aIdx]
          agent.entity_name = editForm.value.name
          agent.stance = editForm.value.stance
          agent.influence_weight = parseFloat(editForm.value.influence_weight)
          agent.activity_level = parseFloat(editForm.value.activity_level)
          agent.posts_per_hour = parseFloat(editForm.value.posts_per_hour)
          agent.comments_per_hour = parseFloat(editForm.value.comments_per_hour)
          agent.sentiment_bias = parseFloat(editForm.value.sentiment_bias)
        }
      }
      
      isEditing.value = false
    } else {
      addLog(`Erreur lors de la mise à jour : ${res.error || 'Erreur inconnue'}`)
    }
  } catch (err) {
    addLog(`Échec de la mise à jour : ${err.message}`)
  } finally {
    isSaving.value = false
  }
}

// 自动开始准备模拟
const startPrepareSimulation = async () => {
  if (!props.simulationId) {
    addLog(t('log.errorMissingSimId'))
    emit('update-status', 'error')
    return
  }
  
  // 标记第一步完成，开始第二步
  phase.value = 1
  addLog(t('log.simInstanceCreated', { id: props.simulationId }))
  addLog(t('log.preparingSimEnv'))
  emit('update-status', 'processing')
  
  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      use_llm_for_profiles: true,
      parallel_profile_count: 5,
      run_mode: runMode.value
    })
    
    if (res.success && res.data) {
      if (res.data.already_prepared) {
        addLog(t('log.detectedExistingPrep'))
        await loadPreparedData()
        return
      }
      
      taskId.value = res.data.task_id
      addLog(t('log.prepareTaskStarted'))
      addLog(t('log.prepareTaskId', { taskId: res.data.task_id }))
      
      // 立即设置预期Agent总数（从prepare接口返回值获取）
      if (res.data.expected_entities_count) {
        expectedTotal.value = res.data.expected_entities_count
        addLog(t('log.zepEntitiesFound', { count: res.data.expected_entities_count }))
        if (res.data.entity_types && res.data.entity_types.length > 0) {
          addLog(t('log.entityTypes', { types: res.data.entity_types.join(', ') }))
        }
      }
      
      addLog(t('log.startPollingProgress'))
      // 开始轮询进度
      startPolling()
      // 开始实时获取 Profiles
      startProfilesPolling()
    } else {
      addLog(t('log.prepareFailed', { error: res.error || t('common.unknownError') }))
      emit('update-status', 'error')
    }
  } catch (err) {
    addLog(t('log.prepareException', { error: err.message }))
    emit('update-status', 'error')
  }
}

const startPolling = () => {
  pollTimer = setInterval(pollPrepareStatus, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const startProfilesPolling = () => {
  profilesTimer = setInterval(fetchProfilesRealtime, 3000)
}

const stopProfilesPolling = () => {
  if (profilesTimer) {
    clearInterval(profilesTimer)
    profilesTimer = null
  }
}

const pollPrepareStatus = async () => {
  if (!taskId.value && !props.simulationId) return
  
  try {
    const res = await getPrepareStatus({
      task_id: taskId.value,
      simulation_id: props.simulationId
    })
    
    if (res.success && res.data) {
      const data = res.data
      
      // 更新进度
      prepareProgress.value = data.progress || 0
      progressMessage.value = data.message || ''
      
      // 解析阶段信息并输出详细日志
      if (data.progress_detail) {
        currentStage.value = data.progress_detail.current_stage_name || ''
        
        // 输出详细进度日志（避免重复）
        const detail = data.progress_detail
        const logKey = `${detail.current_stage}-${detail.current_item}-${detail.total_items}`
        if (logKey !== lastLoggedMessage && detail.item_description) {
          lastLoggedMessage = logKey
          const stageInfo = `[${detail.stage_index}/${detail.total_stages}]`
          if (detail.total_items > 0) {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.current_item}/${detail.total_items} - ${detail.item_description}`)
          } else {
            addLog(`${stageInfo} ${detail.current_stage_name}: ${detail.item_description}`)
          }
        }
      } else if (data.message) {
        // 从消息中提取阶段
        const match = data.message.match(/\[(\d+)\/(\d+)\]\s*([^:]+)/)
        if (match) {
          currentStage.value = match[3].trim()
        }
        // 输出消息日志（避免重复）
        if (data.message !== lastLoggedMessage) {
          lastLoggedMessage = data.message
          addLog(data.message)
        }
      }
      
      // 检查是否完成
      if (data.status === 'completed' || data.status === 'ready' || data.already_prepared) {
        addLog(t('log.prepareComplete'))
        stopPolling()
        stopProfilesPolling()
        await loadPreparedData()
      } else if (data.status === 'failed') {
        addLog(t('log.prepareFailedWithError', { error: data.error || t('common.unknownError') }))
        stopPolling()
        stopProfilesPolling()
      }
    }
  } catch (err) {
    console.warn('轮询状态失败:', err)
  }
}

const fetchProfilesRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    
    if (res.success && res.data) {
      const prevCount = profiles.value.length
      profiles.value = res.data.profiles || []
      // 只有当 API 返回有效值时才更新，避免覆盖已有的有效值
      if (res.data.total_expected) {
        expectedTotal.value = res.data.total_expected
      }
      
      // 提取实体类型
      const types = new Set()
      profiles.value.forEach(p => {
        if (p.entity_type) types.add(p.entity_type)
      })
      entityTypes.value = Array.from(types)
      
      // 输出 Profile 生成进度日志（仅当数量变化时）
      const currentCount = profiles.value.length
      if (currentCount > 0 && currentCount !== lastLoggedProfileCount) {
        lastLoggedProfileCount = currentCount
        const total = expectedTotal.value || '?'
        const latestProfile = profiles.value[currentCount - 1]
        const profileName = latestProfile?.name || latestProfile?.username || `Agent_${currentCount}`
        if (currentCount === 1) {
          addLog(t('log.startGeneratingAgentProfiles'))
        }
        addLog(t('log.agentProfile', { current: currentCount, total: total, name: profileName, profession: latestProfile?.profession || t('step2.unknownProfession') }))

        // 如果全部生成完成
        if (expectedTotal.value && currentCount >= expectedTotal.value) {
          addLog(t('log.allProfilesComplete', { count: currentCount }))
        }
      }
    }
  } catch (err) {
    console.warn('获取 Profiles 失败:', err)
  }
}

// 配置轮询
const startConfigPolling = () => {
  configTimer = setInterval(fetchConfigRealtime, 2000)
}

const stopConfigPolling = () => {
  if (configTimer) {
    clearInterval(configTimer)
    configTimer = null
  }
}

const fetchConfigRealtime = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    
    if (res.success && res.data) {
      const data = res.data
      
      // 输出配置生成阶段日志（避免重复）
      if (data.generation_stage && data.generation_stage !== lastLoggedConfigStage) {
        lastLoggedConfigStage = data.generation_stage
        if (data.generation_stage === 'generating_profiles') {
          addLog(t('log.generatingAgentProfileConfig'))
        } else if (data.generation_stage === 'generating_config') {
          addLog(t('log.generatingLLMConfig'))
        }
      }
      
      // 如果配置已生成
      if (data.config_generated && data.config) {
        simulationConfig.value = data.config
        addLog(t('log.configComplete'))

        // 显示详细配置摘要
        if (data.summary) {
          addLog(t('log.configSummaryAgents', { count: data.summary.total_agents }))
          addLog(t('log.configSummaryHours', { hours: data.summary.simulation_hours }))
          addLog(t('log.configSummaryPosts', { count: data.summary.initial_posts_count }))
          addLog(t('log.configSummaryTopics', { count: data.summary.hot_topics_count }))
          addLog(t('log.configSummaryPlatforms', { twitter: data.summary.has_twitter_config ? '✓' : '✗', reddit: data.summary.has_reddit_config ? '✓' : '✗' }))
        }
        
        // 显示时间配置详情
        if (data.config.time_config) {
          const tc = data.config.time_config
          addLog(t('log.timeConfigDetail', { minutes: tc.minutes_per_round, rounds: Math.floor((tc.total_simulation_hours * 60) / tc.minutes_per_round) }))
        }
        
        // 显示事件配置
        if (data.config.event_config?.narrative_direction) {
          const narrative = data.config.event_config.narrative_direction
          addLog(t('log.narrativeDirection', { direction: narrative.length > 50 ? narrative.substring(0, 50) + '...' : narrative }))
        }
        
        stopConfigPolling()
        phase.value = 4
        addLog(t('log.envSetupComplete'))
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('获取 Config 失败:', err)
  }
}

const loadPreparedData = async () => {
  phase.value = 2
  addLog(t('log.loadingExistingConfig'))

  // 最后获取一次 Profiles
  await fetchProfilesRealtime()
  addLog(t('log.loadedAgentProfiles', { count: profiles.value.length }))

  // Charger l'analyse du radar tactique enregistrée
  await loadSavedRadarAnalysis()

  // 获取配置（使用实时接口）
  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    if (res.success && res.data) {
      if (res.data.config_generated && res.data.config) {
        simulationConfig.value = res.data.config
        addLog(t('log.configLoadSuccess'))

        // 显示详细配置摘要
        if (res.data.summary) {
          addLog(t('log.configSummaryAgents', { count: res.data.summary.total_agents }))
          addLog(t('log.configSummaryHours', { hours: res.data.summary.simulation_hours }))
          addLog(t('log.configSummaryPostsAlt', { count: res.data.summary.initial_posts_count }))
        }

        addLog(t('log.envSetupComplete'))
        phase.value = 4
        emit('update-status', 'completed')
      } else {
        // 配置尚未生成，开始轮询
        addLog(t('log.configGenerating'))
        startConfigPolling()
      }
    }
  } catch (err) {
    addLog(t('log.loadConfigFailed', { error: err.message }))
    emit('update-status', 'error')
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

const prepareStarted = ref(false)

const triggerPrepareSimulation = () => {
  if (prepareStarted.value) return
  prepareStarted.value = true
  
  if (props.projectData?.simulation_mode === 'social') {
    runMode.value = 'oasis'
  } else {
    runMode.value = 'courtroom'
  }
  
  startPrepareSimulation()
}

onMounted(() => {
  // 自动开始准备流程
  if (props.simulationId && props.projectData) {
    addLog(t('log.step2Init'))
    triggerPrepareSimulation()
  }
})

watch(() => props.projectData, (newVal) => {
  if (newVal && props.simulationId) {
    if (!prepareStarted.value) {
      addLog(t('log.step2Init'))
      triggerPrepareSimulation()
    }
  }
}, { immediate: true })

onUnmounted(() => {
  stopPolling()
  stopProfilesPolling()
  stopConfigPolling()
})
</script>

<style scoped>
.env-setup-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Step Card */
.step-card {
  background: #FFF;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  border: 1px solid #EAEAEA;
  transition: all 0.3s ease;
  position: relative;
}

.step-card.active {
  border-color: #FF5722;
  box-shadow: 0 4px 12px rgba(255, 87, 34, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #E0E0E0;
}

.step-card.active .step-num,
.step-card.completed .step-num {
  color: #000;
}

.step-title {
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.badge {
  font-size: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.success { background: #E8F5E9; color: #2E7D32; }
.badge.processing { background: #FF5722; color: #FFF; }
.badge.pending { background: #F5F5F5; color: #999; }
.badge.accent { background: #E3F2FD; color: #1565C0; }

.card-content {
  /* No extra padding - uses step-card's padding */
}

.api-note {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #999;
  margin-bottom: 8px;
}

.description {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 16px;
}

/* Action Section */
.action-section {
  margin-top: 16px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #000;
  color: #FFF;
}

.action-btn.primary:hover:not(:disabled) {
  opacity: 0.8;
}

.action-btn.secondary {
  background: #F5F5F5;
  color: #333;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #E5E5E5;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-group {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-group.dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.action-group.dual .action-btn {
  width: 100%;
}

/* Info Card */
.info-card {
  background: #F5F5F5;
  border-radius: 6px;
  padding: 16px;
  margin-top: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed #E0E0E0;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 12px;
  color: #666;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
}

.info-value.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  background: #F9F9F9;
  padding: 16px;
  border-radius: 6px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #000;
  font-family: 'JetBrains Mono', monospace;
}

.stat-label {
  font-size: 9px;
  color: #999;
  text-transform: uppercase;
  margin-top: 4px;
  display: block;
}

/* Profiles Preview */
.profiles-preview {
  margin-top: 20px;
  border-top: 1px solid #E5E5E5;
  padding-top: 16px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.profiles-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.profiles-list::-webkit-scrollbar {
  width: 4px;
}

.profiles-list::-webkit-scrollbar-thumb {
  background: #DDD;
  border-radius: 2px;
}

.profiles-list::-webkit-scrollbar-thumb:hover {
  background: #CCC;
}

.profile-card {
  background: #FAFAFA;
  border: 1px solid #E5E5E5;
  border-radius: 6px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.profile-card:hover {
  border-color: #999;
  background: #FFF;
}

.profile-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.profile-realname {
  font-size: 14px;
  font-weight: 700;
  color: #000;
}

.profile-username {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #999;
}

.profile-meta {
  margin-bottom: 8px;
}

.profile-profession {
  font-size: 11px;
  color: #666;
  background: #F0F0F0;
  padding: 2px 8px;
  border-radius: 3px;
}

.profile-bio {
  font-size: 12px;
  color: #444;
  line-height: 1.6;
  margin: 0 0 10px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.topic-tag {
  font-size: 10px;
  color: #1565C0;
  background: #E3F2FD;
  padding: 2px 8px;
  border-radius: 10px;
}

.topic-more {
  font-size: 10px;
  color: #999;
  padding: 2px 6px;
}

/* Config Preview */
/* Config Detail Panel */
.config-detail-panel {
  margin-top: 16px;
}

.config-block {
  margin-top: 16px;
  border-top: 1px solid #E5E5E5;
  padding-top: 12px;
}

.config-block:first-child {
  margin-top: 0;
  border-top: none;
  padding-top: 0;
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.config-block-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-block-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: #F1F5F9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 10px;
}

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.config-item {
  background: #F9F9F9;
  padding: 12px 14px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item-label {
  font-size: 11px;
  color: #94A3B8;
}

.config-item-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

/* Time Periods */
.time-periods {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.period-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #F9F9F9;
  border-radius: 6px;
}

.period-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748B;
  min-width: 70px;
}

.period-hours {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #475569;
  flex: 1;
}

.period-multiplier {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  color: #6366F1;
  background: #EEF2FF;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Agents Cards */
.agents-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

.agents-cards::-webkit-scrollbar {
  width: 4px;
}

.agents-cards::-webkit-scrollbar-thumb {
  background: #DDD;
  border-radius: 2px;
}

.agents-cards::-webkit-scrollbar-thumb:hover {
  background: #CCC;
}

.agent-card {
  background: #F9F9F9;
  border: 1px solid #E5E5E5;
  border-radius: 6px;
  padding: 14px;
  transition: all 0.2s ease;
}

.agent-card:hover {
  border-color: #999;
  background: #FFF;
}

/* Agent Card Header */
.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F1F5F9;
}

.agent-identity {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94A3B8;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.agent-tags {
  display: flex;
  gap: 6px;
}

.agent-type {
  font-size: 10px;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
}

.agent-stance {
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
}

.stance-neutral {
  background: #F1F5F9;
  color: #64748B;
}

.stance-supportive {
  background: #DCFCE7;
  color: #16A34A;
}

.stance-opposing {
  background: #FEE2E2;
  color: #DC2626;
}

.stance-observer {
  background: #FEF3C7;
  color: #D97706;
}

/* Agent Timeline */
.agent-timeline {
  margin-bottom: 14px;
}

.timeline-label {
  display: block;
  font-size: 10px;
  color: #94A3B8;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mini-timeline {
  display: flex;
  gap: 2px;
  height: 16px;
  background: #F8FAFC;
  border-radius: 4px;
  padding: 3px;
}

.timeline-hour {
  flex: 1;
  background: #E2E8F0;
  border-radius: 2px;
  transition: all 0.2s;
}

.timeline-hour.active {
  background: linear-gradient(180deg, #6366F1, #818CF8);
}

.timeline-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: #94A3B8;
}

/* Agent Params */
.agent-params {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.param-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.param-item .param-label {
  font-size: 10px;
  color: #94A3B8;
}

.param-item .param-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.param-value.with-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-bar {
  height: 4px;
  background: linear-gradient(90deg, #6366F1, #A855F7);
  border-radius: 2px;
  min-width: 4px;
  max-width: 40px;
}

.param-value.positive {
  color: #16A34A;
}

.param-value.negative {
  color: #DC2626;
}

.param-value.neutral {
  color: #64748B;
}

.param-value.highlight {
  color: #6366F1;
}

/* Platforms Grid */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.platform-card {
  background: #F9F9F9;
  padding: 14px;
  border-radius: 6px;
}

.platform-card-header {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #E5E5E5;
}

.platform-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.platform-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-size: 12px;
  color: #64748B;
}

.param-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #1E293B;
}

/* Reasoning Content */
.reasoning-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reasoning-item {
  padding: 12px 14px;
  background: #F9F9F9;
  border-radius: 6px;
}

.reasoning-text {
  font-size: 13px;
  color: #555;
  line-height: 1.7;
  margin: 0;
}

/* Profile Modal */
.profile-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.profile-modal {
  background: #FFF;
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background: #FFF;
  border-bottom: 1px solid #F0F0F0;
}

.modal-header-info {
  flex: 1;
}

.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.modal-realname {
  font-size: 20px;
  font-weight: 700;
  color: #000;
}

.modal-username {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #999;
}

.modal-profession {
  font-size: 12px;
  color: #666;
  background: #F5F5F5;
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-block;
  font-weight: 500;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: #999;
  border-radius: 50%;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.2s;
  padding: 0;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* 基本信息网格 */
.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px 16px;
  margin-bottom: 32px;
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.info-value {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.info-value.mbti {
  font-family: 'JetBrains Mono', monospace;
  color: #FF5722;
}

/* Tooltip Style */
.info-tooltip-container {
  position: relative;
  display: inline-block;
  margin-left: 6px;
  cursor: help;
  vertical-align: middle;
}

.info-trigger-i {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.08);
  color: #666;
  font-size: 10px;
  font-weight: bold;
  transition: all 0.2s ease;
}

.info-trigger-i:hover {
  background: #D4AF37;
  color: #FFF;
}

.info-tooltip-bubble {
  visibility: hidden;
  position: absolute;
  top: 125%; /* point downwards to prevent overflow-y clipping on modal header */
  left: 50%;
  transform: translateX(-50%);
  width: 290px;
  background-color: #0F172A; /* Slate 900 */
  color: #F1F5F9;
  text-align: left;
  border: 1px solid rgba(212, 175, 55, 0.3);
  border-radius: 6px;
  padding: 12px;
  font-size: 11px;
  line-height: 1.5;
  text-transform: none; /* overrides uppercase of .info-label */
  letter-spacing: normal;
  font-weight: normal;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
  z-index: 9999;
  opacity: 0;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.info-tooltip-bubble::after {
  content: "";
  position: absolute;
  bottom: 100%; /* Arrow points up */
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: transparent transparent #0F172A transparent;
}

.info-tooltip-container:hover .info-tooltip-bubble {
  visibility: visible;
  opacity: 1;
  transform: translateX(-50%) translateY(5px);
}


/* 模块区域 */
.modal-section {
  margin-bottom: 28px;
}

.section-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.section-bio {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  margin: 0;
  padding: 16px;
  background: #F9F9F9;
  border-radius: 6px;
  border-left: 3px solid #E0E0E0;
}

/* 话题标签 */
.topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-item {
  font-size: 11px;
  color: #1565C0;
  background: #E3F2FD;
  padding: 4px 10px;
  border-radius: 12px;
  transition: all 0.2s;
  border: none;
}

.topic-item:hover {
  background: #BBDEFB;
  color: #0D47A1;
}

/* 详细人设 */
.persona-dimensions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.dimension-card {
  background: #F8F9FA;
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #DDD;
  transition: all 0.2s;
}

.dimension-card:hover {
  background: #F0F0F0;
  border-left-color: #999;
}

.dim-title {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #333;
  margin-bottom: 4px;
}

.dim-desc {
  display: block;
  font-size: 10px;
  color: #888;
  line-height: 1.4;
}

.persona-content {
  max-height: none;
  overflow: visible;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

.persona-content::-webkit-scrollbar {
  width: 4px;
}

.persona-content::-webkit-scrollbar-thumb {
  background: #DDD;
  border-radius: 2px;
}

.section-persona {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
  margin: 0;
  text-align: justify;
}

/* System Logs */
.system-logs {
  background: #000;
  color: #DDD;
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid #222;
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: #888;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 80px; /* Approx 4 lines visible */
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 2px;
}

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time {
  color: #666;
  min-width: 75px;
}

.log-msg {
  color: #CCC;
  word-break: break-all;
}

/* Spinner */
.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid #E5E5E5;
  border-top-color: #FF5722;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
/* Orchestration Content */
.orchestration-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 16px;
}

.box-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.narrative-box {
  background: #FFFFFF;
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid #EEF2F6;
  box-shadow: 0 4px 24px rgba(0,0,0,0.03);
  transition: all 0.3s ease;
}

.narrative-box .box-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  font-size: 13px;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
  font-weight: 600;
}

.special-icon {
  filter: drop-shadow(0 2px 4px rgba(255, 87, 34, 0.2));
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.narrative-box:hover .special-icon {
  transform: rotate(180deg);
}

.narrative-text {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 14px;
  color: #334155;
  line-height: 1.8;
  margin: 0;
  text-align: justify;
  letter-spacing: 0.01em;
}

.topics-section {
  background: #FFF;
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-topic-tag {
  font-size: 12px;
  color:rgba(255, 86, 34, 0.88);
  background: #FFF3E0;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.hot-topic-more {
  font-size: 11px;
  color: #999;
  padding: 4px 6px;
}

.initial-posts-section {
  border-top: 1px solid #EAEAEA;
  padding-top: 16px;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-left: 8px;
  border-left: 2px solid #F0F0F0;
  margin-top: 12px;
}

.timeline-item {
  position: relative;
  padding-left: 20px;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 14px;
  width: 12px;
  height: 2px;
  background: #DDD;
}

.timeline-content {
  background: #F9F9F9;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #EEE;
}

.post-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.post-role {
  font-size: 11px;
  font-weight: 700;
  color: #333;
  text-transform: uppercase;
}

.post-agent-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.post-id,
.post-username {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #666;
  line-height: 1;
  vertical-align: baseline;
}

.post-username {
  margin-right: 6px;
}

.post-text {
  font-size: 12px;
  color: #555;
  line-height: 1.5;
  margin: 0;
}

/* 模拟轮数配置样式 */
.rounds-config-section {
  margin: 24px 0;
  padding-top: 24px;
  border-top: 1px solid #EAEAEA;
}

.rounds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.section-desc {
  font-size: 12px;
  color: #94A3B8;
}

.desc-highlight {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #1E293B;
  background: #F1F5F9;
  padding: 1px 6px;
  border-radius: 4px;
  margin: 0 2px;
}

/* Switch Control */
.switch-control {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: 20px;
  transition: background 0.2s;
}

.switch-control:hover {
  background: #F8FAFC;
}

.switch-control input {
  display: none;
}

.switch-track {
  width: 36px;
  height: 20px;
  background: #E2E8F0;
  border-radius: 10px;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-track::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  background: #FFF;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  transition: transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.switch-control input:checked + .switch-track {
  background: #000;
}

.switch-control input:checked + .switch-track::after {
  transform: translateX(16px);
}

.switch-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748B;
}

.switch-control input:checked ~ .switch-label {
  color: #1E293B;
}

/* Slider Content */
.rounds-content {
  animation: fadeIn 0.3s ease;
}

.slider-display {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.slider-main-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.val-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  color: #000;
}

.val-unit {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.slider-meta-info {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #64748B;
  background: #F1F5F9;
  padding: 4px 8px;
  border-radius: 4px;
}

.range-wrapper {
  position: relative;
  padding: 0 2px;
}

.minimal-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  background: #E2E8F0;
  border-radius: 2px;
  outline: none;
  background-image: linear-gradient(#000, #000);
  background-size: var(--percent, 0%) 100%;
  background-repeat: no-repeat;
  cursor: pointer;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #FFF;
  border: 2px solid #000;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  transition: transform 0.1s;
  margin-top: -6px; /* Center thumb */
}

.minimal-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.minimal-slider::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 2px;
}

.range-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94A3B8;
  position: relative;
}

.mark-recommend {
  cursor: pointer;
  transition: color 0.2s;
  position: relative;
}

.mark-recommend:hover {
  color: #000;
}

.mark-recommend.active {
  color: #000;
  font-weight: 600;
}

.mark-recommend::after {
  content: '';
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 1px;
  height: 4px;
  background: #CBD5E1;
}

/* Auto Info */
.auto-info-card {
  display: flex;
  align-items: center;
  gap: 24px;
  background: #F8FAFC;
  padding: 16px 20px;
  border-radius: 8px;
}

.auto-value {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 4px;
  padding-right: 24px;
  border-right: 1px solid #E2E8F0;
}

.auto-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.auto-meta-row {
  display: flex;
  align-items: center;
}

.duration-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #64748B;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  padding: 3px 8px;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.auto-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.auto-desc p {
  margin: 0;
  font-size: 13px;
  color: #64748B;
  line-height: 1.5;
}

.highlight-tip {
  margin-top: 4px !important;
  font-size: 12px !important;
  color: #000 !important;
  font-weight: 500;
  cursor: pointer;
}

.highlight-tip:hover {
  text-decoration: underline;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Modal Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .profile-modal {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-leave-active .profile-modal {
  transition: all 0.3s ease-in;
}

.modal-enter-from .profile-modal,
.modal-leave-to .profile-modal {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

/* Sélecteur de Mode d'Exécution */
.run-mode-section {
  margin: 24px 0;
  padding-top: 24px;
  border-top: 1px solid #EAEAEA;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mode-cards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 12px;
}

.mode-select-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.mode-select-card:hover {
  border-color: #CBD5E1;
  background: #F1F5F9;
  transform: translateY(-2px);
}

.mode-select-card.active {
  border-color: #3B82F6;
  background: #EFF6FF;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}

.mode-select-card.active.legal-card-active {
  background: linear-gradient(135deg, #B58A3D 0%, #D4AF37 50%, #B58A3D 100%) !important;
  border-color: #D4AF37 !important;
  box-shadow: 0 4px 20px rgba(212, 175, 55, 0.4) !important;
}

.mode-select-card.active.legal-card-active .mode-name {
  color: #0B1220 !important;
  font-weight: 700;
}

.mode-select-card.active.legal-card-active .mode-description {
  color: #0B1220 !important;
  font-weight: 600;
}

.mode-icon {
  font-size: 24px;
  padding: 8px;
  background: #FFFFFF;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}

.mode-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mode-name {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.mode-select-card.active .mode-name {
  color: #1E40AF;
}

.mode-description {
  font-size: 11px;
  color: #64748B;
  line-height: 1.4;
}

.side-select-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
}

.side-cards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 12px;
}

.side-select-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.side-select-card:hover {
  border-color: #CBD5E1;
  background: #F1F5F9;
  transform: translateY(-2px);
}

.side-select-card.active {
  border-color: #B58A3D;
  background: #FDFBF7;
  box-shadow: 0 4px 12px rgba(181, 138, 61, 0.08);
}

.side-icon {
  font-size: 24px;
  padding: 8px;
  background: #FFFFFF;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}

.side-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.side-name {
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.side-select-card.active .side-name {
  color: #8C621F;
}

.side-description {
  font-size: 11px;
  color: #64748B;
  line-height: 1.4;
}

/* Mode Édition */
.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.edit-mode-btn, .save-profile-btn, .cancel-profile-btn {
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}
.edit-mode-btn {
  background: #F3F4F6;
  border-color: #E5E7EB;
  color: #374151;
}
.edit-mode-btn:hover {
  background: #E5E7EB;
}
.save-profile-btn {
  background: #000;
  color: #FFF;
}
.save-profile-btn:hover:not(:disabled) {
  opacity: 0.8;
}
.save-profile-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.cancel-profile-btn {
  background: transparent;
  border-color: #D1D5DB;
  color: #4B5563;
}
.cancel-profile-btn:hover {
  background: #F9FAFB;
}
.modal-name-row-edit {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.edit-input, .edit-select, .edit-textarea {
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  background: #FAFAFA;
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color 0.2s, background-color 0.2s;
  color: #000;
}
.edit-input:focus, .edit-select:focus, .edit-textarea:focus {
  outline: none;
  border-color: #000;
  background: #FFF;
}
.name-edit {
  font-size: 16px;
  font-weight: 700;
  max-width: 200px;
}
.name-edit-handle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  max-width: 150px;
}
.profession-edit {
  font-size: 12px;
  padding: 4px 8px;
  max-width: 200px;
}
.edit-profile-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.form-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bio-textarea {
  height: 60px;
  resize: vertical;
}
.persona-textarea {
  height: 120px;
  resize: vertical;
}
.behavioral-parameters-section {
  border-top: 1px dashed #E5E7EB;
  margin-top: 12px;
  padding-top: 16px;
}
.behavioral-parameters-section .section-label {
  font-size: 12px;
  font-weight: 700;
  color: #1E293B;
  display: block;
  margin-bottom: 12px;
  text-transform: uppercase;
}
.behavior-grid {
  grid-template-columns: repeat(3, 1fr);
}

/* Radar Tactique Premium Design */
.radar-tactique-section {
  margin-top: 24px;
  margin-bottom: 24px;
  padding: 20px;
  border-radius: 16px;
  background: rgba(253, 251, 247, 0.4);
  border: 1px solid rgba(181, 138, 61, 0.15);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.02);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
}

.radar-header-inline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.radar-header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.radar-trigger-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #B58A3D 0%, #D4AF37 50%, #B58A3D 100%);
  color: #FFFFFF;
  border: none;
  padding: 12px 24px;
  border-radius: 30px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(181, 138, 61, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.radar-trigger-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -50%;
  width: 200%;
  height: 100%;
  background: linear-gradient(
    to right,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.3) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  transform: skewX(-25deg);
  transition: 0.75s;
  opacity: 0;
}

.radar-trigger-btn:hover:not(:disabled)::before {
  left: 125%;
  opacity: 1;
}

.radar-trigger-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(181, 138, 61, 0.4);
}

.radar-trigger-btn:active:not(:disabled) {
  transform: translateY(1px);
}

.radar-trigger-btn:disabled {
  background: #CBD5E1;
  color: #94A3B8;
  cursor: not-allowed;
  box-shadow: none;
}

.radar-results-card {
  margin-top: 20px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.03);
}

.matrix-title-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  border-left: 3px solid #B58A3D;
  padding-left: 12px;
}
.matrix-title-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.matrix-title {
  font-size: 15px;
  font-weight: 700;
  color: #1E293B;
}

.matrix-subtitle {
  font-size: 12px;
  color: #64748B;
}

.table-container {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
}

.radar-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.radar-table th {
  background: #F8FAFC;
  padding: 12px 16px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #E2E8F0;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.05em;
}

.radar-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #F1F5F9;
  color: #334155;
  vertical-align: middle;
}

.radar-table tbody tr:last-child td {
  border-bottom: none;
}

.radar-table tbody tr:hover {
  background: rgba(248, 250, 252, 0.5);
}

.node-cell {
  white-space: nowrap;
  color: #1E293B;
}

.vector-badge {
  display: inline-block;
  padding: 4px 8px;
  background: rgba(181, 138, 61, 0.08);
  color: #8C621F;
  border: 1px solid rgba(181, 138, 61, 0.2);
  border-radius: 6px;
  font-weight: 600;
  font-size: 11px;
}

.impact-value-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 120px;
}

.impact-text {
  font-weight: 700;
  color: #15803D;
}

.progress-bar-container {
  height: 6px;
  background: #E2E8F0;
  border-radius: 3px;
  overflow: hidden;
  width: 100px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #22C55E, #16A34A);
  border-radius: 3px;
}

.plan-cell {
  line-height: 1.5;
  color: #475569;
}

.draft-btn {
  background: #1E293B;
  color: #FFFFFF;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.draft-btn:hover {
  background: #0F172A;
  transform: translateY(-1px);
}

/* Modal de Projet de Requête */
.legal-draft-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.legal-draft-modal {
  background: #FFFFFF;
  border-radius: 16px;
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(226, 232, 240, 0.8);
  overflow: hidden;
}

.draft-body {
  padding: 24px;
  overflow-y: auto;
  background: #FAF9F6;
  flex: 1;
}

.draft-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 16px;
  color: #64748B;
}

.draft-loader p {
  font-size: 14px;
  font-weight: 500;
}

.typewriter-content {
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #1A1A1A;
  white-space: pre-wrap;
  margin: 0;
  padding: 20px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
  min-height: 300px;
}

.cursor {
  display: inline-block;
  margin-left: 2px;
  font-weight: bold;
  animation: blink 0.8s infinite;
  color: #B58A3D;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.spinner-icon {
  display: inline-block;
  animation: rotate 1.5s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Plan Cell Clamp */
.plan-cell-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 250px;
}

/* Selected row highlight */
.radar-table tbody tr.row-selected {
  background: rgba(181, 138, 61, 0.05) !important;
  border-left: 3px solid #B58A3D;
}

/* Modals layout */
.large-modal-overlay, .detail-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}

/* Glassmorphic Premium Modal styling */
.glassmorphic-modal {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(181, 138, 61, 0.25);
  border-radius: 20px;
  box-shadow: 0 30px 70px rgba(181, 138, 61, 0.12), 0 10px 20px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalSlideUp 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes modalSlideUp {
  from {
    transform: scale(0.96) translateY(20px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

.large-modal {
  width: 92%;
  max-width: 1200px;
  max-height: 88vh;
}

.detail-modal {
  width: 90%;
  max-width: 700px;
  max-height: 85vh;
}

.gold-border-bottom {
  border-bottom: 1px solid rgba(181, 138, 61, 0.2);
}

.gold-border-top {
  border-top: 1px solid rgba(181, 138, 61, 0.2);
}

.font-serif-gold {
  color: #B58A3D;
  font-family: 'Outfit', 'Georgia', serif;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.gold-border-btn {
  border: 1px solid rgba(181, 138, 61, 0.3) !important;
  color: #8C621F !important;
  background: transparent !important;
}

.gold-border-btn:hover {
  background: rgba(181, 138, 61, 0.05) !important;
  border-color: #B58A3D !important;
}

/* Expanded Table styles */
.large-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.matrix-description-text {
  font-size: 13px;
  color: #64748B;
  margin-bottom: 20px;
  line-height: 1.6;
}

.large-table-container {
  border: 1px solid rgba(181, 138, 61, 0.15);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.01);
  background: #FFF;
}

.large-radar-table th {
  background: #FDFDFB;
  border-bottom: 1px solid rgba(181, 138, 61, 0.15);
  color: #64748B;
  padding: 14px 20px;
  font-size: 11px;
}

.large-radar-table td {
  padding: 16px 20px;
  border-bottom: 1px solid #F8FAFC;
}

.plan-cell-expanded {
  line-height: 1.6;
  color: #334155;
  font-size: 13px;
}

.expand-matrix-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: #B58A3D;
  border: 1px solid rgba(181, 138, 61, 0.4);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;
}

.expand-matrix-btn:hover {
  background: rgba(181, 138, 61, 0.08);
  border-color: #B58A3D;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(181, 138, 61, 0.15);
}

.detail-btn {
  background: #F8FAFC;
  color: #475569;
  border: 1px solid #E2E8F0;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.detail-btn:hover {
  background: #F1F5F9;
  color: #1E293B;
  border-color: #CBD5E1;
  transform: translateY(-1px);
}

/* Detail Modal specific styling */
.detail-body-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-card-header-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  background: #FAF9F6;
  border: 1px solid rgba(181, 138, 61, 0.1);
  padding: 16px;
  border-radius: 12px;
}

.detail-meta-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label-tag {
  font-size: 10px;
  font-weight: 700;
  color: #94A3B8;
  letter-spacing: 0.08em;
}

.detail-value-highlight {
  font-size: 16px;
  font-weight: 700;
  color: #1E293B;
}

.large-vector-badge {
  font-size: 12px;
  padding: 6px 12px;
  width: fit-content;
}

/* Impact Card */
.detail-impact-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: rgba(34, 197, 94, 0.03);
  border: 1px solid rgba(34, 197, 94, 0.15);
  border-radius: 12px;
  padding: 16px 20px;
}

.impact-radial-indicator {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  min-width: 140px;
  border-right: 1px solid rgba(34, 197, 94, 0.15);
  padding-right: 20px;
}

.impact-radial-text {
  font-size: 18px;
  font-weight: 800;
  color: #16A34A;
}

.detail-progress-container {
  height: 6px;
  background: #E2E8F0;
  border-radius: 3px;
  overflow: hidden;
  width: 100px;
}

.detail-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #22C55E, #16A34A);
}

.impact-explanation {
  flex: 1;
}

.detail-section-title {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
  margin-bottom: 4px;
}

.detail-section-desc {
  font-size: 11px;
  color: #64748B;
  line-height: 1.4;
  margin: 0;
}

/* Plan / Roadmap Section */
.detail-plan-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-section-label-gold {
  font-size: 12px;
  font-weight: 700;
  color: #B58A3D;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-plan-card-body {
  background: #FCFAF7;
  border-left: 4px solid #B58A3D;
  border-top: 1px solid rgba(181, 138, 61, 0.1);
  border-bottom: 1px solid rgba(181, 138, 61, 0.1);
  border-right: 1px solid rgba(181, 138, 61, 0.1);
  padding: 16px 20px;
  border-radius: 0 8px 8px 0;
}

.detail-plan-text {
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  margin: 0;
  text-align: justify;
}

/* Status Section */
.detail-status-section {
  margin-top: 4px;
}

.status-active-badge, .status-inactive-badge {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
}

.status-active-badge {
  background: rgba(22, 163, 74, 0.05);
  border: 1px solid rgba(22, 163, 74, 0.15);
}

.status-inactive-badge {
  background: rgba(148, 163, 184, 0.05);
  border: 1px solid rgba(148, 163, 184, 0.15);
}

.status-icon {
  font-size: 16px;
  line-height: 1;
}

.status-active-badge .status-icon {
  color: #16A34A;
}

.status-inactive-badge .status-icon {
  color: #64748B;
}

.status-text-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-title {
  font-size: 12px;
  font-weight: 700;
  color: #1E293B;
}

.status-desc {
  font-size: 11px;
  color: #64748B;
  line-height: 1.4;
}

/* Footer Actions */
.modal-footer-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: #FFF;
}

.draft-btn-view {
  background: #475569;
  color: #FFF;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.draft-btn-view:hover {
  background: #334155;
  transform: translateY(-1px);
}

.draft-btn-generate {
  background: #B58A3D;
  color: #FFF;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
}

.draft-btn-generate:hover {
  background: #8C621F;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(181, 138, 61, 0.25);
}

/* Pulsing Gold animation for generate action */
.pulsing-gold-btn {
  animation: pulseGold 2s infinite;
}

@keyframes pulseGold {
  0% {
    box-shadow: 0 0 0 0 rgba(181, 138, 61, 0.4);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(181, 138, 61, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(181, 138, 61, 0);
  }
}

.select-badge-animate {
  animation: badgePop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  background-color: #16A34A;
  color: white;
  margin-left: 4px;
  font-size: 10px;
}

@keyframes badgePop {
  0% {
    transform: scale(0.8);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
