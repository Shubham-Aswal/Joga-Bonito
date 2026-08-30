import mongoose from 'mongoose';

const gameSchema = new mongoose.Schema(
  {
    gameId: {
      type: String,
      required: [true, 'Game ID is required'],
      lowercase: true,
      trim: true, // e.g., "memory-match", "market-basket", "routine-order"
    },
    avatar : {
      type : URL,
      url : [undefined,""],
      default : ""
    },
    name: {
      type: String,
      required: [true, 'Game name is required'],
      trim: true,
    },
    cognitiveDomain: {
      type: String,
      required: [true, 'Cognitive domain is required'],
      enum: ['memory', 'attention', 'orientation', 'motor', 'executive'],
      lowercase: true,
    },
    description: {
      type: String,
      default: '',
      trim: true,
    },
    defaultDifficulty: {
      type: Number,
      default: 1,
      min: 1,
      max: 5,
    },
    isActive: {
      type: Boolean,
      default: true,
    },
  },
  {
    timestamps: true,
  }
);

export const Game = mongoose.model('Game', gameSchema);