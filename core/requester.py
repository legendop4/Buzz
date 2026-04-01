import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Requester:
    """
    Thin wrapper around a shared requests.Session.
    Centralises verify=False, proxies, and timeout so every
    module stays free of boilerplate request kwargs.
    """

    def __init__(self, session, config: dict):
        self.session = session
        self.base_url = config["base_url"].rstrip("/")
        self.proxies = config.get("proxies", None)
        self.timeout = config.get("timeout", 10)

    # ------------------------------------------------------------------
    # Core HTTP methods
    # ------------------------------------------------------------------
    def get(self, path: str, **kwargs):
        """GET base_url + path. Returns response or None on error."""
        url = self.base_url + path
        try:
            r = self.session.get(
                url, verify=False, proxies=self.proxies,
                timeout=self.timeout, **kwargs
            )
            return r
        except Exception as e:
            print(f"[-] GET {path} failed: {e}")
            return None

    def post(self, path: str, data: dict, **kwargs):
        """POST base_url + path with form data. Returns response or None on error."""
        url = self.base_url + path
        try:
            r = self.session.post(
                url, data=data, verify=False, proxies=self.proxies,
                timeout=self.timeout, **kwargs
            )
            self._log_status(path, r)
            return r
        except Exception as e:
            print(f"[-] POST {path} failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Cart-specific helpers (used by multiple modules)
    # ------------------------------------------------------------------
    def add_to_cart(self, payload: dict):
        """POST /cart with the given payload."""
        return self.post("/cart", payload)
    def apply_coupon(self, coupon: str, csrf_token: str):
        """POST /cart/coupon — requires CSRF on PortSwigger labs."""
        return self.post("/cart/coupon", {"csrf": csrf_token, "coupon": coupon})
    def get_cart(self):
        """GET /cart — used to read the rendered total."""
        return self.get("/cart")

    def clear_cart(self, product_id: str = "1"):
        """
        Attempt to empty the cart.
        Strategy 1 — POST /cart with quantity=-1 and redir (PortSwigger requires redir).
        Strategy 2 — POST /cart/delete as a fallback.
        """
        r = self.post("/cart", {"productId": product_id, "redir": "PRODUCT", "quantity": "-1"})
        if r is None or r.status_code not in (200, 302):
            self.post("/cart/delete", {"productId": product_id})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _log_status(self, path: str, response):
        print(f"[DEBUG] POST {path} → {response.status_code}")
        if response.status_code == 400:
            print(f"[DEBUG] 400 body: {response.text[:300]}")