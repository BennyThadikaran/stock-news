from typing import Union, Dict, List
from bse import BSE
from datetime import datetime, timedelta
from os import system
from pathlib import Path
from argparse import ArgumentParser
import sys
import json
import re
import logging


class BaseFormatter:
    """Base Formatter"""

    def mainHeading(self, string: str) -> str:
        return f"{string}\n"

    def subHeading(self, string: str) -> str:
        return f"{string}\n"

    def string(
        self, key: str, val: str, date: Union[datetime, str, None] = None
    ) -> str:
        raise NotImplementedError

    @staticmethod
    def hr() -> str:
        return f'\n{"":->70}\n'


class ColorFormatter(BaseFormatter):
    """Format strings with Terminal color output"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def mainHeading(self, string: str) -> str:
        return f"{self.HEADER}{self.BOLD}{string}{self.ENDC}\n"

    def subHeading(self, string: str) -> str:
        return f"{self.BOLD}{string}{self.ENDC}\n"

    def heading(self, sym: str, category: str) -> str:
        return f"{self.CYAN}{self.BOLD}{sym.upper()} - {category}{self.ENDC}\n"

    def subject(self, subject: str, headline: str) -> str:
        return f"{self.GREEN}{subject}{self.ENDC}\n{headline}{self.ENDC}"

    def url(self, filename: str) -> str:
        baseurl = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"
        return f"\n{self.CYAN}{baseurl}/{filename}{self.ENDC}"

    def string(
        self, key: str, val: str, date: Union[datetime, str, None] = None
    ) -> str:
        string = f"{self.HEADER}{self.BOLD}{key}:".ljust(25)
        string += f"{self.GREEN}{val}{self.ENDC}".ljust(48)

        if date:
            string += f"{date:%d %b %Y}" if isinstance(date, datetime) else date

        return string + "\n"


class TextFormatter(BaseFormatter):
    """Format strings in plain text"""

    def heading(self, sym: str, category: str) -> str:
        return f"{sym.upper()} - {category}\n"

    def subject(self, subject: str, headline: str) -> str:
        return f"{subject}\n{headline}"

    def url(self, filename: str) -> str:
        baseurl = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"
        return f"\n{baseurl}/{filename}"

    def string(
        self, key: str, val: str, date: Union[datetime, str, None] = None
    ) -> str:
        string = f"{key}:".ljust(15)
        string += f"{val}".ljust(40)

        if date:
            string += f"{date:%d %b %Y}" if isinstance(date, datetime) else date

        return string + "\n"


class MarkdownFormatter(BaseFormatter):
    """Format strings in Markdown text"""

    div_table_start = True
    other_table_start = True
    result_table_start = True

    def mainHeading(self, string: str) -> str:
        return f"# {string}\n"

    def subHeading(self, string: str) -> str:
        return f"## {string}\n"

    def heading(self, sym: str, category: str) -> str:
        return f"## {sym.upper()} - {category}\n"

    def subject(self, subject: str, headline: str) -> str:
        return f"**{subject}**\n{headline}"

    def url(self, filename: str) -> str:
        baseurl = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"
        return f"\n{baseurl}/{filename}"

    def string(
        self, key: str, val: str, date: Union[datetime, str, None] = None
    ) -> str:
        string = ""
        header = "|Company|Description|Ex Date|\n|---|---|---|\n"
        resultHeader = "|Company|Result Date|\n|---|---|\n"

        if date is None and self.result_table_start:
            string += resultHeader
            self.result_table_start = False

        if "Dividend" in val and self.div_table_start:
            string += header
            self.div_table_start = False

        if ("Bonus" in val or "Split" in val) and self.other_table_start:
            string += header
            self.other_table_start = False

        string += f"|{key}|{val}|"

        if date:
            dt = (
                date.strftime("%d %b %Y")
                if isinstance(date, datetime)
                else date
            )
            string += f"{dt}|"

        return string + "\n"


class FormatterFactory:
    @staticmethod
    def get(name: str):
        if name == "txt":
            return TextFormatter()

        if name == "md":
            return MarkdownFormatter()

        return ColorFormatter()


def isBlackListed(string: str) -> bool:
    """Looks for blacklisted keywords in string and returns True if found"""

    string = string.lower()

    # Picked from announcements subcategory
    filtered_words = (
        "trading window",
        "reg. 74 (5)",  # demat
        "book closure",
        "investor meet",
        "loss of share",
        "loss of certificate",
        "investor conference",
        "shares in physical",
    )

    for key in filtered_words:
        if key in string:
            return True

    return False


def cleanDividendAction(string: str) -> str:
    """Formats dividend string, removing '-' and extra zeroes

    'Interim Dividend - Rs. - 18.0000' => 'Interim Dividend Rs.18.0'
    """

    # 'Interim Dividend - Rs. - 18.0000' -> split on '-' and strip space chars
    # ['Interim Dividend', 'Rs.'], 18.0000
    *str_lst, dividend = tuple(i.strip() for i in string.split("-"))

    try:
        dividend = float(dividend)
    except ValueError:
        # Not a valid number. return string as is
        return string

    return f'{" ".join(str_lst)}{dividend}'


def parseComplaints(string) -> str:
    """Parses shareholder complaints string.
    Looks for integer values between HTML tags"""

    m = re.findall(r">(\d+)<", string)

    if len(m) < 4:
        return string

    return f"Pending: {m[0]}\nReceived: {m[1]}\nDisposed: {m[2]}\nUnresolved: {m[3]}"


# Check if system is windows or linux
if "win" in sys.platform:
    # enable color support in Windows
    system("color")

dt = datetime.now()

parser = ArgumentParser(
    prog="news.py",
    description="A script for displaying Corporate filings on BSE exchange.",
)

group = parser.add_mutually_exclusive_group(required=False)

group.add_argument(
    "-p",
    "--prev",
    type=int,
    nargs="?",
    const=1,
    default=None,
    dest="prev",
    metavar="N",
    help="Get news for previous day or N days back.",
)

group.add_argument(
    "-d",
    "--date",
    type=lambda x: datetime.fromisoformat(x),
    action="store",
    metavar="YYYY-MM-DD",
    help="Get news for specified date",
)

parser.add_argument(
    "--fmt",
    choices=("txt", "md", "html", "color"),
    default="color",
    help="Output format (choose from txt, md, html, color)",
)

parser.add_argument(
    "-f", "--file", type=Path, help="Add watchlist symbols file"
)

parser.add_argument(
    "-o",
    "--out",
    type=Path,
    help="Output to file",
)

args = parser.parse_args()


DIR = Path(__file__).parent
WATCH_FILE = DIR / "watchlist.json"

if args.date:
    if args.date > dt:
        raise ValueError("Date cannot be greater than today")

    dt = args.date

if args.prev:
    dt = dt - timedelta(args.prev)

symList: Union[List[str], None] = None

# set up logging
logger = logging.getLogger(__file__)

if args.out:
    log_handler = logging.FileHandler(args.out, mode="w")
else:
    log_handler = logging.StreamHandler(stream=sys.stdout)

logging.basicConfig(
    handlers=[log_handler],
    format="%(message)s",
    level=logging.INFO,
)


if args.file:
    watchlist: Dict[str, str] = {}

    if not args.file.exists():
        raise FileNotFoundError(f"{args.file} not found. ")

    symList = args.file.read_text().strip().split("\n")
else:
    if not WATCH_FILE.exists():
        raise FileNotFoundError(
            f"{WATCH_FILE} not found. Use -f to generate watchlist.json"
        )

    watchlist = json.loads(WATCH_FILE.read_bytes())

with BSE(DIR) as bse:
    if symList:
        for sym in symList:
            code: str = bse.getScripCode(sym)
            watchlist[code] = sym

        WATCH_FILE.write_text(json.dumps(watchlist, indent=3))
        print("watchlist.json file saved")

    try:
        actions: List[dict] = bse.actions()
        result_calendar: List[dict] = bse.resultCalendar()
    except (TimeoutError, ConnectionError) as e:
        exit(repr(e))

    announcements: List[dict] = []

    for code in watchlist:
        try:
            res: dict = bse.announcements(
                from_date=dt, to_date=dt, scripcode=code
            )
        except (TimeoutError, ConnectionError) as e:
            exit(repr(e))

        announcements.extend(res["Table"])

fmt = FormatterFactory.get(args.fmt)

ann_txt = result_txt = portfolio_acts = other_acts = ""

# PROCESS RESULT CALENDAR
for res in result_calendar:
    if res["scrip_Code"] in watchlist:
        result_txt += fmt.string(res["short_name"], res["meeting_date"])

# PROCESS CORP ANNOUNCEMENTS
for ann in announcements:
    code = str(ann["SCRIP_CD"])
    sym = watchlist[code]
    subject: str = ann["NEWSSUB"]

    if not (code in watchlist and ann["CATEGORYNAME"]):
        continue

    if isBlackListed(subject):
        continue

    if (
        "Regulation" in subject or "Notice" in subject or "Change" in subject
    ) and "-" in subject:
        # Strip company name, scrip code etc. and limit subject to 70 chars
        subject = subject[subject.find("-") + 1 :][:70]

    if "XBRL" in subject:
        subject = subject.replace("- XBRL", "")

    if "investor complaints" in subject.lower():
        headline = parseComplaints(ann["HEADLINE"])
    else:
        headline: str = ann["HEADLINE"].replace("<BR>", "")

    ann_txt += fmt.heading(sym, ann["CATEGORYNAME"])

    ann_txt += fmt.subject(subject.strip(), headline)

    if ann["ATTACHMENTNAME"]:
        ann_txt += fmt.url(ann["ATTACHMENTNAME"])

    ann_txt += fmt.hr()

# PROCESS CORP. ACTIONS
for act in actions:
    purpose_lc: str = act["Purpose"].lower()
    sym: str = act["short_name"]
    code = str(act["scrip_code"])
    ex_date = act["Ex_date"]

    if "dividend" in purpose_lc:
        act["Purpose"] = cleanDividendAction(act["Purpose"])

    if code in watchlist:
        portfolio_acts += fmt.string(sym, act["Purpose"], ex_date)
    elif "bonus" in purpose_lc or "split" in purpose_lc:
        other_acts += fmt.string(sym, act["Purpose"], ex_date)

# PRINT ANNOUNCEMENTS
logger.info(fmt.mainHeading(f"CORP. ANNOUNCEMENTS - {dt:%A %d %b %Y}"))

if ann_txt:
    logger.info(ann_txt)
else:
    logger.info(fmt.subHeading("No announcements to display."))

# PRINT RESULT CALENDAR
if result_txt:
    logger.info(fmt.mainHeading("Result Calendar"))
    logger.info(result_txt)

# PRINT ACTIONS
logger.info(fmt.mainHeading("Corporate Actions"))

if portfolio_acts:
    logger.info(fmt.subHeading("Portfolio"))
    logger.info(portfolio_acts)
else:
    logger.info("\tNo actions on Portfolio\n")

if other_acts:
    logger.info(fmt.subHeading("Other Corp. Actions"))
    logger.info(other_acts)
