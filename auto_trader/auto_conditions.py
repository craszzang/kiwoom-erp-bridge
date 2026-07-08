"""Resolve Kiwoom conditions from config without UI dialogs."""

from __future__ import annotations

import logging

from auto_trader.condition_picker import ConditionChoice, load_conditions_from_api
from auto_trader.config import AutomationConfig, TraderConfig
from auto_trader.kiwoom_api import KiwoomAPI

logger = logging.getLogger(__name__)


def resolve_conditions(api: KiwoomAPI, config: TraderConfig) -> list[ConditionChoice]:
    """Pick conditions from automation rules or saved config (no dialog)."""
    auto: AutomationConfig = config.automation
    try:
        all_conds = load_conditions_from_api(api)
    except Exception as exc:
        logger.error("condition load failed: %s", exc)
        return []

    if not all_conds:
        logger.warning("no saved Kiwoom conditions — use HTS to create one")
        return []

    if auto.condition_names:
        want = {n.strip() for n in auto.condition_names if n.strip()}
        picked = [c for c in all_conds if c.name in want]
        if picked:
            logger.info("auto conditions by name: %s", [c.name for c in picked])
            return picked
        scored: list[tuple[int, ConditionChoice]] = []
        for c in all_conds:
            score = sum(1 for w in want if w in c.name)
            if score:
                scored.append((score, c))
        if scored:
            scored.sort(key=lambda x: -x[0])
            best = scored[0][1]
            logger.info("auto conditions keyword match: %s (score=%d)", best.name, scored[0][0])
            return [best]
        for c in all_conds:
            if any(w in c.name for w in want):
                logger.info("auto conditions partial match: %s", c.name)
                return [c]

    if auto.condition_indices:
        idx_set = {int(i) for i in auto.condition_indices}
        picked = [c for c in all_conds if c.index in idx_set]
        if picked:
            logger.info("auto conditions by index: %s", picked)
            return picked

    if config.condition_name:
        for c in all_conds:
            if c.name == config.condition_name:
                return [c]
        return [ConditionChoice(index=config.condition_index, name=config.condition_name)]

    if auto.use_first_condition:
        logger.info("auto first condition: [%s] %s", all_conds[0].index, all_conds[0].name)
        config.condition_name = all_conds[0].name
        config.condition_index = all_conds[0].index
        return [all_conds[0]]

    return []


def resolve_parallel_conditions(api: KiwoomAPI, config: TraderConfig) -> list[ConditionChoice]:
    """Return all HTS conditions matching automation keywords (parallel lanes)."""
    auto: AutomationConfig = config.automation
    try:
        all_conds = load_conditions_from_api(api)
    except Exception as exc:
        logger.error("condition load failed: %s", exc)
        return []

    if not all_conds:
        logger.warning("no saved Kiwoom conditions — use HTS to create one")
        return []

    if auto.condition_names:
        want = [n.strip() for n in auto.condition_names if n.strip()]
        want_set = set(want)
        exact = [c for c in all_conds if c.name in want_set]
        if exact:
            logger.info("parallel conditions exact: %s", [c.name for c in exact])
            return exact
        matched: list[ConditionChoice] = []
        seen: set[str] = set()
        for c in all_conds:
            if any(w in c.name for w in want) and c.name not in seen:
                matched.append(c)
                seen.add(c.name)
        if matched:
            logger.info("parallel conditions keyword: %s", [c.name for c in matched])
            return matched

    if auto.condition_indices:
        idx_set = {int(i) for i in auto.condition_indices}
        picked = [c for c in all_conds if c.index in idx_set]
        if picked:
            return picked

    if auto.use_first_condition:
        return [all_conds[0]]

    return all_conds[: min(8, len(all_conds))]
