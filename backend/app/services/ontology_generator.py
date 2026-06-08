"""
本体生成服务
接口1：分析文本内容，生成适合社会模拟的实体和关系类型定义
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient
from ..utils.locale import get_language_instruction

logger = logging.getLogger(__name__)


def _to_pascal_case(name: str) -> str:
    """将任意格式的名称转换为 PascalCase（如 'works_for' -> 'WorksFor', 'person' -> 'Person'）"""
    # 按非字母数字字符分割
    parts = re.split(r'[^a-zA-Z0-9]+', name)
    # 再按 camelCase 边界分割（如 'camelCase' -> ['camel', 'Case']）
    words = []
    for part in parts:
        words.extend(re.sub(r'([a-z])([A-Z])', r'\1_\2', part).split('_'))
    # 每个词首字母大写，过滤空串
    result = ''.join(word.capitalize() for word in words if word)
    return result if result else 'Unknown'


# Prompt système pour la génération de l'ontologie
ONTOLOGY_SYSTEM_PROMPT = """Tu es un expert en conception d'ontologies pour les graphes de connaissances. Ta tâche est d'analyser le contenu textuel et les besoins de la simulation fournis, puis de concevoir des types d'entités et de relations adaptés pour une **simulation d'opinion sur les réseaux sociaux**.

**IMPORTANT : Tu dois renvoyer UNIQUEMENT des données au format JSON valide. Aucun autre texte n'est autorisé.**

## Contexte Principal

Nous développons un **système de simulation d'opinion sur les réseaux sociaux**. Dans ce système :
- Chaque entité est un "compte" ou "sujet" capable de s'exprimer, d'interagir et de propager des informations sur les réseaux sociaux.
- Les entités s'influencent mutuellement, partagent, commentent et répondent.
- Nous devons simuler les réactions et les parcours de diffusion de l'information de diverses parties lors d'un événement d'opinion publique.

Par conséquent, **les entités doivent être des acteurs réels capables de publier et d'interagir sur les réseaux sociaux** :

