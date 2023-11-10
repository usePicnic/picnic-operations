import requests


async def get_portfolio_data():
    """
    Fetch portfolio data from the Picnic Investments API.

    The function sends a POST request to the API with a specific set of NFT IDs,
    receives the portfolio data associated with these NFTs, sorts them by APY in
    descending order, and formats the data into a string. Portfolios with names
    starting with "Easy_CT" are excluded from the result.

    Returns:
        str: A string of sorted portfolio data, or an error message if the API request fails.
    """

    # The headers for the API request
    headers = {
        "content-type": "application/json",
    }

    # The data to be sent with the API request
    data = {
        "networkName": "polygon",
        "nftIds": [
            678,  # EasyCryptoBTC
            679,  # EasyCryptoETH
            680,  # EasyPassiveUSD
            862,  # EasyPassiveEUR
            804,  # EasyPassiveMATIC
            807,  # EasyPassiveBRL
            932,  # EasyCryptoMatic
            940,  # EasyPassiveETH
            941,  # EasyCryptoAave
            942,  # EasyCryptoUni
            943,  # EasyCryptoLido
            982,  # EasyCryptoPAXG
            998,  # EasyPassiveUSDDavos
            1220,  # EasyCryptoGRT
            1221,  # EasyCryptoLINK
            1323,  # Alt Power @cassio.defi
            1325,  # Classic Hodler @cassio.defi
            1326,  # Just Stable @cassio.defi
            1327,  # Feel the Burn @cassio.defi
            1884,  # Avax
            1885,  # Shiba Inu
            1886,  # Ocean Protocol
            1887,  # ApeCoin
            1881,  # LP MATIC-USDC
            1882,  # LP MATIC-ETH
            1883,  # LP ETH-USDC
            1890,  # LP WBTC-USDC
            2044,  # Render Token (RNDR)
            2045,  # Decentraland (MANA)
            2046,  # Curve DAO Token (CRV)
            2047,  # Mask Network (MASK)
            2048,  # The Sandbox (SAND)
        ],
        "perPage": 999,
    }

    # Make the API request
    response = requests.post(
        "https://picnicinvestimentos.com/api/get-portfolios", headers=headers, json=data
    )

    # Make sure the request was successful
    if response.status_code == 200:
        # Parse the response as JSON
        portfolios = response.json()["portfolios"]

        # Sort the portfolios by APY in descending order
        portfolios = sorted(portfolios, key=lambda p: p["apy"], reverse=True)

        # Format the portfolios and return them as a string
        portfolios_str = "\n".join(
            [
                f"""    > `name`: {p["name"]}, `nftId`: {p["nftId"]}, `apy`: {p["apy"]:.2f}%"""
                for p in portfolios
                if not p["name"].startswith("Easy_CT")
            ]
        )

        return portfolios_str
    else:
        return "Failed to fetch portfolio data"
