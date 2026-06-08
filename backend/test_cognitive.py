import os
import sys
import unittest
import shutil
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure backend root is in the path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.services.cognitive_engine import CognitiveAgentState, CognitiveEngine
from app.services.cognitive_memory import CognitiveMemoryService
from app.services.cognitive_helper import inject_cognitive_prompts, update_cognitive_states


class TestCognitiveArchitecture(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.simulation_id = "test_simulation_cognitive"
        # Base path for temporary database
        self.db_path = os.path.join(base_dir, 'uploads', 'kuzu', self.simulation_id)
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path, ignore_errors=True)

    def tearDown(self):
        # Cleanup test graph database
        if os.path.exists(self.db_path):
            try:
                # Close connection if any remains open by removing the cached database
                from app.services.local_graph_database import LocalGraphDatabase
                if self.db_path in LocalGraphDatabase._KUZU_DATABASES:
                    del LocalGraphDatabase._KUZU_DATABASES[self.db_path]
                shutil.rmtree(self.db_path, ignore_errors=True)
            except Exception as e:
                print(f"Error cleaning up test db: {e}")

    def test_agent_state_serialization(self):
        state = CognitiveAgentState(
            agent_id="agent_123",
            name="Alice",
            tensions={"exploration_vs_security": 0.8},
            beliefs={"general_trust": {"high": 0.1, "medium": 0.2, "low": 0.7}},
            meta_narrative="I feel insecure but adventurous.",
            recent_reflection="I decided to explore anyway."
        )
        
        data = state.to_dict()
        self.assertEqual(data["agent_id"], "agent_123")
        self.assertEqual(data["name"], "Alice")
        self.assertEqual(data["tensions"]["exploration_vs_security"], 0.8)
        self.assertEqual(data["beliefs"]["general_trust"]["low"], 0.7)
        self.assertEqual(data["meta_narrative"], "I feel insecure but adventurous.")
        self.assertEqual(data["recent_reflection"], "I decided to explore anyway.")
        
        restored = CognitiveAgentState.from_dict(data)
        self.assertEqual(restored.agent_id, "agent_123")
        self.assertEqual(restored.name, "Alice")
        self.assertEqual(restored.tensions["exploration_vs_security"], 0.8)
        self.assertEqual(restored.beliefs["general_trust"]["low"], 0.7)
        self.assertEqual(restored.meta_narrative, "I feel insecure but adventurous.")
        self.assertEqual(restored.recent_reflection, "I decided to explore anyway.")

    def test_memory_service_save_and_retrieve_state(self):
        state = CognitiveAgentState(
            agent_id="agent_456",
            name="Bob",
            tensions={"exploration_vs_security": 0.4},
            beliefs={"general_trust": {"high": 0.6, "medium": 0.3, "low": 0.1}},
            meta_narrative="Testing memory engine.",
            recent_reflection="Just a test reflection."
        )
        
        # Save to DB
        CognitiveMemoryService.save_agent_state(self.simulation_id, state)
        
        # Retrieve from DB
        retrieved = CognitiveMemoryService.get_agent_state(self.simulation_id, "agent_456", "Bob")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.agent_id, "agent_456")
        self.assertEqual(retrieved.name, "Bob")
        self.assertAlmostEqual(retrieved.tensions["exploration_vs_security"], 0.4)
        self.assertAlmostEqual(retrieved.beliefs["general_trust"]["high"], 0.6)
        self.assertEqual(retrieved.meta_narrative, "Testing memory engine.")
        self.assertEqual(retrieved.recent_reflection, "Just a test reflection.")

    def test_memory_fragments_and_decay(self):
        # Create agent state first to link memories
        state = CognitiveAgentState(agent_id="agent_789", name="Charlie")
        CognitiveMemoryService.save_agent_state(self.simulation_id, state)
        
        # Add memory fragments
        CognitiveMemoryService.add_memory_fragment(
            self.simulation_id, 
            "agent_789", 
            "I joined the forum.", 
            emotional_charge=0.8
        )
        CognitiveMemoryService.add_memory_fragment(
            self.simulation_id, 
            "agent_789", 
            "I saw an argument.", 
            emotional_charge=0.2
        )
        
        # Verify both exist
        memories = CognitiveMemoryService.get_active_memories(self.simulation_id, "agent_789")
        self.assertEqual(len(memories), 2)
        self.assertIn("I joined the forum.", memories)
        self.assertIn("I saw an argument.", memories)
        
        # Apply decay once (default decay = 0.85)
        # Strength goes from 1.0 -> 0.85. Still above threshold (0.2 / 0.15)
        CognitiveMemoryService.apply_memory_decay(self.simulation_id, "agent_789", decay_factor=0.85)
        memories_after_decay = CognitiveMemoryService.get_active_memories(self.simulation_id, "agent_789")
        self.assertEqual(len(memories_after_decay), 2)
        
        # Apply heavy decay to push strength below threshold (< 0.15)
        # Strength goes from 0.85 * 0.10 = 0.085
        CognitiveMemoryService.apply_memory_decay(self.simulation_id, "agent_789", decay_factor=0.10)
        memories_after_heavy_decay = CognitiveMemoryService.get_active_memories(self.simulation_id, "agent_789")
        self.assertEqual(len(memories_after_heavy_decay), 0)

    def test_cognitive_engine_bayesian_belief_updates(self):
        engine = CognitiveEngine()
        state = CognitiveAgentState(
            agent_id="agent_999",
            name="Daniel",
            beliefs={"general_trust": {"high": 0.5, "medium": 0.3, "low": 0.2}}
        )
        
        # If action is CREATE_POST (affirmative trust action)
        updated = engine._update_beliefs_bayesian(state, "Daniel posted something positive", "CREATE_POST")
        # High trust should increase, low trust decrease
        self.assertGreater(updated["general_trust"]["high"], 0.5)
        self.assertLess(updated["general_trust"]["low"], 0.2)
        self.assertAlmostEqual(sum(updated["general_trust"].values()), 1.0)
        
        # If action is MUTE (distrust/negative action)
        state.beliefs = {"general_trust": {"high": 0.5, "medium": 0.3, "low": 0.2}}
        updated_neg = engine._update_beliefs_bayesian(state, "Daniel muted a user", "MUTE")
        # High trust should decrease, low trust increase
        self.assertLess(updated_neg["general_trust"]["high"], 0.5)
        self.assertGreater(updated_neg["general_trust"]["low"], 0.2)
        self.assertAlmostEqual(sum(updated_neg["general_trust"].values()), 1.0)

    def test_cognitive_engine_tension_plasticity(self):
        engine = CognitiveEngine()
        state = CognitiveAgentState(
            agent_id="agent_999",
            name="Daniel",
            tensions={"exploration_vs_security": 0.5}
        )
        
        engine._update_tensions_plasticity(state, "exploration_vs_security")
        tension_val = state.tensions["exploration_vs_security"]
        # Drift should change it by ±0.02
        self.assertTrue(tension_val == 0.52 or tension_val == 0.48)

    @patch('app.services.cognitive_engine.OpenAI')
    async def test_cognitive_engine_run_cycle(self, mock_openai_cls):
        # Setup mocks
        mock_client = MagicMock()
        mock_openai_cls.return_returns = mock_client
        
        # Configure the mock response
        mock_response_1 = MagicMock()
        mock_response_1.choices = [
            MagicMock(message=MagicMock(content='''```json
{
  "analyst": {"thought": "Logical perspective.", "action": "CREATE_POST"},
  "creative": {"thought": "Emotional response.", "action": "CREATE_POST"},
  "protector": {"thought": "Safety response.", "action": "DO_NOTHING"}
}
```'''))
        ]
        
        mock_response_2 = MagicMock()
        mock_response_2.choices = [
            MagicMock(message=MagicMock(content='''```json
{
  "action": "CREATE_POST",
  "reasoning": "Decided to share ideas based on exploration tension.",
  "tension_used": "exploration_vs_security"
}
```'''))
        ]
        
        mock_response_3 = MagicMock()
        mock_response_3.choices = [
            MagicMock(message=MagicMock(content='''```json
{
  "meta_narrative": "I feel more confident in expressing my views.",
  "recent_reflection": "Shared thoughts as exploring ideas."
}
```'''))
        ]
        
        mock_client.chat.completions.create.side_effect = [
            mock_response_1,
            mock_response_2,
            mock_response_3
        ]
        
        engine = CognitiveEngine()
        engine.client = mock_client
        
        state = CognitiveAgentState(
            agent_id="agent_abc",
            name="Emma",
            tensions={"exploration_vs_security": 0.6},
            beliefs={"general_trust": {"high": 0.4, "medium": 0.4, "low": 0.2}}
        )
        
        result = await engine.run_cognitive_cycle(
            state,
            environment_stimulus="User posts about a new project.",
            memories=[]
        )
        
        self.assertEqual(result["action"], "CREATE_POST")
        self.assertEqual(result["reasoning"], "Decided to share ideas based on exploration tension.")
        self.assertEqual(result["state"]["meta_narrative"], "I feel more confident in expressing my views.")
        self.assertEqual(result["state"]["recent_reflection"], "Shared thoughts as exploring ideas.")
        # Tension must have shifted
        self.assertNotEqual(result["state"]["tensions"]["exploration_vs_security"], 0.6)

    def test_cognitive_helper_injection(self):
        # Create a mock Agent with system_message
        class MockSystemMessage:
            def __init__(self, content):
                self.content = content
        
        class MockAgent:
            def __init__(self, agent_id, system_message):
                self.agent_id = agent_id
                self.system_message = MockSystemMessage(system_message)
        
        agent_obj = MockAgent(1, "Base system message instruction.")
        active_agents = [(1, agent_obj)]
        config = {"simulation_id": self.simulation_id}
        agent_names = {1: "Agent1"}
        
        # Save a state first
        state = CognitiveAgentState(
            agent_id="1",
            name="Agent1",
            tensions={"exploration_vs_security": 0.7},
            beliefs={"general_trust": {"high": 0.5, "medium": 0.3, "low": 0.2}},
            meta_narrative="Exploring the space.",
            recent_reflection="Observing surroundings."
        )
        CognitiveMemoryService.save_agent_state(self.simulation_id, state)
        
        inject_cognitive_prompts(active_agents, config, agent_names)
        
        self.assertTrue(hasattr(agent_obj, 'original_system_message'))
        self.assertEqual(agent_obj.original_system_message, "Base system message instruction.")
        self.assertIn("DYNAMIC COGNITIVE STATE (PIE)", agent_obj.system_message.content)
        self.assertIn("Exploration vs Security: 0.70", agent_obj.system_message.content)
        self.assertIn("general_trust: high (50%)", agent_obj.system_message.content)
        self.assertIn("Exploring the space.", agent_obj.system_message.content)

    def test_attention_budget_constraints(self):
        class MockSystemMessage:
            def __init__(self, content):
                self.content = content
        class MockAgent:
            def __init__(self, agent_id, system_message):
                self.agent_id = agent_id
                self.system_message = MockSystemMessage(system_message)
        
        agent_obj = MockAgent(2, "Base.")
        active_agents = [(2, agent_obj)]
        config = {"simulation_id": self.simulation_id}
        agent_names = {2: "Agent2"}
        
        # Save a state with LOW introspection and long_term budget
        state = CognitiveAgentState(
            agent_id="2",
            name="Agent2",
            meta_narrative="I should think deep.",
            recent_reflection="Deep thoughts.",
            attention_budget={"social": 0.6, "introspection": 0.1, "risk": 0.2, "long_term": 0.1}
        )
        CognitiveMemoryService.save_agent_state(self.simulation_id, state)
        
        # Add memories (one old/weak, one new/strong)
        # We will write weak memories directly, but calling add_memory_fragment creates 1.0 strength.
        # We can apply memory decay to lower their strength.
        CognitiveMemoryService.add_memory_fragment(self.simulation_id, "2", "Weak memory")
        CognitiveMemoryService.apply_memory_decay(self.simulation_id, "2", decay_factor=0.3) # strength becomes 0.3 (below 0.6)
        
        CognitiveMemoryService.add_memory_fragment(self.simulation_id, "2", "Strong memory") # strength is 1.0 (above 0.6)
        
        # Inject prompts
        inject_cognitive_prompts(active_agents, config, agent_names)
        
        # 1. Introspection check: it should show limited introspection message instead of actual reflections
        self.assertNotIn("I should think deep.", agent_obj.system_message.content)
        self.assertIn("Mon introspection est limitée par mon attention actuelle.", agent_obj.system_message.content)
        
        # 2. Long_term budget check: it should only contain "Strong memory", and NOT "Weak memory" because threshold is 0.6
        self.assertNotIn("Weak memory", agent_obj.system_message.content)
        self.assertIn("Strong memory", agent_obj.system_message.content)

    def test_mood_drift_state_machine(self):
        engine = CognitiveEngine()
        state = CognitiveAgentState(agent_id="agent_m", name="MoodAgent")
        
        # Initial mood: Neutre
        self.assertEqual(state.mood, "Neutre")
        
        # Hostile action 1: should become Méfiant
        engine._update_mood_state(state, "MUTE")
        self.assertEqual(state.mood, "Méfiant")
        self.assertEqual(state.negative_interactions_count, 1)
        
        # Hostile action 2: should become Paranoïaque
        engine._update_mood_state(state, "DISLIKE_POST")
        self.assertEqual(state.mood, "Paranoïaque")
        self.assertEqual(state.negative_interactions_count, 2)
        
        # Hostile action 3: should become Isolé
        engine._update_mood_state(state, "DO_NOTHING")
        self.assertEqual(state.mood, "Isolé")
        self.assertEqual(state.negative_interactions_count, 3)
        
        # Social action: should recover one level (to Paranoïaque)
        engine._update_mood_state(state, "LIKE_POST")
        self.assertEqual(state.mood, "Paranoïaque")
        self.assertEqual(state.negative_interactions_count, 2)

    def test_legal_tensions_simulation(self):
        class MockSystemMessage:
            def __init__(self, content):
                self.content = content
        class MockAgent:
            def __init__(self, agent_id, system_message):
                self.agent_id = agent_id
                self.system_message = MockSystemMessage(system_message)
        
        agent_obj = MockAgent(3, "Base.")
        active_agents = [(3, agent_obj)]
        # Simulation type is legal!
        config = {"simulation_id": self.simulation_id, "simulation_type": "legal"}
        agent_names = {3: "Agent3"}
        
        state = CognitiveAgentState(
            agent_id="3",
            name="Agent3",
            tensions={"prudence_vs_rapidite": 0.8, "offensive_vs_negociation": 0.2, "procedure_vs_equite": 0.4}
        )
        CognitiveMemoryService.save_agent_state(self.simulation_id, state)
        
        inject_cognitive_prompts(active_agents, config, agent_names)
        
        # Verify legal tension labels are injected
        self.assertIn("Prudence vs Rapidité: 0.80", agent_obj.system_message.content)
        self.assertIn("Offensive vs Négociation: 0.20", agent_obj.system_message.content)
        self.assertIn("Procédure vs Équité: 0.40", agent_obj.system_message.content)
        # Should NOT contain default social labels
        self.assertNotIn("Exploration vs Security", agent_obj.system_message.content)

    @patch.object(CognitiveEngine, '_call_llm')
    def test_generate_legal_courtroom_metacognition(self, mock_call_llm):
        mock_call_llm.return_value = '{"meta_narrative": "Je commence à douter de la culpabilité.", "recent_reflection": "Les arguments sur la diligence raisonnable étaient convaincants."}'
        
        engine = CognitiveEngine()
        state = CognitiveAgentState(
            agent_id="judge_1",
            name="Le Juge",
            tensions={"prudence_vs_rapidite": 0.8, "offensive_vs_negociation": 0.2, "procedure_vs_equite": 0.4}
        )
        
        res = engine.generate_legal_courtroom_metacognition(
            agent_name="Le Juge",
            state=state,
            round_idx=1,
            prosecutor_speech="L\'accusé a commis un vice caché flagrant.",
            defense_speech="La diligence a été respectée.",
            verdict="Relaxe temporaire",
            clerk_analysis="Débats équilibrés.",
            last_stim="Nouveau témoignage"
        )
        
        self.assertEqual(res["meta_narrative"], "Je commence à douter de la culpabilité.")
        self.assertEqual(res["recent_reflection"], "Les arguments sur la diligence raisonnable étaient convaincants.")
        mock_call_llm.assert_called_once()


if __name__ == '__main__':
    unittest.main()
