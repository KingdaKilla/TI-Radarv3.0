"""Tests fuer Port-Interfaces — ABC-Compliance."""
import pytest
from shared.domain.ports import PatentQueryPort, ProjectQueryPort, PublicationQueryPort


def test_patent_query_port_is_abstract():
    with pytest.raises(TypeError):
        PatentQueryPort()


def test_project_query_port_is_abstract():
    with pytest.raises(TypeError):
        ProjectQueryPort()


def test_publication_query_port_is_abstract():
    with pytest.raises(TypeError):
        PublicationQueryPort()
