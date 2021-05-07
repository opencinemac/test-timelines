import dataclasses
import decimal
import fractions
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as et

from typing import Dict, List, NamedTuple


@dataclasses.dataclass
class TimebaseInfo:
    """TimebaseInfo details the framerate/timebase of an event or object."""

    # timebase is is the timebase value of the object, or the rate at which timecode
    # is being calculated. It may or may not be identical to the framerate.
    timebase: int

    # ntsc is whether this is an ntsc-style timebase.
    ntsc: bool

    # drop_frame is whether this timebase results in drop-frame style timecode.
    drop_frame: bool

    # framerate is the frame rate at which the media is playing back.
    framerate: fractions.Fraction

    @classmethod
    def from_element(cls, elm: et.Element) -> "TimebaseInfo":
        """
        from element parses a new TimebaseInfo instance from a FCP7XML <timecode/>
        element.
        """
        timebase_elm = elm.find("./rate/timebase")
        assert timebase_elm is not None
        assert timebase_elm.text is not None
        timebase = int(timebase_elm.text)

        ntsc_elm = elm.find("./rate/ntsc")
        assert ntsc_elm is not None
        assert ntsc_elm.text is not None
        ntsc = ntsc_elm.text == "TRUE"

        drop_frame_elm = elm.find("./displayformat")
        assert drop_frame_elm is not None
        assert drop_frame_elm.text is not None
        drop_frame = drop_frame_elm.text == "DF"

        if ntsc:
            frame_rate = fractions.Fraction(timebase * 1000, 1001)
        else:
            frame_rate = fractions.Fraction(timebase)

        return TimebaseInfo(
            timebase=timebase,
            ntsc=ntsc,
            drop_frame=drop_frame,
            framerate=frame_rate,
        )


@dataclasses.dataclass
class _TimecodeElementInfo:
    """_TimecodeElementInfo is the parsed data from an FCP7XML <timecode/> element."""

    # base is the timebase data.
    base: TimebaseInfo

    # timecode is the timecode string from the <string/> element.
    timecode: str

    # frame is the frame number from the <frame/> element.
    frame: int

    @classmethod
    def from_element(cls, elm: et.Element) -> "_TimecodeElementInfo":
        """
        from_element parses a _TimecodeElementInfo instance from an FCP7XML
        <timecode/> element.
        """
        timecode_text = elm.findtext("./string")
        assert timecode_text is not None

        frame_text = elm.findtext("./frame")
        assert frame_text is not None
        frame = int(frame_text)

        return cls(
            base=TimebaseInfo.from_element(elm),
            timecode=timecode_text,
            frame=frame,
        )


