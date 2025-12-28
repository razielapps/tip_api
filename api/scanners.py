import requests
import json
import time
import random
from datetime import datetime, date
from urllib.parse import urlparse

class TipScanner:
    def __init__(self, proxy=None):
        self.base_url = "your_url_here"
        self.session = requests.Session()
        
        # Set headers from your original code
        user_agent_string = (
            "User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0"
            ", Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImtleS12MSJ9.eyJpc3MiOiJiZXR3YXRjaCIsImlhdCI6MTc2NDkwMDg3MCwiZXhwIjoxNzY1NTA1NjcwLCJqdGkiOiI1YTNmYTU5OC0wMmYxLTQxZDAtYTY4My0zMGQxMDBmNTI3ZTkiLCJmcCI6IjUyYzUyMzIwNjM4YzJjYTNmYzdiOWM4YTU0N2M1ZWZkOTI1MTFiOWZiZTkzYjYyNmQzNDZhMzYxOWY0MTNiNGQiLCJzY29wZSI6ImFwaTpyZWFkIn0.HxQ6lMD0gIjcTElFjniNsYM76dbFEVE-l5694pIvBDX74uW2IsasH4zg0RpGzcEXiVqvWWOBkTWqNHeUE0DRY9WifnKS2vxjqpj0V79MqDKbz7XyrJ19qioe9PoYxYNPU0n28_k9UUikJV9Bnhbm7ikA6dT1zeg4XAskuX8ilTrf5PGhtaoqai8MCv-vdh3dEi1bkievDMwzCKcCNMZhHOpi6XMBHsfTU7NpM3v6hYEukD6jUL6lPLGeRmAkH65w_cCcH9-k4AFat-R7xCA-uq5Wv5ZoxTWjDmqCJEl4678wp1o__Ux_chCFtH4sXfImAUIT8eDYvq1XTtZDHNVvdw"
            ", host: betwatch.fr"
            ", referrer: your_referrer_here"
            ", prioty: u=4"
            ", Accept: */*"
            ", Connection: keep-alive"
        )
        
        self.session.headers.update({"User-Agent": user_agent_string})
        self.proxy = proxy
        self.request_count = 0
        self.last_request_time = None
    
    def make_request(self, url, step):
        """Make a single request with optional proxy"""
        self.request_count += 1
        
        # Rate limiting
        if self.last_request_time:
            time_since_last = (datetime.utcnow() - self.last_request_time).total_seconds()
            if time_since_last < 2.0:
                wait_time = 2.0 - time_since_last
                time.sleep(wait_time)
        
        try:
            print(f"[REQUEST] Step {step}")
            
            kwargs = {
                'timeout': 30,
                'headers': self.session.headers
            }
            
            if self.proxy:
                kwargs['proxies'] = {
                    'http': self.proxy,
                    'https': self.proxy
                }
            
            response = requests.get(url, **kwargs)
            self.last_request_time = datetime.utcnow()
            
            if response.status_code == 200:
                return response
            else:
                print(f"[ERROR] HTTP {response.status_code} for step {step}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Request failed: {e}")
            return None
    
    def fire_request(self, step, f_date, min_percent=69, max_percent=100, 
                    min_vol=50, max_vol=103, exclude_major_leagues=False):
        """Make request to betwatch.fr"""
        params = (
            f"live_only=false&prematch_only=false&finished_only=false&favorite_only=false"
            f"&utc=1&step={step}&date={f_date}&order_by_time=false"
            f"&not_countries=&not_leagues={'228,2005,39218,3784863,12251791,12374160,12375833,141,10932509,11086347,12199359,59,55,57,81,117,13' if exclude_major_leagues else ''}"
            f"&min_vol={min_vol}&max_vol={max_vol}"
            f"&min_percent={min_percent}&max_percent={max_percent}"
            f"&min_odd=0&max_odd=349&filtering=true"
        )
        
        url = f"{self.base_url}{params}"
        print(f"[REQUEST] URL: {url[:100]}...")
        
        response = self.make_request(url, step)
        
        if response:
            try:
                data = response.json()
                if "data" in data:
                    print(f"[SUCCESS] Got {len(data['data'])} matches")
                return data
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON decode failed: {e}")
                return None
        
        return None
    
    def process_match(self, data, out_list, seen):
        """Process matches and append unique ones"""
        for match in data:
            home = match.get("htn", "") or match.get("home", "")
            away = match.get("atn", "") or match.get("away", "")
            
            try:
                ce = match.get("ce")
                if not ce:
                    continue
                match_time = datetime.fromisoformat(ce.replace("Z", "+00:00"))
            except Exception:
                continue
            
            league = match.get("ln", match.get("league", "Unknown"))
            total_money = match.get("v", 0)
            market_name = match.get("n", "Unknown Market")
            
            if total_money <= 0 or not match.get("i"):
                continue
            
            outcomes = match["i"]
            money_split = {item[0]: item[1] for item in outcomes if len(item) >= 2}
            odds_split = {
                item[0]: (item[3] if len(item) > 3 else None) for item in outcomes
            }
            
            if not money_split:
                continue
            
            percentages = {
                code: round((money / total_money) * 100, 2)
                for code, money in money_split.items()
            }
            
            dominant_code = max(percentages, key=percentages.get)
            dominant_pct = percentages[dominant_code]
            
            odds_for_dominant = odds_split.get(dominant_code)
            
            match_key = f"{league}|{home}|{away}|{market_name}|{dominant_code}"
            if match_key in seen:
                continue
            seen.add(match_key)
            
            dominant_money = money_split.get(dominant_code, 0)
            
            match_item = {
                "league": league,
                "match": f"{home} vs {away}",
                "match_kickoff": match_time.isoformat(),
                "pick": self.get_label(dominant_code, home, away),
                "odds": odds_for_dominant,
                "percentage": dominant_pct,
                "market": market_name,
                "is_hot": dominant_pct >= 85,
                "total_money": total_money,
                "dominant_money": dominant_money,
            }
            out_list.append(match_item)
    
    def get_label(self, code, home, away):
        if code == "1":
            return home
        elif code == "2":
            return away
        elif code == "X":
            return "Draw"
        elif code in ["Over", "Under"] or "Over" in code or "Under" in code:
            return code.replace("_", " ")
        else:
            return code
    
    def fetch_matches_once(self, threshold_pct=69, limit=None, live_only=False, 
                          exclude_major=False, time_order=False, proxy=None):
        """Fetch matches and ensure uniqueness"""
        today = date.today()
        f_date = today.strftime("%Y-%m-%d")
        step = 1
        remaining = True
        match_list = []
        seen = set()
        
        if proxy:
            self.proxy = proxy
        
        while remaining:
            req = self.fire_request(
                step,
                f_date,
                min_percent=threshold_pct,
                max_percent=100,
                exclude_major_leagues=exclude_major,
            )
            
            if not req or "data" not in req:
                break
            
            if not req["data"]:
                remaining = False
                break
            
            self.process_match(req["data"], match_list, seen)
            
            remaining = req.get("remaining", False)
            if remaining:
                step += 1
            
            time.sleep(random.uniform(0.3, 0.8))
        
        if limit:
            return match_list[:limit]
        return match_list

