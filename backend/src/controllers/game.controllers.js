import mongoose from "mongoose";
import { Game } from "../models/game.models.js";
import asyncHandler from "../../utilities/asyncHandler.js";
import ApiError from "../../utilities/apiError.js";
import ApiResponse from "../../utilities/apiResponse.js";

/**
 * @desc    Get all available cognitive training games
 * @route   GET /api/games
 * @access  Public
 */
export const getAllGames = asyncHandler(async (req, res) => {
  const { domain, cognitiveDomain, isActive } = req.query;

  const filter = {
    isActive: isActive !== undefined ? isActive === "true" : true,
  };

  const targetDomain = domain || cognitiveDomain;
  if (targetDomain) {
    filter.cognitiveDomain = targetDomain.toLowerCase().trim();
  }

  const games = await Game.find(filter).sort({ createdAt: -1 });

  return res.status(200).json({
    success: true,
    count: games.length,
    data: games,
    message: "Games retrieved successfully",
  });
});

/**
 * @desc    Get a specific game by gameId or MongoDB _id
 * @route   GET /api/games/:id
 * @access  Public
 */
export const getGameById = asyncHandler(async (req, res) => {
  const { id } = req.params;

  if (!id) {
    throw new ApiError(400, "Game ID is required");
  }

  const normalizedId = id.trim();
  const isObjectId = mongoose.isValidObjectId(normalizedId);

  const game = await Game.findOne(
    isObjectId
      ? { $or: [{ _id: normalizedId }, { gameId: normalizedId.toLowerCase() }] }
      : { gameId: normalizedId.toLowerCase() }
  );

  if (!game) {
    throw new ApiError(404, `Game with ID '${id}' not found`);
  }

  return res.status(200).json({
    success: true,
    data: game,
    message: "Game retrieved successfully",
  });
});
