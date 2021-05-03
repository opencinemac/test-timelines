# timeline-tests

timeline-tests is a set of test files for testing timecode and timelines. These files 
are kept in their own repo to be shared among multiple implementation of the same
domain.

# Sequence Folders

Each sequence folder contains a set of cut list formats all generated from the same 
source sequence.

Sequence folders are organized by the NLE that generated them: '[NLE]/[TIMELINE]' 

## PPRO/Many Basic Edits

start tc: 01:00:00:00
duration: 00:13:35:00
events: 215

This timeline contains 215 events with no respeeds, transitions or other effects and no 
black space. It is primarily meant as a way to generate tabl`e tests for timecode 
libraries.

**'Many Basic Edits.json'** is a semi-parsed version combining information from the .edl
and .xml for deriving table-tests for timecode libraries. Timecode string values are
pulled from the EDL and lined up with frame representation and time base info pulled
from the FPC7XML.

# Scripts

The ``'./Scripts'`` directory contains a number of scripts for pulling information from
these scripts.

## generate_tc_table_tests.py

Can generate a json file to power timecode table-tests by combining information from
an FCP7XML and EDL of the same sequence.

Sequences must contain only 1 video track, and should not have respeed effects or 
transitions.

usage: 

```shell
python3 generate_tc_table_tests.py [xml_list_path] [edl_list_path]
```

Outputs: json of the same name as the xml in the same directory.
