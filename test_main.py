from datetime import date, datetime, timedelta

import pytest
import tweepy

from main import Magazine, MagazineSaleDate, MessageSender, Weekday


class FakeMagazineSaleDate(MagazineSaleDate):
    def __init__(
        self,
        magazine: Magazine,
        crawl_datetime: datetime,
        previous_sale_date: date,
        next_sale_date: date,
    ) -> None:
        self.magazine = magazine
        self.crawl_datetime = crawl_datetime
        self.previous_sale_date = previous_sale_date
        self.next_sale_date = next_sale_date


def create_message_sender(sale_date: date, magazine_weekday: Weekday) -> MessageSender:
    magazine_sale_date = FakeMagazineSaleDate(
        magazine=Magazine(id_="0", name="foo", weekday=magazine_weekday),
        crawl_datetime=datetime.now(),
        previous_sale_date=sale_date,
        next_sale_date=sale_date,
    )

    sender = MessageSender(
        magazine_sale_date=magazine_sale_date, client=tweepy.Client()
    )
    return sender


@pytest.mark.filterwarnings(
    "ignore: Unverified HTTPS request is being made to host 'www.fujisan.co.jp'."
)
def test_web_crawl() -> None:
    MAGAZINES = [
        Magazine(id_="1130", name="週刊少年ジャンプ", weekday="Monday"),
        Magazine(id_="1131", name="週刊少年チャンピオン", weekday="Thursday"),
        Magazine(id_="1132", name="週刊少年マガジン", weekday="Wednesday"),
        Magazine(id_="2651", name="モーニング", weekday="Thursday"),
        Magazine(id_="2680", name="週刊ヤングジャンプ", weekday="Thursday"),
        Magazine(id_="2685", name="週刊ヤングマガジン", weekday="Monday"),
    ]
    for magazine in MAGAZINES:
        # 例外が発生しないこと
        MagazineSaleDate(magazine=magazine, delay_time_sec=0)


def test_normal_sale_date_message() -> None:
    # 2023/4/30は日曜日
    sunday = date(year=2023, month=4, day=30)
    sender = create_message_sender(sale_date=sunday, magazine_weekday="Sunday")

    messages = sender._MessageSender__make_message(today=sunday)  # type: ignore[attr-defined]
    assert len(messages) == 1
    assert messages[0] == "【foo発売日】今日4/30(日)はfooの発売日です。"


def test_abnormal_sale_date_message() -> None:
    # 2023/4/30は日曜日
    sunday = date(year=2023, month=4, day=30)
    sender = create_message_sender(sale_date=sunday, magazine_weekday="Monday")

    messages = sender._MessageSender__make_message(today=sunday)  # type: ignore[attr-defined]
    assert len(messages) == 1
    assert (
        messages[0]
        == "【foo発売日】今日4/30(日)は日曜日ですが、いつもと違いfooの発売日です。"
    )


def test_normal_non_sale_date_message() -> None:
    # 2023/4/30は日曜日
    sunday = date(year=2023, month=4, day=30)
    sender = create_message_sender(sale_date=sunday, magazine_weekday="Sunday")

    messages = sender._MessageSender__make_message(today=sunday + timedelta(days=1))  # type: ignore[attr-defined]
    assert len(messages) == 0


def test_abnormal_non_sale_date_message() -> None:
    # 2023/4/30は日曜日
    sunday = date(year=2023, month=4, day=30)
    sender = create_message_sender(sale_date=sunday, magazine_weekday="Monday")

    messages = sender._MessageSender__make_message(today=sunday + timedelta(days=1))  # type: ignore[attr-defined]
    assert len(messages) == 1
    assert (
        messages[0]
        == "【foo休刊】今日5/1(月)は月曜日ですが、いつもと違いfooは休刊です。直近の発売日は4/30(日)で、次の発売日は4/30(日)です。"
    )
