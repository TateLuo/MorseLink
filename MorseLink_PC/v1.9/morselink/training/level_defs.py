from __future__ import annotations

from .models import StageDef, UnitDef, UnitStepDef


def _normal_unit_steps(prefix: str, output_lengths: tuple[int, int, int], continuous: bool) -> list[UnitStepDef]:
    return [
        UnitStepDef(
            step_id=f"{prefix}_rx_identify",
            mode="rx",
            question_count=1,
            focus="accuracy",
            output_length=int(output_lengths[0]),
            continuous=continuous,
            rx_gap_scale=1.0,
        ),
        UnitStepDef(
            step_id=f"{prefix}_tx_rhythm",
            mode="tx",
            question_count=1,
            focus="rhythm",
            output_length=int(output_lengths[1]),
            continuous=continuous,
        ),
        UnitStepDef(
            step_id=f"{prefix}_rx_speed",
            mode="rx",
            question_count=1,
            focus="speed",
            output_length=int(output_lengths[2]),
            continuous=continuous,
            rx_gap_scale=0.88,
        ),
    ]


def _boss_unit_steps(prefix: str, output_lengths: tuple[int, int], continuous: bool) -> list[UnitStepDef]:
    return [
        UnitStepDef(
            step_id=f"{prefix}_rx_boss",
            mode="rx",
            question_count=1,
            no_hint=True,
            focus="speed",
            output_length=int(output_lengths[0]),
            continuous=continuous,
            rx_gap_scale=0.82,
        ),
        UnitStepDef(
            step_id=f"{prefix}_tx_boss",
            mode="tx",
            question_count=1,
            no_hint=True,
            focus="rhythm",
            output_length=int(output_lengths[1]),
            continuous=continuous,
        ),
    ]


def _build_stage1_units() -> list[UnitDef]:
    # Stage 1 rhythm:
    # Unit1-2: K/M; Unit3: +R; Unit4: +S; Unit5 Boss; Unit6: +A; Unit7: +N; Unit8 Boss.
    charsets = [
        ["K", "M"],
        ["K", "M"],
        ["K", "M", "R"],
        ["K", "M", "R", "S"],
        ["K", "M", "R", "S"],
        ["K", "M", "R", "S", "A"],
        ["K", "M", "R", "S", "A", "N"],
        ["K", "M", "R", "S", "A", "N"],
    ]
    unit_meta = [
        ("建立 K/M 基础节奏。", ["K", "M"], ["rhythm", "letters"]),
        ("巩固 K/M 识别稳定性。", [], ["reinforce", "letters"]),
        ("加入 R，重点压住 K-R 混淆。", ["R"], ["new_char", "confusion"]),
        ("加入 S，训练短码密集节奏。", ["S"], ["new_char", "density"]),
        ("Boss：无提示连续 KMRS 挑战。", [], ["boss", "no_hint"]),
        ("加入 A，强化 A-S 区分。", ["A"], ["new_char", "accuracy"]),
        ("加入 N，强化 N-K 区分。", ["N"], ["new_char", "accuracy"]),
        ("Boss：Stage 1 毕业考核（无提示）。", [], ["boss", "graduation"]),
    ]

    units: list[UnitDef] = []
    for idx, charset in enumerate(charsets, start=1):
        prefix = f"S1U{idx}"
        is_boss = idx in {5, 8}
        objective, added_chars, tags = unit_meta[idx - 1]
        if is_boss:
            steps = _boss_unit_steps(prefix, output_lengths=(72, 18), continuous=True)
        else:
            steps = _normal_unit_steps(prefix, output_lengths=(72, 18, 36), continuous=True)
        units.append(
            UnitDef(
                unit_index=idx,
                name=f"Unit {idx}",
                objective=objective,
                added_chars=list(added_chars),
                tags=list(tags),
                charset=list(charset),
                steps=steps,
                is_boss=is_boss,
                xp_reward=30 if is_boss else 10,
            )
        )
    return units


