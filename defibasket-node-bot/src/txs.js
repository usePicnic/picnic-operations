require("dotenv").config({ path: __dirname + "/../.env" });

const fs = require("fs");
const path = require("node:path");
const { ethers } = require("ethers");
const { Client, GatewayIntentBits, Collection, Events } = require("discord.js");
const { REST, Routes } = require("discord.js");
const { MongoClient } = require("mongodb");

const ERC20_ABI = require("./lib/erc20_abi.json");
const { tokensDataset } = require("./config");

const DISCORD_BOT_TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.OPS_CHANNEL_ID;
const ALCHEMY_SECOND_API_KEY = process.env.ALCHEMY_SECOND_API_KEY;
const MONGO_URL = process.env.MONGO_URL;

const PROVIDER_URL = `https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_SECOND_API_KEY}`;
const DEFIBASKET_ADDRESS = "0xee13C86EE4eb1EC3a05E2cc3AB70576F31666b3b";
const ABI_FILE_PATH = "./lib/defi_basket_abi.json";
const BLOCKNUMBER_FILE_PATH = "blocknumber.txt";

const uri = MONGO_URL;


async function fetchUserAddresses() {
  const client = new MongoClient(uri, { useUnifiedTopology: true });
  const dbName = "defibasket-common";
const collectionName = "users";

  try {
    await client.connect();
    const database = client.db(dbName);
    const collection = database.collection(collectionName);

    const addresses = await collection
      .find()
      .map((doc) => doc.addresses.map((addrObj) => addrObj.address))
      .toArray();

    // Flatten the array of arrays to get a single array of addresses
    const flattenedAddresses = [].concat(...addresses);

    return flattenedAddresses;

    // // Export addresses to a .txt file
    // fs.writeFileSync("addresses.txt", flattenedAddresses.join("\n"), "utf-8");
    // console.log("Wallet addresses exported successfully to addresses.txt!");
  } catch (error) {
    console.error("Error fetching wallet addresses:", error);
  } finally {
    await client.close();
  }
}

async function fetchSmartWalletAddresses() {
  const client = new MongoClient(uri, { useUnifiedTopology: true });
  const dbName = "defibasket-common";
  const collectionName = "smartAccounts";

  try {
    await client.connect();
    const database = client.db(dbName);
    const collection = database.collection(collectionName);

    const addresses = await collection
      .find()
      .map((doc) => doc.address)
      .toArray();

    // Flatten the array of arrays to get a single array of addresses
    const flattenedAddresses = [].concat(...addresses);

    return flattenedAddresses;

    // // Export addresses to a .txt file
    // fs.writeFileSync("addresses.txt", flattenedAddresses.join("\n"), "utf-8");
    // console.log("Wallet addresses exported successfully to addresses.txt!");
  } catch (error) {
    console.error("Error fetching wallet addresses:", error);
  } finally {
    await client.close();
  }
}

// let monitoredWallets = [];
// generate set for monitored wallets
let monitoredWallets = new Set();

async function initializeMonitoredWallets() {
  const userWallets = await fetchUserAddresses();
  const smartWallets = await fetchSmartWalletAddresses();

  userWallets.forEach((wallet) => monitoredWallets.add(wallet.toLowerCase()));
  smartWallets.forEach((wallet) => monitoredWallets.add(wallet.toLowerCase()));
}

initializeMonitoredWallets();

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

const GUILD_ID = "854417722703216692";
const CLIENT_ID = "1116073397907111946";

discordClient.once("ready", () => {
  console.log("Discord bot is ready!");
});

discordClient.login(DISCORD_BOT_TOKEN);

discordClient.commands = new Collection();

const commandsPath = path.join(__dirname, "commands");
const commandFiles = fs
  .readdirSync(commandsPath)
  .filter((file) => file.endsWith(".js"));

