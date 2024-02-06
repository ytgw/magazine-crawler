######################################################################
# import
######################################################################
import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

import tweepy
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import PoolManager
from urllib3.util import create_urllib3_context  # type: ignore[attr-defined]

API_KEY = os.environ.get("TWITTER_API_KEY")
API_KEY_SECRET = os.environ.get("TWITTER_API_KEY_SECRET")
ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")


######################################################################
# global setting
######################################################################
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "data", "magazine-crawler.log"),
    format="%(asctime)s %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger()


######################################################################
# type, function, class
######################################################################
Weekday = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


class AddedCipherAdapter(HTTPAdapter):
    # https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
    def init_poolmanager(
        self, connections: int, maxsize: Any, block: bool = False, **pool_kwargs: Any
    ) -> Any:
        ctx = create_urllib3_context(ciphers=":HIGH:!DH")
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )


class WeekdayUtil:
    @staticmethod
    def english2int(string: Weekday) -> int:
        if string == "Monday":
            return 0
        if string == "Tuesday":
            return 1
        if string == "Wednesday":
            return 2
        if string == "Thursday":
            return 3
        if string == "Friday":
            return 4
        if string == "Saturday":
            return 5
        if string == "Sunday":
            return 6
        raise Exception(f"{string} is unknown weekday.")

    @staticmethod
    def int2english(num: int) -> Weekday:
        if num == 0:
            return "Monday"
        if num == 1:
            return "Tuesday"
        if num == 2:
            return "Wednesday"
        if num == 3:
            return "Thursday"
        if num == 4:
            return "Friday"
        if num == 5:
            return "Saturday"
        if num == 6:
            return "Sunday"
        raise Exception(f"{num} is unknown weekday. num must be from 0 to 6.")

    @staticmethod
    def english2japanese(english: Weekday) -> str:
        if english == "Monday":
            return "月"
        if english == "Tuesday":
            return "火"
        if english == "Wednesday":
            return "水"
        if english == "Thursday":
            return "木"
        if english == "Friday":
            return "金"
        if english == "Saturday":
            return "土"
        if english == "Sunday":
            return "日"
        raise Exception(f"{english} is unknown weekday.")

    @staticmethod
    def int2japanese(num: int) -> str:
        return WeekdayUtil().english2japanese(WeekdayUtil().int2english(num))


def date2str(input_date: date) -> str:
    date_str = input_date.strftime("%-m/%-d")
    weekday = WeekdayUtil().int2japanese(input_date.weekday())
    return f"{date_str}({weekday})"


@dataclass(frozen=True)
class Magazine:
    id_: str
    name: str
    weekday: Weekday


@dataclass
class MagazineSaleDate:
    magazine: Magazine
    crawl_datetime: datetime
    previous_sale_date: date
    next_sale_date: date

    def __init__(self, magazine: Magazine, delay_time_sec: int = 10) -> None:
        self.magazine = magazine
        self.crawl_datetime = datetime.now()
        self.previous_sale_date = self.__crawl_sale_date(
            f"https://www.fujisan.co.jp/product/{self.magazine.id_}/new/"
        )
        time.sleep(delay_time_sec)
        self.next_sale_date = self.__crawl_sale_date(
            f"https://www.fujisan.co.jp/product/{self.magazine.id_}/next/"
        )
        time.sleep(delay_time_sec)

    def __crawl_sale_date(self, url: str) -> date:
        """WEBサイトをクロールして発売日を取得する。"""
        session = Session()
        session.mount(url, AddedCipherAdapter())
        response = session.get(
            url=url,
            headers={"User-Agent": UserAgent().chrome},
            timeout=(3.0, 3.0),
        )
        soup = BeautifulSoup(response.content, "html.parser")
        sale_date_element = (
            soup.find("body")  # type: ignore
            .find(name="div", attrs={"class": "product-kind-container"})
            .find(name="div", id="product-navi")
            .find(name="ul", attrs={"class": "product-kind-ul"})
            .find(name="li", attrs={"class": "current"})
            .find(name="p")
        )
        sale_date_str = sale_date_element.get_text()  # type: ignore
        sale_datetime = datetime.strptime(sale_date_str, "%Y年%m月%d日")
        return date.fromisoformat(sale_datetime.strftime("%Y-%m-%d"))