def _build_stage2_units() -> list[UnitDef]:
    # Stage 2 keeps 1-2 new chars per unit.
    charsets = [
        ["K", "M", "R", "S", "A", "N", "T"],
        ["K", "M", "R", "S", "A", "N", "T", "E"],
        ["K", "M", "R", "S", "A", "N", "T", "E", "O"],
        ["K", "M", "R", "S", "A", "N", "T", "E", "O", "I"],
        ["K", "M", "R", "S", "A", "N", "T", "E", "O", "I"],
        ["K", "M", "R", "S", "A", "N", "T", "E", "O", "I", "H"],
        ["K", "M", "R", "S", "A", "N", "T", "E", "O", "I", "H", "D"],
        ["K", "M", "R", "S", "A", "N", "T", "E", "O", "I", "H", "D"],
    ]
    unit_meta = [
        ("加入 T，强化长划时值控制。", ["T"], ["new_char", "timing"]),
        ("加入 E，强化短码回收速度。", ["E"], ["new_char", "speed"]),
        ("加入 O，强化三长划稳定性。", ["O"], ["new_char", "rhythm"]),
        ("加入 I，强化短码切换。", ["I"], ["new_char", "switching"]),
        ("Boss：无提示连续混合 T/E/O/I。", [], ["boss", "no_hint"]),
        ("加入 H，训练高密度点串耐力。", ["H"], ["new_char", "endurance"]),
        ("加入 D，训练划点切换控制。", ["D"], ["new_char", "transition"]),
        ("Boss：Stage 2 毕业考核（全量混合）。", [], ["boss", "graduation"]),
    ]

    units: list[UnitDef] = []
    for idx, charset in enumerate(charsets, start=1):
        prefix = f"S2U{idx}"
        is_boss = idx in {5, 8}
        objective, added_chars, tags = unit_meta[idx - 1]
        if is_boss:
            steps = _boss_unit_steps(prefix, output_lengths=(74, 19), continuous=True)
        else:
            steps = _normal_unit_steps(prefix, output_lengths=(74, 19, 38), continuous=True)
        units.append(
            UnitDef(
                unit_index=idx,
                name=f"Unit {idx}",
                objective=objective,
                added_chars=list(added_chars),
                tags=list(tags),
                charset=list(charset),
                steps=steps,
                is_boss=is_boss,
                xp_reward=30 if is_boss else 10,
            )
        )
    return units


def _build_stage3_units() -> list[UnitDef]:
    # Stage 3: words and callsigns.
    pool_selectors = [
        {"letter": 39, "callSign": 12},
        {"letter": 39, "callSign": 24},
        {"letter": 39, "Abbreviation": 40},
        {"letter": 39, "callSign": 30, "Abbreviation": 55},
        {"letter": 39, "callSign": 30, "Abbreviation": 55},
        {"letter": 39, "callSign": 30, "QAbbreviation": 16, "Abbreviation": 55},
        {"letter": 39, "callSign": 36, "QAbbreviation": 26, "Abbreviation": 70},
        {"letter": 39, "callSign": 36, "QAbbreviation": 26, "Abbreviation": 70},
    ]
    unit_meta = [
        ("从字符过渡到短词与呼号前缀。", [], ["words", "callsign"]),
        ("扩展呼号后缀与数字段解析。", [], ["callsign", "parsing"]),
        ("引入高频缩写块。", [], ["abbrev", "chunks"]),
        ("在同一循环中混合呼号与缩写。", [], ["mix", "switching"]),
        ("Boss：无提示连续呼号+缩写流。", [], ["boss", "no_hint"]),
        ("引入 Q 简语语义块。", [], ["qabbrev", "semantic"]),
        ("Q 简语与呼号快速上下文切换。", [], ["qabbrev", "mix"]),
        ("Boss：Stage 3 混合业务毕业考核。", [], ["boss", "graduation"]),
    ]

    units: list[UnitDef] = []
    for idx, selector in enumerate(pool_selectors, start=1):
        prefix = f"S3U{idx}"
        is_boss = idx in {5, 8}
        objective, added_chars, tags = unit_meta[idx - 1]
        if is_boss:
            steps = _boss_unit_steps(prefix, output_lengths=(10, 3), continuous=False)
        else:
            steps = _normal_unit_steps(prefix, output_lengths=(8, 2, 5), continuous=False)
        units.append(
            UnitDef(
                unit_index=idx,
                name=f"Unit {idx}",
                objective=objective,
                added_chars=list(added_chars),
                tags=list(tags),
                pool_selector=dict(selector),
                steps=steps,
                is_boss=is_boss,
                xp_reward=30 if is_boss else 10,
            )
        )
    return units


