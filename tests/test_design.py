"""Tests for Design Agent core framework (TICKET-003)."""

import os
import pytest


# Sync tests for agent structure
def test_design_agent_initializes():
    """Test that design agent initializes without errors."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.design import design_agent

    assert design_agent is not None


def test_design_agent_has_correct_name():
    """Test that design agent has the correct name."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.design import design_agent

    assert design_agent.name == "design_phase_agent"


def test_design_agent_has_four_tools():
    """Test that design agent has exactly four tools."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.design import design_agent

    assert len(design_agent.tools) == 4


def test_design_agent_uses_config_model():
    """Test that design agent uses the model from config."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.design import design_agent
    from src.config import LLM_MODEL

    assert design_agent.model == LLM_MODEL


# Async tests for tool function behavior
@pytest.mark.asyncio
async def test_interview_tool_returns_formatted_response():
    """Test that interview tool returns properly formatted dict response."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.design_tools import conduct_interview

    result = await conduct_interview(
        user_input="I want to design a phone stand",
        project_name="test_project"
    )

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["in_progress", "complete", "error"]
    assert "interview_complete" in result
    assert isinstance(result["interview_complete"], bool)


@pytest.mark.asyncio
async def test_interview_tool_validates_empty_input():
    """Test that interview tool handles empty input gracefully."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.design_tools import conduct_interview

    result = await conduct_interview(
        user_input="",
        project_name="test_project"
    )

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_sketch_tool_returns_formatted_response():
    """Test that sketch tool returns properly formatted dict response."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.design_tools import generate_sketches

    result = await generate_sketches(
        project_name="test_project",
        design_brief={"object_name": "phone stand", "purpose": "desk"}
    )

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["ok", "error"]
    assert "sketches" in result
    assert isinstance(result["sketches"], list)


@pytest.mark.asyncio
async def test_sketch_tool_validates_input():
    """Test that sketch tool validates required inputs."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.design_tools import generate_sketches

    # Test with empty design_brief
    result = await generate_sketches(
        project_name="test_project",
        design_brief={}
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_image_tool_returns_formatted_response():
    """Test that image tool returns properly formatted dict response."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.design_tools import generate_images

    result = await generate_images(
        project_name="test_project",
        sketch_id="sketch_001",
        perspective="front"
    )

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["ok", "error"]
    assert "images" in result
    assert isinstance(result["images"], list)


@pytest.mark.asyncio
async def test_blueprint_tool_returns_formatted_response():
    """Test that blueprint tool returns properly formatted dict response."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.design_tools import generate_blueprint

    result = await generate_blueprint(
        project_name="test_project",
        design_brief={"object_name": "phone stand", "purpose": "desk"},
        approved_images=["image_001", "image_002"]
    )

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["ok", "error"]
    assert "blueprint_path" in result or "message" in result
