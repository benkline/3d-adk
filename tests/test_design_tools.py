"""Tests for design_tools interview functionality - TDD approach."""

import asyncio
import json
import os
import pytest
import importlib
from pathlib import Path
from unittest.mock import patch

# Import after we'll patch config
import src.config
import src.tools.design_tools


@pytest.fixture
def tmp_projects_dir(tmp_path):
    """Create a temporary projects directory for testing."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return str(projects_dir)


@pytest.fixture
def mock_projects_dir(tmp_projects_dir, monkeypatch):
    """Patch PROJECTS_DIR to use temporary directory."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("PROJECTS_DIR", tmp_projects_dir)

    # Patch config module
    monkeypatch.setattr(src.config, "PROJECTS_DIR", tmp_projects_dir)

    # Reload design_tools to pick up the patched PROJECTS_DIR
    importlib.reload(src.tools.design_tools)

    return tmp_projects_dir


@pytest.fixture(autouse=True)
def reset_imports(mock_projects_dir):
    """Reset imports between tests to avoid state sharing."""
    yield
    # After test, reload modules to reset any module-level state
    importlib.reload(src.tools.design_tools)


# Now we can import the functions
from src.tools.design_tools import conduct_interview, generate_sketches, generate_images


class TestInterviewMode:
    """Test suite for conduct_interview function."""

    @pytest.mark.asyncio
    async def test_interview_starts_with_first_question(self, mock_projects_dir):
        """When interview starts, first question should be returned."""
        # [ ] Interview completes with all required information
        result = await conduct_interview("I want to make a phone stand", "test-project")

        assert result["status"] == "in_progress"
        assert result["interview_complete"] is False
        assert result["design_brief"] is None
        assert "next_question" in result
        assert "question_number" in result
        assert result["question_number"] == 1

    @pytest.mark.asyncio
    async def test_interview_stores_answer_in_json(self, mock_projects_dir):
        """After first question answered, interview.json should contain the response."""
        # [ ] All responses stored in interview.json
        project_name = "test-project"
        user_input = "A phone stand for my desk"

        await conduct_interview(user_input, project_name)

        interview_path = Path(mock_projects_dir) / project_name / "design" / "interview.json"
        assert interview_path.exists(), f"interview.json not created at {interview_path}"

        with open(interview_path) as f:
            interview_data = json.load(f)

        assert "answers" in interview_data
        assert interview_data["answers"]["object_name"] == user_input

    @pytest.mark.asyncio
    async def test_interview_advances_question_index(self, mock_projects_dir):
        """Subsequent calls should advance to next question."""
        # [ ] Questions flow naturally based on responses
        project_name = "test-project"

        # First call
        result1 = await conduct_interview("A phone stand", project_name)
        assert result1["question_number"] == 1

        # Second call
        result2 = await conduct_interview("100mm x 80mm x 60mm", project_name)
        assert result2["question_number"] == 2
        assert result2["next_question"] != result1["next_question"]

    @pytest.mark.asyncio
    async def test_interview_completes_after_all_answers(self, mock_projects_dir):
        """After 7 answers, interview should be complete."""
        # [ ] Interview completes with all required information
        project_name = "test-project"

        answers = [
            "A phone stand",
            "100mm x 80mm x 60mm",
            "PLA",
            "minimalist",
            "must fit iPhone 14",
            "no",
            "none",
        ]

        for i, answer in enumerate(answers):
            result = await conduct_interview(answer, project_name)

            if i < 6:  # Last question
                assert result["status"] == "in_progress"
                assert result["interview_complete"] is False
            else:  # Final answer
                assert result["status"] == "complete"
                assert result["interview_complete"] is True

    @pytest.mark.asyncio
    async def test_interview_returns_design_brief_when_complete(self, mock_projects_dir):
        """When complete, design_brief should have all required keys."""
        # [ ] Interview completes with all required information
        project_name = "test-project"

        answers = [
            "phone stand",
            "100mm x 80mm x 60mm",
            "PLA",
            "minimalist",
            "must fit iPhone 14, non-slip base",
            "no",
            "none",
        ]

        result = None
        for answer in answers:
            result = await conduct_interview(answer, project_name)

        assert result["interview_complete"] is True
        design_brief = result["design_brief"]

        # Verify required fields
        required_keys = {"name", "purpose", "dimensions", "materials", "aesthetics", "constraints", "special_requirements"}
        assert set(design_brief.keys()) == required_keys

        # Verify dimensions is a dict with width/height/depth
        assert isinstance(design_brief["dimensions"], dict)
        assert "width" in design_brief["dimensions"]
        assert "height" in design_brief["dimensions"]
        assert "depth" in design_brief["dimensions"]

        # Verify materials is a list
        assert isinstance(design_brief["materials"], list)

        # Verify constraints is a list
        assert isinstance(design_brief["constraints"], list)

    @pytest.mark.asyncio
    async def test_interview_returns_summary_when_complete(self, mock_projects_dir):
        """When complete, summary should be generated."""
        # [ ] Summary is comprehensive and accurate
        project_name = "test-project"

        answers = [
            "phone stand",
            "100mm x 80mm x 60mm",
            "PLA",
            "minimalist",
            "must fit iPhone 14",
            "no",
            "none",
        ]

        for answer in answers:
            result = await conduct_interview(answer, project_name)

        assert result["interview_complete"] is True
        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0
        # Summary should reference the project name
        assert "phone stand" in result["summary"].lower() or "summary" in result["summary"].lower()

    @pytest.mark.asyncio
    async def test_interview_empty_user_input_returns_error(self, mock_projects_dir):
        """Empty user input should return error."""
        result = await conduct_interview("", "test-project")

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_interview_empty_project_name_returns_error(self, mock_projects_dir):
        """Empty project name should return error."""
        result = await conduct_interview("some input", "")

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_interview_json_updated_with_each_call(self, mock_projects_dir):
        """interview.json should accumulate answers across calls."""
        # [ ] All responses stored in interview.json
        project_name = "test-project"

        answer1 = "phone stand"
        await conduct_interview(answer1, project_name)

        interview_path = Path(mock_projects_dir) / project_name / "design" / "interview.json"
        with open(interview_path) as f:
            data1 = json.load(f)
        assert data1["current_question_index"] == 1

        answer2 = "100mm x 80mm"
        await conduct_interview(answer2, project_name)

        with open(interview_path) as f:
            data2 = json.load(f)
        assert data2["current_question_index"] == 2
        assert len(data2["answers"]) == 2


