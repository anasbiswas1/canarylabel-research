import toolcall as tc

NAMES = {"send_money", "search_emails", "get_balance"}


def test_strict_form():
    assert tc.parse('Sure.\n<function=send_money>{"recipient": "US1", "amount": 10}</function>') == \
        ("send_money", {"recipient": "US1", "amount": 10})


def test_python_literals_single_quotes_and_trailing_comma():
    assert tc.parse("<function=search_emails>{'query': 'bill', 'unread': True, 'sender': None,}</function>") == \
        ("search_emails", {"query": "bill", "unread": True, "sender": None})


def test_text_after_the_object_and_no_closing_tag():
    assert tc.parse('<function=search_emails>{"query": "a {b}"} and then I will reply') == \
        ("search_emails", {"query": "a {b}"})


def test_code_fence_and_newlines_in_strings():
    out = tc.parse('<function=send_money>\n```json\n{"recipient": "US1", "subject": "line one\nline two"}\n```\n</function>')
    assert out == ("send_money", {"recipient": "US1", "subject": "line one\nline two"})


def test_empty_arguments_and_python_call_form():
    assert tc.parse("<function=get_balance></function>") == ("get_balance", {})
    assert tc.parse("<function=get_balance>{}</function>") == ("get_balance", {})
    assert tc.parse("<function=send_money(recipient='US1', amount=5)>") == ("send_money", {"recipient": "US1", "amount": 5})


def test_wrapped_parameters_are_unwrapped():
    assert tc.parse('<function=send_money>{"name": "send_money", "parameters": {"amount": 1}}</function>') == \
        ("send_money", {"amount": 1})


def test_native_forms_only_for_known_tools():
    assert tc.parse('<tool_call>\n{"name": "get_balance", "arguments": {}}\n</tool_call>', NAMES) == ("get_balance", {})
    assert tc.parse('{"name": "search_emails", "parameters": {"query": "x"}}', NAMES) == ("search_emails", {"query": "x"})
    assert tc.parse('{"name": "rm_rf", "parameters": {}}', NAMES) is None
    assert tc.parse('The balance is {"amount": 3}.', NAMES) is None


def test_no_call():
    assert tc.parse("I have finished the task.") is None
    assert tc.parse("<function=send_money>{broken</function>") is None
