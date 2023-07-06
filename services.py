from bs4 import BeautifulSoup
import httpx
import re
import json
import time
import numpy
import unicodedata

# custom module
import utils


async def get_sentiment(symbols):
    client = httpx.AsyncClient()

    try:
        response = await client.get("https://www.myfxbook.com/community/outlook")

    except Exception as err:
        print(f"get_sentiment: {type(err).__name__}")

    else:
        if response.status_code == 200:
            html = BeautifulSoup(response.text, "html.parser")
            regexp_pattern = re.compile("outlookSymbolPopover\d")
            sentiment_rows = html.find_all("div", {"id": regexp_pattern})

            data = {}
            for row in sentiment_rows:
                td_tags = row.find_all("td")

                symbol = td_tags[0].text
                # lọc các symbol cần lấy
                symbols = [s.lower() for s in symbols]
                if symbol.lower() not in symbols:
                    continue

                data[symbol] = {
                    "Short": {
                        "Percentage": float(td_tags[2].text.strip("%")) / 100,
                        "Volume(lots)": float(td_tags[3].text.strip(" lots")),
                        "Positions": int(td_tags[4].text),
                    },
                    "Long": {
                        "Percentage": float(td_tags[6].text.strip("%")) / 100,
                        "Volume(lots)": float(td_tags[7].text.strip(" lots")),
                        "Positions": int(td_tags[8].text),
                    },
                }

            return data

        else:
            print(f"get_sentiment: {response.status_code}")

    return None


