#!/usr/bin/env python3
"""Workloads: what kind of Cortex Code work a prompt asks for.

A Workload is independent of the Host (which agent asked). GENERAL is any Snowflake
work. MIGRATION is a database or ETL migration to Snowflake, which Cortex Code hands
to Snowflake AIM: an interactive, multi-session agent that installs its own plugin
and runs through an MCP server, so it needs the RW envelope and resumed sessions.

Only hosts with supports_workloads classify prompts; others keep GENERAL routing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Workload:
    name: str
    # Envelope the workload cannot run without, or None for the caller's choice.
    required_envelope: str | None = None
    # Follow-up prompts continue the same Cortex session.
    multi_turn: bool = False


GENERAL = Workload("general")
MIGRATION = Workload("migration", required_envelope="RW", multi_turn=True)

# Systems AIM migrates from (docs: Supported source systems).
_SOURCES = (
    r"sql\s+server|mssql|t-?sql|transact-sql|ssms|azure\s+synapse|synapse|"
    r"oracle|pl/?sql|teradata|redshift|netezza|bigquery|db2|postgres(?:ql)?|mysql|"
    r"sybase|greenplum|vertica|hive|spark\s+sql|databricks\s+sql|"
    r"legacy\s+(?:data\s+)?warehouse"
)
_ACTIONS = (
    r"migrat\w*|convert\w*|replatform\w*|decommission\w*|sunset\w*|moderniz\w*|"
    r"modernis\w*|lift[-\s]and[-\s]shift|port(?:ing)?|translat\w*|rewrit\w*|"
    r"assess\w*|extract\w*"
)

_MIGRATION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    # AIM commands and session phrases from its docs.
    r"^\s*/migrate\b",
    r"\b(?:start|begin|continue|resume)\b.{0,40}\bmigration\b",
    r"\bmigration\b.{0,40}\b(?:state|status|progress)\b",
    r"\b(?:state|status|progress)\b.{0,40}\bmigration\b",
    r"\bimport\s+(?:\w+\s+)?sql\s+files\b",
    # Migration tooling.
    r"\bsnowconvert\b|\bscai\b|\bssis\b|\binformatica\b",
    # An action applied to a source system, in either order.
    rf"\b(?:{_ACTIONS})\b.{{0,60}}\b(?:{_SOURCES})\b",
    rf"\b(?:{_SOURCES})\b.{{0,60}}\b(?:{_ACTIONS})\b",
)]


def classify(prompt: str) -> Workload:
    """Return MIGRATION when the prompt asks for a migration to Snowflake, else GENERAL."""
    if any(p.search(prompt or "") for p in _MIGRATION_PATTERNS):
        return MIGRATION
    return GENERAL
