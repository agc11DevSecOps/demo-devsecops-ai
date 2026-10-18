package ops.copilot.admission

# Model admission for the S1 supply-chain boundary. The decision is a pure
# function of the artifact facts; the default is deny. An artifact is admitted
# only when it uses a safe (non-executable) format, carries a verified signature
# and ships a complete AI BOM.

default allow := false

allow if {
	input.artifact.safe_format == true
	input.artifact.signature_ok == true
	input.artifact.aibom_complete == true
}
