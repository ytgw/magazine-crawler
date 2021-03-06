######################################################################
# import
######################################################################
import logging, os, time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import requests, tweepy, urllib3
from bs4 import BeautifulSoup
from fake_useragent import UserAgent  #type: ignore

API_KEY = os.environ['TWITTER_API_KEY']
API_KEY_SECRET = os.environ['TWITTER_API_KEY_SECRET']
ACCESS_TOKEN = os.environ['TWITTER_ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = os.environ['TWITTER_ACCESS_TOKEN_SECRET']


######################################################################
# global setting
######################################################################
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # type: ignore
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += "HIGH:!DH"  # type: ignore

logging.basicConfig(
    filename = os.path.join(os.path.dirname(__file__), 'data', 'magazine-crawler.log'),
    format = '%(asctime)s %(levelname)s - %(message)s',
    level = logging.INFO
)
logger = logging.getLogger()


######################################################################
# type, function, class
######################################################################
Weekday = Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class WeekdayUtil:
    @staticmethod
    def english2int(string: Weekday) -> int:
        if string == 'Monday':    return 0
        if string == 'Tuesday':   return 1
        if string == 'Wednesday': return 2
        if string == 'Thursday':  return 3
        if string == 'Friday':    return 4
        if string == 'Saturday':  return 5
        if string == 'Sunday':    return 6
        raise Exception(f'{string} is unknown weekday.')


    @staticmethod
    def int2english(num: int) -> Weekday:
        if num == 0: return 'Monday'
        if num == 1: return 'Tuesday'
        if num == 2: return 'Wednesday'
        if num == 3: return 'Thursday'
        if num == 4: return 'Friday'
        if num == 5: return 'Saturday'
        if num == 6: return 'Sunday'
        raise Exception(f'{num} is unknown weekday. num must be from 0 to 6.')


    @staticmethod
    def english2japanese(english: Weekday) -> str:
        if english == 'Monday':    return '?????????'
        if english == 'Tuesday':   return '?????????'
        if english == 'Wednesday': return '?????????'
        if english == 'Thursday':  return '?????????'
        if english == 'Friday':    return '?????????'
        if english == 'Saturday':  return '?????????'
        if english == 'Sunday':    return '?????????'
        raise Exception(f'{english} is unknown weekday.')


    @staticmethod
    def int2japanese(num: int) -> str:
        return WeekdayUtil().english2japanese(WeekdayUtil().int2english(num))


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


    def __init__(self, magazine: Magazine) -> None:
        DELAY_TIME_SEC = 10
        self.magazine = magazine
        self.crawl_datetime = datetime.now()
        self.previous_sale_date = self.__crawl_sale_date(f'https://www.fujisan.co.jp/product/{self.magazine.id_}/new/')
        time.sleep(DELAY_TIME_SEC)
        self.next_sale_date = self.__crawl_sale_date(f'https://www.fujisan.co.jp/product/{self.magazine.id_}/next/')
        time.sleep(DELAY_TIME_SEC)


    def __crawl_sale_date(self, url: str) -> date:
        """WEB?????????????????????????????????????????????????????????
        """
        response = requests.get(url=url, headers={'User-Agent': UserAgent().chrome}, timeout=(3.0, 3.0), verify=False)  #type: ignore
        soup = BeautifulSoup(response.content, 'html.parser')
        sale_date_element = soup.find('body').find(name='div', attrs={'class': 'product-kind-container'}).find(name='div', id='product-navi').find(name='ul', attrs={'class': 'product-kind-ul'}).find(name='li', attrs={'class': 'current'}).find(name='p')  #type: ignore
        sale_date_str = sale_date_element.get_text()  #type: ignore
        sale_datetime = datetime.strptime(sale_date_str, '%Y???%m???%d???')
        return date.fromisoformat(sale_datetime.strftime('%Y-%m-%d'))


@dataclass(frozen=True)
class MessageSender:
    magazine_sale_date: MagazineSaleDate
    client: tweepy.Client  # type: ignore


    def send_message(self, today: date) -> None:
        messages = self.__make_message(today=today)
        self.__log(messages=messages)
        for message in messages:
            if os.environ.get('DEBUG') == 'False':
                self.client.create_tweet(text=message)  # type: ignore
            else:
                print(message)


    def __make_message(self, today: date) -> list[str]:
        """?????????????????????????????????
        """
        magazine_name = self.magazine_sale_date.magazine.name
        previous_sale_date = self.magazine_sale_date.previous_sale_date
        next_sale_date = self.magazine_sale_date.next_sale_date

        magazine_weekday = self.magazine_sale_date.magazine.weekday
        today_weekday = WeekdayUtil().int2english(today.weekday())

        messages: list[str] = []
        # ???????????????
        if today_weekday == magazine_weekday:
            if today not in [previous_sale_date, next_sale_date]:
                msg = f'???{magazine_name}?????????'
                msg += f'?????????{WeekdayUtil().english2japanese(today_weekday)}??????????????????????????????{magazine_name}??????????????????'
                msg += f'??????????????????{next_sale_date.strftime("%-m???%-d???")}{WeekdayUtil().int2japanese(next_sale_date.weekday())}?????????'
                messages.append(msg)

        # ??????????????????
        if today in [previous_sale_date, next_sale_date]:
            msg = f'???{magazine_name}????????????'
            if today_weekday != magazine_weekday:
                msg += f'?????????{WeekdayUtil().english2japanese(today_weekday)}??????????????????????????????{magazine_name}?????????????????????'
            else:
                msg += f'?????????{magazine_name}?????????????????????'
            messages.append(msg)

        return messages


    def __log(self, messages: list[str], message_make_time: datetime=datetime.now()) -> None:
        data = {
            'DEBUG': os.environ.get('DEBUG'),
            'magazine_id': self.magazine_sale_date.magazine.id_,
            'magazine_name': self.magazine_sale_date.magazine.name,
            'magazine_weekday': self.magazine_sale_date.magazine.weekday,

            'crawl_datetime': self.magazine_sale_date.crawl_datetime.isoformat(),
            'previous_sale_date': self.magazine_sale_date.previous_sale_date.isoformat(),
            'next_sale_date': self.magazine_sale_date.next_sale_date.isoformat(),

            'message_make_time': message_make_time.isoformat(),
            'has_messages': (len(messages) > 0 ),
            'messages': messages,
        }

        logger.info(str(data))


######################################################################
# main
######################################################################
if __name__ == '__main__':
    MAGAZINES = [
        Magazine(id_='1130', name='????????????????????????', weekday='Monday'),
        Magazine(id_='1131', name='??????????????????????????????', weekday='Thursday'),
        Magazine(id_='1132', name='????????????????????????', weekday='Wednesday'),

        Magazine(id_='2651', name='???????????????', weekday='Thursday'),
        Magazine(id_='2680', name='???????????????????????????', weekday='Thursday'),
        Magazine(id_='2685', name='???????????????????????????', weekday='Monday'),
    ]
    client = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)  # type: ignore


    for magazine in MAGAZINES:
        try:
            message_sender = MessageSender(magazine_sale_date=MagazineSaleDate(magazine=magazine), client=client)  # type: ignore
            message_sender.send_message(today=date.today())
        except Exception as e:
            logger.error(e)
