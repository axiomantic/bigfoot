"""C2-T7: UnsafePassthroughError pedagogical message.

The error message must include enough framing for a fresh user to recognize
the problem and have at least one immediate fix to try.
"""

from __future__ import annotations


def test_message_contains_pedagogical_text() -> None:
    """C2-T7: The exception message names the plugin, explains the cause,
    and offers actionable fixes including switching guard to error.

    ESCAPE: test_message_contains_pedagogical_text
      CLAIM: UnsafePassthroughError("subprocess:run", "subprocess").args[0]
             contains the plugin name, the phrase
             "doesn't support outside-sandbox passthrough", and the suggestion
             "set guard='error'".
      PATH:  UnsafePassthroughError.__init__ -> _build_message().
      CHECK: Each substring is present in the constructed message.
      MUTATION: Dropping the plugin name, dropping the pedagogical phrase, or
                rewording "set guard='error'" to something else (e.g.
                "guard=error") would each fail one of the substring checks.
      ESCAPE: A message that contains all three substrings but is otherwise
              gibberish would pass; the assertion is intentionally narrow to
              the user-recoverable framing rather than the prose.
    """
    from tripwire._errors import UnsafePassthroughError

    err = UnsafePassthroughError(source_id="subprocess:run", plugin_name="subprocess")
    msg = err.args[0]

    assert "doesn't support outside-sandbox passthrough" in msg, msg
    assert "set guard='error'" in msg, msg
    assert "subprocess" in msg, msg
    # C5: When user_frame is omitted the message renders the canonical
    # "<unknown call site>" placeholder, mirroring GuardedCallError.
    assert "at <unknown call site>" in msg, msg
    assert 'OUTSIDE any "with tripwire:" block' in msg, msg