async def get_technical_summary(
    filtering_symbols=["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
):
    client = httpx.Client()

    headers = {
        "Host": "www.investing.com",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.investing.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Referer": "https://www.investing.com/technical/technical-summary",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        symbols_map = await utils.get_file_content("symbols")

        # tạo payload
        tab = "tab=forex"
        peroids = "options%5Bperiods%5D%5B%5D=300&options%5Bperiods%5D%5B%5D=900&options%5Bperiods%5D%5B%5D=3600&options%5Bperiods%5D%5B%5D=86400"
        symbols_string = ""

        # tạo chuỗi từ các symbol trong parameter
        for symbol in filtering_symbols:
            symbols_string += f"options%5Bcurrencies%5D%5B%5D={symbols_map[symbol.lower()]['investing']}&"

        # cắt ký tự "&" ở cuối symbols_string do thừa
        payload = f"{tab}&{peroids}&{symbols_string[:-1]}"

        # dữ liệu mong muốn: json
        response = client.post(
            "https://www.investing.com/technical/Service/GetSummaryTable",
            headers=headers,
            data=payload,
        )

    except Exception as err:
        print(f"get_technical_summary: {type(err).__name__}")

    else:
        if response.status_code == 200:
            body = json.loads(response.text)
            soup = BeautifulSoup(body["html"], "html.parser")

            tbody = soup.findChild("tbody")

            tr_tags = tbody.find_all("tr")
            data = {}
            for tr_tag in tr_tags:
                row_type = tr_tag["data-row-type"]

                # để lấy symbol và giá hiện tại
                if row_type == "movingAverages":
                    a_tag = tr_tag.find("a")
                    p_tag = tr_tag.find("p")

                    symbol = a_tag.text.replace("/", "") if a_tag and p_tag else None

                # lọc các symbol cần lấy dựa vào cấu hình ban đầu
                if symbol not in data:
                    data[symbol] = {}

                if row_type == "summary":
                    suggestion_arr = tr_tag.find_all(
                        "td",
                        {"class": "js-socket-elem"},
                    )
                    data[symbol].update(
                        {
                            "5MIN": suggestion_arr[0].text.strip(),
                            "15MIN": suggestion_arr[1].text.strip(),
                            "1HOUR": suggestion_arr[2].text.strip(),
                            "1DAY": suggestion_arr[3].text.strip(),
                        }
                    )

            return data

        else:
            print(f"get_technical_summary: {response.status_code}")

    return None


async def get_redirected_url(url):
    # get redirected url
    client = httpx.AsyncClient()

    try:
        target_url = f"{url}"
        response = await client.get(
            target_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

    except Exception as err:
        print(err)

    else:
        return response.next_request.url


async def get_news():
    base_url = "https://www.investing.com"
    client = httpx.AsyncClient()

    try:
        target_url = f"{base_url}/news/latest-news"
        response = await client.get(
            target_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=httpx.Timeout(10),
        )

    except Exception as err:
        print(f"get_news: {type(err).__name__}")

    else:
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            large_title = soup.find("div", {"class": "largeTitle"})
            articles = large_title.findAll(
                "article", {"class": "js-article-item articleItem"}
            )

            data = []
            for article in articles:
                text_div = article.find("div", {"class": "textDiv"})
                p_tag = text_div.find("p")
                if p_tag.text == "":
                    continue

                a_tag = text_div.find("a")
                span_tag = text_div.find("span", {"class": "date"})

                news_date = unicodedata.normalize("NFKD", span_tag.text).replace(
                    " - ", ""
                )
                news_title, news_url = a_tag["title"], a_tag["href"]
                news_description = p_tag.text

                # tính article_id dựa vào weight để sắp xếp lại thứ tự tin tức
                # do tin tức lấy được hiển thị không theo thứ tự
                m = re.search(r"^(\d+) (\w+)", news_date)
                time_amount = m.group(1)
                time_unit = m.group(2)
                if time_unit == "hour" or time_unit == "hours":
                    weight = 100
                elif time_unit == "minutes" or time_unit == "minute":
                    weight = 10
                else:
                    weight = 1

                article_id = weight + int(time_amount)

                data.append(
                    {
                        "id": article_id,
                        "date": news_date,
                        "title": news_title,
                        "url": f"{base_url}{news_url}",
                        "description": news_description,
                    }
                )

            return sorted(data, key=lambda obj: obj["id"])

        else:
            print(f"get_news: {response.status_code}")

    return None


async def get_candles(symbol, timeframe, quantity, time_direction, epoch_time):
    """
    Lấy dữ liệu nến từ API Dukascopy.

    Tham số:
        pairs (str): Cặp tiền tệ.
        timeframe (str): Khoảng thời gian giữa các nến.
        quantity (int): Số lượng nến cần lấy.
        time_direction (str): Hướng thời gian của nến.
            P: past - tính từ nến hiện tại trở về trước
            N: new - tính từ thời điểm có epoch_time trở về sau, yêu cầu epoch_time > 0
        epoch_time (int): Thời gian dạng epoch.
            0: thời gian hiện tại

    Trả về:
        numpy.ndarray: Mảng chứa dữ liệu nến (epoch_date và OHLCV).
        Nếu có lỗi xảy ra trả về mảng rỗng

    """
    epoch_time = int(time.time()) * 1000 if epoch_time == 0 else epoch_time
    dukas_symbol = symbol[:3] + "/" + symbol[3:]

    client = httpx.AsyncClient()

    headers = {
        "Host": "freeserv.dukascopy.com",
        "User-Agent": "Mozilla/5.0",
        "Sec-Ch-Ua-Platform": "Windows",
        "Accept": "*/*",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "script",
        "Referer": "https://freeserv.dukascopy.com/",
    }

    try:
        response = await client.get(
            url=f"https://dukascopy.com/2.0/index.php?path=chart%2Fjson3&instrument={dukas_symbol.upper()}&offer_side=B&interval={timeframe.upper()}&splits=true&stocks=true&limit={quantity}&time_direction={time_direction}&timestamp={epoch_time}&jsonp=_callbacks____0liza023t",
            headers=headers,
        )

    except Exception as err:
        print(f"get_candles: {type(err).__name__}")

    else:
        if response.status_code == 200:
            match = re.search(r"\[[\d\[\]\,\.]*\]|\[null\]", response.text).group()

            if match != [] and match != "[null]":
                # Chuyển đổi chuỗi tìm được sang số và tạo mảng 2D
                data = numpy.array(eval(match))

                return data[::-1] if time_direction == "P" else data

        else:
            print(f"get_candles: {response.status_code}")

    return None


async def get_symbol_news(symbol):
    client = httpx.AsyncClient()
    base_url = "https://www.investing.com"

    symbol_url_style = symbol[:3] + "-" + symbol[3:]

    try:
        response = await client.get(
            url=f"{base_url}/currencies/{symbol_url_style.lower()}-news",
            headers={"User-Agent": "Mozilla/5.0"},
        )

    except Exception as err:
        print(f"get_symbol_news: {type(err).__name__}")

    else:
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            article_links = soup.findAll("a", {"data-test": "article-title-link"})

            articles_arr = []
            for link in article_links:
                articles_arr.append(
                    {
                        "title": link.text,
                        "url": f"{base_url}{link['href']}",
                    }
                )

            return articles_arr

        else:
            print(f"get_symbol_news: {response.status_code}")

    return None
