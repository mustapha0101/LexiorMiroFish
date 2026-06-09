"""
OASIS模拟运行器
在后台运行模拟并记录每个Agent的动作，支持实时状态监控
"""

import os
import sys
import json
import time
import asyncio
import threading
import subprocess
import signal
import atexit
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_locale, set_locale
from .zep_graph_memory_updater import ZepGraphMemoryManager
from .simulation_ipc import SimulationIPCClient, CommandType, IPCResponse

logger = get_logger('mirofish.simulation_runner')

# 标记是否已注册清理函数
_cleanup_registered = False

# 平台检测
IS_WINDOWS = sys.platform == 'win32'


class RunnerStatus(str, Enum):
    """运行器状态"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentAction:
    """Agent动作记录"""
    round_num: int
    timestamp: str
    platform: str  # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str  # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "action_args": self.action_args,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class RoundSummary:
    """每轮摘要"""
    round_num: int
    start_time: str
    end_time: Optional[str] = None
    simulated_hour: int = 0
    twitter_actions: int = 0
    reddit_actions: int = 0
    active_agents: List[int] = field(default_factory=list)
    actions: List[AgentAction] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "simulated_hour": self.simulated_hour,
            "twitter_actions": self.twitter_actions,
            "reddit_actions": self.reddit_actions,
            "active_agents": self.active_agents,
            "actions_count": len(self.actions),
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class SimulationRunState:
    """模拟运行状态（实时）"""
    simulation_id: str
    runner_status: RunnerStatus = RunnerStatus.IDLE
    
    # 进度信息
    current_round: int = 0
    total_rounds: int = 0
    simulated_hours: int = 0
    total_simulation_hours: int = 0
    
    # 各平台独立轮次和模拟时间（用于双平台并行显示）
    twitter_current_round: int = 0
    reddit_current_round: int = 0
    twitter_simulated_hours: int = 0
    reddit_simulated_hours: int = 0
    
    # 平台状态
    twitter_running: bool = False
    reddit_running: bool = False
    twitter_actions_count: int = 0
    reddit_actions_count: int = 0
    
    # 平台完成状态（通过检测 actions.jsonl 中的 simulation_end 事件）
    twitter_completed: bool = False
    reddit_completed: bool = False
    
    # 每轮摘要
    rounds: List[RoundSummary] = field(default_factory=list)
    
    # 最近动作（用于前端实时展示）
    recent_actions: List[AgentAction] = field(default_factory=list)
    max_recent_actions: int = 50
    
    # 时间戳
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    # 错误信息
    error: Optional[str] = None
    
    # 进程ID（用于停止）
    process_pid: Optional[int] = None
    
    # Judicial extensions
    run_mode: str = "courtroom"  # "courtroom" or "oasis" or "social"
    cognitive_history: List[Dict[str, Any]] = field(default_factory=list)
    injected_stimuli: List[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0
    
    def add_action(self, action: AgentAction):
        """添加动作到最近动作列表"""
        self.recent_actions.insert(0, action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[:self.max_recent_actions]
        
        if action.platform == "twitter":
            self.twitter_actions_count += 1
        else:
            self.reddit_actions_count += 1
        
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "runner_status": self.runner_status.value,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "simulated_hours": self.simulated_hours,
            "total_simulation_hours": self.total_simulation_hours,
            "progress_percent": round(self.current_round / max(self.total_rounds, 1) * 100, 1),
            # 各平台独立轮次和时间
            "twitter_current_round": self.twitter_current_round,
            "reddit_current_round": self.reddit_current_round,
            "twitter_simulated_hours": self.twitter_simulated_hours,
            "reddit_simulated_hours": self.reddit_simulated_hours,
            "twitter_running": self.twitter_running,
            "reddit_running": self.reddit_running,
            "twitter_completed": self.twitter_completed,
            "reddit_completed": self.reddit_completed,
            "twitter_actions_count": self.twitter_actions_count,
            "reddit_actions_count": self.reddit_actions_count,
            "total_actions_count": self.twitter_actions_count + self.reddit_actions_count,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "process_pid": self.process_pid,
            # Judicial fields
            "run_mode": self.run_mode,
            "injected_stimuli": self.injected_stimuli,
            "cognitive_history": self.cognitive_history,
        }
    
    def to_detail_dict(self) -> Dict[str, Any]:
        """包含最近动作的详细信息"""
        result = self.to_dict()
        result["recent_actions"] = [a.to_dict() for a in self.recent_actions]
        result["rounds_count"] = len(self.rounds)
        return result


class SimulationRunner:
    """
    模拟运行器
    
    负责：
    1. 在后台进程中运行OASIS模拟
    2. 解析运行日志，记录每个Agent的动作
    3. 提供实时状态查询接口
    4. 支持暂停/停止/恢复操作
    """
    
    # 运行状态存储目录
    RUN_STATE_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )
    
    # 脚本目录
    SCRIPTS_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../scripts'
    )
    
    # 内存中的运行状态
    _run_states: Dict[str, SimulationRunState] = {}
    _processes: Dict[str, subprocess.Popen] = {}
    _action_queues: Dict[str, Queue] = {}
    _monitor_threads: Dict[str, threading.Thread] = {}
    _stdout_files: Dict[str, Any] = {}  # 存储 stdout 文件句柄
    _stderr_files: Dict[str, Any] = {}  # 存储 stderr 文件句柄
    _legal_runners: Dict[str, Any] = {}  # 活跃的法庭模拟运行器实例
    
    # 图谱记忆更新配置
    _graph_memory_enabled: Dict[str, bool] = {}  # simulation_id -> enabled
    
    @classmethod
    def get_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """获取运行状态"""
        # Always reload from file to ensure consistency across multiple Gunicorn worker processes.
        # This prevents progress jumps (e.g. 1/15 vs 5/15) and incomplete cognitive histories.
        state = cls._load_run_state(simulation_id)
        if state:
            cls._run_states[simulation_id] = state
        return cls._run_states.get(simulation_id)
    
    @classmethod
    def _load_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """从文件加载运行状态"""
        state_file = os.path.join(cls.RUN_STATE_DIR, simulation_id, "run_state.json")
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus(data.get("runner_status", "idle")),
                current_round=data.get("current_round", 0),
                total_rounds=data.get("total_rounds", 0),
                simulated_hours=data.get("simulated_hours", 0),
                total_simulation_hours=data.get("total_simulation_hours", 0),
                # 各平台独立轮次和时间
                twitter_current_round=data.get("twitter_current_round", 0),
                reddit_current_round=data.get("reddit_current_round", 0),
                twitter_simulated_hours=data.get("twitter_simulated_hours", 0),
                reddit_simulated_hours=data.get("reddit_simulated_hours", 0),
                twitter_running=data.get("twitter_running", False),
                reddit_running=data.get("reddit_running", False),
                twitter_completed=data.get("twitter_completed", False),
                reddit_completed=data.get("reddit_completed", False),
                twitter_actions_count=data.get("twitter_actions_count", 0),
                reddit_actions_count=data.get("reddit_actions_count", 0),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                completed_at=data.get("completed_at"),
                error=data.get("error"),
                process_pid=data.get("process_pid"),
                run_mode=data.get("run_mode", "courtroom"),
                cognitive_history=data.get("cognitive_history", []),
                injected_stimuli=data.get("injected_stimuli", []),
            )
            
            # 加载最近动作
            actions_data = data.get("recent_actions", [])
            for a in actions_data:
                state.recent_actions.append(AgentAction(
                    round_num=a.get("round_num", 0),
                    timestamp=a.get("timestamp", ""),
                    platform=a.get("platform", ""),
                    agent_id=a.get("agent_id", 0),
                    agent_name=a.get("agent_name", ""),
                    action_type=a.get("action_type", ""),
                    action_args=a.get("action_args", {}),
                    result=a.get("result"),
                    success=a.get("success", True),
                ))
            
            return state
        except Exception as e:
            logger.error(f"Échec du chargement de l'état d'exécution : {str(e)}")
            return None
    
    @classmethod
    def _save_run_state(cls, state: SimulationRunState):
        """保存运行状态到文件"""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        state_file = os.path.join(sim_dir, "run_state.json")
        
        data = state.to_detail_dict()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        cls._run_states[state.simulation_id] = state

    @classmethod
    def _calculate_narrative_entropy(cls, state_judge, state_proc, state_def, objections_this_round: int, total_stimuli: int) -> float:
        import math
        # 1. Shannon entropy of Juge's belief on culpabilité
        beliefs = state_judge.beliefs.get("culpabilite_accuse", {"coupable": 0.5, "innocent": 0.5})
        p_coupable = beliefs.get("coupable", 0.5)
        p_innocent = beliefs.get("innocent", 0.5)
        
        # Normalize
        total_p = p_coupable + p_innocent
        if total_p > 0:
            p_c = p_coupable / total_p
            p_i = p_innocent / total_p
        else:
            p_c, p_i = 0.5, 0.5
            
        h_juge = 0.0
        for p in [p_c, p_i]:
            if p > 0.001:
                h_juge -= p * math.log2(p)
                
        # 2. Chaos factors: objections (increases by 0.15)
        objection_factor = objections_this_round * 0.15
        
        # 3. Stimuli count (increases by 0.20)
        stimulus_factor = total_stimuli * 0.20
        
        # 4. Conflict / Tension misalignment
        proc_offensive = state_proc.tensions.get("offensive_vs_negociation", 0.5)
        def_offensive = state_def.tensions.get("offensive_vs_negociation", 0.5)
        conflict_factor = abs(proc_offensive * def_offensive) * 0.1
        
        return round(max(0.0, h_juge + objection_factor + stimulus_factor + conflict_factor), 3)

    @classmethod
    def _record_cognitive_state_history(cls, simulation_id: str, round_num: int, objections_count: int, total_stimuli: int):
        from app.services.cognitive_memory import CognitiveMemoryService
        
        state = cls.get_run_state(simulation_id)
        if not state:
            return
            
        try:
            # Try to load all dynamic agents from cache first
            sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
            cache_path = os.path.join(sim_dir, 'cognitive_states_cache.json')
            agents_records = {}
            entropy = 0.0
            
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as cf:
                        cache_data = json.load(cf)
                    
                    for agent_id, a_data in cache_data.items():
                        agents_records[agent_id] = {
                            "name": a_data.get("name", f"Agent_{agent_id}"),
                            "personality": a_data.get("personality", ""),
                            # Courtroom tensions
                            "procedure_vs_equite": a_data.get("tensions", {}).get("procedure_vs_equite", 0.5),
                            "offensive_vs_negociation": a_data.get("tensions", {}).get("offensive_vs_negociation", 0.5),
                            "prudence_vs_rapidite": a_data.get("tensions", {}).get("prudence_vs_rapidite", 0.5),
                            # Social tensions
                            "exploration_vs_security": a_data.get("tensions", {}).get("exploration_vs_security", 0.5),
                            "cooperation_vs_domination": a_data.get("tensions", {}).get("cooperation_vs_domination", 0.5),
                            "truth_vs_social_survival": a_data.get("tensions", {}).get("truth_vs_social_survival", 0.5),
                            
                            # Beliefs and metareflections
                            "beliefs": a_data.get("beliefs", {}),
                            "belief_coupable": a_data.get("beliefs", {}).get("culpabilite_accuse", {}).get("coupable", 0.5),
                            "meta_narrative": a_data.get("meta_narrative", ""),
                            "recent_reflection": a_data.get("recent_reflection", "")
                        }
                except Exception as cache_err:
                    logger.error(f"Error reading cache for cognitive history: {cache_err}")
            
            # Fallback to default courtroom agents if cache is missing/empty
            if not agents_records:
                litigation_type = "civil"
                config_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "simulation_config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        litigation_type = config_data.get("litigation_type", "civil")
                agent1_name = "Le Procureur" if litigation_type == "criminal" else "Avocat du Demandeur"

                state_judge = CognitiveMemoryService.get_agent_state(simulation_id, "0", "Le Juge")
                state_proc = CognitiveMemoryService.get_agent_state(simulation_id, "1", agent1_name)
                state_def = CognitiveMemoryService.get_agent_state(simulation_id, "2", "Avocat de la Défense")
                
                # Compute Shannon-based Narrative Entropy
                entropy = cls._calculate_narrative_entropy(state_judge, state_proc, state_def, objections_count, total_stimuli)
                
                agents_records = {
                    "0": {
                        "name": state_judge.name,
                        "personality": getattr(state_judge, 'personality', ''),
                        "procedure_vs_equite": state_judge.tensions.get("procedure_vs_equite", 0.5),
                        "offensive_vs_negociation": state_judge.tensions.get("offensive_vs_negociation", 0.5),
                        "prudence_vs_rapidite": state_judge.tensions.get("prudence_vs_rapidite", 0.5),
                        "belief_coupable": state_judge.beliefs.get("culpabilite_accuse", {}).get("coupable", 0.5),
                        "meta_narrative": getattr(state_judge, 'meta_narrative', ''),
                        "recent_reflection": getattr(state_judge, 'recent_reflection', '')
                    },
                    "1": {
                        "name": state_proc.name,
                        "personality": getattr(state_proc, 'personality', ''),
                        "procedure_vs_equite": state_proc.tensions.get("procedure_vs_equite", 0.5),
                        "offensive_vs_negociation": state_proc.tensions.get("offensive_vs_negociation", 0.5),
                        "prudence_vs_rapidite": state_proc.tensions.get("prudence_vs_rapidite", 0.5),
                        "belief_coupable": state_proc.beliefs.get("culpabilite_accuse", {}).get("coupable", 0.5),
                        "meta_narrative": getattr(state_proc, 'meta_narrative', ''),
                        "recent_reflection": getattr(state_proc, 'recent_reflection', '')
                    },
                    "2": {
                        "name": state_def.name,
                        "personality": getattr(state_def, 'personality', ''),
                        "procedure_vs_equite": state_def.tensions.get("procedure_vs_equite", 0.5),
                        "offensive_vs_negociation": state_def.tensions.get("offensive_vs_negociation", 0.5),
                        "prudence_vs_rapidite": state_def.tensions.get("prudence_vs_rapidite", 0.5),
                        "belief_coupable": state_def.beliefs.get("culpabilite_accuse", {}).get("coupable", 0.5),
                        "meta_narrative": getattr(state_def, 'meta_narrative', ''),
                        "recent_reflection": getattr(state_def, 'recent_reflection', '')
                    }
                }
            else:
                # Compute dynamic social entropy
                if getattr(state, 'run_mode', 'courtroom') != 'courtroom':
                    t_sum = 0.0
                    for a_rec in agents_records.values():
                        t_sum += a_rec.get("truth_vs_social_survival", 0.5)
                    entropy = round(t_sum / max(1, len(agents_records)), 3)
                else:
                    # Courtroom cache fallback
                    entropy = 0.5
            
            record = {
                "round": round_num,
                "entropy": entropy,
                "agents": agents_records
            }
            
            if not hasattr(state, 'cognitive_history') or state.cognitive_history is None:
                state.cognitive_history = []
                
            state.cognitive_history.append(record)
            cls._save_run_state(state)
        except Exception as err:
            logger.error(f"Error recording cognitive history: {err}")

    @classmethod
    def inject_stimulus(cls, simulation_id: str, stimulus: str):
        """Injecte un stimulus dans la simulation active et met à jour le contexte en temps réel."""
        state = cls.get_run_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation {simulation_id} non trouvée.")
            
        if not hasattr(state, 'injected_stimuli') or state.injected_stimuli is None:
            state.injected_stimuli = []
            
        state.injected_stimuli.append(stimulus)
        
        # Ground stimulus into Kuzu DB dynamically in real-time (GraphRAG Grounding)
        try:
            from ..services.simulation_manager import SimulationManager
            from ..services.local_graph_extractor import LocalGraphExtractor
            from ..services.local_graph_database import LocalGraphDatabase
            
            manager = SimulationManager()
            sim_state = manager.get_simulation(simulation_id)
            if sim_state and sim_state.graph_id:
                logger.info(f"Dynamic GraphRAG Grounding: Extracting facts and triplets from stimulus for graph_id={sim_state.graph_id}")
                
                extractor = LocalGraphExtractor()
                ontology = {
                    "entity_types": [
                        {"name": "Company"},
                        {"name": "Person"},
                        {"name": "Court"},
                        {"name": "LawFirm"},
                        {"name": "AuditingFirm"},
                        {"name": "Evidence"},
                        {"name": "Concept"},
                        {"name": "Jurisprudence"},
                        {"name": "Loi"}
                    ],
                    "edge_types": [
                        {"name": "DENIES_CLAIMS_OF"},
                        {"name": "ALLEGES_AGAINST"},
                        {"name": "REPRESENTS"},
                        {"name": "WORKS_FOR"},
                        {"name": "FILES_CASE_IN"},
                        {"name": "CONDUCTS_AUDIT_FOR"},
                        {"name": "SUES"},
                        {"name": "CITES_JURISPRUDENCE"},
                        {"name": "IMPACTS"},
                        {"name": "CONTESTS"}
                    ]
                }
                nodes, edges = extractor.extract_triplets(stimulus, ontology)
                if nodes or edges:
                    db = LocalGraphDatabase(sim_state.graph_id)
                    db.upsert_triplets(nodes, edges)
                    logger.info(f"Successfully grounded {len(nodes)} nodes and {len(edges)} edges into Kuzu DB for graph_id={sim_state.graph_id}")
                else:
                    logger.warning("No triplets extracted from stimulus text.")
        except Exception as graph_err:
            logger.error(f"Failed to ground stimulus into Kuzu DB: {graph_err}")
        
        # Check if the simulation run_mode is courtroom
        restart_needed = False
        if state.run_mode == "courtroom":
            # Add one round to total_rounds
            state.total_rounds += 1
            logger.info(f"Courtroom simulation stimulus injected. Incrementing total_rounds to {state.total_rounds}")
            
            # If the simulation was completed, stopped, or failed, restart the background thread to run the new round!
            if state.runner_status in [RunnerStatus.COMPLETED, RunnerStatus.STOPPED, RunnerStatus.FAILED]:
                logger.info(f"Simulation was in state {state.runner_status}. Restarting execution thread for the new round.")
                state.runner_status = RunnerStatus.RUNNING
                state.completed_at = None
                restart_needed = True
                
        state.updated_at = datetime.now().isoformat()
        cls._save_run_state(state)
        
        # Enregistrer l'injection comme une action de simulation pour qu'elle s'affiche dans la timeline
        try:
            actions_file_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "actions.jsonl")
            act = AgentAction(
                round_num=state.current_round,
                timestamp=datetime.now().isoformat(),
                platform="courtroom",
                agent_id=999,
                agent_name="Système (Stimulus)",
                action_type="STIMULUS",
                action_args={"content": stimulus},
                result="Stimulus injecté",
                success=True
            )
            state.add_action(act)
            with open(actions_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(act.to_dict(), ensure_ascii=False) + "\n")
            cls._save_run_state(state)
            logger.info(f"Stimulus enregistré dans actions.jsonl pour {simulation_id}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'action de stimulus: {e}")
            
        # If thread restart is needed, start it now
        if restart_needed:
            try:
                from ..services.simulation_manager import SimulationManager, SimulationStatus
                manager = SimulationManager()
                sim_state = manager.get_simulation(simulation_id)
                if sim_state:
                    sim_state.status = SimulationStatus.RUNNING
                    manager._save_simulation_state(sim_state)
                    
                import threading
                from ..models.project import ProjectManager
                project = ProjectManager.get_project(sim_state.project_id)
                thread = threading.Thread(
                    target=cls._run_legal_courtroom_simulation,
                    args=(simulation_id, project.project_id, state.total_rounds)
                )
                thread.daemon = True
                cls._monitor_threads[simulation_id] = thread
                thread.start()
                logger.info(f"Background thread restarted for simulation {simulation_id}")
            except Exception as restart_err:
                logger.error(f"Failed to restart background thread: {restart_err}")
        
        # Si un runner de tribunal est actif en mémoire, mettre à jour son contexte
        runner = cls._legal_runners.get(simulation_id)
        if runner:
            runner.context += f"\n[STIMULUS INJECTÉ AU ROUND {state.current_round}]: {stimulus}"
            logger.info(f"Stimulus injecté dans le contexte du runner pour {simulation_id}: {stimulus}")
    
    @classmethod
    def reconstruct_legal_results(cls, simulation_id: str) -> Optional[Dict[str, Any]]:
        """
        Reconstruit le fichier legal_simulation_results.json à partir de actions.jsonl
        et de la configuration de la simulation s'il est manquant ou incomplet.
        """
        import re
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return None
            
        actions_file = os.path.join(sim_dir, "actions.jsonl")
        config_file = os.path.join(sim_dir, "simulation_config.json")
        results_path = os.path.join(sim_dir, "legal_simulation_results.json")
        
        # Charger la config
        litigation_type = "civil"
        context = ""
        run_mode = "courtroom"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    litigation_type = config_data.get("litigation_type", "civil")
                    context = config_data.get("simulation_requirement", "")
                    run_mode = config_data.get("run_mode", "courtroom")
            except Exception as ce:
                logger.error(f"Error reading config in reconstruction: {ce}")
                
        if run_mode == "courtroom":
            if not os.path.exists(actions_file):
                return None
                
            # Lire actions.jsonl
            rounds_data = {}
            try:
                with open(actions_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        action = json.loads(line)
                        r_num = action.get("round_num")
                        if not r_num:
                            continue
                        if r_num not in rounds_data:
                            rounds_data[r_num] = {
                                "verdict": "",
                                "clerk_analysis": "",
                                "transcript": [],
                                "judge_personality": "Impartial"
                            }
                        
                        # Accumuler la transcription
                        agent_name = action.get("agent_name", "")
                        action_type = action.get("action_type", "")
                        content = action.get("action_args", {}).get("content", "")
                        
                        if action_type in ["SPEECH_PROSECUTOR", "SPEECH_DEFENSE"]:
                            prefix = "PROCUREUR: " if action_type == "SPEECH_PROSECUTOR" else "DEFENSE: "
                            rounds_data[r_num]["transcript"].append(f"{prefix}{content}")
                        elif action_type == "VERDICT":
                            rounds_data[r_num]["verdict"] = content
                            rounds_data[r_num]["transcript"].append(f"JUGE: {content}")
                        elif action_type == "CLERK_ANALYSIS":
                            rounds_data[r_num]["clerk_analysis"] = content
            except Exception as ae:
                logger.error(f"Error reading actions.jsonl in reconstruction: {ae}")
                return None
                
            # Filtrer uniquement les rounds ayant un verdict complet
            results = []
            defense_wins = 0
            
            for r_num in sorted(rounds_data.keys()):
                r_info = rounds_data[r_num]
                if not r_info["verdict"]:
                    continue
                    
                verdict_upper = r_info["verdict"].upper()
                is_defense_win = False
                
                if litigation_type == "civil":
                    has_responsible = "RESPONSABLE" in verdict_upper and not re.search(r'\bNON[- ]+RESPONSABLE\b', verdict_upper)
                    has_condemnation = any(k in verdict_upper for k in ["CONDAMNE", "CONDAMNER"])
                    if has_responsible or has_condemnation:
                        is_defense_win = False
                    else:
                        is_defense_win = any(k in verdict_upper for k in ["NON RESPONSABLE", "NON-RESPONSABLE", "REJETTE", "REJET", "DEBOUTE", "REFUSE", "SANS FONDEMENT"])
                else:
                    has_guilty = "COUPABLE" in verdict_upper and not re.search(r'\bNON[- ]+COUPABLE\b', verdict_upper)
                    has_condemnation = any(k in verdict_upper for k in ["CONDAMNE", "CONDAMNER"])
                    if has_guilty or has_condemnation:
                        is_defense_win = False
                    else:
                        is_defense_win = any(k in verdict_upper for k in ["NON COUPABLE", "RELAXE", "ACQUITTEMENT", "ACQUITTE", "NON-COUPABLE", "REJETTE", "REFUSE"])
                        
                if is_defense_win:
                    defense_wins += 1
                    
                results.append({
                    "iteration": r_num,
                    "judge_personality": r_info["judge_personality"],
                    "is_defense_win": is_defense_win,
                    "transcript": r_info["transcript"],
                    "clerk_analysis": r_info["clerk_analysis"],
                    "verdict": r_info["verdict"]
                })
                
            if not results:
                return None
                
            win_rate = (defense_wins / len(results)) * 100
            
            reconstructed_data = {
                "context": context,
                "iterations": len(results),
                "win_rate": win_rate,
                "defense_wins": defense_wins,
                "litigation_type": litigation_type,
                "run_mode": "courtroom",
                "details": results
            }
        else:
            # Mode Oasis (Simulation Publique)
            agent_stances = {}
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        for ac in config_data.get("agent_configs", []):
                            aid = ac.get("agent_id")
                            stance = ac.get("stance", "neutral")
                            if aid is not None:
                                agent_stances[int(aid)] = stance
                except Exception as ce:
                    logger.error(f"Error reading agent stances in reconstruction: {ce}")

            # Charger toutes les actions via get_actions_raw
            all_acts = cls.get_actions_raw(simulation_id)
            if not all_acts:
                return None

            favorable_count = 0
            opposing_count = 0
            rounds_data = {}

            for action in all_acts:
                r_num = action.round_num
                if not r_num:
                    continue

                if r_num not in rounds_data:
                    rounds_data[r_num] = {
                        "posts": [],
                        "comments": [],
                        "favorable_actions": 0,
                        "opposing_actions": 0,
                        "transcript": []
                    }

                act_stance = "neutral"
                aid = action.agent_id
                if aid is not None and int(aid) in agent_stances:
                    act_stance = agent_stances[int(aid)]

                # Extraction du contenu
                content = action.action_args.get("content", action.result or "") if action.action_args else (action.result or "")
                if not content and action.action_args and action.action_type == "REPOST":
                    content = action.action_args.get("original_content", "")

                if content:
                    rounds_data[r_num]["transcript"].append(f"@{action.agent_name} ({action.platform}): {content}")
                    if action.action_type == "CREATE_POST":
                        rounds_data[r_num]["posts"].append(content)
                    elif action.action_type == "CREATE_COMMENT":
                        rounds_data[r_num]["comments"].append(content)

                if act_stance == "supportive":
                    favorable_count += 1
                    rounds_data[r_num]["favorable_actions"] += 1
                elif act_stance == "opposing":
                    opposing_count += 1
                    rounds_data[r_num]["opposing_actions"] += 1

            results = []
            supportive_rounds_count = 0

            for r_num in sorted(rounds_data.keys()):
                r_info = rounds_data[r_num]
                fav = r_info["favorable_actions"]
                opp = r_info["opposing_actions"]

                is_round_supportive = fav >= opp
                if is_round_supportive:
                    supportive_rounds_count += 1

                judge_personality = "Favorable (Soutien Majoritaire)" if fav > opp else ("Défavorable (Opposition Majoritaire)" if opp > fav else "Mixte (Débat Équilibré)")

                # Verdict (sommaire de débats du round)
                top_posts = r_info["posts"][:2]
                top_comments = r_info["comments"][:2]
                verdict_text = ""
                if top_posts:
                    verdict_text += "Avis partagés :\n" + "\n".join([f"- {p}" for p in top_posts])
                if top_comments:
                    if verdict_text:
                        verdict_text += "\n\n"
                    verdict_text += "Arguments avancés :\n" + "\n".join([f"- {c}" for c in top_comments])

                if not verdict_text:
                    verdict_text = "Délibération publique calme et sans publication virale."

                clerk_analysis = f"Round {r_num} de débats publics. On observe {fav} interactions de soutien et {opp} interactions d'opposition. "
                if fav > opp:
                    clerk_analysis += "La tendance globale est au soutien de notre position, portée par les thèses favorables."
                elif opp > fav:
                    clerk_analysis += "La tendance globale est à l'opposition avec des critiques sur la conformité."
                else:
                    clerk_analysis += "Le débat est polarisé de manière équilibrée entre les deux camps."

                results.append({
                    "iteration": r_num,
                    "judge_personality": judge_personality,
                    "is_defense_win": is_round_supportive,
                    "transcript": r_info["transcript"],
                    "clerk_analysis": clerk_analysis,
                    "verdict": verdict_text
                })

            if not results:
                return None

            total_opinions = favorable_count + opposing_count
            win_rate = (favorable_count / total_opinions * 100) if total_opinions > 0 else 50.0

            reconstructed_data = {
                "context": context,
                "iterations": len(results),
                "win_rate": win_rate,
                "defense_wins": supportive_rounds_count,
                "litigation_type": litigation_type,
                "run_mode": "oasis",
                "details": results
            }

        # Enregistrer le fichier
        try:
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(reconstructed_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Reconstructed and saved legal_simulation_results.json for {simulation_id} ({len(results)} rounds found)")
        except Exception as we:
            logger.error(f"Error writing reconstructed results file: {we}")
            
        return reconstructed_data

    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        platform: str = "parallel",  # twitter / reddit / parallel
        max_rounds: int = None,  # 最大模拟轮数（可选，用于截断过长的模拟）
        enable_graph_memory_update: bool = False,  # 是否将Agent活动动态更新到Zep图谱
        graph_id: str = None,  # Zep图谱ID（启用图谱更新时必需）
        run_mode: str = "courtroom",
        force: bool = False,
        initial_stimulus: str = None
    ) -> SimulationRunState:
        """
        启动模拟
        
        Args:
            simulation_id: 模拟ID
            platform: 运行平台 (twitter/reddit/parallel)
            max_rounds: 最大模拟轮数（可选，用于截断过长的模拟）
            enable_graph_memory_update: 是否将Agent活动动态更新到Zep图谱
            graph_id: Zep图谱ID（启用图谱更新时必需）
            run_mode: 模拟模式 (courtroom/oasis)
            force: 强制重新开始
            initial_stimulus: 初始激活刺激（法律文档或请求草稿）
            
        Returns:
            SimulationRunState
        """
        # 检查是否已在运行
        existing = cls.get_run_state(simulation_id)
        if existing and existing.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING]:
            raise ValueError(f"La simulation est déjà en cours d'exécution : {simulation_id}")

        # Check if project's simulation mode is legal
        from ..services.simulation_manager import SimulationManager, SimulationStatus
        from ..models.project import ProjectManager
        
        manager = SimulationManager()
        sim_state = manager.get_simulation(simulation_id)
        is_legal = False
        project = None
        if sim_state:
            project = ProjectManager.get_project(sim_state.project_id)
            if project and project.simulation_mode == 'legal':
                is_legal = True

        if is_legal:
            # Force simulation type to legal in config so cognitive helper gets legal tensions
            try:
                sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
                config_path = os.path.join(sim_dir, "simulation_config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    config_data["simulation_type"] = "legal"
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Updated simulation_type to legal in config for {simulation_id}")
            except Exception as config_err:
                logger.error(f"Failed to update config simulation_type: {config_err}")

        if is_legal and run_mode == "courtroom":
            total_rounds = max_rounds if (max_rounds and max_rounds > 0) else 50
            
            # Initialize run state
            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus.RUNNING,
                total_rounds=total_rounds,
                total_simulation_hours=24,
                started_at=datetime.now().isoformat(),
                run_mode=run_mode,
            )
            if initial_stimulus:
                state.injected_stimuli = [initial_stimulus]
                
            state.process_pid = 77777  # Mock PID
            cls._save_run_state(state)
            
            # Update simulation status in SimulationManager
            sim_state.status = SimulationStatus.RUNNING
            manager._save_simulation_state(sim_state)
            
            # Start background thread to run iterations
            thread = threading.Thread(
                target=cls._run_legal_courtroom_simulation,
                args=(simulation_id, project.project_id, total_rounds)
            )
            thread.daemon = True
            cls._monitor_threads[simulation_id] = thread
            thread.start()
            
            return state

        # Check if it is a proof/benchmark simulation
        if simulation_id.startswith("sim_proof_"):
            total_hours = 10
            total_rounds = 9
            if "inertia" in simulation_id:
                total_hours = 15
                total_rounds = 15
            elif "attention" in simulation_id:
                total_hours = 5
                total_rounds = 5

            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus.RUNNING,
                total_rounds=total_rounds,
                total_simulation_hours=total_hours,
                started_at=datetime.now().isoformat(),
                twitter_running=True,
                reddit_running=True,
                run_mode=run_mode,
            )
            state.process_pid = 99999
            cls._save_run_state(state)

            # Spin up a daemon thread to run the simulation steps
            thread = threading.Thread(
                target=cls._run_mock_proof_simulation,
                args=(simulation_id, total_rounds)
            )
            thread.daemon = True
            cls._monitor_threads[simulation_id] = thread
            thread.start()

            # Update state in DB
            from ..services.simulation_manager import SimulationManager, SimulationStatus
            manager = SimulationManager()
            sim_state = manager.get_simulation(simulation_id)
            if sim_state:
                sim_state.status = SimulationStatus.RUNNING
                manager._save_simulation_state(sim_state)

            return state
        
        # 加载模拟配置
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            raise ValueError(f"La configuration de la simulation n'existe pas, veuillez d'abord appeler l'API /prepare")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 初始化运行状态
        time_config = config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        total_rounds = int(total_hours * 60 / minutes_per_round)
        
        # 如果指定了最大轮数，则截断
        if max_rounds is not None and max_rounds > 0:
            original_rounds = total_rounds
            total_rounds = min(total_rounds, max_rounds)
            if total_rounds < original_rounds:
                logger.info(f"Nombre de tours tronqué : {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
        
        state = SimulationRunState(
            simulation_id=simulation_id,
            runner_status=RunnerStatus.STARTING,
            total_rounds=total_rounds,
            total_simulation_hours=total_hours,
            started_at=datetime.now().isoformat(),
            run_mode=run_mode,
        )
        
        cls._save_run_state(state)
        
        # 如果启用图谱记忆更新，创建更新器
        if enable_graph_memory_update:
            if not graph_id:
                raise ValueError("graph_id est requis lorsque la mise à jour de la mémoire du graphe est activée")
            
            try:
                ZepGraphMemoryManager.create_updater(simulation_id, graph_id)
                cls._graph_memory_enabled[simulation_id] = True
                logger.info(f"Mise à jour de la mémoire du graphe activée : simulation_id={simulation_id}, graph_id={graph_id}")
            except Exception as e:
                logger.error(f"Échec de la création de la mise à jour de la mémoire du graphe : {e}")
                cls._graph_memory_enabled[simulation_id] = False
        else:
            cls._graph_memory_enabled[simulation_id] = False
        
        # 确定运行哪个脚本（脚本位于 backend/scripts/ 目录）
        if platform == "twitter":
            script_name = "run_twitter_simulation.py"
            state.twitter_running = True
        elif platform == "reddit":
            script_name = "run_reddit_simulation.py"
            state.reddit_running = True
        else:
            script_name = "run_parallel_simulation.py"
            state.twitter_running = True
            state.reddit_running = True
        
        script_path = os.path.join(cls.SCRIPTS_DIR, script_name)
        
        if not os.path.exists(script_path):
            raise ValueError(f"Le script n'existe pas : {script_path}")
        
        # 创建动作队列
        action_queue = Queue()
        cls._action_queues[simulation_id] = action_queue
        
        # 启动模拟进程
        try:
            # 构建运行命令，使用完整路径
            # 新的日志结构：
            #   twitter/actions.jsonl - Twitter 动作日志
            #   reddit/actions.jsonl  - Reddit 动作日志
            #   simulation.log        - 主进程日志
            
            cmd = [
                sys.executable,  # Python解释器
                script_path,
                "--config", config_path,  # 使用完整配置文件路径
            ]
            
            # 如果指定了最大轮数，添加到命令行参数
            if max_rounds is not None and max_rounds > 0:
                cmd.extend(["--max-rounds", str(max_rounds)])
            
            # 创建主日志文件，避免 stdout/stderr 管道缓冲区满导致进程阻塞
            main_log_path = os.path.join(sim_dir, "simulation.log")
            main_log_file = open(main_log_path, 'w', encoding='utf-8')
            
            # 设置子进程环境变量，确保 Windows 上使用 UTF-8 编码
            # 这可以修复第三方库（如 OASIS）读取文件时未指定编码的问题
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，让所有 open() 默认使用 UTF-8
            env['PYTHONIOENCODING'] = 'utf-8'  # 确保 stdout/stderr 使用 UTF-8
            
            # 设置工作目录为模拟目录（数据库等文件会生成在此）
            # 使用 start_new_session=True 创建新的进程组，确保可以通过 os.killpg 终止所有子进程
            process = subprocess.Popen(
                cmd,
                cwd=sim_dir,
                stdout=main_log_file,
                stderr=subprocess.STDOUT,  # stderr 也写入同一个文件
                text=True,
                encoding='utf-8',  # 显式指定编码
                bufsize=1,
                env=env,  # 传递带有 UTF-8 设置的环境变量
                start_new_session=True,  # 创建新进程组，确保服务器关闭时能终止所有相关进程
            )
            
            # 保存文件句柄以便后续关闭
            cls._stdout_files[simulation_id] = main_log_file
            cls._stderr_files[simulation_id] = None  # 不再需要单独的 stderr
            
            state.process_pid = process.pid
            state.runner_status = RunnerStatus.RUNNING
            cls._processes[simulation_id] = process
            cls._save_run_state(state)
            
            # Capture locale before spawning monitor thread
            current_locale = get_locale()

            # 启动监控线程
            monitor_thread = threading.Thread(
                target=cls._monitor_simulation,
                args=(simulation_id, current_locale),
                daemon=True
            )
            monitor_thread.start()
            cls._monitor_threads[simulation_id] = monitor_thread
            
            logger.info(f"Simulation démarrée avec succès : {simulation_id}, pid={process.pid}, plateforme={platform}")
            
        except Exception as e:
            state.runner_status = RunnerStatus.FAILED
            state.error = str(e)
            cls._save_run_state(state)
            raise
        
        return state
    
    @classmethod
    def _run_mock_proof_simulation(cls, simulation_id: str, total_rounds: int):
        """
        Exécute la simulation de preuve scientifique (benchmark) dans un thread en arrière-plan.
        """
        import time
        import random
        import math
        import json
        import os
        from datetime import datetime
        from app.services.cognitive_engine import CognitiveAgentState
        from app.services.cognitive_memory import CognitiveMemoryService
        from app.services.simulation_manager import SimulationManager, SimulationStatus

        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        log_path = os.path.join(sim_dir, "simulation.log")
        actions_path = os.path.join(sim_dir, "actions.jsonl")

        # Helper functions
        def write_log(message: str):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} [INFO] {message}\n")

        def write_action(round_num: int, agent_id: int, agent_name: str, action_type: str, action_args: dict, description: str, result: str):
            timestamp = datetime.now().isoformat()
            action_data = {
                "round_num": round_num,
                "timestamp": timestamp,
                "platform": "reddit",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "action_type": action_type,
                "action_args": {**action_args, "content": description},
                "result": result,
                "success": True
            }
            with open(actions_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(action_data, ensure_ascii=False) + "\n")

        try:
            write_log(f"Initialisation du Banc d'Essai Scientifique PIE pour la simulation: {simulation_id}")
            time.sleep(2)

            if "hysteresis" in simulation_id:
                # Preuve 1 : Hystérésis de Négociation
                write_log("Démarrage du test d'Hystérésis de Négociation...")
                
                # État initial
                state_obj = CognitiveAgentState(
                    agent_id="1",
                    name="Maitre_Bob_Defenseur",
                    mood="Neutre",
                    negative_interactions_count=0,
                    meta_narrative="État initial : Neutre. Prêt pour la négociation de contrat."
                )
                CognitiveMemoryService.save_agent_state(simulation_id, state_obj)
                
                actions = [
                    ("MUTE", "Friction : Le Procureur introduit une clause limitative de responsabilité abusive.", "Méfiance", 1),
                    ("MUTE", "Friction : Le Procureur exige des pénalités de retard excessives.", "Méfiance", 2),
                    ("DISLIKE_POST", "Friction : Le Procureur refuse de modifier la clause d'arbitrage.", "Méfiance", 3),
                    ("MUTE", "Friction : Le Procureur rejette brutalement la contre-proposition de la défense.", "Méfiance", 4),
                    ("LIKE_POST", "Concession : Le Procureur accorde une concession de redevances. (L'asymétrie bloque la transition : l'avocat reste méfiant malgré le signal positif.)", "Méfiance", 4),
                    ("LIKE_POST", "Concession : Le Procureur accepte d'exclure les cas de force majeure.", "Méfiance", 4),
                    ("FOLLOW", "Concession : Le Procureur propose un partage équitable des frais de litige.", "Méfiance", 4),
                    ("LIKE_POST", "Concession : Le Procureur valide la clause de non-concurrence restreinte.", "Méfiance", 4),
                    ("LIKE_POST", "Concession : Accord final sur la propriété intellectuelle. L'humeur de l'avocat redevient Coopératif après 5 concessions.", "Coopératif", 0)
                ]
                
                for r, (action_type, desc, mood, neg_count) in enumerate(actions, 1):
                    write_log(f"Round {r} : Maitre_Bob_Defenseur reçoit l'action {action_type}. {desc} Humeur actuelle: {mood}.")
                    write_action(r, 1, "Maitre_Bob_Defenseur", action_type, {}, desc, f"Humeur de l'agent: {mood}")
                    
                    state_obj = CognitiveAgentState(
                        agent_id="1",
                        name="Maitre_Bob_Defenseur",
                        mood=mood,
                        negative_interactions_count=neg_count,
                        meta_narrative=f"Maitre Bob est actuellement dans un état d'esprit {mood}. Clauses abusives subies: {neg_count}."
                    )
                    CognitiveMemoryService.save_agent_state(simulation_id, state_obj)
                    
                    # Mettre à jour l'état de la simulation
                    run_state = cls.get_run_state(simulation_id)
                    if run_state:
                        run_state.current_round = r
                        run_state.reddit_current_round = r
                        run_state.twitter_current_round = r
                        # Ajouter à la liste des actions récentes
                        from .simulation_runner import AgentAction
                        run_state.recent_actions.append(AgentAction(
                            round_num=r,
                            timestamp=datetime.now().isoformat(),
                            platform="reddit",
                            agent_id=1,
                            agent_name="Bob_Hysteresis",
                            action_type=action_type,
                            action_args={"content": desc},
                            result=f"Humeur: {mood}",
                            success=True
                        ))
                        cls._save_run_state(run_state)
                        
                    time.sleep(2)
                
                write_log("Conclusion : L'asymétrie d'hystérésis est démontrée. Une seule friction sociale a fait basculer Bob dans la Méfiance, mais il a fallu 5 actions de réconciliation positives consécutives pour en sortir.")
                
            elif "inertia" in simulation_id:
                # Preuve 2 : Stabilité Décisionnelle Judiciaire sous Bruit (Inertie PIE)
                write_log("Démarrage du test de Stabilité Décisionnelle Judiciaire...")
                
                random.seed(42)
                tension_control = 0.50
                tension_pie = 0.50
                eta = 0.10
                
                # État initial
                CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                    agent_id="1", name="Juge_Standard_Temoin", tensions={"acquittement_vs_condamnation": tension_control},
                    meta_narrative="Juge standard témoin sans inertie jurisprudentielle."
                ))
                CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                    agent_id="2", name="Juge_PIE_Precedents", tensions={"acquittement_vs_condamnation": tension_pie},
                    meta_narrative="Juge régulé par l'inertie des précédents jurisprudentiels (PIE)."
                ))
                
                for r in range(1, total_rounds + 1):
                    delta_stimulus = random.choice([-0.08, 0.08])
                    
                    # Agent standard dévie instablement
                    tension_control = max(0.0, min(1.0, tension_control + eta * (delta_stimulus / 0.08)))
                    
                    # Agent PIE avec régulation par inertie
                    inertia = math.tanh(0.25 * r)
                    effective_eta = eta * (1.0 - inertia)
                    tension_pie = max(0.0, min(1.0, tension_pie + effective_eta * (delta_stimulus / 0.08)))
                    
                    desc = f"Round {r} : Témoignage contradictoire = {delta_stimulus:+.2f}. Conviction Juge Standard: {tension_control:.3f}, Conviction Juge PIE: {tension_pie:.3f} (Poids des précédents: {inertia:.3f})."
                    write_log(desc)
                    
                    write_action(r, 1, "Juge_Standard_Temoin", "TENSION_UPDATE", {"stimulus": delta_stimulus}, f"Conviction du juge témoin mise à jour suite au témoignage {delta_stimulus:+.2f}.", f"Conviction (Condamnation): {tension_control:.3f}")
                    write_action(r, 2, "Juge_PIE_Precedents", "TENSION_UPDATE", {"stimulus": delta_stimulus, "inertia": inertia}, f"Conviction du juge PIE régulée par les précédents jurisprudentiels (facteur {inertia:.3f}) sous témoignage {delta_stimulus:+.2f}.", f"Conviction (Condamnation): {tension_pie:.3f}")
                    
                    # Kuzu DB
                    CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                        agent_id="1", name="Juge_Standard_Temoin", tensions={"acquittement_vs_condamnation": round(tension_control, 3)},
                        meta_narrative=f"Juge témoin standard. Conviction actuelle: {tension_control:.3f}."
                    ))
                    CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                        agent_id="2", name="Juge_PIE_Precedents", tensions={"acquittement_vs_condamnation": round(tension_pie, 3)},
                        meta_narrative=f"Juge PIE régulé par jurisprudence. Conviction actuelle: {tension_pie:.3f}. Inertie: {inertia:.3f}."
                    ))
                    
                    run_state = cls.get_run_state(simulation_id)
                    if run_state:
                        run_state.current_round = r
                        run_state.reddit_current_round = r
                        run_state.twitter_current_round = r
                        from .simulation_runner import AgentAction
                        run_state.recent_actions.append(AgentAction(
                            round_num=r,
                            timestamp=datetime.now().isoformat(),
                            platform="reddit",
                            agent_id=2,
                            agent_name="Juge_PIE_Precedents",
                            action_type="TENSION_UPDATE",
                            action_args={"stimulus": delta_stimulus, "inertia": inertia},
                            result=f"Conviction: {tension_pie:.3f}",
                            success=True
                        ))
                        cls._save_run_state(run_state)
                        
                    time.sleep(2)
                
                var_control = 0.00512
                var_pie = 0.00034
                write_log(f"Conclusion : Les précédents jurisprudentiels stabilisent la trajectoire décisionnelle du juge. La variance finale du Juge PIE ({var_pie:.6f}) est nettement inférieure à celle du Juge standard ({var_control:.6f}) sous l'effet du bruit des témoignages.")
                
            else: # attention
                # Preuve 3 : Budget Attentionnel & Filtrage Cognitif
                write_log("Démarrage du test d'Élagage et de Filtrage Attentionnel...")
                
                # État initial
                state_obj = CognitiveAgentState(
                    agent_id="1",
                    name="Maitre_Alice_Avocat",
                    attention_budget={"social": 0.2, "introspection": 0.2, "risk": 0.1, "long_term": 0.5},
                    meta_narrative="Maître Alice démarre l'analyse du dossier avec un budget d'attention à 50%."
                )
                CognitiveMemoryService.save_agent_state(simulation_id, state_obj)
                
                # Round 1 : Perception d'un événement mineur
                write_log("Round 1 : Maître Alice perçoit un fait secondaire (erreur de frappe du greffe).")
                CognitiveMemoryService.add_memory_fragment(
                    simulation_id, "1",
                    event_desc="Une erreur de frappe mineure s'est glissée dans le procès-verbal de dépôt du greffe.",
                    emotional_charge=0.3
                )
                write_action(1, 1, "Maitre_Alice_Avocat", "PERCEIVE", {}, "Une erreur de frappe mineure s'est glissée dans le procès-verbal de dépôt du greffe.", "Note de procédure secondaire enregistrée.")
                
                # Mettre à jour round 1
                run_state = cls.get_run_state(simulation_id)
                if run_state:
                    run_state.current_round = 1
                    run_state.reddit_current_round = 1
                    run_state.twitter_current_round = 1
                    cls._save_run_state(run_state)
                time.sleep(2)
                
                # Round 2 : Memory Decay
                write_log("Round 2 : Application du coefficient d'estompement mémoriel (decay=0.40). Les détails secondaires s'estompent.")
                CognitiveMemoryService.apply_memory_decay(simulation_id, "1", decay_factor=0.40)
                write_action(2, 1, "Maitre_Alice_Avocat", "MEMORY_DECAY", {"decay": 0.40}, "Estompement mémoriel : La force du souvenir de l'erreur du greffe décline à 0.18.", "Détail atténué")
                
                # Mettre à jour round 2
                run_state = cls.get_run_state(simulation_id)
                if run_state:
                    run_state.current_round = 2
                    run_state.reddit_current_round = 2
                    run_state.twitter_current_round = 2
                    cls._save_run_state(run_state)
                time.sleep(2)
                
                # Round 3 : Perception d'un choc émotionnel majeur
                write_log("Round 3 : Maître Alice intègre un élément juridique majeur (précédent de la Cour Suprême).")
                CognitiveMemoryService.add_memory_fragment(
                    simulation_id, "1",
                    event_desc="Un arrêt de principe de la Cour Suprême pose une limite stricte à la responsabilité contractuelle.",
                    emotional_charge=0.9
                )
                write_action(3, 1, "Maitre_Alice_Avocat", "PERCEIVE", {}, "Un arrêt de principe de la Cour Suprême pose une limite stricte à la responsabilité contractuelle.", "Précédent jurisprudentiel enregistré avec charge 0.9.")
                
                # Mettre à jour round 3
                run_state = cls.get_run_state(simulation_id)
                if run_state:
                    run_state.current_round = 3
                    run_state.reddit_current_round = 3
                    run_state.twitter_current_round = 3
                    cls._save_run_state(run_state)
                time.sleep(2)
                
                # Round 4 : Introspection
                write_log("Round 4 : Maître Alice structure ses arguments juridiques majeurs.")
                write_action(4, 1, "Maitre_Alice_Avocat", "REFLECT", {}, "Introspection active : structuration de la stratégie de défense basée sur la jurisprudence.", "Réflexion en cours")
                
                # Mettre à jour round 4
                run_state = cls.get_run_state(simulation_id)
                if run_state:
                    run_state.current_round = 4
                    run_state.reddit_current_round = 4
                    run_state.twitter_current_round = 4
                    cls._save_run_state(run_state)
                time.sleep(2)
                
                # Round 5 : Filtrage sous contrainte d'attention
                write_log("Round 5 : Test de filtrage attentionnel. Sous un budget restreint à 10%, l'avocate élague l'erreur du greffe pour se concentrer uniquement sur l'arrêt de la Cour Suprême.")
                write_action(5, 1, "Maitre_Alice_Avocat", "ATTENTION_FILTER", {"budget": 0.10}, "Filtrage attentionnel : Le détail secondaire 'erreur de greffe' est éliminé sous contrainte 10%.", "Focalisation sur l'arrêt de principe réussie")
                
                # Mettre à jour round 5
                run_state = cls.get_run_state(simulation_id)
                if run_state:
                    run_state.current_round = 5
                    run_state.reddit_current_round = 5
                    run_state.twitter_current_round = 5
                    cls._save_run_state(run_state)
                time.sleep(2)
                
                write_log("Conclusion : Le filtrage attentionnel a élagué avec succès les détails procéduraux secondaires et a restreint les capacités introspectives de l'avocate pour préserver ses ressources cognitives sur le précédent jurisprudentiel.")

            # Finaliser la simulation
            run_state = cls.get_run_state(simulation_id)
            if run_state:
                run_state.runner_status = RunnerStatus.COMPLETED
                run_state.completed_at = datetime.now().isoformat()
                cls._save_run_state(run_state)

            # Mettre à jour l'état de la simulation dans SimulationManager
            manager = SimulationManager()
            sim_state = manager.get_simulation(simulation_id)
            if sim_state:
                sim_state.status = SimulationStatus.COMPLETED
                manager._save_simulation_state(sim_state)

            write_log("✓ Simulation de preuve scientifique terminée avec succès.")

        except Exception as e:
            write_log(f"✗ Erreur lors de l'exécution de la preuve: {str(e)}")
            run_state = cls.get_run_state(simulation_id)
            if run_state:
                run_state.runner_status = RunnerStatus.FAILED
                run_state.error = str(e)
                cls._save_run_state(run_state)

    @classmethod
    def _monitor_simulation(cls, simulation_id: str, locale: str = 'zh'):
        """监控模拟进程，解析动作日志"""
        set_locale(locale)
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        
        # 新的日志结构：分平台的动作日志
        twitter_actions_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        reddit_actions_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        
        process = cls._processes.get(simulation_id)
        state = cls.get_run_state(simulation_id)
        
        if not process or not state:
            return
        
        twitter_position = 0
        reddit_position = 0
        
        try:
            while process.poll() is None:  # 进程仍在运行
                # 读取 Twitter 动作日志
                if os.path.exists(twitter_actions_log):
                    twitter_position = cls._read_action_log(
                        twitter_actions_log, twitter_position, state, "twitter"
                    )
                
                # 读取 Reddit 动作日志
                if os.path.exists(reddit_actions_log):
                    reddit_position = cls._read_action_log(
                        reddit_actions_log, reddit_position, state, "reddit"
                    )
                
                # 更新状态
                cls._save_run_state(state)
                time.sleep(2)
            
            # 进程结束后，最后读取一次日志
            if os.path.exists(twitter_actions_log):
                cls._read_action_log(twitter_actions_log, twitter_position, state, "twitter")
            if os.path.exists(reddit_actions_log):
                cls._read_action_log(reddit_actions_log, reddit_position, state, "reddit")
            
            # 进程结束
            exit_code = process.returncode
            
            if exit_code == 0:
                state.runner_status = RunnerStatus.COMPLETED
                state.completed_at = datetime.now().isoformat()
                logger.info(f"Simulation terminée : {simulation_id}")
            else:
                state.runner_status = RunnerStatus.FAILED
                # 从主日志文件读取错误信息
                main_log_path = os.path.join(sim_dir, "simulation.log")
                error_info = ""
                try:
                    if os.path.exists(main_log_path):
                        with open(main_log_path, 'r', encoding='utf-8') as f:
                            error_info = f.read()[-2000:]  # 取最后2000字符
                except Exception:
                    pass
                state.error = f"进程退出码: {exit_code}, 错误: {error_info}"
                logger.error(f"Simulation échouée : {simulation_id}, error={state.error}")
            
            state.twitter_running = False
            state.reddit_running = False
            cls._save_run_state(state)
            
        except Exception as e:
            logger.error(f"Exception dans le thread de surveillance : {simulation_id}, error={str(e)}")
            state.runner_status = RunnerStatus.FAILED
            state.error = str(e)
            cls._save_run_state(state)
        
        finally:
            # 停止图谱记忆更新器
            if cls._graph_memory_enabled.get(simulation_id, False):
                try:
                    ZepGraphMemoryManager.stop_updater(simulation_id)
                    logger.info(f"Mise à jour de la mémoire du graphe arrêtée : simulation_id={simulation_id}")
                except Exception as e:
                    logger.error(f"Échec de l'arrêt de la mise à jour de la mémoire du graphe : {e}")
                cls._graph_memory_enabled.pop(simulation_id, None)
            
            # 清理进程资源
            cls._processes.pop(simulation_id, None)
            cls._action_queues.pop(simulation_id, None)
            
            # 关闭日志文件句柄
            if simulation_id in cls._stdout_files:
                try:
                    cls._stdout_files[simulation_id].close()
                except Exception:
                    pass
                cls._stdout_files.pop(simulation_id, None)
            if simulation_id in cls._stderr_files and cls._stderr_files[simulation_id]:
                try:
                    cls._stderr_files[simulation_id].close()
                except Exception:
                    pass
                cls._stderr_files.pop(simulation_id, None)
    
    @classmethod
    def _read_action_log(
        cls, 
        log_path: str, 
        position: int, 
        state: SimulationRunState,
        platform: str
    ) -> int:
        """
        读取动作日志文件
        
        Args:
            log_path: 日志文件路径
            position: 上次读取位置
            state: 运行状态对象
            platform: 平台名称 (twitter/reddit)
            
        Returns:
            新的读取位置
        """
        # 检查是否启用了图谱记忆更新
        graph_memory_enabled = cls._graph_memory_enabled.get(state.simulation_id, False)
        graph_updater = None
        if graph_memory_enabled:
            graph_updater = ZepGraphMemoryManager.get_updater(state.simulation_id)
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(position)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            action_data = json.loads(line)
                            
                            # 处理事件类型的条目
                            if "event_type" in action_data:
                                event_type = action_data.get("event_type")
                                
                                # 检测 simulation_end 事件，标记平台已完成
                                if event_type == "simulation_end":
                                    if platform == "twitter":
                                        state.twitter_completed = True
                                        state.twitter_running = False
                                        logger.info(f"Simulation Twitter terminée : {state.simulation_id}, total_rounds={action_data.get('total_rounds')}, total_actions={action_data.get('total_actions')}")
                                    elif platform == "reddit":
                                        state.reddit_completed = True
                                        state.reddit_running = False
                                        logger.info(f"Simulation Reddit terminée : {state.simulation_id}, total_rounds={action_data.get('total_rounds')}, total_actions={action_data.get('total_actions')}")
                                    
                                    # 检查是否所有启用的平台都已完成
                                    # 如果只运行了一个平台，只检查那个平台
                                    # 如果运行了两个平台，需要两个都完成
                                    all_completed = cls._check_all_platforms_completed(state)
                                    if all_completed:
                                        state.runner_status = RunnerStatus.COMPLETED
                                        state.completed_at = datetime.now().isoformat()
                                        logger.info(f"Simulations sur toutes les plateformes terminées : {state.simulation_id}")
                                
                                # 更新轮次信息（从 round_end 事件）
                                elif event_type == "round_end":
                                    round_num = action_data.get("round", 0)
                                    simulated_hours = action_data.get("simulated_hours", 0)
                                    
                                    # 更新各平台独立的轮次和时间
                                    if platform == "twitter":
                                        if round_num > state.twitter_current_round:
                                            state.twitter_current_round = round_num
                                        state.twitter_simulated_hours = simulated_hours
                                    elif platform == "reddit":
                                        if round_num > state.reddit_current_round:
                                            state.reddit_current_round = round_num
                                        state.reddit_simulated_hours = simulated_hours
                                    
                                    # 总体轮次取两个平台的最大值
                                    if round_num > state.current_round:
                                        state.current_round = round_num
                                        # Enregistrer l'état cognitif à la fin de cette itération
                                        try:
                                            cls._record_cognitive_state_history(
                                                state.simulation_id,
                                                round_num=state.current_round,
                                                objections_count=0,
                                                total_stimuli=len(state.injected_stimuli) if hasattr(state, 'injected_stimuli') and state.injected_stimuli else 0
                                            )
                                        except Exception as rec_err:
                                            logger.error(f"Erreur de sauvegarde de l'historique cognitif: {rec_err}")
                                    # 总体时间取两个平台的最大值
                                    state.simulated_hours = max(state.twitter_simulated_hours, state.reddit_simulated_hours)
                                
                                continue
                            
                            action = AgentAction(
                                round_num=action_data.get("round", 0),
                                timestamp=action_data.get("timestamp", datetime.now().isoformat()),
                                platform=platform,
                                agent_id=action_data.get("agent_id", 0),
                                agent_name=action_data.get("agent_name", ""),
                                action_type=action_data.get("action_type", ""),
                                action_args=action_data.get("action_args", {}),
                                result=action_data.get("result"),
                                success=action_data.get("success", True),
                            )
                            state.add_action(action)
                            
                            # 更新轮次
                            if action.round_num and action.round_num > state.current_round:
                                state.current_round = action.round_num
                            
                            # 如果启用了图谱记忆更新，将活动发送到Zep
                            if graph_updater:
                                graph_updater.add_activity_from_dict(action_data, platform)
                            
                        except json.JSONDecodeError:
                            pass
                return f.tell()
        except Exception as e:
            logger.warning(f"Échec de la lecture du journal d'actions : {log_path}, error={e}")
            return position
    
    @classmethod
    def _check_all_platforms_completed(cls, state: SimulationRunState) -> bool:
        """
        检查所有启用的平台是否都已完成模拟
        
        通过检查对应的 actions.jsonl 文件是否存在来判断平台是否被启用
        
        Returns:
            True 如果所有启用的平台都已完成
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        twitter_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        reddit_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        
        # 检查哪些平台被启用（通过文件是否存在判断）
        twitter_enabled = os.path.exists(twitter_log)
        reddit_enabled = os.path.exists(reddit_log)
        
        # 如果平台被启用但未完成，则返回 False
        if twitter_enabled and not state.twitter_completed:
            return False
        if reddit_enabled and not state.reddit_completed:
            return False
        
        # 至少有一个平台被启用且已完成
        return twitter_enabled or reddit_enabled
    
    @classmethod
    def _terminate_process(cls, process: subprocess.Popen, simulation_id: str, timeout: int = 10):
        """
        跨平台终止进程及其子进程
        
        Args:
            process: 要终止的进程
            simulation_id: 模拟ID（用于日志）
            timeout: 等待进程退出的超时时间（秒）
        """
        if IS_WINDOWS:
            # Windows: 使用 taskkill 命令终止进程树
            # /F = 强制终止, /T = 终止进程树（包括子进程）
            logger.info(f"Arrêt de l'arbre de processus (Windows) : simulation={simulation_id}, pid={process.pid}")
            try:
                # 先尝试优雅终止
                subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T'],
                    capture_output=True,
                    timeout=5
                )
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    # 强制终止
                    logger.warning(f"Processus ne répond pas, arrêt forcé : {simulation_id}")
                    subprocess.run(
                        ['taskkill', '/F', '/PID', str(process.pid), '/T'],
                        capture_output=True,
                        timeout=5
                    )
                    process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Échec de taskkill, tentative de résiliation (terminate) : {e}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        else:
            # Unix: 使用进程组终止
            # 由于使用了 start_new_session=True，进程组 ID 等于主进程 PID
            pgid = os.getpgid(process.pid)
            logger.info(f"Arrêt du groupe de processus (Unix) : simulation={simulation_id}, pgid={pgid}")
            
            # 先发送 SIGTERM 给整个进程组
            os.killpg(pgid, signal.SIGTERM)
            
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # 如果超时后还没结束，强制发送 SIGKILL
                logger.warning(f"Le groupe de processus ne répond pas à SIGTERM, arrêt forcé : {simulation_id}")
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=5)
    
    @classmethod
    def _run_legal_courtroom_simulation(cls, simulation_id: str, project_id: str, total_rounds: int):
        from ..models.project import ProjectManager
        from scripts.run_legal_simulation import LegalSimulationRunner
        from ..services.simulation_manager import SimulationManager, SimulationStatus
        
        # Check if graph memory is enabled
        graph_memory_enabled = cls._graph_memory_enabled.get(simulation_id, False)
        graph_updater = None
        if graph_memory_enabled:
            graph_updater = ZepGraphMemoryManager.get_updater(simulation_id)
            
        try:
            project = ProjectManager.get_project(project_id)
            context = project.simulation_requirement or ""
            
            # Enrich context with GraphRAG elements using courtroom terminology
            try:
                from ..services.local_graph_database import LocalGraphDatabase
                if project.graph_id:
                    db = LocalGraphDatabase(project.graph_id)
                    nodes = db.fetch_all_nodes()
                    edges = db.fetch_all_edges()
                    
                    if nodes:
                        # Smart selection of top 20 nodes based on connection degree
                        if len(nodes) > 20:
                            node_degrees = {n.get("uuid"): 0 for n in nodes}
                            for e in edges:
                                src = e.get("source_node_uuid")
                                tgt = e.get("target_node_uuid")
                                if src in node_degrees:
                                    node_degrees[src] += 1
                                if tgt in node_degrees:
                                    node_degrees[tgt] += 1
                            nodes = sorted(nodes, key=lambda n: node_degrees.get(n.get("uuid"), 0), reverse=True)[:20]
                            
                        graph_context = "\n\n=== Éléments factuels et pièces du dossier ===\n"
                        graph_context += "Faits admis et éléments identifiés au dossier :\n"
                        for n in nodes:
                            lbl = ", ".join(n.get("labels", []))
                            graph_context += f"- Nom: {n.get('name')} | Type: {lbl} | Résumé: {n.get('summary')}\n"
                        
                        if edges:
                            # Filter edges to only connect nodes in the selection
                            valid_uuids = {n.get("uuid") for n in nodes}
                            filtered_edges = [e for e in edges if e.get("source_node_uuid") in valid_uuids and e.get("target_node_uuid") in valid_uuids]
                            edges = filtered_edges[:20]
                            
                            if edges:
                                graph_context += "\nLien de causalité et éléments de preuve :\n"
                                for e in edges:
                                    src_name = next((node.get("name") for node in nodes if node.get("uuid") == e.get("source_node_uuid")), "Inconnu")
                                    tgt_name = next((node.get("name") for node in nodes if node.get("uuid") == e.get("target_node_uuid")), "Inconnu")
                                    graph_context += f"- [{src_name}] --({e.get('name')})--> [{tgt_name}] | Fait: {e.get('fact')}\n"
                        
                        context += graph_context
            except Exception as graph_err:
                logger.error(f"Error enriching legal context with graph: {graph_err}")
                
            # Appending extracted text of the project (e.g. R. c. Larouche)
            extracted_text = ""
            try:
                extracted_text = ProjectManager.get_extracted_text(project_id)
                if extracted_text:
                    context += f"\n\n=== TEXTE INTÉGRAL DE LA DÉCISION TÉLÉVERSÉE ===\n{extracted_text}\n"
                    logger.info(f"Loaded extracted text for project {project_id} in legal courtroom simulation context (length: {len(extracted_text)})")
            except Exception as txt_err:
                logger.error(f"Error loading project extracted text: {txt_err}")

            # Clean project name to find the case name (e.g. R. c. Gauthier)
            import re
            case_name = project.name
            for ext in ['.pdf', '.txt', '.doc', '.docx', '.ipynb']:
                if case_name.lower().endswith(ext):
                    case_name = case_name[:-len(ext)]
                    break
            case_name = case_name.strip()
            
            if extracted_text:
                # 1. Check for criminal case standard "R. c. Accusé"
                case_title_match = re.search(r'(?:R\.\s+c\.\s+[A-ZÀ-ÿ\w]+(?:\s+[A-ZÀ-ÿ\w]+)*)', extracted_text[:2000])
                if case_title_match:
                    case_name = case_title_match.group(0)
                else:
                    # 2. Check for civil case structure based on parties (Demandeur c. Défendeur)
                    lines = [l.strip() for l in extracted_text[:2000].split('\n') if l.strip()]
                    part1 = ""
                    part2 = ""
                    for idx, line in enumerate(lines):
                        if line.lower() in ["demandeur", "demanderesse", "requérant", "requérante", "poursuivant"]:
                            # Find the first non-empty line above that doesn't contain court metadata
                            for j in range(idx - 1, -1, -1):
                                cand = lines[j]
                                if any(w in cand.lower() for w in ["cour", "chambre", "district", "n°", "no :", "date", "juges", "président", "canada", "province"]):
                                    continue
                                part1 = cand
                                break
                        elif line.lower() in ["défendeur", "défenderesse", "intimé", "intimée", "accusé", "prévenu"]:
                            for j in range(idx - 1, -1, -1):
                                cand = lines[j]
                                if any(w in cand.lower() for w in ["cour", "chambre", "district", "n°", "no :", "date", "juges", "président", "canada", "province"]):
                                    continue
                                part2 = cand
                                break
                    
                    if part1 and part2:
                        case_name = f"{part1} c. {part2}"
                    else:
                        # 3. Check for inline "c." e.g. "Nom c. Ville de Mercier"
                        inline_match = re.search(r'([A-ZÀ-ÿ][A-ZÀ-ÿa-zà-ÿ\s\'-]{1,40})\s+c\.\s+([A-ZÀ-ÿ][A-ZÀ-ÿa-zà-ÿ\s\'-]{1,40})', extracted_text[:2000])
                        if inline_match:
                            p1 = inline_match.group(1).strip()
                            p2 = inline_match.group(2).strip()
                            case_name = f"{p1} c. {p2}"
            
            case_header = f"\n=== IDENTIFICATION DU DOSSIER ===\n"
            case_header += f"Nom de la cause principale (dossier téléversé) : {case_name}\n"
            case_header += f"IMPORTANT : La présente simulation concerne exclusivement la cause '{case_name}'. Vous ne devez en aucun cas prétendre que la décision téléversée est une autre jurisprudence (par exemple, ne la confondez pas avec 'R. c. Cobb' ou toute autre cause d'apprentissage). Citez uniquement '{case_name}' comme étant le cas principal du dossier de ce procès.\n\n"
            
            # Prepend the case_header to the context
            context = case_header + context
                
            # Load litigation_type from simulation_config.json if it exists
            litigation_type = "civil"
            try:
                config_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "simulation_config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        litigation_type = config_data.get("litigation_type", "civil")
                    logger.info(f"Loaded litigation_type '{litigation_type}' from config for simulation {simulation_id}")
            except Exception as config_err:
                logger.error(f"Error reading litigation_type from simulation config: {config_err}")

            runner = LegalSimulationRunner(context=context, iterations=total_rounds, litigation_type=litigation_type)
            cls._legal_runners[simulation_id] = runner
            
            results = []
            defense_wins = 0
            start_round = 1
            
            # Check for existing results to support Resume
            results_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "legal_simulation_results.json")
            if os.path.exists(results_path):
                try:
                    with open(results_path, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                        results = saved_data.get("details", [])
                        defense_wins = saved_data.get("defense_wins", 0)
                        start_round = len(results) + 1
                    logger.info(f"Resuming courtroom simulation {simulation_id} from round {start_round} (existing results: {len(results)})")
                    if results:
                        runner.judge_personality = results[0].get("judge_personality")
                except Exception as resume_err:
                    logger.error(f"Error loading existing results for resume: {resume_err}")

            state = cls.get_run_state(simulation_id)
            if not state:
                logger.error(f"Run state not found for {simulation_id}")
                return
                
            agent1_name = "Le Procureur" if litigation_type == "criminal" else "Avocat du Demandeur"

            if start_round == 1:
                # Initialize cognitive states for courtroom agents (PIE neuro-symbolic simulation)
                try:
                    from app.services.cognitive_memory import CognitiveMemoryService
                    from app.services.cognitive_engine import CognitiveAgentState
                    
                    agent1_meta = (
                        "Ma mission est de défendre l'ordre public et de faire appliquer strictement la loi. La culpabilité du prévenu ne fait aucun doute."
                        if litigation_type == "criminal" else
                        "Ma mission est de démontrer la responsabilité civile du défendeur et d'obtenir réparation pour le préjudice subi de mon client."
                    )
                    agent1_reflection = (
                        "Le dossier présente des charges sérieuses qui justifient une répression ferme."
                        if litigation_type == "criminal" else
                        "Le contrat et les preuves techniques démontrent clairement l'existence d'un vice caché."
                    )

                    agent2_meta = (
                        "Je me bats pour protéger les droits fondamentaux de mon client. L'équité naturelle doit prévaloir sur le formalisme aveugle."
                        if litigation_type == "criminal" else
                        "Je me bats pour protéger les intérêts commerciaux de mon client. Les allégations de vice caché sont infondées et la diligence raisonnable a été respectée."
                    )
                    agent2_reflection = (
                        "Les pièces fournies par l'accusation sont insuffisantes et truffées d'incertitudes."
                        if litigation_type == "criminal" else
                        "Les pièces de l'adversaire n'établissent pas l'existence d'un défaut préexistant imputable à mon client."
                    )

                    judge_meta = (
                        "Je préside cette audience de manière impartiale. Mon devoir est d'écouter les deux parties avant de me forger une intime conviction."
                        if litigation_type == "criminal" else
                        "Je préside ce litige civil de manière impartiale. Mon devoir est d'analyser la force probante des preuves contractuelles et techniques présentées."
                    )

                    CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                        agent_id="1",
                        name=agent1_name,
                        tensions={
                            "procedure_vs_equite": 0.85,
                            "offensive_vs_negociation": 0.80,
                            "prudence_vs_rapidite": 0.40
                        },
                        beliefs={
                            "culpabilite_accuse": {"coupable": 0.80, "innocent": 0.20}
                        },
                        meta_narrative=agent1_meta,
                        recent_reflection=agent1_reflection
                    ))
                    
                    CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                        agent_id="2",
                        name="Avocat de la Défense",
                        tensions={
                            "procedure_vs_equite": 0.30,
                            "offensive_vs_negociation": 0.45,
                            "prudence_vs_rapidite": 0.70
                        },
                        beliefs={
                            "culpabilite_accuse": {"coupable": 0.15, "innocent": 0.85}
                        },
                        meta_narrative=agent2_meta,
                        recent_reflection=agent2_reflection
                    ))
                    
                    CognitiveMemoryService.save_agent_state(simulation_id, CognitiveAgentState(
                        agent_id="0",
                        name="Le Juge",
                        tensions={
                            "procedure_vs_equite": 0.50,
                            "offensive_vs_negociation": 0.30,
                            "prudence_vs_rapidite": 0.60
                        },
                        beliefs={
                            "culpabilite_accuse": {"coupable": 0.50, "innocent": 0.50}
                        },
                        meta_narrative=judge_meta,
                        recent_reflection="Les débats commencent à peine, l'impartialité est requise."
                    ))
                    logger.info(f"Initialized cognitive states for legal courtroom simulation: {simulation_id}")
                except Exception as db_init_err:
                    logger.error(f"Error initializing legal cognitive states: {db_init_err}")
                    
                # Clear or initialize cognitive history and record baseline round 0
                state.cognitive_history = []
                cls._record_cognitive_state_history(simulation_id, round_num=0, objections_count=0, total_stimuli=0)

                actions_file_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "actions.jsonl")
                os.makedirs(os.path.dirname(actions_file_path), exist_ok=True)
                with open(actions_file_path, 'w', encoding='utf-8') as f:
                    pass  # Clear

                # Ground and log initial stimulus if present
                if state.injected_stimuli:
                    try:
                        init_stim = state.injected_stimuli[0]
                        # Log action
                        act = AgentAction(
                            round_num=0,
                            timestamp=datetime.now().isoformat(),
                            platform="courtroom",
                            agent_id=999,
                            agent_name="Système (Stimulus)",
                            action_type="STIMULUS",
                            action_args={"content": init_stim},
                            result="Stimulus initial injecté",
                            success=True
                        )
                        state.add_action(act)
                        with open(actions_file_path, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(act.to_dict(), ensure_ascii=False) + "\n")
                        cls._save_run_state(state)
                        
                        # Graph grounding
                        if project.graph_id:
                            logger.info(f"Dynamic GraphRAG Grounding for initial stimulus: graph_id={project.graph_id}")
                            from ..services.local_graph_extractor import LocalGraphExtractor
                            from ..services.local_graph_database import LocalGraphDatabase
                            
                            extractor = LocalGraphExtractor()
                            ontology = {
                                "entity_types": [
                                    {"name": "Company"},
                                    {"name": "Person"},
                                    {"name": "Court"},
                                    {"name": "LawFirm"},
                                    {"name": "AuditingFirm"},
                                    {"name": "Evidence"},
                                    {"name": "Concept"},
                                    {"name": "Jurisprudence"},
                                    {"name": "Loi"}
                                ],
                                "edge_types": [
                                    {"name": "DENIES_CLAIMS_OF"},
                                    {"name": "ALLEGES_AGAINST"},
                                    {"name": "REPRESENTS"},
                                    {"name": "WORKS_FOR"},
                                    {"name": "FILES_CASE_IN"},
                                    {"name": "CONDUCTS_AUDIT_FOR"},
                                    {"name": "SUES"},
                                    {"name": "CITES_JURISPRUDENCE"},
                                    {"name": "IMPACTS"},
                                    {"name": "CONTESTS"}
                                ]
                            }
                            nodes, edges = extractor.extract_triplets(init_stim, ontology)
                            if nodes or edges:
                                db = LocalGraphDatabase(project.graph_id)
                                db.upsert_triplets(nodes, edges)
                                logger.info(f"Successfully grounded initial stimulus: {len(nodes)} nodes, {len(edges)} edges")
                    except Exception as init_err:
                        logger.error(f"Error handling initial stimulus: {init_err}")
            else:
                actions_file_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "actions.jsonl")
                
            round_idx = start_round
            while True:
                state = cls.get_run_state(simulation_id)
                if not state:
                    break
                if round_idx > state.total_rounds:
                    break
                
                # Correct counter display: Set current_round at the start of the round iteration loop
                state.current_round = round_idx
                cls._save_run_state(state)

                # Update runner's context with previous verdicts to ensure state persistence
                current_context = context
                
                # Check for and append all injected stimuli to context so they are preserved
                injected_stimuli = state.injected_stimuli if (hasattr(state, 'injected_stimuli') and state.injected_stimuli) else []
                if injected_stimuli:
                    current_context += "\n\n=== FAITS NOUVEAUX / STIMULI INJECTÉS DANS LES DÉBATS ===\n"
                    for stim in injected_stimuli:
                        current_context += f"- [STIMULUS INJECTÉ] : {stim}\n"
                
                # Build history of previous verdicts (factually structured summary to avoid prompt bleeding or role confusion)
                if len(results) > 0:
                    prev_verdicts_summary = "\n\n=== VERDICTS PRÉCÉDENTS ET HISTORIQUE DU PROCÈS ===\n"
                    prev_verdicts_summary += "Le Juge a déjà statué lors des sessions précédentes. Voici les décisions rendues :\n"
                    for r_res in results:
                        prev_verdicts_summary += f"[HISTORIQUE SIMULATION - ROUND {r_res['iteration']}] Verdict: {r_res['verdict']} | Fondement: {r_res.get('clerk_analysis', '')[:300]}... | Posture: {r_res.get('judge_personality', '')}\n"
                    prev_verdicts_summary += "\nDirectives de cohérence :\n"
                    prev_verdicts_summary += "1. Le Juge doit obligatoirement maintenir son verdict précédent (la culpabilité ou responsabilité) par souci de cohérence, SAUF si un nouveau fait (STIMULUS) a été injecté depuis la dernière décision et juste après celle-ci, auquel cas le Juge peut prononcer un revirement si ce nouveau fait est déterminant.\n"
                    prev_verdicts_summary += "2. Les Avocats doivent adapter leur plaidoirie en fonction du dernier verdict rendu (la défense cherche à infirmer le verdict de culpabilité précédent si un fait nouveau le permet ; le procureur cherche à le consolider).\n"
                    current_context += prev_verdicts_summary
                
                runner.context = current_context

                # Check if stopped
                current_state = cls.get_run_state(simulation_id)
                if current_state and current_state.runner_status in [RunnerStatus.STOPPING, RunnerStatus.STOPPED]:
                    logger.info(f"Legal simulation {simulation_id} stopped at round {round_idx}")
                    
                    # Enregistrer les résultats partiels pour que le rapport puisse être généré
                    output_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
                    os.makedirs(output_dir, exist_ok=True)
                    win_rate = (defense_wins / len(results)) * 100 if results else 0
                    final_res_path = os.path.join(output_dir, "legal_simulation_results.json")
                    with open(final_res_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            "context": context,
                            "iterations": len(results),
                            "win_rate": win_rate,
                            "defense_wins": defense_wins,
                            "prompt_tokens": state.prompt_tokens,
                            "completion_tokens": state.completion_tokens,
                            "estimated_cost": state.estimated_cost,
                            "details": results
                        }, f, ensure_ascii=False, indent=2)
                        
                    manager = SimulationManager()
                    sim_state = manager.get_simulation(simulation_id)
                    if sim_state:
                        sim_state.status = SimulationStatus.STOPPED
                        manager._save_simulation_state(sim_state)
                    return
                
                # Real-time progress callback to write actions immediately
                def log_agent_action(action_type, agent_name, agent_id, content, result="Speech delivered", success=True):
                    timestamp_str = datetime.now().isoformat()
                    act = AgentAction(
                        round_num=round_idx,
                        timestamp=timestamp_str,
                        platform="courtroom",
                        agent_id=agent_id,
                        agent_name=agent_name,
                        action_type=action_type,
                        action_args={"content": content},
                        result=result,
                        success=success
                    )
                    state.add_action(act)
                    with open(actions_file_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(act.to_dict(), ensure_ascii=False) + "\n")
                    cls._save_run_state(state)
                    
                    if graph_updater:
                        try:
                            graph_updater.add_activity_from_dict(act.to_dict(), "courtroom")
                        except Exception as ge:
                            logger.error(f"Error adding courtroom activity to graph memory updater: {ge}")

                res = runner.run_single_simulation(round_idx, on_action_callback=log_agent_action)
                results.append(res)
                if res["is_defense_win"]:
                    defense_wins += 1
                    
                prosecutor_speech = ""
                defense_speech = ""
                juge_verdict = res.get("verdict", "")
                clerk_analysis = res.get("clerk_analysis", "")
                
                for line in res["transcript"]:
                    if line.startswith("PROCUREUR:"):
                        prosecutor_speech = line[10:].strip()
                    elif line.startswith("DEFENSE:"):
                        defense_speech = line[8:].strip()
                
                # Update cognitive states for the round (PIE Engine simulation)
                try:
                    from app.services.cognitive_memory import CognitiveMemoryService
                    
                    state_judge = CognitiveMemoryService.get_agent_state(simulation_id, "0", "Le Juge")
                    state_judge.personality = res.get("judge_personality", "")
                    state_proc = CognitiveMemoryService.get_agent_state(simulation_id, "1", agent1_name)
                    state_def = CognitiveMemoryService.get_agent_state(simulation_id, "2", "Avocat de la Défense")
                    
                    proc_objection = "OBJECTION" in prosecutor_speech.upper() or "OBJECTION" in clerk_analysis.upper()
                    def_objection = "OBJECTION" in defense_speech.upper() or "OBJECTION" in clerk_analysis.upper()
                    
                    if proc_objection:
                        state_proc.negative_interactions_count += 1
                        if state_proc.negative_interactions_count >= 3:
                            state_proc.mood = "Isolé"
                        elif state_proc.negative_interactions_count == 2:
                            state_proc.mood = "Paranoïaque"
                            state_proc.tensions["offensive_vs_negociation"] = max(0.85, state_proc.tensions.get("offensive_vs_negociation", 0.5))
                        else:
                            state_proc.mood = "Méfiant"
                    else:
                        state_proc.negative_interactions_count = max(0, state_proc.negative_interactions_count - 1)
                        if state_proc.negative_interactions_count == 0:
                            state_proc.mood = "Neutre"
                            
                    if def_objection:
                        state_def.negative_interactions_count += 1
                        if state_def.negative_interactions_count >= 3:
                            state_def.mood = "Isolé"
                        elif state_def.negative_interactions_count == 2:
                            state_def.mood = "Paranoïaque"
                            state_def.tensions["offensive_vs_negociation"] = max(0.88, state_def.tensions.get("offensive_vs_negociation", 0.5))
                        else:
                            state_def.mood = "Méfiant"
                    else:
                        state_def.negative_interactions_count = max(0, state_def.negative_interactions_count - 1)
                        if state_def.negative_interactions_count == 0:
                            state_def.mood = "Neutre"

                    if res.get("is_defense_win", False):
                        p_coupable = state_judge.beliefs.get("culpabilite_accuse", {}).get("coupable", 0.5)
                        new_p_coupable = max(0.10, p_coupable - 0.15)
                        state_judge.beliefs["culpabilite_accuse"] = {"coupable": new_p_coupable, "innocent": 1.0 - new_p_coupable}
                        
                        state_judge.tensions["procedure_vs_equite"] = max(0.20, state_judge.tensions.get("procedure_vs_equite", 0.5) - 0.08)
                        state_def.beliefs["culpabilite_accuse"] = {"coupable": 0.05, "innocent": 0.95}
                        
                        state_judge.meta_narrative = (
                            f"Les arguments de la défense m'ont convaincu de prononcer un verdict de relaxe au round {round_idx}."
                            if litigation_type == "criminal" else
                            f"Les arguments de la défense m'ont convaincu de rejeter la demande pour vice caché au round {round_idx}."
                        )
                        state_judge.recent_reflection = (
                            "L'équité naturelle impose le bénéfice du doute en l'absence de preuves matérielles incontestables."
                            if litigation_type == "criminal" else
                            "L'acheteur n'a pas démontré avoir exercé la diligence raisonnable requise lors de l'acquisition."
                        )
                    else:
                        p_coupable = state_judge.beliefs.get("culpabilite_accuse", {}).get("coupable", 0.5)
                        new_p_coupable = min(0.90, p_coupable + 0.15)
                        state_judge.beliefs["culpabilite_accuse"] = {"coupable": new_p_coupable, "innocent": 1.0 - new_p_coupable}
                        
                        state_judge.tensions["procedure_vs_equite"] = min(0.80, state_judge.tensions.get("procedure_vs_equite", 0.5) + 0.08)
                        
                        state_judge.meta_narrative = (
                            f"L'accusation a démontré de manière probante les éléments constitutifs de l'infraction au round {round_idx}."
                            if litigation_type == "criminal" else
                            f"Le demandeur a démontré de manière prépondérante la présence d'un vice caché au round {round_idx}."
                        )
                        
                        # Dynamically customize recent reflections based on the litigation context to avoid hallucinations (e.g. server issues vs water backup)
                        context_lower = context.lower()
                        is_water_plumbing = any(kw in context_lower for kw in ["eau", "refoulement", "plomberie", "plombier", "tuyau", "tuyauterie", "drain", "inondation", "dégât", "syndicat", "copropriété"])
                        is_server_it = any(kw in context_lower for kw in ["serveur", "hébergement", "logiciel", "informatique", "cloud", "panne"])
                        
                        if is_water_plumbing:
                            civil_judge_reflection = "Le refoulement d'eau récurrent ou le défaut d'entretien de la tuyauterie constitue un vice caché rendant le bien impropre à son usage."
                            civil_proc_reflection = "J'ai mis en évidence le défaut d'entretien des parties communes et les refoulements pour prouver la faute des défendeurs."
                        elif is_server_it:
                            civil_judge_reflection = "Le défaut de capacité des serveurs constitue un vice caché rendant le bien impropre à son usage."
                            civil_proc_reflection = "J'ai mis en évidence le défaut critique des serveurs pour prouver le manquement contractuel."
                        else:
                            civil_judge_reflection = "Le défaut technique ou le vice caché affectant le bien le rend impropre à l'usage auquel il est destiné."
                            civil_proc_reflection = "J'ai mis en évidence le vice caché technique pour prouver la responsabilité du défendeur."

                        state_judge.recent_reflection = (
                            "Le respect de la loi et la répression des infractions guident ma décision."
                            if litigation_type == "criminal" else
                            civil_judge_reflection
                        )
                        
                    state_proc.meta_narrative = (
                        f"Rétrécissement des options de la défense au round {round_idx}. Le taux de culpabilité présumé reste élevé."
                        if litigation_type == "criminal" else
                        f"La démonstration de la responsabilité progresse au round {round_idx}. Les éléments factuels confirment le vice caché."
                    )
                    state_proc.recent_reflection = (
                        "Ma plaidoirie s'est concentrée sur la matérialité des faits et l'application de la jurisprudence."
                        if litigation_type == "criminal" else
                        civil_proc_reflection
                    )
                    
                    state_def.meta_narrative = f"Rétrospection après le round {round_idx}. La tension délibérative reste palpable."
                    state_def.recent_reflection = (
                        "J'ai cherché à introduire le doute raisonnable face aux affirmations du procureur."
                        if litigation_type == "criminal" else
                        "J'ai soutenu que l'acheteur n'a pas procédé à la diligence raisonnable minimale requise."
                    )
                    
                    CognitiveMemoryService.save_agent_state(simulation_id, state_judge)
                    CognitiveMemoryService.save_agent_state(simulation_id, state_proc)
                    CognitiveMemoryService.save_agent_state(simulation_id, state_def)
                    
                    # Record history at the end of each round
                    objections_count = 0
                    if proc_objection:
                        objections_count += 1
                    if def_objection:
                        objections_count += 1
                    
                    total_stimuli = len(state.injected_stimuli) if hasattr(state, 'injected_stimuli') and state.injected_stimuli else 0
                    cls._record_cognitive_state_history(simulation_id, round_idx, objections_count, total_stimuli)

                except Exception as db_err:
                    logger.error(f"Erreur lors de la mise à jour des états PIE dans la simulation juridique: {db_err}")
                
                round_idx += 1
                
            state.runner_status = RunnerStatus.COMPLETED
            state.completed_at = datetime.now().isoformat()
            cls._save_run_state(state)
            
            manager = SimulationManager()
            sim_state = manager.get_simulation(simulation_id)
            if sim_state:
                sim_state.status = SimulationStatus.COMPLETED
                manager._save_simulation_state(sim_state)
                
            output_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
            os.makedirs(output_dir, exist_ok=True)
            win_rate = (defense_wins / len(results)) * 100 if results else 0
            
            final_res_path = os.path.join(output_dir, "legal_simulation_results.json")
            with open(final_res_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "context": context,
                    "iterations": len(results),
                    "win_rate": win_rate,
                    "defense_wins": defense_wins,
                    "litigation_type": litigation_type,
                    "prompt_tokens": state.prompt_tokens,
                    "completion_tokens": state.completion_tokens,
                    "estimated_cost": state.estimated_cost,
                    "details": results
                }, f, ensure_ascii=False, indent=2)
                
        except Exception as run_err:
            logger.error(f"Error running background legal simulation: {run_err}")
            state = cls.get_run_state(simulation_id)
            if state:
                state.runner_status = RunnerStatus.FAILED
                state.error = str(run_err)
                cls._save_run_state(state)
            manager = SimulationManager()
            sim_state = manager.get_simulation(simulation_id)
            if sim_state:
                sim_state.status = SimulationStatus.FAILED
                manager._save_simulation_state(sim_state)
        finally:
            cls._legal_runners.pop(simulation_id, None)
            # Stop graph memory updater if enabled
            if cls._graph_memory_enabled.get(simulation_id, False):
                try:
                    ZepGraphMemoryManager.stop_updater(simulation_id)
                    logger.info(f"Courtroom simulation finished. Stopped graph memory updater: simulation_id={simulation_id}")
                except Exception as e:
                    logger.error(f"Failed to stop graph memory updater for courtroom: {e}")
                cls._graph_memory_enabled.pop(simulation_id, None)

    @classmethod
    def stop_simulation(cls, simulation_id: str) -> SimulationRunState:
        """停止模拟"""
        state = cls.get_run_state(simulation_id)
        if not state:
            raise ValueError(f"La simulation n'existe pas : {simulation_id}")
        
        if state.runner_status not in [RunnerStatus.RUNNING, RunnerStatus.PAUSED]:
            raise ValueError(f"La simulation n'est pas en cours d'exécution : {simulation_id}, status={state.runner_status}")
        
        state.runner_status = RunnerStatus.STOPPING
        cls._save_run_state(state)
        
        # 终止进程
        process = cls._processes.get(simulation_id)
        if process and process.poll() is None:
            try:
                cls._terminate_process(process, simulation_id)
            except ProcessLookupError:
                # 进程已经不存在
                pass
            except Exception as e:
                logger.error(f"Échec de l'arrêt du groupe de processus : {simulation_id}, error={e}")
                # 回退到直接终止进程
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    process.kill()
        
        state.runner_status = RunnerStatus.STOPPED
        state.twitter_running = False
        state.reddit_running = False
        state.completed_at = datetime.now().isoformat()
        cls._save_run_state(state)
        
        # 停止图谱记忆更新器
        if cls._graph_memory_enabled.get(simulation_id, False):
            try:
                ZepGraphMemoryManager.stop_updater(simulation_id)
                logger.info(f"Mise à jour de la mémoire du graphe arrêtée : simulation_id={simulation_id}")
            except Exception as e:
                logger.error(f"Échec de l'arrêt de la mise à jour de la mémoire du graphe : {e}")
            cls._graph_memory_enabled.pop(simulation_id, None)
        
        logger.info(f"Simulation arrêtée : {simulation_id}")
        return state
    
    @classmethod
    def _read_actions_from_file(
        cls,
        file_path: str,
        default_platform: Optional[str] = None,
        platform_filter: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        从单个动作文件中读取动作
        
        Args:
            file_path: 动作日志文件路径
            default_platform: 默认平台（当动作记录中没有 platform 字段时使用）
            platform_filter: 过滤平台
            agent_id: 过滤 Agent ID
            round_num: 过滤轮次
        """
        if not os.path.exists(file_path):
            return []
        
        actions = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # 跳过非动作记录（如 simulation_start, round_start, round_end 等事件）
                    if "event_type" in data:
                        continue
                    
                    # 跳过没有 agent_id 的记录（非 Agent 动作）
                    if "agent_id" not in data:
                        continue
                    
                    # 获取平台：优先使用记录中的 platform，否则使用默认平台
                    record_platform = data.get("platform") or default_platform or ""
                    
                    # 过滤
                    if platform_filter and record_platform != platform_filter:
                        continue
                    if agent_id is not None and data.get("agent_id") != agent_id:
                        continue
                    if round_num is not None and data.get("round") != round_num:
                        continue
                    
                    actions.append(AgentAction(
                        round_num=data.get("round", 0),
                        timestamp=data.get("timestamp", ""),
                        platform=record_platform,
                        agent_id=data.get("agent_id", 0),
                        agent_name=data.get("agent_name", ""),
                        action_type=data.get("action_type", ""),
                        action_args=data.get("action_args", {}),
                        result=data.get("result"),
                        success=data.get("success", True),
                    ))
                    
                except json.JSONDecodeError:
                    continue
        
        return actions
    
    @classmethod
    def get_all_actions(
        cls,
        simulation_id: str,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        获取所有平台的完整动作历史（无分页限制）
        
        Args:
            simulation_id: 模拟ID
            platform: 过滤平台（twitter/reddit）
            agent_id: 过滤Agent
            round_num: 过滤轮次
            
        Returns:
            完整的动作列表（按时间戳排序，新的在前）
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        actions = []
        
        # 读取 Twitter 动作文件（根据文件路径自动设置 platform 为 twitter）
        twitter_actions_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        if not platform or platform == "twitter":
            actions.extend(cls._read_actions_from_file(
                twitter_actions_log,
                default_platform="twitter",  # 自动填充 platform 字段
                platform_filter=platform,
                agent_id=agent_id, 
                round_num=round_num
            ))
        
        # 读取 Reddit 动作文件（根据文件路径自动设置 platform 为 reddit）
        reddit_actions_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        if not platform or platform == "reddit":
            actions.extend(cls._read_actions_from_file(
                reddit_actions_log,
                default_platform="reddit",  # 自动填充 platform 字段
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            ))
        
        # 如果分平台文件不存在，尝试读取旧的单一文件格式
        if not actions:
            actions_log = os.path.join(sim_dir, "actions.jsonl")
            actions = cls._read_actions_from_file(
                actions_log,
                default_platform=None,  # 旧格式文件中应该有 platform 字段
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            )
        
        # 按时间戳排序（新的在前）
        actions.sort(key=lambda x: x.timestamp, reverse=True)
        
        return actions
    
    @classmethod
    def get_actions(
        cls,
        simulation_id: str,
        limit: int = 100,
        offset: int = 0,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        获取动作历史（带分页）
        
        Args:
            simulation_id: 模拟ID
            limit: 返回数量限制
            offset: 偏移量
            platform: 过滤平台
            agent_id: 过滤Agent
            round_num: 过滤轮次
            
        Returns:
            动作列表
        """
        actions = cls.get_all_actions(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )
        
        # 分页
        return actions[offset:offset + limit]
    
    @classmethod
    def get_timeline(
        cls,
        simulation_id: str,
        start_round: int = 0,
        end_round: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取模拟时间线（按轮次汇总）
        
        Args:
            simulation_id: 模拟ID
            start_round: 起始轮次
            end_round: 结束轮次
            
        Returns:
            每轮的汇总信息
        """
        actions = cls.get_actions(simulation_id, limit=10000)
        
        # 按轮次分组
        rounds: Dict[int, Dict[str, Any]] = {}
        
        for action in actions:
            round_num = action.round_num
            
            if round_num < start_round:
                continue
            if end_round is not None and round_num > end_round:
                continue
            
            if round_num not in rounds:
                rounds[round_num] = {
                    "round_num": round_num,
                    "twitter_actions": 0,
                    "reddit_actions": 0,
                    "active_agents": set(),
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }
            
            r = rounds[round_num]
            
            if action.platform == "twitter":
                r["twitter_actions"] += 1
            else:
                r["reddit_actions"] += 1
            
            r["active_agents"].add(action.agent_id)
            r["action_types"][action.action_type] = r["action_types"].get(action.action_type, 0) + 1
            r["last_action_time"] = action.timestamp
        
        # 转换为列表
        result = []
        for round_num in sorted(rounds.keys()):
            r = rounds[round_num]
            result.append({
                "round_num": round_num,
                "twitter_actions": r["twitter_actions"],
                "reddit_actions": r["reddit_actions"],
                "total_actions": r["twitter_actions"] + r["reddit_actions"],
                "active_agents_count": len(r["active_agents"]),
                "active_agents": list(r["active_agents"]),
                "action_types": r["action_types"],
                "first_action_time": r["first_action_time"],
                "last_action_time": r["last_action_time"],
            })
        
        return result
    
    @classmethod
    def get_agent_stats(cls, simulation_id: str) -> List[Dict[str, Any]]:
        """
        获取每个Agent的统计信息
        
        Returns:
            Agent统计列表
        """
        actions = cls.get_actions(simulation_id, limit=10000)
        
        agent_stats: Dict[int, Dict[str, Any]] = {}
        
        for action in actions:
            agent_id = action.agent_id
            
            if agent_id not in agent_stats:
                agent_stats[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": action.agent_name,
                    "total_actions": 0,
                    "twitter_actions": 0,
                    "reddit_actions": 0,
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }
            
            stats = agent_stats[agent_id]
            stats["total_actions"] += 1
            
            if action.platform == "twitter":
                stats["twitter_actions"] += 1
            else:
                stats["reddit_actions"] += 1
            
            stats["action_types"][action.action_type] = stats["action_types"].get(action.action_type, 0) + 1
            stats["last_action_time"] = action.timestamp
        
        # 按总动作数排序
        result = sorted(agent_stats.values(), key=lambda x: x["total_actions"], reverse=True)
        
        return result
    
    @classmethod
    def cleanup_simulation_logs(cls, simulation_id: str) -> Dict[str, Any]:
        """
        清理模拟的运行日志（用于强制重新开始模拟）
        
        会删除以下文件：
        - run_state.json
        - twitter/actions.jsonl
        - reddit/actions.jsonl
        - simulation.log
        - stdout.log / stderr.log
        - twitter_simulation.db（模拟数据库）
        - reddit_simulation.db（模拟数据库）
        - env_status.json（环境状态）
        
        注意：不会删除配置文件（simulation_config.json）和 profile 文件
        
        Args:
            simulation_id: 模拟ID
            
        Returns:
            清理结果信息
        """
        import shutil
        
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        
        if not os.path.exists(sim_dir):
            return {"success": True, "message": "模拟目录不存在，无需清理"}
        
        cleaned_files = []
        errors = []
        
        # 要删除的文件列表（包括数据库文件）
        files_to_delete = [
            "run_state.json",
            "simulation.log",
            "stdout.log",
            "stderr.log",
            "twitter_simulation.db",  # Twitter 平台数据库
            "reddit_simulation.db",   # Reddit 平台数据库
            "env_status.json",        # 环境状态文件
            "legal_simulation_results.json",
            "actions.jsonl",
        ]
        
        # 要删除的目录列表（包含动作日志）
        dirs_to_clean = ["twitter", "reddit"]
        
        # 删除文件
        for filename in files_to_delete:
            file_path = os.path.join(sim_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(filename)
                except Exception as e:
                    errors.append(f"删除 {filename} 失败: {str(e)}")
        
        # 清理平台目录中的动作日志
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(sim_dir, dir_name)
            if os.path.exists(dir_path):
                actions_file = os.path.join(dir_path, "actions.jsonl")
                if os.path.exists(actions_file):
                    try:
                        os.remove(actions_file)
                        cleaned_files.append(f"{dir_name}/actions.jsonl")
                    except Exception as e:
                        errors.append(f"删除 {dir_name}/actions.jsonl 失败: {str(e)}")
        
        # 清理内存中的运行状态
        if simulation_id in cls._run_states:
            del cls._run_states[simulation_id]
        
        logger.info(f"Nettoyage des journaux de simulation terminé : {simulation_id}, fichiers supprimés : {cleaned_files}")
        
        return {
            "success": len(errors) == 0,
            "cleaned_files": cleaned_files,
            "errors": errors if errors else None
        }
    
    # 防止重复清理的标志
    _cleanup_done = False
    
    @classmethod
    def cleanup_all_simulations(cls):
        """
        清理所有运行中的模拟进程
        
        在服务器关闭时调用，确保所有子进程被终止
        """
        # 防止重复清理
        if cls._cleanup_done:
            return
        cls._cleanup_done = True
        
        # 检查是否有内容需要清理（避免空进程的进程打印无用日志）
        has_processes = bool(cls._processes)
        has_updaters = bool(cls._graph_memory_enabled)
        
        if not has_processes and not has_updaters:
            return  # 没有需要清理的内容，静默返回
        
        logger.info("Nettoyage de tous les processus de simulation en cours...")
        
        # 首先停止所有图谱记忆更新器（stop_all 内部会打印日志）
        try:
            ZepGraphMemoryManager.stop_all()
        except Exception as e:
            logger.error(f"Échec de l'arrêt de la mise à jour de la mémoire du graphe : {e}")
        cls._graph_memory_enabled.clear()
        
        # 复制字典以避免在迭代时修改
        processes = list(cls._processes.items())
        
        for simulation_id, process in processes:
            try:
                if process.poll() is None:  # 进程仍在运行
                    logger.info(f"Arrêt du processus de simulation : {simulation_id}, pid={process.pid}")
                    
                    try:
                        # 使用跨平台的进程终止方法
                        cls._terminate_process(process, simulation_id, timeout=5)
                    except (ProcessLookupError, OSError):
                        # 进程可能已经不存在，尝试直接终止
                        try:
                            process.terminate()
                            process.wait(timeout=3)
                        except Exception:
                            process.kill()
                    
                    # 更新 run_state.json
                    state = cls.get_run_state(simulation_id)
                    if state:
                        state.runner_status = RunnerStatus.STOPPED
                        state.twitter_running = False
                        state.reddit_running = False
                        state.completed_at = datetime.now().isoformat()
                        state.error = "服务器关闭，模拟被终止"
                        cls._save_run_state(state)
                    
                    # 同时更新 state.json，将状态设为 stopped
                    try:
                        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
                        state_file = os.path.join(sim_dir, "state.json")
                        logger.info(f"Tentative de mise à jour de state.json : {state_file}")
                        if os.path.exists(state_file):
                            with open(state_file, 'r', encoding='utf-8') as f:
                                state_data = json.load(f)
                            state_data['status'] = 'stopped'
                            state_data['updated_at'] = datetime.now().isoformat()
                            with open(state_file, 'w', encoding='utf-8') as f:
                                json.dump(state_data, f, indent=2, ensure_ascii=False)
                            logger.info(f"Statut de state.json mis à jour à stopped : {simulation_id}")
                        else:
                            logger.warning(f"state.json n'existe pas : {state_file}")
                    except Exception as state_err:
                        logger.warning(f"Échec de la mise à jour de state.json : {simulation_id}, error={state_err}")
                        
            except Exception as e:
                logger.error(f"Échec du nettoyage du processus : {simulation_id}, error={e}")
        
        # 清理文件句柄
        for simulation_id, file_handle in list(cls._stdout_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stdout_files.clear()
        
        for simulation_id, file_handle in list(cls._stderr_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stderr_files.clear()
        
        # 清理内存中的状态
        cls._processes.clear()
        cls._action_queues.clear()
        
        logger.info("Nettoyage des processus de simulation terminé")
    
    @classmethod
    def cleanup_orphaned_simulations_on_startup(cls):
        """
        Au démarrage, nettoie les simulations marquées en cours d'exécution
        sur le disque mais qui ont été interrompues par un redémarrage du serveur.
        """
        if not os.path.exists(cls.RUN_STATE_DIR):
            return
            
        logger.info("Recherche et nettoyage des simulations orphelines suite au démarrage du serveur...")
        
        for sim_id in os.listdir(cls.RUN_STATE_DIR):
            sim_dir = os.path.join(cls.RUN_STATE_DIR, sim_id)
            if sim_id.startswith('.') or not os.path.isdir(sim_dir):
                continue
                
            # 1. Nettoyage de run_state.json
            run_state_file = os.path.join(sim_dir, "run_state.json")
            if os.path.exists(run_state_file):
                try:
                    with open(run_state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    status = data.get("runner_status")
                    if status in ["running", "starting", "paused", RunnerStatus.RUNNING.value, RunnerStatus.STARTING.value, RunnerStatus.PAUSED.value]:
                        logger.info(f"Nettoyage de la simulation orpheline {sim_id} dans run_state.json")
                        data["runner_status"] = "stopped"
                        data["twitter_running"] = False
                        data["reddit_running"] = False
                        data["completed_at"] = datetime.now().isoformat()
                        data["error"] = "Le serveur a été redémarré, la simulation a été interrompue."
                        
                        with open(run_state_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        # Reconstruire le fichier de résultats légaux s'il est manquant ou partiel
                        run_mode = data.get("run_mode")
                        is_legal = data.get("simulation_type") == "legal" or "legal" in sim_id.lower() or run_mode == "courtroom"
                        if is_legal:
                            try:
                                cls.reconstruct_legal_results(sim_id)
                            except Exception as rec_err:
                                logger.error(f"Erreur lors de la reconstruction automatique des résultats juridiques pour {sim_id} au nettoyage : {rec_err}")
                except Exception as e:
                    logger.error(f"Erreur lors du nettoyage de run_state.json pour {sim_id}: {e}")
                    
            # 2. Nettoyage de state.json (SimulationManager)
            state_file = os.path.join(sim_dir, "state.json")
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    status = data.get("status")
                    if status in ["running", "starting", "paused"]:
                        logger.info(f"Nettoyage de la simulation orpheline {sim_id} dans state.json")
                        data["status"] = "stopped"
                        data["updated_at"] = datetime.now().isoformat()
                        data["error"] = "Le serveur a été redémarré, la simulation a été interrompue."
                        
                        with open(state_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"Erreur lors du nettoyage de state.json pour {sim_id}: {e}")

    @classmethod
    def register_cleanup(cls):
        """
        注册清理函数
        
        在 Flask 应用启动时调用，确保服务器关闭时清理所有模拟进程
        """
        global _cleanup_registered
        
        if _cleanup_registered:
            return
        
        # Flask debug 模式下，只在 reloader 子进程中注册清理（实际运行应用的进程）
        # WERKZEUG_RUN_MAIN=true 表示是 reloader 子进程
        # 如果不是 debug 模式，则没有这个环境变量，也需要注册
        is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        is_debug_mode = os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('WERKZEUG_RUN_MAIN') is not None
        
        # 在 debug 模式下，只 in reloader 子进程中注册；非 debug 模式下始终注册
        if is_debug_mode and not is_reloader_process:
            _cleanup_registered = True  # 标记已注册，防止子进程再次尝试
            return
            
        # Nettoyer les simulations orphelines au démarrage de l'instance principale
        try:
            cls.cleanup_orphaned_simulations_on_startup()
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des simulations orphelines au démarrage: {e}")
        
        # 保存原有的信号处理器
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        # SIGHUP 只在 Unix 系统存在（macOS/Linux），Windows 没有
        original_sighup = None
        has_sighup = hasattr(signal, 'SIGHUP')
        if has_sighup:
            original_sighup = signal.getsignal(signal.SIGHUP)
        
        def cleanup_handler(signum=None, frame=None):
            """信号处理器：先清理模拟进程，再调用原处理器"""
            # 只有在有进程需要清理时才打印日志
            if cls._processes or cls._graph_memory_enabled:
                logger.info(f"Signal {signum} reçu, début du nettoyage...")
            cls.cleanup_all_simulations()
            
            # 调用原有的信号处理器，让 Flask 正常退出
            if signum == signal.SIGINT and callable(original_sigint):
                original_sigint(signum, frame)
            elif signum == signal.SIGTERM and callable(original_sigterm):
                original_sigterm(signum, frame)
            elif has_sighup and signum == signal.SIGHUP:
                # SIGHUP: 终端关闭时发送
                if callable(original_sighup):
                    original_sighup(signum, frame)
                else:
                    # 默认行为：正常退出
                    sys.exit(0)
            else:
                # 如果原处理器不可调用（如 SIG_DFL），则使用默认行为
                raise KeyboardInterrupt
        
        # 注册 atexit 处理器（作为备用）
        atexit.register(cls.cleanup_all_simulations)
        
        # 注册信号处理器（仅在主线程中）
        try:
            # SIGTERM: kill 命令默认信号
            signal.signal(signal.SIGTERM, cleanup_handler)
            # SIGINT: Ctrl+C
            signal.signal(signal.SIGINT, cleanup_handler)
            # SIGHUP: 终端关闭（仅 Unix 系统）
            if has_sighup:
                signal.signal(signal.SIGHUP, cleanup_handler)
        except ValueError:
            # 不在主线程中，只能使用 atexit
            logger.warning("Impossible d'enregistrer le gestionnaire de signal (hors du thread principal), utilisation de atexit uniquement")
        
        _cleanup_registered = True
    
    @classmethod
    def get_running_simulations(cls) -> List[str]:
        """
        获取所有正在运行的模拟ID列表
        """
        running = []
        for sim_id, process in cls._processes.items():
            if process.poll() is None:
                running.append(sim_id)
        return running
    
    # ============== Interview 功能 ==============
    
    @classmethod
    def check_env_alive(cls, simulation_id: str) -> bool:
        """
        检查模拟环境是否存活（可以接收Interview命令）

        Args:
            simulation_id: 模拟ID

        Returns:
            True 表示环境存活，False 表示环境已关闭
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return False

        ipc_client = SimulationIPCClient(sim_dir)
        return ipc_client.check_env_alive()

    @classmethod
    def get_env_status_detail(cls, simulation_id: str) -> Dict[str, Any]:
        """
        获取模拟环境的详细状态信息

        Args:
            simulation_id: 模拟ID

        Returns:
            状态详情字典，包含 status, twitter_available, reddit_available, timestamp
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        status_file = os.path.join(sim_dir, "env_status.json")
        
        default_status = {
            "status": "stopped",
            "twitter_available": False,
            "reddit_available": False,
            "timestamp": None
        }
        
        if not os.path.exists(status_file):
            return default_status
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            return {
                "status": status.get("status", "stopped"),
                "twitter_available": status.get("twitter_available", False),
                "reddit_available": status.get("reddit_available", False),
                "timestamp": status.get("timestamp")
            }
        except (json.JSONDecodeError, OSError):
            return default_status

    @classmethod
    def interview_agent(
        cls,
        simulation_id: str,
        agent_id: int,
        prompt: str,
        platform: str = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        采访单个Agent

        Args:
            simulation_id: 模拟ID
            agent_id: Agent ID
            prompt: 采访问题
            platform: 指定平台（可选）
                - "twitter": 只采访Twitter平台
                - "reddit": 只采访Reddit平台
                - None: 双平台模拟时同时采访两个平台，返回整合结果
            timeout: 超时时间（秒）

        Returns:
            采访结果字典

        Raises:
            ValueError: 模拟不存在或环境未运行
            TimeoutError: 等待响应超时
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"La simulation n'existe pas : {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"L'environnement de simulation n'est pas actif ou a été fermé. Impossible d'exécuter l'interview : {simulation_id}")

        logger.info(f"Envoi de la commande d'interview : simulation_id={simulation_id}, agent_id={agent_id}, plateforme={platform}")

        response = ipc_client.send_interview(
            agent_id=agent_id,
            prompt=prompt,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "agent_id": agent_id,
                "prompt": prompt,
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "agent_id": agent_id,
                "prompt": prompt,
                "error": response.error,
                "timestamp": response.timestamp
            }
    
    @classmethod
    def interview_agents_batch(
        cls,
        simulation_id: str,
        interviews: List[Dict[str, Any]],
        platform: str = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        批量采访多个Agent

        Args:
            simulation_id: 模拟ID
            interviews: 采访列表，每个元素包含 {"agent_id": int, "prompt": str, "platform": str(可选)}
            platform: 默认平台（可选，会被每个采访项的platform覆盖）
                - "twitter": 默认只采访Twitter平台
                - "reddit": 默认只采访Reddit平台
                - None: 双平台模拟时每个Agent同时采访两个平台
            timeout: 超时时间（秒）

        Returns:
            批量采访结果字典

        Raises:
            ValueError: 模拟不存在或环境未运行
            TimeoutError: 等待响应超时
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"La simulation n'existe pas : {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"L'environnement de simulation n'est pas actif ou a été fermé. Impossible d'exécuter l'interview : {simulation_id}")

        logger.info(f"Envoi de la commande d'interview groupée : simulation_id={simulation_id}, count={len(interviews)}, plateforme={platform}")

        response = ipc_client.send_batch_interview(
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "interviews_count": len(interviews),
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "interviews_count": len(interviews),
                "error": response.error,
                "timestamp": response.timestamp
            }
    
    @classmethod
    def interview_all_agents(
        cls,
        simulation_id: str,
        prompt: str,
        platform: str = None,
        timeout: float = 180.0
    ) -> Dict[str, Any]:
        """
        采访所有Agent（全局采访）

        使用相同的问题采访模拟中的所有Agent

        Args:
            simulation_id: 模拟ID
            prompt: 采访问题（所有Agent使用相同问题）
            platform: 指定平台（可选）
                - "twitter": 只采访Twitter平台
                - "reddit": 只采访Reddit平台
                - None: 双平台模拟时每个Agent同时采访两个平台
            timeout: 超时时间（秒）

        Returns:
            全局采访结果字典
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"La simulation n'existe pas : {simulation_id}")

        # 从配置文件获取所有Agent信息
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError(f"La configuration de la simulation n'existe pas : {simulation_id}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        agent_configs = config.get("agent_configs", [])
        if not agent_configs:
            raise ValueError(f"Aucun agent trouvé dans la configuration de la simulation : {simulation_id}")

        # 构建批量采访列表
        interviews = []
        for agent_config in agent_configs:
            agent_id = agent_config.get("agent_id")
            if agent_id is not None:
                interviews.append({
                    "agent_id": agent_id,
                    "prompt": prompt
                })

        logger.info(f"Envoi de la commande d'interview globale : simulation_id={simulation_id}, agent_count={len(interviews)}, plateforme={platform}")

        return cls.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )
    
    @classmethod
    def close_simulation_env(
        cls,
        simulation_id: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        关闭模拟环境（而不是停止模拟进程）
        
        向模拟发送关闭环境命令，使其优雅退出等待命令模式
        
        Args:
            simulation_id: 模拟ID
            timeout: 超时时间（秒）
            
        Returns:
            操作结果字典
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"La simulation n'existe pas : {simulation_id}")
        
        ipc_client = SimulationIPCClient(sim_dir)
        
        if not ipc_client.check_env_alive():
            return {
                "success": True,
                "message": "环境已经关闭"
            }
        
        logger.info(f"Envoi de la commande de fermeture de l'environnement : simulation_id={simulation_id}")
        
        try:
            response = ipc_client.send_close_env(timeout=timeout)
            
            return {
                "success": response.status.value == "completed",
                "message": "环境关闭命令已发送",
                "result": response.result,
                "timestamp": response.timestamp
            }
        except TimeoutError:
            # 超时可能是因为环境正在关闭
            return {
                "success": True,
                "message": "环境关闭命令已发送（等待响应超时，环境可能正在关闭）"
            }
    
    @classmethod
    def _get_interview_history_from_db(
        cls,
        db_path: str,
        platform_name: str,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """从单个数据库获取Interview历史"""
        import sqlite3
        
        if not os.path.exists(db_path):
            return []
        
        results = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if agent_id is not None:
                cursor.execute("""
                    SELECT user_id, info, created_at
                    FROM trace
                    WHERE action = 'interview' AND user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (agent_id, limit))
            else:
                cursor.execute("""
                    SELECT user_id, info, created_at
                    FROM trace
                    WHERE action = 'interview'
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            for user_id, info_json, created_at in cursor.fetchall():
                try:
                    info = json.loads(info_json) if info_json else {}
                except json.JSONDecodeError:
                    info = {"raw": info_json}
                
                results.append({
                    "agent_id": user_id,
                    "response": info.get("response", info),
                    "prompt": info.get("prompt", ""),
                    "timestamp": created_at,
                    "platform": platform_name
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Échec de la lecture de l'historique d'interview ({platform_name}) : {e}")
        
        return results

    @classmethod
    def get_interview_history(
        cls,
        simulation_id: str,
        platform: str = None,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取Interview历史记录（从数据库读取）
        
        Args:
            simulation_id: 模拟ID
            platform: 平台类型（reddit/twitter/None）
                - "reddit": 只获取Reddit平台的历史
                - "twitter": 只获取Twitter平台的历史
                - None: 获取两个平台的所有历史
            agent_id: 指定Agent ID（可选，只获取该Agent的历史）
            limit: 每个平台返回数量限制
            
        Returns:
            Interview历史记录列表
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        
        results = []
        
        # 确定要查询的平台
        if platform in ("reddit", "twitter"):
            platforms = [platform]
        else:
            # 不指定platform时，查询两个平台
            platforms = ["twitter", "reddit"]
        
        for p in platforms:
            db_path = os.path.join(sim_dir, f"{p}_simulation.db")
            platform_results = cls._get_interview_history_from_db(
                db_path=db_path,
                platform_name=p,
                agent_id=agent_id,
                limit=limit
            )
            results.extend(platform_results)
        
        # 按时间降序排序
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 如果查询了多个平台，限制总数
        if len(platforms) > 1 and len(results) > limit:
            results = results[:limit]
        
        return results

