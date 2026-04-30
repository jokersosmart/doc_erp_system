"""Unit tests for document state machine and version logic."""
import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.services.document_state_machine import (
    check_transition_permission,
    increment_major_version,
    increment_minor_version,
    validate_status_transition,
)


class TestVersionIncrement:
    def test_increment_minor_version_basic(self):
        assert increment_minor_version("1.0") == "1.1"

    def test_increment_minor_version_multiple(self):
        assert increment_minor_version("1.1") == "1.2"
        assert increment_minor_version("1.9") == "1.10"
        assert increment_minor_version("2.3") == "2.4"

    def test_increment_minor_version_large_minor(self):
        assert increment_minor_version("1.99") == "1.100"

    def test_increment_major_version(self):
        assert increment_major_version("1.5") == "2.0"
        assert increment_major_version("1.0") == "2.0"
        assert increment_major_version("3.7") == "4.0"


class TestStatusTransitions:
    def test_valid_status_transitions(self):
        """All valid transitions should pass without raising."""
        validate_status_transition("DRAFT", "REVIEW")
        validate_status_transition("REVIEW", "APPROVED")
        validate_status_transition("APPROVED", "OBSOLETE")
        validate_status_transition("REVIEW", "DRAFT")  # Can revert to DRAFT

    def test_invalid_status_transitions(self):
        """Invalid transitions should raise HTTPException 422."""
        invalid_pairs = [
            ("DRAFT", "APPROVED"),
            ("DRAFT", "OBSOLETE"),
            ("APPROVED", "DRAFT"),
            ("APPROVED", "REVIEW"),
            ("OBSOLETE", "DRAFT"),
            ("OBSOLETE", "REVIEW"),
            ("OBSOLETE", "APPROVED"),
        ]
        for current, new in invalid_pairs:
            with pytest.raises(HTTPException) as exc_info:
                validate_status_transition(current, new)
            assert exc_info.value.status_code == 422
            assert exc_info.value.detail["code"] == "INVALID_STATUS_TRANSITION"

    def test_same_status_transition_raises(self):
        """Transitioning to the same status should raise 422."""
        with pytest.raises(HTTPException) as exc_info:
            validate_status_transition("DRAFT", "DRAFT")
        assert exc_info.value.status_code == 422

    def test_obsolete_has_no_transitions(self):
        """OBSOLETE state has no valid outgoing transitions."""
        with pytest.raises(HTTPException):
            validate_status_transition("OBSOLETE", "DRAFT")


class TestTransitionPermissions:
    def _make_doc(self, owner_id: str = "user-rd-001", status: str = "DRAFT"):
        doc = MagicMock()
        doc.owner_id = owner_id
        doc.status = status
        return doc

    def test_admin_can_do_all_transitions(self):
        """Admin should not raise for any transition."""
        doc = self._make_doc()
        check_transition_permission("REVIEW", "Admin", doc, "any-user")
        check_transition_permission("APPROVED", "Admin", doc, "any-user")
        check_transition_permission("OBSOLETE", "Admin", doc, "any-user")

    def test_rd_can_advance_own_doc_to_review(self):
        """RD can push their own document to REVIEW."""
        doc = self._make_doc(owner_id="user-rd-001")
        check_transition_permission("REVIEW", "RD", doc, "user-rd-001")

    def test_rd_cannot_advance_others_doc_to_review(self):
        """RD cannot push someone else's document to REVIEW."""
        doc = self._make_doc(owner_id="user-rd-002")
        with pytest.raises(HTTPException) as exc_info:
            check_transition_permission("REVIEW", "RD", doc, "user-rd-001")
        assert exc_info.value.status_code == 403

    def test_rd_cannot_approve(self):
        """RD role is not permitted to APPROVE documents."""
        doc = self._make_doc()
        with pytest.raises(HTTPException) as exc_info:
            check_transition_permission("APPROVED", "RD", doc, "user-rd-001")
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "FORBIDDEN"

    def test_qa_can_approve(self):
        """QA can approve documents."""
        doc = self._make_doc()
        check_transition_permission("APPROVED", "QA", doc, "user-qa-001")

    def test_pm_cannot_approve(self):
        """PM is not in the APPROVED allowed roles."""
        doc = self._make_doc()
        with pytest.raises(HTTPException) as exc_info:
            check_transition_permission("APPROVED", "PM", doc, "user-pm-001")
        assert exc_info.value.status_code == 403
