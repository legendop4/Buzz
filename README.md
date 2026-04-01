# 🐝 Buzzy — Business Logic Vulnerability Scanner

Buzzy is a modular Python-based tool designed to detect **business logic vulnerabilities** in web applications by simulating real attacker workflows.

Unlike traditional scanners that focus on injections, Buzzy targets **application logic flaws** such as:

* Coupon abuse
* Infinite money vulnerabilities
* Checkout manipulation
* Client-side trust issues
* Workflow/state machine flaws

---

## 🚀 Features

### 🔍 Client-Side Trust Exploitation

* Detects price manipulation
* Tests quantity tampering
* Identifies negative/invalid value acceptance

---

### 🎟️ Coupon Exploitation Engine

* Coupon reuse detection
* Coupon stacking attacks
* Automated **gift card infinite money loop**

---

### 💳 Checkout Manipulation Module

* Double checkout (replay attack)
* Checkout without cart validation
* Workflow bypass (state manipulation)
* Order confirmation reuse
* Race condition testing (impact-based detection)

---

### ⚙️ Smart Detection Engine

Buzzy avoids false positives by focusing on **real impact**, not just HTTP responses.

✔ Detects:

* Store credit changes
* Duplicate order confirmations
* Unexpected state transitions

❌ Ignores:

* Simple HTTP 200 responses without impact

---

## 🧠 How It Works

Buzzy mimics real attacker behavior:

1. Interacts with application endpoints
2. Manipulates workflows (cart → coupon → checkout)
3. Replays and automates requests
4. Analyzes **application state changes**

---

## 🏗️ Project Structure

```
buzzy/
│
├── core/
│   ├── requester.py      # HTTP request handler
│   ├── parser.py         # Response parsing utilities
│
├── modules/
│   ├── client_trust.py
│   ├── coupon_exploit.py
│   ├── checkout_manipulation.py
│
├── main.py               # Entry point
└── config.py             # Configuration
```

---

## ⚡ Installation

```bash
git clone https://github.com/your-username/buzzy.git
cd buzzy
pip install -r requirements.txt
```

---

## ▶️ Usage

### Run Client Trust Module

```bash
python main.py --url <target> --module client_trust
```

### Run Coupon Exploit Module

```bash
python main.py --url <target> --module coupon_exploit --coupons NEWCUST5 SIGNUP30
```

### Run Checkout Manipulation Module

```bash
python main.py --url <target> --module checkout_manipulation
```

---

## 🧪 Tested On

Buzzy is designed and tested using PortSwigger Web Security Academy labs.

### Validated Labs:

* Infinite money logic flaw
* Flawed enforcement of business rules
* Excessive trust in client-side controls
* Inconsistent handling of discount coupons

---

## 📊 Example Output

```bash
[+] CHECKOUT MANIPULATION SUMMARY TABLE

double_checkout        | [SAFE]
no_cart_checkout       | [SAFE]
flow_bypass            | [SAFE]
confirmation_reuse     | [SAFE]
checkout_race          | [SAFE]

[*] Summary: 0/5 vulnerabilities found
```

---

## 🎯 Why Buzzy?

Most tools focus on:

* SQL Injection
* XSS
* CSRF

But real-world bugs often come from:

👉 **Broken logic, not broken code**

Buzzy focuses on:

* Workflow abuse
* Feature chaining
* State manipulation

---

## ⚠️ Disclaimer

This tool is for **educational and authorized testing only**.

Do NOT use it against systems without permission.

---

## 🧠 Future Improvements

* Authentication flow testing
* Multi-user race condition engine
* Advanced state machine analysis
* Report generation (JSON/HTML)

---

## 👨‍💻 Author

Built as a cybersecurity learning project focused on **real-world bug bounty techniques**.

---

## ⭐ Contribute

Feel free to:

* Open issues
* Suggest features
* Improve detection modules

---

## 🔥 Final Note

Buzzy is not just a scanner — it’s a **workflow exploitation engine**.
