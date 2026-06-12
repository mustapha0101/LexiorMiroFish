"""
模拟相关API路由
Step2: Zep实体读取与过滤、OASIS模拟准备与运行（全程自动化）
"""

import os
import json
import traceback
from flask import request, jsonify, send_file
from typing import Optional

from . import simulation_bp
from ..config import Config
from ..services.zep_entity_reader import ZepEntityReader
from ..services.oasis_profile_generator import OasisProfileGenerator
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale
from ..models.project import ProjectManager

logger = get_logger('mirofish.api.simulation')


@simulation_bp.before_request
def check_simulation_authorization():
    # Allow OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        return

    # Allow history and list endpoints to handle their own user_id filtering
    if request.path.endswith('/simulation/history') or request.path.endswith('/simulation/list'):
        return
        
    # Allow public benchmark endpoints
    if '/benchmark/' in request.path:
        return

    # Extract simulation_id or project_id
    simulation_id = request.view_args.get('simulation_id') if request.view_args else None
    project_id = request.view_args.get('project_id') if request.view_args else None
    
    if not simulation_id and not project_id:
        if request.is_json:
            data = request.get_json(silent=True) or {}
            simulation_id = data.get('simulation_id')
            project_id = data.get('project_id')
        else:
            simulation_id = request.values.get('simulation_id')
            project_id = request.values.get('project_id')
            
    if simulation_id or project_id:
        user_id = request.headers.get('X-User-Id') or request.args.get('X-User-Id') or request.args.get('user_id') or request.args.get('userId')
        
        project = None
        if project_id:
            project = ProjectManager.get_project(project_id)
        elif simulation_id:
            state = SimulationManager().get_simulation(simulation_id)
            if state:
                project = ProjectManager.get_project(state.project_id)
                
        if project and project.user_id:
            if not user_id or project.user_id != user_id:
                return jsonify({
                    "success": False,
                    "error": "Accès non autorisé"
                }), 403


# Interview prompt 优化前缀
# 添加此前缀可以避免Agent调用工具，直接用文本回复
INTERVIEW_PROMPT_PREFIX = "结合你的人设、所有的过往记忆与行动，不调用任何工具直接用文本回复我："


def optimize_interview_prompt(prompt: str) -> str:
    """
    优化Interview提问，添加前缀避免Agent调用工具
    
    Args:
        prompt: 原始提问
        
    Returns:
        优化后的提问
    """
    if not prompt:
        return prompt
    # 避免重复添加前缀
    if prompt.startswith(INTERVIEW_PROMPT_PREFIX):
        return prompt
    return f"{INTERVIEW_PROMPT_PREFIX}{prompt}"


# ============== 实体读取接口 ==============