for (const file of commandFiles) {
  const filePath = path.join(commandsPath, file);
  const command = require(filePath);
  // Set a new item in the Collection with the key as the command name and the value as the exported module
  if ("data" in command && "execute" in command) {
    console.log("Setting command:", command.data.name);
    discordClient.commands.set(command.data.name, command);
  } else {
    console.log(
      `[WARNING] The command at ${filePath} is missing a required "data" or "execute" property.`
    );
  }
}

// Construct and prepare an instance of the REST module
const rest = new REST().setToken(DISCORD_BOT_TOKEN);
const commands = [];
discordClient.commands.forEach((command) => {
  commands.push(command.data.toJSON());
});

// and deploy your commands!
(async () => {
  try {
    console.log(
      `Started refreshing ${commands.length} application (/) commands.`
    );

    // The put method is used to fully refresh all commands in the guild with the current set
    const data = await rest.put(
      Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID),
      { body: commands }
    );

    console.log(
      `Successfully reloaded ${data.length} application (/) commands.`
    );
  } catch (error) {
    // And of course, make sure you catch and log any errors!
    console.error(error);
  }
})();

discordClient.on(Events.InteractionCreate, async (interaction) => {
  if (!interaction.isChatInputCommand()) return;

  const command = interaction.client.commands.get(interaction.commandName);

  if (!command) {
    console.error(`No command matching ${interaction.commandName} was found.`);
    return;
  }

  try {
    await command.execute(interaction);
  } catch (error) {
    console.error(error);
    if (interaction.replied || interaction.deferred) {
      await interaction.followUp({
        content: "There was an error while executing this command!",
        ephemeral: true,
      });
    } else {
      await interaction.reply({
        content: "There was an error while executing this command!",
        ephemeral: true,
      });
    }
  }
});

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

  if (log.address.toLowerCase() === DEFIBASKET_ADDRESS.toLowerCase()) {
    contract = new ethers.Contract(DEFIBASKET_ADDRESS, ABI, provider);
    event = contract.interface.parseLog(log);
    // if event is a transfer, end the function execution.
    if (event.name === "Transfer") {
      return false;
    }
  } else {
    contract = new ethers.Contract(log.address, ERC20_ABI, provider);
    event = contract.interface.parseLog(log);
  }

  if (!event) {
    console.warn(
      `Unable to parse log with transaction hash: ${log.transactionHash}`
    );
    return false;
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
      if (monitoredWallets.has(event.args.to.toLowerCase())) {
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
  return true;
}

async function runBot() {
  try {
    const startingBlocknumber = getLastProcessedBlockNumber();
    const endingBlocknumber = (await provider.getBlockNumber()) - 5;
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
        ethers.id("Transfer(address,address,uint256)"), // ERC-20 Transfer event signature
        null, // Ignore the sender
        [...monitoredWallets].map((wallet) => ethers.zeroPadValue(wallet, 32)), // List of monitored wallets padded to 32 bytes
      ],
      fromBlock: startingBlocknumber,
      toBlock: endingBlocknumber,
    });

    // const processedTxHashes = new Set();
    if (defiBasketLogs.length === 0 && transferLogs.length === 0) {
      console.log("No logs found");
    } else {
      console.log("Raw defiBasketLogs:", defiBasketLogs);
      console.log("Raw transferLogs:", transferLogs);
    }

    // First, process the defiBasketLogs
    for (const log of defiBasketLogs) {
      // if (!processedTxHashes.has(log.transactionHash)) {
      await processEvent(log);
      // if (eventProcessed) {
      //   processedTxHashes.add(log.transactionHash);
      // }
      // }
    }

    // Then, process the transferLogs, skipping those with transaction hashes
    // that have already been processed
    for (const log of transferLogs) {
      // if (!processedTxHashes.has(log.transactionHash)) {
      await processEvent(log);
      // if (eventProcessed) {
      // processedTxHashes.add(log.transactionHash);
      // }
      // }
    }
  } catch (error) {
    console.error("Error in runBot:", error);
  }
}

// Run the bot every 30s
setInterval(runBot, 30_000);
