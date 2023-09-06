import os
import json
import requests
from web3 import Web3
from eth_abi.packed import encode_packed
from itertools import permutations

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
    "default_amount": 5000,
}
usdc_token = {
    "address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "symbol": "USDC",
    "name": "USD Coin (POS)",
    "currency": "USD",
    "decimals": 6,
    "default_amount": 1000,
}
brz_token_old = {
    "address": "0x491a4eB4f1FC3BfF8E1d2FC856a6A46663aD556f",
    "symbol": "BRZ (old)",
    "name": "BRZ Token",
    "currency": "BRL",
    "decimals": 4,
    "default_amount": 5000,
}
brz_token = {
    "address": "0x4eD141110F6EeeAbA9A1df36d8c26f684d2475Dc",
    "symbol": "BRZ",
    "name": "BRZ Token",
    "currency": "BRL",
    "decimals": 18,
    "default_amount": 5000,
}
weth_token = {
    "address": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    "symbol": "WETH",
    "name": "Wrapped Ether",
    "currency": "ETH",
    "decimals": 18,
    "default_amount": 0.5,
}

# make the following tokens as one object of tokens
tokens = {
    "BRLA": brla_token,
    "USDC": usdc_token,
    # "BRZ_OLD": brz_token_old,
    "BRZ": brz_token,
    "WETH": weth_token,
}

# building token pair
pairs = []
for i, token1 in enumerate(tokens.values()):
    for token2 in list(tokens.values())[i + 1 :]:
        pairs.append((token1, token2))


def display_progress_bar(iteration, total, bar_length=50):
    progress = float(iteration) / float(total)
    arrow = "=" * int(round(progress * bar_length) - 1)
    spaces = " " * (bar_length - len(arrow))

    print(f"\r[{arrow + spaces}] {int(progress * 100)}%", end="", flush=True)


def build_arbitrage_routes(tokens):
    routes = []
    for token1 in tokens.values():
        # Generate all possible routes starting and ending with token1
        other_tokens = [token for token in tokens.values() if token != token1]
        for perm in permutations(other_tokens):
            route = [token1] + list(perm) + [token1]

            # Only append routes with 4 or more tokens
            if len(route) >= 4:
                routes.append(route)

            # Generate sub-routes
            for i in range(2, len(route)):
                for j in range(len(route) - i + 1):
                    sub_route = route[j : j + i]

                    # Only append sub-routes with 4 or more tokens
                    if (
                        sub_route and len(sub_route) + 1 >= 4
                    ):  # +1 for the closing token
                        # Close the loop for the sub-route
                        sub_route.append(sub_route[0])
                        routes.append(sub_route)

    return routes


arbitrage_routes = build_arbitrage_routes(tokens)

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
            "network": kwargs.get("network", "137"),  # Default to "Mainnet"
        }
        # print(params)

        # Removing None values
        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(self.BASE_URL + endpoint, params=params)
        data = response.json()
        # print("oi", response)

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
        self.rates = self.get_base_rate()
        try:
            self.base_rate = (
                base_rate
                if base_rate != 0
                else float(self.rates[self.token1["currency"]])
            )
        except KeyError:
            print(f"Invalid base rate: {base_rate}")
            raise
        print(f"Starting Liq Calc for {self.token0['symbol']}-{self.token1['symbol']}")
        print(f"Base Rate: {self.base_rate:.8f}")

    def get_base_rate(self):
        base_currency = self.token0["currency"]
        response = requests.get(
            f"https://api.coinbase.com/v2/exchange-rates?currency={base_currency}"
        )
        data = response.json()
        return data["data"]["rates"]

    def check_liquidity(self):
        report = ""
        for connector in self.connectors:
            report += f"Checking liquidity for connector: {connector.get_name()}\n"
            self.usd_rate = float(self.rates["USD"])
            for amount in self.amounts:
                adjusted_amount = amount / self.usd_rate
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
                        report += f"🔴 -> {adjusted_amount} {self.token0['symbol']} = {adjusted_quote:.6f} {self.token1['symbol']}, Quote Rate: {quote_rate:.3f}, Vs Base Rate: {comparison:.3f}%\n"
                    else:
                        report += f"🟢 -> {adjusted_amount} {self.token0['symbol']} = {adjusted_quote:.3f} {self.token1['symbol']}, Quote Rate: {quote_rate:.3f}, Vs Base Rate: {comparison:.3f}%\n"
                except ValueError as e:
                    report += f"Not enough liquidity for {adjusted_amount} {self.token0['symbol']}. Error: {str(e)}\n"
        report += "Done!\n"
        return report


# Defining connector
connector = ParaswapConnector()

# Initialize the total number of routes to check
total_routes = len(arbitrage_routes)

# Initialize the iteration count
iteration = 0

# Initialize a list to store results
results = []