@dataclass(frozen=True)
class MessageSender:
    magazine_sale_date: MagazineSaleDate
    client: tweepy.Client

    def send_message(self, today: date) -> None:
        messages = self.__make_message(today=today)
        self.__log(messages=messages)
        for message in messages:
            if os.environ.get("DEBUG") == "False":
                self.client.create_tweet(text=message)
            else:
                print(message)

    def __make_message(self, today: date) -> list[str]:
        """投稿メッセージを返す。"""
        magazine_name = self.magazine_sale_date.magazine.name
        previous_sale_date = self.magazine_sale_date.previous_sale_date
        next_sale_date = self.magazine_sale_date.next_sale_date

        magazine_weekday = self.magazine_sale_date.magazine.weekday
        today_weekday = WeekdayUtil().int2english(today.weekday())

        messages: list[str] = []
        # 休刊の連絡
        if today_weekday == magazine_weekday:
            if today not in [previous_sale_date, next_sale_date]:
                msg = f"【{magazine_name}休刊】"
                msg += f"今日{date2str(today)}は{WeekdayUtil().english2japanese(today_weekday)}曜日ですが、いつもと違い{magazine_name}は休刊です。"
                msg += f"直近の発売日は{date2str(previous_sale_date)}で、次の発売日は{date2str(next_sale_date)}です。"
                messages.append(msg)

        # 発売日の連絡
        if today in [previous_sale_date, next_sale_date]:
            msg = f"【{magazine_name}発売日】"
            msg += f"今日{date2str(today)}は"
            if today_weekday != magazine_weekday:
                msg += f"{WeekdayUtil().english2japanese(today_weekday)}曜日ですが、いつもと違い{magazine_name}の発売日です。"
            else:
                msg += f"{magazine_name}の発売日です。"
            messages.append(msg)

        return messages

    def __log(
        self, messages: list[str], message_make_time: datetime = datetime.now()
    ) -> None:
        data = {
            "DEBUG": os.environ.get("DEBUG"),
            "magazine_id": self.magazine_sale_date.magazine.id_,
            "magazine_name": self.magazine_sale_date.magazine.name,
            "magazine_weekday": self.magazine_sale_date.magazine.weekday,
            "crawl_datetime": self.magazine_sale_date.crawl_datetime.isoformat(),
            "previous_sale_date": self.magazine_sale_date.previous_sale_date.isoformat(),
            "next_sale_date": self.magazine_sale_date.next_sale_date.isoformat(),
            "message_make_time": message_make_time.isoformat(),
            "has_messages": (len(messages) > 0),
            "messages": messages,
        }

        logger.info(str(data))


######################################################################
# main
######################################################################
if __name__ == "__main__":
    MAGAZINES = [
        Magazine(id_="1130", name="週刊少年ジャンプ", weekday="Monday"),
        Magazine(id_="1131", name="週刊少年チャンピオン", weekday="Thursday"),
        Magazine(id_="1132", name="週刊少年マガジン", weekday="Wednesday"),
        Magazine(id_="2651", name="モーニング", weekday="Thursday"),
        Magazine(id_="2680", name="週刊ヤングジャンプ", weekday="Thursday"),
        Magazine(id_="2685", name="週刊ヤングマガジン", weekday="Monday"),
    ]
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_KEY_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )

    for magazine in MAGAZINES:
        today = date.today()
        # today = date(year=2023, month=1, day=16)
        try:
            message_sender = MessageSender(
                magazine_sale_date=MagazineSaleDate(magazine=magazine), client=client
            )
            message_sender.send_message(today=today)
        except Exception as e:
            logger.error(e)