def _build_stage4_units() -> list[UnitDef]:
    # Stage 4: practical sustained copy.
    pool_selectors = [
        {"letter": 39, "callSign": 45, "QAbbreviation": 30, "Abbreviation": 90, "sentences": 2},
        {"letter": 39, "callSign": 45, "QAbbreviation": 30, "Abbreviation": 100, "sentences": 4},
        {"letter": 39, "callSign": 45, "QAbbreviation": 36, "Abbreviation": 120, "sentences": 6},
        {"letter": 39, "callSign": 45, "QAbbreviation": 42, "Abbreviation": 140, "sentences": 8},
        {"letter": 39, "callSign": 45, "QAbbreviation": 42, "Abbreviation": 140, "sentences": 8},
        {"letter": 39, "callSign": 45, "QAbbreviation": 45, "Abbreviation": 160, "sentences": 10},
        {"letter": 39, "callSign": 45, "QAbbreviation": 45, "Abbreviation": 180, "sentences": 12},
        {"letter": 39, "callSign": 45, "QAbbreviation": 45, "Abbreviation": 180, "sentences": 12},
    ]
    unit_meta = [
        ("以短报文块进入持续抄收。", [], ["practical", "sustain"]),
        ("增加报文块数量，保持节奏稳定。", [], ["practical", "load"]),
        ("加入更密集 QSO 片段，提升上下文连续性。", [], ["qso", "continuity"]),
        ("高密度混合业务，训练快速模式切换。", [], ["density", "switching"]),
        ("Boss：无提示长时实战流。", [], ["boss", "no_hint"]),
        ("提升长句发报稳定度。", [], ["tx", "stability"]),
        ("在实战流中定向打击弱项混淆。", [], ["adaptive", "confusion"]),
        ("Boss：Stage 4 持续抄收毕业考核。", [], ["boss", "graduation"]),
    ]

    units: list[UnitDef] = []
    for idx, selector in enumerate(pool_selectors, start=1):
        prefix = f"S4U{idx}"
        is_boss = idx in {5, 8}
        objective, added_chars, tags = unit_meta[idx - 1]
        if is_boss:
            steps = _boss_unit_steps(prefix, output_lengths=(12, 3), continuous=False)
        else:
            steps = _normal_unit_steps(prefix, output_lengths=(10, 3, 6), continuous=False)
        units.append(
            UnitDef(
                unit_index=idx,
                name=f"Unit {idx}",
                objective=objective,
                added_chars=list(added_chars),
                tags=list(tags),
                pool_selector=dict(selector),
                steps=steps,
                is_boss=is_boss,
                xp_reward=30 if is_boss else 10,
            )
        )
    return units


def get_stage_defs() -> list[StageDef]:
    return [
        StageDef(
            stage_id=1,
            name="Stage 1 - 节奏与基础字符",
            subtitle="建立短循环听发节奏。",
            units=_build_stage1_units(),
            xp_goal=100,
            unlock_chars=["K", "M", "R", "S", "A", "N"],
        ),
        StageDef(
            stage_id=2,
            name="Stage 2 - 字符扩展",
            subtitle="每个 Unit 只新增 1-2 个字符。",
            units=_build_stage2_units(),
            xp_goal=100,
            unlock_chars=["T", "E", "O", "I", "H", "D"],
        ),
        StageDef(
            stage_id=3,
            name="Stage 3 - 单词与呼号",
            subtitle="从字符过渡到短词与呼号。",
            units=_build_stage3_units(),
            xp_goal=100,
            unlock_chars=[],
        ),
        StageDef(
            stage_id=4,
            name="Stage 4 - 实战与持续抄收",
            subtitle="连续处理真实混合业务流。",
            units=_build_stage4_units(),
            xp_goal=100,
            unlock_chars=[],
        ),
    ]


def get_stage_by_id(stage_id: int) -> StageDef:
    stages = get_stage_defs()
    normalized = max(1, int(stage_id))
    if normalized > len(stages):
        normalized = len(stages)
    return stages[normalized - 1]
