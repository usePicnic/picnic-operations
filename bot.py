import os
import json
import asyncio
import discord
import requests
import locale
import pytz
import psutil
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from discord.ext import tasks, commands
from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
from get_portfolios_data import get_portfolio_data

# from quoter import LiquidityCalculator, ParaswapConnector

# Load environment variables
load_dotenv()

# Discord and Tesults tokens
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TESULTS_TOKEN = os.getenv("TESULTS_TOKEN")

# Channel ID for the Discord bot
OPS_CHANNEL_ID = int(os.getenv("OPS_CHANNEL_ID"))

# Contract addresses for DeFi Basket and gas station
CONTRACT_ADDRESS = "0xee13C86EE4eb1EC3a05E2cc3AB70576F31666b3b"  # DeFi Basket
GAS_STATION_ADDRESS = "0x6d7cFBDeb7398c00b80C5653bAFEa6dDcfA9f05d"

# URL for Alchemy API
ALCHEMY_URL = f'https://polygon-mainnet.g.alchemy.com/v2/{os.getenv("ALCHEMY_API_KEY")}'

# Event mappings
EVENT_MAPPING = {
    "Approval": "Approval",
    "ApprovalForAll": "Approval for all",
    "DEFIBASKET_CREATE": "Create DEFIBASKET",
    "DEFIBASKET_DEPOSIT": "Deposit DEFIBASKET",
    "DEFIBASKET_EDIT": "Edit DEFIBASKET",
    "DEFIBASKET_WITHDRAW": "Withdraw DEFIBASKET",
    "OwnershipTransferred": "Ownership transferred",
    "Transfer": "Transfer",
}

# Set the locale to en_US
locale.setlocale(locale.LC_ALL, "en_US")

# Load contract ABI from local file
with open("lib/defi_basket_abi.json") as f:
    CONTRACT_ABI = json.load(f)

# Set up web3 and the contract
web3 = AsyncWeb3(AsyncHTTPProvider(ALCHEMY_URL))
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Discord bot intents
intents = discord.Intents.default()
intents.message_content = True

# Discord bot
bot = commands.Bot(command_prefix="$", intents=intents)

###
# Functions, event handlers, and loops
###


def check_battery():
    """
    Check the current battery status of the machine.

    Returns:
        str: A string indicating the battery percentage and whether it's currently charging.
    """

    battery = psutil.sensors_battery()
    if battery is None:
        return "No battery is installed."
    plugged = battery.power_plugged
    percent = battery.percent
    if plugged == False:
        plugged = "Not Plugged In"
    else:
        plugged = "Plugged In"
    return f"{percent}% | {plugged}"


async def handle_event(event):
    """
    Handles a new event from the Ethereum network.

    Args:
        event: The event data.
    """

    message = f"""
**:zap: PICNIC - Transaction tracker :zap:**

A new **{event.event_name}** transaction has been detected.

:small_orange_diamond: **Network**: Polygon
:small_blue_diamond: **Address**: `0x{event['address'].hex()}`
:small_orange_diamond: **Hash**: `0x{event['transactionHash'].hex()}`
:small_blue_diamond: **Link**: [Verifique a transação aqui] (https://polygonscan.com/tx/0x{event['transactionHash'].hex()})
:small_orange_diamond: **Event header**: {event['event']}({', '.join([f"{k}: {v}" for k, v in event['args'].items()])})
"""
    channel = bot.get_channel(OPS_CHANNEL_ID)
    await channel.send(message)


async def log_loop(event_filter, poll_interval):
    """
    Logs new Ethereum events in a loop.

    Args:
        event_filter: The filter used to catch new events.
        poll_interval (int): The time to wait between each check for new events, in seconds.
    """

    while True:
        try:
            print("Checking for new events...")
            for event in await event_filter.get_new_entries():
                await handle_event(event)
        except Exception as e:
            print(f"Error occurred in log_loop: {e}")
        await asyncio.sleep(poll_interval)


