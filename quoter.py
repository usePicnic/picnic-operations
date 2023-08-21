import os
import json
import requests
from web3 import Web3
from eth_abi.packed import encode_packed

# URL for Alchemy API
ALCHEMY_URL = f'https://polygon-mainnet.g.alchemy.com/v2/{os.getenv("ALCHEMY_API_KEY")}'

w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
w3.is_connected()

# Tokens info
brla_token = {
    "address": "0xE6A537a407488807F0bbeb0038B79004f19DDDFb",
    "symbol": "BRLA",
    "name": "BRLA Token",
    "currency": "BRL",
    "decimals": 18,
}
usdc_token = {
    "address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "symbol": "USDC",
    "name": "USD Coin (POS)",
    "currency": "USD",
    "decimals": 6,
}
brz_token_old = {
    "address": "0x491a4eB4f1FC3BfF8E1d2FC856a6A46663aD556f",
    "symbol": "BRZ (old)",
    "name": "BRZ Token",
    "currency": "BRL",
    "decimals": 4,
}
brz_token = {
    "address": "0x4eD141110F6EeeAbA9A1df36d8c26f684d2475Dc",
    "symbol": "BRZ",
    "name": "BRZ Token",
    "currency": "BRL",
    "decimals": 18,
}

# Quickswap's quoter address
QUOTER_ADDRESS = "0xa15F0D7377B2A0C0c10db057f641beD21028FC89"


class QuoteConnector:
    def get_quote(self, token0, token1, amount):
        raise NotImplementedError

    def get_name(self):
        return self.__class__.__name__


class ParaswapConnector(QuoteConnector):
    BASE_URL = "https://apiv5.paraswap.io"

    def get_quote(self, token0, token1, amount, **kwargs):
        endpoint = "/prices"

        # Prepare the request payload
        params = {
            "srcToken": token0["address"],
            "srcDecimals": token0["decimals"],
            "destToken": token1["address"],
            "destDecimals": token1["decimals"],
            "amount": amount,
            "side": kwargs.get("side", "SELL"),  # Default to "SELL"
            "network": kwargs.get("network", "1"),  # Default to "Mainnet"
        }

        # Removing None values
        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(self.BASE_URL + endpoint, params=params)
        data = response.json()

        # Verify the successful response structure and extract the destination amount
        if "priceRoute" in data and "destAmount" in data["priceRoute"]:
            return data["priceRoute"]["destAmount"]
        else:
            raise ValueError(f"Unexpected response format from Paraswap: {data}")


class LiquidityCalculator:
    def __init__(self, connectors, token0, token1, base_rate=0):
        self.connectors = connectors
        self.token0 = token0
        self.token1 = token1
        self.amounts = [100, 1000, 2000, 5000]  # Standardized amounts
        self.base_rate = base_rate if base_rate != 0 else self.get_base_rate()
        print(f"Starting Liq Calc for {self.token0['symbol']}-{self.token1['symbol']}")
        print(f"Base Rate: {self.base_rate:.3f}")

    def get_base_rate(self):
        base_currency = self.token0["currency"]
        response = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        )
        data = response.json()
        return data["rates"][self.token1["currency"]]

    def check_liquidity(self):
        report = ""
        for connector in self.connectors:
            report += f"Checking liquidity for connector: {connector.get_name()}\n"
            for amount in self.amounts:
                adjusted_amount = (
                    amount / self.base_rate
                    if self.token0["currency"] != "USD"
                    else amount
                )
                absolute_amount = int(
                    adjusted_amount * (10 ** int(self.token0["decimals"]))
                )
                try:
                    quote = connector.get_quote(
                        self.token0, self.token1, amount=absolute_amount, network="137"
                    )
                    adjusted_quote = int(quote) / (10 ** int(self.token1["decimals"]))
                    quote_rate = adjusted_quote / adjusted_amount
                    comparison = ((quote_rate - self.base_rate) / self.base_rate) * 100
                    if abs(comparison) > 1:
                        report += f"🔴 -> {adjusted_amount} {self.token0['symbol']} = {adjusted_quote:.3f} {self.token1['symbol']}, Quote Rate: {quote_rate:.3f}, Vs Base Rate: {comparison:.3f}%\n"
                    else:
                        report += f"🟢 -> {adjusted_amount} {self.token0['symbol']} = {adjusted_quote:.3f} {self.token1['symbol']}, Quote Rate: {quote_rate:.3f}, Vs Base Rate: {comparison:.3f}%\n"
                except ValueError as e:
                    report += f"Not enough liquidity for {adjusted_amount} {self.token0['symbol']}. Error: {str(e)}\n"
        report += "Done!\n"
        return report


# Dictionary of predefined tokens
tokens = {
    "1": brla_token,
    "2": usdc_token,
    "3": brz_token_old,
    "4": brz_token,
}

def get_token_input():
    # print("Select a token:")
    print("1: BRLA Token")
    print("2: USD Coin (POS)")
    print("3: BRZ Token (old)")
    print("4: BRZ Token")
    token_choice = input("Enter the number of your choice: ")
    return tokens[token_choice]

def get_base_rate_input():
    base_rate = input("👉 Enter the base rate (or 'latest' to use the latest quote): ")
    if base_rate.lower() == 'latest':
        return 0
    else:
        return float(base_rate)
    
# Defining connector
connector = ParaswapConnector()

while True:
    # Get user input for the first token
    print("👉 Select the first token:")
    token0 = get_token_input()

    print("\n----------------------------------\n")

    # Get user input for the second token
    print("👉 Select the second token:")
    token1 = get_token_input()

    print("\n----------------------------------\n")

    # Get user input for the base rate
    base_rate = get_base_rate_input()

    print("\n----------------------------------\n")

    # Instantiate the LiquidityCalculator
    calculator = LiquidityCalculator([connector], token0, token1, base_rate)

    # Print the liquidity check
    print(calculator.check_liquidity())

    # Ask the user if they want to end the script or run another pair
    continue_choice = input("👉 Run another pair or end? (run/end): ")
    if continue_choice.lower() == 'end':
        break

# # Instantiate the ArbitrageCalculator for USD to BRL
# usd_brl_calculator = LiquidityCalculator([connector], usdc_token, brla_token, 5.02)
# print(usd_brl_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for BRL to USD
# brl_usd_calculator = LiquidityCalculator([connector], brla_token, usdc_token, 0.199203187250996)
# print(brl_usd_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for USD to BRZ (old)
# usd_brz_calculator = LiquidityCalculator([connector], usdc_token, brz_token_old)
# print(usd_brz_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for BRZ (old) to USD
# brz_usd_calculator = LiquidityCalculator([connector], brz_token_old, usdc_token)
# print(brz_usd_calculator.check_liquidity())

# Instantiate the ArbitrageCalculator for USD to BRZ (old)
# usd_brz_calculator = LiquidityCalculator([connector], usdc_token, brz_token, 5.02)
# print(usd_brz_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for BRZ (old) to USD
# brz_usd_calculator = LiquidityCalculator([connector], brz_token, usdc_token, 0.199203187250996)
# print(brz_usd_calculator.check_liquidity())
