"""
LogRaptorX - Core Parsing Engine
High-performance, multi-threaded Windows log parser
Supports binary .evtx via python-evtx
Developer: Kennedy Aikohi
GitHub   : https://github.com/kennedy-aikohi
LinkedIn : https://www.linkedin.com/in/aikohikennedy/
"""

import re
import os
import csv
import gzip
import time
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path


# ---------------------------------------------
#  Data Models
# ---------------------------------------------

@dataclass
class LogEntry:
    line_number: int = 0
    timestamp: str = ""
    level: str = ""
    source: str = ""
    event_id: str = ""
    message: str = ""
    raw: str = ""
    file_path: str = ""
    extra: Dict[str, str] = field(default_factory=dict)

    def to_csv_row(self) -> List[str]:
        return [
            str(self.line_number),
            self.timestamp,
            self.level,
            self.source,
            self.event_id,
            self.message,
            self.file_path,
            self.raw[:300],
        ]

    @staticmethod
    def csv_headers() -> List[str]:
        return ["Line#", "Timestamp", "Level", "Source",
                "EventID", "Message", "FilePath", "Raw"]


@dataclass
class ParseResult:
    entries: List[LogEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_lines: int = 0
    parsed_count: int = 0
    skipped_count: int = 0
    duration_seconds: float = 0.0
    file_path: str = ""

    @property
    def parse_rate(self) -> float:
        if self.duration_seconds > 0:
            return self.parsed_count / self.duration_seconds
        return 0.0


# ---------------------------------------------
#  EVTX Binary Parser
# ---------------------------------------------

# XML namespace used in EVTX records
_NS = "http://schemas.microsoft.com/win/2004/08/events/event"

# Map EVTX Level integer -> human label
_EVTX_LEVEL = {
    0: "INFO",
    1: "CRITICAL",
    2: "ERROR",
    3: "WARN",
    4: "INFO",
    5: "DEBUG",
}

# Map Keywords hex value -> label
_EVTX_KEYWORDS = {
    0x8010000000000000: "AUDIT-FAIL",
    0x8020000000000000: "AUDIT-OK",
}

def _xt(node, tag):
    """Get text from a child element in the EVTX namespace."""
    child = node.find(f"{{{_NS}}}{tag}")
    return child.text if child is not None and child.text else ""

def _xta(node, tag, attr):
    """Get attribute from a child element in the EVTX namespace."""
    child = node.find(f"{{{_NS}}}{tag}")
    return child.get(attr, "") if child is not None else ""


def parse_evtx_file(filepath: str, filters: Dict, progress_cb=None) -> ParseResult:
    """
    Parse a binary Windows Event Log (.evtx) file.
    Uses python-evtx to decode the binary format, then extracts
    fields from the embedded XML in each record.
    """
    result = ParseResult(file_path=filepath)
    t0 = time.perf_counter()

    try:
        import Evtx.Evtx as evtx_lib
    except ImportError:
        result.errors.append(
            "python-evtx not installed. Run: pip install python-evtx"
        )
        return result

    kw_filter = filters.get("keyword", "").lower()
    level_filter = filters.get("levels", set())

    try:
        with evtx_lib.Evtx(filepath) as log:
            # Count total records for progress
            try:
                total = log.get_file_header().current_record_number()
            except Exception:
                total = 0

            record_num = 0
            for chunk in log.chunks():
                for record in chunk.records():
                    record_num += 1
                    result.total_lines += 1

                    try:
                        xml_str = record.xml()
                        entry = _parse_evtx_record(xml_str, record_num, filepath)
                    except Exception as ex:
                        result.skipped_count += 1
                        continue

                    if entry is None:
                        result.skipped_count += 1
                        continue

                    # Apply filters
                    if level_filter and entry.level not in level_filter:
                        result.skipped_count += 1
                        continue
                    if kw_filter and kw_filter not in (
                        entry.message + entry.source + entry.event_id
                    ).lower():
                        result.skipped_count += 1
                        continue

                    # Security keyword flag
                    if _SECURITY_RE.search(entry.message):
                        entry.extra["security_flag"] = "1"

                    result.entries.append(entry)
                    result.parsed_count += 1

                    if progress_cb and record_num % 500 == 0:
                        pct = int(record_num / total * 100) if total > 0 else 0
                        progress_cb(pct, f"Parsed {result.parsed_count:,} events...")

    except Exception as e:
        result.errors.append(f"EVTX read error: {e}")

    result.duration_seconds = time.perf_counter() - t0
    return result


def _parse_evtx_record(xml_str: str, record_num: int, filepath: str) -> Optional[LogEntry]:
    """Parse a single EVTX XML record string into a LogEntry."""
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return None

    system = root.find(f"{{{_NS}}}System")
    if system is None:
        return None

    # Timestamp
    time_created = system.find(f"{{{_NS}}}TimeCreated")
    timestamp = ""
    if time_created is not None:
        ts = time_created.get("SystemTime", "")
        # Normalize: 2024-01-15T09:23:11.123456700Z -> 2024-01-15 09:23:11
        if "T" in ts:
            ts = ts.replace("T", " ")
            ts = ts.split(".")[0]
            ts = ts.rstrip("Z")
        timestamp = ts

    # Level
    level_node = system.find(f"{{{_NS}}}Level")
    level_val = 0
    if level_node is not None and level_node.text:
        try:
            level_val = int(level_node.text)
        except ValueError:
            pass

    # Check Keywords for Audit events
    kw_node = system.find(f"{{{_NS}}}Keywords")
    level = _EVTX_LEVEL.get(level_val, "INFO")
    if kw_node is not None and kw_node.text:
        try:
            kw_val = int(kw_node.text, 16)
            if kw_val & 0x0010000000000000:
                level = "AUDIT-FAIL"
            elif kw_val & 0x0020000000000000:
                level = "AUDIT-OK"
        except (ValueError, TypeError):
            pass

    # Source / Provider
    provider = system.find(f"{{{_NS}}}Provider")
    source = ""
    if provider is not None:
        source = provider.get("Name", "") or provider.get("EventSourceName", "")

    # Event ID
    eid_node = system.find(f"{{{_NS}}}EventID")
    event_id = eid_node.text.strip() if eid_node is not None and eid_node.text else ""

    # Computer
    computer_node = system.find(f"{{{_NS}}}Computer")
    computer = computer_node.text.strip() if computer_node is not None and computer_node.text else ""

    if source and computer:
        source_display = f"{source} ({computer})"
    else:
        source_display = source or computer

    # Message / EventData
    message_parts = []
    event_data = root.find(f"{{{_NS}}}EventData")
    if event_data is not None:
        for data in event_data:
            name = data.get("Name", "")
            val = (data.text or "").strip()
            if val:
                if name:
                    message_parts.append(f"{name}: {val}")
                else:
                    message_parts.append(val)

    # UserData fallback
    if not message_parts:
        user_data = root.find(f"{{{_NS}}}UserData")
        if user_data is not None:
            for child in user_data.iter():
                if child.text and child.text.strip():
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    message_parts.append(f"{tag}: {child.text.strip()}")

    message = "  |  ".join(message_parts) if message_parts else f"Event {event_id}"

    # Raw = condensed XML (first 400 chars)
    raw = xml_str[:400].replace("\n", " ").replace("\r", "")

    return LogEntry(
        line_number=record_num,
        timestamp=timestamp,
        level=level,
        source=source_display,
        event_id=event_id,
        message=message,
        raw=raw,
        file_path=filepath,
    )


# ---------------------------------------------
#  Pattern Library (text log formats)
# ---------------------------------------------

class PatternLibrary:

    WINDOWS_EVT = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)'
        r'\s+(?P<level>Information|Warning|Error|Critical|Verbose|Audit\s+\w+)'
        r'\s+(?P<source>[^\s]+(?:\s[^\s]+)*?)'
        r'\s+(?P<event_id>\d+)'
        r'(?:\s+(?P<message>.+))?',
        re.IGNORECASE
    )

    SYSLOG_RFC3164 = re.compile(
        r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'
        r'\s+(?P<source>\S+)'
        r'\s+(?P<process>[^\[]+)(?:\[(?P<pid>\d+)\])?:'
        r'\s*(?P<message>.+)'
    )

    SYSLOG_RFC5424 = re.compile(
        r'<(?P<priority>\d+)>'
        r'(?P<version>\d)\s+'
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)'
        r'\s+(?P<hostname>\S+)'
        r'\s+(?P<app>\S+)'
        r'\s+(?P<procid>\S+)'
        r'\s+(?P<msgid>\S+)'
        r'\s+(?P<structured>\S+)'
        r'\s*(?P<message>.*)',
        re.DOTALL
    )

    IIS_W3C = re.compile(
        r'(?P<date>\d{4}-\d{2}-\d{2})'
        r'\s+(?P<time>\d{2}:\d{2}:\d{2})'
        r'\s+(?P<server_ip>\S+)'
        r'\s+(?P<method>\S+)'
        r'\s+(?P<uri>\S+)'
        r'\s+(?P<query>\S+)'
        r'\s+(?P<port>\d+)'
        r'\s+(?P<username>\S+)'
        r'\s+(?P<client_ip>\S+)'
        r'\s+(?P<user_agent>\S+)'
        r'\s+(?P<status>\d{3})'
        r'\s+(?P<substatus>\d+)'
        r'\s+(?P<win32_status>\d+)'
        r'\s+(?P<time_taken>\d+)'
    )

    APACHE_COMBINED = re.compile(
        r'(?P<client_ip>\S+)\s+\S+\s+(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\S+)\s+(?P<uri>\S+)\s+(?P<protocol>[^"]+)"\s+'
        r'(?P<status>\d{3})\s+(?P<size>\S+)'
        r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
    )

    GENERIC_TIMESTAMP = re.compile(
        r'(?P<timestamp>'
        r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?'
        r'|\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'
        r'|\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}'
        r')'
        r'(?:\s+(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL|TRACE|NOTICE)[\s:\]]*)?'
        r'(?:\s+(?P<message>.+))?',
        re.IGNORECASE
    )

    LEVEL_MAP = {
        'information': 'INFO', 'info': 'INFO', 'notice': 'INFO',
        'verbose': 'DEBUG', 'debug': 'DEBUG', 'trace': 'DEBUG',
        'warning': 'WARN', 'warn': 'WARN',
        'error': 'ERROR', 'err': 'ERROR',
        'critical': 'CRITICAL', 'fatal': 'CRITICAL',
        'audit success': 'AUDIT-OK', 'audit failure': 'AUDIT-FAIL',
    }

    @classmethod
    def normalize_level(cls, raw: str) -> str:
        return cls.LEVEL_MAP.get(raw.lower().strip(), raw.upper())


