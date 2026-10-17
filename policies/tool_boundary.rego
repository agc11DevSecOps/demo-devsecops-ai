package ops.copilot

# Tool authorization for the S5 boundary. The decision is a pure function of the
# requested action and a machine-built context; the default is deny. Callers map
# an allowed `delete_branch` to a human-review outcome and never treat `allow`
# alone as permission to mutate state.

default allow := false

allow if {
	input.context.descriptor_ok == true
	input.action == "read_ticket"
}

allow if {
	input.context.descriptor_ok == true
	input.action == "search_docs"
}

allow if {
	input.context.descriptor_ok == true
	input.action == "delete_branch"
	input.context.grant_valid == true
}