class TestSketchGeneration:
    """Test suite for generate_sketches function."""

    @pytest.mark.asyncio
    async def test_generate_sketches_empty_project_name_returns_error(self, mock_projects_dir):
        """Empty project name should return error."""
        design_brief = {"name": "test", "purpose": "test"}
        result = await generate_sketches("", design_brief)

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_generate_sketches_empty_design_brief_returns_error(self, mock_projects_dir):
        """Empty design brief should return error."""
        result = await generate_sketches("test-project", {})

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_generate_sketches_returns_ok_status(self, mock_projects_dir, monkeypatch):
        """generate_sketches should return ok status."""
        from unittest.mock import AsyncMock, MagicMock

        design_brief = {
            "name": "phone stand",
            "purpose": "desk organization",
            "dimensions": {"width": 100, "height": 80, "depth": 60},
            "materials": ["PLA"],
            "aesthetics": "minimalist",
            "constraints": ["must fit iPhone 14"],
            "special_requirements": []
        }

        # Mock the Anthropic client and its messages.create method
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["prompt1", "prompt2", "prompt3", "prompt4", "prompt5"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        result = await generate_sketches("test-project", design_brief)

        assert result["status"] == "ok"
        assert "sketches" in result
        assert "sketch_count" in result
        assert result["sketch_count"] >= 3

    @pytest.mark.asyncio
    async def test_generate_sketches_creates_output_directory(self, mock_projects_dir, monkeypatch):
        """generate_sketches should create output directory."""
        from unittest.mock import MagicMock

        design_brief = {
            "name": "test",
            "purpose": "test",
            "dimensions": {},
            "materials": [],
            "aesthetics": "test",
            "constraints": [],
            "special_requirements": []
        }

        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["prompt1", "prompt2", "prompt3"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        result = await generate_sketches("test-project", design_brief)

        sketches_dir = Path(mock_projects_dir) / "test-project" / "design" / "sketches"
        assert sketches_dir.exists(), f"Sketches directory not created at {sketches_dir}"

    @pytest.mark.asyncio
    async def test_generate_sketches_creates_metadata_file(self, mock_projects_dir, monkeypatch):
        """generate_sketches should create metadata.json."""
        from unittest.mock import MagicMock

        design_brief = {
            "name": "test",
            "purpose": "test",
            "dimensions": {},
            "materials": [],
            "aesthetics": "test",
            "constraints": [],
            "special_requirements": []
        }

        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["prompt1", "prompt2"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        await generate_sketches("test-project", design_brief)

        metadata_path = Path(mock_projects_dir) / "test-project" / "design" / "sketches" / "metadata.json"
        assert metadata_path.exists(), f"metadata.json not created at {metadata_path}"

        with open(metadata_path) as f:
            metadata = json.load(f)
        assert "sketches" in metadata

    @pytest.mark.asyncio
    async def test_generate_sketches_returns_sketch_list(self, mock_projects_dir, monkeypatch):
        """generate_sketches should return structured sketch list."""
        from unittest.mock import MagicMock

        design_brief = {
            "name": "phone stand",
            "purpose": "desk organization",
            "dimensions": {"width": 100, "height": 80, "depth": 60},
            "materials": ["PLA"],
            "aesthetics": "minimalist",
            "constraints": [],
            "special_requirements": []
        }

        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["prompt1", "prompt2", "prompt3"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        result = await generate_sketches("test-project", design_brief)

        assert result["status"] == "ok"
        assert len(result["sketches"]) == 3
        assert all("id" in sketch for sketch in result["sketches"])
        assert all("prompt" in sketch for sketch in result["sketches"])
        assert all("variation" in sketch for sketch in result["sketches"])


class TestImageGeneration:
    """Test suite for generate_images function."""

    @pytest.mark.asyncio
    async def test_generate_images_empty_project_name_returns_error(self, mock_projects_dir):
        """Empty project name should return error."""
        result = await generate_images("", "sketch_123", "front")

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_generate_images_empty_sketch_id_returns_error(self, mock_projects_dir):
        """Empty sketch ID should return error."""
        result = await generate_images("test-project", "", "front")

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_generate_images_invalid_perspective_returns_error(self, mock_projects_dir):
        """Invalid perspective should return error."""
        result = await generate_images("test-project", "sketch_123", "invalid")

        assert result["status"] == "error"
        assert "message" in result
        assert "front" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_images_returns_ok_status(self, mock_projects_dir, monkeypatch):
        """generate_images should return ok status with valid inputs."""
        from unittest.mock import MagicMock

        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["A high-quality render of the product from the front"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        result = await generate_images("test-project", "sketch_abc123", "front")

        assert result["status"] == "ok"
        assert "images" in result
        assert result["image_count"] == 1
        assert result["perspective"] == "front"

    @pytest.mark.asyncio
    async def test_generate_images_creates_output_directory(self, mock_projects_dir, monkeypatch):
        """generate_images should create output directory."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["A render from the side"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        result = await generate_images("test-project", "sketch_123", "side")

        images_dir = Path(mock_projects_dir) / "test-project" / "design" / "images"
        assert images_dir.exists(), f"Images directory not created at {images_dir}"

    @pytest.mark.asyncio
    async def test_generate_images_creates_metadata_file(self, mock_projects_dir, monkeypatch):
        """generate_images should create metadata.json."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["A top-down render"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        await generate_images("test-project", "sketch_xyz", "top")

        metadata_path = Path(mock_projects_dir) / "test-project" / "design" / "images" / "metadata.json"
        assert metadata_path.exists(), f"metadata.json not created at {metadata_path}"

        with open(metadata_path) as f:
            metadata = json.load(f)
        assert "images" in metadata
        assert len(metadata["images"]) == 1

    @pytest.mark.asyncio
    async def test_generate_images_record_has_required_keys(self, mock_projects_dir, monkeypatch):
        """Image record should have all required keys."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["A 3D perspective render"]')]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        monkeypatch.setattr(
            "src.tools.design_tools._get_anthropic_client",
            lambda: mock_client
        )

        result = await generate_images("test-project", "sketch_abc", "3d")

        assert result["status"] == "ok"
        assert len(result["images"]) == 1
        image_record = result["images"][0]

        required_keys = {"id", "sketch_id", "perspective", "prompt", "material_context", "created_at", "status", "image_path"}
        assert set(image_record.keys()) == required_keys

        # Verify values
        assert image_record["sketch_id"] == "sketch_abc"
        assert image_record["perspective"] == "3d"
        assert image_record["status"] == "pending_generation"
        assert image_record["image_path"] is None
        assert isinstance(image_record["prompt"], str)
        assert len(image_record["prompt"]) > 0
