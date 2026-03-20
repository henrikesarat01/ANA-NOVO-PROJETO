"""Test the Turn 2 enforcement scenario from ana_debug_20260320_141841."""
from ana_saga_cli.sales.conversation_service import ConversationService
from ana_saga_cli.domain.models import ConversationState, MessageTurn
from ana_saga_cli.llm.mock_client import MockLLMClient
from ana_saga_cli.config import AppConfig

service = ConversationService(AppConfig(stage_debug=True))
service.state = ConversationState(stage_id="etapa_01_abertura")
service.state.response_policy = {
    "response_mode": "explain",
    "question_budget": 0,
    "question_goal": "none",
    "question_type": "none",
    "must_ask": False,
    "answer_now_instead_of_asking": True,
    "social_opening_only": True,
}
service.state.neural_state = {"topic_domain": "social_lateral", "transition_permission": "hold"}
service.state.turns = [
    MessageTurn(role="user", content="faaaaala cu de apertar linguica, tudo certo ? kkkk"),
    MessageTurn(role="assistant", content="faaaaalaaa, seu figura tudo certo por aqui kkkk tamo junto"),
    MessageTurn(role="user", content="voce terminou aquele seu sistema de whatsapp ?"),
]
service.state.last_assistant_message = "faaaaalaaa, seu figura tudo certo por aqui kkkk tamo junto"
service.state.turn_count = 2

response = "Terminei sim kkk ja ta rodando \u2014 so muda bastante de um caso pro outro, entao me conta rapidinho como voces usam WhatsApp hoje ai."
final, reason = service._enforce_final_response_policy_with_trace(response)
print(f"Original: {response}")
print(f"Final:    {final}")
print(f"Reason:   {reason}")

# Also test Turn 1 scenario (should pass through)
service2 = ConversationService(AppConfig(stage_debug=True))
service2.state = ConversationState(stage_id="etapa_01_abertura")
service2.state.response_policy = {
    "response_mode": "explain",
    "question_budget": 0,
    "question_goal": "none",
    "question_type": "none",
    "must_ask": False,
    "answer_now_instead_of_asking": True,
    "social_opening_only": True,
}
service2.state.neural_state = {"topic_domain": "social_lateral", "transition_permission": "hold"}
service2.state.turns = [
    MessageTurn(role="user", content="faaaaala cu de apertar linguica, tudo certo ? kkkk"),
]
service2.state.last_assistant_message = ""
service2.state.turn_count = 1

response2 = "faaaaalaaa, seu figura tudo certo por aqui kkkk tamo junto"
final2, reason2 = service2._enforce_final_response_policy_with_trace(response2)
print(f"\nOriginal: {response2}")
print(f"Final:    {final2}")
print(f"Reason:   {reason2}")
