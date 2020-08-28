from typing import Optional, OrderedDict, Dict, Any
from dataclasses import dataclass, field

import time
import logging

import requests


def timestamp_ms_offset_to_utc8() -> int:
    return int((time.time() + 60*60*8)*1000)


@dataclass
class AnoBBSClient:

    appid: str
    user_agent: str

    host: str

    session: requests.Session = field(default_factory=requests.Session)
    userhash: Optional[str] = None

    def get_thread(self, id: int, page: int, with_login: bool = True, max_attempt_count: int = 3) -> OrderedDict[str, Any]:
        logging.debug(f"将获取串：{id} 第 {page} 页，已登陆：{with_login}")

        for i in range(1, max_attempt_count+1):
            try:
                thread = self.__get_thread(
                    id, page=page, with_login=with_login)
                thread["replys"] = list(filter(
                    lambda post: post["userid"] != "芦苇", thread["replys"]))
            except (requests.exceptions.RequestException, ValueError) as e:
                if i < max_attempt_count:
                    logging.warning(
                        f'获取串 {id} 第 {page} 页失败: {e}. 尝试: {i}/{max_attempt_count}')
                else:
                    logging.error(
                        f'无法获取串 {id} 第 {page} 页: {e}. 已经失败 {max_attempt_count} 次. 放弃')
                    raise e
            else:
                return thread

    def __get_thread(self, id: int, page: int, with_login: bool = False) -> OrderedDict[str, Any]:

        self.__setup_headers(with_login=with_login)

        ts = timestamp_ms_offset_to_utc8()
        url = f"https://{self.host}/Api/thread/id/{id}?page={page}&appid={self.appid}&__t={ts}"
        resp = self.session.get(url)

        return resp.json(object_pairs_hook=OrderedDict)

    def __setup_headers(self, with_login: bool = False):

        if not with_login:
            requests.cookies.remove_cookie_by_name(
                self.session.cookies, "userhash", domain=self.host)
        elif self.userhash != None:
            cookie = requests.cookies.create_cookie(
                name="userhash", value=self.userhash, domain=self.host,
            )
            self.session.cookies.set_cookie(cookie)

        # 芦苇岛搞错了？
        for (k, v) in {
            "expires": "Friday,24-Jan-2027 16:24:36 GMT",
            "domains": self.host,
            "path": "/",
        }.items():
            if k not in self.session.cookies.keys():
                cookie = requests.cookies.create_cookie(
                    name=k, value=v, domain=self.host,
                )
                self.session.cookies.set_cookie(cookie)

        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip, deflate, br",
        })

    def has_logged_in(self) -> bool:
        return self.userhash != None
