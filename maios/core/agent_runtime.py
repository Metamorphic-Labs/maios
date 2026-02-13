"""Agent Runtime for executing agent tasks."""

import logging
from typing import Any, Optional
from uuid import UUID

from maios.core.config import settings
from maios.models.agent import Agent, AgentStatus
from maios.skills.registry import registry

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Runtime for executing agent tasks."""

    def __init__(self, agent: Agent):
        self.agent = agent
        self._client = None

    @property
    def client(self):
        """Lazy-loaded Z.ai client."""
        if self._client is None:
            # Placeholder - actual Z.ai SDK integration
            # from zai import Client
            # self._client = Client(api_key=settings.zai_api_key)
            self._client = MockClient(settings.zai_api_key)
        return self._client

    async def execute_task(
        self,
        task_id: UUID,
        task_title: str,
        task_description: Optional[str] = None,
        context: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Execute a task using the agent's configured model."""
        self.agent.status = AgentStatus.WORKING
        self.agent.current_task_id = task_id

        try:
            # Build the prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_task_prompt(task_title, task_description, context)

            # Call the model (placeholder)
            response = await self._call_model(system_prompt, user_prompt)

            # Process response
            result = self._process_response(response)

            self.agent.status = AgentStatus.IDLE
            self.agent.current_task_id = None
            self.agent.tasks_completed += 1

            return result

        except Exception as e:
            logger.error(f"Agent {self.agent.name} failed task {task_id}: {e}")
            self.agent.status = AgentStatus.ERROR
            self.agent.tasks_failed += 1
            return {
                "status": "error",
                "error": str(e),
            }

    def _build_system_prompt(self) -> str:
        """Build the system prompt from agent configuration."""
        parts = [
            f"You are {self.agent.name}, a {self.agent.role}.",
            self.agent.persona,
        ]

        if self.agent.goals:
            parts.append("\nGoals:")
            for goal in self.agent.goals:
                parts.append(f"- {goal}")

        if self.agent.skill_tags:
            parts.append(f"\nSkills: {', '.join(self.agent.skill_tags)}")

        if self.agent.system_prompt:
            parts.append(f"\n{self.agent.system_prompt}")

        return "\n".join(parts)

    def _build_task_prompt(
        self,
        title: str,
        description: Optional[str],
        context: dict[str, Any] = None,
    ) -> str:
        """Build the task prompt."""
        parts = [f"Task: {title}"]

        if description:
            parts.append(f"\nDescription: {description}")

        if context:
            parts.append("\nContext:")
            for key, value in context.items():
                parts.append(f"- {key}: {value}")

        return "\n".join(parts)

    async def _call_model(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Call the Z.ai model (placeholder)."""
        # Placeholder - actual Z.ai SDK call
        # return await self.client.chat.completions.create(
        #     model=self.agent.model_name,
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_prompt},
        #     ],
        # )
        return {
            "content": f"Processed task with {self.agent.model_name}",
            "model": self.agent.model_name,
        }

    def _process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Process the model response."""
        return {
            "status": "success",
            "result": response.get("content", ""),
            "model": response.get("model", self.agent.model_name),
        }

    async def call_skill(
        self,
        skill_name: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute a skill by name."""
        skill = registry.get_skill(skill_name)
        if skill is None:
            return {"status": "error", "error": f"Skill not found: {skill_name}"}

        if not skill.validate_permissions(self.agent.permissions):
            return {"status": "error", "error": "Permission denied"}

        return await skill.execute(**kwargs)


class MockClient:
    """Mock client for testing without Z.ai SDK."""

    def __init__(self, api_key: str):
        self.api_key = api_key