**CE QUI EST AUTORISÉ** :
- Individus spécifiques (personnalités publiques, personnes impliquées, leaders d'opinion, experts, gens ordinaires)
- Entreprises, sociétés (y compris leurs comptes officiels)
- Organisations (universités, associations, ONG, syndicats, etc.)
- Départements gouvernementaux, agences de régulation
- Médias (journaux, chaînes TV, médias indépendants, sites web)
- Les plateformes de réseaux sociaux elles-mêmes
- Des représentants de groupes spécifiques (ex. association d'anciens élèves, fan clubs)

**CE QUI N'EST PAS AUTORISÉ** :
- Concepts abstraits (ex. "Opinion publique", "Émotion", "Tendance")
- Sujets/Thèmes (ex. "Intégrité académique", "Réforme éducative")
- Opinions/Attitudes (ex. "Partisans", "Opposants")

## Format de Sortie

Veuillez générer un format JSON comprenant la structure suivante :

```json
{
    "entity_types": [
        {
            "name": "NomDuTypeD'Entité (Anglais, PascalCase)",
            "description": "Courte description (dans la langue requise, max 100 caractères)",
            "attributes": [
                {
                    "name": "NomDeL'Attribut (Anglais, snake_case)",
                    "type": "text",
                    "description": "Description de l'attribut"
                }
            ],
            "examples": ["ExempleEntité1", "ExempleEntité2"]
        }
    ],
    "edge_types": [
        {
            "name": "NOM_DU_TYPE_DE_RELATION (Anglais, UPPER_SNAKE_CASE)",
            "description": "Courte description (dans la langue requise, max 100 caractères)",
            "source_targets": [
                {"source": "TypeDEntitéSource", "target": "TypeDEntitéCible"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Explication brève et analyse du texte"
}
```

## Lignes Directrices (EXCELLENTEMENT IMPORTANTES !)

### 1. Conception des types d'entités - Strictement obligatoire

**Quantité requise : Doit être EXACTEMENT 10 types d'entités**

**Structure hiérarchique obligatoire (inclut des types spécifiques et des types de secours généraux)** :

Les 10 types d'entités doivent contenir la hiérarchie suivante :

A. **Types de Secours (OBLIGATOIRES, positionnés comme les 2 derniers de la liste)** :
   - `Person` : Le type de secours pour tout individu naturel. Lorsqu'une personne ne correspond à aucun autre type plus spécifique, elle est assignée ici.
   - `Organization` : Le type de secours pour toute institution. Lorsqu'une organisation ne correspond à aucun autre type plus spécifique, elle est assignée ici.

B. **Types Spécifiques (8 types, axés sur le texte fourni)** :
   - Concevez des types plus spécifiques pour les principaux acteurs mentionnés dans le texte.
   - Par exemple : Si le texte porte sur le monde académique, inclure `Student`, `Professor`, `University`.
   - Par exemple : Si le texte porte sur les affaires, inclure `Company`, `CEO`, `Employee`.

**Pourquoi utiliser des types de secours ?** :
- Le texte peut inclure des personnages marginaux comme "un enseignant du primaire", "le passant A", "un certain internaute".
- Sans un type spécifique, ils doivent se rabattre sur `Person`.
- De même, les petites structures ou groupes temporaires se rabattent sur `Organization`.

**Principes de conception pour les types spécifiques** :
- Identifier les personnages fréquents ou cruciaux.
- Chaque type spécifique doit avoir des frontières claires pour éviter les recoupements.
- La description doit clairement différencier le type de secours et le type spécifique.

### 2. Conception des types de relations (Edges)

- Quantité : 6 à 10 types.
- Les relations doivent refléter des interactions réelles sur les réseaux sociaux.
- Assurez-vous que source_targets couvrent les types d'entités définis.

### 3. Conception des attributs

- 1 à 3 attributs clés par type d'entité.
- **Attention** : Les noms d'attributs NE PEUVENT PAS être `name`, `uuid`, `group_id`, `created_at`, `summary` (mots réservés du système).
- Recommandations : `full_name`, `title`, `role`, `position`, `location`, `description`.

## Référence pour les Types d'Entités

**Individus (Spécifiques)** :
- Student: Étudiant
- Professor: Professeur/Universitaire
- Journalist: Journaliste
- Celebrity: Célébrité/Influenceur
- Executive: Cadre/Dirigeant
- Official: Représentant gouvernemental
- Lawyer: Avocat
- Doctor: Médecin

**Individus (Secours)** :
- Person: Tout individu ne correspondant pas aux cas ci-dessus.

**Organisations (Spécifiques)** :
- University: Université
- Company: Entreprise/Société
- GovernmentAgency: Agence gouvernementale
- MediaOutlet: Agence de presse/Média
- Hospital: Hôpital
- School: École/Établissement
- NGO: Organisation Non-Gouvernementale

**Organisations (Secours)** :
- Organization: Toute organisation ne correspondant pas aux cas ci-dessus.

## Référence pour les Types de Relations

- WORKS_FOR: Travaille pour
- STUDIES_AT: Étudie à
- AFFILIATED_WITH: Affilié à
- REPRESENTS: Représente
- REGULATES: Réglemente
- REPORTS_ON: Couvre/Rapporte sur
- COMMENTS_ON: Commente
- RESPONDS_TO: Répond à
- SUPPORTS: Soutient
- OPPOSES: S'oppose à
- COLLABORATES_WITH: Collabore avec
- COMPETES_WITH: Est en concurrence avec
"""


class OntologyGenerator:
    """
    本体生成器
    分析文本内容，生成实体和关系类型定义
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成本体定义
        
        Args:
            document_texts: 文档文本列表
            simulation_requirement: 模拟需求描述
            additional_context: 额外上下文
            
        Returns:
            本体定义（entity_types, edge_types等）
        """
        # 构建用户消息
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        lang_instruction = get_language_instruction()
        system_prompt = f"{ONTOLOGY_SYSTEM_PROMPT}\n\n{lang_instruction}\nIMPORTANT: Entity type names MUST be in English PascalCase (e.g., 'PersonEntity', 'MediaOrganization'). Relationship type names MUST be in English UPPER_SNAKE_CASE (e.g., 'WORKS_FOR'). Attribute names MUST be in English snake_case. Only description fields and analysis_summary should use the specified language above."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 调用LLM
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=8192
        )
        
        # 验证和后处理
        result = self._validate_and_process(result)
        
        return result
    
    # 传给 LLM 的文本最大长度（缩减到 5000 字母以保证本地大模型近乎瞬间完成，如同云端演示例）
    MAX_TEXT_LENGTH_FOR_LLM = 5000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """构建用户消息"""
        
        # 合并文本
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # 如果文本超过5万字，截断（仅影响传给LLM的内容，不影响图谱构建）
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(原文共{original_length}字，已截取前{self.MAX_TEXT_LENGTH_FOR_LLM}字用于本体分析)..."
        
        message = f"""## 模拟需求

{simulation_requirement}

## 文档内容

{combined_text}
"""
        
        if additional_context:
            message += f"""
## 额外说明

{additional_context}
"""
        
        message += """
请根据以上内容，设计适合社会舆论模拟的实体类型和关系类型。

**必须遵守的规则**：
1. 必须正好输出10个实体类型
2. 最后2个必须是兜底类型：Person（个人兜底）和 Organization（组织兜底）
3. 前8个是根据文本内容设计的具体类型
4. 所有实体类型必须是现实中可以发声的主体，不能是抽象概念
5. 属性名不能使用 name、uuid、group_id 等保留字，用 full_name、org_name 等替代
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证和后处理结果"""
        
        # 确保必要字段存在
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # 验证实体类型
        # 记录原始名称到 PascalCase 的映射，用于后续修正 edge 的 source_targets 引用
        entity_name_map = {}
        valid_entities = []
        for entity in result["entity_types"]:
            if not isinstance(entity, dict) or not entity.get("name") or not isinstance(entity["name"], str) or not entity["name"].strip():
                logger.warning(f"Removing invalid entity definition from ontology: {entity}")
                continue
            original_name = entity["name"]
            entity["name"] = _to_pascal_case(original_name)
            if entity["name"] != original_name:
                logger.warning(f"Entity type name '{original_name}' auto-converted to '{entity['name']}'")
            entity_name_map[original_name] = entity["name"]
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # 确保description不超过100字符
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
            valid_entities.append(entity)
        result["entity_types"] = valid_entities
        
        # 验证关系类型
        valid_edges = []
        for edge in result["edge_types"]:
            if not isinstance(edge, dict) or not edge.get("name") or not isinstance(edge["name"], str) or not edge["name"].strip():
                logger.warning(f"Removing invalid edge definition from ontology: {edge}")
                continue
            original_name = edge["name"]
            edge["name"] = original_name.upper()
            if edge["name"] != original_name:
                logger.warning(f"Edge type name '{original_name}' auto-converted to '{edge['name']}'")
            # 修正 source_targets 中的实体名称引用，与转换后的 PascalCase 保持一致
            for st in edge.get("source_targets", []):
                if st.get("source") in entity_name_map:
                    st["source"] = entity_name_map[st["source"]]
                if st.get("target") in entity_name_map:
                    st["target"] = entity_name_map[st["target"]]
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
            valid_edges.append(edge)
        result["edge_types"] = valid_edges
        
        # Zep API 限制：最多 10 个自定义实体类型，最多 10 个自定义边类型
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10

        # 去重：按 name 去重，保留首次出现的
        seen_names = set()
        deduped = []
        for entity in result["entity_types"]:
            name = entity.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                deduped.append(entity)
            elif name in seen_names:
                logger.warning(f"Duplicate entity type '{name}' removed during validation")
        result["entity_types"] = deduped

        # 兜底类型定义
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }
        
        # 检查是否已有兜底类型
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names
        
        # 需要添加的兜底类型
        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)
        
        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            
            # 如果添加后会超过 10 个，需要移除一些现有类型
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                # 计算需要移除多少个
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                # 从末尾移除（保留前面更重要的具体类型）
                result["entity_types"] = result["entity_types"][:-to_remove]
            
            # 添加兜底类型
            result["entity_types"].extend(fallbacks_to_add)
        
        # 最终确保不超过限制（防御性编程）
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        将本体定义转换为Python代码（类似ontology.py）
        
        Args:
            ontology: 本体定义
            
        Returns:
            Python代码字符串
        """
        code_lines = [
            '"""',
            '自定义实体类型定义',
            '由MiroFish自动生成，用于社会舆论模拟',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== 实体类型定义 ==============',
            '',
        ]
        
        # 生成实体类型
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== 关系类型定义 ==============')
        code_lines.append('')
        
        # 生成关系类型
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # 转换为PascalCase类名
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # 生成类型字典
        code_lines.append('# ============== 类型配置 ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # 生成边的source_targets映射
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)

