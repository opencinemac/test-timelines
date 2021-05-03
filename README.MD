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
