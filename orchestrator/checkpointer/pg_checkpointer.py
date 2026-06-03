"""
orchestrator/checkpointer/pg_checkpointer.py
=============================================
Checkpointer factory — uses MemorySaver for local dev, PostgresSaver for production.
PostgresSaver checkpoints the entire pipeline state to PostgreSQL at every node
transition so a machine restart resumes exactly where it left off.
"""

import logging
from langgraph.checkpoint.memory import MemorySaver

from config.settings import settings

logger = logging.getLogger(__name__)


def get_checkpointer():
    """
    Returns the appropriate LangGraph checkpointer based on the environment.

    - development: MemorySaver (no external DB required, fast for tests)
    - production/staging: PostgresSaver (persistent, survives restarts)
    """
    if settings.environment in ("production", "staging"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            checkpointer = PostgresSaver.from_conn_string(settings.database_url)
            checkpointer.setup()  # creates tables if needed
            logger.info("Using PostgresSaver checkpointer (persistent)")
            return checkpointer
        except Exception as e:
            logger.warning(
                f"Failed to initialise PostgresSaver, falling back to MemorySaver: {e}"
            )
            return MemorySaver()
    else:
        logger.info("Using MemorySaver checkpointer (in-memory, dev mode)")
        return MemorySaver()