@dataclasses.dataclass
class TimecodeInfo:
    """TimecodeInfo holds all the timecode representations for a timecode event."""

    # Timebase rate at which timecode is being calculated. In NTSC cases, it will not
    # match frame_rate_frac (ex: 24).
    timebase: int
    # ntsc is whether timecode should be calculated via NTSC representation.
    ntsc: bool
    # drop_frame is whether this timecode is returned as drop-frame.
    drop_frame: bool
    # frame_rate_frac is the frame rate as a fractional value
    # (ex: 24000/1001 for 23.98).
    frame_rate_frac: str

    # timecode is the timecode string parsed from the edl (ex: 01:00:00:00).
    timecode: str
    # frame is the frame number adjusted by start time parse from the FCP7XML
    # (ex: 86400).
    frame: int
    # frame_xml_raw is the raw value from the FCP7XML NOT adjusted by start time.
    # (ex: 0).
    frame_xml_raw: int
    # seconds_rational is a rational representation of the of real-world seconds this
    # timecode represents (ex: '18018/5').
    seconds_rational: str
    # seconds_decimal is a decimal representation of the real-world seconds this
    # timecode represents (ex: '3603.6')
    seconds_decimal: str
    # ppro_ticks is the Adobe Premiere Pro Ticks value this timecode's real-world time
    # interval would be represented by (ex: 915372057600000).
    ppro_ticks: int
    # ppro_ticks_xml_raw is the raw Adobe Premiere Pro ticks value parsed from the
    # FCP7XML. It is un-adjusted by media start time (ex: 0).
    ppro_ticks_xml_raw: int
    # feet_and_frames is the timecode represented by the number of eet and frames that
    # would have elapsed on 35mm, 4-perf film (ex: 5400+00).
    feet_and_frames: str
    # runtime is the formatted string of the real-world time time elapsed
    # (ex: 01:00:00.6).
    runtime: str

    @classmethod
    def from_element(cls, elm: et.Element) -> "TimecodeInfo":
        """from_element parses a TimecodeInfo from an FCP7XML <timecode/> element."""
        xml_info = _TimecodeElementInfo.from_element(elm)
        return cls._from_xml_info(xml_info)

    @classmethod
    def from_info(
        cls,
        timecode: str,
        frames: int,
        frames_raw: int,
        ppro_ticks_raw: int,
        timebase: TimebaseInfo,
    ) -> "TimecodeInfo":
        """
        from_info returns a TimecodeInfo instance based on some parsed / processed info.
        All missing data will be derived.
        """
        seconds_rational = frames / timebase.framerate
        seconds_decimal = decimal.Decimal(seconds_rational.numerator) / decimal.Decimal(
            seconds_rational.denominator
        )

        ppro_ticks = round(seconds_rational * 254016000000)

        seconds = round(seconds_decimal, 9)
        hours, seconds = divmod(seconds, 60 * 60)
        minutes, seconds = divmod(seconds, 60)
        seconds, fractal = divmod(seconds, 1)

        if fractal == 0:
            fractal_str = ""
        else:
            fractal_str = "." + str(fractal).split(".")[-1].rstrip("0")

        runtime = (
            f"{str(hours).zfill(2)}:{str(minutes).zfill(2)}:"
            f"{str(seconds).zfill(2)}{fractal_str}"
        )

        feet, feet_frames = divmod(frames, 16)
        feet_and_frames = f"{feet}+{str(feet_frames).zfill(2)}"

        return cls(
            timebase=timebase.timebase,
            ntsc=timebase.ntsc,
            drop_frame=timebase.drop_frame,
            frame_rate_frac=str(timebase.framerate),
            timecode=timecode,
            frame=frames,
            frame_xml_raw=frames_raw,
            ppro_ticks=ppro_ticks,
            ppro_ticks_xml_raw=ppro_ticks_raw,
            seconds_rational=str(seconds_rational),
            seconds_decimal=str(seconds_decimal),
            feet_and_frames=feet_and_frames,
            runtime=runtime,
        )

    @classmethod
    def _from_xml_info(cls, elm_info: _TimecodeElementInfo) -> "TimecodeInfo":
        """
        _from_xml_info returns a TimecodeInfo instance from a _TimecodeElementInfo
        instance.
        """
        return cls.from_info(
            elm_info.timecode,
            elm_info.frame,
            frames_raw=elm_info.frame,
            ppro_ticks_raw=-1,
            timebase=elm_info.base,
        )


@dataclasses.dataclass
class EventInfo:
    """EventInfo holds the data for a timeline event."""
    # duration_frames is the number of frames this event covers.
    duration_frames: int
    # source_in holds the timecode info for the source media at the in-point of the
    # event.
    source_in: TimecodeInfo
    # source_out holds the timecode info for the source media at the out-point of the
    # event.
    source_out: TimecodeInfo
    # record_in holds the timecode info for the sequence/timeline at the in-point of
    # the event.
    record_in: TimecodeInfo
    # record_in holds the timecode info for the sequence/timeline at the out-point of
    # the event.
    record_out: TimecodeInfo


@dataclasses.dataclass
class SequenceInfo:
    """
    SequenceInfo contains information about a sequence of timecode events from an NLE
    timeline.
    """
    # start_time holds timecode information about the sequence start time.
    start_time: TimecodeInfo
    # total_duration_frames holds the total duration of the sequence in frame count.
    total_duration_frames: int
    # events contains a list of events
    events: List[EventInfo]


def parse_sequence_info(root: et.ElementTree) -> SequenceInfo:
    """parse_sequence_info parses SequenceInfo from an FCP7XML."""

    total_duration_frames_text = root.findtext("./sequence/duration")
    assert total_duration_frames_text is not None
    print("TOTAL DURATION:", total_duration_frames_text)

    start_time_elm = root.find("./sequence/timecode")
    assert start_time_elm is not None
    start_time_info = TimecodeInfo.from_element(start_time_elm)

    seq_info = SequenceInfo(
        start_time=start_time_info,
        total_duration_frames=int(total_duration_frames_text),
        events=list(),
    )

    return seq_info


# event_regex is the regex or parsing an event from a CMX3600 EDL. It only captures
# event timecodes, not event numbers or any special properties like markers or respeeds.
event_regex = re.compile(
    r"(?P<source_in>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))\s+"
    r"(?P<source_out>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))\s+"
    r"(?P<record_in>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))\s+"
    r"(?P<record_out>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))",
)


def event_list_from_edl(edl_path: pathlib.Path) -> List[re.Match]:
    """event_list_from_edl generates a list of event_regex matches from a CMX3600 EDL"""
    with edl_path.open("r") as f:
        return [x for x in event_regex.finditer(f.read())]


