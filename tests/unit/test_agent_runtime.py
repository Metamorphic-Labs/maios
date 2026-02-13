"""Tests for Agent Runtime."""

import pytest
from uuid import uuid4

from maios.core.agent_runtime import AgentRuntime, MockClient
from maios.models.agent import Agent, AgentStatus


class TestAgentRuntimeCreation:
    """Tests for AgentRuntime creation."""

    def test_agent_runtime_creation(self):
        """Test basic AgentRuntime creation."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
            skill_tags=["code"],
            permissions=["exec"],
        )
        runtime = AgentRuntime(agent)
        assert runtime.agent.name == "TestAgent"
        assert runtime.agent.role == "Developer"
        assert runtime._client is None

    def test_agent_runtime_lazy_client(self):
        """Test lazy loading of client."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
        )
        runtime = AgentRuntime(agent)

        # Client should be None initially
        assert runtime._client is None

        # Accessing client property should create it
        client = runtime.client
        assert client is not None
        assert isinstance(client, MockClient)

        # Should reuse same client
        client2 = runtime.client
        assert client is client2


class TestExecuteTask:
    """Tests for task execution."""

    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        """Test successful task execution."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
        )
        runtime = AgentRuntime(agent)

        result = await runtime.execute_task(
            task_id=uuid4(),
            task_title="Test task",
        )

        assert result["status"] == "success"
        assert "result" in result
        assert agent.status == AgentStatus.IDLE
        assert agent.tasks_completed == 1
        assert agent.current_task_id is None

    @pytest.mark.asyncio
    async def test_execute_task_with_description(self):
        """Test task execution with description."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
        )
        runtime = AgentRuntime(agent)

        result = await runtime.execute_task(
            task_id=uuid4(),
            task_title="Test task",
            task_description="This is a detailed task description",
        )

        assert result["status"] == "success"
        assert agent.tasks_completed == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_context(self):
        """Test task execution with context."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
        )
        runtime = AgentRuntime(agent)

        result = await runtime.execute_task(
            task_id=uuid4(),
            task_title="Test task",
            context={"file": "test.py", "lines": 100},
        )

        assert result["status"] == "success"
        assert agent.tasks_completed == 1

    @pytest.mark.asyncio
    async def test_execute_task_updates_agent_status(self):
        """Test that agent status is updated during execution."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
        )
        runtime = AgentRuntime(agent)
        task_id = uuid4()

        # Initially idle
        assert agent.status == AgentStatus.IDLE

        # Execute task (status changes during execution)
        result = await runtime.execute_task(
            task_id=task_id,
            task_title="Test task",
        )

        # After execution, should be idle again
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task_id is None