class UnderdogTipScanner(TipScanner):
    def __init__(self, proxy=None):
        super().__init__(proxy)
        
        # Hardcoded underdog parameters
        self.not_countries = "GB,US,BE,FR,DE"
        self.not_leagues = "228,39218,3784863,35,37,41,43,105,107,109,111,30558,252549,7129730,10932509,11086347,12199359,12202273,141,89979,11717188,55,57,1081960,59,61,11591693"
        self.min_vol = 51
        self.max_vol = 103
    
    def fire_request(self, step, f_date, min_percent=69, max_percent=100):
        """Override fire_request with underdog parameters"""
        params = (
            f"live_only=false&prematch_only=false&finished_only=false&favorite_only=false"
            f"&utc=1&step={step}&date={f_date}&order_by_time=false"
            f"&not_countries={self.not_countries}&not_leagues={self.not_leagues}"
            f"&min_vol={self.min_vol}&max_vol={self.max_vol}"
            f"&min_percent={min_percent}&max_percent={max_percent}"
            f"&min_odd=0&max_odd=349&filtering=true"
        )
        
        url = f"{self.base_url}{params}"
        print(f"[UNDERDOG REQUEST] Step {step}")
        
        response = self.make_request(url, step)
        
        if response:
            try:
                data = response.json()
                if "data" in data:
                    print(f"[UNDERDOG SUCCESS] Step {step}: {len(data['data'])} matches")
                return data
            except json.JSONDecodeError as e:
                print(f"[UNDERDOG ERROR] JSON decode failed: {e}")
                return None
        
        return None