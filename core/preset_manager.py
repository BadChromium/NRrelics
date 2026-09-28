"""
预设管理器
负责预设的CRUD操作、持久化和词条库加载
"""

import json
import os
import uuid
from typing import Dict, List, Optional
from core.utils import get_resource_path, get_user_data_path, log_debug



# 预设类型常量
PRESET_TYPE_NORMAL_WHITELIST = "normal_whitelist"
PRESET_TYPE_DEEPNIGHT_WHITELIST = "deepnight_whitelist"
PRESET_TYPE_DEEPNIGHT_BLACKLIST = "deepnight_blacklist"


class PresetManager:
    """预设管理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        # presets.json 是用户数据，需读写
        self.presets_file = get_user_data_path(os.path.join(data_dir, "presets.json"))

        # 预设存储结构
        self.normal_general = None
        self.deepnight_general = None
        self.normal_dedicated = {}
        self.deepnight_whitelist_dedicated = {}
        self.deepnight_blacklist = None

        # 词条库缓存
        self._vocab_cache = {}

        # 加载预设
        self.load_presets()

    def load_presets(self):
        """从文件加载预设"""
        if not os.path.exists(self.presets_file):
            # 初始化默认预设
            self._initialize_default_presets()
            self.save_presets()
            return

        try:
            with open(self.presets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.normal_general = data.get("normal_general")
            self.deepnight_general = data.get("deepnight_general")
            self.normal_dedicated = data.get("normal_dedicated", {})
            self.deepnight_whitelist_dedicated = data.get("deepnight_whitelist_dedicated", {})
            self.deepnight_blacklist = data.get("deepnight_blacklist")

        except Exception as e:
            log_debug(f"[错误] 加载预设失败: {e}")
            self._initialize_default_presets()

    def save_presets(self):
        """保存预设到文件"""
        data = {
            "version": "1.0",
            "normal_general": self.normal_general,
            "deepnight_general": self.deepnight_general,
            "normal_dedicated": self.normal_dedicated,
            "deepnight_whitelist_dedicated": self.deepnight_whitelist_dedicated,
            "deepnight_blacklist": self.deepnight_blacklist
        }

        os.makedirs(self.data_dir, exist_ok=True)

        try:
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_debug(f"[错误] 保存预设失败: {e}")

    def _initialize_default_presets(self):
        """初始化默认预设"""
        # 普通模式通用预设
        self.normal_general = {
            "id": "normal_general",
            "name": "普通通用预设",
            "type": PRESET_TYPE_NORMAL_WHITELIST,
            "affixes": [],
            "is_general": True,
            "is_active": True
        }

        # 深夜模式通用预设
        self.deepnight_general = {
            "id": "deepnight_general",
            "name": "深夜通用预设",
            "type": PRESET_TYPE_DEEPNIGHT_WHITELIST,
            "affixes": [],
            "is_general": True,
            "is_active": True
        }

        # 深夜黑名单预设
        self.deepnight_blacklist = {
            "id": "deepnight_blacklist",
            "name": "深夜黑名单",
            "type": PRESET_TYPE_DEEPNIGHT_BLACKLIST,
            "affixes": [],
            "is_general": False,
            "is_active": True
        }

    def load_vocabulary(self, preset_type: str, for_editing: bool = True) -> List[str]:
        """
        加载词条库

        Args:
            preset_type: 预设类型
            for_editing: 是否用于编辑（True=仅加载常规词条，False=加载完整词条库）

        Returns:
            词条列表（已清洗）
        """
        # 生成缓存键（区分编辑和识别）
        cache_key = f"{preset_type}_{'edit' if for_editing else 'full'}"

        # 检查缓存
        if cache_key in self._vocab_cache:
            return self._vocab_cache[cache_key]

        # 确定词条库文件
        if preset_type == PRESET_TYPE_NORMAL_WHITELIST:
            # 编辑模式：只加载normal.txt
            # 识别模式：加载normal.txt + normal_special.txt
            files = ["normal.txt"] if for_editing else ["normal.txt", "normal_special.txt"]
        elif preset_type == PRESET_TYPE_DEEPNIGHT_WHITELIST:
            files = ["deepnight_pos.txt"]
        elif preset_type == PRESET_TYPE_DEEPNIGHT_BLACKLIST:
            files = ["deepnight_neg.txt"]
        else:
            return []

        vocabulary = []
        for filename in files:
            # 词条库是静态资源，只读
            filepath = get_resource_path(os.path.join(self.data_dir, filename))
            if not os.path.exists(filepath):
                log_debug(f"[警告] 词条库文件不存在: {filepath}")
                continue

            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # 支持两种格式：行号→词条 或 直接词条
                    if '→' in line:
                        entry = line.split('→', 1)[1].strip()
                    else:
                        entry = line

                    # 不清洗词条，保留原始格式（包括【】等特殊符号）
                    if entry:
                        vocabulary.append(entry)

        # 缓存
        self._vocab_cache[cache_key] = vocabulary
        return vocabulary

    # ==================== 通用预设操作 ====================

    def get_general_preset(self, mode: str) -> Optional[Dict]:
        """获取通用预设"""
        if mode == "normal":
            return self.normal_general
        elif mode == "deepnight":
            return self.deepnight_general
        return None

    def update_general_preset(self, mode: str, affixes: List[str]):
        """更新通用预设的词条"""
        if mode == "normal":
            self.normal_general["affixes"] = affixes
        elif mode == "deepnight":
            self.deepnight_general["affixes"] = affixes
        self.save_presets()

    # ==================== 专用预设操作 ====================

    def get_dedicated_presets(self, mode: str) -> Dict[str, Dict]:
        """获取专用预设列表"""
        if mode == "normal":
            return self.normal_dedicated
        elif mode == "deepnight":
            return self.deepnight_whitelist_dedicated
        return {}

    def get_active_dedicated_presets(self, mode: str) -> List[Dict]:
        """获取激活的专用预设列表"""
        presets = self.get_dedicated_presets(mode)
        return [p for p in presets.values() if p.get("is_active", True)]

    def create_dedicated_preset(self, mode: str, name: str, affixes: List[str],
                                required_affixes=None, blacklist_exceptions=None,
                                required_affix_groups=None) -> str:
        """
        创建专用预设

        Returns:
            预设ID
        """
        # 检查数量限制
        presets = self.get_dedicated_presets(mode)
        if len(presets) >= 20:
            raise ValueError("专用预设数量已达上限（20个）")

        grouped_supplied = required_affix_groups is not None
        if required_affix_groups is None:
            required_affixes = list(required_affixes or [])
            required_affix_groups = [[a] for a in required_affixes]
        else:
            required_affix_groups = self._validate_required_groups(required_affix_groups)
            required_affixes = [a for group in required_affix_groups for a in group]
        allowed_affixes = set(affixes) | self._active_general_affixes(mode)
        if not set(required_affixes) <= allowed_affixes:
            raise ValueError("必须词条必须属于有效词条")
        blacklist_exceptions = list(blacklist_exceptions or []) if mode == "deepnight" else []
        # 创建预设
        preset_id = str(uuid.uuid4())
        preset_type = PRESET_TYPE_NORMAL_WHITELIST if mode == "normal" else PRESET_TYPE_DEEPNIGHT_WHITELIST

        preset = {
            "id": preset_id,
            "name": name,
            "type": preset_type,
            "affixes": list(affixes),
            "required_affixes": required_affixes,
            "blacklist_exceptions": blacklist_exceptions,
            "is_general": False,
            "is_active": True
        }
        if grouped_supplied:
            preset["required_affix_groups"] = required_affix_groups

        if mode == "normal":
            self.normal_dedicated[preset_id] = preset
        elif mode == "deepnight":
            self.deepnight_whitelist_dedicated[preset_id] = preset

        self.save_presets()
        return preset_id

    def update_dedicated_preset(self, mode: str, preset_id: str, name: str = None, affixes: List[str] = None,
                                required_affixes=None, blacklist_exceptions=None,
                                required_affix_groups=None):
        """更新专用预设"""
        presets = self.get_dedicated_presets(mode)

        if preset_id not in presets:
            raise ValueError(f"预设不存在: {preset_id}")

        preset = presets[preset_id]
        useful = list(affixes) if affixes is not None else preset["affixes"]
        grouped_existing = "required_affix_groups" in preset
        if required_affix_groups is not None:
            groups = self._validate_required_groups(required_affix_groups)
            required = [a for group in groups for a in group]
        elif required_affixes is not None:
            required = list(required_affixes)
            groups = [[a] for a in required]
        elif grouped_existing:
            groups = self._validate_required_groups(preset.get("required_affix_groups"))
            required = [a for group in groups for a in group]
        else:
            required = (list(preset.get("required_affixes", [])) if affixes is None else
                        [a for a in preset.get("required_affixes", []) if a in useful])
            groups = [[a] for a in required]
        allowed_affixes = set(useful) | self._active_general_affixes(mode)
        if (required_affix_groups is not None or required_affixes is not None or
                affixes is not None) and not set(required) <= allowed_affixes:
            raise ValueError("必须词条必须属于有效词条")
        if name is not None:
            preset["name"] = name
        preset["affixes"] = useful
        preset["required_affixes"] = required
        if (required_affix_groups is not None or grouped_existing or
                "required_affix_groups" in preset):
            preset["required_affix_groups"] = groups
        if blacklist_exceptions is not None:
            preset["blacklist_exceptions"] = list(blacklist_exceptions) if mode == "deepnight" else []

        self.save_presets()

    @staticmethod
    def _validate_required_groups(groups):
        if not isinstance(groups, list):
            raise ValueError("必须词条组格式无效")
        result = []
        for group in groups:
            if not isinstance(group, list) or not group:
                raise ValueError("必须词条组不能为空")
            if not all(isinstance(entry, str) and entry for entry in group):
                raise ValueError("必须词条组包含无效词条")
            result.append(list(dict.fromkeys(group)))
        return result

    def _active_general_affixes(self, mode: str) -> set:
        general = self.get_general_preset(mode)
        if not general or not general.get("is_active", True):
            return set()
        affixes = general.get("affixes", [])
        return set(affixes) if isinstance(affixes, list) else set()

    def delete_dedicated_preset(self, mode: str, preset_id: str):
        """删除专用预设"""
        presets = self.get_dedicated_presets(mode)

        if preset_id in presets:
            del presets[preset_id]
            self.save_presets()

    def toggle_preset_active(self, mode: str, preset_id: str):
        """切换预设激活状态"""
        presets = self.get_dedicated_presets(mode)

        if preset_id in presets:
            presets[preset_id]["is_active"] = not presets[preset_id].get("is_active", True)
            self.save_presets()

    def move_preset(self, mode: str, preset_id: str, direction: str):
        """
        移动预设位置

        Args:
            mode: 预设模式 ("normal" 或 "deepnight")
            preset_id: 预设ID
            direction: 移动方向 ("up" 或 "down")
        """
        presets = self.get_dedicated_presets(mode)
        preset_ids = list(presets.keys())

        if preset_id not in preset_ids:
            return

        current_index = preset_ids.index(preset_id)

        if direction == "up" and current_index > 0:
            # 交换位置
            preset_ids[current_index], preset_ids[current_index - 1] = preset_ids[current_index - 1], preset_ids[current_index]
        elif direction == "down" and current_index < len(preset_ids) - 1:
            # 交换位置
            preset_ids[current_index], preset_ids[current_index + 1] = preset_ids[current_index + 1], preset_ids[current_index]
        else:
            return

        # 重建预设字典以保持新的顺序
        new_presets = {}
        for pid in preset_ids:
            new_presets[pid] = presets[pid]

        if mode == "normal":
            self.normal_dedicated = new_presets
        elif mode == "deepnight":
            self.deepnight_whitelist_dedicated = new_presets

        self.save_presets()

    # ==================== 黑名单预设操作 ====================

    def get_blacklist_preset(self) -> Optional[Dict]:
        """获取黑名单预设"""
        return self.deepnight_blacklist

    def update_blacklist_preset(self, affixes: List[str]):
        """更新黑名单预设的词条"""
        self.deepnight_blacklist["affixes"] = affixes
        self.save_presets()