async def get_test_results():
    """
    Get the test results from Tesults.

    Returns:
        tuple: A tuple containing lists of passed and failed tests.
    """

    url = "https://www.tesults.com/api/results?target=1658326264884"
    headers = {"Authorization": f"Bearer {TESULTS_TOKEN}"}

    # Make the API request
    response = requests.get(url, headers=headers)
    # Make sure the request was successful

    if response.status_code == 200:
        SUITES = [
            "Featured portfolio withdraw (prod)",
            "Clone featured portfolios - prod",
        ]
        total_pass = []
        total_fail = []

        # Parse the response as JSON
        results = response.json()["data"]["results"]["runs"]

        for result in results:
            for test in result["cases"]:
                if test["suite"] in SUITES:
                    if test["result"] == "pass":
                        total_pass.append(test["name"])
                    else:
                        total_fail.append(test["name"])

        return total_pass, total_fail
    else:
        print(f"Error occurred: code {response.status_code}")


async def get_balance():
    """
    Get the balance of the gas station.

    Returns:
        float: The balance of the gas station in ether.
    """

    balance = await web3.eth.get_balance(GAS_STATION_ADDRESS)
    return Web3.from_wei(balance, "ether")


def split_message(content, limit=2000):
    """
    Split a message into chunks to respect Discord's character limit.

    Args:
        content (str): The message content.
        limit (int, optional): The maximum length for each chunk. Defaults to 2000.

    Returns:
        list: A list of message chunks.
    """

    lines = content.split("\n")
    messages = []
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 2 > limit:  # adding 2 for newline character
            messages.append(chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk:
        messages.append(chunk)
    return messages


async def report_body(report_title, type="std"):
    """
    Generate the body of a report.

    Args:
        report_title (str): The title of the report.
        type (str, optional): The type of report ("std" or "full"). Defaults to "std".

    Returns:
        tuple: A tuple containing the report body and any extended content.
    """

    # Get portfolios data string
    portfolio_str = await get_portfolio_data()

    (
        total_pass,
        total_fail,
    ) = await get_test_results()  # Call the new function to get test results

    # Make the API request
    response = requests.get("https://dev.usepicnic.com/api/get-easy-metrics")
    data = response.json()

    # Retrieve the desired metrics
    easy_users = data["metrics"]["easyUsers"]
    easy_account_tvl = data["metrics"]["easyAccountTvl"]
    easy_investments_tvl = data["metrics"]["easyInvestmentsTvl"]
    addresses_with_balance_or_portfolio = data["metrics"][
        "numberOfAddressesWithBalanceOrPortfolio"
    ]
    portfolios = data["metrics"]["portfoliosByNftId"]

    # Calculate total tvl
    total_tvl = easy_account_tvl + easy_investments_tvl

    # Sort the portfolios by 'totalValue' in descending order
    sorted_portfolios = dict(
        sorted(portfolios.items(), key=lambda item: item[1]["totalValue"], reverse=True)
    )

    # Create a string with the sorted portfolios information
    portfolio_values_str = ""

    for nft_id, portfolio in sorted_portfolios.items():
        # Calculate the portfolio's percentage of the total tvl
        portfolio_percentage = (portfolio["totalValue"] / total_tvl) * 100
        portfolio_values_str += f'> `name`: {portfolio.get("name", "N/A")}, `Total number`: {portfolio.get("totalNumber", 0)}, `Total value`: {locale.currency(portfolio.get("totalValue", 0), grouping=True)}, `Pct`: {portfolio_percentage:.2f}%\n'

    # Get and format balance to two decimal places for readability
    balance = await get_balance()
    formatted_balance = "{:.2f}".format(balance)
    report_str = f"""
    > **:bar_chart: PICNIC BRASIL - {report_title} :bar_chart:**
    > 
    > **gas station balance**
    > {formatted_balance} MATIC
    > **accounts created** 
    > {easy_users}
    > **users** 
    > {addresses_with_balance_or_portfolio}
    > **checking account tvl**
    > {locale.currency(easy_account_tvl, grouping=True)}
    > **investments tvl**
    > {locale.currency(easy_investments_tvl, grouping=True)}
    > **total tvl**
    > {locale.currency(total_tvl, grouping=True)}
    > **avg ticket**
    > {locale.currency(total_tvl / addresses_with_balance_or_portfolio, grouping=True)}
    > **baskets tests**
    > {len(total_pass)} successes, {len(total_fail)} fails
    {f'> failure list: {total_fail}' if len(total_fail) > 0 else ''}
    """
    report_extended_str = ""
    if report_title == "Daily Morning Report" or type == "full":
        report_extended_str = f"""
    > 
    > **portfolios apy**
    {portfolio_str}
    > 
    > **portfolios values**
    {portfolio_values_str}
    """
    return report_str, report_extended_str


@bot.event
async def on_ready():
    """
    Event handler for when the bot is ready.
    """

    print(f"We have logged in as {bot.user}")
    daily_report.start()
    check_balance_and_notify.start()
    tasks = []

    print("Contract events: ", contract.events)
    for event in contract.events:
        event_filter = await contract.events[event.event_name].create_filter(
            # fromBlock="latest"
            fromBlock=46827233
        )
        # print(f"Created filter for {event.event_name}")
        tasks.append(log_loop(event_filter, 2))
    try:
        await asyncio.gather(*tasks)  # Change this line
    except Exception as e:
        print(f"Error occurred: {e}")


@bot.event
async def on_message(message):
    """
    Event handler for new messages.

    Args:
        message: The message data.
    """

    # If the message is from the bot itself, ignore
    if message.author == bot.user:
        return

    # If the message is a direct message to the bot or the bot is mentioned
    if isinstance(message.channel, discord.DMChannel) or bot.user in message.mentions:
        if message.content:
            await message.channel.send(
                f"""Hi there! I'm the Picnic Bot and I'm quite dumb at the moment. This is the only message I can send."""
            )
    await bot.process_commands(message)


@bot.command()
async def report(ctx, report_type=""):
    """
    Bot command to generate a report.

    Args:
        ctx: The command context.
        report_type (str, optional): The type of report ("std" or "full"). Defaults to "".
    """

    try:
        report_str, report_extended_str = await report_body("Report", type=report_type)
        chunks = split_message(report_str)
        for chunk in chunks:
            await ctx.send(chunk)
        if report_type == "full":
            chunks_ext = split_message(report_extended_str)
            for chunk in chunks_ext:
                await ctx.send(chunk)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


@tasks.loop(minutes=1)
async def daily_report():
    """
    Task loop to generate daily reports.
    """

    now = datetime.now(pytz.timezone("America/Sao_Paulo"))

    if now.hour in [6, 18] and now.minute == 00:  # 6:00am and 6:00pm BRT
        # if now.hour in [6, 18] and now.minute == 21:  # 6:00am and 6:00pm BRT
        # Define report title based on the time
        report_title = (
            "Daily Morning Report" if now.hour == 6 else "Daily Afternoon Report"
        )
        report_str, report_extended_str = await report_body(report_title, type="full")
        channel = bot.get_channel(OPS_CHANNEL_ID)
        chunks = split_message(report_str)
        for chunk in chunks:
            # print("test", len(chunk))
            await channel.send(chunk)
        chunks_ext = split_message(report_extended_str)
        # x = 1
        for chunk in chunks_ext:
            # print(x, len(chunk))
            # x += 1
            await channel.send(chunk)


@tasks.loop(minutes=5)
async def check_balance_and_notify():
    """
    Task loop to check the balance of the gas station and notify if it's too low.
    """

    channel = bot.get_channel(OPS_CHANNEL_ID)
    balance = await get_balance()
    low_balance = balance < 20
    if low_balance:
        await channel.send(
            f"""**:rotating_light: GAS STATION**: <@&889558855623782462>, the balance of our gas station wallet is too low: {balance} MATIC"""
        )

    # Check battery status
    battery_status = check_battery()
    if "Not Plugged In" in battery_status or int(battery_status.split("%")[0]) < 20:
        await channel.send(
            f"""**:rotating_light: SERVER POWER**: <@&889558855623782462>, the server power status is critical: {battery_status}"""
        )


def main():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
