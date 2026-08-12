from finance.data.action_history_provider import ACTION_CLASSES
from finance.models.action_history import ACTION_TITLES, action_title


def test_every_registered_action_has_a_hebrew_title():
    # a new action type registered for deserialization must also get a title,
    # or the action-history view shows a raw English key (the mortgage bug).
    missing = [name for name in ACTION_CLASSES if name not in ACTION_TITLES]
    assert missing == [], f"action kinds with no title: {missing}"


def test_no_titles_for_unregistered_actions():
    orphans = [name for name in ACTION_TITLES if name not in ACTION_CLASSES]
    assert orphans == [], f"titles for unknown actions: {orphans}"


def test_mortgage_actions_are_titled_not_raw():
    # the drift this fixed: the two label maps never got the mortgage/asset kinds
    assert action_title("add_mortgage") == "הוספת נכס"
    assert action_title("edit_mortgage") == "עריכת נכס"
    assert action_title("delete_mortgage") == "מחיקת נכס"


def test_unknown_action_falls_back_to_raw_key():
    assert action_title("something_new") == "something_new"
    assert action_title("") == "פעולה"
