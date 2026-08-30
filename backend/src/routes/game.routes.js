import { Router } from "express";
import { getAllGames, getGameById } from "../controllers/game.controllers.js";

const router = Router();

router.get("/", getAllGames);
router.get("/:id", getGameById);

export default router;
