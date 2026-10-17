package ops.copilot_test

import data.ops.copilot

decide(req) := result if {
	result := copilot.allow with input as req
}

test_read_ticket_allowed if {
	decide({"action": "read_ticket", "context": {"descriptor_ok": true, "grant_valid": false}})
}

test_search_docs_allowed if {
	decide({"action": "search_docs", "context": {"descriptor_ok": true, "grant_valid": false}})
}

test_descriptor_drift_denies_reads if {
	not decide({"action": "read_ticket", "context": {"descriptor_ok": false, "grant_valid": false}})
}

test_delete_branch_without_grant_denied if {
	not decide({"action": "delete_branch", "context": {"descriptor_ok": true, "grant_valid": false}})
}

test_delete_branch_with_valid_grant_allowed if {
	decide({"action": "delete_branch", "context": {"descriptor_ok": true, "grant_valid": true}})
}

test_delete_branch_with_grant_but_drift_denied if {
	not decide({"action": "delete_branch", "context": {"descriptor_ok": false, "grant_valid": true}})
}

test_export_customers_always_denied if {
	not decide({"action": "export_customers", "context": {"descriptor_ok": true, "grant_valid": true}})
}

test_unknown_action_denied if {
	not decide({"action": "drop_database", "context": {"descriptor_ok": true, "grant_valid": true}})
}

test_missing_context_denied if {
	not decide({"action": "read_ticket"})
}
