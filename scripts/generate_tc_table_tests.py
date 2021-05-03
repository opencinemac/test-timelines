import dataclasses
import decimal
import fractions
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as et

from typing import Dict, Union, List


@dataclasses.dataclass
class TimebaseInfo:
    timebase: int
    ntsc: bool
    drop_frame: bool
    framerate: fractions.Fraction

    @classmethod
    def from_element(cls, elm: et.Element) -> "TimebaseInfo":
        timebase = int(elm.find("./rate/timebase").text)
        ntsc = elm.find("./rate/ntsc").text == "TRUE"
        drop_frame = elm.find('./displayformat').text == "DF"

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
    base: TimebaseInfo

    timecode: str
    frame: int

    @classmethod
    def from_element(cls, elm: et.Element) -> "_TimecodeElementInfo":

        timecode = elm.find('./string').text
        frame = int(elm.find('./frame').text)

        return cls(
            base=TimebaseInfo.from_element(elm),
            timecode=timecode,
            frame=frame,
        )


@dataclasses.dataclass
class TimecodeInfo:
    timebase: int
    ntsc: bool
    drop_frame: bool
    frame_rate_frac: str

    timecode: str
    frame: int
    seconds_rational: str
    seconds_decimal: str
    runtime: str

    @classmethod
    def from_element(cls, elm: et.Element) -> "TimecodeInfo":
        xml_info = _TimecodeElementInfo.from_element(elm)
        return cls._from_xml_info(xml_info)

    @classmethod
    def from_info(
        cls, timecode: str, frames: int, timebase: TimebaseInfo,
    ) -> "TimecodeInfo":
        seconds_rational = frames / timebase.framerate
        seconds_decimal = (
            decimal.Decimal(seconds_rational.numerator) /
            decimal.Decimal(seconds_rational.denominator)
        )

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

        return cls(
            timebase=timebase.timebase,
            ntsc=timebase.ntsc,
            drop_frame=timebase.drop_frame,
            frame_rate_frac=str(timebase.framerate),

            timecode=timecode,
            frame=frames,
            seconds_rational=str(seconds_rational),
            seconds_decimal=str(seconds_decimal),
            runtime=runtime,
        )

    @classmethod
    def _from_xml_info(cls, elm_info: _TimecodeElementInfo) -> "TimecodeInfo":
        return cls.from_info(elm_info.timecode, elm_info.frame, elm_info.base)


@dataclasses.dataclass
class EventInfo:
    duration_frames: int
    source_in: TimecodeInfo
    source_out: TimecodeInfo
    record_in: TimecodeInfo
    record_out: TimecodeInfo


@dataclasses.dataclass
class SequenceInfo:
    start_time: TimecodeInfo
    total_duration_frames: int
    events: List[EventInfo]


def parse_sequence_info(root: et.ElementTree) -> SequenceInfo:
    total_duration_frames = int(root.find("./sequence/duration").text)
    print("TOTAL DURATION:", total_duration_frames)

    start_time_elm = root.find("./sequence/timecode")
    start_time_info = TimecodeInfo.from_element(start_time_elm)

    seq_info = SequenceInfo(
        start_time=start_time_info,
        total_duration_frames=total_duration_frames,
        events=list()
    )

    return seq_info


event_regex = re.compile(
    r"(?P<source_in>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))\s+"
    r"(?P<source_out>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))\s+"
    r"(?P<record_in>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))\s+"
    r"(?P<record_out>([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2}))",
)


def event_list_from_edl(edl_path: pathlib.Path) -> List[re.Match]:
    with edl_path.open('r') as f:
        return [x for x in event_regex.finditer(f.read())]


def write_out(xml_path: pathlib.Path, info: SequenceInfo) -> None:
    source_parent = xml_path.parent
    source_name = xml_path.name.split(".")[0]

    out_file = source_parent / f"{source_name}.json"

    print(f"WRITING JSON TO: '{out_file}'")

    with out_file.open('w') as f:
        json.dump(dataclasses.asdict(info), f, indent=4)


def collect_event_info(
    edl_events: List[re.Match], xml_events: List[et.Element],
) -> List[EventInfo]:
    event_bases: Dict[str, TimebaseInfo] = dict()
    events: List[EventInfo] = list()

    for edl_event, xml_event in zip(edl_events, xml_events):
        file_elm = xml_event.find("./file")
        file_id = file_elm.attrib["id"]

        try:
            base_info = event_bases[file_id]
        except KeyError:
            base_info = TimebaseInfo.from_element(xml_event.find("./file/timecode"))
            event_bases[file_id] = base_info

        duration = int(xml_event.find("duration").text)

        source_in_frames = int(xml_event.find("in").text)
        source_out_frames = int(xml_event.find("out").text)
        record_in_frames = int(xml_event.find("start").text)
        record_out_frames = int(xml_event.find("end").text)

        source_in_tc = edl_event.group("source_in")
        source_out_tc = edl_event.group("source_out")
        record_in_tc = edl_event.group("record_in")
        record_out_tc = edl_event.group("record_out")

        event_info = EventInfo(
            duration_frames=duration,
            source_in=TimecodeInfo.from_info(source_in_tc, source_in_frames, base_info),
            source_out=TimecodeInfo.from_info(
                source_out_tc, source_out_frames, base_info,
            ),
            record_in=TimecodeInfo.from_info(record_in_tc, record_in_frames, base_info),
            record_out=TimecodeInfo.from_info(
                record_out_tc, record_out_frames, base_info,
            ),
        )

        events.append(event_info)

    return events


def main() -> None:
    source_xml = pathlib.Path(sys.argv[1])
    source_edl = pathlib.Path(sys.argv[2])

    xml_tree = et.parse(source_xml)
    info = parse_sequence_info(xml_tree)

    edl_events = event_list_from_edl(source_edl)
    xml_events = xml_tree.findall("./sequence/media/video/track/clipitem")

    assert len(edl_events) == len(xml_events)

    print("EVENTS FOUND:", len(edl_events))

    events = collect_event_info(edl_events, xml_events)
    assert len(events) == len(edl_events)

    info.events = events

    write_out(source_xml, info)


if __name__ == '__main__':
    main()
