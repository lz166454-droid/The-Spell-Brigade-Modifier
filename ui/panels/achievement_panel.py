from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from lab.save.game_metadata import achievement_display_description, achievement_display_name, category_label, get_achievements, get_categories
from ui.i18n import tr

class CategoryComboBox(QComboBox):
    def showPopup(self) -> None:
        super().showPopup()
        popup = self.view().window()
        if popup is not None and popup is not self.window():
            popup.setMinimumWidth(max(self.width(), 140))

class AchievementPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._items_by_id: dict[int, QTreeWidgetItem] = {}
        self._categories: dict[str, QTreeWidgetItem] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        header = QHBoxLayout()
        self._title = QLabel(self)
        self._title.setObjectName('sectionTitle')
        self._summary = QLabel('', self)
        self._summary.setObjectName('statValue')
        header.addWidget(self._title)
        header.addStretch(1)
        header.addWidget(self._summary)
        root.addLayout(header)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._category = CategoryComboBox(self)
        self._category.setObjectName('categoryCombo')
        self._category.setMaxVisibleItems(12)
        self._category.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._category.setMinimumContentsLength(6)
        self._category.view().setMinimumWidth(140)
        self._category.currentIndexChanged.connect(self._apply_filter)
        self._search = QLineEdit(self)
        self._search.textChanged.connect(self._apply_filter)
        self._unlock_all_btn = QPushButton(self)
        self._unlock_all_btn.setObjectName('secondaryBtn')
        self._unlock_all_btn.clicked.connect(self._on_unlock_all)
        filter_row.addWidget(self._category)
        filter_row.addWidget(self._search, 1)
        filter_row.addWidget(self._unlock_all_btn)
        root.addLayout(filter_row)
        self._tree = QTreeWidget(self)
        self._tree.setObjectName('achievementTree')
        self._tree.setHeaderHidden(True)
        self._tree.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._tree, 1)
        self._vm = None
        self._build_tree()
        self.retranslate_ui()

    def _build_tree(self) -> None:
        for meta in get_achievements():
            if meta.category not in self._categories:
                parent = QTreeWidgetItem([category_label(meta.category)])
                parent.setFlags(Qt.ItemFlag.ItemIsEnabled)
                parent.setData(0, Qt.ItemDataRole.UserRole, meta.category)
                self._tree.addTopLevelItem(parent)
                self._categories[meta.category] = parent
            item = QTreeWidgetItem([achievement_display_name(meta)])
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, meta.id)
            item.setToolTip(0, achievement_display_description(meta))
            self._categories[meta.category].addChild(item)
            self._items_by_id[meta.id] = item
        self._tree.expandAll()

    def _rebuild_category_combo(self) -> None:
        current = self._category.currentData()
        self._category.blockSignals(True)
        self._category.clear()
        self._category.addItem(tr('achievement.all_categories'), '')
        for category in get_categories():
            self._category.addItem(category_label(category), category)
        if current is not None:
            index = self._category.findData(current)
            if index >= 0:
                self._category.setCurrentIndex(index)
        self._category.blockSignals(False)

    def _update_tree_labels(self) -> None:
        self._tree.blockSignals(True)
        try:
            for meta in get_achievements():
                item = self._items_by_id.get(meta.id)
                if item is not None:
                    item.setText(0, achievement_display_name(meta))
                    item.setToolTip(0, achievement_display_description(meta))
            for category, parent in self._categories.items():
                parent.setText(0, category_label(category))
        finally:
            self._tree.blockSignals(False)

    def bind(self, view_model) -> None:
        self._vm = view_model

    def retranslate_ui(self) -> None:
        self._title.setText(tr('achievement.title'))
        self._search.setPlaceholderText(tr('achievement.search_placeholder'))
        self._unlock_all_btn.setText(tr('achievement.unlock_all'))
        self._rebuild_category_combo()
        self._update_tree_labels()
        self.refresh()

    def refresh(self) -> None:
        if self._vm is None:
            return
        data = self._vm.get_save_data()
        if data is None:
            return
        self._tree.blockSignals(True)
        try:
            self._updating = True
            for achievement_id, item in self._items_by_id.items():
                progress = data.challenges.get(achievement_id)
                if progress is None:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                    continue
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(0, Qt.CheckState.Checked if progress.is_completed else Qt.CheckState.Unchecked)
        finally:
            self._updating = False
            self._tree.blockSignals(False)
        self._update_summary()
        self._apply_filter()

    def _apply_filter(self) -> None:
        category = self._category.currentData()
        keyword = self._search.text().strip().lower()
        for index in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(index)
            parent_category = parent.data(0, Qt.ItemDataRole.UserRole)
            category_match = not category or parent_category == category
            visible_children = 0
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                name = child.text(0).lower()
                text_match = not keyword or keyword in name
                visible = category_match and text_match
                child.setHidden(not visible)
                if visible:
                    visible_children += 1
            parent.setHidden(not category_match or visible_children == 0)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating or self._vm is None or column != 0:
            return
        achievement_id = item.data(0, Qt.ItemDataRole.UserRole)
        if achievement_id is None or not item.parent():
            return
        data = self._vm.get_save_data()
        if data is None or int(achievement_id) not in data.challenges:
            return
        unlocked = item.checkState(0) == Qt.CheckState.Checked
        self._vm.set_achievement(int(achievement_id), unlocked)
        self._update_summary()

    def _update_summary(self) -> None:
        if self._vm is None:
            return
        data = self._vm.get_save_data()
        if data is None:
            return
        completed = sum(1 for item in data.challenges.values() if item.is_completed)
        self._summary.setText(tr('achievement.summary', completed=completed, total=len(data.challenges)))

    def _on_unlock_all(self) -> None:
        if self._vm is None:
            return
        self._vm.unlock_all_achievements()
        self.refresh()
