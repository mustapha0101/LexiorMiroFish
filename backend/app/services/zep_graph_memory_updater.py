"""
本地图谱记忆更新服务 (Formerly Zep)
将模拟中的Agent活动动态更新到Kuzu图谱中
"""

import os
import time
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_locale, set_locale

from .local_graph_extractor import LocalGraphExtractor
from .local_graph_database import LocalGraphDatabase

logger = get_logger('mirofish.zep_graph_memory_updater')

@dataclass
class AgentActivity:
    """Agent活动记录"""
    platform: str
    agent_id: int
    agent_name: str
    action_type: str
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str
    
    def to_episode_text(self) -> str:
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }
        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()
        return f"{self.agent_name}: {description}"
    
    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"发布了一条帖子：「{content}」"
        return "发布了一条帖子"
    def _describe_like_post(self) -> str:
        return "点赞了一条帖子"
    def _describe_dislike_post(self) -> str:
        return "踩了一条帖子"
    def _describe_repost(self) -> str:
        return "转发了一条帖子"
    def _describe_quote_post(self) -> str:
        return "引用了一条帖子"
    def _describe_follow(self) -> str:
        return "关注了一个用户"
    def _describe_create_comment(self) -> str:
        content = self.action_args.get("content", "")
        return f"评论道：「{content}」"
    def _describe_like_comment(self) -> str:
        return "点赞了一条评论"
    def _describe_dislike_comment(self) -> str:
        return "踩了一条评论"
    def _describe_search(self) -> str:
        return "进行了搜索"
    def _describe_search_user(self) -> str:
        return "搜索了用户"
    def _describe_mute(self) -> str:
        return "屏蔽了一个用户"
    def _describe_generic(self) -> str:
        return f"执行了{self.action_type}操作"


class ZepGraphMemoryUpdater:
    """
    ZepGraphMemoryUpdater (Now Local Kuzu backed)
    监控模拟的actions日志文件，将其转换为文本并通过LLM更新图谱
    """
    BATCH_SIZE = 5
    PLATFORM_DISPLAY_NAMES = {'twitter': '世界1', 'reddit': '世界2'}
    SEND_INTERVAL = 0.5
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        self.graph_id = graph_id
        # Ignore API key since we're local
        self.extractor = LocalGraphExtractor()
        
        self._activity_queue: Queue = Queue()
        self._platform_buffers: Dict[str, List[AgentActivity]] = {'twitter': [], 'reddit': []}
        self._buffer_lock = threading.Lock()
        
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        self._total_activities = 0
        self._total_sent = 0
        self._total_items_sent = 0
        self._failed_count = 0
        self._skipped_count = 0
        
    def _get_platform_display_name(self, platform: str) -> str:
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)
    
    def start(self):
        if self._running:
            return
        current_locale = get_locale()
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, args=(current_locale,), daemon=True)
        self._worker_thread.start()
    
    def stop(self):
        self._running = False
        self._flush_remaining()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
    
    def add_activity(self, activity: AgentActivity):
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        self._activity_queue.put(activity)
        self._total_activities += 1
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        if "event_type" in data:
            return
        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        self.add_activity(activity)
    
    def _worker_loop(self, locale: str = 'zh'):
        set_locale(locale)
        # Dummy ontology so NER finds standard entities if no custom ontology is present
        dummy_ontology = {"entity_types": [{"name": "Person"}, {"name": "Concept"}], "edge_types": [{"name": "INTERACTS_WITH"}]}
        
        while self._running or not self._activity_queue.empty():
            try:
                try:
                    activity = self._activity_queue.get(timeout=1)
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)
                        
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            self._send_batch_activities(batch, platform, dummy_ontology)
                            time.sleep(self.SEND_INTERVAL)
                except Empty:
                    pass
            except Exception as e:
                logger.error(f"Error in ZepGraphMemoryUpdater worker loop: {e}")
                time.sleep(1)
    
    def _send_batch_activities(self, activities: List[AgentActivity], platform: str, dummy_ontology: Dict):
        if not activities:
            return
        combined_text = "\n".join([a.to_episode_text() for a in activities])
        
        for attempt in range(self.MAX_RETRIES):
            try:
                nodes, edges = self.extractor.extract_triplets(combined_text, dummy_ontology)
                if nodes or edges:
                    with LocalGraphDatabase(self.graph_id) as db:
                        db.upsert_triplets(nodes, edges)
                
                self._total_sent += 1
                self._total_items_sent += len(activities)
                return
            except Exception as e:
                logger.error(f"Error sending batch activities to graph {self.graph_id}: {e}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
        self._failed_count += 1
    
    def _flush_remaining(self):
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break
        
        try:
            dummy_ontology = {"entity_types": [{"name": "Person"}, {"name": "Concept"}], "edge_types": [{"name": "INTERACTS_WITH"}]}
            with self._buffer_lock:
                for platform, buffer in self._platform_buffers.items():
                    if buffer:
                        self._send_batch_activities(buffer, platform, dummy_ontology)
        except Exception as e:
            logger.warning(f"Error during graph memory flush_remaining: {e}")
        finally:
            with self._buffer_lock:
                for platform in self._platform_buffers:
                    self._platform_buffers[platform] = []
    
    def get_stats(self) -> Dict[str, Any]:
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        return {
            "graph_id": self.graph_id,
            "batches_sent": self._total_sent,
            "failed_count": self._failed_count,
            "buffer_sizes": buffer_sizes,
        }

class ZepGraphMemoryManager:
    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
            updater = ZepGraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def stop_updater(cls, simulation_id: str):
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                
    _stop_all_done = False
    
    @classmethod
    def stop_all(cls):
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        
        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    updater.stop()
                cls._updaters.clear()
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        return {sim_id: updater.get_stats() for sim_id, updater in cls._updaters.items()}
