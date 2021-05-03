.PHONY: timecode-tables
timecode-tables:
	python3 ./scripts/generate_tc_table_tests.py "./Many Basic Edits/Many Basic Edits.xml" "./Many Basic Edits/Many Basic Edits.edl"
