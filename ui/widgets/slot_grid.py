from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget
from ui.i18n import tr

class SlotGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._cells: list[QFrame] = []
        self._gold_labels: list[QLabel] = []
        self._gold_captions: list[QLabel] = []
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for index in range(10):
            cell = QFrame(self)
            cell.setObjectName('slotCell')
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(8, 6, 8, 6)
            cell_layout.setSpacing(6)
            index_label = QLabel(f'#{index}', cell)
            index_label.setObjectName('slotIndex')
            index_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            gold_caption = QLabel(cell)
            gold_caption.setObjectName('slotGoldCaption')
            gold_caption.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            gold_label = QLabel('—', cell)
            gold_label.setObjectName('slotGold')
            gold_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            cell_layout.addWidget(index_label)
            cell_layout.addWidget(gold_caption)
            cell_layout.addStretch(1)
            cell_layout.addWidget(gold_label)
            row = index // 5
            col = index % 5
            layout.addWidget(cell, row, col)
            self._cells.append(cell)
            self._gold_captions.append(gold_caption)
            self._gold_labels.append(gold_label)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        caption = tr('slot.gold')
        for label in self._gold_captions:
            label.setText(caption)

    def update_slots(self, summaries, active_slot: int) -> None:
        for summary in summaries:
            index = summary.index
            if index >= len(self._cells):
                continue
            cell = self._cells[index]
            gold_label = self._gold_labels[index]
            if not summary.exists:
                cell.setObjectName('slotCell')
                gold_label.setText('—')
                gold_label.setObjectName('slotGold')
            else:
                is_active = index == active_slot
                cell.setObjectName('slotCellActive' if is_active else 'slotCell')
                gold_label.setText(f'{summary.gold:,}')
                gold_label.setObjectName('slotGoldActive' if is_active else 'slotGold')
            cell.style().unpolish(cell)
            cell.style().polish(cell)
            gold_label.style().unpolish(gold_label)
            gold_label.style().polish(gold_label)
