const { ethers } = require("ethers");
const ERC20_ABI = require("../lib/erc20_abi.json");
const { PROVIDER_URL } = require("../config");
const provider = new ethers.JsonRpcProvider(PROVIDER_URL);

async function getBalance(wallet, tokenAddress) {
  const contract = new ethers.Contract(tokenAddress, ERC20_ABI, provider);
  return await contract.balanceOf(wallet);
}

module.exports = {
  getBalance,
};
