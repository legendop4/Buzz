import requests
import urllib3
from core.parser import Parser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SessionManager:
    """
    Owns the requests.Session and all authentication logic.
    After calling login(), the session holds valid auth cookies
    that every other module can reuse via .session.
    """

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        self.login_data = config["login"]
        self.proxies = config.get("proxies", None)
        self.session = requests.Session()
        self.parser = Parser()

    # ------------------------------------------------------------------
    # CSRF
    # ------------------------------------------------------------------
    def get_csrf_token(self, url: str) -> str | None:
        """
        GET the given URL and return the value of the first
        <input name="csrf"> found, or None if absent.
        """
        try:
            r = self.session.get(url, verify=False, proxies=self.proxies, timeout=10)
            return self.parser.extract_csrf(r.text)
        except Exception as e:
            print(f"[-] CSRF fetch failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self) -> bool:
        """
        Logs in using credentials from config.
        Returns True if 'Log out' is present in the response (success indicator).
        """
        login_url = self.base_url + "/login"
        csrf_token = self.get_csrf_token(login_url)

        if not csrf_token:
            print("[-] CSRF token not found on login page")
            return False

        data = {
            "csrf": csrf_token,
            "username": self.login_data["username"],
            "password": self.login_data["password"],
        }

        try:
            r = self.session.post(
                login_url, data=data, verify=False,
                proxies=self.proxies, timeout=10
            )
            return "Log out" in r.text
        except Exception as e:
            print(f"[-] Login error: {e}")
            return False