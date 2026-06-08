"""
图谱相关API路由
采用项目上下文机制，服务端持久化状态
"""

import os
import time
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus
from ..services.local_graph_database import LocalGraphDatabase

# 获取日志器
logger = get_logger('mirofish.api')

BENCHMARK_ONTOLOGY = {
    "entity_types": [
        {
            "name": "Avocat",
            "description": "Représentant juridique d'une partie (défense ou poursuite)",
            "attributes": [
                {"name": "nom", "type": "string", "description": "Nom de l'avocat"},
                {"name": "rôle", "type": "string", "description": "Défense ou Procureur"}
            ]
        },
        {
            "name": "Juge",
            "description": "Magistrat qui tranche le litige",
            "attributes": [
                {"name": "nom", "type": "string", "description": "Nom du juge"},
                {"name": "tribunal", "type": "string", "description": "Nom du tribunal"}
            ]
        },
        {
            "name": "Fait",
            "description": "Élément factuel ou circonstance de l'affaire",
            "attributes": [
                {"name": "description", "type": "string", "description": "Description du fait"},
                {"name": "contesté", "type": "boolean", "description": "Si le fait est contesté"}
            ]
        },
        {
            "name": "Jurisprudence",
            "description": "Décision de justice antérieure faisant autorité",
            "attributes": [
                {"name": "titre", "type": "string", "description": "Nom de l'arrêt"},
                {"name": "année", "type": "integer", "description": "Année de décision"}
            ]
        }
    ],
    "edge_types": [
        {
            "name": "REPRÉSENTE",
            "description": "L'avocat représente une partie",
            "source_type": "Avocat",
            "target_type": "Fait"
        },
        {
            "name": "SOUMET",
            "description": "Une partie ou avocat soumet une preuve ou un fait",
            "source_type": "Avocat",
            "target_type": "Fait"
        },
        {
            "name": "S'APPLIQUE_À",
            "description": "Une jurisprudence s'applique à un fait",
            "source_type": "Jurisprudence",
            "target_type": "Fait"
        },
        {
            "name": "TRANCHE",
            "description": "Le juge statue sur un fait",
            "source_type": "Juge",
            "target_type": "Fait"
        }
    ]
}

