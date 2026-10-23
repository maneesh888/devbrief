"""Adapter so Claude Code fits the same `sources.REGISTRY` shape as the
other tools, without disturbing the existing discovery/transcripts modules
(and their tests) that predate multi-source support."""

from devbrief.core import discovery, transcripts

NAME = "claude_code"

discover_projects = discovery.discover_projects
extract_day_text = transcripts.extract_day_text
dominant_branch = transcripts.dominant_branch
