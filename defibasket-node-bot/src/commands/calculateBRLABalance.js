// commands/calculateBRLABalance.js

const { SlashCommandBuilder } = require("@discordjs/builders");
const { ethers } = require("ethers");
const ERC20_ABI = require("../lib/erc20_abi.json");

const ALCHEMY_SECOND_API_KEY = process.env.ALCHEMY_SECOND_API_KEY;
const PROVIDER_URL = `https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_SECOND_API_KEY}`;

const provider = new ethers.JsonRpcProvider(PROVIDER_URL);

function toDecimals(amount, decimals) {
  return amount / BigInt(`1${"0".repeat(Number(decimals))}`);
}

async function calculateBRLABalanceForTimeframe(startBlock, endBlock) {
  // const startBlock = await provider.getBlockNumber(startDate);
  // const endBlock = await provider.getBlockNumber(endDate);

  // Fetch transfer logs for BRLA token
  const transferLogs = await provider.getLogs({
    // Replace with the BRLA token's address
    address: "0xE6A537a407488807F0bbeb0038B79004f19DDDFb",
    topics: [ethers.id("Transfer(address,address,uint256)")],
    fromBlock: startBlock,
    toBlock: endBlock,
  });

  let totalMinted = 0n;
  let totalBurned = 0n;

  for (const log of transferLogs) {
    const event = new ethers.Contract(
      log.address,
      ERC20_ABI,
      provider
    ).interface.parseLog(log);

    // If event or event.args is not defined, log the problematic objects
    if (!event || !event.args) {
      console.error("Problematic log:", log);
      console.error("Resultant event:", event);
      continue; // skip processing this log
    }

    if (event.args.from === "0x0000000000000000000000000000000000000000") {
      totalMinted = totalMinted + event.args.value;
    }

    if (event.args.to === "0x0000000000000000000000000000000000000000") {
      totalBurned = totalBurned + event.args.value;
    }
  }

  // Calculate balance
  const balance = totalMinted - totalBurned;

  return {
    minted: toDecimals(totalMinted, 18).toString(),
    burned: toDecimals(totalBurned, 18).toString(),
    balance: toDecimals(balance, 18).toString(),
  };
}

module.exports = {
  data: new SlashCommandBuilder()
    .setName("calculate")
    .setDescription("Calculate the BRLA balance for a given timeframe.")
    .addSubcommand((subcommand) =>
      subcommand
        .setName("brla_balance")
        .setDescription("Calculate the BRLA balance for the last 7 days.")
    ),
  async execute(interaction) {
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    const now = new Date();

    // const startBlock = await getBlockNumberFromTimestamp(oneWeekAgo);
    // const endBlock = await getBlockNumberFromTimestamp(now);
    const startBlock = 49107926;
    const endBlock = 49333576;

    const result = await calculateBRLABalanceForTimeframe(startBlock, endBlock);

    await interaction.reply(
      `From the last 7 days:\nMinted: ${result.minted}\nBurned: ${result.burned}\nBalance: ${result.balance}`
    );
  },
};