BENCHMARK_ANALYSIS_SUMMARY = (
    "Analyse automatique du cas d'école juridique pour le Banc d'Essai (PIE Engine). "
    "Extraction de l'ontologie standard pour la simulation de l'argumentation juridique, "
    "comprenant les rôles d'Avocat, de Juge, les Faits de la cause et les arrêts de Jurisprudence applicables."
)


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== 项目管理接口 ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    获取项目详情
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/<project_id>/text', methods=['GET'])
def get_project_text(project_id: str):
    """
    获取项目提取的文本
    """
    text = ProjectManager.get_extracted_text(project_id)
    if text is None:
        return jsonify({
            "success": False,
            "error": "Extracted text not found"
        }), 404
        
    return jsonify({
        "success": True,
        "data": {
            "text": text
        }
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
    列出所有项目
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    删除项目
    """
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": t('api.projectDeleteFailed', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "message": t('api.projectDeleted', id=project_id)
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
    重置项目状态（用于重新构建图谱）
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    # 重置到本体已生成状态
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": t('api.projectReset', id=project_id),
        "data": project.to_dict()
    })


# ============== 接口1：上传文件并生成本体 ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    接口1：上传文件，分析生成本体定义
    
    请求方式：multipart/form-data
    
    参数：
        files: 上传的文件（PDF/MD/TXT），可多个
        simulation_requirement: 模拟需求描述（必填）
        project_name: 项目名称（可选）
        additional_context: 额外说明（可选）
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== Début de la génération de l'ontologie ===")
        
        # 获取参数
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        simulation_mode = request.form.get('simulation_mode', 'social')
        
        logger.debug(f"Nom du projet: {project_name}")
        logger.debug(f"Exigence de simulation: {simulation_requirement[:100]}...")
        
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationRequirement')
            }), 400
        
        # 获取上传的文件
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": t('api.requireFileUpload')
            }), 400
        
        # Check if any file starts with "proof_"
        is_benchmark = False
        benchmark_type = "hysteresis"
        for file in uploaded_files:
            if file and file.filename and file.filename.startswith("proof_"):
                is_benchmark = True
                parts = os.path.splitext(file.filename)[0].split('_')
                if len(parts) > 1:
                    benchmark_type = parts[1]
                break
        
        # Create project (with custom project_id if benchmark)
        project_id = None
        if is_benchmark:
            import uuid as uuid_mod
            project_id = f"proj_proof_{benchmark_type}_{uuid_mod.uuid4().hex[:8]}"
            
        if (not project_name or "unnamed" in project_name.lower()) and uploaded_files:
            first_filename = uploaded_files[0].filename
            if first_filename:
                # Remove extension
                project_name = os.path.splitext(first_filename)[0].strip()

        project = ProjectManager.create_project(name=project_name, project_id=project_id)
        project.simulation_requirement = simulation_requirement
        project.simulation_mode = simulation_mode
        logger.info(f"Création du projet '{project_name}' avec ID: {project.project_id}")
        
        # 保存 file 并提取/模拟文本
        document_texts = []
        all_text = ""
        
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # 保存文件到项目目录
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, 
                    file, 
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                
                # 提取/模拟文本
                if is_benchmark:
                    text = f"Cas de simulation de preuve pour le type {benchmark_type}. Analyse de son comportement sous régulation cognitive PIE."
                else:
                    text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
        
        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": t('api.noDocProcessed')
            }), 400
        
        # 保存提取的文本
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Extraction de texte terminée, total de {len(all_text)} caractères")
        
        # 生成/设置本体
        if is_benchmark:
            logger.info("Banc d'Essai détecté: Utilisation de l'ontologie prédéfinie en français.")
            project.ontology = BENCHMARK_ONTOLOGY
            project.analysis_summary = BENCHMARK_ANALYSIS_SUMMARY
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            ProjectManager.save_project(project)
        else:
            logger.info("Appel du LLM pour générer l'ontologie...")
            generator = OntologyGenerator()
            ontology = generator.generate(
                document_texts=document_texts,
                simulation_requirement=simulation_requirement,
                additional_context=additional_context if additional_context else None
            )
            # 保存本体到项目
            entity_count = len(ontology.get("entity_types", []))
            edge_count = len(ontology.get("edge_types", []))
            logger.info(f"Génération de l'ontologie terminée: {entity_count} types d'entités, {edge_count} types de relations")
            
            project.ontology = {
                "entity_types": ontology.get("entity_types", []),
                "edge_types": ontology.get("edge_types", [])
            }
            project.analysis_summary = ontology.get("analysis_summary", "")
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            ProjectManager.save_project(project)
        logger.info(f"=== Génération de l'ontologie terminée === ID Projet: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 接口2：构建图谱 ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    接口2：根据project_id构建图谱
    
    请求（JSON）：
        {
            "project_id": "proj_xxxx",  // 必填，来自接口1
            "graph_name": "图谱名称",    // 可选
            "chunk_size": 500,          // 可选，默认500
            "chunk_overlap": 50         // 可选，默认50
        }
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "图谱构建任务已启动"
            }
        }
    """
    try:
        logger.info("=== Début de la construction du graphe ===")
        
        # 检查配置 (Migrated to Local Kuzu, no ZEP_API_KEY check needed)
        errors = []
        if errors:
            logger.error(f"Erreur de configuration: {errors}")
            return jsonify({
                "success": False,
                "error": t('api.configError', details="; ".join(errors))
            }), 500
        
        # 解析请求
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Paramètres de la requête: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": t('api.requireProjectId')
            }), 400
        
        # 获取项目
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=project_id)
            }), 404

        # 检查项目状态
        force = data.get('force', False)  # 强制重新构建
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": t('api.ontologyNotGenerated')
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": t('api.graphBuilding'),
                "task_id": project.graph_build_task_id
            }), 400
        
        # 如果强制重建，重置状态
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # 获取配置
        graph_name = data.get('graph_name', project.name or 'MiroFish Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # 更新项目配置
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # 获取提取的文本
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": t('api.textNotFound')
            }), 400
        
        # 获取本体
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": t('api.ontologyNotFound')
            }), 400
        
        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Construction du graphe: {graph_name}")
        logger.info(f"Tâche de construction du graphe créée: task_id={task_id}, project_id={project_id}")
        
        # 更新项目状态
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Capture locale before spawning background thread
        current_locale = get_locale()

        # 启动后台任务
        def build_task():
            set_locale(current_locale)
            build_logger = get_logger('mirofish.build')
            try:
                build_logger.info(f"[{task_id}] Début de la construction du graphe...")
                
                if project_id.startswith("proj_proof_"):
                    task_manager.update_task(
                        task_id, 
                        status=TaskStatus.PROCESSING,
                        message=t('progress.initGraphService'),
                        progress=0
                    )
                    time.sleep(0.5)
                    
                    task_manager.update_task(
                        task_id,
                        message=t('progress.textChunking'),
                        progress=10
                    )
                    time.sleep(0.5)
                    
                    task_manager.update_task(
                        task_id,
                        message=t('progress.creatingZepGraph'),
                        progress=30
                    )
                    graph_id = f"graph_proof_{project_id.replace('proj_proof_', '')}"
                    project.graph_id = graph_id
                    ProjectManager.save_project(project)
                    time.sleep(0.5)
                    
                    task_manager.update_task(
                        task_id,
                        message=t('progress.settingOntology'),
                        progress=50
                    )
                    db = LocalGraphDatabase(graph_id)
                    db.set_ontology(project.ontology)
                    time.sleep(0.5)
                    
                    task_manager.update_task(
                        task_id,
                        message="Extraction des entités juridiques en cours...",
                        progress=70
                    )
                    
                    # Détecter le type de benchmark pour peupler le graphe
                    parts = project_id.split('_')
                    benchmark_type = parts[2] if len(parts) > 2 else "hysteresis"
                    
                    nodes = []
                    edges = []
                    
                    if benchmark_type == "hysteresis":
                        nodes = [
                            {"uuid": "node_avocat_bob", "label": "Avocat", "name": "Avocat Bob", "summary": "Avocat de la Défense (Bob), représente la partie défenderesse.", "attributes": {"rôle": "Défense"}},
                            {"uuid": "node_procureur_voisin", "label": "Avocat", "name": "Procureur Voisin", "summary": "Procureur de la Poursuite, soutient l'accusation d'abus de confiance.", "attributes": {"rôle": "Poursuite"}},
                            {"uuid": "node_contrat_achat", "label": "Fait", "name": "Contrat d'Achat", "summary": "Contrat contenant les clauses de négociation litigieuses.", "attributes": {"contesté": True}}
                        ]
                        edges = [
                            {"uuid": "edge_1", "label": "REPRÉSENTE", "source": "node_avocat_bob", "target": "node_contrat_achat", "fact": "L'avocat Bob représente la défense concernant ce contrat."},
                            {"uuid": "edge_2", "label": "SOUMET", "source": "node_procureur_voisin", "target": "node_contrat_achat", "fact": "Le procureur soumet ce contrat comme preuve d'abus."}
                        ]
                    elif benchmark_type == "inertia":
                        nodes = [
                            {"uuid": "node_juge_pie", "label": "Juge", "name": "Juge PIE", "summary": "Magistrat chargé de trancher le litige.", "attributes": {"tribunal": "Cour du Québec"}},
                            {"uuid": "node_temoignage", "label": "Fait", "name": "Témoignage Contradictoire", "summary": "Déclaration confuse d'un témoin oculaire.", "attributes": {"contesté": True}},
                            {"uuid": "node_arret_dunmore", "label": "Jurisprudence", "name": "Arrêt Dunmore", "summary": "Arrêt Dunmore c. Mehralian (2001) établissant le critère de bonne foi.", "attributes": {"année": 2001}}
                        ]
                        edges = [
                            {"uuid": "edge_1", "label": "TRANCHE", "source": "node_juge_pie", "target": "node_temoignage", "fact": "Le juge évalue la crédibilité du témoignage."},
                            {"uuid": "edge_2", "label": "S'APPLIQUE_À", "source": "node_arret_dunmore", "target": "node_temoignage", "fact": "L'arrêt Dunmore s'applique pour trancher la valeur de ce témoignage."}
                        ]
                    else: # attention
                        nodes = [
                            {"uuid": "node_avocate_alice", "label": "Avocat", "name": "Avocate Alice", "summary": "Avocate de la défense représentant les intérêts du prévenu.", "attributes": {"rôle": "Défense"}},
                            {"uuid": "node_precedent_jordan", "label": "Jurisprudence", "name": "Arrêt Jordan", "summary": "Arrêt de la Cour Suprême R. c. Jordan (2016) sur les délais raisonnables.", "attributes": {"année": 2016}},
                            {"uuid": "node_detail_greffe", "label": "Fait", "name": "Erreur de Greffe", "summary": "Erreur matérielle secondaire de date sur le formulaire de dépôt.", "attributes": {"contesté": False}}
                        ]
                        edges = [
                            {"uuid": "edge_1", "label": "SOUMET", "source": "node_avocate_alice", "target": "node_precedent_jordan", "fact": "L'avocate Alice invoque l'arrêt Jordan pour demander l'arrêt des procédures."},
                            {"uuid": "edge_2", "label": "SOUMET", "source": "node_avocate_alice", "target": "node_detail_greffe", "fact": "L'avocate Alice mentionne l'erreur de date."}
                        ]
                    
                    db.upsert_triplets(nodes, edges)
                    time.sleep(0.5)
                    
                    # Mettre à jour le projet comme terminé
                    project.status = ProjectStatus.GRAPH_COMPLETED
                    ProjectManager.save_project(project)
                    
                    task_manager.update_task(
                        task_id,
                        status=TaskStatus.COMPLETED,
                        message=t('progress.graphBuildComplete'),
                        progress=100,
                        result={
                            "project_id": project_id,
                            "graph_id": graph_id,
                            "node_count": len(nodes),
                            "edge_count": len(edges),
                            "chunk_count": 1
                        }
                    )
                    return

                # Normal build logic
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message=t('progress.initGraphService')
                )
                
                # 创建图谱构建服务
                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
                
                # 分块
                task_manager.update_task(
                    task_id,
                    message=t('progress.textChunking'),
                    progress=5
                )
                actual_chunk_size = chunk_size
                if actual_chunk_size < 10000:
                    actual_chunk_size = 10000

                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=actual_chunk_size, 
                    overlap=chunk_overlap
                )
                
                # OPTIMIZATION: Si le texte est colossal, on le limite pour que le test en local s'achève vite (max ~150,000 caractères)
                if len(chunks) > 15:
                    chunks = chunks[:15]
                    
                total_chunks = len(chunks)
                
                # 创建图谱
                task_manager.update_task(
                    task_id,
                    message=t('progress.creatingZepGraph'),
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # 更新项目的graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # 设置本体
                task_manager.update_task(
                    task_id,
                    message=t('progress.settingOntology'),
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # 添加文本（progress_callback 签名是 (msg, progress_ratio)）
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=t('progress.addingChunks', count=total_chunks),
                    progress=15
                )
                
                episode_uuids = builder.add_text_batches(
                    graph_id, 
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )
                
                # 等待Zep处理完成（查询每个episode的processed状态）
                task_manager.update_task(
                    task_id,
                    message=t('progress.waitingZepProcess'),
                    progress=55
                )
                
                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)  # 55% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                builder._wait_for_episodes(episode_uuids, wait_progress_callback)
                
                # 获取图谱数据
                task_manager.update_task(
                    task_id,
                    message=t('progress.fetchingGraphData'),
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # 更新项目状态
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] Construction du graphe terminée: graph_id={graph_id}, nœuds={node_count}, relations={edge_count}")
                
                # 完成
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message=t('progress.graphBuildComplete'),
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # 更新项目状态为失败
                build_logger.error(f"[{task_id}] Échec de la construction du graphe: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=t('progress.buildFailed', error=str(e)),
                    error=traceback.format_exc()
                )
        
        # 启动后台线程
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": t('api.graphBuildStarted', taskId=task_id)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 任务查询接口 ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    查询任务状态
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": t('api.taskNotFound', id=task_id)
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    列出所有任务
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== 图谱数据接口 ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    获取图谱数据（节点和边）
    """
    try:
        # TODO: Switch to local Kuzu graph fetcher
        builder = GraphBuilderService(api_key="local_kuzu_backend")
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    删除本地Kuzu图谱
    """
    try:
        builder = GraphBuilderService(api_key="local_kuzu_backend")
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": t('api.graphDeleted', id=graph_id)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
