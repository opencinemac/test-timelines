.PHONY: timecode-tables
timecode-tables:
	python3 ./scripts/generate_tc_table_tests.py "./PPRO/Many Basic Edits/Many Basic Edits.xml" "./PPRO/Many Basic Edits/Many Basic Edits.edl"
