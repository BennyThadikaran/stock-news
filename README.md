# BSE NEWS.py

A Python Terminal script for displaying Corporate filings on BSE exchange.

Use it track company updates, quarterly results, dividend, bonus etc on your portfolio stocks.

![news.py screenshot](https://res.cloudinary.com/doyu4uovr/image/upload/s--RpyXwBKg--/c_scale,f_auto,w_800/v1698149118/stock-news/news_t3l3o8.png)

Python version: >= 3.6

If you ❤️ my work so far, please 🌟 this repo.

## Installation

1. Clone this repo

2. Install dependencies: `pip install bse`

### Initial Setup

1. **Create a text file** of all stock symbols. One on each line. This could be your stocks portfolio or a watchlist.

```
hdfcbank
tcs
infy
```

2. **Run the script** with `-f` or `--file` option passing the file path.

`py news.py -f watch.txt`

This will generate a `watchlist.json` file and display all announcements & actions for the day.

## Usage

After the initial setup, run the script with no options.

`py news.py`

By default, the current day announcements are printed.

To **print the previous day**, use `-p` or `--prev` option.

```bash
py news.py -p
# print yesterdays announcements
```

Add an optional integer number like `py news.py -p 3` to go 3 days back.

To **jump to a specific date**, use `-d` or `--date` option passing a ISO date string (YYYY-MM-DD).

`py news.py -d 2023-10-18`

All output is displayed in terminal colors. To display no color and plain text, use `-t` or `--txt` option.

`py news.py -t`

To **display help**, use `-h` or `--help`

`py news.py -h`

## Notes

The announcements are filtered for certain keywords in the sub-category. These include `Loss of share certificates`, `book closure`, `Certificate of dematerialization`.

IMHO these are unimportant and thus filtered out. If you wish to add or remove from this list, see `def isBlackListed` in `src/news.py`. The keywords in question are listed in `filtered_words`
