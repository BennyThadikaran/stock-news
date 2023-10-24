from bse import BSE
from datetime import datetime, timedelta
from os import system
from sys import platform
from pathlib import Path
from argparse import ArgumentParser
import json
from re import findall


class BaseFormatter:
    '''Base Formatter'''

    @staticmethod
    def mainHeading(string: str) -> str:
        return string

    @staticmethod
    def subHeading(string: str) -> str:
        return string

    @staticmethod
    def hr() -> str:
        return f"\n{'-' * 70}\n\n"


class ColorFormatter(BaseFormatter):
    '''Format strings with Terminal color output'''

    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    def mainHeading(self, string: str) -> str:
        return f"{self.HEADER}{self.BOLD}{string}{self.ENDC}"

    def subHeading(self, string: str) -> str:
        return f"{self.BOLD}{string}{self.ENDC}"

    def heading(self, sym: str, category: str) -> str:
        return f"{self.CYAN}{self.BOLD}{sym.upper()} - {category}{self.ENDC}\n"

    def subject(self, subject: str, headline: str) -> str:
        return f"{self.GREEN}{subject}{self.ENDC}\n{headline}{self.ENDC}"

    def url(self, filename: str) -> str:
        baseurl = 'https://www.bseindia.com/xml-data/corpfiling/AttachLive'
        return f"\n{self.CYAN}{baseurl}/{filename}{self.ENDC}"

    def string(self, key: str, val: str, date: datetime | None = None) -> str:
        string = f"{self.HEADER}{self.BOLD}{key}:".ljust(25)
        string += f"{self.GREEN}{val}{self.ENDC}".ljust(48)

        if date:
            string += dt.strftime('%d %b %Y')

        return string + '\n'


class TextFormatter(BaseFormatter):

    def heading(self, sym: str, category: str) -> str:
        return f"{sym.upper()} - {category}\n"

    def subject(self, subject: str, headline: str) -> str:
        return f"{subject}\n{headline}"

    def url(self, filename: str) -> str:
        baseurl = 'https://www.bseindia.com/xml-data/corpfiling/AttachLive'
        return f"\n{baseurl}/{filename}"

    def string(self, key: str, val: str, date: datetime | None = None) -> str:
        string = f"{key}:".ljust(15)
        string += f"{val}".ljust(40)

        if date:
            string += dt.strftime('%d %b %Y')

        return string + '\n'


def isBlackListed(string: str) -> bool:
    '''Looks for blacklisted keywords in string and returns True if found'''

    string = string.lower()

    # Picked from announcements subcategory
    filtered_words = (
        'trading window',
        'reg. 74 (5)',
        'reg. 39 (3)'
        'book closure'
    )

    for key in filtered_words:
        if key in string:
            return True

    return False


def cleanDividendAction(string: str) -> str:
    '''Formats dividend string, removing '-' and extra zeroes

    'Interim Dividend - Rs. - 18.0000' => 'Interim Dividend Rs.18.0'
    '''

    if not 'Dividend' in string:
        return string

    out = [i.strip() for i in string.split('-')]

    try:
        dividend = float(out[-1])
    except ValueError:
        return ' '.join(out)

    return f"{' '.join(out[:-1])}{dividend}"


def parseComplaints(string):
    '''Parses shareholder complaints string.
    Looks for integer values between HTML tags'''

    m = findall(r'>(\d+)<', string)

    if len(m) < 4:
        return string

    return f'Pending: {m[0]}\nReceived: {m[1]}\nDisposed: {m[2]}\nUnresolved: {m[3]}'


# Check if system is windows or linux
if 'win' in platform:
    # enable color support in Windows
    system('color')

parser = ArgumentParser(prog='news.py',
                        description='A script for displaying Corporate filings on BSE exchange.')

group = parser.add_mutually_exclusive_group(required=False)

group.add_argument('-p',
                   '--prev',
                   type=int,
                   nargs='?',
                   const=1,
                   default=None,
                   dest='prev',
                   metavar='N',
                   help='Get news for previous day or N days back.')

