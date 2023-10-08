require("dotenv").config({ path: __dirname + "/../.env" });

const { MongoClient } = require("mongodb");
const MONGO_URL = process.env.MONGO_URL;
const uri = MONGO_URL;
const dbName = "defibasket-common";
const collectionName = "users";

async function fetchWalletAddresses() {
  const client = new MongoClient(uri, { useUnifiedTopology: true });

  try {
    await client.connect();
    const database = client.db(dbName);
    const collection = database.collection(collectionName);

    const addresses = await collection
      .find()
      .map((doc) => doc.addresses.map((addrObj) => addrObj.address))
      .toArray();

    return [].concat(...addresses);
  } catch (error) {
    console.error("Error fetching wallet addresses:", error);
  } finally {
    await client.close();
  }
}

module.exports = {
  fetchWalletAddresses,
};
