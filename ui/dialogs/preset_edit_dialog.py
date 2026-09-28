"""
预设编辑对话框
用于编辑通用预设和专用预设
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                               QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import (LineEdit, PrimaryPushButton, PushButton,
                           MessageBox, InfoBar, InfoBarPosition, isDarkTheme)
from core.affix_catalog import AffixCatalog, normalize_name


class PresetEditDialog(QDialog):
    """预设编辑对话框"""

    # 信号
    dedicated_saved = Signal(str, str, list, list, list)
    grouped_saved = Signal(str, str, list, list, list)
    preset_saved = Signal(str, str, list)  # (preset_id, name, affixes)

    def __init__(self, vocabulary: list, preset_data: dict = None, is_general: bool = False, parent=None,
                 mode="normal", exception_vocabulary=None, inherited_vocabulary=None):
        """
        初始化对话框

        Args:
            vocabulary: 词条库列表
            preset_data: 预设数据（编辑模式）
            is_general: 是否为通用预设
            parent: 父窗口
        """
        super().__init__(parent)
        self.inherited_vocabulary = set(inherited_vocabulary or [])
        self.vocabulary = list(vocabulary)
        for value in self.inherited_vocabulary:
            if value not in self.vocabulary:
                self.vocabulary.append(value)
        self.preset_data = preset_data
        if preset_data:
            for value in preset_data.get("affixes", []):
                if value not in self.vocabulary:
                    self.vocabulary.append(value)
            imported_groups = preset_data.get("required_affix_groups")
            imported_required = (
                [member for group in imported_groups if isinstance(group, list)
                 for member in group]
                if isinstance(imported_groups, list)
                else preset_data.get("required_affixes", [])
            )
            for value in imported_required:
                if isinstance(value, str) and value not in self.vocabulary:
                    self.vocabulary.append(value)
        self.mode = mode
        self.exception_vocabulary = exception_vocabulary or []
        self.affix_catalog = AffixCatalog()
        self.required_list = None
        self.required_groups_list = None
        self.exceptions_list = None
        self.is_general = is_general
        self.is_edit_mode = preset_data is not None

        self.setWindowTitle("编辑预设" if self.is_edit_mode else "创建预设")
        self.setMinimumSize(600, 500)

        self._init_ui()
        self._load_preset_data()
        self._sync_required()
        if self.required_list is not None:
            groups = (self.preset_data or {}).get("required_affix_groups")
            required = ([a for group in groups if isinstance(group, list)
                         for a in group if isinstance(a, str)] if isinstance(groups, list)
                        else (self.preset_data or {}).get("required_affixes", []))
            for i in range(self.required_list.count()):
                item = self.required_list.item(i)
                item.setCheckState(Qt.Checked if item.text() in required else Qt.Unchecked)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 预设名称
        if not self.is_general:
            name_layout = QHBoxLayout()
            name_label = QLabel("预设名称:")
            name_label.setFixedWidth(80)
            self.name_input = LineEdit()
            self.name_input.setPlaceholderText("输入预设名称")
            name_layout.addWidget(name_label)
            name_layout.addWidget(self.name_input)
            layout.addLayout(name_layout)
        else:
            # 通用预设显示标题
            title = QLabel("通用预设词条选择")
            title.setStyleSheet("font-size: 16pt; font-weight: bold;")
            layout.addWidget(title)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setFixedWidth(80)
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索词条")
        self.search_input.textChanged.connect(self._filter_vocabulary)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 批量操作按钮
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("批量操作:"))

        self.select_all_btn = PushButton("全选")
        self.select_all_btn.setFixedWidth(80)
        self.select_all_btn.setToolTip("选择所有可见词条（受搜索过滤影响）")
        self.select_all_btn.clicked.connect(self._select_all)
        batch_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = PushButton("全不选")
        self.deselect_all_btn.setFixedWidth(80)
        self.deselect_all_btn.setToolTip("取消选择所有可见词条（受搜索过滤影响）")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        batch_layout.addWidget(self.deselect_all_btn)

        self.invert_selection_btn = PushButton("反选")
        self.invert_selection_btn.setFixedWidth(80)
        self.invert_selection_btn.setToolTip("反选所有可见词条（受搜索过滤影响）")
        self.invert_selection_btn.clicked.connect(self._invert_selection)
        batch_layout.addWidget(self.invert_selection_btn)

        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        # 词条列表
        list_label = QLabel(f"词条列表 (共 {len(self.vocabulary)} 条):")
        layout.addWidget(list_label)

        self.vocab_list = QListWidget()
        self._apply_list_stylesheet()

        # 添加词条到列表
        for vocab in self.vocabulary:
            item = QListWidgetItem(vocab)
            if vocab in self.inherited_vocabulary and vocab not in (self.preset_data or {}).get("affixes", []):
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                item.setData(Qt.UserRole + 1, True)
                item.setToolTip("来自当前启用的通用预设；可加入必须词条组，但不会复制到专用词条")
            else:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
            self.vocab_list.addItem(item)

        layout.addWidget(self.vocab_list)

        if not self.is_general:
            layout.addWidget(QLabel("候选词条：勾选后点击加入/更新组才生效（仅已选有效词条）"))
            self.required_list = QListWidget()
            self.required_list.setMaximumHeight(110)
            layout.addWidget(self.required_list)
            layout.addWidget(QLabel("必须词条组：组内满足任一词条，组与组之间都必须满足"))
            self.required_groups_list = QListWidget()
            self.required_groups_list.setMaximumHeight(120)
            self.required_groups_list.currentRowChanged.connect(self._load_group_selection)
            layout.addWidget(self.required_groups_list)
            self.group_warning_label = QLabel()
            self.group_warning_label.setWordWrap(True)
            self.group_warning_label.setStyleSheet("color: #b06a00;")
            self.group_warning_label.setVisible(False)
            layout.addWidget(self.group_warning_label)
            group_buttons = QHBoxLayout()
            add_group = PushButton("将勾选词条加入同一 OR 组")
            add_group.clicked.connect(self._add_required_group)
            family_group = PushButton("加入已验证同族候选")
            family_group.clicked.connect(self._add_family_alternatives)
            edit_group = PushButton("更新选中组")
            edit_group.clicked.connect(self._update_required_group)
            remove_group = PushButton("删除选中组")
            remove_group.clicked.connect(self._remove_required_group)
            group_buttons.addWidget(add_group)
            group_buttons.addWidget(family_group)
            group_buttons.addWidget(edit_group)
            group_buttons.addWidget(remove_group)
            group_buttons.addStretch()
            layout.addLayout(group_buttons)
            if self.mode == "deepnight":
                layout.addWidget(QLabel("黑名单例外（仅容忍，不计有效；与全局黑名单交集生效）"))
                self.exceptions_list = QListWidget()
                self.exceptions_list.setMaximumHeight(110)
                selected = (self.preset_data or {}).get("blacklist_exceptions", [])
                for text in self.exception_vocabulary:
                    item = QListWidgetItem(text)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked if text in selected else Qt.Unchecked)
                    self.exceptions_list.addItem(item)
                layout.addWidget(self.exceptions_list)

        # 统计信息
        self.count_label = QLabel("已选择: 0 条")
        self.count_label.setStyleSheet("color: #666; font-size: 12pt;")
        layout.addWidget(self.count_label)

        # 只连接更新计数，不连接排序（排序只在加载时执行一次）
        self.vocab_list.itemChanged.connect(self._update_count)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = PrimaryPushButton("保存")
        self.save_btn.clicked.connect(self._save_preset)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _apply_list_stylesheet(self):
        """根据主题应用列表样式"""
        if isDarkTheme():
            # 深色模式
            stylesheet = """
                QListWidget {
                    border: 1px solid #3d3d3d;
                    border-radius: 6px;
                    background-color: #1e1e1e;
                    outline: none;
                    padding: 4px;
                }
                QListWidget::item {
                    height: 38px;
                    padding-left: 8px;
                    color: #e0e0e0;
                    border-radius: 4px;
                    margin-bottom: 2px;
                }
                QListWidget::item:hover {
                    background-color: #2d2d2d;
                }
                QListWidget::item:selected {
                    background-color: #1a3a52;
                    color: #e0e0e0;
                }
                QListWidget::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 4px;
                    border: 1px solid #555555;
                    background-color: #2d2d2d;
                    margin-right: 12px;
                }
                QListWidget::indicator:hover {
                    border-color: #009faa;
                    background-color: #3d3d3d;
                }
                QListWidget::indicator:checked {
                    background-color: #009faa;
                    border: 1px solid #009faa;
                    image: url(":/qfluentwidgets/images/check_box_checked_white.png");
                }
                QListWidget::indicator:checked:selected {
                    background-color: #009faa;
                    border: 1px solid #009faa;
                    image: url(":/qfluentwidgets/images/check_box_checked_white.png");
                }
                QListWidget::indicator:unchecked:selected {
                    border: 1px solid #009faa;
                    background-color: #2d2d2d;
                }
            """
        else:
            # 浅色模式
            stylesheet = """
                QListWidget {
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    background-color: white;
                    outline: none;
                    padding: 4px;
                }
                QListWidget::item {
                    height: 38px;
                    padding-left: 8px;
                    color: #333;
                    border-radius: 4px;
                    margin-bottom: 2px;
                }
                QListWidget::item:hover {
                    background-color: #f5f5f5;
                }
                QListWidget::item:selected {
                    background-color: #e3f2fd;
                    color: #000;
                }
                QListWidget::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 4px;
                    border: 1px solid #c0c0c0;
                    background-color: white;
                    margin-right: 12px;
                }
                QListWidget::indicator:hover {
                    border-color: #009faa;
                    background-color: #f0f8ff;
                }
                QListWidget::indicator:checked {
                    background-color: #009faa;
                    border: 1px solid #009faa;
                    image: url(":/qfluentwidgets/images/check_box_checked_white.png");
                }
                QListWidget::indicator:checked:selected {
                    background-color: #009faa;
                    border: 1px solid #009faa;
                    image: url(":/qfluentwidgets/images/check_box_checked_white.png");
                }
                QListWidget::indicator:unchecked:selected {
                    border: 1px solid #009faa;
                    background-color: white;
                }
            """
        self.vocab_list.setStyleSheet(stylesheet)

    def _load_preset_data(self):
        """加载预设数据（编辑模式）"""
        if not self.preset_data:
            return

        # 设置名称
        if not self.is_general and "name" in self.preset_data:
            self.name_input.setText(self.preset_data["name"])

        # 暂时断开信号，避免加载时触发排序
        self.vocab_list.itemChanged.disconnect(self._update_count)

        # 勾选已有词条
        selected_affixes = set(self.preset_data.get("affixes", []))
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            if item.text() in selected_affixes:
                item.setCheckState(Qt.Checked)

        # 重新连接信号
        self.vocab_list.itemChanged.connect(self._update_count)

        # 更新计数和排序（只在加载时执行一次）
        self._update_count()
        self._sort_items()
        self._load_required_groups()

    def _filter_vocabulary(self, text: str):
        """过滤词条列表"""
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _update_count(self):
        """更新选择计数"""
        count = sum(1 for i in range(self.vocab_list.count())
                   if self.vocab_list.item(i).checkState() == Qt.Checked)
        self.count_label.setText(f"已选择: {count} 条")
        self._sync_required()

    @staticmethod
    def _checked_items(widget):
        if widget is None:
            return []
        return [widget.item(i).text() for i in range(widget.count())
                if widget.item(i).checkState() == Qt.Checked]

    def _sync_required(self):
        if self.required_list is None:
            return
        selected = set(self._checked_items(self.required_list)) & (
            set(self.get_selected_affixes()) | self.inherited_vocabulary
        )
        existing = {
            member for group in self._current_required_groups()
            if isinstance(group, list) for member in group if isinstance(member, str)
        }
        self.required_list.clear()
        for text in dict.fromkeys(
                self.get_selected_affixes() + list(self.inherited_vocabulary) + list(existing)):
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if text in selected else Qt.Unchecked)
            self.required_list.addItem(item)
        self._update_group_warnings()

    def _load_required_groups(self):
        if self.required_groups_list is None:
            return
        self.required_groups_list.clear()
        data = self.preset_data or {}
        groups = data.get("required_affix_groups")
        if "required_affix_groups" not in data:
            legacy = data.get("required_affixes", [])
            groups = [[a] for a in legacy] if isinstance(legacy, list) else [legacy]
        if not isinstance(groups, list):
            groups = [groups]  # Preserve malformed imports until explicitly repaired/deleted.
        for group in groups:
            item = QListWidgetItem(
                " 或 ".join(str(a) for a in group) if isinstance(group, list)
                else "无效组：" + repr(group)
            )
            item.setData(Qt.UserRole, group)
            self.required_groups_list.addItem(item)
        self._update_group_warnings()

    def _current_required_groups(self):
        if self.required_groups_list is None:
            return []
        groups = []
        for i in range(self.required_groups_list.count()):
            item = self.required_groups_list.item(i)
            value = item.data(Qt.UserRole)
            groups.append(value if value is not None else item.text())
        return groups

    def _add_required_group(self):
        selected = self._checked_items(self.required_list)
        if not selected:
            return
        item = QListWidgetItem(" 或 ".join(selected))
        item.setData(Qt.UserRole, list(selected))
        self.required_groups_list.addItem(item)
        for i in range(self.required_list.count()):
            self.required_list.item(i).setCheckState(Qt.Unchecked)
        self._update_group_warnings()

    def _load_group_selection(self, row):
        groups = self._current_required_groups()
        group = groups[row] if 0 <= row < len(groups) else []
        selected = {a for a in group if isinstance(a, str)} if isinstance(group, list) else set()
        for i in range(self.required_list.count()):
            item = self.required_list.item(i)
            item.setCheckState(Qt.Checked if item.text() in selected else Qt.Unchecked)

    def _update_required_group(self):
        row = self.required_groups_list.currentRow()
        if row < 0:
            return
        selected = self._checked_items(self.required_list)
        if not selected:
            return
        item = self.required_groups_list.item(row)
        item.setData(Qt.UserRole, list(selected))
        item.setText(" 或 ".join(selected))
        self._update_group_warnings()

    def _remove_required_group(self):
        row = self.required_groups_list.currentRow()
        if row >= 0:
            self.required_groups_list.takeItem(row)
            self._update_group_warnings()

    def _add_family_alternatives(self):
        row = self.required_groups_list.currentRow()
        if row < 0:
            return
        group = self._current_required_groups()[row]
        if not isinstance(group, list):
            return
        selected = set(self.get_selected_affixes()) | self.inherited_vocabulary
        normalized_selected = {normalize_name(name): name for name in selected}
        alternatives = {
            normalized_selected[normalize_name(name)]
            for entry in group
            for name in self.affix_catalog.alternatives(normalize_name(entry))
            if normalize_name(name) in normalized_selected
        }
        additions = sorted(alternatives - set(group))
        if additions:
            group.extend(additions)
            item = self.required_groups_list.item(row)
            item.setData(Qt.UserRole, group)
            item.setText(" 或 ".join(group))
            self._update_group_warnings()

    def _update_group_warnings(self):
        if self.required_groups_list is None:
            return
        groups = self._current_required_groups()
        if any(not isinstance(g, list) or not g or
               any(not isinstance(a, str) or not a.strip() for a in g) for g in groups):
            self._show_group_error("必须词条组格式无效，请修正或删除无效组。")
            return
        warnings = self.affix_catalog.compatibility_warnings(groups)
        if warnings:
            text = "提示：组间可能存在兼容性冲突：" + "、".join(
                f"组{left}与组{right}" for left, right in warnings
            )
            self.group_warning_label.setText(text)
            self.group_warning_label.setVisible(True)
        else:
            self.group_warning_label.clear()
            self.group_warning_label.setVisible(False)

    def _validate_required_groups(self):
        selected = set(self.get_selected_affixes()) | self.inherited_vocabulary
        for group in self._current_required_groups():
            if not isinstance(group, list) or not group:
                self._show_group_error("必须词条组格式无效：每组至少需要一个词条。")
                return False
            if any(not isinstance(member, str) or not member.strip()
                   for member in group):
                self._show_group_error("必须词条组格式无效：词条不能为空。")
                return False
            if any(member not in selected for member in group):
                self._show_group_error("必须词条组包含未选择的词条，请修正或删除该组。")
                return False
        self._show_group_error("")
        return True

    def _show_group_error(self, text):
        self.group_warning_label.setText(text)
        self.group_warning_label.setVisible(bool(text))

    def _emit_saved(self, preset_id, name, affixes):
        if self.is_general:
            self.preset_saved.emit(preset_id, name, affixes)
        else:
            groups = self._current_required_groups()
            flattened = [
                member for group in groups if isinstance(group, list)
                for member in group
            ]
            self.dedicated_saved.emit(preset_id, name, affixes,
                                      flattened,
                                      self._checked_items(self.exceptions_list))
            self.grouped_saved.emit(preset_id, name, affixes,
                                    groups,
                                    self._checked_items(self.exceptions_list))

    def _sort_items(self):
        """将已勾选的词条置顶"""
        # 暂时断开信号，避免排序时触发 itemChanged
        self.vocab_list.itemChanged.disconnect(self._update_count)

        # 收集所有项
        items = []
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            items.append((item.text(), item.checkState(),
                          bool(item.data(Qt.UserRole + 1))))

        # 排序：已勾选的在前，未勾选的在后，同类按字母排序
        items.sort(key=lambda x: (x[1] != Qt.Checked, x[0]))

        # 清空列表并重新添加
        self.vocab_list.clear()
        for text, check_state, inherited in items:
            item = QListWidgetItem(text)
            if inherited:
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                item.setData(Qt.UserRole + 1, True)
                item.setToolTip("来自当前启用的通用预设；可加入必须词条组，但不会复制到专用词条")
            else:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(check_state)
            self.vocab_list.addItem(item)

        # 重新连接信号
        self.vocab_list.itemChanged.connect(self._update_count)

    def _select_all(self):
        """全选所有可见词条"""
        self.vocab_list.itemChanged.disconnect(self._update_count)

        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            # 只选择可见的词条
            if not item.isHidden():
                item.setCheckState(Qt.Checked)

        self.vocab_list.itemChanged.connect(self._update_count)
        self._update_count()

    def _deselect_all(self):
        """取消全选所有可见词条"""
        self.vocab_list.itemChanged.disconnect(self._update_count)

        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            # 只取消选择可见的词条
            if not item.isHidden():
                item.setCheckState(Qt.Unchecked)

        self.vocab_list.itemChanged.connect(self._update_count)
        self._update_count()

    def _invert_selection(self):
        """反选所有可见词条"""
        self.vocab_list.itemChanged.disconnect(self._update_count)

        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            # 只反选可见的词条
            if not item.isHidden():
                if item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
                else:
                    item.setCheckState(Qt.Checked)

        self.vocab_list.itemChanged.connect(self._update_count)
        self._update_count()

    def _save_preset(self):
        """保存预设"""
        # 验证名称（非通用预设）
        if not self.is_general:
            name = self.name_input.text().strip()
            if not name:
                MessageBox("错误", "请输入预设名称", self).exec()
                return
        else:
            name = "通用预设"

        if not self.is_general and not self._validate_required_groups():
            return

        # 获取选中的词条（允许为空）
        selected_affixes = []
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_affixes.append(item.text())

        # 发送信号
        preset_id = self.preset_data.get("id", "") if self.preset_data else ""
        self._emit_saved(preset_id, name, selected_affixes)
        self.accept()

    def get_selected_affixes(self) -> list:
        """获取选中的词条"""
        selected = []
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def closeEvent(self, event):
        """关闭窗口时自动保存"""
        # 验证名称（非通用预设）
        if not self.is_general:
            name = self.name_input.text().strip()
            if not name:
                # 如果没有名称，询问是否放弃
                reply = MessageBox("提示", "预设名称为空，是否放弃保存？", self)
                if reply.exec():
                    event.accept()
                else:
                    event.ignore()
                return
        else:
            name = "通用预设"

        if not self.is_general and not self._validate_required_groups():
            event.ignore()
            return

        # 获取选中的词条
        selected_affixes = self.get_selected_affixes()

        if not selected_affixes:
            # 如果没有选择词条，询问是否放弃
            reply = MessageBox("提示", "未选择任何词条，是否放弃保存？", self)
            if reply.exec():
                event.accept()
            else:
                event.ignore()
            return

        # 发送保存信号
        preset_id = self.preset_data.get("id", "") if self.preset_data else ""
        self._emit_saved(preset_id, name, selected_affixes)
        event.accept()