group.add_argument('-d', '--date',
                   type=lambda x: datetime.strptime(x, '%Y-%m-%d'),
                   action='store',
                   metavar='YYYY-MM-DD',
                   help='Get news for specified date')

parser.add_argument('-t', '--txt',
                    action='store_true',
                    default=False,
                    help='Output plain text')

parser.add_argument('-f', '--file',
                    type=Path,
                    help='Add watchlist symbols file')

args = parser.parse_args()

dt = datetime.now()

if args.date:
    if args.date > dt:
        raise ValueError('Date cannot be greater than today')

    dt = args.date

if args.prev:
    dt = dt - timedelta(args.prev)

DIR = Path(__file__).parent
WATCH_FILE = DIR / 'watchlist.json'

symList = None

if args.file:
    watchlist = {}

    if not args.file.exists():
        raise FileNotFoundError(
            f'{args.file} not found. ')

    symList = args.file.read_text().strip().split('\n')
else:
    if not WATCH_FILE.exists():
        raise FileNotFoundError(
            '{WATCH_FILE} not found. Use -f to generate watchlist.json')

    watchlist = json.loads(WATCH_FILE.read_bytes())


with BSE() as bse:
    if symList:
        for sym in symList:
            code = bse.getScripCode(sym)
            watchlist[code] = sym

        WATCH_FILE.write_text(json.dumps(watchlist, indent=3))

    actions = bse.actions()

    result_calendar = bse.resultCalendar()

    announcements = []

    for code, sym in watchlist.items():
        res = bse.announcements(from_date=dt, to_date=dt, scripcode=code)
        announcements.extend(res['Table'])


fmt = TextFormatter() if args.txt else ColorFormatter()

ann_txt = result_txt = portfolio_acts = other_acts = ''


# PROCESS RESULT CALENDAR
for res in result_calendar:
    if res['scrip_Code'] in watchlist:
        result_txt += fmt.string(res['short_name'], res['meeting_date'])


# PROCESS CORP ANNOUNCEMENTS
for ann in announcements:
    code = str(ann['SCRIP_CD'])
    sym = watchlist[code]
    subject = ann['NEWSSUB']

    if not (code in watchlist and ann['CATEGORYNAME']):
        continue

    if isBlackListed(ann['SUBCATNAME']):
        continue

    if '-' in subject:
        subject = subject.split('-')[-1][:70].strip()

    if 'investor complaints' in subject.lower():
        headline = parseComplaints(ann['HEADLINE'])
    else:
        headline = ann['HEADLINE'].replace('<BR>', '')

    ann_txt += fmt.heading(sym, ann['CATEGORYNAME'])

    ann_txt += fmt.subject(subject, headline)

    if ann['ATTACHMENTNAME']:
        ann_txt += fmt.url(ann['ATTACHMENTNAME'])

    ann_txt += fmt.hr()


# PROCESS CORP. ACTIONS
for act in actions:
    purpose = act['Purpose'].lower()
    sym = act['short_name']

    if 'Dividend' in purpose:
        purpose = cleanDividendAction(purpose)

    if act['scrip_code'] in watchlist:
        portfolio_acts += fmt.string(sym, purpose, dt)
    elif 'bonus' in purpose or 'split' in purpose:
        other_acts += fmt.string(sym, purpose, dt)


# PRINT ANNOUNCEMENTS
print(fmt.mainHeading(f'CORP. ANNOUNCEMENTS - {dt:%A %d %b %Y}'))

if ann_txt:
    print(ann_txt)
else:
    print('\tNo announcements to display.\n')


# PRINT RESULT CALENDAR
if result_txt:
    print(fmt.mainHeading('Result Calendar'))
    print(result_txt)


# PRINT ACTIONS
print(fmt.mainHeading('Corporate Actions'))

if portfolio_acts:
    print(fmt.subHeading('Portfolio'))
    print(portfolio_acts)
else:
    print(f'\tNo actions on Portfolio\n')

if other_acts:
    print(fmt.subHeading('Other Corp. Actions'))
    print(other_acts)
