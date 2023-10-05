require("dotenv").config();
const { Client, GatewayIntentBits } = require("discord.js");
const { ethers } = require("ethers");
const fs = require("fs");
const ERC20_ABI = require("../lib/erc20_abi.json");

const DISCORD_BOT_TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.OPS_CHANNEL_ID;
const ALCHEMY_SECOND_API_KEY = process.env.ALCHEMY_SECOND_API_KEY;

const PROVIDER_URL = `https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_SECOND_API_KEY}`;
const DEFIBASKET_ADDRESS = "0xee13C86EE4eb1EC3a05E2cc3AB70576F31666b3b";
const ABI_FILE_PATH = "../lib/defi_basket_abi.json";
const BLOCKNUMBER_FILE_PATH = "blocknumber.txt";

const monitoredWallets = [
  "0x5131Ddea9ed6d2faeD4E16CC79995497A99f688E",
  // ... Add more wallet addresses as needed
];

const tokensDataset = {
  "0xE6A537a407488807F0bbeb0038B79004f19DDDFb": {
    symbol: "BRLA",
    name: "BRLA Token",
    currency: "BRL",
    decimals: 18,
  },
  "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174": {
    symbol: "USDC",
    name: "USD Coin (POS)",
    currency: "USD",
    decimals: 6,
  },
  "0x4eD141110F6EeeAbA9A1df36d8c26f684d2475Dc": {
    symbol: "BRZ",
    name: "BRZ Token",
    currency: "BRL",
    decimals: 18,
  },
  "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619": {
    symbol: "WETH",
    name: "Wrapped Ether",
    currency: "ETH",
    decimals: 18,
  },
};

const provider = new ethers.JsonRpcProvider(PROVIDER_URL);
const ABI = JSON.parse(fs.readFileSync(ABI_FILE_PATH));

const discordClient = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
  ],
});

discordClient.once("ready", () => {
  console.log("Discord bot is ready!");
});

discordClient.login(DISCORD_BOT_TOKEN);

// function sendMessageToDiscordChannel(message) {
//   const channel = discordClient.channels.cache.get(CHANNEL_ID);
//   if (channel) {
//     channel.send(message);
//   } else {
//     console.error("Channel not found!");
//   }
// }

function sendMessageToDiscordChannel(event, log, relevantData) {
  const channel = discordClient.channels.cache.get(CHANNEL_ID);
  if (!channel) {
    console.error("Channel not found!");
    return;
  }

  try {
    const embed = {
      color: 0x32a852,
      title: `Event: ${event.name}`,
      url: `https://polygonscan.com/tx/${log.transactionHash}`,
      description: "Details of the triggered event",
      fields: Object.keys(relevantData).map((key) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1), // Capitalize the key
        value:
          typeof relevantData[key] === "object"
            ? JSON.stringify(relevantData[key], null, 2)
            : relevantData[key].toString(),
        inline: true,
      })),
      timestamp: new Date(),
      footer: {
        text: "Picnic Bot",
        icon_url:
          "https://file.notion.so/f/f/97fec8e8-7050-42ce-9bb8-a2fe5900aca6/b03ca908-4da4-43be-9276-d765f5a37eb5/avatar-classic.png?id=b2f5c49e-f4cb-4d12-914c-5063770cbe61&table=block&spaceId=97fec8e8-7050-42ce-9bb8-a2fe5900aca6&expirationTimestamp=1695499200000&signature=C2OobfCzGjOgDaOQs4kjvIN5QPkpRFK6xP1FpoDKONM&downloadName=simbol-classic.png",
      },
    };

    // Send the embed object as part of the message parameters.
    channel.send({ embeds: [embed] });
  } catch (error) {
    // If there's an error building the embed, send a plain text message with the error details.
    channel.send(
      `Failed to send embed message for event: ${event.name}. Error: ${error.message}`
    );
    console.error("Error building embed:", error);
  }
}

function getLastProcessedBlockNumber() {
  if (fs.existsSync(BLOCKNUMBER_FILE_PATH)) {
    return parseInt(fs.readFileSync(BLOCKNUMBER_FILE_PATH, "utf8"));
  }
  return 47438618; // Default value
}

function setLastProcessedBlockNumber(blockNumber) {
  fs.writeFileSync(BLOCKNUMBER_FILE_PATH, blockNumber.toString());
}

