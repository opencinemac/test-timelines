# timeline-tests

timeline-tests is a set of test files for testing timecode and timelines. These files 
are kept in their own repo to be shared among multiple implementation of the same
domain.

# Sub-folders

## Many Basic Edits

start tc: 01:00:00:00
duration: 00:13:35:00
events: 215

This timeline contains 215 events with no respeeds, transitions or other effects and no 
black space. It is primarily meant as a way to generate table tests for timecode 
libraries.
