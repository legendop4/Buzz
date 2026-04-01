import argparse
from core.session import SessionManager
from modules.client_trust import ClientSideTrustExploit
from modules.coupon_exploit import CouponExploit
from modules.checkout_manipulation import CheckoutManipulationExploit


# ------------------------------------------------------------------
# Module registry — add new modules here
# ------------------------------------------------------------------
MODULES = {
    "client_trust":           ClientSideTrustExploit,
    "coupon_exploit":         CouponExploit,
    "checkout_manipulation":  CheckoutManipulationExploit,
}


def load_exploit(module_name: str, session, config: dict):
    if module_name not in MODULES:
        print(f"[-] Unknown module: {module_name}")
        return None
    return MODULES[module_name](session, config)


def main():
    parser = argparse.ArgumentParser(
        description="Logic-Buster: Business Logic Exploitation Framework"
    )
    parser.add_argument("--url",      required=True,  help="Target URL")
    parser.add_argument("--module",   required=True,  choices=list(MODULES.keys()), help="Exploit module to run")
    parser.add_argument("--username", default="wiener")
    parser.add_argument("--password", default="peter")
    parser.add_argument("--proxy",    action="store_true", help="Route traffic through Burp (127.0.0.1:8080)")
    parser.add_argument("--coupons",  nargs="+", default=["NEWCUST5"], metavar="CODE",
                        help="Coupon codes to test e.g. --coupons NEWCUST5 SIGNUP30")
    args = parser.parse_args()

    config = {
        "base_url": args.url.rstrip("/"),
        "login": {
            "username": args.username,
            "password": args.password,
        },
        "proxies": {
            "http":  "http://127.0.0.1:8080",
            "https": "http://127.0.0.1:8080",
        } if args.proxy else None,
        "coupons": args.coupons,
    }

    print(f"[+] Target: {args.url}")
    print(f"[+] Module: {args.module}")

    # SessionManager creates and owns the requests.Session + handles login
    mgr = SessionManager(config)
    if not mgr.login():
        print("[-] Login failed — aborting")
        return

    print("[+] Logged in successfully")

    exploit = load_exploit(args.module, mgr.session, config)
    if not exploit:
        return

    exploit.run()


if __name__ == "__main__":
    main()