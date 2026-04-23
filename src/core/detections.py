"""
LogRaptorX - Detection Rules Engine
SIGMA-inspired rule set for automated threat detection.
Developer: Kennedy Aikohi
"""

import re
import base64
from dataclasses import dataclass, field
from typing import List, Optional
from core.parser import LogEntry


# -------------------------------------------------------
#  Detection Result
# -------------------------------------------------------

@dataclass
class Detection:
    rule_id: str
    rule_name: str
    severity: str
    category: str
    mitre_id: str
    description: str
    matched_value: str
    entry: LogEntry = field(repr=False, default=None)

    @property
    def severity_order(self) -> int:
        return {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(self.severity, 9)


# -------------------------------------------------------
#  Rule Base
# -------------------------------------------------------

class DetectionRule:
    def __init__(self, rule_id, name, severity, category, mitre_id, description, patterns):
        self.rule_id  = rule_id
        self.name     = name
        self.severity = severity
        self.category = category
        self.mitre_id = mitre_id
        self.description = description
        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def match(self, text: str) -> Optional[str]:
        for p in self._patterns:
            m = p.search(text)
            if m:
                return m.group(0)[:120]
        return None


# -------------------------------------------------------
#  Base64 Detector (validates decoded content)
# -------------------------------------------------------

class Base64Rule:
    rule_id     = "LRX-001"
    name        = "Embedded Base64 Payload"
    severity    = "CRITICAL"
    category    = "Execution"
    mitre_id    = "T1027"
    description = "Base64-encoded payload detected - common obfuscation technique"

    _PS_ENC  = re.compile(r"-(?:enc|encoded|encodedcommand)\s+([A-Za-z0-9+/=]{20,})", re.IGNORECASE)
    _BLOB    = re.compile(r"(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
    _HARMFUL = re.compile(r"powershell|cmd|invoke|iex|download|webclient|http|bypass|hidden|shellcode", re.IGNORECASE)

    def match(self, text: str) -> Optional[str]:
        m = self._PS_ENC.search(text)
        if m:
            return f"-EncodedCommand {m.group(1)[:60]}..."

        for m in self._BLOB.finditer(text):
            blob = m.group(0)
            if len(blob) < 40:
                continue
            for enc in ("utf-16-le", "utf-8"):
                try:
                    decoded = base64.b64decode(blob + "==").decode(enc, errors="ignore")
                    if self._HARMFUL.search(decoded):
                        return f"Base64->({decoded[:80]})"
                except Exception:
                    pass
        return None


# -------------------------------------------------------
#  Rule Definitions
# -------------------------------------------------------

RULES: List[DetectionRule] = [

    DetectionRule("LRX-002", "PowerShell Obfuscation / Abuse",
        "CRITICAL", "Execution", "T1059.001",
        "PowerShell executing encoded or obfuscated command",
        [r"-enc\w*\s+[A-Za-z0-9+/=]{20,}",
         r"powershell.*-w\s*hidden",
         r"powershell.*bypass",
         r"\bIEX\s*\(",
         r"Invoke-Expression",
         r"\.downloadstring\(",
         r"Net\.WebClient",
         r"FromBase64String"]),

    DetectionRule("LRX-003", "LOLBAS - Living Off The Land",
        "HIGH", "Execution", "T1218",
        "Trusted Windows binary used for malicious execution",
        [r"certutil.*-decode",
         r"certutil.*-urlcache",
         r"mshta\.exe",
         r"wscript\.exe.*\.js",
         r"cscript\.exe.*\.vbs",
         r"regsvr32.*\/s.*\/u",
         r"rundll32.*javascript",
         r"InstallUtil\.exe",
         r"MSBuild\.exe.*\.csproj"]),

    DetectionRule("LRX-004", "Credential Dumping",
        "CRITICAL", "Credential Access", "T1003",
        "Credential dumping tool or technique detected",
        [r"mimikatz",
         r"sekurlsa",
         r"lsadump",
         r"wce\.exe",
         r"procdump.*lsass",
         r"comsvcs.*minidump",
         r"NtlmHash",
         r"HashDump",
         r"lsass.*access"]),

    DetectionRule("LRX-005", "Lateral Movement",
        "HIGH", "Lateral Movement", "T1021",
        "Remote execution or lateral movement technique",
        [r"psexec",
         r"wmiexec",
         r"smbexec",
         r"atexec",
         r"winrm.*invoke",
         r"Enter-PSSession",
         r"New-PSSession",
         r"Invoke-Command.*ComputerName"]),

    DetectionRule("LRX-006", "Persistence Mechanism",
        "HIGH", "Persistence", "T1547",
        "Registry run key or scheduled task persistence",
        [r"HKCU.*\\Run",
         r"HKLM.*\\Run",
         r"schtasks.*\/create",
         r"New-ScheduledTask",
         r"Register-ScheduledJob",
         r"sc\s+create"]),

    DetectionRule("LRX-007", "Defense Evasion",
        "HIGH", "Defense Evasion", "T1562",
        "Security tool tampering or log clearing",
        [r"Set-MpPreference.*Disable",
         r"DisableRealtimeMonitoring",
         r"netsh.*firewall.*disable",
         r"wevtutil.*cl\s",
         r"wevtutil.*clear",
         r"Remove-EventLog",
         r"auditpol.*success:disable"]),

    DetectionRule("LRX-008", "Suspicious Network / Download",
        "HIGH", "Command and Control", "T1071",
        "Suspicious outbound connection or file download",
        [r"DownloadFile\(",
         r"DownloadString\(",
         r"WebRequest",
         r"bitsadmin.*transfer",
         r"Net\.Sockets\.TcpClient"]),

    DetectionRule("LRX-009", "Process Injection",
        "CRITICAL", "Defense Evasion", "T1055",
        "Process injection or hollowing technique",
        [r"VirtualAllocEx",
         r"WriteProcessMemory",
         r"CreateRemoteThread",
         r"NtQueueApcThread",
         r"SetWindowsHookEx",
         r"QueueUserAPC",
         r"shellcode"]),

    DetectionRule("LRX-010", "Ransomware Indicator",
        "CRITICAL", "Impact", "T1486",
        "Ransomware behavior or shadow copy deletion",
        [r"vssadmin.*delete.*shadows",
         r"bcdedit.*safeboot",
         r"wbadmin.*delete",
         r"cipher.*\/w",
         r"YOUR_FILES_ARE_ENCRYPTED"]),

    DetectionRule("LRX-011", "Reconnaissance",
        "MEDIUM", "Discovery", "T1082",
        "System or network reconnaissance commands",
        [r"\bwhoami\b",
         r"net\s+user",
         r"net\s+group",
         r"\bnltest\b",
         r"Get-ADUser",
         r"Get-ADComputer",
         r"Get-NetUser",
         r"BloodHound"]),

    DetectionRule("LRX-012", "Privilege Escalation",
        "CRITICAL", "Privilege Escalation", "T1134",
        "Token impersonation or privilege escalation",
        [r"SeDebugPrivilege",
         r"SeTcbPrivilege",
         r"ImpersonateLoggedOnUser",
         r"DuplicateTokenEx",
         r"AdjustTokenPrivileges",
         r"juicypotato",
         r"printspoofer",
         r"rottenpotato"]),

    DetectionRule("LRX-013", "C2 Framework Indicator",
        "CRITICAL", "Command and Control", "T1219",
        "Known C2 framework artifact or beacon pattern",
        [r"cobalt.?strike",
         r"cobaltstrike",
         r"metasploit",
         r"meterpreter",
         r"\bempire\b",
         r"\bsliver\b",
         r"\bhavoc\b",
         r"beacon\.(x64|x86|dll)"]),

    DetectionRule("LRX-014", "Audit Log Cleared",
        "CRITICAL", "Defense Evasion", "T1070.001",
        "Windows Security or System audit log was cleared",
        [r"EventID.*1102",
         r"EventID.*104",
         r"log.*cleared",
         r"audit.*log.*cleared"]),

    DetectionRule("LRX-015", "New Service Installed",
        "HIGH", "Persistence", "T1543.003",
        "A new Windows service was installed",
        [r"EventID.*7045",
         r"EventID.*4697",
         r"A new service was installed"]),
]

_BASE64_RULE = Base64Rule()


# -------------------------------------------------------
#  Detection Engine
# -------------------------------------------------------

class DetectionEngine:

    def scan_entry(self, entry: LogEntry) -> List[Detection]:
        text = f"{entry.message} {entry.raw} {entry.source} {entry.event_id}"
        results = []

        hit = _BASE64_RULE.match(text)
        if hit:
            results.append(Detection(
                rule_id=_BASE64_RULE.rule_id,
                rule_name=_BASE64_RULE.name,
                severity=_BASE64_RULE.severity,
                category=_BASE64_RULE.category,
                mitre_id=_BASE64_RULE.mitre_id,
                description=_BASE64_RULE.description,
                matched_value=hit,
                entry=entry,
            ))

        for rule in RULES:
            hit = rule.match(text)
            if hit:
                results.append(Detection(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    mitre_id=rule.mitre_id,
                    description=rule.description,
                    matched_value=hit,
                    entry=entry,
                ))

        return results

    def scan_all(self, entries: List[LogEntry], progress_cb=None) -> List[Detection]:
        all_detections = []
        total = len(entries)
        for i, entry in enumerate(entries):
            hits = self.scan_entry(entry)
            if hits:
                if any(d.severity == "CRITICAL" for d in hits):
                    entry.level = "CRITICAL"
                    entry.extra["detection_flag"] = "CRITICAL"
                elif any(d.severity == "HIGH" for d in hits):
                    if entry.extra.get("detection_flag") != "CRITICAL":
                        entry.extra["detection_flag"] = "HIGH"
                entry.extra["detections"] = str(len(hits))
                all_detections.extend(hits)
            if progress_cb and i % 500 == 0:
                progress_cb(int(i / total * 100), f"Scanning {i:,}/{total:,} entries...")
        return all_detections