# ANSI escape codes for colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Print the header
print(f"{YELLOW}==========================================")
print(f"{GREEN}  _____                     _               ")
print(f"{GREEN} |_   _|                   (_)              ")
print(f"{GREEN}   | |  _ __ __ _ _ __ ___  _ _ __   __ _  ")
print(f"{GREEN}   | | | '__/ _` | '_ ` _ \\| | '_ \\ / _` | ")
print(f"{GREEN}  _| |_| | | (_| | | | | | | | | | | (_| | ")
print(f"{GREEN} |_____|_|  \\__,_|_| |_| |_|_|_| |_|\\__, | ")
print(f"{GREEN}                                     __/ | ")
print(f"{GREEN}                                    |___/  ")
print(f"{YELLOW}=========================================={RESET}\n")
print(f"{RED}Checking arbitrage opportunities...{RESET}\n")

# # For each route, calculate the arbitrage opportunity
# for route in arbitrage_routes:
#     iteration += 1
#     token0 = route[0]
#     initial_amount = token0["default_amount"]  # Initial amount for token1
#     output_amount = 0  # Output amount for the route after execution
#     # display_progress_bar(iteration, total_routes)
#     for i in range(len(route) - 1):
#         token_in = route[i]
#         token_out = route[i + 1]
#         # Get the quote for the route
#         if output_amount != 0:
#             try:
#                 # print("Checking liquidity for", token_in["symbol"], token_out["symbol"])
#                 output_amount = connector.get_quote(token_in, token_out, output_amount)
#                 print(output_amount)
#             except ValueError:
#                 # print(f"Not enough liquidity for {output_amount} {token_in['symbol']}")
#                 output_amount = 0
#                 break
#         else:
#             decimals_initial_amount = int(
#                 initial_amount * (10 ** int(token_in["decimals"]))
#             )
#             try:
#                 # print("Checking liquidity for", token_in["symbol"], token_out["symbol"])
#                 output_amount = connector.get_quote(
#                     token_in, token_out, decimals_initial_amount
#                 )
#                 print(output_amount)
#             except ValueError:
#                 # print(f"Not enough liquidity for {initial_amount} {token_in['symbol']}")
#                 break

#     # Calculate the arbitrage opportunity
#     # print("initial_amount", initial_amount)
#     adjusted_output_amount = float(output_amount) * (10 ** (-token0["decimals"]))
#     # print("output_amount", adjusted_output_amount)
#     arbitrage_opportunity = (
#         (adjusted_output_amount - initial_amount) / initial_amount * 100
#     )

#     route_str = ""
#     for token in route:
#         route_str += token["symbol"] + "-"
#     # print(route_str)
#     # Print the results
#     # Store the results instead of printing them immediately
#     if arbitrage_opportunity > 0:
#         result = (
#             f"🔥🔥🔥 Arbitrage opportunity for {token0['symbol']}: {arbitrage_opportunity}%",
#             f"Route: {route_str}",
#             f"Input amount: {initial_amount}",
#             f"Output amount: {adjusted_output_amount}",
#         )
#     else:
#         result = (
#             f"No arbitrage opportunity for route {route_str}: {arbitrage_opportunity}%"
#         )

#     results.append(result)

# print("\nDone!")

def get_token_input():
    # print("Select a token:")
    print("BRLA: BRLA Token")
    print("USDC: USD Coin (POS)")
    # print("BRZ_OLD: BRZ Token (old)")
    print("BRZ: BRZ Token")
    print("WETH: Wrapped Ether")
    token_choice = input("Enter the number of your choice: ")
    return tokens[token_choice]


def get_base_rate_input():
    base_rate = input("👉 Enter the base rate (or 'latest' to use the latest quote): ")
    if base_rate.lower() == "latest":
        return 0
    else:
        return float(base_rate)


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
    if continue_choice.lower() == "end":
        break

# # Instantiate the ArbitrageCalculator for USD to BRL
# usd_brl_calculator = LiquidityCalculator([connector], usdc_token, brla_token)
# print(usd_brl_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for BRL to USD
# brl_usd_calculator = LiquidityCalculator([connector], brla_token, usdc_token)
# print(brl_usd_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for USD to BRZ (old)
# usd_brz_calculator = LiquidityCalculator([connector], usdc_token, brz_token_old)
# print(usd_brz_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for BRZ (old) to USD
# brz_usd_calculator = LiquidityCalculator([connector], brz_token_old, usdc_token)
# print(brz_usd_calculator.check_liquidity())

# # # Instantiate the ArbitrageCalculator for USD to BRZ (old)
# usd_brz_calculator = LiquidityCalculator([connector], usdc_token, brz_token)
# print(usd_brz_calculator.check_liquidity())

# # Instantiate the ArbitrageCalculator for BRZ (old) to USD
# brz_usd_calculator = LiquidityCalculator([connector], brz_token, usdc_token)
# print(brz_usd_calculator.check_liquidity())
