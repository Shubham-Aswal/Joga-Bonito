import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import authRoutes from "./routes/auth.routes.js";
import sessionRoutes from "./routes/session.routes.js";
import gameRoutes from "./routes/game.routes.js";
import cookieParser from "cookie-parser";
dotenv.config();

const app = express();
app.use(cookieParser())

// A static origin string (or even a fixed list of ports) breaks the moment
// Vite picks a different port than usual — e.g. because 5173 was already
// taken, it silently falls back to 5174, 5175, etc. In development, allow
// any localhost/127.0.0.1 origin regardless of port instead of chasing
// whichever one the dev server happened to land on.
const explicitAllowedOrigins = [process.env.FRONTEND_URL].filter(Boolean);
const localDevOriginPattern = /^https?:\/\/(localhost|127\.0\.0\.1):\d+$/;

app.use(cors({
    origin: "https://joga-bonito-cvkz-nir0nz22i-joga-banito.vercel.app",
    credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get("/", (req, res) => {
  res.status(200).json({
    message: "Joga-Bonito API is running",
  });
});

app.get("/health", (req, res) => {
  res.status(200).json({
    status: "ok",
    service: "joga-bonito-backend",
  });
});

app.use("/api/auth", authRoutes);
app.use("/api/sessions", sessionRoutes);
app.use("/api/games", gameRoutes);

app.use((err, req, res, next) => {
  const statusCode = err.statusCode || 500;
  const message = err.message || "Something went wrong";

  res.status(statusCode).json({
    success: false,
    statusCode,
    message,
    errors: err.errors || [],
  });
});

export default app;