def write_out(xml_path: pathlib.Path, info: SequenceInfo) -> None:
    """
    write_out writes a json of our parsed data out to the same directory and filename
    of our source XML with '.json' as the extension.
    """
    source_parent = xml_path.parent
    source_name = xml_path.name.split(".")[0]

    out_file = source_parent / f"{source_name}.json"

    print(f"WRITING JSON TO: '{out_file}'")

    with out_file.open("w") as f:
        json.dump(dataclasses.asdict(info), f, indent=4)


def collect_event_info(
    edl_events: List[re.Match],
    xml_events: List[et.Element],
    start_frame: int,
) -> List[EventInfo]:
    """
    collect_event_info combines the events from a list of EDL regex matches and FCP7XML
    <clipitem/> elements in order to have a more complete set of timecode
    representations generated from an outside program.
    """
    class FileInfo(NamedTuple):
        base: TimebaseInfo
        start_frame: int

    event_bases: Dict[str, FileInfo] = dict()
    events: List[EventInfo] = list()

    for edl_event, xml_event in zip(edl_events, xml_events):
        file_elm = xml_event.find("./file")
        assert file_elm is not None

        file_id = file_elm.attrib["id"]

        try:
            file_info = event_bases[file_id]
        except KeyError:
            base_elm = xml_event.find("./file/timecode")
            assert base_elm is not None
            base_info = TimebaseInfo.from_element(base_elm)
            file_start_frame = _find_int(base_elm, "./frame")

            file_info = FileInfo(base=base_info, start_frame=file_start_frame)
            event_bases[file_id] = file_info

        source_in_frames_raw = _find_int(xml_event, "in")
        source_in_frames = source_in_frames_raw + file_info.start_frame

        source_out_frames_raw = _find_int(xml_event, "out")
        source_out_frames = source_out_frames_raw + file_info.start_frame

        record_in_frames_raw = _find_int(xml_event, "start")
        record_in_frames = record_in_frames_raw + start_frame

        record_out_frames_raw = _find_int(xml_event, "end")
        record_out_frames = record_out_frames_raw + start_frame

        source_in_tc = edl_event.group("source_in")
        source_out_tc = edl_event.group("source_out")
        record_in_tc = edl_event.group("record_in")
        record_out_tc = edl_event.group("record_out")

        source_in_ppro_ticks_raw = _find_int(xml_event, "pproTicksIn")
        source_out_ppro_ticks_raw = _find_int(xml_event, "pproTicksOut")

        duration = record_out_frames - record_in_frames
        assert duration == source_out_frames - source_in_frames

        event_info = EventInfo(
            duration_frames=duration,
            source_in=TimecodeInfo.from_info(
                source_in_tc,
                source_in_frames,
                source_in_frames_raw,
                source_in_ppro_ticks_raw,
                file_info.base,
            ),
            source_out=TimecodeInfo.from_info(
                source_out_tc,
                source_out_frames,
                source_out_frames_raw,
                source_out_ppro_ticks_raw,
                file_info.base,
            ),
            record_in=TimecodeInfo.from_info(
                record_in_tc,
                record_in_frames,
                record_in_frames_raw,
                -1,
                file_info.base,
            ),
            record_out=TimecodeInfo.from_info(
                record_out_tc,
                record_out_frames,
                record_out_frames_raw,
                -1,
                file_info.base,
            ),
        )

        events.append(event_info)

    return events


def _find_int(elm: et.Element, path: str) -> int:
    """
    _find_int find an integer value from an xml element at path, or raises if the path
    does not exist of the text value cannot be converted into an int.
    """
    int_text = elm.findtext(path)
    assert int_text is not None
    return int(int_text)


def main() -> None:
    """
    main is our main script. It reads in, combines, and writes our event timecode data
    from an FCP7XML and CMX3600 EDL of the same sequence.
    """

    # Get our XML and EDL paths.
    source_xml = pathlib.Path(sys.argv[1])
    source_edl = pathlib.Path(sys.argv[2])

    # Parse the xml into some high-level sequence information.
    xml_tree = et.parse(source_xml)
    info = parse_sequence_info(xml_tree)

    # get a list of regex matches from a our CMX3600 EDL.
    edl_events = event_list_from_edl(source_edl)
    # get a list of <clipitem/> elements from our FCP7XML.
    xml_events = xml_tree.findall("./sequence/media/video/track/clipitem")

    # Assert that we got the same number of elements from each cutlist.
    edl_event_count = len(edl_events)
    xml_event_count = len(xml_events)
    if edl_event_count != xml_event_count:
        raise RuntimeError(
            f"event count from EDL ({edl_event_count}) "
            f"and XML ({xml_event_count}) do not match",
        )

    print("EVENTS FOUND:", len(edl_events))

    events = collect_event_info(edl_events, xml_events, info.start_time.frame)
    assert len(events) == len(edl_events)

    info.events = events

    write_out(source_xml, info)


if __name__ == "__main__":
    main()
