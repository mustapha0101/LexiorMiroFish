<template>
  <div v-if="!session" class="login-gate-container">
    <div class="login-card">
      <div class="logo-area">
        <img src="/logo.png" alt="Lexior Logo" class="auth-logo" />
        <h2 class="auth-brand">{{ $t('common.brandFirst') }} <span class="brand-sub">{{ $t('common.brandSecond') }}</span></h2>
      </div>

      <!-- No Supabase Config Warning -->
      <div v-if="!isConfigured" class="warning-box">
        <span class="warning-icon">⚠️</span>
        <p class="warning-text">
          {{ $t('auth.missingConfig') }}
        </p>
        <!-- Fallback bypass button for development -->
        <button class="bypass-btn" @click="bypassAuth">
          Bypass Auth (Development Mode)
        </button>
      </div>

      <div v-else class="auth-form-wrapper">
        <h3 class="form-title">
          {{ isSignUp ? $t('auth.titleSignUp') : $t('auth.titleLogin') }}
        </h3>

        <form @submit.prevent="handleAuth" class="auth-form">
          <div class="form-group">
            <label for="email">{{ $t('auth.emailLabel') }}</label>
            <input
              id="email"
              type="email"
              v-model="email"
              required
              class="form-input"
              placeholder="avocat@lexior.com"
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="password">{{ $t('auth.passwordLabel') }}</label>
            <input
              id="password"
              type="password"
              v-model="password"
              required
              class="form-input"
              placeholder="••••••••"
              :disabled="loading"
            />
          </div>

          <div v-if="error" class="error-message">
            {{ $t('auth.errorMsg') }}{{ error }}
          </div>

          <div v-if="successMsg" class="success-message">
            {{ successMsg }}
          </div>

          <button type="submit" class="auth-submit-btn" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            {{ isSignUp ? $t('auth.signUpBtn') : $t('auth.loginBtn') }}
          </button>
        </form>

        <div class="auth-toggle">
          <button class="toggle-btn" @click="isSignUp = !isSignUp" :disabled="loading">
            {{ isSignUp ? $t('auth.toggleToLogin') : $t('auth.toggleToSignUp') }}
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="auth-success-wrapper">
    <!-- Slot for authenticated content -->
    <slot></slot>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { supabase } from '../utils/supabase'

const session = ref(null)
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const successMsg = ref('')
const isSignUp = ref(false)
const isConfigured = ref(!!supabase)

const emit = defineEmits(['session-change'])

watch(session, (newVal) => {
  emit('session-change', newVal)
}, { immediate: true })

onMounted(async () => {
  if (supabase) {
    // Check active session
    const { data, error: sessionErr } = await supabase.auth.getSession()
    if (!sessionErr && data?.session) {
      session.value = data.session
      return
    }

    // Listen to auth state changes
    supabase.auth.onAuthStateChange((event, currentSession) => {
      session.value = currentSession
    })
  }

  // Fallback check for developer bypass session
  const storedBypass = localStorage.getItem('lexior_bypass_session')
  if (storedBypass) {
    try {
      session.value = JSON.parse(storedBypass)
    } catch (e) {
      localStorage.removeItem('lexior_bypass_session')
    }
  }
})

const handleAuth = async () => {
  if (!supabase) return
  
  loading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    if (isSignUp.value) {
      const { data, error: signUpErr } = await supabase.auth.signUp({
        email: email.value,
        password: password.value,
      })
      if (signUpErr) throw signUpErr
      successMsg.value = "Inscription réussie ! Veuillez vérifier vos courriels si nécessaire."
    } else {
      const { data, error: signInErr } = await supabase.auth.signInWithPassword({
        email: email.value,
        password: password.value,
      })
      if (signInErr) throw signInErr
      session.value = data.session
    }
  } catch (err) {
    error.value = err.message || err
  } finally {
    loading.value = false
  }
}

// Development bypass
const bypassAuth = () => {
  const devSession = { user: { email: 'dev-bypass@lexior.com', id: 'dev-bypass-id' } }
  session.value = devSession
  localStorage.setItem('lexior_bypass_session', JSON.stringify(devSession))
}

// Expose sign out function
const handleSignOut = async () => {
  if (supabase) {
    await supabase.auth.signOut()
  }
  session.value = null
  localStorage.removeItem('lexior_bypass_session')
}

defineExpose({
  session,
  handleSignOut
})
</script>

<style scoped>
.login-gate-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  padding: 20px;
  background: #F8FAFC;
  font-family: 'Inter', -apple-system, sans-serif;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
  backdrop-filter: blur(10px);
  text-align: center;
  animation: fadeIn 0.4s ease-out;
}

.logo-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 30px;
}

.auth-logo {
  height: 64px;
  width: auto;
  margin-bottom: 12px;
}

.auth-brand {
  font-family: 'Inter', -apple-system, sans-serif;
  font-weight: 800;
  font-size: 1.5rem;
  color: #0B1220;
  letter-spacing: 0.5px;
  margin: 0;
}

.brand-sub {
  color: #C5A880;
  font-weight: 300;
}

.warning-box {
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.warning-icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
  display: block;
}

.warning-text {
  font-size: 0.85rem;
  color: #B45309;
  line-height: 1.4;
  margin: 0 0 16px 0;
}

.bypass-btn {
  background: #C5A880;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  width: 100%;
}

.bypass-btn:hover {
  background: #B4966E;
}

.auth-form-wrapper {
  text-align: left;
}

.form-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: #0B1220;
  margin-top: 0;
  margin-bottom: 24px;
  text-align: center;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748B;
}

.form-input {
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s;
  background: #F8FAFC;
}

.form-input:focus {
  border-color: #C5A880;
  background: #FFFFFF;
  box-shadow: 0 0 0 3px rgba(197, 168, 128, 0.15);
}

.error-message {
  font-size: 0.8rem;
  color: #EF4444;
  background: #FEF2F2;
  border-radius: 6px;
  padding: 10px;
  border-left: 3px solid #EF4444;
  line-height: 1.4;
}

.success-message {
  font-size: 0.8rem;
  color: #10B981;
  background: #ECFDF5;
  border-radius: 6px;
  padding: 10px;
  border-left: 3px solid #10B981;
  line-height: 1.4;
}

.auth-submit-btn {
  background: #0B1220;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  padding: 14px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.auth-submit-btn:hover {
  background: #1A2536;
}

.auth-submit-btn:disabled {
  background: #94A3B8;
  cursor: not-allowed;
}

.auth-toggle {
  margin-top: 24px;
  text-align: center;
}

.toggle-btn {
  background: none;
  border: none;
  color: #64748B;
  font-size: 0.85rem;
  cursor: pointer;
  transition: color 0.2s;
}

.toggle-btn:hover {
  color: #C5A880;
  text-decoration: underline;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
