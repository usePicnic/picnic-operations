require("dotenv").config({ path: __dirname + "/../.env" });

const ALCHEMY_SECOND_API_KEY = process.env.ALCHEMY_SECOND_API_KEY;
const PROVIDER_URL = `https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_SECOND_API_KEY}`;

const tokensDataset = {
  "0xE6A537a407488807F0bbeb0038B79004f19DDDFb": {
    symbol: "BRLA",
    name: "BRLA Token",
    currency: "BRL",
    decimals: 18,
  },
  "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174": {
    symbol: "USDC.e",
    name: "USD Coin (Bridged)",
    currency: "USD",
    decimals: 6,
  },
  "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359": {
    symbol: "USDC",
    name: "USD Coin (Native)",
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
  "0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6": {
    symbol: "EURe",
    name: "Monerium EUR emoney",
    currency: "EUR",
    decimals: 18,
  },
  "0xc2132D05D31c914a87C6611C10748AEb04B58e8F": {
    symbol: "USDT",
    name: "Tether USD (PoS)",
    currency: "USD",
    decimals: 6,
  },
  "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063": {
    symbol: "DAI",
    name: "Dai Stablecoin",
    currency: "USD",
    decimals: 18,
  },
};

module.exports = {
  PROVIDER_URL,
  tokensDataset,
};
