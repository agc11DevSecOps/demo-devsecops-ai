package ops.copilot_admission_test

import data.ops.copilot.admission

admit(req) := result if {
	result := admission.allow with input as req
}

test_complete_artifact_admitted if {
	admit({"artifact": {"safe_format": true, "signature_ok": true, "aibom_complete": true}})
}

test_unsafe_format_denied if {
	not admit({"artifact": {"safe_format": false, "signature_ok": true, "aibom_complete": true}})
}

test_bad_signature_denied if {
	not admit({"artifact": {"safe_format": true, "signature_ok": false, "aibom_complete": true}})
}

test_incomplete_aibom_denied if {
	not admit({"artifact": {"safe_format": true, "signature_ok": true, "aibom_complete": false}})
}

test_missing_facts_denied if {
	not admit({"artifact": {"safe_format": true}})
}
