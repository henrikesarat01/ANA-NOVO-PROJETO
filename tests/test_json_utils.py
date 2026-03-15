from ana_saga_cli.llm.json_utils import parse_last_json_object


def test_parse_last_json_object_returns_last_valid_dict() -> None:
    raw = '''
    Exemplo de formato:
    {"question_budget": 1, "response_mode": "ask"}

    Resposta final:
    {"question_budget": 0, "response_mode": "pricing_answer", "main_intention": "pricing_answer"}
    '''

    payload = parse_last_json_object(raw)

    assert payload == {
        "question_budget": 0,
        "response_mode": "pricing_answer",
        "main_intention": "pricing_answer",
    }


def test_parse_last_json_object_returns_empty_dict_when_no_valid_json_exists() -> None:
    assert parse_last_json_object("sem json valido aqui") == {}