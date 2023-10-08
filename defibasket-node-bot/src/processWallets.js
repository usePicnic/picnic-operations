const { fetchWalletAddresses } = require("./db.js");
const { getBalance } = require("./utils/ethersUtils.js");
const { tokensDataset } = require("./config.js");

const NETWORK_TOKEN_ADDRESS = "0x0000000000000000000000000000000000001010"; // MATIC on Polygon

async function hasNetworkTokenBalance(wallet) {
  const balance = await getBalance(wallet, NETWORK_TOKEN_ADDRESS);
  return balance > 0n;
}

async function processWallets() {
  const monitoredWallets = await fetchWalletAddresses();
  const result = [];

  for (const wallet of monitoredWallets) {
    const balances = {};

    for (const tokenAddress in tokensDataset) {
      const balance = await getBalance(wallet, tokenAddress);
      if (balance > 0n) {
        balances[tokenAddress] = {
          symbol: tokensDataset[tokenAddress].symbol,
          balance: balance.toString(),
        };
      }
    }

    if (
      Object.keys(balances).length > 0 &&
      !(await hasNetworkTokenBalance(wallet))
    ) {
      result.push({
        wallet,
        balances,
        noNetworkTokenBalance: true,
      });
    }
  }

  return result;
}

// Call the function to execute the script
processWallets()
  .then((data) => console.log(data))
  .catch((err) => console.error(err));
