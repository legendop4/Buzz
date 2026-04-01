from bs4 import BeautifulSoup


class Parser:
    """
    All HTML parsing lives here.
    Methods accept raw HTML strings and return Python values —
    no requests.Response objects, no session — purely functional.
    """

    CURRENCY_SYMBOLS = ("$", "£", "€")
    EMPTY_CART_PHRASES = ("your cart is empty", "no items", "0 items")

    # ------------------------------------------------------------------
    # CSRF
    # ------------------------------------------------------------------
    def extract_csrf(self, html: str) -> str | None:
        """Return the value of <input name="csrf">, or None."""
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("input", {"name": "csrf"})
        return tag["value"] if tag else None

    # ------------------------------------------------------------------
    # Hidden form fields
    # ------------------------------------------------------------------
    def extract_hidden_fields(self, html: str) -> dict:
        """
        Return all <input type="hidden"> name→value pairs.
        Useful for scraping required fields like 'redir' automatically
        instead of hardcoding them in payloads.
        """
        soup = BeautifulSoup(html, "html.parser")
        return {
            tag["name"]: tag.get("value", "")
            for tag in soup.find_all("input", {"type": "hidden"})
            if tag.get("name")
        }

    # ------------------------------------------------------------------
    # Cart total
    # ------------------------------------------------------------------
    def extract_total(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"])
            for i, cell in enumerate(cells):
                # strip trailing colon — lab renders 'Total:' not 'Total'
                label = cell.get_text(strip=True).lower().rstrip(":")
                if label == "total":
                    if i + 1 < len(cells):
                        return cells[i + 1].get_text(strip=True)

        # Scoped currency fallback inside tables only
        for table in soup.find_all("table"):
            for tag in table.find_all(string=True):
                text = tag.strip()
                if (
                    text
                    and any(sym in text for sym in self.CURRENCY_SYMBOLS)
                    and any(c.isdigit() for c in text)
                ):
                    return text

        page_text = soup.get_text(separator=" ").lower()
        if any(phrase in page_text for phrase in self.EMPTY_CART_PHRASES):
            return "$0.00"

        return None

    def extract_discount(self, html: str) -> str | None:
        """
        Handles two layouts:
          Layout A — single 'Discount' label row: ['Discount', '-$5.00']
          Layout B — Code/Reduction table: ['NEWCUST5', '-$5.00']
                     identified by a header row containing 'Reduction'
        """
        soup = BeautifulSoup(html, "html.parser")

        # Detect if this table uses Code/Reduction headers
        has_reduction_table = False
        for row in soup.find_all("tr"):
            cells = [c.get_text(strip=True).lower() for c in row.find_all(["th", "td"])]
            if "reduction" in cells:
                has_reduction_table = True
                break

        if has_reduction_table:
            # Collect all discount values from the Reduction column (negative currency)
            discounts = []
            for row in soup.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    val = cells[-1].get_text(strip=True)
                    if val.startswith("-") and any(s in val for s in self.CURRENCY_SYMBOLS):
                        discounts.append(val)
            return ", ".join(discounts) if discounts else None

        # Layout A — look for a 'discount' labelled cell
        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"])
            for i, cell in enumerate(cells):
                if "discount" in cell.get_text(strip=True).lower():
                    if i + 1 < len(cells):
                        return cells[i + 1].get_text(strip=True)

        return None

    def extract_store_credit(self, html: str) -> str | None:
        """
        Extract the store credit / account balance shown in the header.
        PortSwigger renders this as 'Store credit: $X.XX'.
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(string=True):
            text = tag.strip()
            if "store credit" in text.lower() and any(c.isdigit() for c in text):
                # Extract just the currency part after the colon
                if ":" in text:
                    return text.split(":", 1)[1].strip()
                return text
        return None

    def coupon_was_rejected(self, html: str) -> bool:
        """
        Return True if the page contains a coupon error/rejection message.
        """
        indicators = [
            "coupon already applied",
            "invalid coupon",
            "coupon not valid",
            "unrecognised coupon",
            "expired coupon",
        ]
        text = html.lower()
        return any(phrase in text for phrase in indicators)

    def parse_price(self, value: str) -> float | None:
        """
        Convert a display price like '$45.00' or '-$10.00' to a float.
        Returns None if parsing fails.
        """
        try:
            cleaned = value.replace(",", "")
            for sym in self.CURRENCY_SYMBOLS:
                cleaned = cleaned.replace(sym, "")
            return float(cleaned.strip())
        except (ValueError, AttributeError):
            return None