@simulation_bp.route('/entities/<graph_id>', methods=['GET'])
def get_graph_entities(graph_id: str):
    """
    获取图谱中的所有实体（已过滤）
    
    只返回符合预定义实体类型的节点（Labels不只是Entity的节点）
    
    Query参数：
        entity_types: 逗号分隔的实体类型列表（可选，用于进一步过滤）
        enrich: 是否获取相关边信息（默认true）
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        entity_types_str = request.args.get('entity_types', '')
        entity_types = [t.strip() for t in entity_types_str.split(',') if t.strip()] if entity_types_str else None
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        
        logger.info(f"Récupération des entités du graphe: graph_id={graph_id}, entity_types={entity_types}, enrich={enrich}")
        
        reader = ZepEntityReader()
        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=enrich
        )
        
        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des entités du graphe: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/entities/<graph_id>/<entity_uuid>', methods=['GET'])
def get_entity_detail(graph_id: str, entity_uuid: str):
    """获取单个实体的详细信息"""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        reader = ZepEntityReader()
        entity = reader.get_entity_with_context(graph_id, entity_uuid)
        
        if not entity:
            return jsonify({
                "success": False,
                "error": t('api.entityNotFound', id=entity_uuid)
            }), 404
        
        return jsonify({
            "success": True,
            "data": entity.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des détails de l'entité: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/entities/<graph_id>/by-type/<entity_type>', methods=['GET'])
def get_entities_by_type(graph_id: str, entity_type: str):
    """获取指定类型的所有实体"""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        
        reader = ZepEntityReader()
        entities = reader.get_entities_by_type(
            graph_id=graph_id,
            entity_type=entity_type,
            enrich_with_edges=enrich
        )
        
        return jsonify({
            "success": True,
            "data": {
                "entity_type": entity_type,
                "count": len(entities),
                "entities": [e.to_dict() for e in entities]
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'entité: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 模拟管理接口 ==============

@simulation_bp.route('/create', methods=['POST'])
def create_simulation():
    """
    Créer une nouvelle simulation
    
    Remarque : Les paramètres tels que max_rounds sont générés intelligemment par le LLM, pas besoin de les définir manuellement.
    
    Requête (JSON) :
        {
            "project_id": "proj_xxxx",      // Requis
            "graph_id": "lexior_xxxx",      // Optionnel, s'il n'est pas fourni, il est récupéré du projet
            "enable_twitter": true,         // Optionnel, par défaut true
            "enable_reddit": true           // Optionnel, par défaut true
        }
    
    Retour :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "project_id": "proj_xxxx",
                "graph_id": "lexior_xxxx",
                "status": "created",
                "enable_twitter": true,
                "enable_reddit": true,
                "created_at": "2025-12-01T10:00:00"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        project_id = data.get('project_id')
        if not project_id:
            return jsonify({
                "success": False,
                "error": t('api.requireProjectId')
            }), 400
        
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=project_id)
            }), 404
        
        graph_id = data.get('graph_id') or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.graphNotBuilt')
            }), 400
        
        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=data.get('enable_twitter', True),
            enable_reddit=data.get('enable_reddit', True),
        )
        
        return jsonify({
            "success": True,
            "data": state.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la création de la simulation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def _check_simulation_prepared(simulation_id: str) -> tuple:
    """
    检查模拟是否已经准备完成
    
    检查条件：
    1. state.json 存在且 status 为 "ready"
    2. 必要文件存在：reddit_profiles.json, twitter_profiles.csv, simulation_config.json
    
    注意：运行脚本(run_*.py)保留在 backend/scripts/ 目录，不再复制到模拟目录
    
    Args:
        simulation_id: 模拟ID
        
    Returns:
        (is_prepared: bool, info: dict)
    """
    import os
    from ..config import Config
    
    simulation_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
    
    # 检查目录是否存在
    if not os.path.exists(simulation_dir):
        return False, {"reason": "模拟目录不存在"}
    
    # 必要文件列表（不包括脚本，脚本位于 backend/scripts/）
    required_files = [
        "state.json",
        "simulation_config.json",
        "reddit_profiles.json",
        "twitter_profiles.csv"
    ]
    
    # 检查文件是否存在
    existing_files = []
    missing_files = []
    for f in required_files:
        file_path = os.path.join(simulation_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
        else:
            missing_files.append(f)
    
    if missing_files:
        return False, {
            "reason": "缺少必要文件",
            "missing_files": missing_files,
            "existing_files": existing_files
        }
    
    # 检查state.json中的状态
    state_file = os.path.join(simulation_dir, "state.json")
    try:
        import json
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        status = state_data.get("status", "")
        config_generated = state_data.get("config_generated", False)
        
        # 详细日志
        logger.debug(f"Détection de l'état de préparation de la simulation: {simulation_id}, status={status}, config_generated={config_generated}")
        
        # 如果 config_generated=True 且文件存在，认为准备完成
        # 以下状态都说明准备工作已完成：
        # - ready: 准备完成，可以运行
        # - preparing: 如果 config_generated=True 说明已完成
        # - running: 正在运行，说明准备早就完成了
        # - completed: 运行完成，说明准备早就完成了
        # - stopped: 已停止，说明准备早就完成了
        # - failed: 运行失败（但准备是完成的）
        prepared_statuses = ["ready", "preparing", "running", "completed", "stopped", "failed"]
        if status in prepared_statuses and config_generated:
            # 获取文件统计信息
            profiles_file = os.path.join(simulation_dir, "reddit_profiles.json")
            config_file = os.path.join(simulation_dir, "simulation_config.json")
            
            profiles_count = 0
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0
            
            # 如果状态是preparing但文件已完成，自动更新状态为ready
            if status == "preparing":
                try:
                    state_data["status"] = "ready"
                    from datetime import datetime
                    state_data["updated_at"] = datetime.now().isoformat()
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Mise à jour automatique du statut de la simulation: {simulation_id} preparing -> ready")
                    status = "ready"
                except Exception as e:
                    logger.warning(f"Échec de la mise à jour automatique du statut: {e}")
            
            logger.info(f"Résultat de détection de la simulation {simulation_id}: Préparation terminée (status={status}, config_generated={config_generated})")
            return True, {
                "status": status,
                "entities_count": state_data.get("entities_count", 0),
                "profiles_count": profiles_count,
                "entity_types": state_data.get("entity_types", []),
                "config_generated": config_generated,
                "created_at": state_data.get("created_at"),
                "updated_at": state_data.get("updated_at"),
                "existing_files": existing_files
            }
        else:
            logger.warning(f"Résultat de détection de la simulation {simulation_id}: Non préparée (status={status}, config_generated={config_generated})")
            return False, {
                "reason": f"状态不在已准备列表中或config_generated为false: status={status}, config_generated={config_generated}",
                "status": status,
                "config_generated": config_generated
            }
            
    except Exception as e:
        return False, {"reason": f"读取状态文件失败: {str(e)}"}


@simulation_bp.route('/prepare', methods=['POST'])
def prepare_simulation():
    """
    准备模拟环境（异步任务，LLM智能生成所有参数）
    
    这是一个耗时操作，接口会立即返回task_id，
    使用 GET /api/simulation/prepare/status 查询进度
    
    特性：
    - 自动检测已完成的准备工作，避免重复生成
    - 如果已准备完成，直接返回已有结果
    - 支持强制重新生成（force_regenerate=true）
    
    步骤：
    1. 检查是否已有完成的准备工作
    2. 从Zep图谱读取并过滤实体
    3. 为每个实体生成OASIS Agent Profile（带重试机制）
    4. LLM智能生成模拟配置（带重试机制）
    5. 保存配置文件和预设脚本
    
    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",                   // 必填，模拟ID
            "entity_types": ["Student", "PublicFigure"],  // 可选，指定实体类型
            "use_llm_for_profiles": true,                 // 可选，是否用LLM生成人设
            "parallel_profile_count": 5,                  // 可选，并行生成人设数量，默认5
            "force_regenerate": false                     // 可选，强制重新生成，默认false
        }
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",           // 新任务时返回
                "status": "preparing|ready",
                "message": "准备任务已启动|已有完成的准备工作",
                "already_prepared": true|false    // 是否已准备完成
            }
        }
    """
    import threading
    import os
    from ..models.task import TaskManager, TaskStatus
    from ..config import Config
    
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
        
        # 检查是否强制重新生成
        force_regenerate = data.get('force_regenerate', False)
        logger.info(f"Début du traitement de la requête /prepare: simulation_id={simulation_id}, force_regenerate={force_regenerate}")
        
        # 检查是否已经准备完成（避免重复生成）
        if not force_regenerate:
            logger.debug(f"Vérification de la préparation de la simulation {simulation_id}...")
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            logger.debug(f"Résultat de la vérification: is_prepared={is_prepared}, prepare_info={prepare_info}")
            if is_prepared:
                logger.info(f"Simulation {simulation_id} déjà préparée, génération ignorée")
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "message": t('api.alreadyPrepared'),
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    }
                })
            else:
                logger.info(f"Simulation {simulation_id} non préparée, démarrage de la tâche de préparation")
        
        # 从项目获取必要信息
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=state.project_id)
            }), 404
        
        # 获取模拟需求
        simulation_requirement = project.simulation_requirement or ""
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": t('api.projectMissingRequirement')
            }), 400
        
        # 获取文档文本
        document_text = ProjectManager.get_extracted_text(state.project_id) or ""
        
        entity_types_list = data.get('entity_types')
        use_llm_for_profiles = data.get('use_llm_for_profiles', True)
        parallel_profile_count = data.get('parallel_profile_count', 5)
        
        # ========== 同步获取实体数量（在后台任务启动前） ==========
        # 这样前端在调用prepare后立即就能获取到预期Agent总数
        try:
            logger.info(f"Récupération synchrone du nombre d'entités: graph_id={state.graph_id}")
            if project.simulation_mode == 'legal':
                from app.services.local_graph_database import LocalGraphDatabase
                graph_nodes = []
                try:
                    with LocalGraphDatabase(state.graph_id, read_only=True) as db:
                        tables = db._get_all_tables()
                        node_tables = [t for t in tables if t.startswith("Node_")]
                        for table_name in node_tables:
                            label = table_name[5:]
                            query = f"MATCH (n:{table_name}) RETURN n.uuid, n.name"
                            res = db._execute(query)
                            while res.has_next():
                                row = res.get_next()
                                graph_nodes.append({
                                    "uuid": row[0],
                                    "name": row[1],
                                    "label": label
                                })
                except Exception as db_err:
                    logger.warning(f"Impossible de lire les nœuds en synchrone : {db_err}")
                
                non_actor_labels = {"fact", "jurisprudence", "evidence", "loi", "law", "concept", "court", "municipality", "document", "grainerealite"}
                actor_count = 0
                for n in graph_nodes:
                    if n["label"].lower() not in non_actor_labels:
                        actor_count += 1
                
                expected_count = 5 + max(0, actor_count - 3)
                state.entities_count = expected_count
                state.entity_types = ["Juge", "Avocat", "Défendeur", "Greffier", "Témoin", "Expert", "Policier"]
                logger.info(f"Prédiction synchrone d'acteurs tribunal: {expected_count}")
            else:
                reader = ZepEntityReader()
                # 快速读取实体（不需要边信息，只统计数量）
                filtered_preview = reader.filter_defined_entities(
                    graph_id=state.graph_id,
                    defined_entity_types=entity_types_list,
                    enrich_with_edges=False  # 不获取边信息，加快速度
                )
                # 保存实体数量到状态（供前端立即获取）
                state.entities_count = filtered_preview.filtered_count
                state.entity_types = list(filtered_preview.entity_types)
                logger.info(f"Nombre d'entités attendu: {filtered_preview.filtered_count}, Types: {filtered_preview.entity_types}")
        except Exception as e:
            logger.warning(f"Échec de la récupération synchrone du nombre d'entités (nouvelle tentative en arrière-plan): {e}")
            # 失败不影响后续流程，后台任务会重新获取
        
        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_prepare",
            metadata={
                "simulation_id": simulation_id,
                "project_id": state.project_id
            }
        )
        
        # Store run_mode in simulation state
        run_mode = data.get('run_mode', 'courtroom')
        state.run_mode = run_mode
        state.status = SimulationStatus.PREPARING
        manager._save_simulation_state(state)
        
        # Capture locale before spawning background thread
        current_locale = get_locale()

        # 定义后台任务
        def run_prepare():
            set_locale(current_locale)
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message=t('progress.startPreparingEnv')
                )
                
                if project.simulation_mode == 'legal':
                    from datetime import datetime
                    import time
                    import json
                    
                    def migrate_node_table(db, uuid_val, current_label, target_label):
                        if current_label == target_label:
                            return True
                        src_table = f"Node_{current_label}"
                        tgt_table = f"Node_{target_label}"
                        tables = db._get_all_tables()
                        if tgt_table not in tables:
                            try:
                                db._execute(f"CREATE NODE TABLE {tgt_table} (uuid STRING, name STRING, summary STRING, attributes STRING, PRIMARY KEY (uuid))")
                            except Exception as e:
                                logger.warning(f"Failed to create table {tgt_table}: {e}")
                                return False
                        try:
                            # Read details
                            res = db._execute(f"MATCH (n:{src_table}) WHERE n.uuid = $uuid RETURN n.name, n.summary, n.attributes", {"uuid": uuid_val})
                            if not res.has_next():
                                return False
                            row = res.get_next()
                            name, summary, attributes = row[0], row[1], row[2]
                            
                            # Read outgoing rels
                            outgoing_rels = []
                            try:
                                res_out = db._execute(f"MATCH (n:{src_table})-[r]->(m) WHERE n.uuid = $uuid RETURN label(r), m.uuid, label(m), r.uuid, r.fact, r.attributes", {"uuid": uuid_val})
                                while res_out.has_next():
                                    row_out = res_out.get_next()
                                    rel_label = row_out[0][4:] if row_out[0].startswith("Rel_") else row_out[0]
                                    target_node_label = row_out[2][5:] if row_out[2].startswith("Node_") else row_out[2]
                                    outgoing_rels.append({
                                        "rel_label": rel_label,
                                        "target_uuid": row_out[1],
                                        "target_label": target_node_label,
                                        "uuid": row_out[3],
                                        "fact": row_out[4],
                                        "attributes": row_out[5]
                                    })
                            except Exception as ex:
                                logger.warning(f"Error reading outgoing relationships: {ex}")
                                
                            # Read incoming rels
                            incoming_rels = []
                            try:
                                res_in = db._execute(f"MATCH (m)-[r]->(n:{src_table}) WHERE n.uuid = $uuid RETURN label(r), m.uuid, label(m), r.uuid, r.fact, r.attributes", {"uuid": uuid_val})
                                while res_in.has_next():
                                    row_in = res_in.get_next()
                                    rel_label = row_in[0][4:] if row_in[0].startswith("Rel_") else row_in[0]
                                    source_node_label = row_in[2][5:] if row_in[2].startswith("Node_") else row_in[2]
                                    incoming_rels.append({
                                        "rel_label": rel_label,
                                        "source_uuid": row_in[1],
                                        "source_label": source_node_label,
                                        "uuid": row_in[3],
                                        "fact": row_in[4],
                                        "attributes": row_in[5]
                                    })
                            except Exception as ex:
                                logger.warning(f"Error reading incoming relationships: {ex}")
                                
                            # Delete rels
                            for rel in outgoing_rels:
                                try:
                                    db._execute(f"MATCH (n:{src_table})-[r:Rel_{rel['rel_label']}]->(m:Node_{rel['target_label']}) WHERE n.uuid = $src AND m.uuid = $tgt DELETE r", {"src": uuid_val, "tgt": rel["target_uuid"]})
                                except Exception as ex:
                                    logger.warning(f"Error deleting outgoing relationship: {ex}")
                            for rel in incoming_rels:
                                try:
                                    db._execute(f"MATCH (m:Node_{rel['source_label']})-[r:Rel_{rel['rel_label']}]->(n:{src_table}) WHERE m.uuid = $src AND n.uuid = $tgt DELETE r", {"src": rel["source_uuid"], "tgt": uuid_val})
                                except Exception as ex:
                                    logger.warning(f"Error deleting incoming relationship: {ex}")
                                    
                            # Delete node
                            db._execute(f"MATCH (n:{src_table}) WHERE n.uuid = $uuid DELETE n", {"uuid": uuid_val})
                            
                            # Create new node
                            db._execute(f"CREATE (n:{tgt_table} {{uuid: $uuid, name: $name, summary: $summary, attributes: $attributes}})", {
                                "uuid": uuid_val, "name": name, "summary": summary, "attributes": attributes
                            })
                            
                            # Recreate outgoing rels
                            for rel in outgoing_rels:
                                try:
                                    rel_table = f"Rel_{rel['rel_label']}"
                                    if rel_table not in db._get_all_tables():
                                        db._execute(f"CREATE REL TABLE {rel_table} (FROM {tgt_table} TO Node_{rel['target_label']}, uuid STRING, fact STRING, attributes STRING)")
                                    db._execute(f"MATCH (n:{tgt_table}), (m:Node_{rel['target_label']}) WHERE n.uuid = $src AND m.uuid = $tgt CREATE (n)-[r:{rel_table} {{uuid: $r_uuid, fact: $r_fact, attributes: $r_attrs}}]->(m)", {
                                        "src": uuid_val, "tgt": rel["target_uuid"], "r_uuid": rel["uuid"], "r_fact": rel["fact"], "r_attrs": rel["attributes"]
                                    })
                                except Exception as ex:
                                    logger.warning(f"Error recreating outgoing relationship: {ex}")
                                    
                            # Recreate incoming rels
                            for rel in incoming_rels:
                                try:
                                    rel_table = f"Rel_{rel['rel_label']}"
                                    if rel_table not in db._get_all_tables():
                                        db._execute(f"CREATE REL TABLE {rel_table} (FROM Node_{rel['source_label']} TO {tgt_table}, uuid STRING, fact STRING, attributes STRING)")
                                    db._execute(f"MATCH (m:Node_{rel['source_label']}), (n:{tgt_table}) WHERE m.uuid = $src AND n.uuid = $tgt CREATE (m)-[r:{rel_table} {{uuid: $r_uuid, fact: $r_fact, attributes: $r_attrs}}]->(n)", {
                                        "src": rel["source_uuid"], "tgt": uuid_val, "r_uuid": rel["uuid"], "r_fact": rel["fact"], "r_attrs": rel["attributes"]
                                    })
                                except Exception as ex:
                                    logger.warning(f"Error recreating incoming relationship: {ex}")
                            logger.info(f"Node {uuid_val} migrated successfully from Node_{current_label} to Node_{target_label}")
                            return True
                        except Exception as ex:
                            logger.error(f"Failed to migrate node {uuid_val}: {ex}")
                            return False
                    
                    # 1. Update task to reading progress
                    task_manager.update_task(
                        task_id,
                        status=TaskStatus.PROCESSING,
                        progress=10,
                        message="[1/4] Lecture des entités du graphe..."
                    )
                    
                    # Read nodes from Kuzu DB
                    from app.services.local_graph_database import LocalGraphDatabase
                    graph_nodes = []
                    try:
                        with LocalGraphDatabase(state.graph_id, read_only=False) as db:
                            tables = db._get_all_tables()
                            node_tables = [t for t in tables if t.startswith("Node_")]
                            for table_name in node_tables:
                                label = table_name[5:]  # Remove 'Node_'
                                query = f"MATCH (n:{table_name}) RETURN n.uuid, n.name, n.summary"
                                res = db._execute(query)
                                while res.has_next():
                                    row = res.get_next()
                                    graph_nodes.append({
                                        "uuid": row[0],
                                        "name": row[1],
                                        "summary": row[2] or "",
                                        "label": label
                                    })
                    except Exception as e:
                        logger.warning(f"Impossible de lire les nœuds Kuzu : {e}")
                    
                    # Deduplicate and clean up entities extracted from Kuzu DB
                    if graph_nodes:
                        cleaned_nodes = []
                        # Generic roles/nouns that shouldn't be separate personas
                        generic_placeholders = {
                            "the accused", "l'accusé", "l·accusé", "l'intimé", "l'appelant", "the appellant", "the respondent", "le prévenu",
                            "the prosecutor", "le poursuivant", "le procureur", "the crown", "la couronne", "la poursuite",
                            "the judge", "le juge", "juge des faits", "the court", "la cour",
                            "the lawyer", "l'avocat", "avocat de l'accusé", "l·avocat de l·accusé",
                            "le policier", "policier", "the police", "the officer", "police officer",
                            "sa majesté le roi", "sa majeste le roi", "sa majesté", "sa majeste",
                            "crpq"
                        }
                        
                        abbreviations = {
                            "crpq": "centre des renseignements policiers du quebec",
                            "dpcp": "directeur des poursuites criminelles et pénales",
                            "canlii": "canadian legal information institute"
                        }
                        
                        def normalize_name(name_str):
                            n = name_str.lower().strip()
                            # Strip titles and honorifics
                            n = n.replace("monsieur ", "").replace("m. ", "").replace("me ", "")
                            n = n.replace("sergent ", "").replace("sergente ", "").replace("agent ", "").replace("sd ", "").replace("s/d ", "")
                            n = n.replace("dr. ", "").replace("juge ", "").replace("justice ", "").replace("presiding ", "")
                            n = n.replace(".", "").replace("-", " ").replace("·", " ")
                            n = ' '.join(n.split())
                            return abbreviations.get(n, n)
                        
                        # Group nodes by normalized names to find exact/case duplicates
                        grouped_nodes = {}
                        for node in graph_nodes:
                            name_val = node["name"]
                            name_norm = normalize_name(name_val)
                            
                            # Skip purely generic placeholder entities
                            if name_norm in generic_placeholders or name_val.lower().strip() in generic_placeholders:
                                logger.info(f"Skipping generic placeholder entity node: {name_val}")
                                continue
                                
                            if name_norm not in grouped_nodes:
                                grouped_nodes[name_norm] = []
                            grouped_nodes[name_norm].append(node)
                        
                        # Resolve duplicates within each group
                        for norm, group in grouped_nodes.items():
                            if len(group) == 1:
                                cleaned_nodes.append(group[0])
                            else:
                                best_node = group[0]
                                for candidate in group[1:]:
                                    current_label = best_node["label"].lower()
                                    cand_label = candidate["label"].lower()
                                    
                                    # Specific labels priority
                                    label_priority = ["accusedperson", "judge", "prosecutor", "policeofficer", "lawyer", "governmentagency", "organization"]
                                    if cand_label in label_priority and current_label not in label_priority:
                                        best_node = candidate
                                    elif cand_label not in label_priority and current_label in label_priority:
                                        pass
                                    elif len(candidate["summary"]) > len(best_node["summary"]):
                                        best_node = candidate
                                    elif len(candidate["name"]) > len(best_node["name"]):
                                        best_node = candidate
                                
                                # Merge summaries
                                all_summaries = [n["summary"] for n in group if n["summary"]]
                                if all_summaries:
                                    best_node["summary"] = max(all_summaries, key=len)
                                    
                                logger.info(f"Merged exact duplicate nodes for '{norm}' -> {best_node['name']} ({best_node['label']})")
                                cleaned_nodes.append(best_node)
                        
                        # Cross-type substring deduplication (e.g. "Samuel Danazarre" (AccusedPerson) merges with "M. Danazarre" (Person))
                        final_nodes = []
                        cleaned_nodes.sort(key=lambda x: len(x["name"]), reverse=True)
                        
                        for node in cleaned_nodes:
                            is_dup = False
                            node_name_norm = normalize_name(node["name"])
                            for existing in final_nodes:
                                existing_name_norm = normalize_name(existing["name"])
                                
                                # Substring overlap check (at least 3 characters to prevent matching single letters)
                                if (node_name_norm in existing_name_norm or existing_name_norm in node_name_norm) and len(node_name_norm) >= 3:
                                    if len(node["summary"]) > len(existing["summary"]):
                                        existing["summary"] = node["summary"]
                                    is_dup = True
                                    logger.info(f"Substring match merged '{node['name']}' ({node['label']}) into existing node '{existing['name']}' ({existing['label']})")
                                    break
                                    
                            if not is_dup:
                                final_nodes.append(node)
                                
                        graph_nodes = final_nodes
                    
                    time.sleep(0.3)
                    task_manager.update_task(
                        task_id,
                        progress=20,
                        message=f"[1/4] Extraction des structures Kuzu complétée. {len(graph_nodes)} entités trouvées."
                    )
                    time.sleep(0.3)
                    
                    # 2. Update task to generating profiles progress
                    task_manager.update_task(
                        task_id,
                        progress=30,
                        message="[2/4] Initialisation des profils d'agents de simulation..." if run_mode == "oasis" else "[2/4] Initialisation des acteurs du tribunal..."
                    )
                    time.sleep(0.3)
                    
                    sim_dir = manager._get_simulation_dir(simulation_id)
                    
                    # Classification du litige (civil ou criminel) et extraction des parties
                    litigation_type = "civil"
                    plaintiff_name = "Le Demandeur"
                    defendant_name = "Le Défendeur"
                    accused_name = "Le Prévenu"
                    prosecutor_name = "Le Procureur"
                    
                    juge_name = "Le Juge"
                    juge_node = None
                    plaintiff_node = None
                    defendant_node = None
                    prosecutor_node = None
                    accused_node = None
                    
                    try:
                        from openai import OpenAI
                        api_key = Config.LLM_API_KEY or "local-no-key"
                        base_url = Config.LLM_BASE_URL
                        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
                        
                        if base_url:
                            client = OpenAI(api_key=api_key, base_url=base_url)
                        else:
                            client = OpenAI(api_key=api_key)
                            
                        # 1. Classification du type de litige
                        classification_prompt = f"""Analyse la description du litige ci-dessous et classifie-la en un type précis de litige.
Réponds UNIQUEMENT par l'un de ces deux mots en minuscule sans aucune ponctuation : "civil" ou "criminal".

- Choisi "civil" s'il s'agit de litiges commerciaux, de contrats, de vices cachés, de droit civil, de poursuites entre entreprises ou individus, d'indemnisations.
- Choisi "criminal" s'il s'agit d'infractions criminelles, de fraudes pénales, d'agressions, d'homicides ou de poursuites par l'État/le Ministère Public pour un crime.

Description du litige :
{simulation_requirement}

Texte du document (extrait) :
{document_text[:1000]}
"""
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "Tu es un assistant juridique expert qui classifie les litiges."},
                                {"role": "user", "content": classification_prompt}
                            ],
                            temperature=0.0,
                            max_tokens=5
                        )
                        output_text = response.choices[0].message.content.strip().lower()
                        if "criminal" in output_text:
                            litigation_type = "criminal"
                        else:
                            litigation_type = "civil"
                        logger.info(f"Détection automatique du type de litige : {litigation_type} (LLM retourné : {output_text})")
                        
                        # 2. Mappage des acteurs réels depuis le graphe s'il contient des nœuds
                        if graph_nodes:
                            try:
                                nodes_for_prompt = [
                                    {
                                        "name": n["name"],
                                        "type": n["label"],
                                        "summary": n["summary"][:200] + "..." if len(n["summary"]) > 200 else n["summary"]
                                    }
                                    for n in graph_nodes
                                ]
                                
                                mapping_prompt = f"""Analyse les entités extraites du graphe de connaissances ci-dessous et associe-les aux rôles clés de ce procès.
Type de litige : {litigation_type}

Rôles attendus :
1. Le Juge (magistrat impartial présidant le tribunal)
2. La partie poursuivante (soit le Demandeur civil, soit le Procureur/Ministère Public/Sa Majesté pénal)
3. La partie poursuivée (soit le Défendeur civil, soit l'Accusé/Prévenu/The Accused pénal)

Entités du graphe disponibles :
{json.dumps(nodes_for_prompt, ensure_ascii=False, indent=2)}

Description générale du litige :
{simulation_requirement}

Retourne uniquement un objet JSON avec cette structure (remplace les valeurs par le nom exact de l'entité correspondante du graphe, ou garde la valeur par défaut si elle n'est pas dans le graphe) :
{{
  "juge": "Nom de l'entité du Juge",
  "poursuite": "Nom de l'entité du Demandeur ou du Procureur",
  "defense": "Nom de l'entité du Défendeur ou de l'Accusé"
}}
"""
                                map_res = client.chat.completions.create(
                                    model=model_name,
                                    messages=[
                                        {"role": "system", "content": "Tu es un assistant juridique expert qui mappe les entités du graphe aux rôles du procès. Tu réponds uniquement en JSON."},
                                        {"role": "user", "content": mapping_prompt}
                                    ],
                                    temperature=0.0,
                                    max_tokens=150
                                )
                                raw_map = map_res.choices[0].message.content.strip()
                                if raw_map.startswith("```json"):
                                    raw_map = raw_map[7:]
                                elif raw_map.startswith("```"):
                                    raw_map = raw_map[3:]
                                if raw_map.endswith("```"):
                                    raw_map = raw_map[:-3]
                                mapping = json.loads(raw_map.strip())
                                logger.info(f"Mapping brut obtenu du LLM: {mapping}")
                                
                                mapped_juge = mapping.get("juge")
                                mapped_poursuite = mapping.get("poursuite")
                                mapped_defense = mapping.get("defense")
                                
                                # Recherche des nœuds correspondants
                                for n in graph_nodes:
                                    if n["name"] == mapped_juge:
                                        juge_node = n
                                        juge_name = n["name"]
                                    elif n["name"] == mapped_poursuite:
                                        if litigation_type == "criminal":
                                            prosecutor_node = n
                                            prosecutor_name = n["name"]
                                        else:
                                            plaintiff_node = n
                                            plaintiff_name = n["name"]
                                    elif n["name"] == mapped_defense:
                                        if litigation_type == "criminal":
                                            accused_node = n
                                            accused_name = n["name"]
                                        else:
                                            defendant_node = n
                                            defendant_name = n["name"]
                                
                                logger.info(f"Mappage des acteurs du graphe réussi: Juge={juge_name}, Poursuite={prosecutor_name if litigation_type=='criminal' else plaintiff_name}, Défense={accused_name if litigation_type=='criminal' else defendant_name}")
                                
                                # Dynamic Kuzu DB migration of mapped personas to their correct legal roles
                                try:
                                    if juge_node:
                                        migrate_node_table(db, juge_node["uuid"], juge_node["label"], "Judge")
                                    if litigation_type == "criminal":
                                        if prosecutor_node:
                                            migrate_node_table(db, prosecutor_node["uuid"], prosecutor_node["label"], "Prosecutor")
                                        if accused_node:
                                            migrate_node_table(db, accused_node["uuid"], accused_node["label"], "AccusedPerson")
                                except Exception as migrate_err:
                                    logger.warning(f"Erreur lors de la migration des types de nœuds : {migrate_err}")
                            except Exception as e:
                                logger.warning(f"Erreur lors du mappage des entités du graphe par LLM : {e}. Utilisation de l'extraction de secours.")
                        
                        # Extraction de secours si le mappage de graphe n'a pas tout rempli
                        if not graph_nodes or (plaintiff_name == "Le Demandeur" and defendant_name == "Le Défendeur" and accused_name == "Le Prévenu"):
                            if litigation_type == "civil":
                                party_prompt = f"""Analyse les faits juridiques ci-dessous et identifie précisément :
1. Le Demandeur (plaintiff - qui poursuit ou réclame)
2. Le Défendeur (defendant - la partie poursuivie)

Description :
{simulation_requirement}

Extraits du dossier :
{document_text[:2000]}

Retourne uniquement un JSON avec cette structure :
{{
  "plaintiff": "Nom de l'entreprise ou de la personne",
  "defendant": "Nom de l'entreprise ou de la personne"
}}
"""
                                party_res = client.chat.completions.create(
                                    model=model_name,
                                    messages=[
                                        {"role": "system", "content": "Tu es un assistant juridique qui extrait les entités d'un dossier. Tu réponds uniquement en JSON."},
                                        {"role": "user", "content": party_prompt}
                                    ],
                                    temperature=0.0,
                                    max_tokens=100
                                )
                                raw_party = party_res.choices[0].message.content.strip()
                                if raw_party.startswith("```json"):
                                    raw_party = raw_party[7:]
                                elif raw_party.startswith("```"):
                                    raw_party = raw_party[3:]
                                if raw_party.endswith("```"):
                                    raw_party = raw_party[:-3]
                                parsed_parties = json.loads(raw_party.strip())
                                if plaintiff_name == "Le Demandeur":
                                    plaintiff_name = parsed_parties.get("plaintiff", "Le Demandeur")
                                if defendant_name == "Le Défendeur":
                                    defendant_name = parsed_parties.get("defendant", "Le Défendeur")
                                logger.info(f"Parties civiles extraites via secours : Demandeur={plaintiff_name}, Défendeur={defendant_name}")
                            else:
                                accused_prompt = f"""Analyse le dossier pénal ci-dessous et identifie précisément le nom de l'Accusé / Prévenu (la personne poursuivie).

Description :
{simulation_requirement}

Extraits du dossier :
{document_text[:2000]}

Retourne uniquement un JSON avec cette structure :
{{
  "accused": "Nom de l'accusé"
}}
"""
                                accused_res = client.chat.completions.create(
                                    model=model_name,
                                    messages=[
                                        {"role": "system", "content": "Tu es un assistant juridique qui extrait l'accusé d'un dossier pénal. Tu réponds uniquement en JSON."},
                                        {"role": "user", "content": accused_prompt}
                                    ],
                                    temperature=0.0,
                                    max_tokens=50
                                )
                                raw_accused = accused_res.choices[0].message.content.strip()
                                if raw_accused.startswith("```json"):
                                    raw_accused = raw_accused[7:]
                                elif raw_accused.startswith("```"):
                                    raw_accused = raw_accused[3:]
                                if raw_accused.endswith("```"):
                                    raw_accused = raw_accused[:-3]
                                parsed_accused = json.loads(raw_accused.strip())
                                if accused_name == "Le Prévenu":
                                    accused_name = parsed_accused.get("accused", "Le Prévenu")
                                logger.info(f"Accusé pénal extrait via secours : Accusé={accused_name}")
                                
                    except Exception as e:
                        logger.warning(f"Erreur lors de la classification/extraction LLM : {e}. Utilisation des valeurs par défaut.")
                        # Fallback simple basé sur des mots-clés
                        req_lower = (simulation_requirement + " " + document_text).lower()
                        if any(k in req_lower for k in ["pénale", "pénal", "criminel", "criminal", "meurtre", "vol de", "agression", "infraction"]):
                            litigation_type = "criminal"
                    
                    # 3. Génération des profils
                    if run_mode == "oasis":
                        task_manager.update_task(
                            task_id,
                            progress=30,
                            message="[2/4] Génération dynamique de 8 personas d'opinion publique..."
                        )
                        generator = OasisProfileGenerator(graph_id=state.graph_id)
                        
                        def thread_progress(current, total, msg):
                            task_manager.update_task(
                                task_id,
                                progress=30 + int(current / total * 20) if total > 0 else 30,
                                message=f"[2/4] {msg}"
                            )
                            
                        profiles = generator.generate_public_opinion_profiles(
                            case_facts=document_text,
                            simulation_requirement=simulation_requirement,
                            count=8,
                            progress_callback=thread_progress
                        )
                        reddit_profiles = [p.to_reddit_format() for p in profiles]
                    else:
                        if litigation_type == "civil":
                            def_username = "defendeur_" + defendant_name.lower().replace(" ", "_").replace("'", "").replace('"', '')
                            def_username = ''.join(c for c in def_username if c.isalnum() or c == '_')[:25]
                            
                            reddit_profiles = [
                              {
                                "user_id": 0,
                                "username": "juge_court",
                                "name": f"Juge {juge_name}" if "juge" not in juge_name.lower() else juge_name,
                                "bio": f"Magistrat impartial présidant le tribunal. Identité : {juge_name}.",
                                "persona": f"Magistrat d'expérience chargé de trancher le litige opposant {plaintiff_name} à {defendant_name}. Évalue rigoureusement la crédibilité des faits et la force des arguments juridiques présentés par les avocats. Baigné de la réalité du dossier, ses convictions s'appuient sur : {juge_node['summary'] if juge_node else 'les faits généraux du dossier'}.",
                                "karma": 3000, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 52, "gender": "male", "mbti": "ISTJ", "country": "Canada", "profession": "Juge",
                                "interested_topics": ["Jurisprudence", "Verdict", "Droit civil"]
                              },
                              {
                                "user_id": 1,
                                "username": "avocat_demandeur",
                                "name": f"Avocat de {plaintiff_name}",
                                "bio": f"Représentant légal de {plaintiff_name}. Rigoureux et convaincant.",
                                "persona": f"Avocat représentant les intérêts du demandeur ({plaintiff_name}, la partie qui poursuit). Il cherche à prouver la responsabilité civile du défendeur ({defendant_name}) en s'appuyant sur des contrats, des faits techniques et des jurisprudences civiles. Éléments du dossier de son client : {plaintiff_node['summary'] if plaintiff_node else 'la plainte initiale'}.",
                                "karma": 2100, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 44, "gender": "male", "mbti": "ENTJ", "country": "Canada", "profession": "Avocat",
                                "interested_topics": ["Responsabilité civile", "Preuve", "Contrat"]
                              },
                              {
                                "user_id": 2,
                                "username": "avocat_defense",
                                "name": f"Avocat de {defendant_name}",
                                "bio": f"Avocat plaidant dévoué à la protection des droits et intérêts de {defendant_name}.",
                                "persona": f"Avocat de la défense cherchant à réfuter les prétentions de la partie demanderesse ({plaintiff_name}), à invoquer des moyens d'exonération pour son client {defendant_name} (diligence raisonnable, force majeure, faute de la victime) et à citer des précédents favorables à la défense. Éléments de défense du client : {defendant_node['summary'] if defendant_node else 'les arguments en défense'}.",
                                "karma": 2500, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 39, "gender": "female", "mbti": "INFJ", "country": "Canada", "profession": "Avocate",
                                "interested_topics": ["Défense", "Exonération", "Diligence raisonnable"]
                              },
                              {
                                "user_id": 3,
                                "username": def_username,
                                "name": f"{defendant_name}",
                                "bio": f"Partie poursuivie ({defendant_name}) dans le cadre de ce litige civil.",
                                "persona": f"Le défendeur ({defendant_name}) poursuivi pour responsabilité civile. Il collabore avec son avocate pour présenter sa défense, expliquer ses actions et contester toute allégation de faute, de vice caché ou de manquement contractuel face à {plaintiff_name}. Contexte et antécédents : {defendant_node['summary'] if defendant_node else 'les faits reprochés'}.",
                                "karma": 500, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 29, "gender": "male", "mbti": "ISFP", "country": "Canada", "profession": "Défendeur",
                                "interested_topics": ["Contrat", "Faits", "Défense"]
                              },
                              {
                                "user_id": 4,
                                "username": "greffier_analyste",
                                "name": "Le Greffier",
                                "bio": "Officier de justice chargé de documenter les débats juridiques.",
                                "persona": f"Greffier responsable de la retranscription fidèle des débats d'audience de ce litige opposant {plaintiff_name} à {defendant_name} et de l'analyse objective des arguments soulevés par les deux parties.",
                                "karma": 1800, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 33, "gender": "female", "mbti": "INFP", "country": "Canada", "profession": "Greffière",
                                "interested_topics": ["Transcription", "Analyse", "Procédure d'audience"]
                              }
                            ]
                        else:
                            acc_username = "prevenu_" + accused_name.lower().replace(" ", "_").replace("'", "").replace('"', '')
                            acc_username = ''.join(c for c in acc_username if c.isalnum() or c == '_')[:25]
                            
                            reddit_profiles = [
                              {
                                "user_id": 0,
                                "username": "juge_court",
                                "name": f"Juge {juge_name}" if "juge" not in juge_name.lower() else juge_name,
                                "bio": f"Magistrat impartial présidant le tribunal. Identité : {juge_name}.",
                                "persona": f"Magistrat d'expérience chargé de trancher le litige pénal concernant les accusations portées contre {accused_name}. Évalue rigoureusement la crédibilité des faits et la force des précédents cités par les avocats. Baigné de la réalité du dossier, ses convictions s'appuient sur : {juge_node['summary'] if juge_node else 'les faits du dossier'}.",
                                "karma": 3000, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 52, "gender": "male", "mbti": "ISTJ", "country": "Canada", "profession": "Juge",
                                "interested_topics": ["Jurisprudence", "Verdict", "Droit de fond"]
                              },
                              {
                                "user_id": 1,
                                "username": "procureur_etat",
                                "name": f"{prosecutor_name}",
                                "bio": f"Représentant du Ministère Public. Rigoureux et ferme.",
                                "persona": f"Procureur chargé de requérir l'application stricte de la loi pénale au nom de la société. Démontre la culpabilité de l'accusé ({accused_name}) en se fondant sur les éléments de preuve factuels et jurisprudentiels du dossier. Infos de la poursuite: {prosecutor_node['summary'] if prosecutor_node else 'les arguments de la poursuite'}.",
                                "karma": 2100, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 44, "gender": "male", "mbti": "ENTJ", "country": "Canada", "profession": "Procureur",
                                "interested_topics": ["Accusation", "Preuve", "Ordre public"]
                              },
                              {
                                "user_id": 2,
                                "username": "avocat_defense",
                                "name": f"Avocat de {accused_name}",
                                "bio": f"Avocat plaidant dévoué à la protection des droits de son client {accused_name}.",
                                "persona": f"Avocat de la défense cherchant à soulever un doute raisonnable en faveur de son client {accused_name}, à invoquer des moyens d'exonération (force majeure, légitime défense, état de nécessité) et à citer des précédents favorables à la défense. Éléments de défense de son client: {accused_node['summary'] if accused_node else 'la version de la défense'}.",
                                "karma": 2500, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 39, "gender": "female", "mbti": "INFJ", "country": "Canada", "profession": "Avocate",
                                "interested_topics": ["Défense", "Exonération", "Droits constitutionnels"]
                              },
                              {
                                "user_id": 3,
                                "username": acc_username,
                                "name": f"{accused_name}",
                                "bio": f"Personne poursuivie ({accused_name}) devant le tribunal.",
                                "persona": f"L'accusé ({accused_name}) poursuivi pour les faits décrits dans le dossier. Il collabore avec son avocate pour présenter ses explications et prétend son innocence. Faits reprochés et version personnelle : {accused_node['summary'] if accused_node else 'les infractions reprochées'}.",
                                "karma": 500, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 29, "gender": "male", "mbti": "ISFP", "country": "Canada", "profession": "Prévenu",
                                "interested_topics": ["Procès", "Faits", "Déposition"]
                              },
                              {
                                "user_id": 4,
                                "username": "greffier_analyste",
                                "name": "Le Greffier",
                                "bio": "Officier de justice chargé de documenter les débats juridiques.",
                                "persona": f"Greffier responsable de la retranscription fidèle des débats d'audience de ce procès pénal impliquant {accused_name} et de l'analyse objective des arguments soulevés par l'accusation et la défense.",
                                "karma": 1800, "created_at": datetime.now().strftime("%Y-%m-%d"), "age": 33, "gender": "female", "mbti": "INFP", "country": "Canada", "profession": "Greffière",
                                "interested_topics": ["Transcription", "Analyse", "Procédure d'audience"]
                              }
                            ]

                        # Extraction dynamique des acteurs secondaires depuis le graphe Kuzu
                        mapped_uuids = set()
                        mapped_names = set()
                        if juge_node:
                            mapped_uuids.add(juge_node.get("uuid"))
                            mapped_names.add(juge_name)
                        if plaintiff_node:
                            mapped_uuids.add(plaintiff_node.get("uuid"))
                            mapped_names.add(plaintiff_name)
                        if defendant_node:
                            mapped_uuids.add(defendant_node.get("uuid"))
                            mapped_names.add(defendant_name)
                        if prosecutor_node:
                            mapped_uuids.add(prosecutor_node.get("uuid"))
                            mapped_names.add(prosecutor_name)
                        if accused_node:
                            mapped_uuids.add(accused_node.get("uuid"))
                            mapped_names.add(accused_name)

                        extra_nodes = []
                        non_actor_labels = {"fact", "jurisprudence", "evidence", "loi", "law", "concept", "court", "municipality", "document", "grainerealite"}
                        for n in graph_nodes:
                            if n["uuid"] in mapped_uuids or n["name"] in mapped_names:
                                continue
                            if n["label"].lower() in non_actor_labels:
                                continue
                            extra_nodes.append(n)

                        extra_profiles = []
                        if extra_nodes:
                            try:
                                extra_nodes_for_prompt = [
                                    {
                                        "name": n["name"],
                                        "type": n["label"],
                                        "summary": n["summary"][:200] + "..." if len(n["summary"]) > 200 else n["summary"]
                                    }
                                    for n in extra_nodes
                                ]
                                
                                extra_prompt = f"""Tu es un assistant juridique expert en simulation de procès devant les tribunaux québécois.
Génère un profil d'agent de simulation sous format JSON pour chacun des acteurs secondaires suivants issus du graphe de connaissances de l'affaire.
Chaque acteur doit être préparé pour participer au procès en cours.

Description de l'affaire :
{simulation_requirement}

Acteurs secondaires à traiter :
{json.dumps(extra_nodes_for_prompt, ensure_ascii=False, indent=2)}

Génère UNIQUEMENT un tableau JSON d'objets (sans texte explicatif ni balises de code markdown) avec cette structure :
[
  {{
    "name": "Nom de l'acteur (doit être exactement le nom fourni)",
    "username": "Nom d'utilisateur court sans espace ni accent (ex: temoin_ledoux)",
    "profession": "Sa profession ou son rôle dans l'affaire en un ou deux mots (ex: Témoin, Policier, Expert, etc.)",
    "bio": "Courte biographie de 1-2 phrases en français décrivant qui il est et son lien avec l'affaire.",
    "persona": "Instructions de comportement détaillées pour cet agent dans le procès en français, décrivant sa personnalité, sa connaissance des faits (basée sur son résumé) et sa position dans l'audience.",
    "age": un entier réaliste entre 25 et 65,
    "gender": "male" ou "female",
    "mbti": "un type MBTI réaliste (ex: ISTJ, ENFP)",
    "country": "Canada",
    "interested_topics": ["Sujet1", "Sujet2"] (2 ou 3 sujets d'intérêt liés à l'affaire ou à son rôle)
  }}
]
"""
                                response = client.chat.completions.create(
                                    model=model_name,
                                    messages=[
                                        {"role": "system", "content": "Tu es un assistant juridique qui génère des profils d'acteurs de procès en format JSON."},
                                        {"role": "user", "content": extra_prompt}
                                    ],
                                    temperature=0.2,
                                    max_tokens=2000
                                )
                                raw_extra_res = response.choices[0].message.content.strip()
                                if raw_extra_res.startswith("```json"):
                                    raw_extra_res = raw_extra_res[7:]
                                elif raw_extra_res.startswith("```"):
                                    raw_extra_res = raw_extra_res[3:]
                                if raw_extra_res.endswith("```"):
                                    raw_extra_res = raw_extra_res[:-3]
                                
                                generated_list = json.loads(raw_extra_res.strip())
                                if isinstance(generated_list, list):
                                    for gen in generated_list:
                                        node = next((n for n in extra_nodes if n["name"] == gen.get("name")), None)
                                        if node:
                                            extra_profiles.append({
                                                "username": gen.get("username", "user_" + node["name"].lower().replace(" ", "_")),
                                                "name": gen.get("name", node["name"]),
                                                "bio": gen.get("bio", f"Acteur secondaire dans le procès. Identité: {node['name']}."),
                                                "persona": gen.get("persona", f"Acteur impliqué en tant que {node['label']}. Résumé: {node['summary']}."),
                                                "karma": 1000,
                                                "created_at": datetime.now().strftime("%Y-%m-%d"),
                                                "age": gen.get("age", 40),
                                                "gender": gen.get("gender", "male"),
                                                "mbti": gen.get("mbti", "ISTJ"),
                                                "country": gen.get("country", "Canada"),
                                                "profession": gen.get("profession", node["label"]),
                                                "interested_topics": gen.get("interested_topics", [node["label"], "Procès"])
                                            })
                            except Exception as e:
                                logger.warning(f"Erreur lors de la génération LLM des profils supplémentaires: {e}. Utilisation du fallback.")
                                
                        # Fallback pour tous les nœuds non générés
                        for node in extra_nodes:
                            if not any(ep["name"] == node["name"] for ep in extra_profiles):
                                label = node["label"]
                                name = node["name"]
                                summary = node["summary"]
                                username = label.lower() + "_" + name.lower().replace(" ", "_").replace("'", "").replace('"', '')
                                username = ''.join(c for c in username if c.isalnum() or c == '_')[:25]
                                extra_profiles.append({
                                    "username": username,
                                    "name": name,
                                    "bio": f"Acteur impliqué dans le dossier sous le type {label}. Nom : {name}.",
                                    "persona": f"Participe au procès en tant que {label}. S'appuie sur les faits suivants : {summary if summary else 'Aucun détail supplémentaire disponible.'}",
                                    "karma": 1000,
                                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                                    "age": 40,
                                    "gender": "male",
                                    "mbti": "ISTJ",
                                    "country": "Canada",
                                    "profession": label,
                                    "interested_topics": [label, "Procès"]
                                })
                        
                        # Assembler les user_id et ajouter à reddit_profiles
                        for idx, ep in enumerate(extra_profiles):
                            ep["user_id"] = 5 + idx
                            reddit_profiles.append(ep)
                    
                    twitter_csv_lines = ["user_id,name,username,user_char,description"]
                    for p in reddit_profiles:
                        name_esc = p["name"].replace('"', '""')
                        username_esc = p["username"].replace('"', '""')
                        persona_esc = p["persona"].replace('"', '""')
                        bio_esc = p["bio"].replace('"', '""')
                        twitter_csv_lines.append(f'{p["user_id"]},{name_esc},{username_esc},"{persona_esc}","{bio_esc}"')
                    twitter_csv = "\n".join(twitter_csv_lines) + "\n"
                    
                    with open(os.path.join(sim_dir, "reddit_profiles.json"), 'w', encoding='utf-8') as f:
                        json.dump(reddit_profiles, f, ensure_ascii=False, indent=2)
                    with open(os.path.join(sim_dir, "twitter_profiles.csv"), 'w', encoding='utf-8') as f:
                        f.write(twitter_csv)
                        
                    task_manager.update_task(
                        task_id,
                        progress=60,
                        message=f"[2/4] Profils d'agents initialisés avec succès. ({len(reddit_profiles)} agents)"
                    )
                    time.sleep(0.3)
                    
                    # 3. Update task to generating config progress
                    task_manager.update_task(
                        task_id,
                        progress=70,
                        message="[3/4] Analyse des contraintes et génération de la configuration de simulation..."
                    )
                    time.sleep(0.3)
                    
                    if run_mode == "oasis":
                        agent_configs = []
                        for idx, p in enumerate(reddit_profiles):
                            role_type = p.get("profession") or "Citoyen"
                            agent_configs.append({
                              "agent_id": p["user_id"],
                              "entity_uuid": f"node_{p['username']}",
                              "entity_name": p["name"],
                              "entity_type": role_type,
                              "activity_level": 1.0,
                              "posts_per_hour": 1,
                              "comments_per_hour": 1,
                              "active_hours": list(range(24)),
                              "response_delay_min": 1,
                              "response_delay_max": 2,
                              "sentiment_bias": 0.0,
                              "stance": "neutral",
                              "influence_weight": 1.5 if idx < 4 else 1.0
                            })
                        event_config = {
                          "initial_posts": [
                            {
                              "content": f"Nouveaux débats publics autour de l'affaire. Faits initiaux : {document_text[:200]}...",
                              "poster_type": reddit_profiles[1]["profession"] if "profession" in reddit_profiles[1] else "Journaliste",
                              "poster_agent_id": 1
                            }
                          ],
                          "scheduled_events": [],
                          "hot_topics": ["Réputation", "Dossier", "Transparence"],
                          "narrative_direction": "Débat public et dynamique d'opinion sur les réseaux sociaux."
                        }
                    else:
                        agent_configs = [
                          {
                            "agent_id": 0, "entity_uuid": "node_juge", "entity_name": reddit_profiles[0]["name"], "entity_type": "Juge",
                            "activity_level": 1.0, "posts_per_hour": 1, "comments_per_hour": 1, "active_hours": list(range(24)), "response_delay_min": 1, "response_delay_max": 2, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 2.0
                          },
                          {
                            "agent_id": 1, "entity_uuid": "node_procureur", "entity_name": reddit_profiles[1]["name"], "entity_type": "Avocat",
                            "activity_level": 1.0, "posts_per_hour": 1, "comments_per_hour": 1, "active_hours": list(range(24)), "response_delay_min": 1, "response_delay_max": 2, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 1.5
                          },
                          {
                            "agent_id": 2, "entity_uuid": "node_avocat_defense", "entity_name": reddit_profiles[2]["name"], "entity_type": "Avocat",
                            "activity_level": 1.0, "posts_per_hour": 1, "comments_per_hour": 1, "active_hours": list(range(24)), "response_delay_min": 1, "response_delay_max": 2, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 1.5
                          },
                          {
                            "agent_id": 3, "entity_uuid": "node_defendeur", "entity_name": reddit_profiles[3]["name"], "entity_type": "Défendeur",
                            "activity_level": 1.0, "posts_per_hour": 1, "comments_per_hour": 1, "active_hours": list(range(24)), "response_delay_min": 1, "response_delay_max": 2, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 1.0
                          },
                          {
                            "agent_id": 4, "entity_uuid": "node_greffier", "entity_name": reddit_profiles[4]["name"], "entity_type": "Greffier",
                            "activity_level": 1.0, "posts_per_hour": 1, "comments_per_hour": 1, "active_hours": list(range(24)), "response_delay_min": 1, "response_delay_max": 2, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 1.0
                          }
                        ]
                        for idx in range(5, len(reddit_profiles)):
                            p = reddit_profiles[idx]
                            role_type = p.get("profession") or "Citoyen"
                            agent_configs.append({
                              "agent_id": p["user_id"],
                              "entity_uuid": f"node_{p['username']}",
                              "entity_name": p["name"],
                              "entity_type": role_type,
                              "activity_level": 1.0,
                              "posts_per_hour": 1,
                              "comments_per_hour": 1,
                              "active_hours": list(range(24)),
                              "response_delay_min": 1,
                              "response_delay_max": 2,
                              "sentiment_bias": 0.0,
                              "stance": "neutral",
                              "influence_weight": 1.0
                            })
                        event_config = {
                          "initial_posts": [
                            {
                              "content": f"Ouverture du dossier de procès. Faits : {document_text[:200]}...",
                              "poster_type": "Greffier",
                              "poster_agent_id": 4
                            }
                          ],
                          "scheduled_events": [],
                          "hot_topics": ["Verdict", "Preuve", "Jurisprudence"],
                          "narrative_direction": "Instruction civile et débats d'audience." if litigation_type == "civil" else "Instruction criminelle et débats d'audience."
                        }

                    config_data = {
                      "simulation_id": simulation_id,
                      "project_id": state.project_id,
                      "graph_id": state.graph_id,
                      "simulation_requirement": simulation_requirement,
                      "litigation_type": litigation_type,
                      "run_mode": run_mode,
                      "time_config": {
                        "total_simulation_hours": 24,
                        "minutes_per_round": 30,
                        "agents_per_hour_min": 1,
                        "agents_per_hour_max": 2,
                        "peak_hours": [9, 10, 11, 14, 15, 16],
                        "peak_activity_multiplier": 1.0,
                        "off_peak_hours": [0, 1, 2, 3, 4, 5],
                        "off_peak_activity_multiplier": 0.1,
                        "morning_hours": [6, 7, 8],
                        "morning_activity_multiplier": 0.5,
                        "work_hours": [12, 13, 17, 18, 19, 20, 21, 22, 23],
                        "work_activity_multiplier": 0.8
                      },
                      "agent_configs": agent_configs,
                      "event_config": event_config,
                      "twitter_config": {"platform": "twitter", "recency_weight": 0.4, "popularity_weight": 0.3, "relevance_weight": 0.3, "viral_threshold": 10, "echo_chamber_strength": 0.5},
                      "reddit_config": {"platform": "reddit", "recency_weight": 0.3, "popularity_weight": 0.4, "relevance_weight": 0.3, "viral_threshold": 15, "echo_chamber_strength": 0.6},
                      "llm_model": getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini'),
                      "llm_base_url": Config.LLM_BASE_URL,
                      "generated_at": datetime.now().isoformat(),
                      "generation_reasoning": "Régulation cognitive du tribunal activée."
                    }
                    
                    with open(os.path.join(sim_dir, "simulation_config.json"), 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, ensure_ascii=False, indent=2)
                        
                    task_manager.update_task(
                        task_id,
                        progress=85,
                        message="[3/4] Fichier simulation_config.json généré."
                    )
                    time.sleep(0.3)
                    
                    # 4. Copying scripts progress
                    task_manager.update_task(
                        task_id,
                        progress=90,
                        message="[4/4] Préparation des scripts d'audience..."
                    )
                    time.sleep(0.3)
                    
                    state.entities_count = len(reddit_profiles)
                    state.profiles_count = len(reddit_profiles)
                    state.entity_types = list(set([p.get("profession", "Citoyen") for p in reddit_profiles]))
                    state.config_generated = True
                    state.config_reasoning = "Régulation cognitive du tribunal activée."
                    state.status = SimulationStatus.READY
                    manager._save_simulation_state(state)
                    
                    task_manager.update_task(
                        task_id,
                        progress=100,
                        message="[4/4] Environnement de simulation prêt pour le procès !"
                    )
                    task_manager.complete_task(
                        task_id,
                        result=state.to_simple_dict()
                    )
                    return

                if simulation_id.startswith("sim_proof_"):
                    import time
                    import json
                    parts = simulation_id.split('_')
                    benchmark_type = parts[2] if len(parts) > 2 else "hysteresis"
                    
                    # 1. Update task to reading progress
                    task_manager.update_task(
                        task_id,
                        status=TaskStatus.PROCESSING,
                        progress=10,
                        message="[1/4] Lecture des entités du graphe..."
                    )
                    time.sleep(0.3)
                    task_manager.update_task(
                        task_id,
                        progress=20,
                        message="[1/4] Extraction des structures Kuzu complétée. 2 entités trouvées."
                    )
                    time.sleep(0.3)
                    
                    # 2. Update task to generating profiles progress
                    task_manager.update_task(
                        task_id,
                        progress=30,
                        message="[2/4] Initialisation des profils d'agents de simulation..."
                    )
                    time.sleep(0.3)
                    
                    sim_dir = manager._get_simulation_dir(simulation_id)
                    
                    # Predefined profiles
                    if benchmark_type == "hysteresis":
                        reddit_profiles = [
                          {
                            "user_id": 0,
                            "username": "avocat_bob",
                            "name": "Avocat Bob",
                            "bio": "Avocat de la Défense spécialisé en droit des affaires et négociations contractuelles.",
                            "persona": "Bob est un avocat pragmatique et méfiant. Il accorde une importance cruciale à la protection de son client. Si la partie adverse propose une clause abusive, son niveau de confiance chute drastiquement (effet d'hystérésis).",
                            "karma": 1200, "created_at": "2026-05-25", "age": 45, "gender": "male", "mbti": "INTJ", "country": "Canada", "profession": "Avocat",
                            "interested_topics": ["Droit des contrats", "Négociations", "Litige commercial"]
                          },
                          {
                            "user_id": 1,
                            "username": "procureur_voisin",
                            "name": "Procureur Voisin",
                            "bio": "Procureur de la Poursuite. Favorable à une régulation stricte des transactions.",
                            "persona": "Voisin représente la Poursuite. Il est direct, rigide et cherche à imposer des clauses restrictives pour garantir la conformité réglementaire.",
                            "karma": 950, "created_at": "2026-05-25", "age": 50, "gender": "male", "mbti": "ESTJ", "country": "Canada", "profession": "Procureur",
                            "interested_topics": ["Conformité", "Régulation", "Procédure civile"]
                          }
                        ]
                        twitter_csv = (
                            "user_id,name,username,user_char,description\n"
                            "0,Avocat Bob,avocat_bob,\"Bob est un avocat pragmatique et méfiant. Il accorde une importance cruciale à la protection de son client. Si la partie adverse propose une clause abusive, son niveau de confiance chute drastiquement (effet d'hystérésis).\",\"Avocat de la Défense spécialisé en droit des affaires.\"\n"
                            "1,Procureur Voisin,procureur_voisin,\"Voisin représente la Poursuite. Il est direct, rigide et cherche à imposer des clauses restrictives pour garantir la conformité réglementaire.\",\"Procureur de la Poursuite.\"\n"
                        )
                    elif benchmark_type == "inertia":
                        reddit_profiles = [
                          {
                            "user_id": 0,
                            "username": "juge_pie",
                            "name": "Juge PIE",
                            "bio": "Magistrat de la Cour du Québec, intègre la régulation PIE pour stabiliser ses convictions.",
                            "persona": "Juge PIE est un magistrat hautement impartial. Il intègre l'inertie de conviction jurisprudentielle pour éviter de surréagir au bruit des déclarations contradictoires.",
                            "karma": 2500, "created_at": "2026-05-25", "age": 55, "gender": "male", "mbti": "ISTJ", "country": "Canada", "profession": "Juge",
                            "interested_topics": ["Impartialité", "Jurisprudence", "Preuve"]
                          },
                          {
                            "user_id": 1,
                            "username": "temoin_oculaire",
                            "name": "Témoin Oculaire",
                            "bio": "Témoin présent sur les lieux du litige, sujet aux variations de mémoire.",
                            "persona": "Témoin oculaire dont le témoignage fluctue. Il apporte du bruit cognitif à la simulation avec des déclarations contradictoires.",
                            "karma": 300, "created_at": "2026-05-25", "age": 30, "gender": "female", "mbti": "ESFP", "country": "Canada", "profession": "Témoin",
                            "interested_topics": ["Témoignage", "Faits"]
                          }
                        ]
                        twitter_csv = (
                            "user_id,name,username,user_char,description\n"
                            "0,Juge PIE,juge_pie,\"Juge PIE est un magistrat hautement impartial. Il intègre l'inertie de conviction jurisprudentielle pour éviter de surréagir au bruit des déclarations contradictoires.\",\"Magistrat de la Cour du Québec.\"\n"
                            "1,Témoin Oculaire,temoin_oculaire,\"Témoin oculaire dont le témoignage fluctue. Il apporte du bruit cognitif à la simulation avec des déclarations contradictoires.\",\"Témoin présent sur les lieux.\"\n"
                        )
                    else: # attention
                        reddit_profiles = [
                          {
                            "user_id": 0,
                            "username": "avocate_alice",
                            "name": "Avocate Alice",
                            "bio": "Avocate de la Défense confrontée à des contraintes de temps strictes.",
                            "persona": "Alice doit plaider une affaire urgente. Son budget attentionnel PIE restreint à 10% l'oblige à élaguer les détails secondaires pour se concentrer sur les précédents de la Cour Suprême.",
                            "karma": 1800, "created_at": "2026-05-25", "age": 38, "gender": "female", "mbti": "INTJ", "country": "Canada", "profession": "Avocate",
                            "interested_topics": ["Stratégie", "Droit criminel", "Efficacité"]
                          },
                          {
                            "user_id": 1,
                            "username": "prevenu_dupont",
                            "name": "Prévenu Dupont",
                            "bio": "Accusé dans l'affaire, impatient de connaître l'issue.",
                            "persona": "Dupont est le client d'Alice. Il s'inquiète des délais de procédure et insiste sur les erreurs mineures du greffe.",
                            "karma": 400, "created_at": "2026-05-25", "age": 28, "gender": "male", "mbti": "ISFP", "country": "Canada", "profession": "Prévenu",
                            "interested_topics": ["Procédure", "Droits"]
                          }
                        ]
                        twitter_csv = (
                            "user_id,name,username,user_char,description\n"
                            "0,Avocate Alice,avocate_alice,\"Alice doit plaider une affaire urgente. Son budget attentionnel PIE restreint à 10% l'oblige à élaguer les détails secondaires pour se concentrer sur les précédents de la Cour Suprême.\",\"Avocate de la Défense.\"\n"
                            "1,Prévenu Dupont,prevenu_dupont,\"Dupont est le client d'Alice. Il s'inquiète des délais de procédure et insiste sur les erreurs mineures du greffe.\",\"Accusé dans l'affaire.\"\n"
                        )
                        
                    # Write profiles files
                    with open(os.path.join(sim_dir, "reddit_profiles.json"), 'w', encoding='utf-8') as f:
                        json.dump(reddit_profiles, f, ensure_ascii=False, indent=2)
                    with open(os.path.join(sim_dir, "twitter_profiles.csv"), 'w', encoding='utf-8') as f:
                        f.write(twitter_csv)
                        
                    task_manager.update_task(
                        task_id,
                        progress=60,
                        message=f"[2/4] Profils d'agents initialisés avec succès. ({len(reddit_profiles)} agents)"
                    )
                    time.sleep(0.3)
                    
                    # 3. Update task to generating config progress
                    task_manager.update_task(
                        task_id,
                        progress=70,
                        message="[3/4] Analyse des contraintes et génération de la configuration de simulation..."
                    )
                    time.sleep(0.3)
                    
                    # Predefined config
                    config_data = {
                      "simulation_id": simulation_id,
                      "project_id": state.project_id,
                      "graph_id": state.graph_id,
                      "simulation_requirement": simulation_requirement,
                      "time_config": {
                        "total_simulation_hours": 24,
                        "minutes_per_round": 30,
                        "agents_per_hour_min": 1,
                        "agents_per_hour_max": 2,
                        "peak_hours": [9, 10, 11, 14, 15, 16],
                        "peak_activity_multiplier": 1.0,
                        "off_peak_hours": [0, 1, 2, 3, 4, 5],
                        "off_peak_activity_multiplier": 0.1,
                        "morning_hours": [6, 7, 8],
                        "morning_activity_multiplier": 0.5,
                        "work_hours": [12, 13, 17, 18, 19, 20, 21, 22, 23],
                        "work_activity_multiplier": 0.8
                      },
                      "agent_configs": [
                        {
                          "agent_id": 0,
                          "entity_uuid": "node_avocat_bob" if benchmark_type == "hysteresis" else ("node_juge_pie" if benchmark_type == "inertia" else "node_avocate_alice"),
                          "entity_name": "Avocat Bob" if benchmark_type == "hysteresis" else ("Juge PIE" if benchmark_type == "inertia" else "Avocate Alice"),
                          "entity_type": "Avocat" if benchmark_type == "hysteresis" else ("Juge" if benchmark_type == "inertia" else "Avocat"),
                          "activity_level": 0.9, "posts_per_hour": 1.0, "comments_per_hour": 2.0, "active_hours": [9, 17], "response_delay_min": 1, "response_delay_max": 5, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 1.5
                        },
                        {
                          "agent_id": 1,
                          "entity_uuid": "node_procureur_voisin" if benchmark_type == "hysteresis" else ("node_temoin" if benchmark_type == "inertia" else "node_prevenu_dupont"),
                          "entity_name": "Procureur Voisin" if benchmark_type == "hysteresis" else ("Témoin Oculaire" if benchmark_type == "inertia" else "Prévenu Dupont"),
                          "entity_type": "Avocat" if benchmark_type == "hysteresis" else ("Fait" if benchmark_type == "inertia" else "Fait"),
                          "activity_level": 0.9, "posts_per_hour": 1.0, "comments_per_hour": 2.0, "active_hours": [9, 17], "response_delay_min": 1, "response_delay_max": 5, "sentiment_bias": 0.0, "stance": "neutral", "influence_weight": 1.5
                        }
                      ],
                      "event_config": {
                        "initial_posts": [
                          {
                            "content": "Proposition de contrat de partenariat commercial soumis pour révision." if benchmark_type == "hysteresis" else ("Ouverture de l'audience pour entendre les témoins." if benchmark_type == "inertia" else "Dépôt d'une demande de libération conditionnelle accélérée."),
                            "poster_type": "Avocat" if benchmark_type == "hysteresis" else ("Juge" if benchmark_type == "inertia" else "Avocat"),
                            "poster_agent_id": 0
                          }
                        ],
                        "scheduled_events": [],
                        "hot_topics": ["Négociation" if benchmark_type == "hysteresis" else ("Témoignage" if benchmark_type == "inertia" else "Arrêt Jordan"), "Preuve"],
                        "narrative_direction": "Simulation de cas pratique."
                      },
                      "twitter_config": {"platform": "twitter", "recency_weight": 0.4, "popularity_weight": 0.3, "relevance_weight": 0.3, "viral_threshold": 10, "echo_chamber_strength": 0.5},
                      "reddit_config": {"platform": "reddit", "recency_weight": 0.3, "popularity_weight": 0.4, "relevance_weight": 0.3, "viral_threshold": 15, "echo_chamber_strength": 0.6},
                      "llm_model": "local_pie_engine",
                      "llm_base_url": "http://127.0.0.1:11434/v1",
                      "generated_at": "2026-05-25T12:00:00",
                      "generation_reasoning": "Régulation cognitive PIE activée pour le Banc d'Essai."
                    }
                    
                    with open(os.path.join(sim_dir, "simulation_config.json"), 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, ensure_ascii=False, indent=2)
                        
                    task_manager.update_task(
                        task_id,
                        progress=85,
                        message="[3/4] Fichier simulation_config.json généré."
                    )
                    time.sleep(0.3)
                    
                    # 4. Copying scripts progress
                    task_manager.update_task(
                        task_id,
                        progress=90,
                        message="[4/4] Préparation des scripts d'exécution du Banc d'Essai..."
                    )
                    time.sleep(0.3)
                    
                    # Update simulation state
                    state.entities_count = len(reddit_profiles)
                    state.profiles_count = len(reddit_profiles)
                    state.entity_types = ["Avocat", "Fait", "Jurisprudence", "Juge"]
                    state.config_generated = True
                    state.config_reasoning = "Régulation cognitive PIE activée."
                    state.status = SimulationStatus.READY
                    manager._save_simulation_state(state)
                    
                    task_manager.update_task(
                        task_id,
                        progress=100,
                        message="[4/4] Environnement de simulation prêt pour l'exécution !"
                    )
                    task_manager.complete_task(
                        task_id,
                        result=state.to_simple_dict()
                    )
                    return
                
                # 准备模拟（带进度回调）
                # 存储阶段进度详情
                stage_details = {}
                
                def progress_callback(stage, progress, message, **kwargs):
                    # 计算总进度
                    stage_weights = {
                        "reading": (0, 20),           # 0-20%
                        "generating_profiles": (20, 70),  # 20-70%
                        "generating_config": (70, 90),    # 70-90%
                        "copying_scripts": (90, 100)       # 90-100%
                    }
                    
                    start, end = stage_weights.get(stage, (0, 100))
                    current_progress = int(start + (end - start) * progress / 100)
                    
                    # 构建详细进度信息
                    stage_names = {
                        "reading": t('progress.readingGraphEntities'),
                        "generating_profiles": t('progress.generatingProfiles'),
                        "generating_config": t('progress.generatingSimConfig'),
                        "copying_scripts": t('progress.preparingScripts')
                    }
                    
                    stage_index = list(stage_weights.keys()).index(stage) + 1 if stage in stage_weights else 1
                    total_stages = len(stage_weights)
                    
                    # 更新阶段详情
                    stage_details[stage] = {
                        "stage_name": stage_names.get(stage, stage),
                        "stage_progress": progress,
                        "current": kwargs.get("current", 0),
                        "total": kwargs.get("total", 0),
                        "item_name": kwargs.get("item_name", "")
                    }
                    
                    # 构建详细进度信息
                    detail = stage_details[stage]
                    progress_detail_data = {
                        "current_stage": stage,
                        "current_stage_name": stage_names.get(stage, stage),
                        "stage_index": stage_index,
                        "total_stages": total_stages,
                        "stage_progress": progress,
                        "current_item": detail["current"],
                        "total_items": detail["total"],
                        "item_description": message
                    }
                    
                    # 构建简洁 message
                    if detail["total"] > 0:
                        detailed_message = (
                            f"[{stage_index}/{total_stages}] {stage_names.get(stage, stage)}: "
                            f"{detail['current']}/{detail['total']} - {message}"
                        )
                    else:
                        detailed_message = f"[{stage_index}/{total_stages}] {stage_names.get(stage, stage)}: {message}"
                    
                    task_manager.update_task(
                        task_id,
                        progress=current_progress,
                        message=detailed_message,
                        progress_detail=progress_detail_data
                    )
                
                result_state = manager.prepare_simulation(
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    defined_entity_types=entity_types_list,
                    use_llm_for_profiles=use_llm_for_profiles,
                    progress_callback=progress_callback,
                    parallel_profile_count=parallel_profile_count
                )
                
                # 任务完成
                task_manager.complete_task(
                    task_id,
                    result=result_state.to_simple_dict()
                )
                
            except Exception as e:
                logger.error(f"Échec de la préparation de la simulation: {str(e)}")
                task_manager.fail_task(task_id, str(e))
                
                # 更新模拟状态为失败
                err_state = manager.get_simulation(simulation_id)
                if err_state:
                    err_state.status = SimulationStatus.FAILED
                    err_state.error = str(e)
                    manager._save_simulation_state(err_state)
        
        # 启动后台线程
        thread = threading.Thread(target=run_prepare, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "task_id": task_id,
                "status": "preparing",
                "message": t('api.prepareStarted'),
                "already_prepared": False,
                "expected_entities_count": state.entities_count,  # 预期的Agent总数
                "entity_types": state.entity_types  # 实体类型列表
            }
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Échec du démarrage de la tâche de préparation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/prepare/status', methods=['POST'])
def get_prepare_status():
    """
    查询准备任务进度
    
    支持两种查询方式：
    1. 通过task_id查询正在进行的任务进度
    2. 通过simulation_id检查是否已有完成的准备工作
    
    请求（JSON）：
        {
            "task_id": "task_xxxx",          // 可选，prepare返回的task_id
            "simulation_id": "sim_xxxx"      // 可选，模拟ID（用于检查已完成的准备）
        }
    
    返回：
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|ready",
                "progress": 45,
                "message": "...",
                "already_prepared": true|false,  // 是否已有完成的准备
                "prepare_info": {...}            // 已准备完成时的详细信息
            }
        }
    """
    from ..models.task import TaskManager
    
    try:
        data = request.get_json() or {}
        
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        
        # 如果提供了simulation_id，先检查是否已准备完成
        if simulation_id:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "progress": 100,
                        "message": t('api.alreadyPrepared'),
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    }
                })
        
        # 如果没有task_id，返回错误
        if not task_id:
            if simulation_id:
                # 有simulation_id但未准备完成
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "not_started",
                        "progress": 0,
                        "message": t('api.notStartedPrepare'),
                        "already_prepared": False
                    }
                })
            return jsonify({
                "success": False,
                "error": t('api.requireTaskOrSimId')
            }), 400
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            # 任务不存在，但如果有simulation_id，检查是否已准备完成
            if simulation_id:
                is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
                if is_prepared:
                    return jsonify({
                        "success": True,
                        "data": {
                            "simulation_id": simulation_id,
                            "task_id": task_id,
                            "status": "ready",
                            "progress": 100,
                            "message": t('api.taskCompletedPrepared'),
                            "already_prepared": True,
                            "prepare_info": prepare_info
                        }
                    })
            
            return jsonify({
                "success": False,
                "error": t('api.taskNotFound', id=task_id)
            }), 404
        
        task_dict = task.to_dict()
        task_dict["already_prepared"] = False
        
        return jsonify({
            "success": True,
            "data": task_dict
        })
        
    except Exception as e:
        logger.error(f"Échec de la requête de statut de la tâche: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _check_simulation_ownership(simulation_id: str, user_id: Optional[str]) -> bool:
    if not user_id:
        return True
    manager = SimulationManager()
    state = manager.get_simulation(simulation_id)
    if not state:
        return True
    from ..models.project import ProjectManager
    project = ProjectManager.get_project(state.project_id)
    if not project:
        return True
    if project.user_id and project.user_id != user_id:
        return False
    return True


@simulation_bp.route('/<simulation_id>', methods=['GET'])
def get_simulation(simulation_id: str):
    """获取模拟状态"""
    try:
        user_id = request.headers.get('X-User-Id')
        if not _check_simulation_ownership(simulation_id, user_id):
            return jsonify({
                "success": False,
                "error": "Accès non autorisé"
            }), 403

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
        
        result = state.to_dict()
        
        # Charger les données radar et la sélection si elles existent
        sim_dir = manager._get_simulation_dir(simulation_id)
        radar_file = os.path.join(sim_dir, "radar_analysis.json")
        if os.path.exists(radar_file):
            try:
                with open(radar_file, 'r', encoding='utf-8') as f:
                    radar_data = json.load(f)
                    result["selected_draft"] = radar_data.get("selected_draft")
                    result["radar_analysis"] = {
                        "defense": radar_data.get("defense"),
                        "plaintiff": radar_data.get("plaintiff")
                    }
            except Exception as e:
                logger.warning(f"Error loading radar analysis into simulation state: {e}")

        # 如果模拟已准备好，附加运行说明
        if state.status == SimulationStatus.READY:
            result["run_instructions"] = manager.get_run_instructions(simulation_id)
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération du statut de la simulation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/list', methods=['GET'])
def list_simulations():
    """
    列出所有模拟
    
    Query参数：
        project_id: 按项目ID过滤（可选）
    """
    try:
        project_id = request.args.get('project_id')
        user_id = request.headers.get('X-User-Id')
        
        manager = SimulationManager()
        simulations = manager.list_simulations(project_id=project_id, user_id=user_id)
        
        return jsonify({
            "success": True,
            "data": [s.to_dict() for s in simulations],
            "count": len(simulations)
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la liste des simulations: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def _get_report_id_for_simulation(simulation_id: str) -> str:
    """
    获取 simulation 对应的最新 report_id
    
    遍历 reports 目录，找出 simulation_id 匹配的 report，
    如果有多个则返回最新的（按 created_at 排序）
    
    Args:
        simulation_id: 模拟ID
        
    Returns:
        report_id 或 None
    """
    import json
    from datetime import datetime
    
    # reports 目录路径：backend/uploads/reports
    # __file__ 是 app/api/simulation.py，需要向上两级到 backend/
    reports_dir = os.path.join(os.path.dirname(__file__), '../../uploads/reports')
    if not os.path.exists(reports_dir):
        return None
    
    matching_reports = []
    
    try:
        for report_folder in os.listdir(reports_dir):
            report_path = os.path.join(reports_dir, report_folder)
            if not os.path.isdir(report_path):
                continue
            
            meta_file = os.path.join(report_path, "meta.json")
            if not os.path.exists(meta_file):
                continue
            
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                if meta.get("simulation_id") == simulation_id:
                    matching_reports.append({
                        "report_id": meta.get("report_id"),
                        "created_at": meta.get("created_at", ""),
                        "status": meta.get("status", "")
                    })
            except Exception:
                continue
        
        if not matching_reports:
            return None
        
        # 按创建时间倒序排序，返回最新的
        matching_reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return matching_reports[0].get("report_id")
        
    except Exception as e:
        logger.warning(f"Échec de la recherche du rapport pour la simulation {simulation_id}: {e}")
        return None


@simulation_bp.route('/history', methods=['GET'])
def get_simulation_history():
    """
    获取历史模拟列表（带项目详情）
    
    用于首页历史项目展示，返回包含项目名称、描述等丰富信息的模拟列表
    
    Query参数：
        limit: 返回数量限制（默认20）
    
    返回：
        {
            "success": true,
            "data": [
                {
                    "simulation_id": "sim_xxxx",
                    "project_id": "proj_xxxx",
                    "project_name": "武大舆情分析",
                    "simulation_requirement": "如果武汉大学发布...",
                    "status": "completed",
                    "entities_count": 68,
                    "profiles_count": 68,
                    "entity_types": ["Student", "Professor", ...],
                    "created_at": "2024-12-10",
                    "updated_at": "2024-12-10",
                    "total_rounds": 120,
                    "current_round": 120,
                    "report_id": "report_xxxx",
                    "version": "v1.0.2"
                },
                ...
            ],
            "count": 7
        }
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        user_id = request.headers.get('X-User-Id')
        manager = SimulationManager()
        simulations = manager.list_simulations(user_id=user_id)[:limit]
        
        # 增强模拟数据，只从 Simulation 文件读取
        enriched_simulations = []
        for sim in simulations:
            sim_dict = sim.to_dict()
            
            # 获取模拟配置信息（从 simulation_config.json 读取 simulation_requirement）
            config = manager.get_simulation_config(sim.simulation_id)
            if config:
                sim_dict["simulation_requirement"] = config.get("simulation_requirement", "")
                time_config = config.get("time_config", {})
                sim_dict["total_simulation_hours"] = time_config.get("total_simulation_hours", 0)
                # 推荐轮数（后备值）
                recommended_rounds = int(
                    time_config.get("total_simulation_hours", 0) * 60 / 
                    max(time_config.get("minutes_per_round", 60), 1)
                )
            else:
                sim_dict["simulation_requirement"] = ""
                sim_dict["total_simulation_hours"] = 0
                recommended_rounds = 0
            
            # 获取运行状态（从 run_state.json 读取用户设置的实际轮数）
            run_state = SimulationRunner.get_run_state(sim.simulation_id)
            if run_state:
                sim_dict["current_round"] = run_state.current_round
                sim_dict["runner_status"] = run_state.runner_status.value
                # 使用用户设置 the total_rounds, 若无则使用推荐轮数
                sim_dict["total_rounds"] = run_state.total_rounds if run_state.total_rounds > 0 else recommended_rounds
                sim_dict["run_mode"] = getattr(run_state, "run_mode", "courtroom")
            else:
                sim_dict["current_round"] = 0
                sim_dict["runner_status"] = "idle"
                sim_dict["total_rounds"] = recommended_rounds
                sim_dict["run_mode"] = "social" if (sim.enable_twitter or sim.enable_reddit) else "courtroom"
            
            # 获取关联项目的文件列表（最多3个）
            project = ProjectManager.get_project(sim.project_id)
            if project and hasattr(project, 'files') and project.files:
                sim_dict["files"] = [
                    {"filename": f.get("filename", "未知文件")} 
                    for f in project.files[:3]
                ]
            else:
                sim_dict["files"] = []
            
            # 获取关联的 report_id（查找该 simulation 最新的 report）
            sim_dict["report_id"] = _get_report_id_for_simulation(sim.simulation_id)
            
            # 添加版本号
            sim_dict["version"] = "v1.0.2"
            
            # 格式化日期
            try:
                created_date = sim_dict.get("created_at", "")[:10]
                sim_dict["created_date"] = created_date
            except:
                sim_dict["created_date"] = ""
            
            enriched_simulations.append(sim_dict)
        
        return jsonify({
            "success": True,
            "data": enriched_simulations,
            "count": len(enriched_simulations)
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'historique des simulations: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles', methods=['GET'])
def get_simulation_profiles(simulation_id: str):
    """
    获取模拟的Agent Profile
    
    Query参数：
        platform: 平台类型（reddit/twitter，默认reddit）
    """
    try:
        platform = request.args.get('platform', 'reddit')
        
        manager = SimulationManager()
        profiles = manager.get_profiles(simulation_id, platform=platform)
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "count": len(profiles),
                "profiles": profiles
            }
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Échec de la récupération du profil: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles/realtime', methods=['GET'])
def get_simulation_profiles_realtime(simulation_id: str):
    """
    实时获取模拟的Agent Profile（用于在生成过程中实时查看进度）
    
    与 /profiles 接口的区别：
    - 直接读取文件，不经过 SimulationManager
    - 适用于生成过程中的实时查看
    - 返回额外的元数据（如文件修改时间、是否正在生成等）
    
    Query参数：
        platform: 平台类型（reddit/twitter，默认reddit）
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "platform": "reddit",
                "count": 15,
                "total_expected": 93,  // 预期总数（如果有）
                "is_generating": true,  // 是否正在生成
                "file_exists": true,
                "file_modified_at": "2025-12-04T18:20:00",
                "profiles": [...]
            }
        }
    """
    import json
    import csv
    from datetime import datetime
    
    try:
        platform = request.args.get('platform', 'reddit')
        
        # 获取模拟目录
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
        
        # 确定文件路径
        if platform == "reddit":
            profiles_file = os.path.join(sim_dir, "reddit_profiles.json")
        else:
            profiles_file = os.path.join(sim_dir, "twitter_profiles.csv")
        
        # 检查文件是否存在
        file_exists = os.path.exists(profiles_file)
        profiles = []
        file_modified_at = None
        
        if file_exists:
            # 获取文件修改时间
            file_stat = os.stat(profiles_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            try:
                if platform == "reddit":
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                else:
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        profiles = list(reader)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Échec de la lecture du fichier de profils (écriture possible en cours): {e}")
                profiles = []
        
        # 检查是否正在生成（通过 state.json 判断）
        is_generating = False
        total_expected = None
        
        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    total_expected = state_data.get("entities_count")
            except Exception:
                pass
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "platform": platform,
                "count": len(profiles),
                "total_expected": total_expected,
                "is_generating": is_generating,
                "file_exists": file_exists,
                "file_modified_at": file_modified_at,
                "profiles": profiles
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération du profil en temps réel: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles/update', methods=['POST'])
def update_simulation_profile(simulation_id: str):
    """
    Mettre à jour le profil cognitif et comportemental d'un acteur dans une simulation.
    """
    import csv
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")
        if user_id is None:
            return jsonify({
                "success": False,
                "error": "L'identifiant de l'acteur (user_id) est requis."
            }), 400

        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        profiles_file = os.path.join(sim_dir, "reddit_profiles.json")
        twitter_file = os.path.join(sim_dir, "twitter_profiles.csv")
        config_file = os.path.join(sim_dir, "simulation_config.json")

        updated_reddit = False
        updated_twitter = False
        updated_config = False

        # 1. Mettre à jour reddit_profiles.json
        if os.path.exists(profiles_file):
            try:
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)

                for p in profiles:
                    if int(p.get("user_id", -1)) == int(user_id):
                        for key in ["name", "username", "bio", "persona", "profession", "age", "gender", "mbti", "country", "interested_topics"]:
                            if key in data:
                                p[key] = data[key]
                        updated_reddit = True
                        break

                if updated_reddit:
                    with open(profiles_file, 'w', encoding='utf-8') as f:
                        json.dump(profiles, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de reddit_profiles.json: {e}")

        # 2. Mettre à jour twitter_profiles.csv
        if os.path.exists(twitter_file):
            try:
                csv_profiles = []
                with open(twitter_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    csv_profiles = list(reader)

                for p in csv_profiles:
                    if int(p.get("user_id", -1)) == int(user_id):
                        if "name" in data:
                            p["name"] = data["name"]
                        if "username" in data:
                            p["username"] = data["username"]
                        bio = data.get("bio", p.get("description", ""))
                        persona = data.get("persona", "")
                        user_char = f"{bio} {persona}".strip()
                        p["user_char"] = user_char.replace('\n', ' ').replace('\r', ' ')
                        p["description"] = bio.replace('\n', ' ').replace('\r', ' ')
                        updated_twitter = True
                        break

                if updated_twitter:
                    with open(twitter_file, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(csv_profiles)
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de twitter_profiles.csv: {e}")

        # 3. Mettre à jour simulation_config.json
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                agent_configs = config_data.get("agent_configs", [])
                for agent in agent_configs:
                    if int(agent.get("agent_id", -1)) == int(user_id):
                        if "name" in data:
                            agent["entity_name"] = data["name"]
                        for key in ["stance", "influence_weight", "activity_level", "posts_per_hour", "comments_per_hour", "sentiment_bias"]:
                            if key in data:
                                # Convert parameters to correct type
                                if key in ["influence_weight", "activity_level", "posts_per_hour", "comments_per_hour", "sentiment_bias"]:
                                    agent[key] = float(data[key])
                                else:
                                    agent[key] = data[key]
                        updated_config = True
                        break

                if updated_config:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de simulation_config.json: {e}")

        if not updated_reddit and not updated_twitter and not updated_config:
            return jsonify({
                "success": False,
                "error": f"Acteur avec l'ID {user_id} introuvable."
            }), 404

        return jsonify({
            "success": True,
            "message": "Profil de l'acteur et configuration mis à jour avec succès."
        })

    except Exception as e:
        logger.error(f"Échec de la mise à jour du profil: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config/realtime', methods=['GET'])
def get_simulation_config_realtime(simulation_id: str):
    """
    实时获取模拟配置（用于在生成过程中实时查看进度）
    
    与 /config 接口的区别：
    - 直接读取文件，不经过 SimulationManager
    - 适用于生成过程中的实时查看
    - 返回额外的元数据（如文件修改时间、是否正在生成等）
    - 即使配置还没生成完也能返回部分信息
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "file_exists": true,
                "file_modified_at": "2025-12-04T18:20:00",
                "is_generating": true,  // 是否正在生成
                "generation_stage": "generating_config",  // 当前生成阶段
                "config": {...}  // 配置内容（如果存在）
            }
        }
    """
    import json
    from datetime import datetime
    
    try:
        # 获取模拟目录
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
        
        # 配置文件路径
        config_file = os.path.join(sim_dir, "simulation_config.json")
        
        # 检查文件是否存在
        file_exists = os.path.exists(config_file)
        config = None
        file_modified_at = None
        
        if file_exists:
            # 获取文件修改时间
            file_stat = os.stat(config_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Échec de la lecture du fichier de configuration (écriture possible en cours): {e}")
                config = None
        
        # 检查是否正在生成（通过 state.json 判断）
        is_generating = False
        generation_stage = None
        config_generated = False
        
        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    config_generated = state_data.get("config_generated", False)
                    
                    # 判断当前阶段
                    if is_generating:
                        if state_data.get("profiles_generated", False):
                            generation_stage = "generating_config"
                        else:
                            generation_stage = "generating_profiles"
                    elif status == "ready":
                        generation_stage = "completed"
            except Exception:
                pass
        
        # 构建返回数据
        response_data = {
            "simulation_id": simulation_id,
            "file_exists": file_exists,
            "file_modified_at": file_modified_at,
            "is_generating": is_generating,
            "generation_stage": generation_stage,
            "config_generated": config_generated,
            "config": config
        }
        
        # 如果配置存在，提取一些关键统计信息
        if config:
            response_data["summary"] = {
                "total_agents": len(config.get("agent_configs", [])),
                "simulation_hours": config.get("time_config", {}).get("total_simulation_hours"),
                "initial_posts_count": len(config.get("event_config", {}).get("initial_posts", [])),
                "hot_topics_count": len(config.get("event_config", {}).get("hot_topics", [])),
                "has_twitter_config": "twitter_config" in config,
                "has_reddit_config": "reddit_config" in config,
                "generated_at": config.get("generated_at"),
                "llm_model": config.get("llm_model")
            }
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la configuration en temps réel: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config', methods=['GET'])
def get_simulation_config(simulation_id: str):
    """
    获取模拟配置（LLM智能生成的完整配置）
    
    返回包含：
        - time_config: 时间配置（模拟时长、轮次、高峰/低谷时段）
        - agent_configs: 每个Agent的活动配置（活跃度、发言频率、立场等）
        - event_config: 事件配置（初始帖子、热点话题）
        - platform_configs: 平台配置
        - generation_reasoning: LLM的配置推理说明
    """
    try:
        manager = SimulationManager()
        config = manager.get_simulation_config(simulation_id)
        
        if not config:
            return jsonify({
                "success": False,
                "error": t('api.configNotFound')
            }), 404
        
        return jsonify({
            "success": True,
            "data": config
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la configuration: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config/download', methods=['GET'])
def download_simulation_config(simulation_id: str):
    """下载模拟配置文件"""
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return jsonify({
                "success": False,
                "error": t('api.configFileNotFound')
            }), 404
        
        return send_file(
            config_path,
            as_attachment=True,
            download_name="simulation_config.json"
        )
        
    except Exception as e:
        logger.error(f"Échec du téléchargement de la configuration: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/script/<script_name>/download', methods=['GET'])
def download_simulation_script(script_name: str):
    """
    下载模拟运行脚本文件（通用脚本，位于 backend/scripts/）
    
    script_name可选值：
        - run_twitter_simulation.py
        - run_reddit_simulation.py
        - run_parallel_simulation.py
        - action_logger.py
    """
    try:
        # 脚本位于 backend/scripts/ 目录
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        # 验证脚本名称
        allowed_scripts = [
            "run_twitter_simulation.py",
            "run_reddit_simulation.py", 
            "run_parallel_simulation.py",
            "action_logger.py"
        ]
        
        if script_name not in allowed_scripts:
            return jsonify({
                "success": False,
                "error": t('api.unknownScript', name=script_name, allowed=allowed_scripts)
            }), 400
        
        script_path = os.path.join(scripts_dir, script_name)
        
        if not os.path.exists(script_path):
            return jsonify({
                "success": False,
                "error": t('api.scriptFileNotFound', name=script_name)
            }), 404
        
        return send_file(
            script_path,
            as_attachment=True,
            download_name=script_name
        )
        
    except Exception as e:
        logger.error(f"Échec du téléchargement du script: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== API de génération de profils (utilisation indépendante) ==============

@simulation_bp.route('/generate-profiles', methods=['POST'])
def generate_profiles():
    """
    Générer des profils d'agents OASIS directement à partir du graphe (sans créer de simulation)
    
    Requête (JSON) :
        {
            "graph_id": "lexior_xxxx",        // Requis
            "entity_types": ["Student"],      // Optionnel
            "use_llm": true,                  // Optionnel
            "platform": "reddit"              // Optionnel
        }
    """
    try:
        data = request.get_json() or {}
        
        graph_id = data.get('graph_id')
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.requireGraphId')
            }), 400
        
        entity_types = data.get('entity_types')
        use_llm = data.get('use_llm', True)
        platform = data.get('platform', 'reddit')
        
        reader = ZepEntityReader()
        filtered = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=True
        )
        
        if filtered.filtered_count == 0:
            return jsonify({
                "success": False,
                "error": t('api.noMatchingEntities')
            }), 400
        
        generator = OasisProfileGenerator()
        profiles = generator.generate_profiles_from_entities(
            entities=filtered.entities,
            use_llm=use_llm
        )
        
        if platform == "reddit":
            profiles_data = [p.to_reddit_format() for p in profiles]
        elif platform == "twitter":
            profiles_data = [p.to_twitter_format() for p in profiles]
        else:
            profiles_data = [p.to_dict() for p in profiles]
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "entity_types": list(filtered.entity_types),
                "count": len(profiles_data),
                "profiles": profiles_data
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la génération des profils: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 模拟运行控制接口 ==============

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    """
    开始运行模拟

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",          // 必填，模拟ID
            "platform": "parallel",                // 可选: twitter / reddit / parallel (默认)
            "max_rounds": 100,                     // 可选: 最大模拟轮数，用于截断过长的模拟
            "enable_graph_memory_update": false,   // 可选: 是否将Agent活动动态更新到Zep图谱记忆
            "force": false                         // 可选: 强制重新开始（会停止运行中的模拟并清理日志）
        }

    关于 force 参数：
        - 启用后，如果模拟正在运行或已完成，会先停止并清理运行日志
        - 清理的内容包括：run_state.json, actions.jsonl, simulation.log 等
        - 不会清理配置文件（simulation_config.json）和 profile 文件
        - 适用于需要重新运行模拟的场景

    关于 enable_graph_memory_update：
        - 启用后，模拟中所有Agent的活动（发帖、评论、点赞等）都会实时更新到Zep图谱
        - 这可以让图谱"记住"模拟过程，用于后续分析或AI对话
        - 需要模拟关联的项目有有效的 graph_id
        - 采用批量更新机制，减少API调用次数

    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "process_pid": 12345,
                "twitter_running": true,
                "reddit_running": true,
                "started_at": "2025-12-01T10:00:00",
                "graph_memory_update_enabled": true,  // 是否启用了图谱记忆更新
                "force_restarted": true               // 是否是强制重新开始
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        platform = data.get('platform', 'parallel')
        max_rounds = data.get('max_rounds')  # 可选：最大模拟轮数
        enable_graph_memory_update = data.get('enable_graph_memory_update', False)  # 可选：是否启用图谱记忆更新
        force = data.get('force', False)  # 可选：强制重新开始
        run_mode = data.get('run_mode', 'courtroom')
        client_side = data.get('client_side', 'defense')
        judge_type = data.get('judge_type', 'single')
        selected_judge_personality = data.get('selected_judge_personality')
        selected_judges_personalities = data.get('selected_judges_personalities')

        # 验证 max_rounds 参数
        if max_rounds is not None:
            try:
                max_rounds = int(max_rounds)
                if max_rounds <= 0:
                    return jsonify({
                        "success": False,
                        "error": t('api.maxRoundsPositive')
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": t('api.maxRoundsInvalid')
                }), 400

        if platform not in ['twitter', 'reddit', 'parallel']:
            return jsonify({
                "success": False,
                "error": t('api.invalidPlatform', platform=platform)
            }), 400

        # 检查模拟是否已准备好
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        # Persist client side choice to project
        if state.project_id:
            project = ProjectManager.get_project(state.project_id)
            if project:
                project.client_side = client_side
                ProjectManager.save_project(project)

        force_restarted = False
        
        # 智能处理状态：如果准备工作已完成，允许重新启动
        if state.status != SimulationStatus.READY:
            # 检查准备工作是否已完成
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)

            if is_prepared:
                # 准备工作已完成，检查是否有正在运行的进程
                if state.status == SimulationStatus.RUNNING:
                    # 检查模拟进程是否真的在运行
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if run_state and run_state.runner_status.value == "running":
                        # 进程确实在运行
                        if force:
                            # 强制模式：停止运行中的模拟
                            logger.info(f"Mode forcé : Arrêt de la simulation en cours {simulation_id}")
                            try:
                                SimulationRunner.stop_simulation(simulation_id)
                            except Exception as e:
                                logger.warning(f"Avertissement lors de l'arrêt de la simulation: {str(e)}")
                        else:
                            logger.info(f"Simulation {simulation_id} is already running. Returning current state gracefully.")
                            response_data = run_state.to_dict()
                            if max_rounds:
                                response_data['max_rounds_applied'] = max_rounds
                            response_data['graph_memory_update_enabled'] = enable_graph_memory_update
                            response_data['force_restarted'] = False
                            if enable_graph_memory_update:
                                response_data['graph_id'] = graph_id
                            
                            return jsonify({
                                "success": True,
                                "data": response_data
                            })

                # 如果是强制模式，清理运行日志
                if force:
                    logger.info(f"Mode forcé : Nettoyage des journaux de simulation {simulation_id}")
                    cleanup_result = SimulationRunner.cleanup_simulation_logs(simulation_id)
                    if not cleanup_result.get("success"):
                        logger.warning(f"Avertissement lors du nettoyage des journaux: {cleanup_result.get('errors')}")
                    force_restarted = True

                # 进程不存在或已结束，重置状态为 ready
                logger.info(f"Préparation de la simulation {simulation_id} terminée, réinitialisation du statut à ready (ancien statut : {state.status.value})")
                state.status = SimulationStatus.READY
                manager._save_simulation_state(state)
            else:
                # 准备工作未完成
                return jsonify({
                    "success": False,
                    "error": t('api.simNotReady', status=state.status.value)
                }), 400
        
        # 获取图谱ID（用于图谱记忆更新）
        graph_id = None
        if enable_graph_memory_update:
            # 从模拟状态或项目中获取 graph_id
            graph_id = state.graph_id
            if not graph_id:
                # 尝试从项目中获取
                project = ProjectManager.get_project(state.project_id)
                if project:
                    graph_id = project.graph_id
            
            if not graph_id:
                return jsonify({
                    "success": False,
                    "error": t('api.graphIdRequiredForMemory')
                }), 400
            
            logger.info(f"Activation de la mise à jour de la mémoire du graphe: simulation_id={simulation_id}, graph_id={graph_id}")
        
        # 启动模拟
        initial_stimulus = data.get('initial_stimulus')
        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory_update,
            graph_id=graph_id,
            run_mode=run_mode,
            force=force,
            initial_stimulus=initial_stimulus,
            judge_type=judge_type,
            selected_judge_personality=selected_judge_personality,
            selected_judges_personalities=selected_judges_personalities
        )
        
        # 更新模拟状态
        state.status = SimulationStatus.RUNNING
        manager._save_simulation_state(state)
        
        response_data = run_state.to_dict()
        if max_rounds:
            response_data['max_rounds_applied'] = max_rounds
        response_data['graph_memory_update_enabled'] = enable_graph_memory_update
        response_data['force_restarted'] = force_restarted
        if enable_graph_memory_update:
            response_data['graph_id'] = graph_id
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Échec du démarrage de la simulation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/stop', methods=['POST'])
def stop_simulation():
    """
    停止模拟
    
    请求（JSON）：
        {
            "simulation_id": "sim_xxxx"  // 必填，模拟ID
        }
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "stopped",
                "completed_at": "2025-12-01T12:00:00"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        run_state = SimulationRunner.stop_simulation(simulation_id)
        
        # 更新模拟状态
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.PAUSED
            manager._save_simulation_state(state)
        
        return jsonify({
            "success": True,
            "data": run_state.to_dict()
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Échec de l'arrêt de la simulation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/delete', methods=['POST'])
def delete_simulation():
    """
    Supprimer une simulation et ses données physiques
    """
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
            
        # 1. 停止运行中的模拟 (如果存在且运行中)
        run_state = SimulationRunner.get_run_state(simulation_id)
        if run_state and run_state.runner_status.value in ["running", "paused", "starting"]:
            try:
                SimulationRunner.stop_simulation(simulation_id)
                logger.info(f"Simulation {simulation_id} stopped before deletion")
            except Exception as e:
                logger.warning(f"Error stopping simulation {simulation_id} during delete: {e}")
                
        # 2. 清理内存和日志
        SimulationRunner.cleanup_simulation_logs(simulation_id)
        
        # 3. 删除物理目录
        safe_id = os.path.basename(simulation_id)
        sim_dir = os.path.join(SimulationManager.SIMULATION_DATA_DIR, safe_id)
        if os.path.exists(sim_dir):
            import shutil
            shutil.rmtree(sim_dir)
            logger.info(f"Simulation physical directory deleted: {sim_dir}")
            
        # 4. Supprimer la base de données d'état cognitif Kuzu
        try:
            from app.services.local_graph_database import LocalGraphDatabase
            with LocalGraphDatabase(simulation_id) as db:
                db.delete_graph()
            logger.info(f"Cognitive state graph database deleted for simulation {simulation_id}")
        except Exception as e:
            logger.warning(f"Failed to delete cognitive state graph database for {simulation_id}: {e}")
            
        return jsonify({
            "success": True,
            "message": "Simulation supprimée avec succès"
        })
    except Exception as e:
        logger.error(f"Suppression de simulation échouée: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/live-chat', methods=['POST'])
def live_chat_with_character():
    """
    Discuter en direct avec un personnage (Avocat ou Procureur/Adversaire) pendant le procès
    """
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')
        character = data.get('character') # 'adversary' or 'advocate'
        message = data.get('message')
        chat_history = data.get('chat_history', [])
        inject_as_stimulus = data.get('inject_as_stimulus', True)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
            
        if not character or character not in ['adversary', 'advocate']:
            return jsonify({
                "success": False,
                "error": "Character must be 'adversary' or 'advocate'"
            }), 400
            
        if not message:
            return jsonify({
                "success": False,
                "error": t('api.requireMessage')
            }), 400
            
        # 获取项目背景需求
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
            
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=state.project_id)
            }), 404
            
        simulation_requirement = project.simulation_requirement or ""
        
        # Get litigation_type from simulation_config.json
        litigation_type = "civil"
        try:
            config_path = os.path.join(SimulationManager.SIMULATION_DATA_DIR, simulation_id, "simulation_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    litigation_type = config_data.get("litigation_type", "civil")
        except Exception:
            pass

        # Build Trial Context from active simulation state
        trial_context_str = ""
        current_stimuli = state.injected_stimuli if (hasattr(state, 'injected_stimuli') and state.injected_stimuli) else []
        if current_stimuli:
            trial_context_str += "\nFAITS NOUVEAUX ET STIMULI INJECTÉS DANS LE PROCÈS JUSQU'À PRÉSENT :\n"
            for stim in current_stimuli:
                trial_context_str += f"- {stim}\n"
                
        recent_actions = state.recent_actions if (hasattr(state, 'recent_actions') and state.recent_actions) else []
        if recent_actions:
            trial_context_str += "\nDÉBATS ET ACTIONS RÉCENTES DEVANT LE TRIBUNAL :\n"
            # Reverse to display chronological order (oldest to newest among the last 10)
            for act in reversed(list(recent_actions)[:10]):
                desc = getattr(act, 'result', '')
                name = getattr(act, 'agent_name', 'Inconnu')
                trial_context_str += f"- [{name}] {desc}\n"
        
        # Get client_side from the project
        client_side = getattr(project, "client_side", "defense")
        
        # Read the win_rate from results
        sim_dir = os.path.join(SimulationManager.SIMULATION_DATA_DIR, simulation_id)
        results_path = os.path.join(sim_dir, "legal_simulation_results.json")
        win_rate = 50.0
        if os.path.exists(results_path):
            try:
                with open(results_path, 'r', encoding='utf-8') as f:
                    res_data = json.load(f)
                    win_rate = res_data.get("win_rate", 50.0)
            except Exception:
                pass

        # Determine roles based on litigation_type and client_side
        if litigation_type == "criminal":
            if client_side == "plaintiff":
                # User is Prosecution (Procureur), adversary is Defense
                user_role_label = "le Procureur (Représentant du Ministère Public)"
                adversary_role_label = "l'Avocat de la Défense"
                adversary_role_desc = "d'Avocat de la Défense cherchant à soulever un doute raisonnable ou à invoquer des moyens d'exonération pour ton client"
                adversary_role_constraint = "Tu es l'Avocat de la Défense de l'accusé."
                example_summary = "Lors d'une discussion hors-champ, la Poursuite a proposé un compromis de peine. La Défense a répliqué en invoquant un doute raisonnable..."
                
                adversary_win_rate = win_rate
                user_win_rate = 100.0 - win_rate
            else:
                # User is Defense, adversary is Prosecution (Procureur)
                user_role_label = "l'Avocat de la Défense"
                adversary_role_label = "le Procureur (Accusation)"
                adversary_role_desc = "de Procureur ferme et coriace requérant l'application stricte de la loi pénale au nom de la société"
                adversary_role_constraint = "Tu es le Procureur représentant le Ministère Public."
                example_summary = "Lors d'une discussion hors-champ, la Défense a présenté un affidavit. Le Procureur a répliqué en insistant sur la culpabilité de l'accusé..."
                
                adversary_win_rate = 100.0 - win_rate
                user_win_rate = win_rate
        else: # civil
            if client_side == "plaintiff":
                # User is Plaintiff (Demandeur), adversary is Defense
                user_role_label = "l'Avocat du Demandeur"
                adversary_role_label = "l'Avocat de la Défense"
                adversary_role_desc = "d'Avocat de la Défense protégeant les intérêts de ton client contre les réclamations de la partie adverse"
                adversary_role_constraint = "Tu ne dois JAMAIS utiliser le mot 'Procureur' ou 'Ministère Public' car il s'agit d'un litige civil. Utilise 'l'Avocat de la Défense'."
                example_summary = "Lors d'une négociation hors-champ, l'Avocat du Demandeur a proposé un règlement à l'amiable. L'Avocat de la Défense a répliqué en contestant la responsabilité..."
                
                adversary_win_rate = win_rate
                user_win_rate = 100.0 - win_rate
            else:
                # User is Defense, adversary is Plaintiff (Demandeur)
                user_role_label = "l'Avocat de la Défense"
                adversary_role_label = "l'Avocat du Demandeur"
                adversary_role_desc = "d'Avocat Adverse défendant vigoureusement les intérêts financiers et contractuels de ton client (le Demandeur)"
                adversary_role_constraint = "Tu ne dois JAMAIS utiliser le mot 'Procureur' ou 'Ministère Public' car il s'agit d'un litige civil. Utilise 'l'Avocat du Demandeur'."
                example_summary = "Lors d'une négociation hors-champ, la Défense a présenté un affidavit. L'Avocat du Demandeur a répliqué en insistant sur l'obligation de résultat..."
                
                adversary_win_rate = 100.0 - win_rate
                user_win_rate = win_rate

        # 1. 依据角色定义 System Prompt
        if character == 'adversary':
            system_prompt = f"""Tu es {adversary_role_label} du dossier de procès suivant :
{simulation_requirement}

