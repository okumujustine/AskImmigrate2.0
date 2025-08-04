// src/components/SessionStatus.tsx - Fixed to match existing interface

import { MessageSquare, Globe, Zap } from "lucide-react";
import React, { useState } from "react";
import multilingualService from "../services/multilingualService";

interface SessionStatusProps {
  hasSessionId: boolean;
  sessionId?: string;
  responseMetadata?: any; // New optional prop for multilingual metadata
}

export const SessionStatus: React.FC<SessionStatusProps> = ({
  hasSessionId,
  sessionId,
  responseMetadata,
}) => {
  const [showMetadata, setShowMetadata] = useState(false);

  // Get UI strings from the multilingual service
  const uiStrings = multilingualService.getUIStrings();

  const truncateSessionId = (id: string, maxLength: number = 20) => {
    if (id.length <= maxLength) return id;
    return id.substring(0, maxLength) + "...";
  };

  const displayText = hasSessionId
    ? `${uiStrings.sessionActive} ${truncateSessionId(sessionId || "", 20)}`
    : uiStrings.sessionReady;

  // Determine if we should show multilingual indicator
  const isMultilingual =
    responseMetadata?.multilingual_processing ||
    responseMetadata?.translation_method !== "english_native";

  const translationMethod = responseMetadata?.translation_method;
  const isNativeResponse = translationMethod === "native_spanish_llm";

  return (
    <div className="session-status">
      <div className="status-indicator">
        <MessageSquare size={16} className="status-icon" />
        <span
          className="status-text"
          title={
            hasSessionId && sessionId && sessionId.length > 20
              ? `${uiStrings.sessionActive} ${sessionId}`
              : undefined
          }
        >
          {displayText}
        </span>

        {/* Multilingual indicators */}
        {isMultilingual && (
          <>
            <span title="Multilingual response">
              <Globe size={14} className="multilingual-icon" />
            </span>
            {isNativeResponse && (
              <span title="Native language generation">
                <Zap size={12} className="native-response-icon" />
              </span>
            )}
          </>
        )}

        {/* Metadata toggle for debugging */}
        {responseMetadata && (
          <button
            className="metadata-toggle"
            onClick={() => setShowMetadata(!showMetadata)}
            title="Show response metadata"
          >
            📊
          </button>
        )}
      </div>

      {/* Metadata details (expandable) */}
      {showMetadata && responseMetadata && (
        <div className="metadata-details">
          <div className="metadata-row">
            <strong>Language:</strong>{" "}
            {responseMetadata.target_language || "en"}
          </div>
          {responseMetadata.translation_method && (
            <div className="metadata-row">
              <strong>Method:</strong> {responseMetadata.translation_method}
            </div>
          )}
          {responseMetadata.confidence && (
            <div className="metadata-row">
              <strong>Confidence:</strong>{" "}
              {(responseMetadata.confidence * 100).toFixed(1)}%
            </div>
          )}
          {responseMetadata.processing_time && (
            <div className="metadata-row">
              <strong>Time:</strong>{" "}
              {responseMetadata.processing_time.toFixed(2)}s
            </div>
          )}
        </div>
      )}
    </div>
  );
};
