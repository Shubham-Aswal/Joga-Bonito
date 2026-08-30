import mongoose from "mongoose";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import { Game } from "../models/game.models.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Support .env in backend directory and project root
dotenv.config({ path: path.resolve(__dirname, "../../.env") });
dotenv.config({ path: path.resolve(__dirname, "../../../.env") });
dotenv.config();

export const sampleGames = [
  {
    gameId: "memory-match",
    name: "Memory Match",
    cognitiveDomain: "memory",
    description:
      "Flip cards and find matching pairs to stimulate visual short-term recall and pattern recognition.",
    avatar:
      "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60",
    defaultDifficulty: 1,
    isActive: true,
  },
  {
    gameId: "attention-flow",
    name: "Attention Challenge",
    cognitiveDomain: "attention",
    description:
      "Track moving targets amidst color distractions to improve selective attention and reaction speed.",
    avatar:
      "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=500&auto=format&fit=crop&q=60",
    defaultDifficulty: 1,
    isActive: true,
  },
  {
    gameId: "routine-order",
    name: "Daily Routine Sequencer",
    cognitiveDomain: "executive",
    description:
      "Sequence daily life steps in chronological order to strengthen executive planning and decision-making.",
    avatar:
      "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?w=500&auto=format&fit=crop&q=60",
    defaultDifficulty: 1,
    isActive: true,
  },
];

export const seedGames = async () => {
  const mongoURI =
    process.env.MONGO_URI || "mongodb://localhost:27017/cognitive-training";

  try {
    console.log("Connecting to MongoDB for seeding...");
    await mongoose.connect(mongoURI);
    console.log("Connected to MongoDB.");

    for (const gameData of sampleGames) {
      await Game.findOneAndUpdate(
        { gameId: gameData.gameId },
        { $set: gameData },
        { upsert: true, new: true, setDefaultsOnInsert: true }
      );
      console.log(`✓ Seeded game: [${gameData.cognitiveDomain}] ${gameData.name} (${gameData.gameId})`);
    }

    console.log("All sample games seeded successfully.");
  } catch (error) {
    console.error("Error seeding games:", error.message);
    process.exit(1);
  } finally {
    await mongoose.disconnect();
    console.log("MongoDB connection closed.");
  }
};

// Execute if run directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  seedGames();
}
