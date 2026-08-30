import app from "./src/app.js";
import connectDB from "./src/db/db.js";
import dotenv from "dotenv";
dotenv.config();
dotenv.config({
  path: "../.env",
});
const PORT = process.env.PORT || 3000 ;

const startServer = async () => {
  try {
    await connectDB();

    app.listen(PORT, () => {
      console.log(`Server is running on http://localhost:${PORT}`);
    });
  } catch (error) {
    console.error("Failed to start server:", error.message);
    process.exit(1);
  }
};

startServer();
