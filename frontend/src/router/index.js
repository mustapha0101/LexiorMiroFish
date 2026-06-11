import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import LegalSimulationView from '../views/LegalSimulationView.vue'
import ResearchPaper from '../views/ResearchPaper.vue'
import { supabase } from '../utils/supabase'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/research',
    name: 'Research',
    component: ResearchPaper
  },
  {
    path: '/legal-simulator',
    name: 'LegalSimulator',
    component: LegalSimulationView
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  },
  {
    path: '/financial-guide',
    name: 'FinancialGuide',
    component: () => import('../views/FinancialGuide.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  // Allow public access ONLY to the Research and FinancialGuide pages. All other pages require auth.
  if (to.name !== 'Research' && to.name !== 'FinancialGuide') {
    let session = null
    if (supabase) {
      try {
        const { data } = await supabase.auth.getSession()
        session = data?.session
      } catch (e) {
        console.error('Error in router session check:', e)
      }
    }
    
    // Check developer bypass fallback
    if (!session) {
      const storedBypass = localStorage.getItem('lexior_bypass_session')
      if (storedBypass) {
        try {
          session = JSON.parse(storedBypass)
        } catch (e) {}
      }
    }
    
    // If not authenticated, redirect to Login / Home (except if already going to Home)
    if (!session && to.name !== 'Home') {
      next({ name: 'Home' })
      return
    }
  }
  next()
})

export default router
