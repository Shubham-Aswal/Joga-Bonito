/**
 * Adaptive Engine Client Service
 * Handles communication with the standalone Python FastAPI Adaptive Engine microservice.
 */

const getAdaptiveEngineUrl = () => {
  const url = process.env.ADAPTIVE_ENGINE_URL || "http://localhost:8001";
  return url.replace(/\/+$/, "");
};

const REQUEST_TIMEOUT_MS = 6000;

/**
 * Fetch the adaptive difficulty state for a given user.
 * @param {string} userId - User ID (MongoDB _id or custom string)
 * @returns {Promise<Object>} Adaptive state object
 */
export const getAdaptiveState = async (userId) => {
  if (!userId) {
    return {
      user_id: "",
      current_level: 1,
      recent_scores: [],
      average_score: 0.0,
      trend: "new_user",
      is_new_user: true,
      analysis: "We'll start with an easier level and gradually adjust the challenge based on your performance.",
      last_updated: null,
    };
  }

  const baseUrl = getAdaptiveEngineUrl();
  const url = `${baseUrl}/api/v1/adaptive/${encodeURIComponent(String(userId))}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.warn(`[AdaptiveEngine] GET ${url} responded with status ${response.status}`);
      return {
        user_id: String(userId),
        current_level: 1,
        recent_scores: [],
        average_score: 0.0,
        trend: "new_user",
        is_new_user: true,
        analysis: "Starting with a baseline level.",
        last_updated: null,
      };
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.warn(`[AdaptiveEngine] Failed to connect to adaptive engine at ${url}:`, error.message);
    return {
      user_id: String(userId),
      current_level: 1,
      recent_scores: [],
      average_score: 0.0,
      trend: "new_user",
      is_new_user: true,
      analysis: "Starting with a baseline level.",
      last_updated: null,
      fallback: true,
    };
  }
};

/**
 * Submit game performance score to the adaptive engine to calculate the next difficulty level.
 * @param {Object} payload - Game score & metrics payload
 * @returns {Promise<Object>} Adaptive recommendation response
 */
export const submitGameScore = async ({
  userId,
  gameType,
  score,
  levelPlayed,
  accuracy,
  responseTime,
  mistakes,
  hintsUsed,
  sessionDuration,
  cognitiveDomain,
}) => {
  const baseUrl = getAdaptiveEngineUrl();
  const url = `${baseUrl}/api/v1/adaptive/score`;

  const parsedScore = Math.max(0, Math.min(100, Math.round(Number(score) || 0)));
  const parsedLevel = Math.max(1, Math.min(10, Math.round(Number(levelPlayed) || 1)));

  // If accuracy is passed as 0-1 (e.g. 0.85), convert to percentage 0-100
  let parsedAccuracy = accuracy !== undefined && accuracy !== null ? Number(accuracy) : undefined;
  if (parsedAccuracy !== undefined && parsedAccuracy <= 1 && parsedAccuracy > 0) {
    parsedAccuracy = Math.round(parsedAccuracy * 100 * 10) / 10;
  }

  const body = {
    user_id: String(userId),
    game_type: String(gameType || "default").trim().toLowerCase(),
    score: parsedScore,
    level_played: parsedLevel,
    accuracy: parsedAccuracy,
    response_time: responseTime !== undefined ? Number(responseTime) : undefined,
    mistakes: mistakes !== undefined ? Math.max(0, Math.round(Number(mistakes))) : undefined,
    hints_used: hintsUsed !== undefined ? Math.max(0, Math.round(Number(hintsUsed))) : undefined,
    session_duration: sessionDuration !== undefined ? Number(sessionDuration) : undefined,
    cognitive_domain: cognitiveDomain ? String(cognitiveDomain).trim().toLowerCase() : undefined,
  };

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      console.warn(`[AdaptiveEngine] POST ${url} responded with status ${response.status}: ${errorText}`);
      return {
        user_id: String(userId),
        current_level: parsedLevel,
        recommended_level: parsedLevel,
        decision: "maintain",
        challenge_state: "optimal",
        trend: "stable",
        latest_score: parsedScore,
        average_recent_score: parsedScore,
        confidence: 0.7,
        analysis: "You're holding steady at this level. Keep practicing!",
        decision_source: "fallback_backend_error",
      };
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.warn(`[AdaptiveEngine] Failed to submit score to adaptive engine at ${url}:`, error.message);
    return {
      user_id: String(userId),
      current_level: parsedLevel,
      recommended_level: parsedLevel,
      decision: "maintain",
      challenge_state: "optimal",
      trend: "stable",
      latest_score: parsedScore,
      average_recent_score: parsedScore,
      confidence: 0.7,
      analysis: "You're holding steady at this level. Keep practicing!",
      decision_source: "fallback_backend_connection",
    };
  }
};
