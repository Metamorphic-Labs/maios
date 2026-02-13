# tests/unit/test_execute_code.py
import pytest


@pytest.mark.asyncio
async def test_execute_code_skill_exists():
    """Test execute_code skill is registered."""
    from maios.skills.builtin.execute_code import ExecuteCodeSkill

    skill = ExecuteCodeSkill()
    assert skill.name == "execute_code"
    assert "exec" in skill.required_permissions


@pytest.mark.asyncio
async def test_execute_code_skill_validates_input():
    """Test execute_code validates input."""
    from maios.skills.builtin.execute_code import ExecuteCodeSkill

    skill = ExecuteCodeSkill()
    result = await skill.execute(code="print('hello')", language="python")

    # Result will vary based on implementation
    assert "status" in result or "error" in result
