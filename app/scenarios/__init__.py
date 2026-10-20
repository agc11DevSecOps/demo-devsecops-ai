"""Scenario registry: handlers emit evidence and never authorize actions."""

from __future__ import annotations

from app.scenarios.s0 import scenario_s0
from app.scenarios.s1 import scenario_s1
from app.scenarios.s2 import scenario_s2
from app.scenarios.s3 import scenario_s3
from app.scenarios.s4 import scenario_s4
from app.scenarios.s5 import scenario_s5
from app.scenarios.s6 import scenario_s6
from app.scenarios.s7 import scenario_s7
from app.scenarios.s8 import scenario_s8

SCENARIOS = {
    "S0": scenario_s0,
    "S1": scenario_s1,
    "S2": scenario_s2,
    "S3": scenario_s3,
    "S4": scenario_s4,
    "S5": scenario_s5,
    "S6": scenario_s6,
    "S7": scenario_s7,
    "S8": scenario_s8,
}

__all__ = ["SCENARIOS", "scenario_s0", "scenario_s1", "scenario_s2", "scenario_s3", "scenario_s4", "scenario_s5", "scenario_s6", "scenario_s7", "scenario_s8"]