_SECURITY_RE = re.compile(
    r'\b(failed|failure|denied|unauthorized|breach|attack|'
    r'malware|virus|trojan|exploit|injection|overflow|'
    r'privilege|escalation|lateral|credential|hash|'
    r'mimikatz|cobalt|beacon|ransomware|exfil|'
    r'suspicious|anomal|critical|alert|lsass|dump|'
    r'powershell|bypass|obfuscat|encoded|base64)\b',
    re.IGNORECASE
)


# ---------------------------------------------
#  Format Detector
# ---------------------------------------------

class FormatDetector:

    EVTX_MAGIC = b'ElfFile\x00'

    @classmethod
    def detect(cls, filepath: str) -> str:
        # Check binary magic first
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(8)
            if magic == cls.EVTX_MAGIC:
                return 'evtx'
        except Exception:
            pass

        # Text-based detection
        try:
            opener = gzip.open if filepath.endswith('.gz') else open
            with opener(filepath, 'rt', encoding='utf-8', errors='replace') as f:
                header = ''.join(f.readline() for _ in range(5))
            hl = header.lower()
            if '#fields:' in hl or '#software: microsoft internet' in hl:
                return 'iis_w3c'
            if re.search(r'<\d+>\d\s+\d{4}-\d{2}-\d{2}T', header):
                return 'syslog5424'
            if re.search(r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s+\S+\[', header):
                return 'syslog3164'
            if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.*\[.*\].*"(GET|POST|PUT|DELETE)', header):
                return 'apache'
            if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+(Information|Warning|Error|Critical)', header, re.IGNORECASE):
                return 'windows_evt'
        except Exception:
            pass

        return 'generic'


# ---------------------------------------------
#  Text Line Parsers
# ---------------------------------------------

class LineParser:

    @staticmethod
    def parse_windows_evt(line, lineno, fpath):
        m = PatternLibrary.WINDOWS_EVT.search(line)
        if not m:
            return None
        return LogEntry(
            line_number=lineno,
            timestamp=m.group('timestamp'),
            level=PatternLibrary.normalize_level(m.group('level') or ''),
            source=m.group('source') or '',
            event_id=m.group('event_id') or '',
            message=(m.group('message') or '').strip(),
            raw=line.rstrip(),
            file_path=fpath,
        )

    @staticmethod
    def parse_syslog3164(line, lineno, fpath):
        m = PatternLibrary.SYSLOG_RFC3164.search(line)
        if not m:
            return None
        return LogEntry(
            line_number=lineno,
            timestamp=m.group('timestamp'),
            level='INFO',
            source=f"{m.group('source')}/{m.group('process')}".strip('/'),
            event_id=m.group('pid') or '',
            message=(m.group('message') or '').strip(),
            raw=line.rstrip(),
            file_path=fpath,
        )

    @staticmethod
    def parse_syslog5424(line, lineno, fpath):
        m = PatternLibrary.SYSLOG_RFC5424.search(line)
        if not m:
            return None
        try:
            severity = int(m.group('priority')) & 0x7
            levels = ['CRITICAL','CRITICAL','CRITICAL','ERROR','WARN','NOTICE','INFO','DEBUG']
            level = levels[severity] if severity < len(levels) else 'INFO'
        except (ValueError, IndexError):
            level = 'INFO'
        return LogEntry(
            line_number=lineno,
            timestamp=m.group('timestamp'),
            level=level,
            source=f"{m.group('hostname')}/{m.group('app')}",
            event_id=m.group('msgid') or '',
            message=(m.group('message') or '').strip(),
            raw=line.rstrip(),
            file_path=fpath,
        )

    @staticmethod
    def parse_iis_w3c(line, lineno, fpath):
        if line.startswith('#'):
            return None
        m = PatternLibrary.IIS_W3C.search(line)
        if not m:
            return None
        status = m.group('status') or ''
        level = 'ERROR' if status.startswith('5') else ('WARN' if status.startswith('4') else 'INFO')
        return LogEntry(
            line_number=lineno,
            timestamp=f"{m.group('date')} {m.group('time')}",
            level=level,
            source=m.group('server_ip') or '',
            event_id=status,
            message=f"{m.group('method')} {m.group('uri')} -> {status}",
            raw=line.rstrip(),
            file_path=fpath,
        )

    @staticmethod
    def parse_apache(line, lineno, fpath):
        m = PatternLibrary.APACHE_COMBINED.search(line)
        if not m:
            return None
        status = m.group('status') or ''
        level = 'ERROR' if status.startswith('5') else ('WARN' if status.startswith('4') else 'INFO')
        return LogEntry(
            line_number=lineno,
            timestamp=m.group('timestamp'),
            level=level,
            source=m.group('client_ip') or '',
            event_id=status,
            message=f"{m.group('method')} {m.group('uri')}",
            raw=line.rstrip(),
            file_path=fpath,
        )

    @staticmethod
    def parse_generic(line, lineno, fpath):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return None
        m = PatternLibrary.GENERIC_TIMESTAMP.search(line)
        if m:
            level_raw = m.group('level') or ''
            return LogEntry(
                line_number=lineno,
                timestamp=m.group('timestamp') or '',
                level=PatternLibrary.normalize_level(level_raw) if level_raw else 'INFO',
                source='',
                event_id='',
                message=(m.group('message') or stripped).strip(),
                raw=stripped,
                file_path=fpath,
            )
        return LogEntry(
            line_number=lineno,
            timestamp='',
            level='INFO',
            source='',
            event_id='',
            message=stripped[:500],
            raw=stripped,
            file_path=fpath,
        )


TEXT_PARSERS = {
    'windows_evt': LineParser.parse_windows_evt,
    'syslog3164':  LineParser.parse_syslog3164,
    'syslog5424':  LineParser.parse_syslog5424,
    'iis_w3c':     LineParser.parse_iis_w3c,
    'apache':      LineParser.parse_apache,
    'generic':     LineParser.parse_generic,
    'powershell':  LineParser.parse_generic,
}


# ---------------------------------------------
#  Main Parse Engine
# ---------------------------------------------

class ParseEngine:

    CHUNK_LINES = 5_000
    MAX_WORKERS = min(8, (os.cpu_count() or 4))

    def __init__(self):
        self._cancel_flag = threading.Event()

    def cancel(self):
        self._cancel_flag.set()

    def reset(self):
        self._cancel_flag.clear()

    def parse_file(self, filepath: str, fmt: str = 'auto',
                   filters: Optional[Dict] = None, progress_cb=None) -> ParseResult:
        self.reset()
        result = ParseResult(file_path=filepath)
        t0 = time.perf_counter()
        filters = filters or {}

        if fmt == 'auto':
            fmt = FormatDetector.detect(filepath)

        # Route .evtx to dedicated binary parser
        if fmt == 'evtx' or filepath.lower().endswith('.evtx') or filepath.lower().endswith('.evt'):
            return parse_evtx_file(filepath, filters, progress_cb)

        # Text-based parsing
        parser_fn = TEXT_PARSERS.get(fmt, LineParser.parse_generic)

        try:
            lines = self._read_lines(filepath)
        except Exception as e:
            result.errors.append(f"Cannot open file: {e}")
            return result

        total_lines = len(lines)
        result.total_lines = total_lines

        if total_lines == 0:
            result.duration_seconds = time.perf_counter() - t0
            return result

        chunks = [
            (lines[i:i + self.CHUNK_LINES], i + 1, filepath, parser_fn, filters)
            for i in range(0, total_lines, self.CHUNK_LINES)
        ]

        completed = 0
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as pool:
            futures = {pool.submit(self._process_chunk, *c): c for c in chunks}
            for future in as_completed(futures):
                if self._cancel_flag.is_set():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                chunk_entries, chunk_skipped = future.result()
                result.entries.extend(chunk_entries)
                result.parsed_count += len(chunk_entries)
                result.skipped_count += chunk_skipped
                completed += 1
                if progress_cb:
                    pct = int(completed / len(chunks) * 100)
                    progress_cb(pct, f"Parsed {result.parsed_count:,} entries...")

        result.duration_seconds = time.perf_counter() - t0
        result.entries.sort(key=lambda e: e.line_number)
        return result

    def parse_multiple(self, filepaths: List[str], fmt: str = 'auto',
                       filters: Optional[Dict] = None, progress_cb=None) -> ParseResult:
        combined = ParseResult()
        total = len(filepaths)
        for idx, fp in enumerate(filepaths):
            if self._cancel_flag.is_set():
                break

            def _cb(pct, msg, _i=idx):
                if progress_cb:
                    overall = int((_i + pct / 100) / total * 100)
                    progress_cb(overall, f"[{_i+1}/{total}] {msg}")

            r = self.parse_file(fp, fmt, filters, _cb)
            combined.entries.extend(r.entries)
            combined.errors.extend(r.errors)
            combined.total_lines += r.total_lines
            combined.parsed_count += r.parsed_count
            combined.skipped_count += r.skipped_count
            combined.duration_seconds += r.duration_seconds

        combined.entries.sort(key=lambda e: e.timestamp or '')
        return combined

    @staticmethod
    def _read_lines(filepath: str) -> List[str]:
        opener = gzip.open if filepath.endswith('.gz') else open
        with opener(filepath, 'rt', encoding='utf-8', errors='replace') as f:
            return f.readlines()

    @staticmethod
    def _process_chunk(lines, start_lineno, filepath, parser_fn, filters):
        entries = []
        skipped = 0
        level_filter = filters.get('levels', set())
        keyword_filter = filters.get('keyword', '').lower()

        for offset, line in enumerate(lines):
            entry = parser_fn(line, start_lineno + offset, filepath)
            if entry is None:
                skipped += 1
                continue
            if level_filter and entry.level not in level_filter:
                skipped += 1
                continue
            if keyword_filter and keyword_filter not in (
                entry.message + entry.source + entry.raw
            ).lower():
                skipped += 1
                continue
            if _SECURITY_RE.search(entry.message):
                entry.extra['security_flag'] = '1'
            entries.append(entry)

        return entries, skipped


# ---------------------------------------------
#  CSV Exporter
# ---------------------------------------------

class CSVExporter:

    @staticmethod
    def export(entries: List[LogEntry], output_path: str, progress_cb=None) -> int:
        total = len(entries)
        written = 0
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow(LogEntry.csv_headers())
                BATCH = 1000
                for i in range(0, total, BATCH):
                    batch = entries[i:i + BATCH]
                    writer.writerows(e.to_csv_row() for e in batch)
                    written += len(batch)
                    if progress_cb:
                        progress_cb(int(written / total * 100),
                                    f"Exporting {written:,}/{total:,}")
        except Exception as e:
            raise RuntimeError(f"CSV export failed: {e}") from e
        return written
