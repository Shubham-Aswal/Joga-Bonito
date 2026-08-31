import asyncHandler from "../../utilities/asyncHandler.js";
import ApiError from "../../utilities/apiError.js";
import ApiResponse from "../../utilities/apiResponse.js";
import { Session } from "../models/session.models.js";
import { Performance } from "../models/performance.model.js";
import { Game } from "../models/game.models.js";
import { getAdaptiveState, submitGameScore } from "../services/adaptive.service.js";

const createSession = asyncHandler(async (req, res) => {
  const userId = req.user?._id;

  if (!userId) {
    throw new ApiError(401, "Unauthorized request");
  }

  const { gameId, difficulty: customDifficulty } = req.body;

  if (!gameId) {
    throw new ApiError(400, "Game ID is required");
  }

  const normalizedGameId = String(gameId).trim().toLowerCase();

  // Query Adaptive Engine for user's cognitive level
  const adaptiveState = await getAdaptiveState(userId);
  const initialDifficulty = customDifficulty
    ? Math.max(1, Math.min(10, Number(customDifficulty)))
    : (adaptiveState?.current_level || 1);

  const createdPerformance = await Performance.create({
    score: 0,
    accuracy: 0,
    timeTaken: 0,
    mistakes: 0,
    hintsUsed: 0,
    averageLatencyMs: 0,
  });

  const session = await Session.create({
    userId,
    gameId: normalizedGameId,
    difficulty: initialDifficulty,
    status: "in-progress",
    performance: createdPerformance._id,
  });

  res.cookie("_performance", createdPerformance._id.toString(), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });

  return res.status(201).json(
    ApiResponse.success(201, "Session created successfully", {
      _id: session._id,
      userId: session.userId,
      gameId: session.gameId,
      difficulty: session.difficulty,
      status: session.status,
      performance: createdPerformance._id,
      startedAt: session.startedAt,
      adaptive: adaptiveState,
    })
  );
});

const endSession = asyncHandler(async (req, res) => {
  const performanceId = req.cookies?._performance;

  if (!performanceId) {
    throw new ApiError(400, "No active performance session found");
  }

  const {
    score = 0,
    accuracy,
    timeTaken,
    mistakes,
    hintsUsed,
    averageLatencyMs,
  } = req.body || {};

  const performanceUpdate = {};

  if (typeof score !== "undefined") performanceUpdate.score = Number(score);
  if (typeof accuracy !== "undefined") performanceUpdate.accuracy = Number(accuracy);
  if (typeof timeTaken !== "undefined") performanceUpdate.timeTaken = Number(timeTaken);
  if (typeof mistakes !== "undefined") performanceUpdate.mistakes = Number(mistakes);
  if (typeof hintsUsed !== "undefined") performanceUpdate.hintsUsed = Number(hintsUsed);
  if (typeof averageLatencyMs !== "undefined") performanceUpdate.averageLatencyMs = Number(averageLatencyMs);

  const performanceDoc = await Performance.findByIdAndUpdate(
    performanceId,
    performanceUpdate,
    { new: true }
  );

  if (!performanceDoc) {
    throw new ApiError(404, "Performance record not found");
  }

  const session = await Session.findOneAndUpdate(
    { performance: performanceId, status: "in-progress" },
    {
      status: "completed",
      completedAt: new Date(),
    },
    { new: true }
  );

  if (!session) {
    throw new ApiError(404, "Active session record not found");
  }

  res.clearCookie("_performance", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });

  // Lookup game for domain metadata
  const game = await Game.findOne({ gameId: session.gameId });
  const cognitiveDomain = game?.cognitiveDomain || "memory";

  // Send score and metrics to standalone Adaptive Engine
  const adaptiveResult = await submitGameScore({
    userId: session.userId,
    gameType: session.gameId,
    score: performanceDoc.score,
    levelPlayed: session.difficulty,
    accuracy: performanceDoc.accuracy,
    responseTime: performanceDoc.timeTaken,
    mistakes: performanceDoc.mistakes,
    hintsUsed: performanceDoc.hintsUsed,
    sessionDuration: performanceDoc.timeTaken,
    cognitiveDomain,
  });

  return res.status(200).json(
    ApiResponse.success(200, "Session ended successfully", {
      performance: performanceDoc,
      session,
      adaptive: adaptiveResult,
    })
  );
});

const getUserAdaptiveProfile = asyncHandler(async (req, res) => {
  const userId = req.user?._id;

  if (!userId) {
    throw new ApiError(401, "Unauthorized request");
  }

  const adaptiveState = await getAdaptiveState(userId);

  return res.status(200).json(
    ApiResponse.success(200, "Adaptive profile retrieved successfully", adaptiveState)
  );
});

export { createSession, endSession, getUserAdaptiveProfile };
