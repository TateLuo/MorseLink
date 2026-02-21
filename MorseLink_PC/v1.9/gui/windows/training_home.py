from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from morselink.training.engine import TrainingEngine
from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from ui_widgets import FluentIcon as FIF
from ui_widgets import PushButton

from gui.windows.training_rx_runner import TrainingRxRunner
from gui.windows.training_tutorial import TrainingTutorialPage
from gui.windows.training_tx_runner import TrainingTxRunner


STAGE_LABELS = {
    1: "\u5165\u95e8",
    2: "\u521d\u7ea7",
    3: "\u4e2d\u7ea7",
    4: "\u719f\u7ec3",
}
TUTORIAL_DONE_KEY = "Training/tutorial_done"


class TrainingHome(QWidget):
    """Stage/Unit training home with short closed-loop sessions."""

    def __init__(self, stackedWidget, context=None):
        super().__init__()
        self.context = context
        self.stackedWidget = stackedWidget

        self.config_manager = self.context.config_manager if self.context else ConfigManager()
        if self.context and hasattr(self.context, "create_database_tool"):
            self.db_tool = self.context.create_database_tool()
        else:
            self.db_tool = DatabaseTool()

        self.engine = TrainingEngine(db_tool=self.db_tool, config_manager=self.config_manager)
        self.engine.set_callbacks(
            on_task=self._on_task,
            on_state=self._on_state,
            on_finish=self._on_finish,
        )

        self._dashboard: dict = {}
        self._active_task = None
        self._last_finish_payload: dict | None = None
        self._selected_stage_id: int | None = None
        self._unit_buttons: list[QPushButton] = []
        self._stage_buttons: dict[int, QPushButton] = {}
        self._tutorial_done = bool(self.config_manager.get_value(TUTORIAL_DONE_KEY, False, bool))
        self._tutorial_skip_session = bool(self._tutorial_done)

        self._init_ui()
        self._refresh_dashboard()

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.page_stack = QStackedWidget(self)
        root.addWidget(self.page_stack)

        self._init_tutorial_page()
        self._init_map_page()
        self._init_runner_page()
        self._init_summary_page()

        if self._tutorial_done:
            self.page_stack.setCurrentWidget(self.page_map)
        else:
            self.page_stack.setCurrentWidget(self.page_tutorial)

    def _init_tutorial_page(self) -> None:
        self.page_tutorial = TrainingTutorialPage(
            context=self.context,
            on_exit=self._on_tutorial_exit,
            parent=self.page_stack,
        )
        self.page_stack.addWidget(self.page_tutorial)

    def _init_map_page(self) -> None:
        self.page_map = QWidget(self)
        layout = QVBoxLayout(self.page_map)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        self.label_panel_title = QLabel(self.tr("阶段选择"), self.page_map)
        self.label_panel_title.setObjectName("mapPageTitle")
        layout.addWidget(self.label_panel_title)

        self.map_panel = QWidget(self.page_map)
        self.map_panel.setObjectName("mapPanel")
        panel_layout = QVBoxLayout(self.map_panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.stage_chip_row = QWidget(self.map_panel)
        self.stage_chip_row.setObjectName("stageChipRow")
        stage_switch_row = QHBoxLayout(self.stage_chip_row)
        stage_switch_row.setContentsMargins(0, 0, 0, 0)
        stage_switch_row.setSpacing(8)
        for stage in self.engine.stage_defs:
            button = PushButton(self._stage_label(stage.stage_id), self.stage_chip_row)
            button.setObjectName("stageChip")
            button.clicked.connect(lambda _=False, sid=stage.stage_id: self._select_stage(sid))
            stage_switch_row.addWidget(button)
            self._stage_buttons[int(stage.stage_id)] = button
        stage_switch_row.addStretch(1)
        top_row.addWidget(self.stage_chip_row, 1)

        self.btn_start_training = PushButton(FIF.PLAY, self.tr("开始训练"), self.map_panel)
        self.btn_start_training.setObjectName("primaryStartButton")
        self.btn_start_training.clicked.connect(self.start_training)
        top_row.addWidget(self.btn_start_training)

        self.btn_open_tutorial = PushButton(FIF.SEARCH, self.tr("新手教学"), self.map_panel)
        self.btn_open_tutorial.setObjectName("tutorialButton")
        self.btn_open_tutorial.setCursor(Qt.PointingHandCursor)
        self.btn_open_tutorial.clicked.connect(self.open_tutorial)
        top_row.addWidget(self.btn_open_tutorial)
        panel_layout.addLayout(top_row)

        self.label_stage_title = QLabel(self.tr("入门课程"), self.map_panel)
        self.label_stage_title.setObjectName("stageTitle")
        panel_layout.addWidget(self.label_stage_title)

        self.label_stage_subtitle = QLabel(self.tr(""), self.map_panel)
        self.label_stage_subtitle.setObjectName("stageSubtitle")
        self.label_stage_subtitle.setWordWrap(True)
        panel_layout.addWidget(self.label_stage_subtitle)

        self.overview_card = QWidget(self.map_panel)
        self.overview_card.setObjectName("overviewCard")
        overview_layout = QVBoxLayout(self.overview_card)
        overview_layout.setContentsMargins(12, 10, 12, 10)
        overview_layout.setSpacing(8)

        self.label_stage_progress = QLabel(self.tr("当前进度：0 / 0"), self.overview_card)
        self.label_stage_progress.setObjectName("stageProgress")
        overview_layout.addWidget(self.label_stage_progress)

        self.label_objective = QLabel(self.tr("目标：-"), self.overview_card)
        self.label_objective.setObjectName("stageObjective")
        self.label_objective.setWordWrap(True)
        overview_layout.addWidget(self.label_objective)

        self.label_added = QLabel(self.tr("新增字符：无"), self.overview_card)
        self.label_added.setObjectName("stageAdded")
        overview_layout.addWidget(self.label_added)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(8)
        self.metric_progress_value = self._create_metric_tile(metric_row, self.tr("完成 Unit"), "0/0")
        self.metric_streak_value = self._create_metric_tile(metric_row, self.tr("连续天数"), "0")
        self.metric_xp_value = self._create_metric_tile(metric_row, self.tr("总 XP"), "0")
        self.metric_unlock_value = self._create_metric_tile(metric_row, self.tr("本 Unit 新增"), "-")
        overview_layout.addLayout(metric_row)

        panel_layout.addWidget(self.overview_card)

        self.unit_board = QWidget(self.map_panel)
        self.unit_board.setObjectName("unitBoard")
        unit_board_layout = QVBoxLayout(self.unit_board)
        unit_board_layout.setContentsMargins(10, 10, 10, 10)
        unit_board_layout.setSpacing(8)

        self.label_course_title = QLabel(self.tr("课程 Unit"), self.unit_board)
        self.label_course_title.setObjectName("unitBoardTitle")
        unit_board_layout.addWidget(self.label_course_title)

        self.unit_grid_widget = QWidget(self.unit_board)
        self.unit_grid = QGridLayout(self.unit_grid_widget)
        self.unit_grid.setContentsMargins(0, 0, 0, 0)
        self.unit_grid.setHorizontalSpacing(8)
        self.unit_grid.setVerticalSpacing(8)
        unit_board_layout.addWidget(self.unit_grid_widget)
        panel_layout.addWidget(self.unit_board)

        self.daily_bar = QWidget(self.map_panel)
        self.daily_bar.setObjectName("dailyBar")
        daily_layout = QHBoxLayout(self.daily_bar)
        daily_layout.setContentsMargins(10, 8, 10, 8)
        daily_layout.setSpacing(8)

        self.label_daily = QLabel(self.tr("今天目标：完成 3 个 Unit（0/3）"), self.daily_bar)
        self.label_daily.setObjectName("dailyGoal")
        daily_layout.addWidget(self.label_daily, 1)

        self.btn_continue_learning = PushButton(self.tr("继续学习"), self.daily_bar)
        self.btn_continue_learning.setObjectName("continueButton")
        self.btn_continue_learning.clicked.connect(self.start_training)
        daily_layout.addWidget(self.btn_continue_learning)
        panel_layout.addWidget(self.daily_bar)

        self.label_map_hint = QLabel(self.tr("点击 Unit 卡片可开始训练。"), self.map_panel)
        self.label_map_hint.setObjectName("mapHint")
        self.label_map_hint.setWordWrap(True)
        panel_layout.addWidget(self.label_map_hint)

        self.label_next_stage_hint = QLabel(self.tr("下一阶段尚未解锁。"), self.map_panel)
        self.label_next_stage_hint.setObjectName("nextStageHint")
        panel_layout.addWidget(self.label_next_stage_hint)

        layout.addWidget(self.map_panel)
        layout.addStretch(1)

        self._apply_map_styles()
        self.page_stack.addWidget(self.page_map)

    def _create_metric_tile(self, row: QHBoxLayout, title: str, value: str) -> QLabel:
        tile = QWidget(self.overview_card)
        tile.setObjectName("metricTile")
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(10, 6, 10, 6)
        tile_layout.setSpacing(0)

        value_label = QLabel(value, tile)
        value_label.setObjectName("metricValue")
        tile_layout.addWidget(value_label)

        title_label = QLabel(title, tile)
        title_label.setObjectName("metricTitle")
        tile_layout.addWidget(title_label)

        row.addWidget(tile, 1)
        return value_label

    def _apply_map_styles(self) -> None:
        self.page_map.setStyleSheet(
            """
            QLabel#mapPageTitle {
                font-size: 17px;
                font-weight: 700;
                color: #1d2944;
                padding-left: 4px;
            }
            QWidget#mapPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f5f8fd,
                    stop: 1 #edf3fb
                );
                border: 1px solid #d7e3f4;
                border-radius: 12px;
            }
            QWidget#stageChipRow {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid #d4e1f2;
                border-radius: 20px;
            }
            QPushButton#primaryStartButton {
                color: #ffffff;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4f9cff,
                    stop: 1 #2f73e6
                );
                border: 1px solid #2f73e6;
                border-radius: 16px;
                min-height: 32px;
                padding: 0 16px;
                font-weight: 700;
            }
            QPushButton#primaryStartButton:hover {
                background: #3b84ee;
            }
            QPushButton#tutorialButton {
                color: #2b4c76;
                background: #ffffff;
                border: 1px solid #c4d4ea;
                border-radius: 16px;
                min-height: 32px;
                padding: 0 14px;
                font-weight: 600;
            }
            QPushButton#tutorialButton:hover {
                background: #eef4ff;
                border-color: #9dbde6;
            }
            QLabel#stageTitle {
                font-size: 16px;
                font-weight: 700;
                color: #23385b;
            }
            QLabel#stageSubtitle {
                color: #5f708d;
            }
            QWidget#overviewCard {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid #d8e3f3;
                border-radius: 10px;
            }
            QLabel#stageProgress {
                font-size: 13px;
                font-weight: 600;
                color: #21375b;
            }
            QLabel#stageObjective, QLabel#stageAdded {
                color: #3f5375;
            }
            QWidget#metricTile {
                background: #f7faff;
                border: 1px solid #dbe6f5;
                border-radius: 8px;
            }
            QLabel#metricValue {
                font-size: 16px;
                font-weight: 700;
                color: #1d4fa9;
            }
            QLabel#metricTitle {
                color: #657796;
                font-size: 12px;
            }
            QWidget#unitBoard {
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid #d8e3f3;
                border-radius: 10px;
            }
            QLabel#unitBoardTitle {
                color: #2a3f62;
                font-weight: 700;
            }
            QWidget#dailyBar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #e8f3ff,
                    stop: 1 #d9ebff
                );
                border: 1px solid #bfd9f8;
                border-radius: 10px;
            }
            QLabel#dailyGoal {
                color: #244573;
                font-weight: 600;
            }
            QPushButton#continueButton {
                color: #ffffff;
                background: #3d87ec;
                border: 1px solid #2f73e6;
                border-radius: 14px;
                min-height: 28px;
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton#continueButton:hover {
                background: #2f73e6;
            }
            QLabel#mapHint {
                color: #445b7e;
                padding-left: 2px;
            }
            QLabel#nextStageHint {
                color: #7d8ca3;
                font-size: 12px;
                padding-left: 2px;
            }
            """
        )

    def _init_runner_page(self) -> None:
        self.page_runner = QWidget(self)
        layout = QVBoxLayout(self.page_runner)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        header_card = QWidget(self.page_runner)
        header_card.setObjectName("runnerHeaderCard")
        header = QHBoxLayout(header_card)
        header.setContentsMargins(12, 10, 12, 10)
        header.setSpacing(10)

        self.label_runner_title = QLabel(self.tr("训练进行中"), header_card)
        self.label_runner_title.setObjectName("runnerTitle")
        header.addWidget(self.label_runner_title)

        self.label_runner_status = QLabel(self.tr("准备就绪"), header_card)
        self.label_runner_status.setObjectName("runnerStatus")
        header.addWidget(self.label_runner_status)
        header.addStretch(1)

        self.btn_stop = PushButton(FIF.PAUSE, self.tr("停止"), header_card)
        self.btn_stop.setObjectName("runnerStopButton")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_training)
        header.addWidget(self.btn_stop)
        layout.addWidget(header_card)

        objective_card = QWidget(self.page_runner)
        objective_card.setObjectName("runnerObjectiveCard")
        objective_layout = QVBoxLayout(objective_card)
        objective_layout.setContentsMargins(12, 8, 12, 8)
        self.label_runner_objective = QLabel(self.tr("目标："), objective_card)
        self.label_runner_objective.setObjectName("runnerObjective")
        self.label_runner_objective.setWordWrap(True)
        objective_layout.addWidget(self.label_runner_objective)
        layout.addWidget(objective_card)

        body_card = QWidget(self.page_runner)
        body_card.setObjectName("runnerBodyCard")
        body_layout = QVBoxLayout(body_card)
        body_layout.setContentsMargins(8, 8, 8, 8)

        self.runner_stack = QStackedWidget(body_card)
        self.rx_runner = TrainingRxRunner(context=self.context, parent=self.runner_stack)
        self.tx_runner = TrainingTxRunner(context=self.context, parent=self.runner_stack)
        self.runner_stack.addWidget(self.rx_runner)
        self.runner_stack.addWidget(self.tx_runner)
        body_layout.addWidget(self.runner_stack)
        layout.addWidget(body_card, 1)

        self._apply_runner_styles()
        self.page_stack.addWidget(self.page_runner)

    def _apply_runner_styles(self) -> None:
        self.page_runner.setStyleSheet(
            """
            QWidget#runnerHeaderCard, QWidget#runnerObjectiveCard, QWidget#runnerBodyCard {
                background: #f5f8fd;
                border: 1px solid #d7e2f2;
                border-radius: 12px;
            }
            QLabel#runnerTitle {
                color: #1e2f4a;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#runnerStatus {
                background: #eaf2ff;
                color: #2f5e9b;
                border: 1px solid #b8d0f2;
                border-radius: 12px;
                padding: 3px 10px;
                font-weight: 600;
            }
            QPushButton#runnerStopButton {
                background: #ffffff;
                color: #3a4e6c;
                border: 1px solid #c6d3e7;
                border-radius: 8px;
                min-height: 32px;
                padding: 0 14px;
                font-weight: 600;
            }
            QPushButton#runnerStopButton:hover {
                background: #f1f5fb;
            }
            QLabel#runnerObjective {
                color: #395274;
                font-weight: 600;
            }
            """
        )

    def _init_summary_page(self) -> None:
        self.page_summary = QWidget(self)
        layout = QVBoxLayout(self.page_summary)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        self.summary_panel = QWidget(self.page_summary)
        self.summary_panel.setObjectName("summaryPanel")
        panel_layout = QVBoxLayout(self.summary_panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)

        hero_card = QWidget(self.summary_panel)
        hero_card.setObjectName("summaryHeroCard")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(12)

        self.label_summary_check = QLabel("✓", hero_card)
        self.label_summary_check.setObjectName("summaryCheckIcon")
        self.label_summary_check.setAlignment(Qt.AlignCenter)
        self.label_summary_check.setFixedSize(56, 56)
        hero_layout.addWidget(self.label_summary_check, 0, Qt.AlignTop)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)
        self.label_summary_title = QLabel(self.tr("Unit 完成"), hero_card)
        self.label_summary_title.setObjectName("summaryTitle")
        hero_text.addWidget(self.label_summary_title)

        self.label_summary_objective = QLabel(self.tr("目标："), hero_card)
        self.label_summary_objective.setObjectName("summaryObjective")
        self.label_summary_objective.setWordWrap(True)
        hero_text.addWidget(self.label_summary_objective)
        hero_layout.addLayout(hero_text, 1)
        panel_layout.addWidget(hero_card)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        accuracy_card = QWidget(self.summary_panel)
        accuracy_card.setObjectName("summaryMetricCard")
        accuracy_layout = QHBoxLayout(accuracy_card)
        accuracy_layout.setContentsMargins(14, 12, 14, 12)
        accuracy_layout.setSpacing(12)

        self.label_summary_ring = QLabel("0%", accuracy_card)
        self.label_summary_ring.setObjectName("summaryRing")
        self.label_summary_ring.setAlignment(Qt.AlignCenter)
        self.label_summary_ring.setFixedSize(116, 116)
        accuracy_layout.addWidget(self.label_summary_ring, 0, Qt.AlignVCenter)

        accuracy_text = QVBoxLayout()
        accuracy_text.setSpacing(6)
        self.label_summary_accuracy = QLabel(self.tr("准确率：0.0%"), accuracy_card)
        self.label_summary_accuracy.setObjectName("summaryMetricPrimary")
        accuracy_text.addWidget(self.label_summary_accuracy)

        self.label_summary_rhythm = QLabel(self.tr("节奏评分：0.0"), accuracy_card)
        self.label_summary_rhythm.setObjectName("summaryMetricSecondary")
        accuracy_text.addWidget(self.label_summary_rhythm)

        self.label_summary_grade = QLabel(self.tr("评级：C"), accuracy_card)
        self.label_summary_grade.setObjectName("summaryGrade")
        accuracy_text.addWidget(self.label_summary_grade)
        accuracy_text.addStretch(1)
        accuracy_layout.addLayout(accuracy_text, 1)
        stats_row.addWidget(accuracy_card, 1)

        reward_card = QWidget(self.summary_panel)
        reward_card.setObjectName("summaryMetricCard")
        reward_layout = QVBoxLayout(reward_card)
        reward_layout.setContentsMargins(14, 12, 14, 12)
        reward_layout.setSpacing(8)

        self.label_summary_xp = QLabel(self.tr("XP +0"), reward_card)
        self.label_summary_xp.setObjectName("summaryXp")
        reward_layout.addWidget(self.label_summary_xp)

        self.label_summary_combo = QLabel(self.tr("连击 +0"), reward_card)
        self.label_summary_combo.setObjectName("summaryCombo")
        reward_layout.addWidget(self.label_summary_combo)
        reward_layout.addStretch(1)
        stats_row.addWidget(reward_card, 1)

        panel_layout.addLayout(stats_row)

        action_card = QWidget(self.summary_panel)
        action_card.setObjectName("summaryActionCard")
        action_row = QHBoxLayout(action_card)
        action_row.setContentsMargins(14, 12, 14, 12)
        action_row.setSpacing(10)

        self.btn_continue = PushButton(FIF.PLAY, self.tr("继续下一个"), action_card)
        self.btn_continue.setObjectName("summaryPrimaryBtn")
        self.btn_continue.setCursor(Qt.PointingHandCursor)
        self.btn_continue.clicked.connect(self._continue_next_unit)
        action_row.addWidget(self.btn_continue)

        self.btn_retry = PushButton(FIF.SYNC, self.tr("再练一次"), action_card)
        self.btn_retry.setObjectName("summarySecondaryBtn")
        self.btn_retry.setCursor(Qt.PointingHandCursor)
        self.btn_retry.clicked.connect(self._retry_current_unit)
        action_row.addWidget(self.btn_retry)
        panel_layout.addWidget(action_card)

        self.label_summary_stage = QLabel("", self.summary_panel)
        self.label_summary_stage.setObjectName("summaryHint")
        self.label_summary_stage.setWordWrap(True)
        panel_layout.addWidget(self.label_summary_stage)

        layout.addWidget(self.summary_panel)
        layout.addStretch(1)

        self._apply_summary_styles()
        self.page_stack.addWidget(self.page_summary)

    def _apply_summary_styles(self) -> None:
        self.page_summary.setStyleSheet(
            """
            QWidget#summaryPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f5f8fd,
                    stop: 1 #edf3fb
                );
                border: 1px solid #d7e3f4;
                border-radius: 12px;
            }
            QWidget#summaryHeroCard, QWidget#summaryMetricCard, QWidget#summaryActionCard {
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid #d8e3f3;
                border-radius: 10px;
            }
            QLabel#summaryCheckIcon {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #dff8f1,
                    stop: 1 #c8efe6
                );
                border: 2px solid #78d1bb;
                border-radius: 28px;
                color: #24a888;
                font-size: 30px;
                font-weight: 700;
            }
            QLabel#summaryTitle {
                color: #1c2f4d;
                font-size: 36px;
                font-weight: 700;
            }
            QLabel#summaryObjective {
                color: #435a7c;
                font-size: 18px;
                font-weight: 600;
            }
            QLabel#summaryRing {
                background: #ffffff;
                border: 10px solid #f36d79;
                border-radius: 58px;
                color: #2e3b4f;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#summaryMetricPrimary {
                color: #243755;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#summaryMetricSecondary {
                color: #586f91;
                font-size: 20px;
                font-weight: 600;
            }
            QLabel#summaryGrade {
                color: #2f4770;
                font-size: 22px;
                font-weight: 700;
                padding: 2px 8px;
                background: #f7f0d6;
                border: 1px solid #ecd38b;
                border-radius: 8px;
                max-width: 132px;
            }
            QLabel#summaryXp {
                color: #2a3a52;
                font-size: 34px;
                font-weight: 800;
            }
            QLabel#summaryCombo {
                color: #4b6285;
                font-size: 24px;
                font-weight: 600;
            }
            QPushButton#summaryPrimaryBtn {
                color: #ffffff;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #5fd0d8,
                    stop: 1 #3193ee
                );
                border: 1px solid #2f89dd;
                border-radius: 22px;
                min-height: 44px;
                padding: 0 28px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#summaryPrimaryBtn:hover {
                background: #3ea1e8;
            }
            QPushButton#summarySecondaryBtn {
                color: #2f69bc;
                background: #edf4ff;
                border: 1px solid #bdd1ef;
                border-radius: 22px;
                min-height: 44px;
                padding: 0 28px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#summarySecondaryBtn:hover {
                background: #dfebff;
            }
            QLabel#summaryHint {
                color: #3f5678;
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid #d8e3f3;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 15px;
                font-weight: 600;
            }
            """
        )

    def _summary_ring_style(self, accuracy: float) -> None:
        border_color = "#f36d79"
        if accuracy >= 90.0:
            border_color = "#49c18d"
        elif accuracy >= 75.0:
            border_color = "#f1b550"
        self.label_summary_ring.setStyleSheet(
            "QLabel#summaryRing {"
            "background: #ffffff; "
            f"border: 10px solid {border_color}; "
            "border-radius: 58px; "
            "color: #2e3b4f; font-size: 26px; font-weight: 700; }"
        )

    def open_tutorial(self) -> None:
        self.page_tutorial.load_default_selection()
        self.page_stack.setCurrentWidget(self.page_tutorial)

    def _on_tutorial_exit(self, completed: bool) -> None:
        if completed:
            self._tutorial_done = True
            self.config_manager.set_value(TUTORIAL_DONE_KEY, True)
            self.config_manager.sync()
        else:
            self._tutorial_skip_session = True
        self._refresh_dashboard()
        self.page_stack.setCurrentWidget(self.page_map)

    def _select_stage(self, stage_id: int) -> None:
        unlocked_max = int(self._dashboard.get("unlocked_stage_max", 1))
        if int(stage_id) > unlocked_max:
            self.label_map_hint.setText(self.tr("该阶段尚未解锁。"))
            return
        self._selected_stage_id = int(stage_id)
        self._refresh_dashboard()

    def _stage_label(self, stage_id: int) -> str:
        sid = int(stage_id)
        label = STAGE_LABELS.get(sid)
        if label is not None:
            return self.tr(label)
        return f"Stage {sid}"

    def _refresh_stage_buttons(self) -> None:
        selected = int(self._dashboard.get("stage_id", 1))
        current_stage = int(self._dashboard.get("current_stage", selected))
        unlocked_max = int(self._dashboard.get("unlocked_stage_max", current_stage))

        for stage_id, button in self._stage_buttons.items():
            unlocked = stage_id <= unlocked_max
            label = self._stage_label(stage_id)
            if stage_id == current_stage:
                label += self.tr(" · 当前")
            elif not unlocked:
                label += self.tr(" · 未解锁")
            button.setText(label)
            button.setEnabled(unlocked)

            if stage_id == selected:
                button.setStyleSheet(
                    "QPushButton { "
                    "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e7f2ff,stop:1 #cfe4ff); "
                    "color: #1754b8; border: 1px solid #63a5ff; border-radius: 16px; "
                    "padding: 6px 14px; min-height: 30px; font-weight: 700; }"
                    "QPushButton:hover { background: #d8eaff; }"
                )
            elif unlocked:
                button.setStyleSheet(
                    "QPushButton { "
                    "background: #f5f7fb; color: #31415f; border: 1px solid #ced8e7; "
                    "border-radius: 16px; padding: 6px 14px; min-height: 30px; }"
                    "QPushButton:hover { background: #eaf0fa; border-color: #a9bfdc; }"
                )
            else:
                button.setStyleSheet(
                    "QPushButton, QPushButton:disabled { "
                    "background: #eff2f6; color: #9aa6b8; border: 1px solid #dde3ec; "
                    "border-radius: 16px; padding: 6px 14px; min-height: 30px; }"
                )

    def _format_added_chars(self, chars: list[str]) -> str:
        valid = [str(ch).strip().upper() for ch in chars if str(ch).strip()]
        return ", ".join(valid) if valid else self.tr("无")

    def _tr_dynamic(self, value: str) -> str:
        text = str(value or "").strip()
        return self.tr(text) if text else ""

    @staticmethod
    def _card_text(card: dict) -> str:
        title = str(card.get("title", "Unit"))
        if card.get("is_boss"):
            title = f"{title}★"
        stars = int(card.get("stars", 0))
        if stars > 0:
            return f"{title}\n{'★' * stars}"
        return title

    @staticmethod
    def _card_style(status: str) -> str:
        if status == "current":
            return (
                "QPushButton {"
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f9cff,stop:1 #2f73e6); "
                "color: #ffffff; border: 1px solid #2b6ed8; "
                "border-radius: 10px; font-weight: 700; min-height: 66px; }"
                "QPushButton:hover { background: #3a84ee; }"
            )
        if status == "completed":
            return (
                "QPushButton {"
                "background: #f3f7fd; color: #27405f; border: 1px solid #cad8eb; "
                "border-radius: 10px; min-height: 66px; }"
                "QPushButton:hover { background: #e9f0fb; }"
            )
        if status == "available":
            return (
                "QPushButton {"
                "background: #ffffff; color: #2b4361; border: 1px dashed #9fb7d6; "
                "border-radius: 10px; min-height: 66px; }"
                "QPushButton:hover { background: #f3f8ff; border-color: #6f9cd2; }"
            )
        return (
            "QPushButton {"
            "background: #edf1f6; color: #a0adbf; border: 1px solid #d8e0eb; "
            "border-radius: 10px; min-height: 66px; }"
            "QPushButton:disabled { color: #a0adbf; }"
        )

    def _clear_unit_grid(self) -> None:
        while self.unit_grid.count():
            item = self.unit_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._unit_buttons = []

    def _render_unit_grid(self, cards: list[dict]) -> None:
        self._clear_unit_grid()
        if not cards:
            return

        columns = 4 if len(cards) >= 4 else max(1, len(cards))
        for idx, card in enumerate(cards):
            status = str(card.get("status", "locked"))
            title = self._card_text(card)
            if status == "locked":
                title = self.tr("锁定 | ") + title

            row = idx // columns
            col = idx % columns
            button = QPushButton(title, self.unit_grid_widget)
            button.setStyleSheet(self._card_style(status))
            button.setToolTip(self._tr_dynamic(str(card.get("objective", ""))))

            unit_index = int(card.get("unit_index", idx + 1))
            if status == "locked":
                button.setEnabled(False)
            else:
                button.setCursor(Qt.PointingHandCursor)
                button.clicked.connect(lambda _=False, u=unit_index: self._start_unit(u))

            self.unit_grid.addWidget(button, row, col)
            self._unit_buttons.append(button)

    def _refresh_dashboard(self) -> None:
        self._dashboard = self.engine.get_dashboard(stage_id=self._selected_stage_id)
        self._selected_stage_id = int(self._dashboard.get("stage_id", 1))

        stage_id = int(self._dashboard.get("stage_id", 1))
        stage_label = self._stage_label(stage_id)
        stage_name = self._tr_dynamic(str(self._dashboard.get("stage_name", stage_label)))
        subtitle = self._tr_dynamic(str(self._dashboard.get("subtitle", "")))
        completed = int(self._dashboard.get("completed_units", 0))
        unit_total = int(self._dashboard.get("unit_total", 0))
        current_unit = int(self._dashboard.get("current_unit", 1))
        daily_goal = int(self._dashboard.get("daily_goal", 3))
        daily_done = int(self._dashboard.get("daily_units_done", 0))
        daily_done_display = max(0, min(daily_goal, daily_done))
        streak = int(self._dashboard.get("streak_days", 0))
        total_xp = int(self._dashboard.get("total_xp", 0))
        objective = self._tr_dynamic(str(self._dashboard.get("current_unit_objective", "-")))
        current_added_chars = list(self._dashboard.get("current_unit_added_chars", []))
        added_chars = self._format_added_chars(current_added_chars)
        unlock_preview = (
            "+" + "/".join([str(ch).strip().upper() for ch in current_added_chars][:3])
            if current_added_chars
            else self.tr("无")
        )

        self.label_stage_title.setText(self.tr("{0}课程").format(stage_label))
        self.label_stage_subtitle.setText(subtitle if subtitle else stage_name)
        self.label_stage_progress.setText(
            self.tr("当前进度：{0}/{1} Unit，正在学习 Unit {2}").format(completed, unit_total, current_unit)
        )
        self.label_daily.setText(
            self.tr("今天目标：完成 {0} 个 Unit（{1}/{0}） | 连续学习 {2} 天").format(
                daily_goal, daily_done_display, streak
            )
        )
        self.label_objective.setText(self.tr("目标：{0}").format(objective))
        self.label_added.setText(self.tr("新增字符：{0}").format(added_chars))
        self.label_course_title.setText(self.tr("{0} Unit 列表").format(stage_label))
        self.metric_progress_value.setText(f"{completed}/{unit_total}")
        self.metric_streak_value.setText(self.tr("{0}天").format(streak))
        self.metric_xp_value.setText(f"{total_xp}")
        self.metric_unlock_value.setText(unlock_preview)

        if daily_done >= daily_goal:
            self.btn_continue_learning.setText(self.tr("继续巩固"))
        else:
            self.btn_continue_learning.setText(self.tr("继续学习"))
        self.btn_start_training.setText(self.tr("开始训练 Unit {0}").format(current_unit))
        if self._tutorial_done:
            self.btn_open_tutorial.setText(self.tr("复习新手教学"))
        else:
            self.btn_open_tutorial.setText(self.tr("完成新手教学"))

        unlocked_stage_max = int(self._dashboard.get("unlocked_stage_max", stage_id))
        stage_total = len(self.engine.stage_defs)
        if unlocked_stage_max < stage_total:
            next_stage = self._stage_label(unlocked_stage_max + 1)
            self.label_next_stage_hint.setText(self.tr("下一阶段 {0} 尚未解锁。").format(next_stage))
        else:
            self.label_next_stage_hint.setText(self.tr("已解锁全部阶段，可继续刷星提升表现。"))

        if self._tutorial_done or self._tutorial_skip_session:
            self.label_map_hint.setText(self.tr("点击 Unit 卡片可直接开练，或使用右上角按钮从当前 Unit 开始。"))
        else:
            self.label_map_hint.setText(self.tr("建议先完成新手教学，再开始正式训练。"))

        self._refresh_stage_buttons()
        self._render_unit_grid(list(self._dashboard.get("units", [])))

    def _start_unit(self, unit_index: int) -> None:
        if not self._tutorial_done and not self._tutorial_skip_session:
            self.label_map_hint.setText(self.tr("请先完成新手教学，或在教学页选择本次跳过。"))
            self.page_stack.setCurrentWidget(self.page_tutorial)
            return
        stage_id = int(self._dashboard.get("stage_id", 1))
        started = self.engine.start_training(stage_id=stage_id, unit_index=unit_index)
        if not started:
            self.label_map_hint.setText(self.tr("该单元尚未解锁。"))
            return
        self.label_map_hint.setText(self.tr("训练进行中。"))
        self.page_stack.setCurrentWidget(self.page_runner)

    def _step_title(self, step_id: str) -> str:
        normalized = str(step_id or "").lower()
        if "rx_identify" in normalized:
            return self.tr("Rx 识别")
        if "tx_rhythm" in normalized:
            return self.tr("Tx 节奏")
        if "rx_speed" in normalized:
            return self.tr("Rx 加速")
        if "rx_boss" in normalized:
            return self.tr("Boss Rx 连续抄收")
        if "tx_boss" in normalized:
            return self.tr("Boss Tx 连续发报")
        return step_id

    def _continue_next_unit(self) -> None:
        if not self._last_finish_payload:
            self._refresh_dashboard()
            self.page_stack.setCurrentWidget(self.page_map)
            return
        next_stage = int(self._last_finish_payload.get("next_stage_id", self._dashboard.get("stage_id", 1)))
        next_unit = int(self._last_finish_payload.get("next_unit_index", self._dashboard.get("current_unit", 1)))
        self._selected_stage_id = next_stage
        if self.engine.start_training(stage_id=next_stage, unit_index=next_unit):
            self.page_stack.setCurrentWidget(self.page_runner)
            return
        self._refresh_dashboard()
        self.page_stack.setCurrentWidget(self.page_map)

    def _retry_current_unit(self) -> None:
        if not self._last_finish_payload:
            self._refresh_dashboard()
            self.page_stack.setCurrentWidget(self.page_map)
            return
        stage_id = int(self._last_finish_payload.get("stage_before", self._dashboard.get("stage_id", 1)))
        unit_index = int(self._last_finish_payload.get("unit_before", self._dashboard.get("current_unit", 1)))
        self._selected_stage_id = stage_id
        if self.engine.start_training(stage_id=stage_id, unit_index=unit_index):
            self.page_stack.setCurrentWidget(self.page_runner)
            return
        self._refresh_dashboard()
        self.page_stack.setCurrentWidget(self.page_map)

    def start_training(self) -> None:
        if not self._tutorial_done and not self._tutorial_skip_session:
            self.page_stack.setCurrentWidget(self.page_tutorial)
            return
        self._start_unit(int(self._dashboard.get("current_unit", 1)))

    def stop_training(self) -> None:
        self.rx_runner.stop_round()
        self.tx_runner.stop_round()
        self.engine.stop_training()
        self._refresh_dashboard()
        self.page_stack.setCurrentWidget(self.page_map)

    def _on_task(self, task) -> None:
        self._active_task = task
        boss_flag = self.tr(" ★") if task.is_boss else ""
        stage_label = self._stage_label(int(task.stage_id))
        self.label_runner_title.setText(
            self.tr("{0} | 单元 {1}{2}").format(
                stage_label,
                int(task.unit_index),
                boss_flag,
            )
        )
        self.label_runner_status.setText(self.tr("执行中：{0}").format(self._step_title(task.step_id)))
        self.label_runner_objective.setText(self.tr("目标：{0}").format(self._tr_dynamic(task.unit_objective)))
        self.page_stack.setCurrentWidget(self.page_runner)

        if task.mode == "rx":
            self.runner_stack.setCurrentWidget(self.rx_runner)
            self.rx_runner.start_round(task, self.engine.submit_result)
        else:
            self.runner_stack.setCurrentWidget(self.tx_runner)
            self.tx_runner.start_round(task, self.engine.submit_result)

    def _on_state(self, payload: dict) -> None:
        event = str(payload.get("event", ""))
        if event == "started":
            self.label_runner_status.setText(
                self.tr("开始单元 {0}/{1}").format(
                    int(payload.get("unit_index", 1)),
                    int(payload.get("unit_total", 1)),
                )
            )
            objective = self._tr_dynamic(str(payload.get("unit_objective", "")))
            if objective:
                self.label_runner_objective.setText(self.tr("目标：{0}").format(objective))
            return
        if event == "step_done":
            self.label_runner_status.setText(
                self.tr("已完成 {0}/{1}: {2}").format(
                    int(payload.get("step_index", 0)) + 1,
                    int(payload.get("step_total", 0)),
                    self._step_title(payload.get("step_id", "")),
                )
            )
            return
        if event == "stopped":
            self.label_runner_status.setText(self.tr("训练已停止。"))
            return
        if event == "finished":
            self.label_runner_status.setText(self.tr("单元结算完成。"))

    def _on_finish(self, payload: dict) -> None:
        self._last_finish_payload = dict(payload)
        accuracy = float(payload.get("accuracy", 0.0))
        rhythm = float(payload.get("rhythm", 0.0))
        grade = str(payload.get("grade", "C"))
        xp_base = int(payload.get("xp_base", 0))
        xp_bonus = int(payload.get("xp_bonus", 0))
        stage_upgraded = bool(payload.get("stage_upgraded", False))
        unit_unlock_passed = bool(payload.get("unit_unlock_passed", payload.get("passed", True)))
        stage_unlock_passed = bool(payload.get("stage_unlock_passed", False))
        unlocked_chars = list(payload.get("unlock_chars", []))
        objective = self._tr_dynamic(str(payload.get("unit_objective", "-")))
        unit_before = int(payload.get("unit_before", self._dashboard.get("current_unit", 1)))

        xp_text = self.tr("+{0} XP").format(int(payload.get("xp_gain", xp_base + xp_bonus)))
        if xp_bonus > 0:
            xp_text += self.tr("  · 奖励 +{0}").format(xp_bonus)

        self.label_summary_title.setText(self.tr("Unit {0} 完成").format(unit_before))
        self.label_summary_objective.setText(self.tr("目标：{0}").format(objective))
        self.label_summary_ring.setText(self.tr("{0:.0f}%").format(accuracy))
        self._summary_ring_style(accuracy)
        self.label_summary_accuracy.setText(self.tr("准确率 {0:.1f}%").format(accuracy))
        self.label_summary_rhythm.setText(self.tr("节奏评分 {0:.1f}").format(rhythm))
        self.label_summary_grade.setText(self.tr("评级 {0}").format(grade))
        self.label_summary_xp.setText(xp_text)
        self.label_summary_combo.setText(
            self.tr("连击 +1（当前总连击 {0}）").format(int(payload.get("combo_units", 0)))
        )
        if unit_unlock_passed:
            self.label_summary_check.setText("✓")
            self.label_summary_check.setStyleSheet(
                "QLabel#summaryCheckIcon {"
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #dff8f1,stop:1 #c8efe6);"
                "border: 2px solid #78d1bb; border-radius: 28px;"
                "color: #24a888; font-size: 30px; font-weight: 700; }"
            )
        else:
            self.label_summary_check.setText("!")
            self.label_summary_check.setStyleSheet(
                "QLabel#summaryCheckIcon {"
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fff2e6,stop:1 #ffe6d6);"
                "border: 2px solid #f2b783; border-radius: 28px;"
                "color: #d9822b; font-size: 30px; font-weight: 700; }"
            )

        if stage_upgraded:
            unlock_text = ", ".join(unlocked_chars) if unlocked_chars else self.tr("新内容")
            self.label_summary_stage.setText(
                self.tr("阶段升级成功，已解锁：{0}").format(unlock_text)
            )
            self.btn_continue.setText(self.tr("进入下一阶段"))
        elif not unit_unlock_passed:
            min_acc = float(payload.get("unit_unlock_min_accuracy", 70.0))
            min_rhythm = float(payload.get("unit_unlock_min_rhythm", 65.0))
            self.label_summary_stage.setText(
                self.tr(
                    "未达 Unit 解锁阈值：准确率≥{0:.0f}% 且节奏≥{1:.0f}。请重练本 Unit。"
                ).format(min_acc, min_rhythm)
            )
            self.btn_continue.setText(self.tr("继续本 Unit"))
        elif bool(payload.get("is_boss", False)) and not stage_unlock_passed:
            min_acc = float(payload.get("stage_unlock_min_accuracy", 75.0))
            min_rhythm = float(payload.get("stage_unlock_min_rhythm", 70.0))
            min_score = float(payload.get("stage_unlock_min_score", 75.0))
            self.label_summary_stage.setText(
                self.tr(
                    "Boss 已通过 Unit 门槛，但阶段解锁需：准确率≥{0:.0f}% 、节奏≥{1:.0f} 、总分≥{2:.0f}。"
                ).format(min_acc, min_rhythm, min_score)
            )
            self.btn_continue.setText(self.tr("继续本 Unit"))
        else:
            self.label_summary_stage.setText(self.tr("可继续下一个 Unit，或再练一次本 Unit。"))
            self.btn_continue.setText(self.tr("继续下一个"))

        self._selected_stage_id = int(payload.get("next_stage_id", self._selected_stage_id or 1))
        self._refresh_dashboard()
        self.page_stack.setCurrentWidget(self.page_summary)

    def apply_ui_scale(self, scale: float) -> None:
        factor = max(0.8, min(1.6, float(scale)))
        font = self.font()
        font.setPointSizeF(max(8.0, 10.0 * factor))
        self.setFont(font)
        self.rx_runner.apply_ui_scale(scale)
        self.tx_runner.apply_ui_scale(scale)

    def refresh_send_runtime(self) -> None:
        self.tx_runner.refresh_runtime()

    def recreate_buzzers(self) -> None:
        self.rx_runner.recreate_buzzer()
        self.tx_runner.recreate_buzzer()
        self.page_tutorial.recreate_buzzer()

    def close(self) -> bool:  # type: ignore[override]
        self.page_tutorial.stop_audio()
        should_close_local = not (self.context and hasattr(self.context, "create_buzzer"))
        if should_close_local and getattr(self.page_tutorial, "buzzer", None) and hasattr(self.page_tutorial.buzzer, "close"):
            try:
                self.page_tutorial.buzzer.close()
            except Exception:
                pass
        self.stop_training()
        return super().close()
