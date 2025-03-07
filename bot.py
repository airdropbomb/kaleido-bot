import requests
import time
import json
import asyncio
import os
from colorama import Fore, Style, init
import random

# Initialize colorama
init(autoreset=True)

class KaleidoMiningBot:
    def __init__(self, wallet, bot_index, proxy=None):
        self.wallet = wallet
        self.bot_index = bot_index
        self.proxy = proxy
        self.current_earnings = {"total": 0, "pending": 0, "paid": 0}
        self.mining_state = {
            "is_active": False,
            "worker": "quantum-rig-1",
            "pool": "quantum-1",
            "start_time": None
        }
        self.referral_bonus = 0
        self.stats = {
            "hashrate": 75.5,
            "shares": {"accepted": 0, "rejected": 0},
            "efficiency": 1.4,
            "power_usage": 120
        }
        self.api = requests.Session()
        self.api.headers.update({
            "Content-Type": "application/json",
            "Referer": "https://kaleidofinance.xyz/testnet",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
        })
        if self.proxy:
            self.api.proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
        self.base_url = "https://kaleidofinance.xyz/api/testnet"

    async def initialize(self):
        try:
            if self.proxy:
                print(f"{Fore.YELLOW}[ℹ️] Account [{self.bot_index}] Using proxy: {self.proxy}{Style.RESET_ALL}")
            reg_response = await self.retry_request(
                lambda: self.api.get(f"{self.base_url}/check-registration?wallet={self.wallet}"),
                "Registration check"
            )

            if not reg_response.json().get("isRegistered", False):
                raise Exception("Wallet not registered")

            self.referral_bonus = reg_response.json().get("userData", {}).get("referralBonus", 0)
            self.current_earnings = {
                "total": self.referral_bonus,
                "pending": 0,
                "paid": 0
            }
            self.mining_state["start_time"] = int(time.time() * 1000)
            self.mining_state["is_active"] = True

            print(f"{Fore.GREEN}[✅] Account [{self.bot_index}] Mining initialized successfully{Style.RESET_ALL}")
            await self.start_mining_loop()

        except Exception as e:
            print(f"{Fore.RED}[❌] Account [{self.bot_index}] Initialization failed: {e}{Style.RESET_ALL}")

    async def retry_request(self, request_fn, operation_name, retries=3):
        for i in range(retries):
            try:
                response = request_fn()
                if response.status_code == 200:
                    return response
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                if i == retries - 1:
                    raise e
                print(f"{Fore.YELLOW}[{operation_name}] Retrying ({i + 1}/{retries})...{Style.RESET_ALL}")
                await asyncio.sleep(2 * (i + 1))

    def calculate_earnings(self):
        time_elapsed = (int(time.time() * 1000) - self.mining_state["start_time"]) / 1000
        return (self.stats["hashrate"] * time_elapsed * 0.0001) * (1 + self.referral_bonus)

    async def update_balance(self):
        try:
            new_earnings = self.calculate_earnings()
            payload = {
                "wallet": self.wallet,
                "earnings": {
                    "total": self.current_earnings["total"] + new_earnings,
                    "session": new_earnings,
                    "lastUpdate": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
                }
            }

            response = await self.retry_request(
                lambda: self.api.post(f"{self.base_url}/update-balance", json=payload),
                "Balance update"
            )

            if response.json().get("success", False):
                self.current_earnings["total"] = response.json().get("balance", 0)
                print(f"{Fore.CYAN}[➡️] Account [{self.bot_index}] Balance updated: {Fore.GREEN}{self.current_earnings['total']}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[❌] Account [{self.bot_index}] Failed to update balance: {response.text}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}[❌] Account [{self.bot_index}] Update failed: {e}{Style.RESET_ALL}")

    async def start_mining_loop(self):
        while self.mining_state["is_active"]:
            await self.update_balance()
            print(f"{Fore.MAGENTA}================================================={Style.RESET_ALL}")
            await asyncio.sleep(30)

    async def stop(self):
        self.mining_state["is_active"] = False
        await self.update_balance()
        return self.current_earnings["paid"]


class MiningCoordinator:
    def __init__(self):
        self.bots = []
        self.total_paid = 0
        self.is_running = False
        self.proxies = []

    async def load_wallets(self):
        try:
            with open("wallets.txt", "r") as file:
                return [line.strip() for line in file if line.startswith("0x")]
        except Exception as e:
            print(f"{Fore.RED}Error loading wallets: {e}{Style.RESET_ALL}")
            return []

    async def load_proxies(self):
        try:
            with open("proxy.txt", "r") as file:
                self.proxies = [line.strip() for line in file if line.strip()]
            if not self.proxies:
                print(f"{Fore.YELLOW}[ℹ️] No proxies found in proxy.txt, running without proxies{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}[ℹ️] Loaded {len(self.proxies)} proxies from proxy.txt{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error loading proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    async def start(self):
        if self.is_running:
            print(f"{Fore.YELLOW}Mining coordinator is already running{Style.RESET_ALL}")
            return

        self.is_running = True

        os.system("cls" if os.name == "nt" else "clear")
        self.display_banner()

        wallets = await self.load_wallets()
        await self.load_proxies()

        if not wallets:
            print(f"{Fore.RED}No valid wallets found in wallets.txt{Style.RESET_ALL}")
            return

        print(f"{Fore.CYAN}[🕵️‍♀️] Total account : {len(wallets)}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}================================================={Style.RESET_ALL}")

        # Proxy တွေကို wallet တစ်ခုချင်းစီအတွက် assign လုပ်တယ်
        self.bots = []
        for i, wallet in enumerate(wallets):
            # Proxy ရှိရင် random တစ်ခု ရွေးမယ်၊ မရှိရင် None
            proxy = random.choice(self.proxies) if self.proxies else None
            self.bots.append(KaleidoMiningBot(wallet, i + 1, proxy=proxy))

        await asyncio.gather(*[bot.initialize() for bot in self.bots])

        import signal
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def display_banner(self):
        BANNER = f"""
{Fore.CYAN}
       █████╗ ██████╗ ██████╗     ███╗   ██╗ ██████╗ ██████╗ ███████╗
      ██╔══██╗██╔══██╗██╔══██╗    ████╗  ██║██╔═══██╗██╔══██╗██╔════╝
      ███████║██║  ██║██████╔╝    ██╔██╗ ██║██║   ██║██║  ██║█████╗  
      ██╔══██║██║  ██║██╔══██╗    ██║╚██╗██║██║   ██║██║  ██║██╔══╝  
      ██║  ██║██████╔╝██████╔╝    ██║ ╚████║╚██████╔╝██████╔╝███████╗
      ╚═╝  ╚═╝╚═════╝ ╚═════╝     ╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝ 
{Style.RESET_ALL}
Bot Auto Mining Kaleido 
{Fore.YELLOW}Telegram : https://t.me/airdropbombnode{Style.RESET_ALL}
        """
        print(BANNER)

    async def handle_shutdown(self, signum, frame):
        print(f"\n{Fore.YELLOW}Shutting down miners...{Style.RESET_ALL}")
        self.total_paid = sum([await bot.stop() for bot in self.bots])
        print(f"""
{Fore.MAGENTA}=================================================
   💰 Final Summary
=================================================
{Fore.CYAN}Total Wallets: {len(self.bots)}
{Fore.GREEN}Total Paid: {self.total_paid:.8f} KLDO
{Fore.MAGENTA}================================================={Style.RESET_ALL}
        """)
        exit()


if __name__ == "__main__":
    coordinator = MiningCoordinator()
    asyncio.run(coordinator.start())
