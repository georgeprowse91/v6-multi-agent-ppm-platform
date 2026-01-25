"""
Base Agent Class for Multi-Agent PPM Platform

This module provides the abstract base class that all agents inherit from.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all PPM agents.

    All agents must implement the process() method and can optionally
    override lifecycle hooks (initialize, validate, cleanup).
    """

    def __init__(self, agent_id: str, config: dict[str, Any] | None = None):
        """
        Initialize the agent.

        Args:
            agent_id: Unique identifier for this agent instance
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.initialized = False

    async def initialize(self) -> None:
        """
        Initialize agent resources (databases, connections, models, etc.).

        Called once before the agent starts processing requests.
        Override this method to perform setup tasks.
        """
        self.logger.info(f"Initializing agent {self.agent_id}")
        self.initialized = True

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """
        Validate input data before processing.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise

        Override this method to add agent-specific validation.
        """
        return True

    @abstractmethod
    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process the agent's core logic.

        This is the main method that must be implemented by all agents.

        Args:
            input_data: Input data for the agent to process

        Returns:
            Dictionary containing the agent's response

        Raises:
            ValueError: If input validation fails
            Exception: For agent-specific errors
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up agent resources.

        Called when the agent is shutting down.
        Override this method to perform cleanup tasks.
        """
        self.logger.info(f"Cleaning up agent {self.agent_id}")

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the full agent workflow with validation and error handling.

        Args:
            input_data: Input data for processing

        Returns:
            Dictionary containing:
                - success: Boolean indicating success/failure
                - data: Agent response data (if successful)
                - error: Error message (if failed)
                - metadata: Execution metadata (timing, agent_id, etc.)
        """
        start_time = datetime.utcnow()

        try:
            # Ensure agent is initialized
            if not self.initialized:
                await self.initialize()

            # Validate input
            if not await self.validate_input(input_data):
                return {
                    "success": False,
                    "error": "Input validation failed",
                    "metadata": {
                        "agent_id": self.agent_id,
                        "timestamp": start_time.isoformat(),
                    },
                }

            # Process the request
            self.logger.info(f"Processing request for agent {self.agent_id}")
            result = await self.process(input_data)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "success": True,
                "data": result,
                "metadata": {
                    "agent_id": self.agent_id,
                    "timestamp": start_time.isoformat(),
                    "execution_time_seconds": execution_time,
                },
            }

        except Exception as e:
            self.logger.error(f"Error in agent {self.agent_id}: {str(e)}", exc_info=True)
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "agent_id": self.agent_id,
                    "timestamp": start_time.isoformat(),
                    "execution_time_seconds": execution_time,
                },
            }

    def get_capabilities(self) -> list[str]:
        """
        Return list of capabilities this agent provides.

        Override this method to declare agent capabilities.

        Returns:
            List of capability strings
        """
        return []

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