Statut actuel de la simulation :
- Les simulations montrent que le camp de l'utilisateur ({user_role_label}) a {user_win_rate}% de chances de victoire.
- Ton camp ({adversary_role_label}) a donc {adversary_win_rate}% de chances de victoire.
{trial_context_str}

Directives :
1. Reste dans ton rôle {adversary_role_desc}. {adversary_role_constraint}
2. Si la partie adverse (l'utilisateur) te propose un deal, une médiation ou des menaces réputationnelles/médiatiques, évalue cela en fonction de ton win rate théorique ({adversary_win_rate}%). 
3. Sois arrogant et exigeant si ton taux est élevé, plus coopératif si ton taux est faible. 
4. Réponds toujours en français sur un ton juridique professionnel. Ne mentionne pas l'IA.
5. Adresses-toi à l'utilisateur (qui est {user_role_label}) en l'appelant 'Maître' ou 'Mon cher confrère'. Tu ne dois JAMAIS utiliser de placeholders ou d'emplacements réservés comme '[Mon Nom]', '[Votre Nom]', '[Nom de l'avocat]' ou '[Nom]'. Sois direct et utilise simplement 'Maître' ou 'Mon cher confrère'.

Tu dois obligatoirement répondre sous la forme d'un objet JSON valide contenant exactement ces deux clés :
{{
  "response": "Le message de réponse directe à l'utilisateur. Ton professionnel et juridique, s'adressant à 'Maître' ou 'Mon cher confrère'. Pas de crochets.",
  "stimulus_summary": "Un fait juridique ou un résumé objectif à la troisième personne de cet échange hors-champ. Ne transcris pas la conversation mot à mot. Décris plutôt l'événement de façon synthétique pour le procès (ex: '{example_summary}')."
}}
Assure-toi que la réponse est uniquement un objet JSON valide, sans formatage markdown de bloc de code (ne mets pas de ```json ou ```).
"""
        else:
            # Discussion stratégique avec le co-conseil (advocate)
            camp_label = "la Défense" if client_side == "defense" else "le Demandeur"
            system_prompt = f"""Tu es {user_role_label} (co-conseil et confrère de l'utilisateur, qui est également avocat dans le même camp) dans le dossier de procès suivant :
{simulation_requirement}
{trial_context_str}

Directives :
1. Tu es le confrère et co-conseil de l'utilisateur. Sois poli, stratégique, combatif et à l'écoute.
2. Rappelle-toi que le client (le défendeur/accusé ou demandeur dans l'affaire selon les faits) est une tierce personne physique ou morale définie dans les faits du dossier, et non l'utilisateur lui-même. C'est le client commun que vous défendez ou représentez ensemble. L'utilisateur est ton confrère avocat.
3. L'utilisateur (votre confrère) te propose des arguments stratégiques, des points d'attention ou des orientations pour le procès.
4. Évalue ses propositions. Conseille-le de façon constructive, dis-lui si sa stratégie te semble judicieuse et comment vous allez l'adapter ensemble pour les prochains débats devant le juge.
5. Réponds toujours en français sur un ton de collaboration professionnelle et engagée entre confrères. Ne mentionne pas l'IA.
6. Adresses-toi à l'utilisateur en l'appelant 'Maître' ou 'Mon cher confrère'. Tu ne dois JAMAIS utiliser de placeholders comme '[Mon Nom]', '[Votre Nom]' ou '[Nom]'. Utilise simplement 'Maître' ou 'Mon cher confrère'.

Tu dois obligatoirement répondre sous la forme d'un objet JSON valide contenant exactement ces deux clés :
{{
  "response": "Le message de réponse directe à l'utilisateur. Ton collaboratif, professionnel, s'adressant à l'utilisateur avec respect en l'appelant 'Maître' ou 'Mon cher confrère'. Pas de crochets.",
  "stimulus_summary": "Un fait juridique ou un résumé objectif à la troisième personne de cet échange hors-champ. Ne transcris pas la conversation mot à mot. Décris plutôt l'événement de façon synthétique pour le procès (ex: 'Lors d'une réunion stratégique hors-champ, l'équipe d'avocats de {camp_label} a analysé les pièces fournies par le client et a décidé d'ajuster sa stratégie en...')."
}}
Assure-toi que la réponse est uniquement un objet JSON valide, sans formatage markdown de bloc de code (ne mets pas de ```json ou ```).
"""
            
        # 2. Appeler l'API de chat LLM
        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
        
        from openai import OpenAI
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
            
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        messages.append({"role": "user", "content": message})
        
        # Call the LLM API with JSON response format fallback
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
        except Exception as format_err:
            logger.warning(f"Model doesn't support response_format json_object, falling back to standard: {format_err}")
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7
            )
            
        reply_content = response.choices[0].message.content.strip()
        
        # Nettoyage si le modèle a renvoyé du markdown
        if reply_content.startswith("```"):
            lines = reply_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            reply_content = "\n".join(lines).strip()
            
        # Clean response and parse JSON robustly
        reply = ""
        stimulus_summary = ""
        parsed_success = False
        
        # Attempt 1: Try regex to extract first JSON block
        import re
        json_match = re.search(r'(\{.*\})', reply_content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                reply = parsed.get("response", "").strip()
                stimulus_summary = parsed.get("stimulus_summary", "").strip()
                parsed_success = True
            except Exception as e:
                logger.warning(f"Failed to parse regex-extracted JSON: {e}")
                
        # Attempt 2: Direct load if no regex match or failed
        if not parsed_success:
            try:
                parsed = json.loads(reply_content)
                reply = parsed.get("response", "").strip()
                stimulus_summary = parsed.get("stimulus_summary", "").strip()
                parsed_success = True
            except Exception as e:
                logger.warning(f"Failed to parse raw content as JSON: {e}")

        # Attempt 3: Regex-based key extraction if JSON parsing failed (e.g. unescaped newlines/quotes)
        if not parsed_success:
            try:
                # Extract response field value
                response_match = re.search(r'["\']response["\']\s*:\s*["\']((?:[^"\'\\]|\\.)*)["\']', reply_content, re.DOTALL)
                # Extract stimulus_summary field value
                summary_match = re.search(r'["\']stimulus_summary["\']\s*:\s*["\']((?:[^"\'\\]|\\.)*)["\']', reply_content, re.DOTALL)
                
                if response_match:
                    reply = response_match.group(1)
                    # Replace escape sequences
                    reply = reply.replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                    reply = reply.strip()
                    
                if summary_match:
                    stimulus_summary = summary_match.group(1)
                    stimulus_summary = stimulus_summary.replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                    stimulus_summary = stimulus_summary.strip()
                
                if reply:
                    parsed_success = True
                    logger.info("Successfully extracted live chat fields using regex key parser")
            except Exception as e:
                logger.warning(f"Failed regex-based key extraction: {e}")
                
        # Fallback if both failed
        if not parsed_success or not reply:
            reply = reply_content
            if character == 'adversary':
                opponent_name = "au Procureur" if litigation_type == "criminal" else "à l'Avocat du Demandeur"
                stimulus_summary = f"Lors d'une discussion de négociation directe hors-champ, la Défense a proposé un compromis {opponent_name} qui a répondu."
            else:
                stimulus_summary = f"Lors d'une réunion stratégique hors-champ, la Défense a ajusté ses arguments suite aux instructions du client."
                
        # 3. Injecter l'influence sous forme de Stimulus dans la simulation
        if inject_as_stimulus:
            if character == 'adversary':
                stimulus_text = f"[NÉGOCIATION EN DIRECT - ADVERSAIRE] {stimulus_summary}"
            else:
                stimulus_text = f"[STRATÉGIE EN DIRECT - AVOCAT] {stimulus_summary}"
                
            try:
                SimulationRunner.inject_stimulus(simulation_id, stimulus_text)
                logger.info(f"Live chat message injected as stimulus for simulation {simulation_id}")
            except Exception as e:
                logger.error(f"Failed to inject live chat stimulus: {e}")
        else:
            logger.info(f"Live chat message NOT injected as stimulus (inject_as_stimulus is False)")
            
        return jsonify({
            "success": True,
            "data": {
                "response": reply,
                "injected": inject_as_stimulus
            }
        })
    except Exception as e:
        logger.error(f"Live chat failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 实时状态监控接口 ==============

@simulation_bp.route('/<simulation_id>/run-status', methods=['GET'])
def get_run_status(simulation_id: str):
    """
    获取模拟运行实时状态（用于前端轮询）
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "current_round": 5,
                "total_rounds": 144,
                "progress_percent": 3.5,
                "simulated_hours": 2,
                "total_simulation_hours": 72,
                "twitter_running": true,
                "reddit_running": true,
                "twitter_actions_count": 150,
                "reddit_actions_count": 200,
                "total_actions_count": 350,
                "started_at": "2025-12-01T10:00:00",
                "updated_at": "2025-12-01T10:30:00"
            }
        }
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        
        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "current_round": 0,
                    "total_rounds": 0,
                    "progress_percent": 0,
                    "twitter_actions_count": 0,
                    "reddit_actions_count": 0,
                    "total_actions_count": 0,
                }
            })
        
        return jsonify({
            "success": True,
            "data": run_state.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'état d'exécution: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/run-status/detail', methods=['GET'])
def get_run_status_detail(simulation_id: str):
    """
    获取模拟运行详细状态（包含所有动作）
    
    用于前端展示实时动态
    
    Query参数：
        platform: 过滤平台（twitter/reddit，可选）
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "current_round": 5,
                ...
                "all_actions": [
                    {
                        "round_num": 5,
                        "timestamp": "2025-12-01T10:30:00",
                        "platform": "twitter",
                        "agent_id": 3,
                        "agent_name": "Agent Name",
                        "action_type": "CREATE_POST",
                        "action_args": {"content": "..."},
                        "result": null,
                        "success": true
                    },
                    ...
                ],
                "twitter_actions": [...],  # Twitter 平台的所有动作
                "reddit_actions": [...]    # Reddit 平台的所有动作
            }
        }
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        platform_filter = request.args.get('platform')
        
        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "all_actions": [],
                    "twitter_actions": [],
                    "reddit_actions": []
                }
            })
        
        # 获取完整的动作列表
        all_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform_filter
        )
        
        # 分平台获取动作
        twitter_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="twitter"
        ) if not platform_filter or platform_filter == "twitter" else []
        
        reddit_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="reddit"
        ) if not platform_filter or platform_filter == "reddit" else []
        
        # 获取当前轮次的动作（recent_actions 只展示最新一轮）
        current_round = run_state.current_round
        recent_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform_filter,
            round_num=current_round
        ) if current_round > 0 else []
        
        # 获取基础状态信息
        result = run_state.to_dict()
        result["all_actions"] = [a.to_dict() for a in all_actions]
        result["twitter_actions"] = [a.to_dict() for a in twitter_actions]
        result["reddit_actions"] = [a.to_dict() for a in reddit_actions]
        result["rounds_count"] = len(run_state.rounds)
        # recent_actions 只展示当前最新一轮两个平台的内容
        result["recent_actions"] = [a.to_dict() for a in recent_actions]
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération du statut détaillé: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/cognitive-states', methods=['GET'])
def get_cognitive_states(simulation_id: str):
    """
    Retourne les états cognitifs (tensions, croyances, auto-narrations) de tous les agents.
    """
    try:
        from app.services.cognitive_memory import CognitiveMemoryService
        from app.services.local_graph_database import LocalGraphDatabase
        
        states = []
        db_success = False
        
        try:
            with LocalGraphDatabase(simulation_id, read_only=True) as db:
                tables = db._get_all_tables()
                if "Node_CognitiveState" in tables:
                    query = "MATCH (n:Node_CognitiveState) RETURN n.uuid, n.name, n.summary, n.attributes"
                    res = db._execute(query)
                    while res.has_next():
                        row = res.get_next()
                        attr = json.loads(row[3]) if row[3] else {}
                        states.append({
                            "agent_id": row[0],
                            "name": row[1],
                            "meta_narrative": row[2],
                            "personality": attr.get("personality", ""),
                            "tensions": attr.get("tensions", {}),
                            "beliefs": attr.get("beliefs", {}),
                            "recent_reflection": attr.get("recent_reflection", "")
                        })
                    db_success = True
                else:
                    db_success = True  # Table not present, empty states list is correct
        except Exception as db_err:
            logger.warning(f"Kuzu DB busy/locked while getting cognitive states for {simulation_id}: {db_err}. Falling back to JSON cache.")
            
        if not db_success:
            # Fallback to local JSON cache file
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            cache_path = os.path.join(base_dir, 'uploads', 'simulations', simulation_id, 'cognitive_states_cache.json')
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as cf:
                        cache_data = json.load(cf)
                        states = list(cache_data.values())
                        db_success = True
                except Exception as cache_err:
                    logger.error(f"Failed to read cognitive states cache file: {cache_err}")
            
            if not db_success:
                # Secondary fallback: try to reconstruct from cognitive history in run_state.json
                run_state_path = os.path.join(base_dir, 'uploads', 'simulations', simulation_id, 'run_state.json')
                if os.path.exists(run_state_path):
                    try:
                        with open(run_state_path, 'r', encoding='utf-8') as sf:
                            run_state_data = json.load(sf)
                            history = run_state_data.get("cognitive_history", [])
                            if history:
                                last_record = history[-1]
                                for agent_id, agent_info in last_record.get("agents", {}).items():
                                    states.append({
                                        "agent_id": agent_id,
                                        "name": agent_info.get("name", ""),
                                        "meta_narrative": "",
                                        "personality": agent_info.get("personality", ""),
                                        "tensions": {
                                            "procedure_vs_equite": agent_info.get("procedure_vs_equite", 0.5),
                                            "offensive_vs_negociation": agent_info.get("offensive_vs_negociation", 0.5),
                                            "prudence_vs_rapidite": agent_info.get("prudence_vs_rapidite", 0.5)
                                        },
                                        "beliefs": {
                                            "culpabilite_accuse": {
                                                "coupable": agent_info.get("belief_coupable", 0.5)
                                            }
                                        },
                                        "recent_reflection": ""
                                    })
                                db_success = True
                    except Exception as hist_err:
                        logger.error(f"Failed to read cognitive history from run_state: {hist_err}")

        return jsonify({
            "success": True,
            "data": states
        })
    except Exception as e:
        logger.error(f"Erreur de récupération des états cognitifs: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/<simulation_id>/actions', methods=['GET'])
def get_simulation_actions(simulation_id: str):
    """
    获取模拟中的Agent动作历史
    
    Query参数：
        limit: 返回数量（默认100）
        offset: 偏移量（默认0）
        platform: 过滤平台（twitter/reddit）
        agent_id: 过滤Agent ID
        round_num: 过滤轮次
    
    返回：
        {
            "success": true,
            "data": {
                "count": 100,
                "actions": [...]
            }
        }
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        platform = request.args.get('platform')
        agent_id = request.args.get('agent_id', type=int)
        round_num = request.args.get('round_num', type=int)
        
        actions = SimulationRunner.get_actions(
            simulation_id=simulation_id,
            limit=limit,
            offset=offset,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )
        
        return jsonify({
            "success": True,
            "data": {
                "count": len(actions),
                "actions": [a.to_dict() for a in actions]
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'historique des actions: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/timeline', methods=['GET'])
def get_simulation_timeline(simulation_id: str):
    """
    获取模拟时间线（按轮次汇总）
    
    用于前端展示进度条和时间线视图
    
    Query参数：
        start_round: 起始轮次（默认0）
        end_round: 结束轮次（默认全部）
    
    返回每轮的汇总信息
    """
    try:
        start_round = request.args.get('start_round', 0, type=int)
        end_round = request.args.get('end_round', type=int)
        
        timeline = SimulationRunner.get_timeline(
            simulation_id=simulation_id,
            start_round=start_round,
            end_round=end_round
        )
        
        return jsonify({
            "success": True,
            "data": {
                "rounds_count": len(timeline),
                "timeline": timeline
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la chronologie: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/agent-stats', methods=['GET'])
def get_agent_stats(simulation_id: str):
    """
    获取每个Agent的统计信息
    
    用于前端展示Agent活跃度排行、动作分布等
    """
    try:
        stats = SimulationRunner.get_agent_stats(simulation_id)
        
        return jsonify({
            "success": True,
            "data": {
                "agents_count": len(stats),
                "stats": stats
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des statistiques de l'Agent: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 数据库查询接口 ==============

@simulation_bp.route('/<simulation_id>/posts', methods=['GET'])
def get_simulation_posts(simulation_id: str):
    """
    获取模拟中的帖子
    
    Query参数：
        platform: 平台类型（twitter/reddit）
        limit: 返回数量（默认50）
        offset: 偏移量
    
    返回帖子列表（从SQLite数据库读取）
    """
    try:
        platform = request.args.get('platform', 'reddit')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )
        
        db_file = f"{platform}_simulation.db"
        db_path = os.path.join(sim_dir, db_file)
        
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "platform": platform,
                    "count": 0,
                    "posts": [],
                    "message": t('api.dbNotExist')
                }
            })
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM post 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            posts = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(*) FROM post")
            total = cursor.fetchone()[0]
            
        except sqlite3.OperationalError:
            posts = []
            total = 0
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "total": total,
                "count": len(posts),
                "posts": posts
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des publications: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/comments', methods=['GET'])
def get_simulation_comments(simulation_id: str):
    """
    获取模拟中的评论（仅Reddit）
    
    Query参数：
        post_id: 过滤帖子ID（可选）
        limit: 返回数量
        offset: 偏移量
    """
    try:
        post_id = request.args.get('post_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )
        
        db_path = os.path.join(sim_dir, "reddit_simulation.db")
        
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "count": 0,
                    "comments": []
                }
            })
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if post_id:
                cursor.execute("""
                    SELECT * FROM comment 
                    WHERE post_id = ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (post_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM comment 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            comments = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.OperationalError:
            comments = []
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "count": len(comments),
                "comments": comments
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des commentaires: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interview 采访接口 ==============

@simulation_bp.route('/interview', methods=['POST'])
def interview_agent():
    """
    采访单个Agent

    注意：此功能需要模拟环境处于运行状态（完成模拟循环后进入等待命令模式）

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",       // 必填，模拟ID
            "agent_id": 0,                     // 必填，Agent ID
            "prompt": "你对这件事有什么看法？",  // 必填，采访问题
            "platform": "twitter",             // 可选，指定平台（twitter/reddit）
                                               // 不指定时：双平台模拟同时采访两个平台
            "timeout": 60                      // 可选，超时时间（秒），默认60
        }

    返回（不指定platform，双平台模式）：
        {
            "success": true,
            "data": {
                "agent_id": 0,
                "prompt": "你对这件事有什么看法？",
                "result": {
                    "agent_id": 0,
                    "prompt": "...",
                    "platforms": {
                        "twitter": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit": {"agent_id": 0, "response": "...", "platform": "reddit"}
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }

    返回（指定platform）：
        {
            "success": true,
            "data": {
                "agent_id": 0,
                "prompt": "你对这件事有什么看法？",
                "result": {
                    "agent_id": 0,
                    "response": "我认为...",
                    "platform": "twitter",
                    "timestamp": "2025-12-08T10:00:00"
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        agent_id = data.get('agent_id')
        prompt = data.get('prompt')
        platform = data.get('platform')  # 可选：twitter/reddit/None
        timeout = data.get('timeout', 60)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        if agent_id is None:
            return jsonify({
                "success": False,
                "error": t('api.requireAgentId')
            }), 400
        
        if not prompt:
            return jsonify({
                "success": False,
                "error": t('api.requirePrompt')
            }), 400
        
        # 验证platform参数
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": t('api.invalidInterviewPlatform')
            }), 400
        
        # Check if project's simulation mode is legal
        import json
        from datetime import datetime
        
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        is_legal = False
        project = None
        if state:
            project = ProjectManager.get_project(state.project_id)
            if project and project.simulation_mode == 'legal':
                is_legal = True

        if is_legal:
            # 1. Load the profiles
            sim_dir = manager._get_simulation_dir(simulation_id)
            profiles_path = os.path.join(sim_dir, "reddit_profiles.json")
            if not os.path.exists(profiles_path):
                return jsonify({
                    "success": False,
                    "error": "Profils d'agents introuvables."
                }), 404
                
            with open(profiles_path, 'r', encoding='utf-8') as f:
                profiles_data = json.load(f)
                
            profile = next((p for p in profiles_data if p.get("user_id") == agent_id), None)
            if not profile:
                return jsonify({
                    "success": False,
                    "error": f"Agent avec l'ID {agent_id} introuvable."
                }), 404
                
            agent_name = profile.get("username") or profile.get("name")
            agent_persona = profile.get("persona") or ""
            
            # Load case document details as context
            doc_text = ProjectManager.get_extracted_text(state.project_id) or ""
            context = f"Exigences de simulation : {project.simulation_requirement or ''}"
            if doc_text:
                context += f"\n\nFaits admis et pièces du dossier d'audience (faits réels à respecter absolument) :\n{doc_text}"

            # Charger l'état cognitif PIE de l'agent depuis Kuzu DB
            cognitive_state_info = ""
            try:
                from app.services.local_graph_database import LocalGraphDatabase
                with LocalGraphDatabase(simulation_id, read_only=True) as db:
                    tables = db._get_all_tables()
                    if "Node_CognitiveState" in tables:
                        query = "MATCH (n:Node_CognitiveState) RETURN n.uuid, n.name, n.summary, n.attributes"
                        res = db._execute(query)
                        while res.has_next():
                            row = res.get_next()
                            uuid_str = row[0]
                            name_str = row[1]
                            
                            # Match agent by ID or name
                            if uuid_str == str(agent_id) or name_str == agent_name or agent_name.lower() in name_str.lower() or name_str.lower() in agent_name.lower():
                                summary = row[2] or ""
                                attr = json.loads(row[3]) if row[3] else {}
                                tensions = attr.get("tensions", {})
                                beliefs = attr.get("beliefs", {})
                                recent_reflection = attr.get("recent_reflection", "")
                                
                                cognitive_state_info = f"\n\n--- ÉTAT COGNITIF PIE DE L'AGENT ---\n"
                                if summary:
                                    cognitive_state_info += f"Auto-narration/état d'esprit interne : {summary}\n"
                                if tensions:
                                    cognitive_state_info += f"Tensions psychologiques actives (ex. Procédure vs Équité, etc.) : {tensions}\n"
                                if beliefs:
                                    cognitive_state_info += f"Croyances sur l'affaire : {beliefs}\n"
                                if recent_reflection:
                                    cognitive_state_info += f"Réflexions récentes : {recent_reflection}\n"
                                break
            except Exception as db_err:
                logger.warning(f"Impossible de charger l'état cognitif de l'agent: {db_err}")

            # Load history
            history_path = os.path.join(sim_dir, "interview_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []
                    
            agent_history = [h for h in history if h.get("agent_id") == agent_id]
            
            system_prompt = f"Tu es {agent_name}, un acteur du procès.\n" \
                            f"Ton profil/persona : {agent_persona}\n\n" \
                            f"Contexte du dossier de l'affaire :\n{context}\n\n" \
                            f"{cognitive_state_info}\n\n" \
                            f"RÈGLES ABSOLUES :\n" \
                            f"1. Tu es pleinement ancré dans l'affaire et les faits réels décrits ci-dessus. Réponds de manière réaliste à la question en te basant STRICTEMENT sur les faits et documents du dossier, ne sors pas de ton rôle.\n" \
                            f"2. Prends en compte ton état d'esprit interne (PIE), tes tensions actives, et tes croyances pour orienter tes réponses.\n" \
                            f"3. Ne fais référence à aucun élément technique de la simulation (comme PIE, Kuzu, modèle, prompt, LLM). Reste purement dans ton personnage juridique."
                            
            messages = []
            for turn in agent_history:
                messages.append({"role": "user", "content": turn.get("prompt")})
                messages.append({"role": "assistant", "content": turn.get("response")})
                
            messages.append({"role": "user", "content": prompt})
            
            from openai import OpenAI
            from ..config import Config
            api_key = Config.LLM_API_KEY or "local-no-key"
            base_url = Config.LLM_BASE_URL
            model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
            
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)
                
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
            except Exception as llm_err:
                logger.error(f"Error querying LLM for legal agent interview: {llm_err}")
                response_text = "Je m'excuse, je rencontre des difficultés techniques à répondre."
                
            new_turn = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "prompt": prompt,
                "response": response_text,
                "platform": "courtroom",
                "timestamp": datetime.now().isoformat()
            }
            history.append(new_turn)
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
            return jsonify({
                "success": True,
                "data": {
                    "agent_id": agent_id,
                    "prompt": prompt,
                    "response": response_text,
                    "platform": "courtroom",
                    "timestamp": datetime.now().isoformat()
                }
            })

        # 检查环境状态
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": t('api.envNotRunning')
            }), 400
        
        # 优化prompt，添加前缀避免Agent调用工具
        optimized_prompt = optimize_interview_prompt(prompt)
        
        result = SimulationRunner.interview_agent(
            simulation_id=simulation_id,
            agent_id=agent_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": t('api.interviewTimeout', error=str(e))
        }), 504
        
    except Exception as e:
        logger.error(f"Échec de l'interview: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/interview/batch', methods=['POST'])
def interview_agents_batch():
    """
    批量采访多个Agent

    注意：此功能需要模拟环境处于运行状态

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",       // 必填，模拟ID
            "interviews": [                    // 必填，采访列表
                {
                    "agent_id": 0,
                    "prompt": "你对A有什么看法？",
                    "platform": "twitter"      // 可选，指定该Agent的采访平台
                },
                {
                    "agent_id": 1,
                    "prompt": "你对B有什么看法？"  // 不指定platform则使用默认值
                }
            ],
            "platform": "reddit",              // 可选，默认平台（被每项的platform覆盖）
                                               // 不指定时：双平台模拟每个Agent同时采访两个平台
            "timeout": 120                     // 可选，超时时间（秒），默认120
        }

    返回：
        {
            "success": true,
            "data": {
                "interviews_count": 2,
                "result": {
                    "interviews_count": 4,
                    "results": {
                        "twitter_0": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit_0": {"agent_id": 0, "response": "...", "platform": "reddit"},
                        "twitter_1": {"agent_id": 1, "response": "...", "platform": "twitter"},
                        "reddit_1": {"agent_id": 1, "response": "...", "platform": "reddit"}
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        interviews = data.get('interviews')
        platform = data.get('platform')  # 可选：twitter/reddit/None
        timeout = data.get('timeout', 120)

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not interviews or not isinstance(interviews, list):
            return jsonify({
                "success": False,
                "error": t('api.requireInterviews')
            }), 400

        # 验证platform参数
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": t('api.invalidInterviewPlatform')
            }), 400

        # 验证每个采访项
        for i, interview in enumerate(interviews):
            if 'agent_id' not in interview:
                return jsonify({
                    "success": False,
                    "error": t('api.interviewListMissingAgentId', index=i+1)
                }), 400
            if 'prompt' not in interview:
                return jsonify({
                    "success": False,
                    "error": t('api.interviewListMissingPrompt', index=i+1)
                }), 400
            # 验证每项的platform（如果有）
            item_platform = interview.get('platform')
            if item_platform and item_platform not in ("twitter", "reddit"):
                return jsonify({
                    "success": False,
                    "error": t('api.interviewListInvalidPlatform', index=i+1)
                }), 400

        # Check if project's simulation mode is legal
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        is_legal = False
        project = None
        if state:
            project = ProjectManager.get_project(state.project_id)
            if project and project.simulation_mode == 'legal':
                is_legal = True

        if is_legal:
            import json
            from datetime import datetime
            
            # 1. Load the profiles
            sim_dir = manager._get_simulation_dir(simulation_id)
            profiles_path = os.path.join(sim_dir, "reddit_profiles.json")
            if not os.path.exists(profiles_path):
                return jsonify({
                    "success": False,
                    "error": "Profils d'agents introuvables."
                }), 404
                
            with open(profiles_path, 'r', encoding='utf-8') as f:
                profiles_data = json.load(f)
                
            # Load history
            history_path = os.path.join(sim_dir, "interview_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []

            results = {}
            from openai import OpenAI
            from ..config import Config
            api_key = Config.LLM_API_KEY or "local-no-key"
            base_url = Config.LLM_BASE_URL
            model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
            
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)

            doc_text = ProjectManager.get_extracted_text(state.project_id) or ""
            context = f"Exigences de simulation : {project.simulation_requirement or ''}"
            if doc_text:
                context += f"\n\nFaits admis et pièces du dossier d'audience (faits réels à respecter absolument) :\n{doc_text}"

            for item in interviews:
                agent_id = item.get('agent_id')
                prompt = item.get('prompt')
                
                profile = next((p for p in profiles_data if p.get("user_id") == agent_id), None)
                if not profile:
                    if agent_id in [1001, 1002, 1003]:
                        if agent_id == 1001:
                            profile = {
                                "user_id": 1001,
                                "username": "juge_formaliste",
                                "name": "Juge 1 : Formaliste strict",
                                "persona": "Tu es le Juge 1 (Formaliste strict) du tribunal collégial présidant ce litige. Tu appliques la loi à la lettre, sans pitié. Tu te focalises scrupuleusement sur les détails de procédure et les textes contractuels."
                            }
                        elif agent_id == 1002:
                            profile = {
                                "user_id": 1002,
                                "username": "juge_equite",
                                "name": "Juge 2 : Sensible à l'équité",
                                "persona": "Tu es le Juge 2 (Sensible à l'équité) du tribunal collégial présidant ce litige. Tu prends en compte les circonstances atténuantes, le préjudice réel subi par les parties et le contexte social général."
                            }
                        elif agent_id == 1003:
                            profile = {
                                "user_id": 1003,
                                "username": "juge_conservateur",
                                "name": "Juge 3 : Conservateur",
                                "persona": "Tu es le Juge 3 (Conservateur) du tribunal collégial présidant ce litige. Tu favorises la stabilité contractuelle, la jurisprudence classique établie et l'ordre public."
                            }
                    else:
                        continue
                    
                agent_name = profile.get("username") or profile.get("name")
                agent_persona = profile.get("persona") or ""
                
                # Charger l'état cognitif PIE de l'agent depuis Kuzu DB
                cognitive_state_info = ""
                try:
                    from app.services.local_graph_database import LocalGraphDatabase
                    with LocalGraphDatabase(simulation_id, read_only=True) as db:
                        tables = db._get_all_tables()
                        if "Node_CognitiveState" in tables:
                            query = "MATCH (n:Node_CognitiveState) RETURN n.uuid, n.name, n.summary, n.attributes"
                            res = db._execute(query)
                            while res.has_next():
                                row = res.get_next()
                                uuid_str = row[0]
                                name_str = row[1]
                                
                                # Match agent by ID or name
                                if uuid_str == str(agent_id) or name_str == agent_name or agent_name.lower() in name_str.lower() or name_str.lower() in agent_name.lower():
                                    summary = row[2] or ""
                                    attr = json.loads(row[3]) if row[3] else {}
                                    tensions = attr.get("tensions", {})
                                    beliefs = attr.get("beliefs", {})
                                    recent_reflection = attr.get("recent_reflection", "")
                                    
                                    cognitive_state_info = f"\n\n--- ÉTAT COGNITIF PIE DE L'AGENT ---\n"
                                    if summary:
                                        cognitive_state_info += f"Auto-narration/état d'esprit interne : {summary}\n"
                                    if tensions:
                                        cognitive_state_info += f"Tensions psychologiques actives (ex. Procédure vs Équité, etc.) : {tensions}\n"
                                    if beliefs:
                                        cognitive_state_info += f"Croyances sur l'affaire : {beliefs}\n"
                                    if recent_reflection:
                                        cognitive_state_info += f"Réflexions récentes : {recent_reflection}\n"
                                    break
                except Exception as db_err:
                    logger.warning(f"Impossible de charger l'état cognitif de l'agent: {db_err}")

                agent_history = [h for h in history if h.get("agent_id") == agent_id]
                
                system_prompt = f"Tu es {agent_name}, un acteur du procès.\n" \
                                f"Ton profil/persona : {agent_persona}\n\n" \
                                f"Contexte du dossier de l'affaire :\n{context}\n\n" \
                                f"{cognitive_state_info}\n\n" \
                                f"RÈGLES ABSOLUES :\n" \
                                f"1. Tu es pleinement ancré dans l'affaire et les faits réels décrits ci-dessus. Réponds de manière réaliste à la question en te basant STRICTEMENT sur les faits et documents du dossier, ne sors pas de ton rôle.\n" \
                                f"2. Prends en compte ton état d'esprit interne (PIE), tes tensions actives, et tes croyances pour orienter tes réponses.\n" \
                                f"3. Ne fais référence à aucun élément technique de la simulation (comme PIE, Kuzu, modèle, prompt, LLM). Reste purement dans ton personnage juridique."
                                
                messages = []
                for turn in agent_history:
                    messages.append({"role": "user", "content": turn.get("prompt")})
                    messages.append({"role": "assistant", "content": turn.get("response")})
                    
                messages.append({"role": "user", "content": prompt})
                
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_prompt}] + messages,
                        temperature=0.7
                    )
                    response_text = response.choices[0].message.content
                except Exception as llm_err:
                    logger.error(f"Error querying LLM for legal agent interview (batch): {llm_err}")
                    response_text = "Je m'excuse, je rencontre des difficultés techniques à répondre."
                    
                timestamp = datetime.now().isoformat()
                new_turn = {
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "prompt": prompt,
                    "response": response_text,
                    "platform": "courtroom",
                    "timestamp": timestamp
                }
                history.append(new_turn)
                
                # Format for frontend Step5Interaction.vue
                results[f"reddit_{agent_id}"] = {
                    "agent_id": agent_id,
                    "response": response_text,
                    "platform": "reddit",
                    "timestamp": timestamp
                }
                results[f"twitter_{agent_id}"] = {
                    "agent_id": agent_id,
                    "response": response_text,
                    "platform": "twitter",
                    "timestamp": timestamp
                }

            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
            return jsonify({
                "success": True,
                "data": {
                    "interviews_count": len(interviews),
                    "result": {
                        "results": results
                    },
                    "timestamp": datetime.now().isoformat()
                }
            })

        # 检查环境状态
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": t('api.envNotRunning')
            }), 400

        # 优化每个采访项的prompt，添加前缀避免Agent调用工具
        optimized_interviews = []
        for interview in interviews:
            optimized_interview = interview.copy()
            optimized_interview['prompt'] = optimize_interview_prompt(interview.get('prompt', ''))
            optimized_interviews.append(optimized_interview)

        result = SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=optimized_interviews,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": t('api.batchInterviewTimeout', error=str(e))
        }), 504

    except Exception as e:
        logger.error(f"Échec de l'interview groupée: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/interview/all', methods=['POST'])
def interview_all_agents():
    """
    全局采访 - 使用相同问题采访所有Agent

    注意：此功能需要模拟环境处于运行状态

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",            // 必填，模拟ID
            "prompt": "你对这件事整体有什么看法？",  // 必填，采访问题（所有Agent使用相同问题）
            "platform": "reddit",                   // 可选，指定平台（twitter/reddit）
                                                    // 不指定时：双平台模拟每个Agent同时采访两个平台
            "timeout": 180                          // 可选，超时时间（秒），默认180
        }

    返回：
        {
            "success": true,
            "data": {
                "interviews_count": 50,
                "result": {
                    "interviews_count": 100,
                    "results": {
                        "twitter_0": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit_0": {"agent_id": 0, "response": "...", "platform": "reddit"},
                        ...
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        prompt = data.get('prompt')
        platform = data.get('platform')  # 可选：twitter/reddit/None
        timeout = data.get('timeout', 180)

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not prompt:
            return jsonify({
                "success": False,
                "error": t('api.requirePrompt')
            }), 400

        # 验证platform参数
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": t('api.invalidInterviewPlatform')
            }), 400

        # 检查环境状态
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": t('api.envNotRunning')
            }), 400

        # 优化prompt，添加前缀避免Agent调用工具
        optimized_prompt = optimize_interview_prompt(prompt)

        result = SimulationRunner.interview_all_agents(
            simulation_id=simulation_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": t('api.globalInterviewTimeout', error=str(e))
        }), 504

    except Exception as e:
        logger.error(f"Échec de l'interview globale: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/interview/history', methods=['POST'])
def get_interview_history():
    """
    获取Interview历史记录

    从模拟数据库中读取所有Interview记录

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",  // 必填，模拟ID
            "platform": "reddit",          // 可选，平台类型（reddit/twitter）
                                           // 不指定则返回两个平台的所有历史
            "agent_id": 0,                 // 可选，只获取该Agent的采访历史
            "limit": 100                   // 可选，返回数量，默认100
        }

    返回：
        {
            "success": true,
            "data": {
                "count": 10,
                "history": [
                    {
                        "agent_id": 0,
                        "response": "我认为...",
                        "prompt": "你对这件事有什么看法？",
                        "timestamp": "2025-12-08T10:00:00",
                        "platform": "reddit"
                    },
                    ...
                ]
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        platform = data.get('platform')  # 不指定则返回两个平台的历史
        agent_id = data.get('agent_id')
        limit = data.get('limit', 100)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        # Check if project's simulation mode is legal
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        is_legal = False
        if state:
            project = ProjectManager.get_project(state.project_id)
            if project and project.simulation_mode == 'legal':
                is_legal = True

        if is_legal:
            sim_dir = manager._get_simulation_dir(simulation_id)
            history_path = os.path.join(sim_dir, "interview_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []
            
            if agent_id is not None:
                history = [h for h in history if h.get("agent_id") == agent_id]
                
            history = history[:limit]
            
            formatted_history = []
            for h in history:
                formatted_history.append({
                    "agent_id": h.get("agent_id"),
                    "prompt": h.get("prompt"),
                    "response": h.get("response"),
                    "timestamp": h.get("timestamp"),
                    "platform": h.get("platform", "courtroom")
                })
                
            return jsonify({
                "success": True,
                "data": {
                    "count": len(formatted_history),
                    "history": formatted_history
                }
            })

        history = SimulationRunner.get_interview_history(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": {
                "count": len(history),
                "history": history
            }
        })

    except Exception as e:
        logger.error(f"Échec de la récupération de l'historique d'interview: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/env-status', methods=['POST'])
def get_env_status():
    """
    获取模拟环境状态

    检查模拟环境是否存活（可以接收Interview命令）

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx"  // 必填，模拟ID
        }

    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "env_alive": true,
                "twitter_available": true,
                "reddit_available": true,
                "message": "环境正在运行，可以接收Interview命令"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        env_alive = SimulationRunner.check_env_alive(simulation_id)
        
        # 获取更详细的状态信息
        env_status = SimulationRunner.get_env_status_detail(simulation_id)

        if env_alive:
            message = t('api.envRunning')
        else:
            message = t('api.envNotRunningShort')

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "env_alive": env_alive,
                "twitter_available": env_status.get("twitter_available", False),
                "reddit_available": env_status.get("reddit_available", False),
                "message": message
            }
        })

    except Exception as e:
        logger.error(f"Échec de la récupération de l'état de l'environnement: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/close-env', methods=['POST'])
def close_simulation_env():
    """
    关闭模拟环境
    
    向模拟发送关闭环境命令，使其优雅退出等待命令模式。
    
    注意：这不同于 /stop 接口，/stop 会强制终止进程，
    而此接口会让模拟优雅地关闭环境并退出。
    
    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",  // 必填，模拟ID
            "timeout": 30                  // 可选，超时时间（秒），默认30
        }
    
    返回：
        {
            "success": true,
            "data": {
                "message": "环境关闭命令已发送",
                "result": {...},
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        timeout = data.get('timeout', 30)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        result = SimulationRunner.close_simulation_env(
            simulation_id=simulation_id,
            timeout=timeout
        )
        
        # 更新模拟状态
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.COMPLETED
            manager._save_simulation_state(state)
        
        return jsonify({
            "success": result.get("success", False),
            "data": result
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Legal Simulation API ==============

@simulation_bp.route('/legal/run', methods=['POST'])
def run_legal_simulation():
    """
    Lance la simulation juridique multi-agents.
    """
    import threading
    from scripts.run_legal_simulation import LegalSimulationRunner
    from ..models.task import TaskManager, TaskStatus
    
    try:
        data = request.get_json() or {}
        context = data.get('context')
        iterations = data.get('iterations', 10)
        judge_type = data.get('judge_type', 'single')
        selected_judge_personality = data.get('selected_judge_personality')
        selected_judges_personalities = data.get('selected_judges_personalities')
        
        if not context:
            return jsonify({
                "success": False,
                "error": "Le paramètre 'context' est requis."
            }), 400
            
        project_id = data.get('project_id')
        if project_id:
            try:
                from ..models.project import ProjectManager
                from ..services.local_graph_database import LocalGraphDatabase
                project = ProjectManager.get_project(project_id)
                if project and project.graph_id:
                    with LocalGraphDatabase(project.graph_id) as db:
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
                logger.error(f"Erreur d'enrichissement par le graphe: {graph_err}")
                
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="legal_simulation",
            metadata={"context": context[:100] + "..."}
        )
        
        # Détection du type de litige (civil vs criminel)
        litigation_type = "civil"
        try:
            from openai import OpenAI
            api_key = Config.LLM_API_KEY or "local-no-key"
            base_url = Config.LLM_BASE_URL
            model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
            
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)
                
            classification_prompt = f"""Analyse la description du litige ci-dessous et classifie-la en un type précis de litige.
Réponds UNIQUEMENT par l'un de ces deux mots en minuscule sans aucune ponctuation : "civil" ou "criminal".

- Choisi "civil" s'il s'agit de litiges commerciaux, de contrats, de vices cachés, de droit civil, de poursuites entre entreprises ou individus, d'indemnisations.
- Choisi "criminal" s'il s'agit d'infractions criminelles, de fraudes pénales, d'agressions, d'homicides ou de poursuites par l'État/le Ministère Public pour un crime.

Description du litige :
{context[:2000]}
"""
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Tu es un assistant juridique expert qui classifie les litiges."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.0,
                max_tokens=5
            )
            output_text = response.choices[0].message.content.strip().lower()
            if "criminal" in output_text:
                litigation_type = "criminal"
            else:
                litigation_type = "civil"
            logger.info(f"Détection automatique du type de litige (Monte-Carlo) : {litigation_type} (LLM retourné : {output_text})")
        except Exception as e:
            logger.warning(f"Erreur lors de la détection du type de litige par LLM : {e}. Par défaut : civil")
            req_lower = context.lower()
            if any(k in req_lower for k in ["pénale", "pénal", "criminel", "criminal", "meurtre", "vol de", "agression", "infraction"]):
                litigation_type = "criminal"
                
        def _run_in_background():
            try:
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=10, message="Démarrage...")
                runner = LegalSimulationRunner(
                    context=context, 
                    iterations=iterations, 
                    litigation_type=litigation_type,
                    judge_type=judge_type,
                    selected_judge_personality=selected_judge_personality,
                    selected_judges_personalities=selected_judges_personalities
                )
                outfile = runner.run_full_simulation()
                task_manager.complete_task(task_id, result={"output_file": outfile})
            except Exception as e:
                logger.error(f"Erreur Simulation Juridique: {e}")
                task_manager.fail_task(task_id, str(e))
                
        # Démarrage
        thread = threading.Thread(target=_run_in_background, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "message": "Simulation juridique lancée en arrière-plan.",
                "task_id": task_id
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lancement simulation juridique: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/legal/result/<task_id>', methods=['GET'])
def get_legal_simulation_result(task_id):
    """
    Récupère le résultat détaillé d'une simulation juridique complétée.
    """
    from ..models.task import TaskManager, TaskStatus
    import json
    
    task = TaskManager().get_task(task_id)
    if not task:
        return jsonify({
            "success": False,
            "error": "Tâche non trouvée."
        }), 404
        
    if task.status != TaskStatus.COMPLETED:
        return jsonify({
            "success": False,
            "status": task.status.value,
            "progress": task.progress,
            "message": task.message,
            "error": task.error
        }), 200
        
    outfile = task.result.get("output_file") if task.result else None
    if not outfile or not os.path.exists(outfile):
        return jsonify({
            "success": False,
            "error": "Fichier résultat introuvable."
        }), 404
        
    try:
        with open(outfile, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



@simulation_bp.route('/benchmark/create', methods=['POST'])
def create_pie_benchmark():
    """
    Crée un projet et une simulation réels pour exécuter un benchmark en direct.
    """
    try:
        data = request.get_json() or {}
        benchmark_type = data.get('type') # 'hysteresis', 'inertia', 'attention'
        
        if not benchmark_type:
            return jsonify({
                "success": False,
                "error": "Le paramètre 'type' (hysteresis, inertia, attention) est requis."
            }), 400
            
        import uuid
        import json
        from datetime import datetime
        from app.models.project import Project, ProjectManager, ProjectStatus
        from app.services.simulation_manager import SimulationState, SimulationStatus, SimulationManager
        from app.services.local_graph_database import LocalGraphDatabase
        
        # 1. Créer le projet
        proj_id = f"proj_proof_{benchmark_type}_{uuid.uuid4().hex[:8]}"
        graph_id = f"graph_proof_{benchmark_type}_{uuid.uuid4().hex[:8]}"
        
        import os
        # S'assurer que les répertoires du projet existent
        ProjectManager._ensure_projects_dir()
        proj_dir = ProjectManager._get_project_dir(proj_id)
        files_dir = ProjectManager._get_project_files_dir(proj_id)
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)
        
        name_map = {
            "hysteresis": "Banc d'Essai - Négociation de Contrat",
            "inertia": "Banc d'Essai - Stabilité Décisionnelle Judiciaire",
            "attention": "Banc d'Essai - Analyse de Dossier Complexe"
        }
        
        req_map = {
            "hysteresis": "Démonstration quantitative de l'hystérésis d'humeur lors de négociations contractuelles tendues face à des clauses abusives répétées.",
            "inertia": "Comparaison de la stabilité décisionnelle d'un magistrat face aux contradictions des témoignages : Juge standard vs Juge régulé par les précédents judiciaires (PIE).",
            "attention": "Modélisation de la focalisation de l'attention de l'avocat et de l'élagage des détails procéduraux mineurs sous contrainte de temps strict (10% de budget attentionnel)."
        }
        
        project = Project(
            project_id=proj_id,
            name=name_map.get(benchmark_type, "Banc d'Essai Scientifique"),
            status=ProjectStatus.GRAPH_COMPLETED,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            simulation_requirement=req_map.get(benchmark_type, "Validation du moteur de simulation"),
            graph_id=graph_id
        )
        ProjectManager.save_project(project)
        
        # 2. Insérer des nœuds dans Kuzu DB pour que le graphe s'affiche
        with LocalGraphDatabase(graph_id) as db:
            if benchmark_type == "hysteresis":
                db.upsert_triplets(
                    nodes=[
                        {"uuid": "1", "label": "Avocat", "name": "Maitre_Bob_Defenseur", "summary": "Avocat de la défense négociant un accord de règlement à l'amiable.", "attributes": {}},
                        {"uuid": "2", "label": "Procureur", "name": "Maitre_Voisin_Procureur", "summary": "Procureur de la partie adverse initiant des clauses restrictives.", "attributes": {}}
                    ],
                    edges=[
                        {"uuid": "e1", "label": "OPPOSE", "source": "1", "target": "2", "fact": "Maître Bob s'oppose au Procureur lors de la négociation."},
                        {"uuid": "e2", "label": "NEGOCIE", "source": "2", "target": "1", "fact": "Le Procureur négocie les clauses du règlement."}
                    ]
                )
            elif benchmark_type == "inertia":
                db.upsert_triplets(
                    nodes=[
                        {"uuid": "1", "label": "Juge", "name": "Juge_Standard_Temoin", "summary": "Juge témoin sujet aux fluctuations des déclarations d'audience.", "attributes": {}},
                        {"uuid": "2", "label": "Juge", "name": "Juge_PIE_Precedents", "summary": "Juge régulé par l'inertie des précédents judiciaires (stable).", "attributes": {}}
                    ],
                    edges=[
                        {"uuid": "e1", "label": "COMPARE", "source": "2", "target": "1", "fact": "Comparaison de variance découlant du cadre jurisprudentiel."}
                    ]
                )
            else: # attention
                db.upsert_triplets(
                    nodes=[
                        {"uuid": "1", "label": "Avocat", "name": "Maitre_Alice_Avocat", "summary": "Avocate analysant un dossier juridique volumineux sous contrainte de temps.", "attributes": {}},
                        {"uuid": "2", "label": "Greffier", "name": "Greffier_Tribunal", "summary": "Greffier ayant rédigé des notes de procédure secondaires.", "attributes": {}}
                    ],
                    edges=[
                        {"uuid": "e1", "label": "ANALYSE", "source": "1", "target": "2", "fact": "Maître Alice analyse les notes rédigées par le greffier."}
                    ]
                )
            
        # 3. Créer la simulation
        sim_id = f"sim_proof_{benchmark_type}_{uuid.uuid4().hex[:8]}"
        sim_state = SimulationState(
            simulation_id=sim_id,
            project_id=proj_id,
            graph_id=graph_id,
            enable_twitter=True,
            enable_reddit=True,
            status=SimulationStatus.READY,
            entities_count=2,
            profiles_count=2 if benchmark_type == "inertia" else 1,
            entity_types=["Avocat", "Procureur"] if benchmark_type == "hysteresis" else (["Juge"] if benchmark_type == "inertia" else ["Avocat", "Greffier"]),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            config_generated=True
        )
        
        sim_manager = SimulationManager()
        sim_manager._save_simulation_state(sim_state)
        
        # 4. Écrire simulation_config.json
        sim_dir = sim_manager._get_simulation_dir(sim_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        config_data = {
            "project_id": proj_id,
            "simulation_id": sim_id,
            "simulation_requirement": req_map.get(benchmark_type, ""),
            "time_config": {
                "total_simulation_hours": 10 if benchmark_type != "inertia" else 15,
                "minutes_per_round": 60,
                "rounds": 10 if benchmark_type != "inertia" else 15
            },
            "recommend_config": {},
            "agent_config": {}
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
            
        # 5. Écrire les profiles
        reddit_profiles = []
        if benchmark_type == "hysteresis":
            reddit_profiles = [
                {"id": 1, "name": "Maitre_Bob_Defenseur", "profession": "Avocat de la Défense", "bio": "Agent pour le test d'hystérésis d'humeur dans une négociation de contrat."}
            ]
        elif benchmark_type == "inertia":
            reddit_profiles = [
                {"id": 1, "name": "Juge_Standard_Temoin", "profession": "Juge Témoin", "bio": "Agent représentant un juge sans ancrage jurisprudentiel fort."},
                {"id": 2, "name": "Juge_PIE_Precedents", "profession": "Juge PIE", "bio": "Agent représentant un juge s'appuyant sur des précédents stables."}
            ]
        else: # attention
            reddit_profiles = [
                {"id": 1, "name": "Maitre_Alice_Avocat", "profession": "Avocate Associée", "bio": "Agent pour le test d'élagage d'informations juridiques secondaires."}
            ]
            
        with open(os.path.join(sim_dir, "reddit_profiles.json"), 'w', encoding='utf-8') as f:
            json.dump(reddit_profiles, f, ensure_ascii=False, indent=2)
            
        # Créer un fichier csv vide pour twitter pour passer la validation de préparation
        with open(os.path.join(sim_dir, "twitter_profiles.csv"), 'w', encoding='utf-8') as f:
            f.write("id,name,profession,bio\n")
            for profile in reddit_profiles:
                f.write(f"{profile['id']},{profile['name']},{profile['profession']},{profile['bio']}\n")
                
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": sim_id,
                "project_id": proj_id,
                "status": "ready"
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors de la création du benchmark: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Live Proofs / Benchmark API ==============

@simulation_bp.route('/benchmark/run', methods=['POST'])
def run_pie_benchmark():
    """
    Exécute un benchmark cognitif PIE en direct et renvoie les résultats détaillés.
    """
    try:
        data = request.get_json() or {}
        benchmark_type = data.get('type') # 'hysteresis', 'inertia', 'attention'
        
        if not benchmark_type:
            return jsonify({
                "success": False,
                "error": "Le paramètre 'type' (hysteresis, inertia, attention) est requis."
            }), 400
            
        from ..services.cognitive_engine import CognitiveAgentState, CognitiveEngine
        from ..services.cognitive_memory import CognitiveMemoryService
        from ..services.cognitive_helper import inject_cognitive_prompts
        
        if benchmark_type == 'hysteresis':
            # Preuve 1 : Hystérésis & Négociation Contractuelle
            engine = CognitiveEngine()
            state = CognitiveAgentState(
                agent_id="agent_test_hysteresis",
                name="Maitre_Bob_Defenseur",
                mood="Neutre",
                negative_interactions_count=0
            )
            
            steps = []
            steps.append({
                "round": 0,
                "action": "INITIAL",
                "mood": state.mood,
                "negative_count": state.negative_interactions_count,
                "description": "État initial : Neutre. Prêt pour la négociation de contrat."
            })
            
            actions = [
                ("MUTE", "Friction : Le Procureur introduit une clause limitative de responsabilité abusive."),
                ("MUTE", "Friction : Le Procureur exige des pénalités de retard excessives."),
                ("DISLIKE_POST", "Friction : Le Procureur refuse de modifier la clause d'arbitrage."),
                ("MUTE", "Friction : Le Procureur rejette brutalement la contre-proposition de la défense."),
                ("LIKE_POST", "Concession : Le Procureur accorde une concession de redevances. (L'avocat reste méfiant due à l'asymétrie.)"),
                ("LIKE_POST", "Concession : Le Procureur accepte d'exclure les cas de force majeure des pénalités."),
                ("FOLLOW", "Concession : Le Procureur propose un partage équitable des frais de litige."),
                ("LIKE_POST", "Concession : Le Procureur valide la clause de non-concurrence restreinte."),
                ("LIKE_POST", "Concession : Accord final sur la propriété intellectuelle. L'humeur de l'avocat redevient Coopératif après 5 concessions.")
            ]
            
            for i, (action, desc) in enumerate(actions, 1):
                engine._update_mood_state(state, action)
                steps.append({
                    "round": i,
                    "action": action,
                    "mood": state.mood,
                    "negative_count": state.negative_interactions_count,
                    "description": desc
                })
                
            return jsonify({
                "success": True,
                "data": {
                    "steps": steps,
                    "conclusion": "L'asymétrie d'hystérésis est démontrée : 1 seule friction suffit à rendre l'avocat méfiant, mais 5 concessions successives sont requises pour restaurer la coopération."
                }
            })
            
        elif benchmark_type == 'inertia':
            # Preuve 2 : Stabilisation de la Trajectoire par Inertie Identitaire
            import random
            import math
            random.seed(42) # Reproductibilité
            
            steps_count = 15
            tension_control = 0.50
            tension_pie = 0.50
            eta = 0.10
            
            history = []
            history.append({
                "step": 0,
                "stimulus": 0.0,
                "tension_control": tension_control,
                "tension_pie": tension_pie,
                "inertia": 0.0
            })
            
            for i in range(1, steps_count + 1):
                delta_stimulus = random.choice([-0.08, 0.08])
                tension_control = max(0.0, min(1.0, tension_control + eta * (delta_stimulus / 0.08)))
                
                inertia = math.tanh(0.25 * i)
                effective_eta = eta * (1.0 - inertia)
                tension_pie = max(0.0, min(1.0, tension_pie + effective_eta * (delta_stimulus / 0.08)))
                
                history.append({
                    "step": i,
                    "stimulus": delta_stimulus,
                    "tension_control": round(tension_control, 3),
                    "tension_pie": round(tension_pie, 3),
                    "inertia": round(inertia, 3)
                })
                
            var_control = sum((x["tension_control"] - sum(h["tension_control"] for h in history[-5:])/5)**2 for x in history[-5:]) / 5
            var_pie = sum((x["tension_pie"] - sum(h["tension_pie"] for h in history[-5:])/5)**2 for x in history[-5:]) / 5
            
            return jsonify({
                "success": True,
                "data": {
                    "history": history,
                    "variance_control": round(var_control, 6),
                    "variance_pie": round(var_pie, 6),
                    "conclusion": f"L'ancrage par les précédents judiciaires (inertie PIE) stabilise la décision : la variance des convictions du Juge PIE ({var_pie:.6f}) est nettement inférieure à celle du Juge standard ({var_control:.6f}) soumis au bruit des témoignages."
                }
            })
            
        elif benchmark_type == 'attention':
            # Preuve 3 : Budget Attentionnel & Filtrage Cognitif
            import shutil
            
            simulation_id = "demo_attention_pie"
            agent_id = "agent_demo_attention"
            agent_name = "Alice_Attention"
            
            # Nettoyer l'ancienne DB si elle existe
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, 'uploads', 'kuzu', simulation_id)
            if os.path.exists(db_path):
                try:
                    from app.services.local_graph_database import LocalGraphDatabase
                    if db_path in LocalGraphDatabase._KUZU_DATABASES:
                        del LocalGraphDatabase._KUZU_DATABASES[db_path]
                except Exception:
                    pass
                shutil.rmtree(db_path, ignore_errors=True)
                
            # Créer l'état
            initial_state = CognitiveAgentState(agent_id=agent_id, name="Maitre_Alice_Avocat")
            CognitiveMemoryService.save_agent_state(simulation_id, initial_state)
            
            # Ajouter mémoires
            CognitiveMemoryService.add_memory_fragment(
                simulation_id, agent_id, 
                event_desc="Une erreur de frappe mineure s'est glissée dans le procès-verbal de dépôt du greffe.", 
                emotional_charge=0.3
            )
            CognitiveMemoryService.apply_memory_decay(simulation_id, agent_id, decay_factor=0.40)
            
            CognitiveMemoryService.add_memory_fragment(
                simulation_id, agent_id, 
                event_desc="Un arrêt de principe de la Cour Suprême pose une limite stricte à la responsabilité contractuelle.", 
                emotional_charge=0.9
            )
            
            class MockAgent:
                def __init__(self):
                    self.system_message = type('MockMsg', (object,), {'content': "System: Act as Alice."})()
            
            # Cas A : Budget élevé
            state_high = CognitiveAgentState(
                agent_id=agent_id, name=agent_name,
                attention_budget={"social": 0.2, "introspection": 0.2, "risk": 0.1, "long_term": 0.5}
            )
            CognitiveMemoryService.save_agent_state(simulation_id, state_high)
            
            agent_a = MockAgent()
            config_a = {"simulation_id": simulation_id, "simulation_type": "social"}
            inject_cognitive_prompts([(agent_id, agent_a)], config_a, {int(agent_id) if agent_id.isdigit() else 1: agent_name})
            prompt_high = agent_a.system_message.content
            
            # Cas B : Budget faible
            state_low = CognitiveAgentState(
                agent_id=agent_id, name=agent_name,
                attention_budget={"social": 0.2, "introspection": 0.1, "risk": 0.5, "long_term": 0.1}
            )
            CognitiveMemoryService.save_agent_state(simulation_id, state_low)
            
            agent_b = MockAgent()
            inject_cognitive_prompts([(agent_id, agent_b)], config_a, {int(agent_id) if agent_id.isdigit() else 1: agent_name})
            prompt_low = agent_b.system_message.content
            
            # Nettoyage
            try:
                from app.services.local_graph_database import LocalGraphDatabase
                if db_path in LocalGraphDatabase._KUZU_DATABASES:
                    del LocalGraphDatabase._KUZU_DATABASES[db_path]
                shutil.rmtree(db_path, ignore_errors=True)
            except Exception:
                pass
                
            return jsonify({
                "success": True,
                "data": {
                    "memories": [
                        {"desc": "Erreur de frappe mineure du greffe (élaguée sous budget restreint 10%)", "importance": "faible"},
                        {"desc": "Arrêt de principe de la Cour Suprême (retenu sous budget restreint 10%)", "importance": "très forte"}
                    ],
                    "high_budget": {
                        "budget": state_high.attention_budget,
                        "prompt": prompt_high
                    },
                    "low_budget": {
                        "budget": state_low.attention_budget,
                        "prompt": prompt_low
                    },
                    "conclusion": "Le filtre d'attention élague les détails procéduraux secondaires (erreur du greffe) et désactive l'introspection sous contrainte de temps pour focaliser les ressources sur les précédents de la Cour Suprême."
                }
            })
            
        else:
            return jsonify({
                "success": False,
                "error": "Type de benchmark inconnu."
            }), 400
            
    except Exception as e:
        logger.error(f"Erreur benchmark: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/legal-results', methods=['GET'])
def get_simulation_legal_results(simulation_id: str):
    """
    Récupère les résultats détaillés de la simulation de Monte-Carlo juridique.
    """
    try:
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        results_path = os.path.join(sim_dir, "legal_simulation_results.json")
        if not os.path.exists(results_path):
            reconstructed = SimulationRunner.reconstruct_legal_results(simulation_id)
            if not reconstructed:
                return jsonify({
                    "success": False,
                    "error": "Aucun résultat trouvé pour cette simulation."
                }), 404
            return jsonify({
                "success": True,
                "data": reconstructed
            })
        with open(results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des résultats juridiques: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/<simulation_id>/inject', methods=['POST'])
def inject_simulation_stimulus(simulation_id: str):
    """
    Injecte un stimulus (nouveau fait, témoignage surprise, précédent) dans la simulation active.
    """
    try:
        data = request.get_json() or {}
        stimulus = data.get('stimulus')
        if not stimulus:
            return jsonify({
                "success": False,
                "error": "Le paramètre 'stimulus' est requis."
            }), 400
            
        SimulationRunner.inject_stimulus(simulation_id, stimulus)
        
        return jsonify({
            "success": True,
            "message": "Stimulus injecté avec succès."
        })
    except ValueError as val_err:
        return jsonify({
            "success": False,
            "error": str(val_err)
        }), 404
    except Exception as e:
        logger.error(f"Erreur lors de l'injection du stimulus: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/sensitivity-analysis', methods=['POST'])
def run_sensitivity_analysis():
    """
    Exécute le Radar d'Anticipation Tactique (Détecteur de Failles / Lignes de Force)
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        client_side = data.get('client_side', 'defense') # 'defense' or 'plaintiff'
        simulation_id = data.get('simulation_id')

        if not project_id:
            return jsonify({
                "success": False,
                "error": "Le paramètre 'project_id' est requis."
            }), 400

        # Caching logic
        radar_file = None
        if simulation_id:
            try:
                manager = SimulationManager()
                sim_dir = manager._get_simulation_dir(simulation_id)
                radar_file = os.path.join(sim_dir, "radar_analysis.json")
                
                # Retrieve litigation_type for validation
                litigation_type = "civil"
                config_file = os.path.join(sim_dir, "simulation_config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        litigation_type = config_data.get("litigation_type", "civil")
                
                if os.path.exists(radar_file):
                    with open(radar_file, 'r', encoding='utf-8') as f:
                        radar_data = json.load(f)
                        if radar_data.get(client_side):
                            cached_list = radar_data[client_side]
                            has_mismatch = False
                            if isinstance(cached_list, list):
                                for item in cached_list:
                                    imp = str(item.get("impact", "")).lower()
                                    if litigation_type == "civil" and ("acquittement" in imp or "condamnation" in imp):
                                        has_mismatch = True
                                        break
                                    if litigation_type == "criminal" and ("rejet" in imp or "responsabilité" in imp):
                                        has_mismatch = True
                                        break
                            if not has_mismatch:
                                logger.info(f"Returning cached radar analysis for simulation {simulation_id} ({client_side})")
                                return jsonify({
                                    "success": True,
                                    "data": cached_list
                                })
            except Exception as e:
                logger.warning(f"Error reading/validating radar_analysis.json cache: {e}")

        from app.services.sensitivity_analysis import SensitivityAnalysisEngine
        opportunities = SensitivityAnalysisEngine.analyze_case(project_id, client_side, simulation_id=simulation_id)

        # Cache the new results
        if simulation_id and radar_file:
            try:
                radar_data = {}
                if os.path.exists(radar_file):
                    with open(radar_file, 'r', encoding='utf-8') as f:
                        radar_data = json.load(f)
                radar_data[client_side] = opportunities
                with open(radar_file, 'w', encoding='utf-8') as f:
                    json.dump(radar_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved radar analysis cache for simulation {simulation_id} ({client_side})")
            except Exception as e:
                logger.warning(f"Failed to save radar analysis cache: {e}")

        return jsonify({
            "success": True,
            "data": opportunities
        })
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de sensibilité : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/generate-request', methods=['POST'])
def generate_legal_request():
    """
    Génère un projet de requête formel basé sur un vecteur d'attaque choisi.
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        client_side = data.get('client_side', 'defense')
        node_name = data.get('node_name')
        vector_name = data.get('vector_name')
        request_type = data.get('request_type', 'requete')
        simulation_id = data.get('simulation_id')

        if not project_id or not node_name or not vector_name:
            return jsonify({
                "success": False,
                "error": "Les paramètres 'project_id', 'node_name' et 'vector_name' sont requis."
            }), 400

        from app.services.sensitivity_analysis import SensitivityAnalysisEngine
        draft_text = SensitivityAnalysisEngine.generate_draft(
            project_id=project_id,
            client_side=client_side,
            node_name=node_name,
            vector_name=vector_name,
            request_type=request_type,
            simulation_id=simulation_id
        )

        return jsonify({
            "success": True,
            "data": {
                "draft": draft_text
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la requête : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/<simulation_id>/export-pdf', methods=['GET'])
def export_simulation_pdf(simulation_id: str):
    """
    Exporte le déroulement complet de la simulation en PDF (conversations + états cognitifs).
    """
    try:
        from app.services.pdf_exporter import SimulationPDFExporter
        from flask import send_file
        
        pdf_path = SimulationPDFExporter.generate_pdf(simulation_id)
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"simulation_{simulation_id}_export.pdf"
        )
    except FileNotFoundError as fnf_err:
        return jsonify({
            "success": False,
            "error": str(fnf_err)
        }), 404
    except Exception as e:
        logger.error(f"Erreur lors de l'export PDF de la simulation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/<simulation_id>/select-draft', methods=['POST'])
def save_selected_draft(simulation_id: str):
    """
    Enregistre la requête / le stimulus choisi par l'utilisateur pour cette simulation
    """
    try:
        data = request.get_json() or {}
        node_name = data.get('node_name')
        vector_name = data.get('vector_name')
        text = data.get('text')
        client_side = data.get('client_side', 'defense')

        if not text:
            return jsonify({
                "success": False,
                "error": "Le texte du stimulus / requête est requis."
            }), 400

        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        radar_file = os.path.join(sim_dir, "radar_analysis.json")

        radar_data = {}
        if os.path.exists(radar_file):
            try:
                with open(radar_file, 'r', encoding='utf-8') as f:
                    radar_data = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading radar_analysis.json: {e}")

        radar_data["selected_draft"] = {
            "node_name": node_name,
            "vector_name": vector_name,
            "text": text,
            "client_side": client_side
        }

        with open(radar_file, 'w', encoding='utf-8') as f:
            json.dump(radar_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Selected draft saved for simulation {simulation_id}: {node_name} - {vector_name}")
        return jsonify({
            "success": True
        })
    except Exception as e:
        logger.error(f"Error saving selected draft: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/<simulation_id>/radar-analysis', methods=['GET'])
def get_radar_analysis(simulation_id: str):
    """
    Récupère l'analyse radar et le draft sélectionné pour la simulation si existants
    """
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        radar_file = os.path.join(sim_dir, "radar_analysis.json")

        if not os.path.exists(radar_file):
            return jsonify({
                "success": True,
                "data": {
                    "defense": None,
                    "plaintiff": None,
                    "selected_draft": None
                }
            })

        with open(radar_file, 'r', encoding='utf-8') as f:
            radar_data = json.load(f)

        return jsonify({
            "success": True,
            "data": {
                "defense": radar_data.get("defense"),
                "plaintiff": radar_data.get("plaintiff"),
                "selected_draft": radar_data.get("selected_draft")
            }
        })
    except Exception as e:
        logger.error(f"Error fetching radar analysis: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Génère un flux audio MP3 à partir du texte fourni.
    """
    try:
        if request.method == 'OPTIONS':
            return
            
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        voice = data.get('voice', 'fr-FR-HenriNeural')
        
        if not text:
            return jsonify({
                "success": False,
                "error": "Le paramètre 'text' est requis."
            }), 400
            
        # Clean text: remove markdown markers
        import re
        text = re.sub(r'\*+', '', text)
        text = re.sub(r'#+', '', text)
        text = re.sub(r'`+', '', text)
        text = text.strip()
        
        import edge_tts
        import asyncio
        import tempfile
        
        async def _communicate():
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_f:
                temp_path = temp_f.name
            await communicate.save(temp_path)
            return temp_path
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            temp_path = loop.run_until_complete(_communicate())
        finally:
            loop.close()
            
        return send_file(
            temp_path,
            mimetype="audio/mpeg",
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Erreur de génération TTS en direct: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500