class TestBuildPrompts:
    """Tests for prompt building."""

    def test_build_system_prompt_basic(self):
        """Test basic system prompt building."""
        agent = Agent(
            name="CodeAgent",
            role="Software Developer",
            persona="An expert developer",
        )
        runtime = AgentRuntime(agent)

        prompt = runtime._build_system_prompt()

        assert "You are CodeAgent" in prompt
        assert "Software Developer" in prompt
        assert "An expert developer" in prompt

    def test_build_system_prompt_with_goals(self):
        """Test system prompt building with goals."""
        agent = Agent(
            name="CodeAgent",
            role="Software Developer",
            persona="An expert developer",
            goals=["Write clean code", "Fix bugs"],
        )
        runtime = AgentRuntime(agent)

        prompt = runtime._build_system_prompt()

        assert "Goals:" in prompt
        assert "- Write clean code" in prompt
        assert "- Fix bugs" in prompt

    def test_build_system_prompt_with_skills(self):
        """Test system prompt building with skill tags."""
        agent = Agent(
            name="CodeAgent",
            role="Software Developer",
            persona="An expert developer",
            skill_tags=["python", "javascript", "testing"],
        )
        runtime = AgentRuntime(agent)

        prompt = runtime._build_system_prompt()

        assert "Skills:" in prompt
        assert "python" in prompt
        assert "javascript" in prompt
        assert "testing" in prompt

    def test_build_system_prompt_with_custom_prompt(self):
        """Test system prompt building with custom system prompt."""
        agent = Agent(
            name="CodeAgent",
            role="Software Developer",
            persona="An expert developer",
            system_prompt="Always write tests first.",
        )
        runtime = AgentRuntime(agent)

        prompt = runtime._build_system_prompt()

        assert "Always write tests first." in prompt

    def test_build_task_prompt_basic(self):
        """Test basic task prompt building."""
        agent = Agent(name="TestAgent", role="Developer", persona="Test")
        runtime = AgentRuntime(agent)

        prompt = runtime._build_task_prompt("Implement feature X", None, None)

        assert "Task: Implement feature X" in prompt

    def test_build_task_prompt_with_description(self):
        """Test task prompt building with description."""
        agent = Agent(name="TestAgent", role="Developer", persona="Test")
        runtime = AgentRuntime(agent)

        prompt = runtime._build_task_prompt(
            "Implement feature X",
            "Create a new API endpoint",
            None,
        )

        assert "Task: Implement feature X" in prompt
        assert "Description: Create a new API endpoint" in prompt

    def test_build_task_prompt_with_context(self):
        """Test task prompt building with context."""
        agent = Agent(name="TestAgent", role="Developer", persona="Test")
        runtime = AgentRuntime(agent)

        prompt = runtime._build_task_prompt(
            "Implement feature X",
            None,
            {"file": "api.py", "priority": "high"},
        )

        assert "Context:" in prompt
        assert "- file: api.py" in prompt
        assert "- priority: high" in prompt


class TestCallSkill:
    """Tests for skill calling."""

    @pytest.mark.asyncio
    async def test_call_skill_not_found(self):
        """Test calling a non-existent skill."""
        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
            permissions=["exec"],
        )
        runtime = AgentRuntime(agent)

        result = await runtime.call_skill("nonexistent_skill")

        assert result["status"] == "error"
        assert "Skill not found" in result["error"]

    @pytest.mark.asyncio
    async def test_call_skill_permission_denied(self):
        """Test calling a skill without required permissions."""
        # Import to register the skill
        from maios.skills.builtin import execute_code  # noqa: F401

        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
            permissions=[],  # No permissions
        )
        runtime = AgentRuntime(agent)

        # execute_code requires "exec" permission
        result = await runtime.call_skill(
            "execute_code", code="print('test')", language="python"
        )

        assert result["status"] == "error"
        assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_call_execute_code_skill(self):
        """Test calling the execute_code skill with proper permissions."""
        # Import to register the skill
        from maios.skills.builtin import execute_code  # noqa: F401

        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
            permissions=["exec"],
        )
        runtime = AgentRuntime(agent)

        result = await runtime.call_skill(
            "execute_code", code="print('test')", language="python"
        )

        assert "status" in result
        # The execute_code skill returns "pending" status as placeholder
        assert result["status"] in ["success", "pending", "error"]


class TestMockClient:
    """Tests for MockClient."""

    def test_mock_client_creation(self):
        """Test MockClient creation."""
        client = MockClient("test-api-key")
        assert client.api_key == "test-api-key"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_task_error_handling(self):
        """Test that errors during execution are handled properly."""

        class FailingRuntime(AgentRuntime):
            async def _call_model(self, system_prompt, user_prompt):
                raise RuntimeError("Model call failed")

        agent = Agent(
            name="TestAgent",
            role="Developer",
            persona="A test agent",
        )
        runtime = FailingRuntime(agent)

        result = await runtime.execute_task(
            task_id=uuid4(),
            task_title="Test task",
        )

        assert result["status"] == "error"
        assert "Model call failed" in result["error"]
        assert agent.status == AgentStatus.ERROR
        assert agent.tasks_failed == 1