async function processEvent(log) {
  // const event = contract.interface.parseLog(log);

  let event;
  let contract;

  if (log.topics[0] === ethers.utils.id("Transfer(address,address,uint256)")) {
    contract = new ethers.Contract(log.address, ERC20_ABI, provider);
    event = contract.interface.parseLog(log);
  } else {
    contract = new ethers.Contract(DEFIBASKET_ADDRESS, ABI, provider);
    event = contract.interface.parseLog(log);
  }

  if (!event) {
    console.warn(
      `Unable to parse log with transaction hash: ${log.transactionHash}`
    );
    return;
  }

  let relevantData = {};
  let tokenInfo;

  const tx = await provider.getTransaction(log.transactionHash);
  const decodedInput = contract.interface.parseTransaction({ data: tx.data });

  switch (event.name) {
    case "DEFIBASKET_CREATE":
      relevantData.from = tx.from;
      relevantData.nftId = Number(event.args.nftId);
      relevantData.wallet = event.args.wallet;
      tokenInfo = tokensDataset[decodedInput.args.inputs.tokens[0]];
      if (tokenInfo) {
        relevantData.inputToken = tokenInfo.symbol;
        relevantData.inputAmount =
          Number(decodedInput.args.inputs.amounts[0]) /
          10 ** tokenInfo.decimals;
      } else {
        console.warn(
          `Token address not found in dataset: ${decodedInput.args.inputs.tokens[0]}`
        );
      }
      break;

    case "DEFIBASKET_DEPOSIT":
      relevantData.from = tx.from;
      relevantData.nftId = Number(decodedInput.args.nftId);
      tokenInfo = tokensDataset[decodedInput.args.inputs.tokens[0]];
      if (tokenInfo) {
        relevantData.inputToken = tokenInfo.symbol;
        relevantData.inputAmount =
          Number(decodedInput.args.inputs.amounts[0]) /
          10 ** tokenInfo.decimals;
      } else {
        console.warn(
          `Token address not found in dataset: ${decodedInput.args.inputs.tokens[0]}`
        );
      }

      break;

    case "DEFIBASKET_EDIT":
      relevantData.from = tx.from;
      relevantData.nftId = Number(decodedInput.args.nftId);
      break;

    case "DEFIBASKET_WITHDRAW":
      relevantData.from = tx.from;
      relevantData.nftId = Number(decodedInput.args.nftId);
      tokenInfo = tokensDataset[decodedInput.args.outputs.tokens[0]];
      if (tokenInfo) {
        relevantData.outputToken = tokenInfo.symbol;
        relevantData.outputAmount =
          Number(event.args.outputAmounts) / 10 ** tokenInfo.decimals;
      } else {
        console.warn(
          `Token address not found in dataset: ${decodedInput.args.outputs.tokens[0]}`
        );
      }
      relevantData.outputPercentage = Number(
        decodedInput.args.outputs.amounts[0]
      );
      break;
    case "Transfer":
      if (monitoredWallets.includes(event.args.to)) {
        relevantData.from = event.args.from;
        relevantData.to = event.args.to;
        tokenInfo = tokensDataset[log.address];
        if (tokenInfo) {
          relevantData.token = tokenInfo.symbol;
          relevantData.amount =
            Number(event.args.value) / 10 ** tokenInfo.decimals;
        } else {
          console.warn(`Token address not found in dataset: ${log.address}`);
        }
      }
      break;

    default:
      console.log(`Event ${event.name} not processed.`);
      return;
  }

  console.log(`Event: ${event.name}`);
  console.log(`Relevant Data:`, relevantData);

  // sendMessageToDiscordChannel(
  //   `**Event:** ${event.name}\n**Relevant Data:** \`\`\`${JSON.stringify(
  //     relevantData
  //   )}\n[View on Polygonscan](<https://polygonscan.com/tx/${
  //     log.transactionHash
  //   }>)\`\`\``
  // );
  sendMessageToDiscordChannel(event, log, relevantData);
}

async function runBot() {
  try {
    const startingBlocknumber = getLastProcessedBlockNumber();
    const endingBlocknumber = await provider.getBlockNumber();
    // const endingBlocknumber = startingBlocknumber + 100;
    setLastProcessedBlockNumber(endingBlocknumber);

    const defiBasketLogs = await provider.getLogs({
      address: DEFIBASKET_ADDRESS,
      fromBlock: startingBlocknumber,
      toBlock: endingBlocknumber,
    });
    const transferLogs = await provider.getLogs({
      address: Object.keys(tokensDataset), // Fetch logs for all tokens in the dataset
      topics: [
        ethers.utils.id("Transfer(address,address,uint256)"), // ERC-20 Transfer event signature
        null, // Ignore the sender
        monitoredWallets.map((wallet) => ethers.utils.hexZeroPad(wallet, 32)), // List of monitored wallets padded to 32 bytes
      ],
      fromBlock: startingBlocknumber,
      toBlock: endingBlocknumber,
    });

    const allLogs = [...defiBasketLogs, ...transferLogs];

    if (allLogs.length === 0) {
      console.log("No logs found");
      return;
    }

    for (const log of allLogs) {
      await processEvent(log);
    }
  } catch (error) {
    console.error("Error in runBot:", error);
  }
}

// Run the bot every 30s
setInterval(runBot, 30_000);
