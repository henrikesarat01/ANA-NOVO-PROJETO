from ana_saga_cli.config import AppConfig
from ana_saga_cli.sales.conversation_service import ConversationService


def test_mock_response_is_not_empty():
    service = ConversationService(AppConfig(provider="mock"))
    result = service.respond("como funciona esse sistema?")
    assert result.response
    assert result.stage_id
    assert service.state.lead_summary
